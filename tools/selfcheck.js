#!/usr/bin/env node
/* DOG Монитор — автопроверка сайта в настоящем браузере (телефонный экран).

   node tools/selfcheck.js <папка сайта> <куда записать итог .json> [--shots <папка для снимков экрана>] [--url <адрес сайта>]

   Поднимает сайт из папки (со свежими data/*.json, ещё до выкладки) на локальном адресе, открывает его в Chrome,
   проходит по вкладкам и проверяет: страница работает без ошибок, цена и графики нарисованы, недельные свечи и
   «DOG и биткоин» отвечают на нажатие, значок TradingView ведёт на график DOG, кошельки и «как держат DOG» на месте,
   ничего не вылезает за экран, данные свежие. Итог — data/selfcheck.json (виден на сайте в листе «Обновление и
   проверка» и в утреннем сообщении). Код выхода 1, если хоть одна проверка не прошла.
   Нужен playwright-core (или playwright) и Chrome/Chromium. В сеть ходит только сама страница — как у читателя. */
const fs = require('fs');
const path = require('path');
const http = require('http');

const args = process.argv.slice(2);
const opt = k => { const i = args.indexOf(k); return i >= 0 ? args.splice(i, 2)[1] : null; };
const SHOTS = opt('--shots'), URL0 = opt('--url');
const SITE = path.resolve(args[0] || '.'), OUT = args[1] ? path.resolve(args[1]) : null;

let pw;
try { pw = require('playwright-core'); } catch (e) { pw = require('playwright'); }

const MIME = { '.html': 'text/html; charset=utf-8', '.js': 'text/javascript; charset=utf-8', '.json': 'application/json; charset=utf-8', '.css': 'text/css', '.svg': 'image/svg+xml', '.png': 'image/png', '.jpg': 'image/jpeg', '.woff': 'font/woff', '.webmanifest': 'application/manifest+json', '.txt': 'text/plain; charset=utf-8' };
function serve() {
  return new Promise(resolve => {
    const srv = http.createServer((req, res) => {
      let p = decodeURIComponent(req.url.split('?')[0]);
      if (p.endsWith('/')) p += 'index.html';
      const f = path.join(SITE, p);
      if (!f.startsWith(SITE) || !fs.existsSync(f) || fs.statSync(f).isDirectory()) { res.writeHead(404); res.end('not found'); return; }
      res.writeHead(200, { 'content-type': MIME[path.extname(f)] || 'application/octet-stream', 'cache-control': 'no-store' });
      fs.createReadStream(f).pipe(res);
    });
    srv.listen(0, '127.0.0.1', () => resolve(srv));
  });
}

const items = [];
const add = (ok, t, en, d) => { items.push(Object.assign({ ok: !!ok, t, en }, d ? { d: String(d).slice(0, 200) } : {})); console.log((ok ? 'OK   ' : 'FAIL ') + t + (d && !ok ? ' — ' + String(d).slice(0, 200) : '')); };
const hours = iso => { const t = Date.parse(iso || ''); return isNaN(t) ? null : (Date.now() - t) / 36e5; };

