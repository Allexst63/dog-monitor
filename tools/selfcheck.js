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
    await page.goto(base + '?nosw=1&nostat=1#overview', { waitUntil: 'load', timeout: 45000 });
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
    // «DOG и мем-монеты» на «Главном»: 7D / 30D / 90D — монеты заново выстраиваются по изменению, карточки плавно едут на новые места
    {
      await page.evaluate(() => { const e = document.querySelector('#mm-box'); if (e) e.scrollIntoView({ block: 'center' }); }); await page.waitForTimeout(250);
      const r = await page.evaluate(async () => {
        const seg = document.querySelector('#hmm-p'); if (!seg) return null;
        const before = [...document.querySelectorAll('#hmm-grid .mr')].map(e => e.dataset.id).join(',');
        const b7 = seg.querySelector('[data-hmp="7"]'); if (!b7) return null;
        b7.click();
        await new Promise(x => setTimeout(x, 90));
        const moving = [...document.querySelectorAll('#hmm-grid .mr')].filter(e => e.getAnimations().length).length;
        await new Promise(x => setTimeout(x, 1300));
        const cards = [...document.querySelectorAll('#hmm-grid .mr')];
        const pct = t => parseFloat(String(t).replace('−', '-').replace('+', '').replace('%', ''));
        const vals = cards.map(e => pct(e.querySelector('.v').textContent)), ids = cards.map(e => e.dataset.id);
        const dogLast = ids.indexOf('dog') === 5;
        const sorted = vals.slice(0, dogLast ? 5 : 6).every((v, i, a) => i === 0 || a[i - 1] >= v);
        const res = { before, after: ids.join(','), n: cards.length, out: document.querySelectorAll('#hmm-grid .mr.out').length, moving, sorted, dog: ids.includes('dog'), sub: (document.querySelector('#hmm-sub') || {}).textContent || '', on: (seg.querySelector('[aria-pressed="true"]') || {}).dataset?.hmp };
        const b90 = seg.querySelector('[data-hmp="90"]'); if (b90) b90.click();
        await new Promise(x => setTimeout(x, 1200));
        return res;
      });
      add(!!r && r.n === 6 && r.out === 0 && r.dog && r.sorted && r.on === '7' && r.moving > 0 && /^DOG #\d+ of \d+$/.test(r.sub.trim()), 'Главная: «DOG и мем-монеты» — 7D / 30D / 90D; монеты выстраиваются по изменению за период, карточки плавно меняются местами', 'Home: “DOG and meme coins” — 7D / 30D / 90D; coins re-rank by the period’s change, cards glide to their new places', r ? `${r.after}; ${r.sub}; в движении ${r.moving}` : 'переключателя нет');
    }
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
    // «Страх и жадность» прямо на «Графиках»: три линии и периоды; нажатие показывает день, минимум в таблице — его точку;
    // нажатие на индекс — он один и под ним цена (DOG — у индекса DOG, биткоин — у индексов рынка), повторное — снова все три
    {
      await page.evaluate(() => { const e = document.querySelector('#f3s-in .f3s-plot'); if (e) e.scrollIntoView({ block: 'center' }); }); await page.waitForTimeout(350);
      const f = await page.evaluate(() => ({ paths: [...document.querySelectorAll('#f3s-in .f3s-plot path')].filter(p => (p.getAttribute('d') || '').length > 100).length, cards: document.querySelectorAll('#f3s-in .f3s-c').length, per: document.querySelectorAll('#f3s-in [data-f3per]').length }));
      let read = '', min = null, px = null, three = null, look = null;
      const b = await page.locator('#f3s-in .f3s-plot').boundingBox().catch(() => null);
      if (f.paths >= 3 && b) {
        await page.touchscreen.tap(b.x + b.width * 0.6, b.y + b.height / 2); await page.waitForTimeout(300);
        read = await page.evaluate(() => (document.querySelector('#f3s-in .f3s-read') || {}).textContent || '');
        await page.evaluate(() => { const v = document.querySelector('#f3s-in .f3s-v'); if (v) v.click(); }); await page.waitForTimeout(500);
        min = await page.evaluate(() => ({ dot: document.querySelectorAll('#f3s-in .f3s-p.on').length, fx: /\bfx-/.test((document.querySelector('#f3s-in .f3s-g') || {}).className || '') }));
        px = {};
        for (const k of ['d', 'm']) {
          await page.evaluate(k2 => { const c = document.querySelector(`#f3s-in [data-f3focus="${k2}"]`); if (c && c.getAttribute('aria-pressed') !== 'true') c.click(); }, k);
          await page.waitForTimeout(700);
          px[k] = await page.evaluate(k2 => { const pp = document.querySelector('#f3s-in .f3s-pp.on'), r = pp ? pp.getBoundingClientRect() : null; return { on: !!pp, h: r ? Math.round(r.height) : 0, line: !!(pp && [...pp.querySelectorAll('path')].some(p => (p.getAttribute('d') || '').length > 100)), lab: pp ? ((pp.querySelector('.f3s-pph') || {}).textContent || '') : '', pv: pp ? ((pp.querySelector('.f3s-pv') || {}).textContent || '') : '', read: (document.querySelector('#f3s-in .f3s-read') || {}).textContent || '', others: [...document.querySelectorAll('#f3s-in .f3s-p:not(.tp)')].filter(p => p.dataset.k !== k2 && getComputedStyle(p).pointerEvents !== 'none').length }; }, k);
        }
        await shot('5-charts-fng');
        await page.evaluate(() => { const c = document.querySelector('#f3s-in [data-f3focus="m"]'); if (c) c.click(); }); await page.waitForTimeout(700);
        three = await page.evaluate(() => ({ off: !document.querySelector('#f3s-in .f3s-pp.on'), fx: /\bfx-/.test((document.querySelector('#f3s-in .f3s-g') || {}).className || '') }));
        // «Old money»: alt.me — шалфей, CMC — индиго, DOG — оранжевый; карточки без кружков — крупное число и цветная полоска слева
        look = await page.evaluate(() => {
          const hue = hex => { const m = /^#([0-9a-f]{6})$/i.exec(String(hex || '').trim()); if (!m) return null; const v = parseInt(m[1], 16), r = (v >> 16) / 255, g = ((v >> 8) & 255) / 255, b = (v & 255) / 255, mx = Math.max(r, g, b), mn = Math.min(r, g, b), d = mx - mn; if (!d) return null; let h = mx === r ? ((g - b) / d) % 6 : mx === g ? (b - r) / d + 2 : (r - g) / d + 4; h *= 60; return h < 0 ? h + 360 : h; };
          const cs = getComputedStyle(document.documentElement), H = k => hue(cs.getPropertyValue(k)), hm = H('--f3m'), hc = H('--f3c'), hd = H('--f3d');
          const cards = [...document.querySelectorAll('#f3s-in .f3s-c')];
          const strip = cards.filter(c => { const st = getComputedStyle(c); return parseFloat(st.borderLeftWidth) >= 2 && st.borderLeftColor !== st.borderTopColor; }).length;
          const nums = cards.filter(c => /^\d+$/.test(((c.querySelector('.f3s-n') || {}).textContent || '').trim())).length;
          return { th: document.querySelectorAll('#f3s-in .f3s-t thead th').length, nums, strip, balls: document.querySelectorAll('.f3s-ball').length, hm: Math.round(hm), hc: Math.round(hc), hd: Math.round(hd), pal: hm >= 85 && hm <= 150 && hc >= 200 && hc <= 250 && hd >= 15 && hd <= 40 };
        });
      }
      add(f.paths >= 3 && f.cards === 3 && f.per === 4 && /DOG\s*\d/.test(read) && !/^\s*Today/.test(read) && !!min && min.dot === 1 && min.fx, 'Графики: «Страх и жадность» прямо на вкладке — три линии и периоды 30D–All; нажатие показывает день, минимум в таблице — его точку', 'Charts: Fear & Greed right on the tab — three lines and 30D–All; a tap shows that day, a low in the table shows its dot', `${f.paths} линии, ${f.cards} карточки; ${read.replace(/\s+/g, ' ').slice(0, 60)}`);
      add(!!px && !!px.d && px.d.on && px.d.line && px.d.h >= 60 && /DOG price/.test(px.d.lab) && /^\$0\.\d/.test(px.d.pv) && /DOG[^$]*\$0\.\d/.test(px.d.read) && !!px.m && px.m.on && /Bitcoin price/.test(px.m.lab) && /^\$\d{2,3},\d{3}/.test(px.m.pv) && /BTC[^$]*\$\d{2,3},\d{3}/.test(px.m.read) && px.d.others === 0 && px.m.others === 0 && !!three && three.off && !three.fx, 'Графики: нажатие на индекс — он один и под ним его цена (DOG — у индекса DOG, биткоин — у alternative.me), цена дня — прямо над графиком цены; точки других индексов не нажимаются; повторное — снова все три, без цены', 'Charts: tapping an index shows it alone with its price below (DOG for the DOG index, bitcoin for alternative.me), the day’s price right above the price chart; other indices’ dots don’t take taps; tapping again — all three, no price', px ? `${(px.d || {}).pv || '—'} | ${(px.m || {}).pv || '—'}; чужих точек: ${(px.d || {}).others}/${(px.m || {}).others}` : 'нет графика');
      add(!!look && look.th === 4 && look.nums === 3 && look.strip === 3 && look.balls === 0 && look.pal, '«Страх и жадность»: цвета «Old money» (alt.me — фисташковый, CMC — индиго, DOG — оранжевый), карточки без кружков — крупное число и цветная полоска слева', 'Fear & Greed: “Old money” colours (alt.me pistachio, CMC indigo, DOG orange), cards without balls: a large number and a coloured strip on the left', JSON.stringify(look || null));
      // «Главное» → разбор индекса DOG → «Open on Charts»: вкладка «Графики», индекс DOG один, под ним цена DOG; и лист «история трёх» с «Главного»
      await tab('overview');
      await page.evaluate(() => { const g = document.querySelector('#fng-box [data-info="fng_d"]'); if (g) g.click(); }); await page.waitForTimeout(900);
      // пик индекса DOG в листе (разворот с наибольшим значением) — запомним его день
      const sheetPeak = await page.evaluate(() => { let best = null; document.querySelectorAll('#sheet [data-fturn]').forEach(b => { const k = (b.querySelector('.k') || {}).textContent || '', m = /peak\s*(\d+)/.exec(k); if (m && (!best || +m[1] > best.v)) best = { v: +m[1], d: ((b.querySelector('.d') || {}).textContent || '').trim() }; }); return best; });
      const hasGo = await page.evaluate(() => { const b = document.querySelector('#sheet [data-f3go="d"]'); if (b) { b.click(); return true; } return false; });
      await page.waitForTimeout(1500);
      const go = await page.evaluate(() => ({ tab: [...document.querySelectorAll('#view > .panel')].filter(p => !p.hidden).map(p => p.dataset.panel).join(','), sheet: !document.querySelector('#sheet').hidden, dog: (document.querySelector('#f3s-in [data-f3focus="d"]') || {}).getAttribute?.('aria-pressed'), pane: !!document.querySelector('#f3s-in .f3s-pp.on[data-k="d"]'), vis: (() => { const e = document.querySelector('#f3s-in .f3s-plot'); if (!e) return false; const r = e.getBoundingClientRect(); return r.bottom > 60 && r.top < innerHeight; })() }));
      // тот же пик на «Графиках» за всё время: максимум DOG в таблице — тот же день, что в листе
      await page.evaluate(() => { const b = document.querySelector('#f3s-in [data-f3per="all"]'); if (b) b.click(); }); await page.waitForTimeout(600);
      go.high = await page.evaluate(() => { const b = [...document.querySelectorAll('#f3s-in .f3s-v[data-f3k="d"]')].pop(); return b ? { v: +((b.querySelector('b') || {}).textContent || 0), d: ((b.querySelector('span') || {}).textContent || '').trim() } : null; });
      go.peakSame = !!go.high && (!sheetPeak || sheetPeak.v !== go.high.v || sheetPeak.d === go.high.d);
      go.sheetPeak = sheetPeak;
      await page.evaluate(() => { const b = document.querySelector('#f3s-in [data-f3per="90"]'); if (b) b.click(); }); await page.waitForTimeout(400);
      await page.evaluate(() => { const c = document.querySelector('#f3s-in [data-f3focus="d"]'); if (c && c.getAttribute('aria-pressed') === 'true') c.click(); }); await page.waitForTimeout(500);
      await tab('overview');
      await page.evaluate(() => { const g = document.querySelector('#fng-box [data-info="fng_m"]'); if (g) g.click(); }); await page.waitForTimeout(900);
      go.alt = await page.evaluate(() => { const b = document.querySelector('#sheet [data-f3go="m"]'); return !!b && !!b.previousElementSibling && b.previousElementSibling.classList.contains('fic'); });
      await page.evaluate(() => { const c = document.querySelector('#sheet [data-close]'); if (c) c.click(); }); await page.waitForTimeout(450);
      await page.evaluate(() => { const h = document.querySelector('#fng-box [data-info="fng_all"]'); if (h) h.click(); }); await page.waitForTimeout(900);
      const shs = await page.evaluate(() => ({ paths: [...document.querySelectorAll('#f3s-sh .f3s-plot path')].filter(p => (p.getAttribute('d') || '').length > 100).length }));
      await page.evaluate(() => { const c = document.querySelector('#sheet [data-close]'); if (c) c.click(); }); await page.waitForTimeout(450);
      add(hasGo && go.tab === 'charts' && !go.sheet && go.dog === 'true' && go.pane && go.vis && go.alt && go.peakSame && shs.paths >= 3, 'Разбор индекса → «Open on Charts» (сразу под графиком у всех трёх): открываются «Графики», индекс один и под ним его цена; пик DOG — тот же день, что в листе; с «Главного» история трёх индексов открывается листом', 'Index sheet → “Open on Charts”: the Charts tab opens with that index alone and its price below; from Home the history of all three opens as a sheet', JSON.stringify(go) + `; лист: ${shs.paths} линии`);
      await tab('charts');
    }
    // карта ликвидности убрана 18.11.2026 (v13)
    add(await page.evaluate(() => !document.querySelector('#lqbox, .lqsec')), 'Графики: карты ликвидности нет (убрана)', 'Charts: no liquidity map (removed)');
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
      if (en === 'iPad') {
        // меню слева: зажать и провести пальцем — подсветка идёт за пальцем, отпустили — открывается раздел под пальцем
        await page.evaluate(() => { const b = document.querySelector('#railnav [data-tab="overview"]'); if (b) b.click(); }); await page.waitForTimeout(600);
        const rd = await page.evaluate(async () => {
          const l = document.querySelector('#railnav [role="tablist"]'), at = k => { const r = l.querySelector(`[data-tab="${k}"]`).getBoundingClientRect(); return [r.left + r.width / 2, r.top + r.height / 2]; };
          if (!l || !l.querySelector('.rn-ind')) return { ind: false };
          const a = at('overview'), b = at('wallets'), ev = (t, x, y, el) => (el || l).dispatchEvent(new PointerEvent(t, { bubbles: true, pointerId: 41, pointerType: 'touch', isPrimary: true, clientX: x, clientY: y }));
          ev('pointerdown', a[0], a[1], l.querySelector('[data-tab="overview"]'));
          const ys = [];
          for (let k = 1; k <= 8; k++) { ev('pointermove', a[0], a[1] + (b[1] - a[1]) * k / 8); ys.push(getComputedStyle(l.querySelector('.rn-ind')).translate); }
          ev('pointerup', b[0], b[1]);
          await new Promise(x => setTimeout(x, 700));
          return { ind: true, moved: new Set(ys).size >= 5, tab: (document.querySelector('#railnav [aria-selected="true"]') || {}).dataset.tab };
        });
        add(rd.ind && rd.moved && rd.tab === 'wallets', 'iPad: меню слева — зажать и провести пальцем, подсветка идёт за пальцем, открывается раздел под пальцем', 'iPad: side menu — press and slide, the highlight follows, the section under the finger opens', JSON.stringify(rd));
        await page.evaluate(() => { const b = document.querySelector('#railnav [data-tab="overview"]'); if (b) b.click(); }); await page.waitForTimeout(500);
      }
      if (SHOTS) { await page.evaluate(() => { const b = document.querySelector('[data-tab="overview"]'); if (b) b.click(); }); await page.waitForTimeout(800); await shot('9-' + en.toLowerCase()); }
    }
    await page.setViewportSize({ width: 390, height: 844 });

    // 6. только английский: и старая ссылка ?lang=ru открывает английскую версию, кириллицы на странице нет
    await page.goto(base + '?nosw=1&nostat=1&lang=ru#overview', { waitUntil: 'load', timeout: 45000 });
    const enOnly = await wait(() => !!document.querySelector('#hprice') && /\d/.test(document.querySelector('#hprice').textContent) && !/[А-Яа-яЁё]/.test(document.body.innerText) && !/[?&]lang=/.test(location.search) && !document.querySelector('[data-lang]'), 25000);
    add(enOnly, 'Сайт только на английском: старая ссылка ?lang=ru открывает английскую версию', 'English only: the old ?lang=ru link opens the English site');
    await shot('8-home-lang');

    // 7. вся история дневных свечей: data/prices.json (с 25.04.2024) стоит перед свечами Kraken — и на «Главной», и на «Графиках»
    await page.goto(base + '?nosw=1&nostat=1&debug=1#overview', { waitUntil: 'load', timeout: 45000 });
    await wait(() => !!document.querySelector('#pchart canvas'), 25000);
    await page.evaluate(() => { const b = document.querySelector('[data-htf="1d"]'); if (b) b.click(); });
    const deep = await wait(() => { try { const HC = window.__dm.hc(); return HC && HC.tf === '1d' && HC.rows.length > 800 && HC.rows[0][0] < Date.UTC(2024, 4, 1) / 1000; } catch (e) { return false; } }, 20000);
    const dh = await page.evaluate(() => { try { const HC = window.__dm.hc(); return HC.rows.length + ' свечей с ' + new Date(HC.rows[0][0] * 1000).toISOString().slice(0, 10); } catch (e) { return '—'; } });
    add(deep, 'Главная: дневные свечи — вся история DOG с апреля 2024, листается пальцем', 'Home: daily candles cover all of DOG’s history since April 2024', dh);

    // 8. цифры «барабаном» (v18): живое изменение — крутятся только изменившиеся цифры (цена на «Главном», индекс, цена в стакане);
    // палец на графике — число сразу; переключатели — фон выбранного скользит; «Big orders from» — мелкие заявки бледнеют
    {
      const r = await page.evaluate(async () => {
        const D = window.__dm, out = {}, fr = () => new Promise(x => requestAnimationFrame(() => requestAnimationFrame(x))), sl = ms => new Promise(x => setTimeout(x, ms));
        try {
          const hp = document.querySelector('#hprice'), t0 = hp.textContent, p0 = parseFloat(t0);
          D.setHero(p0 * 1.0021, -1.2, '24h', false); await fr();
          const mv = hp.querySelectorAll('dm-c.hu, dm-c.hd').length, ch = [...t0].filter((c, k) => c !== hp.textContent[k]).length;
          await sl(1100);
          const rest = [...hp.querySelectorAll('dm-c')].every((c, k) => c.getAttribute('data-c') != null || (m => m && +m[1] % 10 === +hp.textContent[k])(/\* -(\d+)\)/.exec(c.firstChild.style.transform)));
          D.setHero(p0 * 0.8, 3, 'since then', true, 'test');
          const scrub = !hp.querySelector('dm-c.hu, dm-c.hd') && [...hp.querySelectorAll('dm-s')].every(x => !x.getAnimations().length);
          D.setHero(p0, -1.2, '24h', false);
          out.hero = mv > 0 && mv === ch && rest && scrub && hp.textContent === t0;
          const S = D.S, m = S.fngM || (S.fng || {}).market;
          if (m && m.v != null) {
            const g = () => document.querySelector('#fng-box [data-info="fng_m"]'), v0 = g().querySelector('.gnum').textContent, nv = m.v >= 97 ? m.v - 3 : m.v + 3;
            S.fngM = Object.assign({}, m, { v: nv, ts: (m.ts || 0) + 1, t: Date.now() }); D.paintFng(); await fr();
            out.fng = !!g().querySelector('.gnum dm-roll') && g().querySelector('.gnum').textContent === String(nv) && g().querySelector('svg circle').getAnimations().length > 0;
            S.fngM = m; D.paintFng(); out.fngTxt = v0 + ' → ' + nv;
          } else out.fng = null;
          const pr = document.querySelector('#p-overview .periods'), th = pr && pr.querySelector(':scope > .pth'), b4 = pr && pr.querySelector('[data-htf="4h"]');
          if (th && b4) { b4.click(); await sl(80); const midX = new DOMMatrix(getComputedStyle(th).transform).m41; await sl(750); const endX = new DOMMatrix(getComputedStyle(th).transform).m41; out.slide = Math.abs(endX - b4.offsetLeft) < 1.5 && Math.abs(midX - endX) > 2 && getComputedStyle(b4).backgroundColor === 'rgba(0, 0, 0, 0)'; pr.querySelector('[data-htf="1d"]').click(); } else out.slide = false;
          const st = document.querySelector('#sum-box .stp-th');
          if (st) {
            st.dispatchEvent(new KeyboardEvent('keydown', { key: 'End', bubbles: true })); await sl(80);
            const rows = [...document.querySelectorAll('#sum-box .ev[data-q]')];
            out.stp = st.getAttribute('aria-valuetext') === '100M DOG' && rows.length > 0 && rows.every(x => x.classList.contains('dim') === (+x.dataset.q < 100));
            st.dispatchEvent(new KeyboardEvent('keydown', { key: 'Home', bubbles: true }));
            out.stp = out.stp && [...document.querySelectorAll('#sum-box .ev[data-q]')].every(x => !x.classList.contains('dim'));
          } else out.stp = document.querySelectorAll('#sum-box .ev[data-q]').length ? false : null;
        } catch (e) { out.err = String(e && e.message || e); }
        return out;
      });
      await tab('books');
      const ob = await wait(() => !!document.querySelector('#obmidp'), 15000) && await page.evaluate(async () => {
        const mp = document.querySelector('#obmidp'), real = mp.dataset.v, dg = (real.split('.')[1] || '').length;
        mp.dataset.v = (parseFloat(real) * 0.997).toFixed(dg); window.__dm.obPaint();
        await new Promise(x => requestAnimationFrame(x));
        const m2 = document.querySelector('#obmidp');
        return !!m2.querySelector('dm-roll') && m2.textContent === m2.dataset.v && m2.querySelectorAll('dm-c.hu').length > 0;
      }).catch(() => false);
      await tab('overview');
      add(r.hero && r.fng !== false && ob, `Цифры «барабаном»: цена на «Главном», индекс (${r.fngTxt || '—'}) и цена в стакане — крутятся только изменившиеся цифры; палец на графике — число сразу`, 'Rolling digits: the Home price, an index and the order book price roll only the digits that changed; finger on the chart — set at once', r.err || JSON.stringify(Object.assign({}, r, { ob })));
      add(r.slide && r.stp !== false, `Переключатели: фон выбранного скользит (свечи 15m–1w); «Big orders from» — ступенчатый ползунок${r.stp === null ? ' (в сводке нет заявок — ползунка нет)' : ', мелкие заявки бледнеют'}`, 'Switches: the selected background slides; “Big orders from” stepped slider fades smaller orders', JSON.stringify(r));
      // провести пальцем по переключателю: таблетка идёт за пальцем, отпустили — выбран вариант под пальцем (свечи и мем-монеты)
      const sw = await page.evaluate(async () => {
        const one = async (sel, from, to) => {
          const g = document.querySelector(sel); if (!g || !g.querySelector(':scope > .pth')) return sel + ': нет';
          const at = v => { const b = [...g.children].find(x => x.tagName === 'BUTTON' && x.textContent.trim() === v); const r = b.getBoundingClientRect(); return [r.left + r.width / 2, r.top + r.height / 2]; };
          g.scrollIntoView({ block: 'center' }); await new Promise(x => setTimeout(x, 150));
          const a = at(from), b = at(to), th = g.querySelector(':scope > .pth'), ev = (t, x, y, el) => (el || g).dispatchEvent(new PointerEvent(t, { bubbles: true, pointerId: 42, pointerType: 'touch', isPrimary: true, clientX: x, clientY: y }));
          const start = [...g.children].find(x => x.tagName === 'BUTTON' && x.textContent.trim() === from);
          if (start.getAttribute('aria-pressed') !== 'true') { start.click(); await new Promise(x => setTimeout(x, 700)); }
          const g2 = document.querySelector(sel), th2 = g2.querySelector(':scope > .pth'), xs = [];
          ev('pointerdown', a[0], a[1], [...g2.children].find(x => x.tagName === 'BUTTON' && x.textContent.trim() === from));
          for (let k = 1; k <= 8; k++) { ev('pointermove', a[0] + (b[0] - a[0]) * k / 8, a[1], g2); xs.push(th2.style.getPropertyValue('--tx')); }
          ev('pointerup', b[0], b[1], g2);
          await new Promise(x => setTimeout(x, 700));
          const g3 = document.querySelector(sel), p = g3.querySelector(':scope > button[aria-pressed="true"]');
          return new Set(xs).size >= 6 && p && p.textContent.trim() === to ? 'ok' : sel + ': ' + (p && p.textContent.trim()) + ' / ' + new Set(xs).size;
        };
        const out = [await one('#p-overview .periods', '1d', '1h'), await one('#hmm-p', '90D', '30D')];
        const back = [['#p-overview .periods', '1d'], ['#hmm-p', '90D']];
        for (const [s2, v] of back) { const b = [...document.querySelector(s2).children].find(x => x.tagName === 'BUTTON' && x.textContent.trim() === v); if (b) b.click(); await new Promise(x => setTimeout(x, 500)); }
        const hp = document.querySelector('#hprice').textContent, digits = (hp.replace(/^0\.0*/, '').match(/\d/g) || []).length;
        return { sw: out, price: hp, digits, story: !!document.querySelector('#sum-box .playbtn, #sum-box [data-si]') };
      });
      add(sw.sw.every(x => x === 'ok'), 'Переключатели: провести пальцем — таблетка идёт за пальцем, отпустили — выбран вариант под пальцем (свечи 1d → 1h, мем-монеты 90D → 30D)', 'Switches: slide a finger — the pill follows, the option under the finger is chosen', sw.sw.join('; '));
      add(sw.digits === 4 && !sw.story, `Главная: цена — все цифры (${sw.price}, 4 значащие), «историй» в «The last 24 hours» нет`, 'Home: the price keeps all 4 significant digits; no stories button in “The last 24 hours”', JSON.stringify(sw));
      // живая цена: середина лучших заявок Kraken и Gate по WebSocket, соединения под присмотром (в GitHub Actions — обязательно)
      {
        const ok = await wait(() => { try { const L = window.__dm.live(); return (L.k || L.g) && L.price > 0; } catch (e) { return false; } }, 25000);
        const L = await page.evaluate(() => { try { const L = window.__dm.live(); return { k: L.k, g: L.g, p: L.price, hp: document.querySelector('#hprice').textContent, badge: !document.querySelector('#hlive').hidden }; } catch (e) { return {}; } });
        const must = !!process.env.GITHUB_ACTIONS;
        add(ok ? L.badge && Math.abs(parseFloat(L.hp) / L.p - 1) < 0.002 : !must, ok ? `Главная: живая цена — середина лучших заявок (${[L.k ? 'Kraken' : '', L.g ? 'Gate' : ''].filter(Boolean).join(' и ')} онлайн), на экране ${L.hp}` : 'Главная: живая цена — биржи отсюда недоступны (пропущено)', 'Home: the live price is the middle of the best bid and ask (Kraken and Gate online)', JSON.stringify(L));
      }
      // список «пальцем» (шаг цены в стакане), кольцо «Кто сколько держит» рисуется заново, настройка «не гасить экран»
      {
        await tab('books');
        const st = await wait(() => !!document.querySelector('[data-obstepsheet]'), 10000) && await page.evaluate(async () => {
          const sl = ms => new Promise(x => setTimeout(x, ms));
          document.querySelector('[data-obstepsheet]').click(); await sl(600);
          const l = document.querySelector('#sheet .vsw'); if (!l || !l.querySelector('.vth')) return 'нет списка';
          const rows = [...l.querySelectorAll('.stepr')], cur = rows.findIndex(b => b.getAttribute('aria-pressed') === 'true'), to = cur > 0 ? cur - 1 : cur + 1;
          const at = b => { const r = b.getBoundingClientRect(); return [r.left + r.width / 2, r.top + r.height / 2]; }, a = at(rows[cur]), z = at(rows[to]);
          const ev = (t, x, y, el) => (el || l).dispatchEvent(new PointerEvent(t, { bubbles: true, pointerId: 43, pointerType: 'touch', isPrimary: true, clientX: x, clientY: y }));
          ev('pointerdown', a[0], a[1], rows[cur]); const ys = [];
          for (let k = 1; k <= 8; k++) { ev('pointermove', a[0], a[1] + (z[1] - a[1]) * k / 8); ys.push(l.querySelector('.vth').style.getPropertyValue('--ty')); }
          ev('pointerup', z[0], z[1]); await sl(900);
          const want = rows[to].dataset.obstep, now = (window.__dm.S.bstep || 0).toString(), ok = new Set(ys).size >= 6 && document.querySelector('#sheet').hidden && Math.abs(+now - +want) < +want * 1e-6;
          if (!ok) return 'шаг ' + now + ' вместо ' + want + ' / ' + new Set(ys).size;
          document.querySelector('[data-obstepsheet]').click(); await sl(600);
          const back = [...document.querySelectorAll('#sheet .stepr')][cur]; if (back) back.click(); await sl(900);
          return 'ok';
        });
        await tab('wallets');
        const rg = await wait(() => !!document.querySelector('#tiers-sec .seg'), 10000) && await page.evaluate(async () => {
          const sec = document.querySelector('#tiers-sec'); sec.scrollIntoView({ block: 'center' }); await new Promise(x => setTimeout(x, 1300));
          const bs = [...sec.querySelectorAll('.seg > button')], cur = bs.findIndex(b => b.getAttribute('aria-pressed') === 'true'), nx = bs[(cur + 1) % bs.length];
          nx.click(); await new Promise(x => setTimeout(x, 200));
          const s2 = document.querySelector('#tiers-sec'), arcs = [...s2.querySelectorAll('.tring circle[data-tier]')].filter(c => c.getAnimations().length).length, mid = s2.querySelector('.tring .c b').textContent;
          await new Promise(x => setTimeout(x, 1100));
          const end = document.querySelector('#tiers-sec .tring .c b').textContent;
          const back = [...document.querySelectorAll('#tiers-sec .seg > button')][cur]; if (back) back.click();
          return { arcs, mid, end, ok: arcs > 0 && parseFloat(mid) < parseFloat(end) };
        });
        await tab('overview');
        const aw = await page.evaluate(async () => {
          if (!('wakeLock' in navigator)) return { skip: true };
          const b = document.querySelector('#menu'); if (b) b.click(); await new Promise(x => setTimeout(x, 600));
          const row = !!document.querySelector('#sheet [data-awake]'); const on = (document.querySelector('#sheet [data-awake][aria-pressed="true"]') || {}).textContent;
          const c = document.querySelector('#sheet [data-close].iconbtn'); if (c) c.click(); await new Promise(x => setTimeout(x, 400)); return { row, on };
        });
        add(st === 'ok' && rg && rg.ok && (aw.skip || aw.row), `Стакан: шаг цены — вести пальцем по списку; кошельки: кольцо рисуется заново, проценты досчитываются (${rg ? rg.mid + ' → ' + rg.end : '—'}); «Keep the screen on» в «More»${aw.on ? ' (на телефоне — ' + aw.on + ')' : ''}`, 'Order book step list by finger; wallets ring redraws and counts up; Keep the screen on setting', JSON.stringify({ st, rg, aw }));
      }
    }
  } catch (e) {
    add(false, 'Проверка в браузере прервалась', 'The browser check was interrupted', e && e.message);
  }
  // история цен и индексов — как у источников: закрытия DOG — как у Kraken, alternative.me — как в его API, биткоин — как у Coinbase.
  // Сверяет сама страница, как у читателя; источник не ответил — пункт помечается «пропущено» (сверка в следующий раз).
  {
    const v = await page.evaluate(async () => {
      const get = async (u, ms) => { const c = new AbortController(), t = setTimeout(() => c.abort(), ms || 15000); try { const r = await fetch(u, { signal: c.signal, cache: 'no-store' }); return r.ok ? await r.json() : null; } catch (e) { return null; } finally { clearTimeout(t); } };
      const [P, B, F] = await Promise.all([get('data/prices.json'), get('data/btc.json'), get('data/fng.json')]);
      const today = new Date().toISOString().slice(0, 10), day = sec => new Date(sec * 1000).toISOString().slice(0, 10), out = {};
      const K = await get('https://api.kraken.com/0/public/OHLC?pair=DOGUSD&interval=1440');
      const kr = K && K.result && Object.values(K.result).find(Array.isArray);
      if (kr && P && P.d) {
        let n = 0, same = 0, worst = 0, wd = '';
        for (const r of kr) { const d = day(+r[0]); if (d >= today || (P.kraken_from && d < P.kraken_from) || !P.d[d]) continue; n++; const dv = Math.abs(P.d[d][3] / +r[4] - 1); if (dv <= 0.001) same++; if (dv > worst) { worst = dv; wd = d; } }
        out.k = { n, same, worst, wd };
      }
      // до 27.06.2025 закрытия в prices.json — с Gate (DOG/USDT): [время, объём в USDT, закрытие, максимум, минимум, открытие, …]
      const G = await get('https://api.gateio.ws/api/v4/spot/candlesticks?currency_pair=DOG_USDT&interval=1d&limit=1000');
      if (Array.isArray(G) && P && P.d && P.kraken_from) {
        let n = 0, same = 0, worst = 0, wd = '';
        for (const r of G) { const d = day(+r[0]); if (d >= P.kraken_from || !P.d[d] || (P.s && P.s[d] && P.s[d] !== 'g')) continue; n++; const dv = Math.abs(P.d[d][3] / +r[2] - 1); if (dv <= 0.001) same++; if (dv > worst) { worst = dv; wd = d; } }
        out.g = { n, same, worst, wd };
      }
      const A = await get('https://api.alternative.me/fng/?limit=0');
      if (A && Array.isArray(A.data) && F && F.market && F.market.hist) {
        const m = new Map(F.market.hist); let n = 0, same = 0; const bad = [];
        for (const x of A.data) { const d = day(+x.timestamp); if (d >= today || !m.has(d)) continue; n++; if (+x.value === m.get(d)) same++; else if (bad.length < 3) bad.push(`${d} ${m.get(d)}/${x.value}`); }
        out.a = { n, same, bad };
      }
      const C = await get('https://api.exchange.coinbase.com/products/BTC-USD/candles?granularity=86400');
      if (Array.isArray(C) && B && B.d) {
        let n = 0, same = 0, worst = 0;
        for (const r of C) { const d = day(+r[0]); if (d >= today || !(B.d[d] > 0)) continue; n++; const dv = Math.abs(B.d[d] / +r[4] - 1); if (dv <= 0.001) same++; if (dv > worst) worst = dv; }
        out.c = { n, same, worst };
      }
      return out;
    }).catch(() => ({}));
    const pc = x => (x * 100).toFixed(2).replace('.', ',') + '%';
    if (v.k) add(v.k.n >= 30 && v.k.same === v.k.n, `Цены DOG в истории как у Kraken: ${v.k.same} из ${v.k.n} дней (наибольшее расхождение ${pc(v.k.worst)})`, `DOG prices in the history match Kraken: ${v.k.same} of ${v.k.n} days (largest gap ${(v.k.worst * 100).toFixed(2)}%)`, v.k.wd);
    else add(true, 'Цены DOG: сверка с Kraken пропущена — Kraken не ответил', 'DOG prices: the Kraken comparison was skipped — Kraken did not answer');
    if (v.g) add(v.g.n >= 30 && v.g.same === v.g.n, `Цены DOG до 27.06.2025 как у Gate: ${v.g.same} из ${v.g.n} дней (наибольшее расхождение ${pc(v.g.worst)})`, `DOG prices before 27 Jun 2025 match Gate: ${v.g.same} of ${v.g.n} days (largest gap ${(v.g.worst * 100).toFixed(2)}%)`, v.g.wd);
    else add(true, 'Цены DOG до 27.06.2025: сверка с Gate пропущена — Gate не ответил', 'DOG prices before 27 Jun 2025: the Gate comparison was skipped — Gate did not answer');
    if (v.a) add(v.a.n >= 300 && v.a.same === v.a.n, `alternative.me: история индекса как у источника — ${v.a.same} из ${v.a.n} дней`, `alternative.me: the index history matches the source — ${v.a.same} of ${v.a.n} days`, v.a.bad.join('; '));
    else add(true, 'alternative.me: сверка пропущена — источник не ответил', 'alternative.me: comparison skipped — the source did not answer');
    if (v.c) add(v.c.n >= 30 && v.c.same === v.c.n, `Цены биткоина в истории как у Coinbase: ${v.c.same} из ${v.c.n} дней`, `Bitcoin prices in the history match Coinbase: ${v.c.same} of ${v.c.n} days`, pc(v.c.worst));
    else add(true, 'Биткоин: сверка с Coinbase пропущена — Coinbase не ответил', 'Bitcoin: the Coinbase comparison was skipped — Coinbase did not answer');
  }
  add(!errs.length, 'Страница работает без ошибок скрипта', 'The page runs without script errors', errs.slice(0, 2).join(' | '));
  await browser.close();
  if (srv) srv.close();

  // индекс DOG: формулы на странице нет — сегодняшнее число страница берёт с кривой сервера «цена → индекс»; в цене расчёта кривая
  // даёт ровно число сервера; у одинаковых (округлённых) значений пик — день с наибольшим точным значением, и разворот сервера — тот же день
  try {
    const html = fs.readFileSync(path.join(SITE, 'index.html'), 'utf8');
    const J = f => JSON.parse(fs.readFileSync(path.join(SITE, 'data', f), 'utf8'));
    const F = J('fng.json'), px = J('prices.json').d, d = F.dog || {}, H = d.hist || [];
    const noFormula = !/Math\.tanh|thF\(|FNG_W\b/.test(html);
    const C = d.now || {}, pts = C.pts || [], base = px[C.day] ? px[C.day][3] : null;
    const at = base ? pts.find(q => Math.abs(q[0] / base - 1) < 1e-5) : null, last = H.find(x => x[0] === C.day);
    const curveOk = pts.length > 50 && !!at && !!last && Math.abs(at[1] - (last.length > 2 ? last[2] : last[1])) < 0.05;
    const exv = x => x.length > 2 ? x[2] : x[1];
    let hi = null, lo = null;
    for (const x of H) { if (!hi || x[1] > hi[1] || (x[1] === hi[1] && exv(x) >= exv(hi))) hi = x; if (!lo || x[1] < lo[1] || (x[1] === lo[1] && exv(x) <= exv(lo))) lo = x; }
    const T = d.turns || [], twin = T.filter(t => (t[2] === 'p' && hi && t[1] === hi[1] && t[0] !== hi[0]) || (t[2] === 't' && lo && t[1] === lo[1] && t[0] !== lo[0]));
    const tp = T.filter(t => px[t[0]] && Math.abs(px[t[0]][3] - t[3]) < 1e-12).length;
    add(noFormula && curveOk && !twin.length && tp === T.length, `Индекс DOG: формулы на странице нет, сегодняшнее число — с кривой сервера (в цене расчёта ${at ? at[1] : '—'}); пик ${hi ? hi[1] + ' — ' + hi[0] : '—'} и дно ${lo ? lo[1] + ' — ' + lo[0] : '—'} — те же дни, что у разворотов; цена у разворотов — закрытие дня (${tp} из ${T.length})`, `DOG index: no formula in the page, today’s number comes off the server’s curve (${at ? at[1] : '—'} at the calculation price); the high ${hi ? hi[1] + ' — ' + hi[0] : '—'} and the low ${lo ? lo[1] + ' — ' + lo[0] : '—'} are the same days as the turns; turn prices are day closes (${tp} of ${T.length})`, twin.map(t => t[0] + ' ' + t[1]).join('; ') || (noFormula ? '' : 'формула найдена в index.html'));
  } catch (e) { add(false, 'Индекс DOG: проверка кривой и разворотов не удалась', 'DOG index: checking the curve and the turns failed', e.message); }

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
