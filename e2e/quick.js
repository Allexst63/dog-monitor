const fs = require('fs');
const { chromium } = require('playwright');
const SITE = 'https://allexst63.github.io/dog-monitor/';
(async () => {
  const b = await chromium.launch(); const out = {};
  for (const [name, vp, phone] of [['desk', { width: 1440, height: 900 }, false], ['phone', { width: 390, height: 844 }, true]]) {
    const ctx = await b.newContext({ viewport: vp, deviceScaleFactor: phone ? 2 : 1, isMobile: phone, hasTouch: phone, timezoneId: 'Europe/Paris' });
    const pg = await ctx.newPage(); const errs = [];
    pg.on('pageerror', e => errs.push(e.message)); pg.on('console', m => { if (m.type() === 'error') errs.push(m.text().slice(0, 160)); });
    await pg.goto(SITE + '?v=' + Date.now());
    try { await pg.waitForFunction(() => /Live/.test(document.querySelector('#status-t').textContent), null, { timeout: 25000 }); } catch (e) { }
    await new Promise(r => setTimeout(r, 2500));
    const w = await pg.evaluate(() => { const i = document.querySelector('.bf-h.b i'), ax = document.querySelector('.tre-axis'), r = document.querySelector('.bf-row'); return { row: r && Math.round(r.getBoundingClientRect().width), bar: i && Math.round(i.getBoundingClientRect().width), axis: ax && Math.round(ax.getBoundingClientRect().width), ua: navigator.userAgent.match(/Chrome\/[\d.]+/)[0] }; });
    await pg.screenshot({ path: `e2e/q_${name}.png` });
    out[name] = { status: await pg.textContent('#status'), w, errs };
    await ctx.close();
  }
  await b.close(); fs.writeFileSync('e2e/result.json', JSON.stringify(out, null, 1));
})().catch(e => { fs.writeFileSync('e2e/result.json', JSON.stringify({ fatal: String(e) })); });
