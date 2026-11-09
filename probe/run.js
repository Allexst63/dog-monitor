// Temporary: why are the charts squeezed on the live site? DOM metrics + isolated Lightweight Charts experiments (Chromium from Playwright 1.48)
const { chromium } = require('playwright');
const fs = require('fs');
const OUT = 'probe/out4';
fs.mkdirSync(OUT, { recursive: true });
const SITE = 'https://allexst63.github.io/dog-monitor/';
const log = [];
const L = (...a) => { const s = a.map(x => typeof x === 'string' ? x : JSON.stringify(x)).join(' '); log.push(s); console.log(s); };
(async () => {
  const b = await chromium.launch();
  L('browser', b.version());
  const ctx = await b.newContext({ viewport: { width: 390, height: 844 }, deviceScaleFactor: 2, isMobile: true, hasTouch: true, locale: 'en-US', timezoneId: 'Asia/Dubai' });
  const p = await ctx.newPage();
  const errs = []; p.on('console', m => { if (m.type() === 'error' || m.type() === 'warning') errs.push(m.type() + ': ' + m.text().slice(0, 300)); }); p.on('pageerror', e => errs.push('PAGEERROR ' + e.message));
  await p.goto(SITE + '?nosw=1#charts', { waitUntil: 'load', timeout: 60000 });
  await p.waitForTimeout(20000);
  L('dom', await p.evaluate(() => [...document.querySelectorAll('.tvchart')].map(el => {
    const c = el.querySelector('.tv-lightweight-charts');
    return { id: el.id, cw: el.clientWidth, ch: el.clientHeight, chart: c ? c.style.width + 'x' + c.style.height : null,
      tds: c ? [...c.querySelectorAll('tr')].slice(0, 3).map(tr => [...tr.children].map(td => Math.round(td.getBoundingClientRect().width))) : null,
      canv: c ? [...c.querySelectorAll('canvas')].slice(0, 6).map(cv => cv.width + 'x' + cv.height + '/' + cv.style.width) : null };
  })));
  L('fonts', await p.evaluate(() => [...document.fonts].map(f => f.family + ':' + f.status).join(', ')));
  // isolated experiments with the same library
  L('exp', await p.evaluate(async () => {
    const LW = window.LightweightCharts; if (!LW) return 'no LW';
    const out = {};
    const pts = Array.from({ length: 120 }, (_, i) => ({ time: 1794000000 + i * 3600, value: 0.00078 + Math.sin(i / 7) * 0.00002 }));
    const make = async (name, opts, ser) => {
      const d = document.createElement('div'); d.style.cssText = 'width:342px;height:300px;position:relative'; document.body.appendChild(d);
      try {
        const ch = LW.createChart(d, opts);
        const s = ch.addSeries(LW.LineSeries, ser || {});
        s.setData(pts);
        await new Promise(r => setTimeout(r, 600));
        out[name] = { ps: ch.priceScale('right').width(), ts: ch.timeScale().width(), lbl: ch.priceScale('right').width() };
        ch.remove();
      } catch (e) { out[name] = 'ERR ' + e.message; }
      d.remove();
    };
    const cf = { type: 'custom', formatter: p => (+p).toFixed(7), minMove: 1e-7 };
    await make('E1_default_autosize', { autoSize: true });
    await make('E2_custom_format', { autoSize: true }, { priceFormat: cf });
    await make('E3_font', { autoSize: true, layout: { fontSize: 11, fontFamily: '"Golos Text", system-ui, sans-serif' } }, { priceFormat: cf });
    await make('E4_minwidth', { autoSize: true, rightPriceScale: { minimumWidth: 64 } }, { priceFormat: cf });
    await make('E5_locale', { autoSize: true, localization: { locale: 'en-GB', timeFormatter: t => String(t) } }, { priceFormat: cf });
    await make('E6_explicit_width', { width: 342, height: 300 }, { priceFormat: cf });
    await make('E7_panes_attr', { autoSize: true, layout: { attributionLogo: true, panes: { separatorColor: '#ccc', separatorHoverColor: '#ccc', enableResize: false } } }, { priceFormat: cf });
    return out;
  }));
  // exact replica of the site's TV chart options
  L('exp2', await p.evaluate(async () => {
    const LW = window.LightweightCharts; const out = {};
    const d = document.createElement('div'); d.style.cssText = 'width:342px;height:520px;position:relative'; document.body.appendChild(d);
    const ch = LW.createChart(d, { autoSize: true, layout: { background: { type: 'solid', color: '#fff' }, textColor: '#888', fontSize: 11, fontFamily: '"Golos Text", system-ui, sans-serif', attributionLogo: true, panes: { separatorColor: '#ddd', separatorHoverColor: '#ddd', enableResize: false } },
      grid: { vertLines: { color: '#eee' }, horzLines: { color: '#eee' } }, rightPriceScale: { borderColor: '#ddd', minimumWidth: 64 },
      timeScale: { borderColor: '#ddd', rightOffset: 3, barSpacing: 6, timeVisible: true, secondsVisible: false },
      crosshair: { mode: 0 }, handleScroll: { mouseWheel: true, pressedMouseMove: true, horzTouchDrag: true, vertTouchDrag: false }, handleScale: { mouseWheel: true, pinch: true, axisPressedMouseMove: { time: true, price: false } } });
    const pf = { type: 'custom', formatter: p => (+p).toFixed(7), minMove: 1e-7 };
    const pts = Array.from({ length: 300 }, (_, i) => ({ time: 1794000000 + i * 3600, open: 0.00078, high: 0.00079, low: 0.00077, close: 0.000785 }));
    const cs = ch.addSeries(LW.CandlestickSeries, { priceFormat: pf }, 0); cs.setData(pts);
    const vol = ch.addSeries(LW.HistogramSeries, { priceScaleId: 'vol', priceFormat: { type: 'custom', formatter: v => String(Math.round(v)) }, lastValueVisible: false, priceLineVisible: false }, 0);
    vol.setData(pts.map(x => ({ time: x.time, value: 1000 })));
    out.afterMain = ch.priceScale('right', 0).width();
    const rsi = ch.addSeries(LW.LineSeries, { priceFormat: { type: 'custom', formatter: v => String(Math.round(v)), minMove: 1 }, autoscaleInfoProvider: () => ({ priceRange: { minValue: 0, maxValue: 100 } }) }, 1);
    rsi.setData(pts.map((x, i) => ({ time: x.time, value: 40 + (i % 20) })));
    rsi.createPriceLine({ price: 70, color: 'red', lineWidth: 1, lineStyle: 2, axisLabelVisible: true, title: '' });
    out.afterRsi = ch.priceScale('right', 0).width();
    const h = ch.addSeries(LW.HistogramSeries, { priceFormat: { type: 'custom', formatter: v => v.toFixed(2) + '%', minMove: 0.0001 }, priceLineVisible: false, lastValueVisible: false }, 2);
    h.setData(pts.map((x, i) => ({ time: x.time, value: Math.sin(i / 9) })));
    out.afterMacd = ch.priceScale('right', 0).width();
    try { ch.panes().forEach((pp, i) => pp.setStretchFactor([280, 104, 104][i])); } catch (e) { out.sf = e.message; }
    try { ch.priceScale('right', 1).applyOptions({ scaleMargins: { top: 0.1, bottom: 0.08 } }); } catch (e) { out.ps = e.message; }
    await new Promise(r => setTimeout(r, 800));
    out.final = { ps0: ch.priceScale('right', 0).width(), ts: ch.timeScale().width(), w: d.querySelector('.tv-lightweight-charts').style.width };
    ch.remove(); d.remove();
    return out;
  }));
  L('errors', errs);
  await b.close();
  fs.writeFileSync(OUT + '/log.txt', log.join('\n'));
})().catch(e => { fs.writeFileSync(OUT + '/err.txt', String(e && e.stack || e)); });
