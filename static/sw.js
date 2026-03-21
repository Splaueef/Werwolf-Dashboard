// Werwolf PWA Service Worker
const CACHE = 'werwolf-v2';
const STATIC = [
  '/',
  '/static/manifest.json',
];

self.addEventListener('install', e => {
  e.waitUntil(
    caches.open(CACHE).then(c => c.addAll(STATIC))
  );
  self.skipWaiting();
});

self.addEventListener('activate', e => {
  e.waitUntil(
    caches.keys().then(keys =>
      Promise.all(keys.filter(k => k !== CACHE).map(k => caches.delete(k)))
    )
  );
  self.clients.claim();
});

// Network first — кешуємо тільки статику, API завжди мережа
self.addEventListener('fetch', e => {
  const url = new URL(e.request.url);
  // API запити — тільки мережа
  if (url.pathname.startsWith('/proxy/') || url.pathname.startsWith('/api/')) {
    e.respondWith(fetch(e.request));
    return;
  }
  // Статика — мережа з fallback на кеш
  e.respondWith(
    fetch(e.request)
      .then(r => {
        const clone = r.clone();
        caches.open(CACHE).then(c => c.put(e.request, clone));
        return r;
      })
      .catch(() => caches.match(e.request))
  );
});
