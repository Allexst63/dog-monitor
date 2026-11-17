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
  // ширина экрана — по самому экрану: телефонный браузер расширяет страницу под слишком широкое содержимое, и тогда
  // innerWidth растёт вместе с ним (вылезание так не заметить)
  const noOverflow = () => page.evaluate(() => document.scrollingElement.scrollWidth <= Math.min(window.innerWidth, screen.width || window.innerWidth) + 1);
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
    const fng = await page.evaluate(() => [...document.querySelectorAll('#fng-box .fng-g')].map(g => (g.querySelector('.gnum') || {}).textContent || ''));
    const fngOrd = await page.evaluate(() => [...document.querySelectorAll('#fng-box .fng-g')].map(g => g.dataset.info).join(','));
    const fngTop = await page.evaluate(() => { const f = document.querySelector('#fng-box .fng'), h = document.querySelector('#p-overview .hero'); return !!f && !!h && f.getBoundingClientRect().top < h.getBoundingClientRect().top; });
    add(fng.length === 3 && fng.filter(t => /^\d+$/.test(t)).length >= 2 && fngTop && fngOrd === 'fng_m,fng_c,fng_d', `Главная: «Страх и жадность» сверху, число в дуге (alternative.me ${fng[0] || '—'}, CoinMarketCap ${fng[1] || '—'}, DOG ${fng[2] || '—'})`, `Home: Fear & Greed on top, the number inside the gauge (alternative.me ${fng[0] || '—'}, CoinMarketCap ${fng[1] || '—'}, DOG ${fng[2] || '—'})`);
    // график на «Главном»: свечи по интервалам (15м · 1ч · 4ч · 1д · 1н) и переключатель «свечи / линия»; 1 млн DOG и капитализация
    {
      const h = await page.evaluate(() => ({ tf: document.querySelectorAll('#p-overview [data-htf]').length, md: document.querySelectorAll('#p-overview [data-hmode]').length, m1: (document.querySelector('#h1m') || {}).textContent || '', cap: (document.querySelector('#hcap2') || {}).textContent || '', rays: getComputedStyle(document.querySelector('#p-overview .hero'), '::before').display }));
      await page.evaluate(() => { const b = document.querySelector('#p-overview [data-hmode="line"]'); if (b) b.click(); });
      const line = await wait(() => document.querySelector('#p-overview [data-hmode="line"][aria-pressed="true"]') && !!document.querySelector('#pchart canvas'), 8000);
      await page.evaluate(() => { const b = document.querySelector('#p-overview [data-hmode="candles"]'); if (b) b.click(); });
      const cand = await wait(() => document.querySelector('#p-overview [data-hmode="candles"][aria-pressed="true"]') && !!document.querySelector('#pchart canvas'), 8000);
      add(h.tf === 5 && h.md === 2 && line && cand && /\d/.test(h.m1) && /\d/.test(h.cap) && h.rays === 'none', `Главная: интервалы свечей (${h.tf}), «свечи / линия» переключаются, 1 млн DOG ${h.m1.trim()}, капитализация ${h.cap.trim()}`, `Home: candle intervals (${h.tf}), candles/line toggle works, 1M DOG ${h.m1.trim()}, market cap ${h.cap.trim()}`, JSON.stringify({ line, cand, rays: h.rays }));
    }
    // первый экран: индексы, цена и весь график — значок TradingView виден над нижним меню
    {
      await page.evaluate(() => window.scrollTo(0, 0)); await page.waitForTimeout(300);
      const fit = await page.evaluate(() => {
        const ch = document.querySelector('#pchart'), lg = document.querySelector('#pchart a#tv-attr-logo'), tb = document.querySelector('#tabbar'), f = document.querySelector('#fng-box .fng');
        if (!ch || !lg || !tb) return null;
        const c = ch.getBoundingClientRect(), l = lg.getBoundingClientRect(), t = tb.getBoundingClientRect();
        return { h: Math.round(c.height), vh: innerHeight, logo: Math.round(l.bottom), tab: Math.round(t.top), fng: f ? Math.round(f.getBoundingClientRect().top) : -1 };
      });
      add(!!fit && fit.logo > 0 && fit.logo <= fit.tab && fit.h >= 0.3 * fit.vh && fit.fng >= 0, `Главная: первый экран — индексы, цена и весь график (${fit ? fit.h : '—'} px), значок TradingView над нижним меню`, `Home: the first screen shows the indices, the price and the whole chart (${fit ? fit.h : '—'} px), TradingView mark above the bottom menu`, JSON.stringify(fit));
    }
    // график на «Главной» одним пальцем: зажать и вести (наискосок) — вверху дата и цена свечи, страница стоит, карточка не прыгает;
    // отпустили — сразу живая цена; просто провести — график листается в прошлое (как тачпад), цена остаётся живой; короткое нажатие ничего не меняет
    {
      let g = null, p = null;
      const b = await page.locator('#pchart').boundingBox();
      if (b) {
        const cdp = await ctx.newCDPSession(page);
        const tch = (type, pts) => cdp.send('Input.dispatchTouchEvent', { type, touchPoints: pts.map((q, i) => ({ x: q[0], y: q[1], id: i })) });
        const h0 = await page.evaluate(() => [Math.round(scrollY), document.querySelector('.hero-head').getBoundingClientRect().height, document.querySelector('#hlabel').textContent]);
        const x0 = b.x + b.width * 0.25, y0 = b.y + b.height * 0.4, hs = [];
        await tch('touchStart', [[x0, y0]]);
        await page.waitForTimeout(380);
        for (let k = 1; k <= 10; k++) { await tch('touchMove', [[x0 + b.width * 0.04 * k, y0 + b.width * 0.034 * k]]); await page.waitForTimeout(20); hs.push(await page.evaluate(() => document.querySelector('.hero-head').getBoundingClientRect().height)); }
        g = await page.evaluate(() => ({ sy: Math.round(scrollY), lab: document.querySelector('#hlabel').textContent, when: (document.querySelector('#hwhen') || {}).textContent || '', leg: (document.querySelector('#hleg') || {}).textContent || '' }));
        await tch('touchEnd', []); await page.waitForTimeout(300);
        g.after = await page.evaluate(() => document.querySelector('#hlabel').textContent + '|' + ((document.querySelector('#hwhen') || {}).textContent || ''));
        await page.touchscreen.tap(b.x + b.width * 0.35, b.y + b.height * 0.45); await page.waitForTimeout(400);
        g.tap = await page.evaluate(() => document.querySelector('#hlabel').textContent);
        g.sy0 = h0[0]; g.lab0 = h0[2]; g.jump = Math.round(Math.max(...hs.map(h => Math.abs(h - h0[1]))) * 10) / 10;
        // просто провести вправо — в прошлое
        const w0 = await page.evaluate(() => document.querySelector('#hwhat').textContent);
        const x1 = b.x + b.width * 0.2, y1 = b.y + b.height * 0.5;
        await tch('touchStart', [[x1, y1]]);
        for (let k = 1; k <= 10; k++) { await tch('touchMove', [[x1 + b.width * 0.05 * k, y1 + (k % 2)]]); await page.waitForTimeout(16); }
        await page.waitForTimeout(120);
        await tch('touchEnd', []); await page.waitForTimeout(500);
        p = await page.evaluate(() => ({ sy: Math.round(scrollY), what: document.querySelector('#hwhat').textContent, lab: document.querySelector('#hlabel').textContent, scrub: !!document.querySelector('#p-overview .hero.scrub'), last: !!document.querySelector('#pchart > .ch-last:not([hidden])') }));
        p.w0 = w0;
        const lb = await page.$('#pchart > .ch-last:not([hidden])');
        if (lb) { await lb.tap(); await page.waitForTimeout(800); }
        p.back = await page.evaluate(() => !document.querySelector('#pchart > .ch-last:not([hidden])') && document.querySelector('#hwhat').textContent);
        await cdp.detach().catch(() => { });
      }
      await page.evaluate(() => window.scrollTo(0, 0));
      add(!!g && g.sy === g.sy0 && g.jump < 0.5 && /^(с|since) /.test(g.lab) && !!g.when && !/^DOG/.test(g.when) && /(Макс|H) \d/.test(g.leg) && g.after.split('|')[0] === g.lab0 && /^DOG/.test(g.after.split('|')[1]) && g.tap === g.lab0, 'Главная: зажать палец на графике и вести — вверху дата и цена свечи, страница стоит, карточка не прыгает; отпустили — снова живая цена', 'Home: hold a finger on the chart and slide — that candle’s date and price on top, the page stays still and the card steady; let go and the live price is back', g ? `${g.when}; ${g.lab} → ${g.after}; нажатие: ${g.tap}; прокрутка ${g.sy - g.sy0}, сдвиг ${g.jump}` : 'графика нет');
      add(!!p && p.sy === (g ? g.sy0 : 0) && p.what !== p.w0 && p.last && !p.scrub && p.lab === (g ? g.lab0 : '') && p.back === p.w0, 'Главная: провести пальцем — график листается в прошлое, страница стоит, цена живая; кнопка «»» возвращает к последней свече', 'Home: a finger slide scrolls the chart into the past, the page stays still and the price live; the “»” button returns to the latest candle', p ? `${p.w0} → ${p.what}; назад: ${p.back}` : 'графика нет');
    }
    const st = await page.evaluate(() => ({ c: document.querySelector('#status').className, t: document.querySelector('#status-t').textContent }));
    add(/\d\d:\d\d/.test(st.t), `Статус в шапке показывает время данных («${st.t.trim().slice(0, 40)}»)`, `Header status shows the data time (“${st.t.trim().slice(0, 40)}”)`);
    add(await noOverflow(), 'Главная: ничего не вылезает за экран телефона', 'Home: nothing overflows the phone screen');
    await shot('1-home');
    // «Страх и жадность»: в каждом разборе — график индекса с ценой (DOG или биткоин), не сплющен и отвечает на нажатие
    for (const [key, nm] of [['fng_m', 'alternative.me'], ['fng_c', 'CoinMarketCap'], ['fng_d', 'DOG']]) {
      await page.evaluate(k => { const b = document.querySelector(`[data-info="${k}"]`); if (b) b.click(); }, key);
      await page.waitForTimeout(800);
      const r = await page.evaluate(() => { const pl = document.querySelector('#sheet-body .fic-plot'); if (!pl) return null; pl.scrollIntoView({ block: 'center' }); const b = pl.getBoundingClientRect(); return { h: b.height, w: b.width, ps: [...pl.querySelectorAll('path')].map(p => (p.getAttribute('d') || '').length), read: (document.querySelector('#sheet-body .fic-read') || {}).textContent || '' }; });
      let ok = !!r && r.h >= 120 && r.w >= 200 && r.ps.length >= 3 && Math.min(...r.ps) > 100, after = '';
      if (ok) {
        await page.waitForTimeout(300);
        const b2 = await page.evaluate(() => { const b = document.querySelector('#sheet-body .fic-plot').getBoundingClientRect(); return { x: b.left, y: b.top, w: b.width, h: b.height }; });
        await page.touchscreen.tap(b2.x + b2.w * 0.35, b2.y + b2.h / 2);
        await page.waitForTimeout(300);
        after = await page.evaluate(() => (document.querySelector('#sheet-body .fic-read') || {}).textContent || '');
        ok = !!after && after !== r.read;
      }
      add(ok, `«Страх и жадность», ${nm}: график индекса с ценой показан и отвечает на нажатие`, `Fear & Greed, ${nm}: the index chart with prices is shown and responds to taps`, r ? `высота ${Math.round(r.h)} px; ${after.slice(0, 70)}` : 'графика нет');
      // точки разворотов: есть на графике, нажатие на точку показывает её день, цену и метку «пик» или «дно»
      if (ok) {
        const dt = await page.evaluate(() => { const d = [...document.querySelectorAll('#sheet-body .fic-t')]; const x = d[d.length - 1]; if (!x) return { n: 0 }; const r = x.getBoundingClientRect(); return { n: d.length, x: r.left + r.width / 2 + 4, y: r.top + r.height / 2 - 4, rows: document.querySelectorAll('#sheet-body [data-fturn]').length }; });
        let tk = '';
        if (dt.n) { await page.touchscreen.tap(dt.x, dt.y); await page.waitForTimeout(300); tk = await page.evaluate(() => ((document.querySelector('#sheet-body .fic-read .tk') || {}).textContent || '') + ' · ' + ((document.querySelector('#sheet-body .fic-read .p') || {}).textContent || '')); }
        add(dt.n >= 3 && dt.rows >= 3 && /пик|дно|peak|low/.test(tk), `«Страх и жадность», ${nm}: точки разворотов нажимаются (${dt.n} точек)`, `Fear & Greed, ${nm}: turning-point dots respond to taps (${dt.n} dots)`, tk.slice(0, 80));
      }
      await page.evaluate(() => { const c = document.querySelector('#sheet [data-close]'); if (c) c.click(); });
      await page.waitForTimeout(450);
    }
    // индекс DOG везде одно и то же число: шкала на «Главном», «Сейчас» в разборе и сегодняшняя точка графика
    {
      const g = await page.evaluate(() => { const x = document.querySelector('#fng-box [data-info="fng_d"] .gnum'); return x ? x.textContent.trim() : ''; });
      await page.evaluate(() => { const b = document.querySelector('[data-info="fng_d"]'); if (b) b.click(); });
      await page.waitForTimeout(800);
      const k = await page.evaluate(() => ({ now: ((document.querySelector('#sheet-body .kv dd b') || {}).textContent || '').trim(), pt: ((document.querySelector('#sheet-body .fic-read .v b') || {}).textContent || '').trim(), d: ((document.querySelector('#sheet-body .fic-read .d') || {}).textContent || '').trim() }));
      // разбор открыт 8 секунд (цена онлайн может сдвинуться) — после закрытия шкала показывает то же число, что «Сейчас»
      await page.waitForTimeout(8000);
      const now2 = await page.evaluate(() => ((document.querySelector('#sheet-body [data-fng-now="d"] b') || {}).textContent || '').trim());
      await page.evaluate(() => { const c = document.querySelector('#sheet [data-close]'); if (c) c.click(); });
      await page.waitForTimeout(450);
      const g2 = await page.evaluate(() => { const x = document.querySelector('#fng-box [data-info="fng_d"] .gnum'); return x ? x.textContent.trim() : ''; });
      add(!!g && g === k.now && g === k.pt && g2 === now2, `Индекс DOG одинаковый на шкале, в разборе и на графике (${g || '—'} / ${k.now || '—'} / ${k.pt || '—'}; после закрытия ${g2 || '—'} / ${now2 || '—'})`, `DOG index is the same on the gauge, in the breakdown and on the chart (${g || '—'} / ${k.now || '—'} / ${k.pt || '—'}; after closing ${g2 || '—'} / ${now2 || '—'})`, k.d);
    }
    // крупные заявки из «Что нового» — их потом ищем в сводном стакане
    const evs = await page.evaluate(() => [...document.querySelectorAll('#sum-box .ev')].map(e => e.textContent.replace(/\s+/g, ' ').trim()));

    // 2. стакан
    await tab('books');
    // «Что нового» и стакан говорят одно и то же: новая крупная заявка видна в сводном стакане (вид «две колонки», шаг 0.00001)
    {
      const want = evs.map(t => { const m = t.match(/(\w+): new (buy|sell) order for ([\d.,]+)([KMB]?) DOG at \$?([\d.]+)/); return m ? { t, ex: m[1], side: m[2] === 'buy' ? 'b' : 'a', q: parseFloat(m[3].replace(/,/g, '')) * ({ K: 1e3, M: 1e6, B: 1e9 }[m[4]] || 1), p: parseFloat(m[5]) } : null; }).filter(Boolean);
      if (want.length) {
        await page.evaluate(() => { const v = document.querySelector('[data-obview="two"]'); if (v) v.click(); });
        await page.waitForTimeout(500);
        await page.evaluate(() => { const st = document.querySelector('[data-obstep="0.00001"]'); if (st) st.click(); const a = document.querySelector('[data-obex="all"]'); if (a) a.click(); });
        await page.waitForTimeout(500);
        await page.evaluate(() => { const m = document.querySelector('[data-obmore="1"]'); if (m) m.click(); });
        await page.waitForTimeout(700);
        const rowsB = await page.evaluate(() => { const num = t => { const m = String(t).replace('≥', '').replace(/,/g, '').match(/([\d.]+)\s*([KMB]?)/); return m ? parseFloat(m[1]) * ({ K: 1e3, M: 1e6, B: 1e9 }[m[2]] || 1) : 0; }; const g = side => [...document.querySelectorAll(`#obcard .ob2 .h.${side}`)].map(h => ({ p: parseFloat((h.querySelector('.p') || {}).textContent || 'NaN'), q: num((h.querySelector('.q') || {}).textContent || '') })).filter(r => r.p > 0); return { b: g('b'), a: g('a') }; });
        const res = want.map(w => { const rows = rowsB[w.side]; if (!rows.length) return { w, st: 'skip' }; const bp = w.side === 'b' ? Math.floor(w.p / 1e-5 + 1e-6) * 1e-5 : Math.ceil(w.p / 1e-5 - 1e-6) * 1e-5; const lo = Math.min(...rows.map(r => r.p)), hi = Math.max(...rows.map(r => r.p)); if (bp < lo - 1e-9 || bp > hi + 1e-9) return { w, st: 'skip' }; const r = rows.find(x => Math.abs(x.p - bp) < 1e-9); return { w, st: r && r.q >= w.q * 0.9 ? 'ok' : 'miss', got: r ? r.q : 0 }; });
        const chk = res.filter(x => x.st !== 'skip'), okN = chk.filter(x => x.st === 'ok').length;
        add(!chk.length || okN > 0, `Стакан: крупные заявки из «Что нового» видны в сводном стакане (${okN} из ${chk.length})`, `Order book: large orders from “What’s new” are visible in the combined book (${okN} of ${chk.length})`, chk.filter(x => x.st === 'miss').map(x => `${x.w.ex} ${x.w.p}: ${Math.round(x.w.q / 1e5) / 10}M, в стакане ${Math.round(x.got / 1e5) / 10}M`).join('; '));
        await page.evaluate(() => { const v = document.querySelector('[data-obview="col"]'); if (v) v.click(); const m = document.querySelector('[data-obmore="0"]'); if (m) m.click(); });
        await page.waitForTimeout(400);
      }
    }
    const rows = await page.evaluate(() => document.querySelectorAll('#p-books .ob-r, #p-books [data-lv], #p-books tr').length);
    add(rows >= 10 && await noOverflow(), `Стакан: уровни цен показаны (${rows})`, `Order book: price levels are shown (${rows})`);
    // сводный стакан: все покупки ниже цены, все продажи выше (без «пересечений» между биржами)
    const ob = await page.evaluate(() => { const num = e => parseFloat(e.textContent.replace(',', '.')); const b = [...document.querySelectorAll('#obcard .ob-r.b .p, #obcard .ob2 .h.b .p')].map(num), a = [...document.querySelectorAll('#obcard .ob-r.a .p, #obcard .ob2 .h.a .p')].map(num), m = document.querySelector('#obmidp'); return { b: b.length ? Math.max(...b) : null, a: a.length ? Math.min(...a) : null, m: m ? num(m) : null }; });
    add(ob.b != null && ob.a != null && ob.m != null && ob.b <= ob.m * 1.0000001 && ob.a >= ob.m * 0.9999999 && ob.b < ob.a * 1.0000001, 'Стакан: покупки ниже цены, продажи выше', 'Order book: bids below the price, asks above', JSON.stringify(ob));
    // стакан — первым на вкладке; перевес у цены — маленькая строка, нажатие открывает разбор
    {
      const r = await page.evaluate(() => { const card = document.querySelector('#obcard'), imb = document.querySelector('#p-books [data-obimb]'); return { cardTop: card ? Math.round(card.getBoundingClientRect().top + window.scrollY) : null, imbH: imb ? Math.round(imb.getBoundingClientRect().height) : null, cells: imb ? imb.querySelectorAll('.c').length : 0 }; });
      let opened = false;
      if (r.cells) { await page.evaluate(() => document.querySelector('#p-books [data-obimb]').click()); await page.waitForTimeout(600); opened = await page.evaluate(() => !document.querySelector('#sheet').hidden && document.querySelectorAll('#sheet-body .wh-r').length >= 3); await page.evaluate(() => { const c = document.querySelector('#sheet [data-close]'); if (c) c.click(); }); await page.waitForTimeout(450); }
      add(r.cardTop != null && r.cardTop < 360 && r.cells === 4 && r.imbH <= 80 && opened, `Стакан первым экраном, перевес у цены — одна строка (${r.cells} диапазона), разбор открывается`, `Order book comes first; the balance near the price is one row (${r.cells} ranges) and opens its breakdown`, JSON.stringify(r));
    }
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
    // DOG и мем-монеты: все линии нарисованы, нажатие на линию выбирает монету, в списке у каждой монеты есть связь с DOG
    {
      await page.evaluate(() => { const e = document.querySelector('#mmplot'); if (e) e.scrollIntoView({ block: 'center' }); });
      const ok = await wait(() => document.querySelectorAll('#mmplot path').length >= 8 && document.querySelectorAll('#mmlist [data-mm]').length >= 8, 15000);
      let det = '';
      if (ok) {
        const m = await page.evaluate(() => { const b = document.querySelector('#mmplot').getBoundingClientRect(); return { b: { x: b.left, y: b.top, w: b.width, h: b.height }, sel: (document.querySelector('#mmlist [aria-pressed="true"]') || {}).dataset?.mm, n: document.querySelectorAll('#mmlist [data-mm]').length, corr: [...document.querySelectorAll('#mmlist .c')].filter(c => /\d/.test(c.textContent)).length }; });
        await page.touchscreen.tap(m.b.x + m.b.w * 0.5, m.b.y + m.b.h * 0.5); await page.waitForTimeout(300);
        const r = await page.evaluate(() => ({ read: (document.querySelector('#mmread') || {}).textContent || '', h: document.querySelector('#mmplot').getBoundingClientRect().height }));
        det = `${m.n} монет, связь у ${m.corr}; высота ${Math.round(r.h)} px; ${r.read.replace(/\s+/g, ' ').slice(0, 90)}`;
        // нажатие показывает день: вверху дата, а не «сейчас»
        add(m.corr >= m.n - 2 && r.h >= 150 && /DOG [+−]?\d/.test(r.read) && !/^\s*(now|сейчас)/i.test(r.read), 'Графики: «DOG и мем-монеты» нарисован и отвечает на нажатие', 'Charts: “DOG and meme coins” is drawn and responds to taps', det);
      } else add(false, 'Графики: «DOG и мем-монеты» нарисован и отвечает на нажатие', 'Charts: “DOG and meme coins” is drawn and responds to taps', 'линий или списка нет');
      await shot('5-charts-memes');
    }
    {
      const f = await page.evaluate(() => ({ rows: document.querySelectorAll('#fngc-sec .fngr').length, paths: [...document.querySelectorAll('#f3plot path')].filter(p => (p.getAttribute('d') || '').length > 100).length }));
      let read = '', sh = null;
      if (f.paths >= 2) {
        await page.evaluate(() => { const e = document.querySelector('#f3plot'); if (e) e.scrollIntoView({ block: 'center' }); }); await page.waitForTimeout(300);
        const b = await page.locator('#f3plot').boundingBox();
        if (b) {
          await page.touchscreen.tap(b.x + b.width * 0.3, b.y + b.height / 2); await page.waitForTimeout(900);
          sh = await page.evaluate(() => { const pl = document.querySelector('#sheet-body .f3s-plot'); if (!pl) return null; const r = pl.getBoundingClientRect(); return { x: r.left, y: r.top, w: r.width, h: r.height, paths: [...pl.querySelectorAll('path')].filter(p => (p.getAttribute('d') || '').length > 100).length, read: (document.querySelector('#sheet-body .f3s-read') || {}).textContent || '' }; });
          if (sh) {
            sh.v9 = await page.evaluate(() => {
              const c = getComputedStyle(document.documentElement).getPropertyValue('--f3c').trim(), m = c.match(/^#([0-9a-f]{6})$/i);
              let blue = false; if (m) { const v = parseInt(m[1], 16), r = v >> 16, g = (v >> 8) & 255, b = v & 255; blue = b > 180 && b > r + 60 && b > g + 30; }
              return { th: document.querySelectorAll('#sheet-body .f3s-t thead th').length, balls: document.querySelectorAll('#sheet-body .f3s-ball').length, c, blue };
            });
            await page.touchscreen.tap(sh.x + sh.w * 0.6, sh.y + sh.h / 2); await page.waitForTimeout(300);
            read = await page.evaluate(() => (document.querySelector('#sheet-body .f3s-read') || {}).textContent || '');
            // минимум в таблице: нажатие показывает этот день на графике — точка выделена, индекс выбран
            await page.evaluate(() => { const v = document.querySelector('#sheet-body .f3s-v'); if (v) v.click(); }); await page.waitForTimeout(500);
            sh.min = await page.evaluate(() => { const v = document.querySelector('#sheet-body .f3s-v'); const d = v ? (v.querySelector('span') || {}).textContent : ''; return { dot: document.querySelectorAll('#sheet-body .f3s-p.on').length, fx: /\bfx-/.test((document.querySelector('#sheet-body .f3s-g') || {}).className || ''), same: !!d && ((document.querySelector('#sheet-body .f3s-d b') || {}).textContent || '').trim() !== '' }; });
          }
          await page.evaluate(() => { const c = document.querySelector('#sheet [data-close]'); if (c) c.click(); }); await page.waitForTimeout(450);
        }
      }
      add(f.rows === 3 && f.paths >= 2 && !!sh && sh.h >= 180 && sh.paths >= 3 && /DOG\s*\d/.test(read) && !/^(Сегодня|Today)/.test(read.trim()) && !!sh.min && sh.min.dot === 1 && sh.min.fx, `Графики: «Страх и жадность» — три строки и общий график; нажатие открывает историю трёх индексов, там нажатие показывает день, а нажатие на минимум — его точку`, `Charts: Fear & Greed — three rows and a shared chart; a tap opens the history of all three, where a tap shows that day and tapping a low shows its dot`, `${f.rows} строки, ${f.paths} линии; ${sh ? `лист ${Math.round(sh.h)} px, ${sh.paths} линии; ` : 'листа нет; '}${read.replace(/\s+/g, ' ').slice(0, 60)}`);
      { const v = sh && sh.v9; add(!!v && v.th === 4 && v.balls === 3 && v.blue, '«Страх и жадность — история»: CoinMarketCap — синий, числа индексов — в шариках цвета линии, колонки «В среднем» нет', 'Fear & Greed history: CoinMarketCap in blue, index numbers in balls of their line colour, no “Average” column', JSON.stringify(v || null)); }
    }
    // карта ликвидности: заявки бирж (покупки ниже цены, продажи выше), линия цены, сводка словами; нажатие на строку — её цифры
    {
      await wait(() => !!document.querySelector('#lqbox svg'), 15000);
      const lq = await page.evaluate(() => {
        const b = document.querySelector('#lqbox'); if (!b) return null;
        return { bid: b.querySelectorAll('.lq-b').length, ask: b.querySelectorAll('.lq-a').length, now: !!b.querySelector('.lq-now'), sum: (document.querySelector('#lqsum') || {}).textContent || '', rows: b.querySelectorAll('[data-lqi]').length };
      });
      let info = '';
      if (lq && lq.rows) {
        const row = page.locator('#lqbox [data-lqi]').nth(Math.floor(lq.rows * 0.7));
        await row.scrollIntoViewIfNeeded().catch(() => { }); await page.waitForTimeout(200);
        const r = await row.boundingBox();
        if (r) { await page.touchscreen.tap(r.x + 40, r.y + r.height / 2); await page.waitForTimeout(300); info = await page.evaluate(() => (document.querySelector('#lqinfo') || {}).textContent || ''); }
      }
      add(!!lq && lq.bid > 3 && lq.ask > 3 && lq.now && /buy wall/i.test(lq.sum) && /\$0\.\d/.test(info), 'Графики: карта ликвидности — крупные заявки на покупку и продажу, цена, средняя цена держателей; нажатие на строку показывает её цифры', 'Charts: liquidity map — big buy and sell orders, the price, holders’ average cost; tapping a row shows its numbers', lq ? `покупки ${lq.bid}, продажи ${lq.ask}; ${info.slice(0, 60)}` : 'карты нет');
    }
    add(await page.evaluate(() => !document.querySelector('#p-charts .tv-wait')), 'Графики: ничего не «зависло» на загрузке', 'Charts: nothing is stuck loading');
    add(await noOverflow(), 'Графики: ничего не вылезает за экран телефона', 'Charts: nothing overflows the phone screen');

    // 4. кошельки
    await tab('wallets');
    const w = await page.evaluate(() => ({ rows: document.querySelectorAll('#wlist .wrow').length, hk: (document.querySelector('#p-wallets .hk') || {}).textContent || '', ring: !!document.querySelector('#tiers-sec .tring svg circle[data-tier]'), warn: !!document.querySelector('#p-wallets .tag.warn') }));
    add(w.rows >= 25 && w.ring, `Кошельки: топ-100 и кольцо «У кого сколько DOG» показаны (${w.rows} строк)`, `Wallets: top 100 and the “Who holds how much” ring are shown (${w.rows} rows)`);
    // четыре плитки вверху — каждая открывает свой разбор
    {
      const res = [];
      for (const k of ['holders', 'top', 'whales', 'exch']) {
        const ok = await page.evaluate(k2 => { const b = document.querySelector(`#p-wallets .tiles [data-info="${k2}"]`); if (!b) return false; b.click(); return true; }, k);
        await page.waitForTimeout(500);
        const r = ok ? await page.evaluate(() => ({ open: !document.querySelector('#sheet').hidden, t: (document.querySelector('#sheet-title') || {}).textContent || '', n: ((document.querySelector('#sheet-body') || {}).textContent || '').length })) : { open: false, n: 0 };
        res.push(r.open && r.n > 200 ? 1 : 0);
        await page.evaluate(() => { const c = document.querySelector('#sheet [data-close]'); if (c) c.click(); });
        await page.waitForTimeout(400);
      }
      add(res.every(Boolean), `Кошельки: плитки открывают разборы (${res.filter(Boolean).length} из 4)`, `Wallets: tiles open their breakdowns (${res.filter(Boolean).length} of 4)`);
    }
    add(/\d[\d.,]*%/.test(w.hk), 'Кошельки: «как держат DOG» — доля в прибыли, в убытке и без движения больше года', 'Wallets: “how DOG is held” — share in profit, at a loss and unmoved for over a year');
    // кошельки от 10 млн: блок есть, число кошельков совпадает со ступенью «от 10 млн» в «У кого сколько DOG» (±3: списки сняты в разное время)
    {
      await page.evaluate(() => { const b = document.querySelector('#tiers-sec [data-tmode="size"]'); if (b) b.click(); });
      await page.waitForTimeout(300);
      const wh = await page.evaluate(() => {
        const num = t => +String(t || '').replace(/[^\d]/g, '');
        const big = num((document.querySelector('#whale-sec .wh-top b') || {}).textContent);
        const tiers = [...document.querySelectorAll('#tiers-sec .tlist button')].map(b => ({ name: (b.children[1] || {}).textContent || '', w: num((b.querySelector('.w') || {}).textContent) }));
        const k5 = tiers.findIndex(t => /5–10|5-10/.test(t.name)), t10 = k5 > 0 ? tiers.slice(0, k5).reduce((a, t) => a + t.w, 0) : 0;   // ступени выше «5–10 млн»
        return { big, t10, txt: ((document.querySelector('#whale-sec .wh-top') || {}).textContent || '').replace(/\s+/g, ' ').slice(0, 100) };
      });
      add(wh.big > 100 && (!wh.t10 || Math.abs(wh.big - wh.t10) <= 3), `Кошельки: «Кошельки от 10 млн DOG» — ${wh.big || '—'} (в «У кого сколько DOG» — ${wh.t10 || '—'})`, `Wallets: “Wallets with 10M+ DOG” — ${wh.big || '—'} (“Who holds how much” — ${wh.t10 || '—'})`, wh.txt);
    }
    add(await noOverflow(), 'Кошельки: ничего не вылезает за экран телефона', 'Wallets: nothing overflows the phone screen');
    await shot('6-wallets');
    await page.evaluate(() => { const e = document.querySelector('#p-wallets .hk'); if (e) e.scrollIntoView({ block: 'start' }); window.scrollBy(0, -90); });
    await page.waitForTimeout(300);
    await shot('7-wallets-held');

    // 5. новости, история
    add(await page.evaluate(() => !document.querySelector('#tabbar [data-tab="news"]')), 'Вкладки «Новости» нет (убрана)', 'No “News” tab (removed)');
    {
      const tb = await page.evaluate(() => { const bs = [...document.querySelectorAll('#tabbar button[data-tab]')]; const cur = (document.querySelector('#tabbar [aria-selected="true"]') || {}).dataset; return { cur: cur && cur.tab, b: bs.map(b => { const r = b.getBoundingClientRect(); return [b.dataset.tab, r.left + r.width / 2, r.top + r.height / 2]; }) }; });
      let after = '';
      if (tb.b.length >= 4) {
        const from = tb.b.find(x => x[0] === tb.cur) || tb.b[0], to = tb.b.find(x => x[0] !== tb.cur && x !== from && Math.abs(x[1] - from[1]) > 120) || tb.b[tb.b.length - 1];
        await page.evaluate(([x, y]) => { const t = document.elementFromPoint(x, y); t.dispatchEvent(new PointerEvent('pointerdown', { bubbles: true, pointerId: 31, pointerType: 'touch', isPrimary: true, clientX: x, clientY: y })); }, [from[1], from[2]]);
        for (let k = 1; k <= 8; k++) await page.evaluate(([x, y]) => document.querySelector('#tabbar').dispatchEvent(new PointerEvent('pointermove', { bubbles: true, pointerId: 31, pointerType: 'touch', isPrimary: true, clientX: x, clientY: y })), [from[1] + (to[1] - from[1]) * k / 8, from[2]]);
        await page.evaluate(([x, y]) => document.querySelector('#tabbar').dispatchEvent(new PointerEvent('pointerup', { bubbles: true, pointerId: 31, pointerType: 'touch', isPrimary: true, clientX: x, clientY: y })), [to[1], to[2]]);
        await page.waitForTimeout(700);
        after = await page.evaluate(() => (document.querySelector('#tabbar [aria-selected="true"]') || {}).dataset.tab || '');
        add(after === to[0] && !!(await page.evaluate(() => document.querySelector('#tabbar .tb-ind'))), 'Нижнее меню: зажать и провести пальцем — открывается раздел под пальцем', 'Bottom menu: press and slide — the section under the finger opens', `${tb.cur} → ${after}`);
        await tab(tb.cur || 'overview');
      }
    }
    await page.evaluate(() => { const b = document.querySelector('[data-tab="history"]'); if (b) b.click(); });
    await page.waitForTimeout(600);
    add(await page.evaluate(() => document.querySelectorAll('#p-history tbody tr').length >= 3), 'История: список обновлений показан', 'History: the list of updates is shown');

    // 6. iPad и компьютер: меню слева (на iPad — значки с подписями, на компьютере — полное), нижнего меню нет; ничего не вылезает за экран
    for (const [vw, vh, nm, en] of [[820, 1180, 'iPad', 'iPad'], [1440, 900, 'компьютер', 'computer']]) {
      await page.setViewportSize({ width: vw, height: vh });
      await page.waitForTimeout(500);
      const bad = [];
      for (const k of ['overview', 'books', 'charts', 'wallets']) {
        await page.evaluate(k2 => { const b = document.querySelector(`[data-tab="${k2}"]`); if (b) b.click(); }, k);
        await page.waitForTimeout(900);
        const r = await page.evaluate(() => { const rl = document.querySelector('.rail'), b = rl && rl.getBoundingClientRect(); return { ov: document.scrollingElement.scrollWidth > window.innerWidth + 1, rail: !!rl && getComputedStyle(rl).display !== 'none' && b.left <= 1 && b.width >= 60, bar: getComputedStyle(document.querySelector('#tabbar')).display !== 'none', sel: !!document.querySelector('.rail [data-tab][aria-selected="true"]') }; });
        if (r.ov) bad.push(k + ': ' + (en === 'iPad' ? 'вылезает' : 'overflow'));
        if (!r.rail || r.bar || !r.sel) bad.push(k + ': меню');
      }
      add(!bad.length, `${nm}: все вкладки помещаются, меню на месте`, `${en}: every tab fits, navigation in place`, bad.join('; '));
      if (SHOTS) { await page.evaluate(() => { const b = document.querySelector('[data-tab="overview"]'); if (b) b.click(); }); await page.waitForTimeout(800); await shot('9-' + en.toLowerCase()); }
    }
    await page.setViewportSize({ width: 390, height: 844 });

    // 6. только английский: и старая ссылка ?lang=ru открывает английскую версию, кириллицы на странице нет
    await page.goto(base + '?nosw=1&lang=ru#overview', { waitUntil: 'load', timeout: 45000 });
    const enOnly = await wait(() => !!document.querySelector('#hprice') && /\d/.test(document.querySelector('#hprice').textContent) && !/[А-Яа-яЁё]/.test(document.body.innerText) && !/[?&]lang=/.test(location.search) && !document.querySelector('[data-lang]'), 25000);
    add(enOnly, 'Сайт только на английском: старая ссылка ?lang=ru открывает английскую версию', 'English only: the old ?lang=ru link opens the English site');
    await shot('8-home-lang');

    // 7. вся история дневных свечей: data/prices.json (с 25.04.2024) стоит перед свечами Kraken — и на «Главной», и на «Графиках»
    await page.goto(base + '?nosw=1&debug=1#overview', { waitUntil: 'load', timeout: 45000 });
    await wait(() => !!document.querySelector('#pchart canvas'), 25000);
    await page.evaluate(() => { const b = document.querySelector('[data-htf="1d"]'); if (b) b.click(); });
    const deep = await wait(() => { try { const HC = window.__dm.hc(); return HC && HC.tf === '1d' && HC.rows.length > 800 && HC.rows[0][0] < Date.UTC(2024, 4, 1) / 1000; } catch (e) { return false; } }, 20000);
    const dh = await page.evaluate(() => { try { const HC = window.__dm.hc(); return HC.rows.length + ' свечей с ' + new Date(HC.rows[0][0] * 1000).toISOString().slice(0, 10); } catch (e) { return '—'; } });
    add(deep, 'Главная: дневные свечи — вся история DOG с апреля 2024, листается пальцем', 'Home: daily candles cover all of DOG’s history since April 2024', dh);
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
