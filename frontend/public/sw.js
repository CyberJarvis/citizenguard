/**
 * CoastGuardian Service Worker
 * Enables offline functionality for the ocean hazard platform
 */

const CACHE_VERSION = 'v1';
const STATIC_CACHE = `coastguardian-static-${CACHE_VERSION}`;
const TILE_CACHE = `coastguardian-tiles-${CACHE_VERSION}`;
const API_CACHE = `coastguardian-api-${CACHE_VERSION}`;
const GEOJSON_CACHE = `coastguardian-geojson-${CACHE_VERSION}`;

// Static assets to cache on install
const STATIC_ASSETS = [
  '/',
  '/map',
  '/manifest.json',
  '/icons/icon-192x192.png',
  '/icons/icon-512x512.png',
  '/offline.html',
];

// GeoJSON files to cache
const GEOJSON_ASSETS = [
  '/geojson/ports.geojson',
  '/geojson/fishing_villages.geojson',
  '/geojson/marine_protected_areas.geojson',
  '/geojson/population_density.geojson',
  '/geojson/coast_guard_stations.geojson',
];

// Tile URL patterns to cache
const TILE_PATTERNS = [
  /https:\/\/.*\.tile\.openstreetmap\.org\/.*/,
  /https:\/\/server\.arcgisonline\.com\/ArcGIS\/rest\/services\/.*/,
  /https:\/\/tiles\.stadiamaps\.com\/.*/,
];

// API endpoints that can be cached for offline
const CACHEABLE_API_PATTERNS = [
  /\/api\/v1\/hazards\/timeline/,
  /\/api\/v1\/hazards\/nearby/,
  /\/api\/v1\/alerts\/active/,
];

// Install event - cache static assets
self.addEventListener('install', (event) => {
  console.log('[SW] Installing service worker...');

  event.waitUntil(
    Promise.all([
      // Cache static assets
      caches.open(STATIC_CACHE).then((cache) => {
        console.log('[SW] Caching static assets');
        return cache.addAll(STATIC_ASSETS).catch((err) => {
          console.warn('[SW] Some static assets failed to cache:', err);
        });
      }),
      // Cache GeoJSON files
      caches.open(GEOJSON_CACHE).then((cache) => {
        console.log('[SW] Caching GeoJSON files');
        return cache.addAll(GEOJSON_ASSETS).catch((err) => {
          console.warn('[SW] Some GeoJSON files failed to cache:', err);
        });
      }),
    ]).then(() => {
      console.log('[SW] Installation complete');
      return self.skipWaiting();
    })
  );
});

// Activate event - clean up old caches
self.addEventListener('activate', (event) => {
  console.log('[SW] Activating service worker...');

  event.waitUntil(
    caches.keys().then((cacheNames) => {
      return Promise.all(
        cacheNames.map((cacheName) => {
          // Delete old version caches
          if (cacheName.startsWith('coastguardian-') && !cacheName.includes(CACHE_VERSION)) {
            console.log('[SW] Deleting old cache:', cacheName);
            return caches.delete(cacheName);
          }
        })
      );
    }).then(() => {
      console.log('[SW] Activation complete');
      return self.clients.claim();
    })
  );
});

// Fetch event - implement caching strategies
self.addEventListener('fetch', (event) => {
  const { request } = event;
  const url = new URL(request.url);

  // Skip non-GET requests
  if (request.method !== 'GET') {
    return;
  }

  // Skip chrome-extension and other non-http requests
  if (!url.protocol.startsWith('http')) {
    return;
  }

  // Strategy: Map tiles - Cache first, network fallback
  if (isTileRequest(url.href)) {
    event.respondWith(tilesCacheFirst(request));
    return;
  }

  // Strategy: GeoJSON files - Cache first, network fallback
  if (url.pathname.endsWith('.geojson')) {
    event.respondWith(geojsonCacheFirst(request));
    return;
  }

  // Strategy: Cacheable API - Network first, cache fallback
  if (isCacheableAPI(url.pathname)) {
    event.respondWith(apiNetworkFirst(request));
    return;
  }

  // Strategy: Static assets - Cache first, network fallback
  if (isStaticAsset(url.pathname)) {
    event.respondWith(staticCacheFirst(request));
    return;
  }

  // Default: Network only with offline fallback
  event.respondWith(networkWithOfflineFallback(request));
});

