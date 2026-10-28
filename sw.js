// DOG Monitor — офлайн-копия сайта (service worker).
// Свои файлы (страница, data/*.json): сначала сеть, при сбое — последняя сохранённая копия.
// Шрифты и значки не меняются — берём из кэша. Запросы к биржам и DOG DATA (другие сайты) не трогаем.
const CACHE = 'dogmon-v1';
const CORE = ['./', 'index.html', 'manifest.webmanifest', 'favicon.svg', 'fonts/jost.woff', 'fonts/golos-text.woff', 'icons/icon-192.png', 'icons/apple-touch-icon.png'];

self.addEventListener('install', e => {
  e.waitUntil(caches.open(CACHE).then(c => c.addAll(CORE)).catch(() => { }).then(() => self.skipWaiting()));
});

self.addEventListener('activate', e => {
  e.waitUntil(caches.keys()
    .then(keys => Promise.all(keys.filter(k => k.startsWith('dogmon-') && k !== CACHE).map(k => caches.delete(k))))
    .then(() => self.clients.claim()));
});

// ключ без ?v=… — чтобы без сети нашлась последняя версия файла
const keyOf = req => { const u = new URL(req.url); u.search = ''; return u.href; };

self.addEventListener('fetch', e => {
  const req = e.request;
  if (req.method !== 'GET') return;
  const u = new URL(req.url);
  if (u.origin !== self.location.origin) return;
  if (u.pathname.includes('/data/snapshots/')) return;            // архив сводок: только сеть, в кэше не копим
  const key = keyOf(req);
  if (/\/(fonts|icons)\//.test(u.pathname)) {
    e.respondWith(caches.match(key).then(m => m || fetch(req).then(r => {
      if (r.ok) { const cp = r.clone(); caches.open(CACHE).then(c => c.put(key, cp)); }
      return r;
    })));
    return;
  }
  e.respondWith(fetch(req).then(r => {
    if (r.ok && r.type === 'basic') { const cp = r.clone(); caches.open(CACHE).then(c => c.put(key, cp)); }
    return r;
  }).catch(() => caches.match(key).then(m => m || (req.mode === 'navigate'
    ? caches.match(new URL('./', self.location).href).then(x => x || caches.match(new URL('index.html', self.location).href))
    : Response.error()))));
});
