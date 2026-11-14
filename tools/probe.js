// временная проверка живого сайта в настоящем браузере (ветка probe3) — в основной сайт не входит
const pw = require('playwright-core');
(async () => {
  let browser; try { browser = await pw.chromium.launch({ channel: 'chrome' }); } catch (e) { browser = await pw.chromium.launch(); }
  const ctx = await browser.newContext({ viewport: { width: 390, height: 844 }, isMobile: true, hasTouch: true, locale: 'ru-RU' });
  const page = await ctx.newPage();
  const errs = []; page.on('pageerror', e => errs.push(String(e.message)));
  const wsl = {}; page.on('websocket', ws => { const k = ws.url().replace(/^wss:\/\//, '').split('/')[0]; const o = wsl[k] = wsl[k] || { open: 0, rx: 0, closed: 0 }; o.open++; ws.on('framereceived', () => o.rx++); ws.on('close', () => o.closed++); });
  await page.goto('https://allexst63.github.io/dog-monitor/?nosw=1&lang=ru#books', { waitUntil: 'load', timeout: 60000 });
  const hasNew = await page.evaluate(() => /fng-box|obSoon/.test(document.documentElement.innerHTML));
  console.log('NEW VERSION LIVE:', hasNew);
  await page.waitForSelector('#obcard .ob-r, #obcard .ob2 .h', { timeout: 30000 });
  const snap = () => page.evaluate(() => { const num = e => parseFloat(e.textContent.replace(',', '.')); const b = [...document.querySelectorAll('#obcard .ob-r.b .p')].map(num), a = [...document.querySelectorAll('#obcard .ob-r.a .p')].map(num);
    return { mid: (document.querySelector('.ob-mid') || {}).innerText.replace(/\n/g, ' | '), maxBid: Math.max(...b), minAsk: Math.min(...a), chips: [...document.querySelectorAll('#obx .chip')].map(c => c.innerText.replace(/\n/g, '/')).join(', '), note: (document.querySelector('.obnote') || {}).innerText, st: (document.querySelector('.obst') || {}).innerText.replace(/\n/g, ' '), hdr: (document.querySelector('#hprice') || {}).innerText, rows: [...document.querySelectorAll('#obcard .ob-r')].map(r => r.innerText.replace(/\n/g, ' ')).join(' ; ') }; });
  for (let i = 0; i < 5; i++) { await page.waitForTimeout(i ? 6000 : 8000); const s = await snap(); console.log(`T+${8 + i * 6}s`, JSON.stringify(s)); }
  // мелкий шаг, две стороны: меняется ли стакан каждую секунду
  await page.evaluate(() => document.querySelector('[data-obview="two"]').click());
  await page.evaluate(() => document.querySelector('[data-obstepsheet]').click()); await page.waitForTimeout(400);
  await page.evaluate(() => document.querySelector('[data-obstep="1e-7"]').click()); await page.waitForTimeout(800);
  let prev = '', changes = 0; const fine = [];
  for (let i = 0; i < 20; i++) { await page.waitForTimeout(1000); const t = await page.evaluate(() => { const num = e => parseFloat(e.textContent.replace(',', '.')); const b = [...document.querySelectorAll('#obcard .ob2 .h.b .p')].map(num), a = [...document.querySelectorAll('#obcard .ob2 .h.a .p')].map(num); return JSON.stringify({ m: document.querySelector('#obmidp').innerText, b: Math.max(...b), a: Math.min(...a), n: b.length + a.length, h: document.querySelector('#obcard .ob2').innerText.length + ':' + document.querySelector('#obcard .ob2').innerText.slice(0, 160).replace(/\n/g, ' ') }); }); if (t !== prev) changes++; prev = t; if (i % 5 === 0) fine.push(t); }
  console.log('FINE changes in 20s:', changes); fine.forEach(f => console.log('  ', f));
  for (const k of ['kraken', 'gate', 'mexc', 'bingx', 'digifinex', 'coinw']) { await page.evaluate(k => { const c = document.querySelector(`#obx [data-obex="${k}"]`); if (c) c.click(); }, k); await page.waitForTimeout(900); const s = await page.evaluate(() => ({ mid: (document.querySelector('.ob-mid') || {}).innerText.replace(/\n/g, ' | '), note: (document.querySelector('.obnote') || {}).innerText, st: (document.querySelector('.obst') || {}).innerText.replace(/\n/g, ' '), top: [...document.querySelectorAll('#obcard .ob2 .h')].slice(0, 4).map(r => r.innerText.replace(/\n/g, ' ')).join(' ; ') })); console.log(k, JSON.stringify(s)); }
  console.log('trades:', await page.evaluate(() => ((document.querySelector('#obtr') || {}).innerText || '').replace(/\n+/g, ' | ').slice(0, 600)));
  await page.evaluate(() => document.querySelector('#obx [data-obex="all"]').click());
  await page.evaluate(() => document.querySelector('[data-tab="overview"]').click()); await page.waitForTimeout(1500);
  console.log('fng:', await page.evaluate(() => ((document.querySelector('#fng-box') || {}).innerText || '').replace(/\n+/g, ' | ')));
  console.log('mir:', await page.evaluate(() => [...document.querySelectorAll('.mirnote')].map(e => e.innerText).join(' || ')));
  await page.evaluate(() => { const b = document.querySelector('[data-info="fng_d"]'); if (b) b.click(); }); await page.waitForTimeout(600);
  console.log('fng_d:', await page.evaluate(() => (document.querySelector('#sheet').innerText || '').replace(/\n+/g, ' | ').slice(0, 1800)));
  console.log('WS:', JSON.stringify(wsl)); console.log('ERRS:', JSON.stringify(errs));
  await browser.close(); process.exit(0);
})().catch(e => { console.error('ERR', e); process.exit(1); });