// Background sync for offline submissions
self.addEventListener('sync', (event) => {
  console.log('[SW] Background sync triggered:', event.tag);

  if (event.tag === 'sync-sos') {
    event.waitUntil(syncQueuedSOS());
  }

  if (event.tag === 'sync-reports') {
    event.waitUntil(syncQueuedReports());
  }
});

// Push notification handler
self.addEventListener('push', (event) => {
  console.log('[SW] Push notification received');

  let data = {
    title: 'CoastGuardian Alert',
    body: 'New notification',
    icon: '/icons/icon-192x192.png',
    badge: '/icons/badge-72x72.png',
    url: '/map',
  };

  try {
    if (event.data) {
      data = { ...data, ...event.data.json() };
    }
  } catch (e) {
    console.warn('[SW] Failed to parse push data:', e);
  }

  const options = {
    body: data.body,
    icon: data.icon,
    badge: data.badge,
    vibrate: [200, 100, 200],
    data: {
      url: data.url,
      dateOfArrival: Date.now(),
    },
    actions: data.actions || [
      { action: 'view', title: 'View' },
      { action: 'dismiss', title: 'Dismiss' },
    ],
    tag: data.tag || 'coastguardian-notification',
    renotify: true,
  };

  event.waitUntil(
    self.registration.showNotification(data.title, options)
  );
});

// Notification click handler
self.addEventListener('notificationclick', (event) => {
  console.log('[SW] Notification clicked:', event.action);

  event.notification.close();

  if (event.action === 'dismiss') {
    return;
  }

  const urlToOpen = event.notification.data?.url || '/map';

  event.waitUntil(
    clients.matchAll({ type: 'window', includeUncontrolled: true })
      .then((windowClients) => {
        // Focus existing window if available
        for (const client of windowClients) {
          if (client.url.includes(urlToOpen) && 'focus' in client) {
            return client.focus();
          }
        }
        // Open new window
        if (clients.openWindow) {
          return clients.openWindow(urlToOpen);
        }
      })
  );
});

// Message handler for cache management
self.addEventListener('message', (event) => {
  const { type, payload } = event.data || {};

  switch (type) {
    case 'CACHE_TILES':
      event.waitUntil(cacheTilesForArea(payload));
      break;
    case 'CLEAR_TILE_CACHE':
      event.waitUntil(clearTileCache());
      break;
    case 'GET_CACHE_SIZE':
      event.waitUntil(getCacheSize().then((size) => {
        event.ports[0].postMessage({ type: 'CACHE_SIZE', payload: size });
      }));
      break;
    case 'SKIP_WAITING':
      self.skipWaiting();
      break;
  }
});

// ============ Helper Functions ============

function isTileRequest(url) {
  return TILE_PATTERNS.some((pattern) => pattern.test(url));
}

function isCacheableAPI(pathname) {
  return CACHEABLE_API_PATTERNS.some((pattern) => pattern.test(pathname));
}

function isStaticAsset(pathname) {
  return (
    pathname.startsWith('/_next/static/') ||
    pathname.startsWith('/icons/') ||
    pathname.endsWith('.js') ||
    pathname.endsWith('.css') ||
    pathname.endsWith('.woff2') ||
    pathname.endsWith('.png') ||
    pathname.endsWith('.jpg') ||
    pathname.endsWith('.svg')
  );
}

// ============ Caching Strategies ============

async function tilesCacheFirst(request) {
  const cache = await caches.open(TILE_CACHE);
  const cachedResponse = await cache.match(request);

  if (cachedResponse) {
    // Return cached tile, update in background
    fetchAndCache(request, TILE_CACHE);
    return cachedResponse;
  }

  try {
    const networkResponse = await fetch(request);
    if (networkResponse.ok) {
      cache.put(request, networkResponse.clone());
    }
    return networkResponse;
  } catch (error) {
    console.warn('[SW] Tile fetch failed:', error);
    return new Response('', { status: 404 });
  }
}

