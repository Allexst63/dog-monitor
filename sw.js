// DOG Monitor — мгновенный запуск и офлайн-копия сайта (service worker).
// Страница: сразу из сохранённой копии, свежая версия скачивается следом (если отличается — страница узнаёт об этом
//   и перезагружается сама). Библиотека графиков, шрифты и значки не меняются — из кэша.
// data/*.json: сначала сеть, при сбое — последняя сохранённая копия (страница и сама хранит последние данные).
// Запросы к биржам и DOG DATA (другие сайты) не трогаем.
const CACHE = 'dogmon-v2';
const SHELL = new URL('./', self.location).href;
const CORE = ['manifest.webmanifest', 'favicon.svg', 'fonts/jost.woff', 'fonts/golos-text.woff', 'icons/icon-192.png', 'icons/apple-touch-icon.png', 'vendor/lightweight-charts-5.0.8.js'];

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

// ключ без ?v=… — чтобы без сети нашлась последняя версия файла
const keyOf = req => { const u = new URL(req.url); u.search = ''; u.hash = ''; return u.href; };

// страница: сохранённая копия сразу, обновление — в фоне
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
    if (changed) {            // страница, которая сейчас открывается, ещё не готова слушать — сообщаем чуть позже
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
  if (u.pathname.includes('/data/snapshots/')) return;            // архив сводок: только сеть, в кэше не копим
  const key = keyOf(req);
  if (req.mode === 'navigate' || key === SHELL || key === SHELL + 'index.html') {
    if (/[?&]nosw=1\b/.test(u.search)) return;
    e.respondWith(shell(e));
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
