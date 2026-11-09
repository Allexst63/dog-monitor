// Temporary: are the squeezed charts a real problem or a full-page screenshot artifact in Chromium 130?
const { chromium } = require('playwright');
const fs = require('fs');
const OUT = 'probe/out5';
fs.mkdirSync(OUT, { recursive: true });
const SITE = 'https://allexst63.github.io/dog-monitor/';
const log = [];
const L = (...a) => { const s = a.map(x => typeof x === 'string' ? x : JSON.stringify(x)).join(' '); log.push(s); console.log(s); };
const metrics = p => p.evaluate(() => [...document.querySelectorAll('.tvchart')].map(el => { const c = el.querySelector('.tv-lightweight-charts'); return el.id + ' ' + (c ? c.style.width : '-') + ' canv ' + (c ? [...c.querySelectorAll('canvas')].slice(0, 3).map(cv => cv.width + '/' + cv.style.width).join(',') : '-'); }));
(async () => {
  const b = await chromium.launch();
  for (const [name, opts] of [['phone2', { viewport: { width: 390, height: 844 }, deviceScaleFactor: 2, isMobile: true, hasTouch: true }], ['desk1', { viewport: { width: 1360, height: 900 }, deviceScaleFactor: 1 }]]) {
    const ctx = await b.newContext(Object.assign({ locale: 'en-US', timezoneId: 'Asia/Dubai' }, opts));
    const p = await ctx.newPage();
    await p.goto(SITE + '?nosw=1#charts', { waitUntil: 'load', timeout: 60000 });
    await p.waitForTimeout(18000);
    L(name, 'before', await metrics(p));
    await p.screenshot({ path: `${OUT}/${name}_view.png` });
    await p.evaluate(() => { const el = document.querySelector('#dlchart'); if (el) el.scrollIntoView({ block: 'center' }); });
    await p.waitForTimeout(1500);
    await p.screenshot({ path: `${OUT}/${name}_view_delta.png` });
    L(name, 'after view shots', await metrics(p));
    await p.evaluate(() => window.scrollTo(0, 0));
    await p.waitForTimeout(800);
    await p.screenshot({ path: `${OUT}/${name}_full.png`, fullPage: true });
    L(name, 'after full shot', await metrics(p));
    await p.waitForTimeout(1500);
    await p.screenshot({ path: `${OUT}/${name}_view_after_full.png` });
    await ctx.close();
  }
  await b.close();
  fs.writeFileSync(OUT + '/log.txt', log.join('\n'));
})().catch(e => { fs.writeFileSync(OUT + '/err.txt', String(e && e.stack || e)); });