async function geojsonCacheFirst(request) {
  const cache = await caches.open(GEOJSON_CACHE);
  const cachedResponse = await cache.match(request);

  if (cachedResponse) {
    return cachedResponse;
  }

  try {
    const networkResponse = await fetch(request);
    if (networkResponse.ok) {
      cache.put(request, networkResponse.clone());
    }
    return networkResponse;
  } catch (error) {
    console.warn('[SW] GeoJSON fetch failed:', error);
    return new Response('{"error": "Offline"}', {
      status: 503,
      headers: { 'Content-Type': 'application/json' },
    });
  }
}

async function apiNetworkFirst(request) {
  const cache = await caches.open(API_CACHE);

  try {
    const networkResponse = await fetch(request);
    if (networkResponse.ok) {
      cache.put(request, networkResponse.clone());
    }
    return networkResponse;
  } catch (error) {
    console.warn('[SW] API fetch failed, using cache:', error);
    const cachedResponse = await cache.match(request);
    if (cachedResponse) {
      return cachedResponse;
    }
    return new Response(JSON.stringify({
      success: false,
      error: { code: 'OFFLINE', message: 'You are offline' },
      offline: true,
    }), {
      status: 503,
      headers: { 'Content-Type': 'application/json' },
    });
  }
}

async function staticCacheFirst(request) {
  const cache = await caches.open(STATIC_CACHE);
  const cachedResponse = await cache.match(request);

  if (cachedResponse) {
    return cachedResponse;
  }

  try {
    const networkResponse = await fetch(request);
    if (networkResponse.ok) {
      cache.put(request, networkResponse.clone());
    }
    return networkResponse;
  } catch (error) {
    return new Response('Offline', { status: 503 });
  }
}

async function networkWithOfflineFallback(request) {
  try {
    return await fetch(request);
  } catch (error) {
    // Try to return cached offline page
    const cache = await caches.open(STATIC_CACHE);
    const offlineResponse = await cache.match('/offline.html');
    if (offlineResponse) {
      return offlineResponse;
    }
    return new Response('Offline', { status: 503 });
  }
}

async function fetchAndCache(request, cacheName) {
  try {
    const cache = await caches.open(cacheName);
    const response = await fetch(request);
    if (response.ok) {
      cache.put(request, response);
    }
  } catch (error) {
    // Ignore background fetch errors
  }
}

// ============ Tile Caching for Offline Maps ============

async function cacheTilesForArea(payload) {
  const { center, radiusKm = 100, minZoom = 5, maxZoom = 12, tileServer } = payload;
  const cache = await caches.open(TILE_CACHE);
  const tiles = getTilesInRadius(center.lat, center.lng, radiusKm, minZoom, maxZoom);

  const tileBase = tileServer || 'https://a.tile.openstreetmap.org';
  let cached = 0;
  let failed = 0;

  for (const tile of tiles) {
    const url = `${tileBase}/${tile.z}/${tile.x}/${tile.y}.png`;
    try {
      const response = await fetch(url);
      if (response.ok) {
        await cache.put(url, response);
        cached++;
      } else {
        failed++;
      }
    } catch (error) {
      failed++;
    }

    // Report progress every 50 tiles
    if ((cached + failed) % 50 === 0) {
      self.clients.matchAll().then((clients) => {
        clients.forEach((client) => {
          client.postMessage({
            type: 'TILE_CACHE_PROGRESS',
            payload: { cached, failed, total: tiles.length },
          });
        });
      });
    }
  }

  // Final report
  self.clients.matchAll().then((clients) => {
    clients.forEach((client) => {
      client.postMessage({
        type: 'TILE_CACHE_COMPLETE',
        payload: { cached, failed, total: tiles.length },
      });
    });
  });
}

