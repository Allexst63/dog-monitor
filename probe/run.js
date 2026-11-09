// Временная проверка: образцы сообщений WebSocket MEXC и BingX из браузера на адресе сайта
const { chromium } = require('playwright');
const fs = require('fs');
const OUT = 'probe/out2';
fs.mkdirSync(OUT, { recursive: true });
(async () => {
  const b = await chromium.launch();
  const p = await (await b.newContext()).newPage();
  await p.goto('https://allexst63.github.io/dog-monitor/robots.txt', { waitUntil: 'load', timeout: 60000 });
  const res = await p.evaluate(async () => {
    const gunzip = async buf => new Response(new Blob([buf]).stream().pipeThrough(new DecompressionStream('gzip'))).text();
    const b64 = u8 => { let s = ''; for (let i = 0; i < u8.length; i++) s += String.fromCharCode(u8[i]); return btoa(s); };
    const run = (url, subs, gz, n, ms) => new Promise(res => {
      const msgs = []; let done = false; const ws = new WebSocket(url); ws.binaryType = 'arraybuffer';
      const fin = () => { if (done) return; done = true; try { ws.close(); } catch (e) { } res(msgs); };
      ws.onopen = () => subs.forEach(s => ws.send(JSON.stringify(s)));
      ws.onmessage = async ev => {
        let t;
        if (typeof ev.data === 'string') t = ev.data;
        else if (gz) t = await gunzip(ev.data);
        else t = 'B64 ' + b64(new Uint8Array(ev.data));
        if (t === 'Ping') { ws.send('Pong'); msgs.push('Ping'); return; }
        msgs.push(t);
        if (msgs.length >= n) fin();
      };
      ws.onclose = ev => { msgs.push('close ' + ev.code); fin(); };
      setTimeout(fin, ms);
    });
    return {
      bingx: await run('wss://open-api-ws.bingx.com/market', [{ id: 'd1', reqType: 'sub', dataType: 'DOG-USDT@depth100' }, { id: 't1', reqType: 'sub', dataType: 'DOG-USDT@trade' }], true, 14, 30000),
      mexc_deals: await run('wss://wbs-api.mexc.com/ws', [{ method: 'SUBSCRIPTION', params: ['spot@public.aggre.deals.v3.api.pb@100ms@DOGUSDT'] }], false, 6, 45000),
      mexc_depth: await run('wss://wbs-api.mexc.com/ws', [{ method: 'SUBSCRIPTION', params: ['spot@public.limit.depth.v3.api.pb@DOGUSDT@20'] }], false, 3, 15000)
    };
  });
  fs.writeFileSync(OUT + '/ws.json', JSON.stringify(res, null, 1));
  await b.close();
})().catch(e => { fs.writeFileSync(OUT + '/err.txt', String(e && e.stack || e)); });
