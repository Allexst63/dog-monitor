// Сквозная проверка живого сайта в настоящем Chromium: реальные API, CORS, автообновление, офлайн, тема, меню.
const fs = require('fs');
const { chromium } = require('playwright');
const SITE = 'https://allexst63.github.io/dog-monitor/';
const sleep = ms => new Promise(r => setTimeout(r, ms));
(async () => {
  const b = await chromium.launch();
  const out = {};
  const mk = async (name, vp, phone, ru) => {
    const ctx = await b.newContext({ viewport: vp, deviceScaleFactor: phone ? 2 : 1, isMobile: phone, hasTouch: phone, locale: ru ? 'ru-RU' : 'en-GB', timezoneId: 'Europe/Paris' });
    const pg = await ctx.newPage();
    const errs = [];
    pg.on('pageerror', e => errs.push('pageerror ' + e.message));
    pg.on('console', m => { if (m.type() === 'error') errs.push('console ' + m.text().slice(0, 200)); });
    return { ctx, pg, errs };
  };
  const live = async pg => { try { await pg.waitForFunction(() => /Live|Онлайн/.test((document.querySelector('#status-t') || {}).textContent || ''), null, { timeout: 25000 }); return true; } catch (e) { return false; } };
  const T = (pg, s) => pg.evaluate(s => { const e = document.querySelector(s); return e ? e.innerText.replace(/\s+/g, ' ').trim() : 'NO ' + s; }, s);

  // 1. телефон EN: загрузка, автообновление через 2 минуты, офлайн
  {
    const { ctx, pg, errs } = await mk('phone_en', { width: 390, height: 844 }, true, false);
    const t0 = Date.now();
    await pg.goto(SITE + '?debug=1&v=' + Date.now(), { waitUntil: 'domcontentloaded' });
    await sleep(300); await pg.screenshot({ path: 'e2e/en_0skeleton.png' });
    const ok = await live(pg), tLive = Date.now() - t0;
    await sleep(1500); await pg.screenshot({ path: 'e2e/en_1home.png' });
    const first = await pg.evaluate(() => { const c = document.querySelector('#pchart'); c.__m = 1; const s = window.__dm.S.cur; return { ts: s.upd.ts, n: s.upd.n, ok: s.upd.okN, bad: s.checks.filter(c => !c.ok).map(c => c.t) }; });
    await sleep(140000);   // автообновление каждые 2 минуты
    const second = await pg.evaluate(() => { const s = window.__dm.S.cur; return { ts: s.upd.ts, n: s.upd.n, ok: s.upd.okN, chartKept: !!document.querySelector('#pchart').__m, status: document.querySelector('#status').className, bad: s.checks.filter(c => !c.ok).map(c => c.t) }; });
    const sw = await pg.evaluate(() => navigator.serviceWorker.ready.then(r => ({ active: !!r.active, ctrl: !!navigator.serviceWorker.controller })).catch(e => String(e)));
    await pg.reload(); await live(pg); await sleep(1500);
    const ctrl2 = await pg.evaluate(() => !!navigator.serviceWorker.controller);
    await ctx.setOffline(true);
    await pg.reload(); await sleep(6000);
    const off = { status: await T(pg, '#status'), bar: await T(pg, '#updbar'), price: await T(pg, '#hprice') };
    await pg.screenshot({ path: 'e2e/en_2offline.png' });
    await ctx.setOffline(false);
    await pg.evaluate(() => window.dispatchEvent(new Event('online'))); await sleep(6000);
    const back = await T(pg, '#status');
    out.phone_en = { ok, tLive, first, second, sw, ctrl2, off, back, errs: errs.filter(e => !/ERR_INTERNET_DISCONNECTED|Failed to load resource/.test(e)).slice(0, 12) };
    await ctx.close();
  }
  // 2. телефон RU: меню, тёмная тема, после перезагрузки тема сохраняется
  {
    const { ctx, pg, errs } = await mk('phone_ru', { width: 390, height: 844 }, true, true);
    await pg.goto(SITE + '?lang=ru&v=' + Date.now()); const ok = await live(pg); await sleep(1200);
    await pg.click('#menu'); await sleep(600); await pg.screenshot({ path: 'e2e/ru_1menu.png' });
    const menu = await T(pg, '#sheet-body');
    await pg.click('#sheet [data-theme-set="dark"]'); await sleep(300);
    await pg.click('#sheet [data-close].iconbtn'); await sleep(400);
    await pg.reload(); await live(pg); await sleep(1500);
    const theme = await pg.evaluate(() => [document.documentElement.dataset.theme, getComputedStyle(document.body).backgroundColor]);
    await pg.screenshot({ path: 'e2e/ru_2dark.png' });
    await pg.click('#tabbar [data-tab="books"]'); await sleep(800); await pg.screenshot({ path: 'e2e/ru_3books_dark.png' });
    out.phone_ru = { ok, menu: menu.slice(0, 600), theme, errs: errs.slice(0, 12) };
    await ctx.close();
  }
  // 3. компьютер: настройки в меню слева, клавиша R
  {
    const { ctx, pg, errs } = await mk('desk', { width: 1440, height: 900 }, false, false);
    await pg.goto(SITE + '?v=' + Date.now()); const ok = await live(pg); await sleep(1500);
    await pg.screenshot({ path: 'e2e/desk_1home.png' });
    await pg.click('#railfoot [data-more]'); await sleep(600); await pg.screenshot({ path: 'e2e/desk_2settings.png' });
    await pg.keyboard.press('Escape'); await sleep(500);
    await pg.keyboard.press('r'); await sleep(400);
    let done = false; try { await pg.waitForFunction(() => { const x = document.querySelector('#sheet [data-upd]'); return x && !x.disabled; }, null, { timeout: 30000 }); done = true; } catch (e) { }
    await sleep(400); await pg.screenshot({ path: 'e2e/desk_3update.png' });
    out.desk = { ok, rail: await T(pg, '#railfoot'), sheet: (await T(pg, '#sheet-body')).slice(0, 500), done, errs: errs.slice(0, 12) };
    await ctx.close();
  }
  await b.close();
  fs.writeFileSync('e2e/result.json', JSON.stringify(out, null, 1));
})().catch(e => { fs.writeFileSync('e2e/result.json', JSON.stringify({ fatal: String(e && e.stack || e) })); process.exit(0); });
