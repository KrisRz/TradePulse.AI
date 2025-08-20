// TradePulse.AI Service Worker - Simplified
const CACHE_NAME = 'tradepulse-v1';

// Minimal cache strategy to avoid precaching errors
self.addEventListener('install', (event) => {
  console.log('[SW] Installing...');
  self.skipWaiting();
});

self.addEventListener('activate', (event) => {
  console.log('[SW] Activating...');
  self.clients.claim();
});

// Simple fetch handler - no aggressive caching to avoid errors
self.addEventListener('fetch', (event) => {
  // Only handle same-origin requests
  if (!event.request.url.startsWith(self.location.origin)) {
    return;
  }
  
  // For API requests, always use network
  if (event.request.url.includes('/api/')) {
    event.respondWith(fetch(event.request));
    return;
  }
  
  // For other requests, try network first
  event.respondWith(
    fetch(event.request).catch(() => {
      // On network failure, return a basic response
      return new Response('Offline', { status: 503 });
    })
  );
});