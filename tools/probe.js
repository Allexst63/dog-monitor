// временная проверка источников (ветка probe) — в основной сайт не входит
const WS = require('ws');
const O = 'https://allexst63.github.io';
const sleep = ms => new Promise(r => setTimeout(r, ms));
async function rest(name, url, show) {
  try {
    const r = await fetch(url, { headers: { Origin: O, 'User-Agent': 'Mozilla/5.0' } });
    const t = await r.text();
    console.log(`REST ${name} ${r.status} len=${t.length} acao=${r.headers.get('access-control-allow-origin')} ct=${r.headers.get('content-type')}`);
    if (show) console.log('   ', t.slice(0, show).replace(/\s+/g, ' '));
    try { return JSON.parse(t); } catch (e) { return null; }
  } catch (e) { console.log(`REST ${name} ERR ${e.message}`); return null; }
}
function ws(name, url, subs, ms, onmsg, opt = {}) {
  return new Promise(res => {
    const st = { n: 0, t0: Date.now(), last: 0, maxGap: 0, kinds: {}, first: [] };
    let w; try { w = new WS(url, { origin: O }); } catch (e) { console.log('WS', name, 'ERR', e.message); return res(st); }
    let ping;
    w.on('open', () => { console.log(`WS ${name} open in ${Date.now() - st.t0}ms`); subs.forEach(s => w.send(typeof s === 'string' ? s : JSON.stringify(s))); if (opt.ping) ping = setInterval(() => w.send(opt.ping), 15000); });
    w.on('message', async (d, bin) => { try { await onmsg(d, bin, st, w); } catch (e) { st.err = e.message; } });
    w.on('error', e => console.log(`WS ${name} error ${e.message}`));
    w.on('close', (c, r) => console.log(`WS ${name} close ${c} ${r}`));
    w.on('unexpected-response', (rq, rs) => console.log(`WS ${name} HTTP ${rs.statusCode}`));
    setTimeout(() => { clearInterval(ping); try { w.close(); } catch (e) { } res(st); }, ms);
  });
}
const gap = (st, key) => { const t = Date.now(); const k = st.g || (st.g = {}); const x = k[key] || (k[key] = { n: 0, last: 0, max: 0 }); if (x.last) x.max = Math.max(x.max, t - x.last); x.last = t; x.n++; };
(async () => {
  console.log('=== REST', new Date().toISOString());
  const fng = await rest('fng', 'https://api.alternative.me/fng/?limit=3', 500);
  await rest('fng400', 'https://api.alternative.me/fng/?limit=400&format=json', 120);
  await rest('cg-coin', 'https://api.coingecko.com/api/v3/coins/markets?vs_currency=usd&ids=dog-go-to-the-moon-rune,dogecoin,shiba-inu,pepe&price_change_percentage=24h,7d,30d', 1500);
  const meme = await rest('cg-meme', 'https://api.coingecko.com/api/v3/coins/markets?vs_currency=usd&category=meme-token&order=market_cap_desc&per_page=100&page=1&price_change_percentage=24h,7d,30d', 200);
  if (Array.isArray(meme)) { const i = meme.findIndex(x => /dog-go-to-the-moon/.test(x.id)); console.log('   meme n=', meme.length, 'DOG idx', i, i >= 0 ? JSON.stringify(meme[i]).slice(0, 900) : meme.slice(0, 5).map(x => x.id)); }
  await rest('cg-search', 'https://api.coingecko.com/api/v3/search?query=dog%20go%20to%20the%20moon', 600);
  await rest('cg-global', 'https://api.coingecko.com/api/v3/global', 300);
  await rest('cmc-fng', 'https://api.coinmarketcap.com/data-api/v3/fear-greed/chart?start=1790000000&end=1795000000', 300);
  const kr = await rest('kraken', 'https://api.kraken.com/0/public/Depth?pair=DOGUSD&count=500');
  await rest('kraken-ticker', 'https://api.kraken.com/0/public/Ticker?pair=DOGUSD,USDTUSD', 900);
  const g = await rest('gate', 'https://api.gateio.ws/api/v4/spot/order_book?currency_pair=DOG_USDT&interval=0&limit=100&with_id=true');
  const df = await rest('digifinex', 'https://openapi.digifinex.com/v3/order_book?symbol=dog_usdt&limit=150');
  await rest('df-ticker', 'https://openapi.digifinex.com/v3/ticker?symbol=dog_usdt', 600);
  const dft = await rest('df-trades', 'https://openapi.digifinex.com/v3/trades?symbol=dog_usdt&limit=100', 100);
  const gt = await rest('gate-trades', 'https://api.gateio.ws/api/v4/spot/trades?currency_pair=DOG_USDT&limit=100', 100);
  await rest('gate-ticker', 'https://api.gateio.ws/api/v4/spot/tickers?currency_pair=DOG_USDT', 600);
  await rest('coinw', 'https://api.coinw.com/api/v1/public?command=returnOrderBook&symbol=DOG(RUNE)_USDT&size=100', 300);
  await rest('mexc', 'https://api.mexc.com/api/v3/depth?symbol=DOGUSDT&limit=20', 200);
  await rest('mexc-tk', 'https://api.mexc.com/api/v3/ticker/24hr?symbol=DOGUSDT', 500);
  await rest('bingx', 'https://open-api.bingx.com/openApi/spot/v1/market/depth?symbol=DOG-USDT&limit=20', 200);
  await rest('bitget', 'https://api.bitget.com/api/v2/spot/market/orderbook?symbol=DOGUSDT&type=step0&limit=5', 300);
  await rest('okx', 'https://www.okx.com/api/v5/market/books?instId=DOG-USDT&sz=5', 300);
  await rest('bybit', 'https://api.bybit.com/v5/market/orderbook?category=spot&symbol=DOGUSDT&limit=5', 300);
  await rest('kucoin', 'https://api.kucoin.com/api/v1/market/orderbook/level2_20?symbol=DOG-USDT', 300);
  await rest('htx', 'https://api.huobi.pro/market/depth?symbol=dogusdt&type=step0&depth=5', 300);
  await rest('bitrue', 'https://openapi.bitrue.com/api/v1/depth?symbol=DOGUSDT&limit=5', 300);
  if (g && df) {
    console.log('=== Gate vs DigiFinex (точные уровни)');
    for (const side of ['bids', 'asks']) {
      const G = g[side].map(x => [+x[0], +x[1]]), D = df[side].map(x => [+x[0], +x[1]]);
      console.log(side, 'gate top', JSON.stringify(G.slice(0, 25)));
      console.log(side, 'digi top', JSON.stringify((side === 'asks' ? D.slice().sort((a, b) => a[0] - b[0]) : D.slice().sort((a, b) => b[0] - a[0])).slice(0, 25)));
      let m = 0, t = 0, mv = 0, tv = 0; const gm = new Map(G.map(x => [x[0].toFixed(7), x[1]]));
      for (const [p, q] of D) { const c = gm.get(p.toFixed(7)); if (!(p >= G[G.length - 1][0] === (side === 'bids')) && side === 'bids') continue; t++; tv += q; if (c && Math.abs(c - q) <= 0.15 * Math.max(c, q)) { m++; mv += q; } }
      console.log(side, 'digi levels in gate range', t, 'matching ±15%', m, 'vol share', (mv / tv).toFixed(3), 'gate n', G.length, 'digi n', D.length);
    }
    console.log('df trades', JSON.stringify((dft && dft.data || []).slice(0, 25)));
    console.log('gate trades', JSON.stringify((gt || []).slice(0, 25).map(x => [x.create_time, x.side, x.price, x.amount])));
  }
  console.log('=== WS');
  // Kraken v2: ticker + book 500, сверка с REST в конце
  const kb = { b: new Map(), a: new Map() };
  const ks = await ws('kraken', 'wss://ws.kraken.com/v2', [{ method: 'subscribe', params: { channel: 'book', symbol: ['DOG/USD'], depth: 500 } }, { method: 'subscribe', params: { channel: 'ticker', symbol: ['DOG/USD'] } }, { method: 'subscribe', params: { channel: 'trade', symbol: ['DOG/USD'], snapshot: true } }], 40000, (d, bin, st) => {
    const m = JSON.parse(d.toString()); const key = (m.channel || m.method || '?') + ':' + (m.type || (m.success != null ? 'ok=' + m.success : ''));
    gap(st, key);
    if (st.first.length < 8 && !st.kinds[key]) { st.kinds[key] = 1; console.log('  kraken', key, d.toString().slice(0, 700)); }
    if (m.channel === 'book') for (const x of m.data) { for (const s of ['bids', 'asks']) for (const l of x[s] || []) { const M = s === 'bids' ? kb.b : kb.a; if (l.qty === 0) M.delete(l.price); else M.set(l.price, l.qty); } st.cs = x.checksum; if (m.type === 'update' && !st.upd) { st.upd = 1; console.log('  kraken update sample', JSON.stringify(m).slice(0, 500)); } }
  });
  console.log('  kraken gaps', JSON.stringify(ks.g));
  const kr2 = await rest('kraken-after', 'https://api.kraken.com/0/public/Depth?pair=DOGUSD&count=500');
  if (kr2 && kr2.result) {
    const R = Object.values(kr2.result)[0];
    for (const [s, M, desc] of [['bids', kb.b, true], ['asks', kb.a, false]]) {
      const W = [...M.entries()].sort((x, y) => desc ? y[0] - x[0] : x[0] - y[0]).slice(0, 500), RR = R[s].map(x => [+x[0], +x[1]]);
      const rm = new Map(RR.map(x => [x[0].toFixed(8), x[1]])); let same = 0; for (const [p, q] of W) { const c = rm.get(p.toFixed(8)); if (c != null && Math.abs(c - q) < 1e-3 * Math.max(1, q)) same++; }
      console.log(`  kraken ${s}: ws n=${M.size} top=${JSON.stringify(W.slice(0, 3))} rest n=${RR.length} top=${JSON.stringify(RR.slice(0, 3))} same=${same}/${W.length} wsEdge=${W.length ? W[W.length - 1][0] : null} restEdge=${RR[RR.length - 1][0]}`);
    }
  }
  // Gate v4
  for (const pl of [['DOG_USDT', '100', '100ms'], ['DOG_USDT', '100', '1000ms'], ['DOG_USDT', '50', '100ms']]) {
    const gs = await ws('gate ' + pl.join('/'), 'wss://api.gateio.ws/ws/v4/', [{ time: Math.floor(Date.now() / 1000), channel: 'spot.order_book', event: 'subscribe', payload: pl }, { time: Math.floor(Date.now() / 1000), channel: 'spot.trades', event: 'subscribe', payload: ['DOG_USDT'] }, { time: Math.floor(Date.now() / 1000), channel: 'spot.tickers', event: 'subscribe', payload: ['DOG_USDT'] }], 15000, (d, bin, st) => {
      const m = JSON.parse(d.toString()); const key = m.channel + ':' + m.event; gap(st, key);
      if (!st.kinds[key]) { st.kinds[key] = 1; console.log('  gate', key, d.toString().slice(0, 600)); }
      if (m.channel === 'spot.order_book' && m.event === 'update') st.sz = [m.result.bids.length, m.result.asks.length];
    });
    console.log('  gate gaps', JSON.stringify(gs.g), gs.sz);
  }
  // MEXC: приходят ли снимки стакана постоянно
  const ms = await ws('mexc', 'wss://wbs-api.mexc.com/ws', [{ method: 'SUBSCRIPTION', params: ['spot@public.limit.depth.v3.api.pb@DOGUSDT@20', 'spot@public.aggre.deals.v3.api.pb@100ms@DOGUSDT', 'spot@public.aggre.bookTicker.v3.api.pb@100ms@DOGUSDT'] }], 75000, (d, bin, st) => {
    if (!bin) { gap(st, 'text'); if (!st.kinds[d.toString().slice(0, 40)]) { st.kinds[d.toString().slice(0, 40)] = 1; console.log('  mexc text', d.toString().slice(0, 300)); } return; }
    const s = d.toString('latin1'); const key = s.includes('limit.depth') ? 'depth' : s.includes('deals') ? 'deals' : s.includes('bookTicker') ? 'bookTicker' : 'other'; gap(st, key);
    if (!st.kinds[key]) { st.kinds[key] = 1; console.log('  mexc', key, 'len', d.length, s.replace(/[^\x20-\x7e]/g, '.').slice(0, 400)); }
  }, { ping: '{"method":"PING"}' });
  console.log('  mexc gaps', JSON.stringify(ms.g));
  const zlib = require('zlib');
  const bs = await ws('bingx', 'wss://open-api-ws.bingx.com/market', [{ id: 'a', reqType: 'sub', dataType: 'DOG-USDT@depth100' }, { id: 'b', reqType: 'sub', dataType: 'DOG-USDT@trade' }], 40000, (d, bin, st, w) => {
    let t = d.toString(); try { t = zlib.gunzipSync(d).toString(); } catch (e) { }
    if (t === 'Ping') { w.send('Pong'); gap(st, 'ping'); return; }
    let m; try { m = JSON.parse(t); } catch (e) { gap(st, 'raw'); return; }
    if (m.ping) { w.send(JSON.stringify({ pong: m.ping, time: m.time })); gap(st, 'ping'); return; }
    const key = String(m.dataType || 'ack'); gap(st, key);
    if (!st.kinds[key]) { st.kinds[key] = 1; console.log('  bingx', key, t.slice(0, 400)); }
  });
  console.log('  bingx gaps', JSON.stringify(bs.g));
  // DigiFinex и CoinW WebSocket — есть ли вообще
  const ds = await ws('digifinex', 'wss://openapi.digifinex.com/ws/v1/', [{ id: 1, method: 'depth.subscribe', params: ['dog_usdt'] }, { id: 2, method: 'trades.subscribe', params: ['dog_usdt'] }], 15000, (d, bin, st) => {
    let t = d.toString(); try { t = zlib.inflateSync(d).toString(); } catch (e) { }
    gap(st, t.slice(0, 30).replace(/[^\x20-\x7e]/g, '.')); if (st.n++ < 3) console.log('  digifinex', t.slice(0, 500));
  });
  console.log('  digifinex gaps', JSON.stringify(Object.fromEntries(Object.entries(ds.g || {}).slice(0, 6))));
  console.log('=== done');
  process.exit(0);
})();
