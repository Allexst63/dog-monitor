// DOG Monitor service worker: instant start and an offline copy of the site.
// Page: served from the saved copy at once; the fresh version downloads next (if it differs, the page is told and reloads itself).
// Chart library, fonts and icons never change — from the cache. data/*.json: network first, the last saved copy on failure.
// Other pages of the site (e.g. /classic/, now only a redirect) — network only. Requests to exchanges and DOG DATA are not touched.
const CACHE = 'dogmon-v7';
const SHELL = new URL('./', self.location).href;
const CORE = ['manifest.webmanifest', 'favicon.svg', 'icons/moon.svg', 'icons/c2-lion-light.png', 'icons/c2-lion-dark.png', 'fonts/inter-400.woff', 'fonts/inter-500.woff', 'fonts/inter-600.woff', 'fonts/inter-700.woff', 'fonts/inter-display-600.woff', 'fonts/inter-display-700.woff', 'fonts/inter-mark.woff', 'icons/icon-192.png', 'icons/apple-touch-icon.png', 'vendor/lightweight-charts-5.0.8-dm1.js'];

self.addEventListener('install', e => {
  e.waitUntil(caches.open(CACHE).then(c => Promise.all(
    [c.add(new Request(SHELL, { cache: 'reload' })).catch(() => { })].concat(CORE.map(u => c.add(u).catch(() => { })))
  )).then(() => self.skipWaiting()));
});

self.addEventListener('activate', e => {
  e.waitUntil(caches.keys()
    .then(keys => Promise.all(keys.filter(k => k.startsWith('dogmon-') && k !== CACHE).map(k => caches.delete(k))))
    .then(() => self.clients.claim()));
});

const keyOf = req => { const u = new URL(req.url); u.search = ''; u.hash = ''; return u.href; };

async function shell(e) {
  const cache = await caches.open(CACHE);
  const cached = await cache.match(SHELL);
  const old = cached ? cached.clone() : null;
  const net = fetch(SHELL, { cache: 'no-cache' }).then(async r => {
    if (!r.ok || r.type !== 'basic') return r;
    const copy = r.clone();
    let changed = false;
    if (old) { try { const [a, b] = await Promise.all([old.text(), r.clone().text()]); changed = a !== b; } catch (er) { } }
    await cache.put(SHELL, copy);
    if (changed) {
      await new Promise(x => setTimeout(x, 2500));
      (await self.clients.matchAll({ type: 'window', includeUncontrolled: true })).forEach(c => c.postMessage({ type: 'dogmon-shell' }));
    }
    return r;
  });
  if (cached) { e.waitUntil(net.catch(() => { })); return cached; }
  return net.catch(() => Response.error());
}

self.addEventListener('fetch', e => {
  const req = e.request;
  if (req.method !== 'GET') return;
  const u = new URL(req.url);
  if (u.origin !== self.location.origin) return;
  if (u.pathname.includes('/data/snapshots/')) return;
  const key = keyOf(req);
  if (key === SHELL || key === SHELL + 'index.html') {
    if (/[?&]nosw=1\b/.test(u.search)) return;
    e.respondWith(shell(e));
    return;
  }
  if (req.mode === 'navigate') {
    e.respondWith(fetch(req).catch(() => caches.match(key).then(m => m || caches.match(SHELL)).then(m => m || Response.error())));
    return;
  }
  if (/\/(fonts|icons|vendor)\//.test(u.pathname)) {
    e.respondWith(caches.match(key).then(m => m || fetch(req).then(r => {
      if (r.ok) { const cp = r.clone(); caches.open(CACHE).then(c => c.put(key, cp)); }
      return r;
    })));
    return;
  }
  e.respondWith(fetch(req).then(r => {
    if (r.ok && r.type === 'basic') { const cp = r.clone(); caches.open(CACHE).then(c => c.put(key, cp)); }
    return r;
  }).catch(() => caches.match(key).then(m => m || Response.error())));
});