(async () => {
  const t0 = Date.now();
  const srv = URL0 ? null : await serve();
  const base = URL0 || `http://127.0.0.1:${srv.address().port}/`;
  let browser;
  try { browser = await pw.chromium.launch({ channel: 'chrome' }); } catch (e) { browser = await pw.chromium.launch(); }
  const ctx = await browser.newContext({ viewport: { width: 390, height: 844 }, deviceScaleFactor: SHOTS ? 2 : 1, isMobile: true, hasTouch: true, locale: 'en-US', timezoneId: 'Europe/Berlin' });
  const page = await ctx.newPage();
  const errs = [];
  page.on('pageerror', e => errs.push(String(e && e.message || e)));
  const shot = async name => { if (SHOTS) { fs.mkdirSync(SHOTS, { recursive: true }); await page.screenshot({ path: path.join(SHOTS, name + '.png') }); } };
  const tab = async k => { await page.evaluate(k2 => { const b = document.querySelector(`#tabbar [data-tab="${k2}"]`) || document.querySelector(`[data-tab="${k2}"]`); if (b) b.click(); else location.hash = '#' + k2; }, k); await page.waitForTimeout(700); };
  const noOverflow = () => page.evaluate(() => document.scrollingElement.scrollWidth <= window.innerWidth + 1);
  const wait = (fn, ms, arg) => page.waitForFunction(fn, arg, { timeout: ms }).then(() => true, () => false);

  try {
    await page.goto(base + '?nosw=1#overview', { waitUntil: 'load', timeout: 45000 });
    // 1. главная
    const gotPrice = await wait(() => { const p = document.querySelector('#hprice'); return !!p && /\d/.test(p.textContent); }, 25000);
    const price = gotPrice ? await page.evaluate(() => document.querySelector('#hprice').textContent.trim()) : '';
    add(gotPrice, 'Главная: цена DOG показана' + (price ? ` (${price.slice(0, 14)})` : ''), 'Home: DOG price is shown' + (price ? ` (${price.slice(0, 14)})` : ''));
    const gotChart = await wait(() => !!document.querySelector('#pchart canvas, #pchart svg'), 15000);
    add(gotChart, 'Главная: график цены нарисован', 'Home: price chart is drawn');
    add(await page.evaluate(() => document.querySelectorAll('#p-overview .tile').length >= 2 && !!document.querySelector('#p-overview .sum')), 'Главная: плитки и «что нового» на месте', 'Home: tiles and “what’s new” are in place');
    await page.waitForTimeout(4000);                       // даём странице закончить своё онлайн-обновление
    const st = await page.evaluate(() => ({ c: document.querySelector('#status').className, t: document.querySelector('#status-t').textContent }));
    add(/\d\d:\d\d/.test(st.t), `Статус в шапке показывает время данных («${st.t.trim().slice(0, 40)}»)`, `Header status shows the data time (“${st.t.trim().slice(0, 40)}”)`);
    add(await noOverflow(), 'Главная: ничего не вылезает за экран телефона', 'Home: nothing overflows the phone screen');
    await shot('1-home');

    // 2. стакан
    await tab('books');
    const rows = await page.evaluate(() => document.querySelectorAll('#p-books .ob-r, #p-books [data-lv], #p-books tr').length);
    add(rows >= 10 && await noOverflow(), `Стакан: уровни цен показаны (${rows})`, `Order book: price levels are shown (${rows})`);
    await shot('2-books');

    // 3. графики
    await tab('charts');
    const candles = await wait(() => !!document.querySelector('#tvchart canvas') && /\d/.test((document.querySelector('#tvleg') || {}).textContent || ''), 20000);
    add(candles, 'Графики: свечи и подпись с ценами нарисованы', 'Charts: candles and the price legend are drawn');
    add(await page.evaluate(() => !document.querySelector('#dlchart') && !/Delta|Дельта/.test(document.querySelector('#p-charts').textContent)), 'Графики: блока «Дельта» нет', 'Charts: no “Delta” block');
    await shot('3-charts');
    await page.evaluate(() => { const b = document.querySelector('#ch-tf [data-chtf="1w"]'); if (b) b.click(); });
    const week = await wait(() => /1w|1н/.test((document.querySelector('#tvleg') || {}).textContent || '') && !!document.querySelector('#tvchart canvas'), 20000);
    add(week, 'Графики: недельные свечи (1н) с RSI открываются', 'Charts: weekly candles (1w) with RSI open');
    await page.waitForTimeout(600);
    await shot('4-charts-week');
    // нажатие на свечу закрепляет её значения
    const tapIn = async (sel, fx, fy) => { const b = await page.locator(sel).boundingBox(); if (!b) return false; await page.touchscreen.tap(b.x + b.width * fx, b.y + b.height * fy); await page.waitForTimeout(500); return true; };
    await page.locator('#tvchart').scrollIntoViewIfNeeded();
    await tapIn('#tvchart', 0.35, 0.25);
    add(await page.evaluate(() => !!document.querySelector('#tvleg .tv-when')), 'Графики: нажатие на свечу показывает её дату и цены', 'Charts: tapping a candle shows its date and prices');
    // значок TradingView → график DOG/USD
    const tv = await page.evaluate(() => { const a = document.querySelector('#tvchart a#tv-attr-logo'); return a ? a.getAttribute('href') : null; });
    add(tv && /tradingview\.com\/chart\/\?symbol=KRAKEN%3ADOGUSD/.test(tv), 'Значок TradingView открывает график DOG/USD', 'The TradingView mark opens the DOG/USD chart', tv);
    // DOG и биткоин
    await page.evaluate(() => { const e = document.querySelector('#crchart'); if (e) e.scrollIntoView({ block: 'center' }); });
    const cr = await wait(() => !!document.querySelector('#crchart canvas') && /BTC/.test((document.querySelector('#crleg') || {}).textContent || ''), 25000);
    add(cr, 'Графики: «DOG и биткоин» нарисован, значения в подписи', 'Charts: “DOG and bitcoin” is drawn with values in the legend');
    if (cr) {
      const before = await page.evaluate(() => document.querySelector('#crleg').textContent);
      await tapIn('#crchart', 0.4, 0.2);
      const after = await page.evaluate(() => document.querySelector('#crleg').textContent);
      add(after !== before && await page.evaluate(() => !!document.querySelector('#crleg [data-crlast]')), 'Графики: нажатие на день показывает значения всех линий в этот день', 'Charts: tapping a day shows every line’s value on that day', after.slice(0, 120));
      await shot('5-charts-btc');
    } else add(false, 'Графики: нажатие на день показывает значения всех линий в этот день', 'Charts: tapping a day shows every line’s value on that day');
    add(await page.evaluate(() => !document.querySelector('#p-charts .tv-wait')), 'Графики: ничего не «зависло» на загрузке', 'Charts: nothing is stuck loading');
    add(await noOverflow(), 'Графики: ничего не вылезает за экран телефона', 'Charts: nothing overflows the phone screen');

    // 4. кошельки
    await tab('wallets');
    const w = await page.evaluate(() => ({ rows: document.querySelectorAll('#wlist .wrow').length, hk: (document.querySelector('#p-wallets .hk') || {}).textContent || '', own: !!document.querySelector('#p-wallets .own-bar'), warn: !!document.querySelector('#p-wallets .tag.warn') }));
    add(w.rows >= 25 && w.own, `Кошельки: топ-100 и «кто владеет DOG» показаны (${w.rows} строк)`, `Wallets: top 100 and “who owns DOG” are shown (${w.rows} rows)`);
    add(/\d[\d.,]*%/.test(w.hk), 'Кошельки: «как держат DOG» — доля в прибыли, в убытке и без движения больше года', 'Wallets: “how DOG is held” — share in profit, at a loss and unmoved for over a year');
    add(await noOverflow(), 'Кошельки: ничего не вылезает за экран телефона', 'Wallets: nothing overflows the phone screen');
    await shot('6-wallets');
    await page.evaluate(() => { const e = document.querySelector('#p-wallets .hk'); if (e) e.scrollIntoView({ block: 'start' }); window.scrollBy(0, -90); });
    await page.waitForTimeout(300);
    await shot('7-wallets-held');

    // 5. новости, история
    add(await page.evaluate(() => !document.querySelector('#tabbar [data-tab="news"]')), 'Вкладки «Новости» нет (убрана)', 'No “News” tab (removed)');
    await page.evaluate(() => { const b = document.querySelector('[data-tab="history"]'); if (b) b.click(); });
    await page.waitForTimeout(600);
    add(await page.evaluate(() => document.querySelectorAll('#p-history tbody tr').length >= 3), 'История: список обновлений показан', 'History: the list of updates is shown');

    // 6. русская версия
    await page.goto(base + '?nosw=1&lang=ru#overview', { waitUntil: 'load', timeout: 45000 });
    const ru = await wait(() => /DOG Монитор/.test(document.title) && !!document.querySelector('#hprice') && /[А-Яа-я]/.test(document.querySelector('#p-overview').textContent), 25000);
    add(ru, 'Русская версия открывается', 'The Russian version opens');
    await shot('8-home-ru');
  } catch (e) {
    add(false, 'Проверка в браузере прервалась', 'The browser check was interrupted', e && e.message);
  }
  add(!errs.length, 'Страница работает без ошибок скрипта', 'The page runs without script errors', errs.slice(0, 2).join(' | '));
  await browser.close();
  if (srv) srv.close();

  // свежесть данных в файлах (то, что уйдёт на сайт)
  let live = null;
  try { live = JSON.parse(fs.readFileSync(path.join(SITE, 'data', 'live.json'), 'utf8')); } catch (e) { }
  if (live) {
    const a = hours(live.ts), top = hours((live.srcTs || {}).top100), hl = hours((live.health || {}).asof);
    const f1 = x => x == null ? '—' : x.toFixed(1).replace('.', ',');
    add(a != null && a < 11, `Сводка свежая: ${f1(a)} ч назад`, `The report is fresh: ${a == null ? '—' : a.toFixed(1)} h old`);
    add(top != null && top < 14, `Балансы топ-100 свежие: ${f1(top)} ч назад` + (live.top100Src === 'ordinals' ? ', из блокчейна' : ''), `Top-100 balances are fresh: ${top == null ? '—' : top.toFixed(1)} h old` + (live.top100Src === 'ordinals' ? ', from the blockchain' : ''));
    add(hl != null && hl < 36, `«Как держат DOG» (DOG DATA): срез ${f1(hl)} ч назад`, `“How DOG is held” (DOG DATA): snapshot ${hl == null ? '—' : hl.toFixed(1)} h old`);
    const bk = Object.keys(live.books || {}).length;
    add(bk >= 4, `Стаканы в сводке: ${bk} бирж`, `Order books in the report: ${bk} exchanges`);
    const ck = live.checks || [], okc = ck.filter(c => c.ok).length;
    add(ck.length > 0 && okc >= ck.length - 1, `Проверка данных сводки: ${okc} из ${ck.length}`, `Report data checks: ${okc} of ${ck.length}`);
  } else add(false, 'data/live.json не читается', 'data/live.json is unreadable');

  const okN = items.filter(x => x.ok).length;
  const res = { ts: new Date().toISOString().replace(/\.\d{3}Z$/, 'Z'), ok: okN === items.length, n: items.length, okN, ms: Date.now() - t0, id: live && live.id, items };
  if (OUT) fs.writeFileSync(OUT, JSON.stringify(res));
  console.log(`SELFCHECK ${okN}/${items.length} за ${Math.round(res.ms / 1000)} с`);
  process.exit(res.ok ? 0 : 1);
})().catch(e => { console.error('SELFCHECK ERR', e); process.exit(2); });
