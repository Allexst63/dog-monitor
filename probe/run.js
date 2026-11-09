// Временная проверка из настоящего браузера на адресе сайта (Origin: https://allexst63.github.io):
// что разрешают биржи и сервисы (fetch и WebSocket) и как работает живой сайт с настоящими данными.
const { chromium } = require('playwright');
const fs = require('fs');
const OUT = 'probe/out';
fs.mkdirSync(OUT, { recursive: true });

(async () => {
  const out = { t: new Date().toISOString(), console: [], tests: {} };
  const b = await chromium.launch();
  const ctx = await b.newContext({ viewport: { width: 390, height: 844 }, deviceScaleFactor: 2, isMobile: true, hasTouch: true, locale: 'en-US' });
  const p = await ctx.newPage();
  p.on('console', m => { if (m.type() === 'error' || m.type() === 'warning') out.console.push(m.type() + ': ' + m.text().slice(0, 300)); });
  p.on('pageerror', e => out.console.push('PAGEERROR ' + e.message));
  p.on('requestfailed', r => out.console.push('FAIL ' + r.url().slice(0, 160) + ' ' + ((r.failure() || {}).errorText || '')));
  await p.goto('https://allexst63.github.io/dog-monitor/?nosw=1#books', { waitUntil: 'load', timeout: 60000 });
  await p.waitForTimeout(25000);
  await p.screenshot({ path: OUT + '/books_live.png' });
  out.tests.book = await p.evaluate(() => ({
    rows: document.querySelectorAll('.ob-r').length,
    status: (document.querySelector('.obst') || {}).textContent,
    note: (document.querySelector('.obnote') || {}).textContent,
    trades: (document.querySelector('#obtr') || {}).innerText,
    feed: (document.querySelector('#obfeed') || {}).innerText,
    head: (document.querySelector('#obcard') || {}).innerText
  }));

  const now = Math.floor(Date.now() / 1000);
  out.tests.fetch = await p.evaluate(async (now) => {
    const urls = {
      cb_candles: 'https://api.exchange.coinbase.com/products/BTC-USD/candles?granularity=86400&start=2024-04-20T00:00:00Z&end=2025-02-14T00:00:00Z',
      kr_xbt_d1: 'https://api.kraken.com/0/public/OHLC?pair=XBTUSD&interval=1440',
      kr_dog_15: 'https://api.kraken.com/0/public/OHLC?pair=DOGUSD&interval=15',
      kr_dog_240: 'https://api.kraken.com/0/public/OHLC?pair=DOGUSD&interval=240',
      kr_trades_3d: 'https://api.kraken.com/0/public/Trades?pair=DOGUSD&count=1000&since=' + (now - 3 * 86400) + '000000000',
      gate_tr_from: 'https://api.gateio.ws/api/v4/spot/trades?currency_pair=DOG_USDT&limit=1000&from=' + (now - 6 * 3600) + '&to=' + now,
      gate_c_1h: 'https://api.gateio.ws/api/v4/spot/candlesticks?currency_pair=DOG_USDT&interval=1h&limit=1000',
      gate_raw: 'https://api.gateio.ws/api/v4/spot/order_book?currency_pair=DOG_USDT&interval=0&limit=100',
      ord_addr: 'https://ordinals.com/address/bc1plzs2lltvv29k603w5m0aqma5e8w0n3pc77dt89l5w9hurmdfgd0swdhspn',
      dd_stats: 'https://www.dogdata.xyz/api/dog-rune/stats',
      dd_conc: 'https://www.dogdata.xyz/api/metrics/holder-concentration',
      dd_top: 'https://www.dogdata.xyz/api/dog-rune/top-holders?limit=100',
      mexc_depth: 'https://api.mexc.com/api/v3/depth?symbol=DOGUSDT&limit=100',
      bingx_depth: 'https://open-api.bingx.com/openApi/spot/v1/market/depth?symbol=DOG-USDT&limit=100'
    };
    const res = {};
    for (const [k, u] of Object.entries(urls)) {
      try {
        const r = await fetch(u, { cache: 'no-store', headers: k === 'ord_addr' ? { Accept: 'application/json' } : {} });
        const txt = await r.text();
        res[k] = { ok: r.ok, status: r.status, len: txt.length, head: txt.slice(0, 400), tail: txt.slice(-200) };
      } catch (e) { res[k] = { err: String(e) }; }
    }
    return res;
  }, now);

  out.tests.ws = await p.evaluate(async () => {
    const gunzip = async buf => { const s = new Blob([buf]).stream().pipeThrough(new DecompressionStream('gzip')); return await new Response(s).text(); };
    const b64 = u8 => { let s = ''; for (let i = 0; i < u8.length; i++) s += String.fromCharCode(u8[i]); return btoa(s); };
    const run = (name, url, subs, opts) => new Promise(res => {
      const msgs = []; let done = false, ws;
      const fin = why => { if (done) return; done = true; try { ws.close(); } catch (e) { } res({ name, why, msgs }); };
      try { ws = new WebSocket(url); } catch (e) { res({ name, why: 'ctor ' + e, msgs }); return; }
      ws.binaryType = 'arraybuffer';
      ws.onopen = () => { msgs.push('open'); for (const s of subs) ws.send(typeof s === 'string' ? s : JSON.stringify(s)); };
      ws.onmessage = async ev => {
        let txt;
        if (typeof ev.data === 'string') txt = ev.data;
        else if (opts && opts.gzip) { try { txt = await gunzip(ev.data); } catch (e) { txt = 'GZERR ' + e + ' ' + b64(new Uint8Array(ev.data).slice(0, 200)); } }
        else txt = 'B64 ' + ev.data.byteLength + ' ' + b64(new Uint8Array(ev.data).slice(0, 6000));
        if (txt === 'Ping' || txt === 'ping') { try { ws.send('Pong'); } catch (e) { } msgs.push('Ping'); return; }
        msgs.push(txt.slice(0, 6000));
        if (msgs.length >= (opts && opts.n || 6)) fin('enough');
      };
      ws.onerror = () => msgs.push('error');
      ws.onclose = ev => { msgs.push('close ' + ev.code + ' ' + ev.reason); fin('closed'); };
      setTimeout(() => fin('timeout'), (opts && opts.ms) || 15000);
    });
    const r = [];
    r.push(await run('bingx', 'wss://open-api-ws.bingx.com/market', [
      { id: 'd1', reqType: 'sub', dataType: 'DOG-USDT@depth100' },
      { id: 'd2', reqType: 'sub', dataType: 'DOG-USDT@depth50' },
      { id: 't1', reqType: 'sub', dataType: 'DOG-USDT@trade' }
    ], { gzip: true, n: 8, ms: 20000 }));
    r.push(await run('mexc_pb', 'wss://wbs-api.mexc.com/ws', [
      { method: 'SUBSCRIPTION', params: ['spot@public.limit.depth.v3.api.pb@DOGUSDT@20', 'spot@public.aggre.deals.v3.api.pb@100ms@DOGUSDT'] }
    ], { n: 8, ms: 20000 }));
    r.push(await run('mexc_json', 'wss://wbs.mexc.com/ws', [
      { method: 'SUBSCRIPTION', params: ['spot@public.limit.depth.v3.api@DOGUSDT@20'] }
    ], { n: 4, ms: 12000 }));
    return r;
  });

  // главная и вкладки живого сайта
  for (const [tab, file] of [['overview', 'home_live'], ['wallets', 'wallets_live']]) {
    try { await p.evaluate(t => { location.hash = t; }, tab); await p.waitForTimeout(1500); await p.screenshot({ path: OUT + '/' + file + '.png' }); } catch (e) { }
  }
  fs.writeFileSync(OUT + '/browser.json', JSON.stringify(out, null, 1));
  await b.close();
})().catch(e => { fs.writeFileSync(OUT + '/browser_err.txt', String(e && e.stack || e)); process.exit(0); });
