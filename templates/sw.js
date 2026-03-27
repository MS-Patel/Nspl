const CACHE_NAME = 'buybestfin-v1';
const STATIC_ASSETS = [
    '/',
    '/static/css/app.css',
    '/static/css/style.css',
    '/static/js/app.js',
    '/static/js/libs/components.js',
    '/static/js/libs/forms.js',
    '/static/js/script.js',
    '/static/images/logo.png',
    '/static/images/icons/icon-192x192.png',
    '/static/images/icons/icon-512x512.png',
    '/manifest.json'
];

self.addEventListener('install', (event) => {
    event.waitUntil(
        caches.open(CACHE_NAME).then((cache) => {
            console.log('[Service Worker] Caching static assets');
            return cache.addAll(STATIC_ASSETS);
        })
    );
    self.skipWaiting();
});

self.addEventListener('activate', (event) => {
    event.waitUntil(
        caches.keys().then((cacheNames) => {
            return Promise.all(
                cacheNames.map((cache) => {
                    if (cache !== CACHE_NAME) {
                        console.log('[Service Worker] Clearing old cache');
                        return caches.delete(cache);
                    }
                })
            );
        })
    );
    self.clients.claim();
});

self.addEventListener('fetch', (event) => {
    // Basic fetch and cache strategy
    if (event.request.method !== 'GET') {
        return;
    }

    event.respondWith(
        caches.match(event.request).then((cachedResponse) => {
            if (cachedResponse) {
                return cachedResponse;
            }

            return fetch(event.request).then((networkResponse) => {
                // Check if response is valid
                if (!networkResponse || networkResponse.status !== 200 || networkResponse.type !== 'basic') {
                    return networkResponse;
                }

                // Don't cache API calls or dynamic routes implicitly for safety unless specified,
                // but for a generic fallback, we'll cache what we fetch that's safe to cache.
                // It's usually safer to cache only specific scopes like static assets.
                const url = new URL(event.request.url);
                if (url.pathname.startsWith('/static/') || url.pathname.startsWith('/media/')) {
                    const responseToCache = networkResponse.clone();
                    caches.open(CACHE_NAME).then((cache) => {
                        cache.put(event.request, responseToCache);
                    });
                }

                return networkResponse;
            }).catch(() => {
                // If network fails and it's an HTML page, we might want to return an offline page,
                // but for now we just fail gracefully.
                // Could return a default offline html here if we had one cached.
            });
        })
    );
});
