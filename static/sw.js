// =====================================================
// NEXORA - Service Worker (Offline Fallback System)
// =====================================================

const CACHE_NAME = 'nexora-orange-offline-v3';
const OFFLINE_URL = '/offline.html';

self.addEventListener('install', (event) => {
    event.waitUntil(
        caches.open(CACHE_NAME).then((cache) => {
            return cache.add(new Request(OFFLINE_URL, { cache: 'reload' }));
        })
    );
    self.skipWaiting();
});

self.addEventListener('activate', (event) => {
    event.waitUntil(
        caches.keys().then((keys) => {
            return Promise.all(
                keys.map((key) => {
                    if (key !== CACHE_NAME) {
                        return caches.delete(key);
                    }
                })
            );
        }).then(() => self.clients.claim())
    );
});

self.addEventListener('fetch', (event) => {
    if (event.request.mode === 'navigate') {
        event.respondWith(
            fetch(event.request).catch(async () => {
                const cache = await caches.open(CACHE_NAME);
                const cachedOffline = await cache.match(OFFLINE_URL);
                return cachedOffline || new Response(
                    '<!DOCTYPE html><html><body style="background:#f59e0b;color:#000;display:flex;align-items:center;justify-content:center;height:100vh;font-family:sans-serif;text-align:center;"><div><h1>NEXORA</h1><h2>سێرڤەر لە کار کەوتووە / You are offline</h2><p>باکگڕاوند پرتەقاڵی و تێکستەکان ڕەش</p></div></body></html>',
                    { headers: { 'Content-Type': 'text/html; charset=utf-8' } }
                );
            })
        );
    }
});
