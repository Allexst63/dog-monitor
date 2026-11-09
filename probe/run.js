// Temporary check of the live site after the Charts / MEXC+BingX update: real data from a real browser on the site's origin
const { chromium, devices } = require('playwright');
const fs = require('fs');
const OUT = 'probe/out3';
fs.mkdirSync(OUT, { recursive: true });
const SITE = 'https://allexst63.github.io/dog-monitor/';
const log = [];
const L = (...a) => { const s = a.map(x => typeof x === 'string' ? x : JSON.stringify(x)).join(' '); log.push(s); console.log(s); };
(async () => {
  // wait until the new version is deployed
  for (let i = 0; i < 40; i++) {
    try { const r = await fetch(SITE + 'index.html?cb=' + Date.now()); const t = await r.text(); if (t.includes('wbs-api.mexc.com')) { L('deployed after', i * 15, 's'); break; } } catch (e) { }
    await new Promise(r => setTimeout(r, 15000));
  }
  const b = await chromium.launch();
  const mk = async (opts) => { const ctx = await b.newContext(opts); const p = await ctx.newPage(); const errs = []; p.on('console', m => { if (m.type() === 'error') errs.push(m.text().slice(0, 200)); }); p.on('pageerror', e => errs.push('PAGEERROR ' + e.message)); return { ctx, p, errs }; };
  const phone = { viewport: { width: 390, height: 844 }, deviceScaleFactor: 2, isMobile: true, hasTouch: true, locale: 'en-US', timezoneId: 'Asia/Dubai' };
  const txt = (p, sel) => p.evaluate(s => [...document.querySelectorAll(s)].map(x => x.innerText.replace(/\s+/g, ' ').trim()).join(' | '), sel).catch(e => 'ERR ' + e.message);
  // 1. Charts
  {
    const { ctx, p, errs } = await mk(phone);
    await p.goto(SITE + '?nosw=1#charts', { waitUntil: 'load', timeout: 60000 });
    await p.waitForTimeout(25000);
    L('charts.wait', await txt(p, '.tv-wait'));
    L('charts.legend', await txt(p, '#tvleg'));
    L('charts.read', await txt(p, '#tvread'));
    L('charts.delta', await txt(p, '#dlsum'));
    L('charts.corr', await txt(p, '#crstats'));
    L('charts.corrread', await txt(p, '#crread'));
    await p.screenshot({ path: OUT + '/charts_phone.png', fullPage: true });
    for (const tf of ['15m', '4h', '1d']) { await p.click(`#ch-tf [data-chtf="${tf}"]`).catch(() => { }); await p.waitForTimeout(4000); L('charts.' + tf, await txt(p, '#tvleg .l1')); }
    await p.click('#dl-win [data-dlwin="3d"]').catch(() => { }); await p.waitForTimeout(12000); L('charts.delta3d', await txt(p, '#dlsum .dl-big'));
    L('charts.errors', errs);
    await ctx.close();
  }
  // 2. Order book: all exchanges, then MEXC and BingX alone
  {
    const { ctx, p, errs } = await mk(phone);
    await p.addInitScript(() => { try { localStorage.setItem('dogmon.bx', JSON.stringify('all')); } catch (e) { } });
    await p.goto(SITE + '?nosw=1#books', { waitUntil: 'load', timeout: 60000 });
    await p.waitForTimeout(35000);
    L('books.chips', await txt(p, '#obx [data-obex]'));
    L('books.status', await txt(p, '#obcard .obst'));
    L('books.note', await txt(p, '#obcard .obnote'));
    L('books.trades', await txt(p, '#obtr .note'));
    L('books.tradeEx', await p.evaluate(() => [...document.querySelectorAll('#obtr .trl-r:not(.hd) span:last-child')].map(x => x.innerText).join(',')).catch(() => ''));
    L('books.feed', await txt(p, '#obfeed'));
    await p.screenshot({ path: OUT + '/books_all.png' });
    for (const k of ['mexc', 'bingx']) {
      await p.click(`#obx [data-obex="${k}"]`).catch(() => { }); await p.waitForTimeout(3000);
      L('books.' + k, await txt(p, '#obcard .obst'), '||', await txt(p, '#obcard .obnote'));
      await p.locator('#obcard').screenshot({ path: OUT + `/books_${k}.png` }).catch(() => { });
    }
    L('books.errors', errs);
    await ctx.close();
  }
  // 3. Wallets header, Russian
  {
    const { ctx, p, errs } = await mk(Object.assign({}, phone, { locale: 'ru-RU' }));
    await p.goto(SITE + '?nosw=1&lang=ru#wallets', { waitUntil: 'load', timeout: 60000 });
    await p.waitForTimeout(15000);
    L('wallets.heads', await txt(p, '#p-wallets .sec-head'));
    await p.screenshot({ path: OUT + '/wallets_ru.png' });
    L('wallets.errors', errs);
    await ctx.close();
  }
  // 4. Desktop, dark, charts
  {
    const { ctx, p, errs } = await mk({ viewport: { width: 1360, height: 900 }, deviceScaleFactor: 1, colorScheme: 'dark', locale: 'en-US', timezoneId: 'Asia/Dubai' });
    await p.goto(SITE + '?nosw=1#charts', { waitUntil: 'load', timeout: 60000 });
    await p.waitForTimeout(25000);
    await p.screenshot({ path: OUT + '/charts_desktop_dark.png', fullPage: true });
    L('desk.errors', errs);
    await ctx.close();
  }
  await b.close();
  fs.writeFileSync(OUT + '/log.txt', log.join('\n'));
})().catch(e => { fs.writeFileSync(OUT + '/err.txt', String(e && e.stack || e)); });
