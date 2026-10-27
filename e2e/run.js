// Сквозная проверка живого сайта в настоящем Chromium: реальные API бирж и DOG DATA, реальный CORS.
const fs = require('fs');
const { chromium } = require('playwright');
const SITE = 'https://allexst63.github.io/dog-monitor/';
(async () => {
  const b = await chromium.launch();
  const out = [];
  const runs = [['phone_en', { width: 390, height: 860 }, '?debug=1'], ['phone_ru', { width: 390, height: 860 }, '?debug=1&lang=ru'], ['desk_en', { width: 1280, height: 900 }, '?debug=1']];
  for (const [name, vp, q] of runs) {
    const phone = name.startsWith('phone');
    const ctx = await b.newContext({ viewport: vp, deviceScaleFactor: phone ? 2 : 1, isMobile: phone, hasTouch: phone, locale: name.endsWith('ru') ? 'ru-RU' : 'en-GB', timezoneId: 'Europe/Paris' });
    const pg = await ctx.newPage();
    const errs = [], reqs = [];
    pg.on('pageerror', e => errs.push('pageerror ' + e.message));
    pg.on('console', m => { if (m.type() === 'error') errs.push('console ' + m.text()); });
    pg.on('requestfailed', r => errs.push('failed ' + r.url() + ' ' + ((r.failure() || {}).errorText || '')));
    pg.on('response', r => { const u = r.url(); if (!u.startsWith(SITE)) reqs.push(r.status() + ' ' + u.slice(0, 110)); });
    const t0 = Date.now();
    await pg.goto(SITE + q + '&v=' + Date.now(), { waitUntil: 'domcontentloaded' });
    let live = false;
    try { await pg.waitForFunction(() => /Live|Онлайн/.test((document.querySelector('#status-t') || {}).textContent || ''), null, { timeout: 25000 }); live = true; } catch (e) { }
    const tLive = Date.now() - t0;
    await pg.waitForTimeout(2000);
    await pg.screenshot({ path: `e2e/${name}_1home.png` });
    const status = await pg.textContent('#status');
    const bar = await pg.evaluate(() => (document.querySelector('#updbar') || {}).innerText || 'none');
    const dm = await pg.evaluate(() => { const s = window.__dm && window.__dm.S.cur; if (!s) return null; return { ts: s.ts, upd: s.upd && { n: s.upd.n, okN: s.upd.okN, kept: s.upd.kept, dur: s.upd.dur, diff: (s.upd.diff || []).map(e => e.h.replace(/<[^>]+>/g, '')) },
      checks: s.checks, price: s.price, totals: s.totals, holders: s.holders, top100pct: s.top100pct, exch: s.exch && { bal: s.exch.bal, d: s.exch.d }, flows: s.flows && { count: s.flows.count, toExch: s.flows.toExch, fromExch: s.flows.fromExch },
      books: Object.fromEntries(Object.entries(s.books || {}).map(([k, b]) => [k, { bid: b.bid, ask: b.ask, ats: b.ats, old: b.old || 0, off: b.off || 0, rows: b.rows, d10: b.d10 }])), btc: s.btc, chart: s.chart && { asof: s.chart.asof, chg: s.chart.chg } }; });
    await pg.click('#status'); await pg.waitForTimeout(900);
    await pg.screenshot({ path: `e2e/${name}_2sheet.png` });
    await pg.click('#sheet [data-upd]'); await pg.waitForTimeout(250);
    await pg.screenshot({ path: `e2e/${name}_3progress.png` });
    let again = false;
    try { await pg.waitForFunction(() => { const x = document.querySelector('#sheet [data-upd]'); return x && !x.disabled; }, null, { timeout: 30000 }); again = true; } catch (e) { }
    await pg.waitForTimeout(400);
    const sheet = await pg.evaluate(() => document.querySelector('#sheet-body').innerText);
    await pg.screenshot({ path: `e2e/${name}_4result.png` });
    await pg.evaluate(() => document.querySelector('#sheet [data-close].iconbtn').click()); await pg.waitForTimeout(500);
    if (phone) {
      await pg.click('#tabbar [data-tab="books"]'); await pg.waitForTimeout(700); await pg.screenshot({ path: `e2e/${name}_5books.png` });
      await pg.click('#menu'); await pg.waitForTimeout(600); await pg.screenshot({ path: `e2e/${name}_6menu.png` });
      const other = name.endsWith('ru') ? 'en' : 'ru';
      await pg.click(`#sheet [data-lang="${other}"]`); await pg.waitForTimeout(3500);
      out.push({ name, langAfterSwitch: await pg.evaluate(() => [document.documentElement.lang, location.search, location.hash]) });
    }
    out.push({ name, live, tLive, status, bar, again, sheet: sheet.slice(0, 4000), dm, errs, reqs: reqs.slice(0, 40) });
    await ctx.close();
  }
  await b.close();
  fs.writeFileSync('e2e/result.json', JSON.stringify(out, null, 1));
})().catch(e => { fs.writeFileSync('e2e/result.json', JSON.stringify({ fatal: String(e && e.stack || e) })); process.exit(0); });
