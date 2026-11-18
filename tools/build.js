// Builds the published page: the readable index.html → a compact one (scripts and styles minified, no comments).
//   node tools/build.js <source index.html> <output index.html>
// Needs esbuild (npm i esbuild). Nothing else in the page changes: same markup, same behaviour; it is just much harder
// to read and copy, and lighter to download. The readable source stays private.
const fs = require('fs');
let esbuild;
try { esbuild = require('esbuild'); } catch (e) { console.error('esbuild is not installed (npm i esbuild)'); process.exit(2); }
const [src, out] = process.argv.slice(2);
if (!src || !out) { console.error('usage: node tools/build.js <source index.html> <output index.html>'); process.exit(2); }
const html = fs.readFileSync(src, 'utf8');

// split into: plain markup | <script>…</script> without attributes (page code) | <style>…</style>
const parts = [], re = /<(script|style)(\s[^>]*)?>([\s\S]*?)<\/\1>/gi;
let last = 0, m;
while ((m = re.exec(html))) {
  if (m.index > last) parts.push({ t: 'html', s: html.slice(last, m.index) });
  parts.push({ t: m[1].toLowerCase(), attrs: m[2] || '', s: m[3] });
  last = re.lastIndex;
}
if (last < html.length) parts.push({ t: 'html', s: html.slice(last) });

const js = code => esbuild.transformSync(code, { loader: 'js', minify: true, target: 'es2020', legalComments: 'none', charset: 'utf8' }).code.trim();
const css = code => esbuild.transformSync(code, { loader: 'css', minify: true, legalComments: 'none', charset: 'utf8' }).code.trim();
// markup: drop comments; a run of spaces with a line break becomes one space (renders the same)
const markup = s => s.replace(/<!--(?!\[)[\s\S]*?-->/g, '').replace(/[ \t]*\n\s*/g, '\n');

let n = { js: 0, css: 0 };
const res = parts.map(p => {
  if (p.t === 'html') return markup(p.s);
  if (p.t === 'script') {
    const typ = (p.attrs.match(/type\s*=\s*["']?([^"'\s>]+)/i) || [])[1];
    if (/\bsrc\s*=/.test(p.attrs) || (typ && !/^(text|application)\/(java|ecma)script$|^module$/i.test(typ))) return `<script${p.attrs}>${p.s}</script>`;
    n.js++; return `<script${p.attrs}>${js(p.s).replace(/<\/script/gi, '<\\/script')}</script>`;
  }
  n.css++; return `<style${p.attrs}>${css(p.s)}</style>`;
}).join('');

fs.writeFileSync(out, res);
const kb = b => (b / 1024).toFixed(0) + ' KB';
console.log(`build: ${n.js} scripts, ${n.css} styles; ${kb(Buffer.byteLength(html))} → ${kb(Buffer.byteLength(res))}`);