function getTilesInRadius(lat, lng, radiusKm, minZoom, maxZoom) {
  const tiles = [];
  const earthRadius = 6371; // km

  for (let zoom = minZoom; zoom <= maxZoom; zoom++) {
    const n = Math.pow(2, zoom);

    // Calculate bounds
    const latRad = lat * Math.PI / 180;
    const deltaLat = (radiusKm / earthRadius) * (180 / Math.PI);
    const deltaLng = deltaLat / Math.cos(latRad);

    const minLat = lat - deltaLat;
    const maxLat = lat + deltaLat;
    const minLng = lng - deltaLng;
    const maxLng = lng + deltaLng;

    // Convert to tile coordinates
    const minX = Math.floor((minLng + 180) / 360 * n);
    const maxX = Math.floor((maxLng + 180) / 360 * n);
    const minY = Math.floor((1 - Math.log(Math.tan(maxLat * Math.PI / 180) + 1 / Math.cos(maxLat * Math.PI / 180)) / Math.PI) / 2 * n);
    const maxY = Math.floor((1 - Math.log(Math.tan(minLat * Math.PI / 180) + 1 / Math.cos(minLat * Math.PI / 180)) / Math.PI) / 2 * n);

    for (let x = minX; x <= maxX; x++) {
      for (let y = minY; y <= maxY; y++) {
        tiles.push({ z: zoom, x: Math.max(0, Math.min(n - 1, x)), y: Math.max(0, Math.min(n - 1, y)) });
      }
    }
  }

  return tiles;
}

async function clearTileCache() {
  await caches.delete(TILE_CACHE);
  console.log('[SW] Tile cache cleared');
}

async function getCacheSize() {
  const cacheNames = await caches.keys();
  let totalSize = 0;

  for (const cacheName of cacheNames) {
    if (cacheName.startsWith('coastguardian-')) {
      const cache = await caches.open(cacheName);
      const keys = await cache.keys();
      totalSize += keys.length;
    }
  }

  return { entries: totalSize };
}

// ============ Offline Queue Sync ============

async function syncQueuedSOS() {
  console.log('[SW] Syncing queued SOS alerts...');

  try {
    const db = await openOfflineDB();
    const tx = db.transaction('sos_queue', 'readwrite');
    const store = tx.objectStore('sos_queue');
    const items = await store.getAll();

    for (const item of items) {
      try {
        const response = await fetch('/api/v1/sos/trigger', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${item.token}`,
          },
          body: JSON.stringify(item.data),
        });

        if (response.ok) {
          await store.delete(item.id);
          console.log('[SW] SOS synced:', item.id);

          // Notify client
          self.clients.matchAll().then((clients) => {
            clients.forEach((client) => {
              client.postMessage({
                type: 'SOS_SYNCED',
                payload: { id: item.id, success: true },
              });
            });
          });
        }
      } catch (error) {
        console.warn('[SW] Failed to sync SOS:', item.id, error);
      }
    }
  } catch (error) {
    console.error('[SW] SOS sync failed:', error);
  }
}

async function syncQueuedReports() {
  console.log('[SW] Syncing queued reports...');

  try {
    const db = await openOfflineDB();
    const tx = db.transaction('report_queue', 'readwrite');
    const store = tx.objectStore('report_queue');
    const items = await store.getAll();

    for (const item of items) {
      try {
        const response = await fetch('/api/v1/hazards/report', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${item.token}`,
          },
          body: JSON.stringify(item.data),
        });

        if (response.ok) {
          await store.delete(item.id);
          console.log('[SW] Report synced:', item.id);

          // Notify client
          self.clients.matchAll().then((clients) => {
            clients.forEach((client) => {
              client.postMessage({
                type: 'REPORT_SYNCED',
                payload: { id: item.id, success: true },
              });
            });
          });
        }
      } catch (error) {
        console.warn('[SW] Failed to sync report:', item.id, error);
      }
    }
  } catch (error) {
    console.error('[SW] Report sync failed:', error);
  }
}

function openOfflineDB() {
  return new Promise((resolve, reject) => {
    const request = indexedDB.open('coastguardian-offline', 1);

    request.onerror = () => reject(request.error);
    request.onsuccess = () => resolve(request.result);

    request.onupgradeneeded = (event) => {
      const db = event.target.result;

      if (!db.objectStoreNames.contains('sos_queue')) {
        db.createObjectStore('sos_queue', { keyPath: 'id', autoIncrement: true });
      }

      if (!db.objectStoreNames.contains('report_queue')) {
        db.createObjectStore('report_queue', { keyPath: 'id', autoIncrement: true });
      }
    };
  });
}
