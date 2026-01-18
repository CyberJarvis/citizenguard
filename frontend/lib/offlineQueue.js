/**
 * Offline Queue Manager
 * Stores pending submissions in IndexedDB for sync when online
 */

const DB_NAME = 'coastguardian-offline';
const DB_VERSION = 1;

const STORES = {
  SOS: 'sos_queue',
  REPORTS: 'report_queue',
  GENERAL: 'general_queue',
};

let dbInstance = null;

/**
 * Open IndexedDB connection
 */
async function openDB() {
  if (dbInstance) {
    return dbInstance;
  }

  return new Promise((resolve, reject) => {
    const request = indexedDB.open(DB_NAME, DB_VERSION);

    request.onerror = () => {
      console.error('Failed to open IndexedDB:', request.error);
      reject(request.error);
    };

    request.onsuccess = () => {
      dbInstance = request.result;
      resolve(dbInstance);
    };

    request.onupgradeneeded = (event) => {
      const db = event.target.result;

      // SOS queue - highest priority
      if (!db.objectStoreNames.contains(STORES.SOS)) {
        const sosStore = db.createObjectStore(STORES.SOS, { keyPath: 'id', autoIncrement: true });
        sosStore.createIndex('timestamp', 'timestamp', { unique: false });
        sosStore.createIndex('status', 'status', { unique: false });
      }

      // Report queue
      if (!db.objectStoreNames.contains(STORES.REPORTS)) {
        const reportStore = db.createObjectStore(STORES.REPORTS, { keyPath: 'id', autoIncrement: true });
        reportStore.createIndex('timestamp', 'timestamp', { unique: false });
        reportStore.createIndex('status', 'status', { unique: false });
      }

      // General queue for other API calls
      if (!db.objectStoreNames.contains(STORES.GENERAL)) {
        const generalStore = db.createObjectStore(STORES.GENERAL, { keyPath: 'id', autoIncrement: true });
        generalStore.createIndex('timestamp', 'timestamp', { unique: false });
        generalStore.createIndex('endpoint', 'endpoint', { unique: false });
      }
    };
  });
}

/**
 * Get auth token from localStorage
 */
function getAuthToken() {
  if (typeof window === 'undefined') return null;

  try {
    const stored = localStorage.getItem('auth');
    if (stored) {
      const parsed = JSON.parse(stored);
      return parsed.state?.token || null;
    }
  } catch (e) {
    console.error('Failed to get auth token:', e);
  }
  return null;
}

/**
 * Queue an SOS alert for offline submission
 * @param {Object} sosData - SOS alert data
 * @returns {Promise<number>} - Queue item ID
 */
export async function queueSOS(sosData) {
  const db = await openDB();
  const token = getAuthToken();

  return new Promise((resolve, reject) => {
    const tx = db.transaction(STORES.SOS, 'readwrite');
    const store = tx.objectStore(STORES.SOS);

    const item = {
      data: sosData,
      token,
      timestamp: Date.now(),
      status: 'pending',
      retries: 0,
      priority: 'critical',
    };

    const request = store.add(item);

    request.onsuccess = () => {
      console.log('[OfflineQueue] SOS queued:', request.result);
      triggerBackgroundSync('sync-sos');
      resolve(request.result);
    };

    request.onerror = () => {
      console.error('[OfflineQueue] Failed to queue SOS:', request.error);
      reject(request.error);
    };
  });
}

/**
 * Queue a hazard report for offline submission
 * @param {Object} reportData - Hazard report data
 * @returns {Promise<number>} - Queue item ID
 */
export async function queueReport(reportData) {
  const db = await openDB();
  const token = getAuthToken();

  return new Promise((resolve, reject) => {
    const tx = db.transaction(STORES.REPORTS, 'readwrite');
    const store = tx.objectStore(STORES.REPORTS);

    const item = {
      data: reportData,
      token,
      timestamp: Date.now(),
      status: 'pending',
      retries: 0,
    };

    const request = store.add(item);

    request.onsuccess = () => {
      console.log('[OfflineQueue] Report queued:', request.result);
      triggerBackgroundSync('sync-reports');
      resolve(request.result);
    };

    request.onerror = () => {
      console.error('[OfflineQueue] Failed to queue report:', request.error);
      reject(request.error);
    };
  });
}

/**
 * Queue a general API call for offline submission
 * @param {string} endpoint - API endpoint
 * @param {string} method - HTTP method
 * @param {Object} data - Request data
 * @returns {Promise<number>} - Queue item ID
 */
export async function queueAPICall(endpoint, method, data) {
  const db = await openDB();
  const token = getAuthToken();

  return new Promise((resolve, reject) => {
    const tx = db.transaction(STORES.GENERAL, 'readwrite');
    const store = tx.objectStore(STORES.GENERAL);

    const item = {
      endpoint,
      method,
      data,
      token,
      timestamp: Date.now(),
      status: 'pending',
      retries: 0,
    };

    const request = store.add(item);

    request.onsuccess = () => {
      console.log('[OfflineQueue] API call queued:', request.result);
      resolve(request.result);
    };

    request.onerror = () => reject(request.error);
  });
}

/**
 * Get all pending items from a queue
 * @param {string} storeName - Store name (SOS, REPORTS, GENERAL)
 */
export async function getPendingItems(storeName = STORES.SOS) {
  try {
    const db = await openDB();

    // Check if the object store exists
    if (!db.objectStoreNames.contains(storeName)) {
      return [];
    }

    return new Promise((resolve, reject) => {
      try {
        const tx = db.transaction(storeName, 'readonly');
        const store = tx.objectStore(storeName);
        const index = store.index('status');
        const request = index.getAll('pending');

        request.onsuccess = () => resolve(request.result);
        request.onerror = () => resolve([]);
      } catch (e) {
        resolve([]);
      }
    });
  } catch (e) {
    console.warn('[OfflineQueue] getPendingItems error:', e);
    return [];
  }
}

/**
 * Get count of all pending items
 */
export async function getPendingCount() {
  try {
    const db = await openDB();
    let total = 0;

    for (const storeName of Object.values(STORES)) {
      // Check if the object store exists before accessing
      if (!db.objectStoreNames.contains(storeName)) {
        continue;
      }

      const count = await new Promise((resolve) => {
        try {
          const tx = db.transaction(storeName, 'readonly');
          const store = tx.objectStore(storeName);
          const request = store.count();
          request.onsuccess = () => resolve(request.result);
          request.onerror = () => resolve(0);
        } catch (e) {
          resolve(0);
        }
      });
      total += count;
    }

    return total;
  } catch (e) {
    console.warn('[OfflineQueue] getPendingCount error:', e);
    return 0;
  }
}

/**
 * Get detailed queue status
 */
export async function getQueueStatus() {
  try {
    const db = await openDB();
    const status = {
      sos: { pending: 0, total: 0 },
      reports: { pending: 0, total: 0 },
      general: { pending: 0, total: 0 },
      lastSync: typeof localStorage !== 'undefined' ? localStorage.getItem('lastOfflineSync') : null,
    };

    for (const [key, storeName] of Object.entries(STORES)) {
      const lowerKey = key.toLowerCase();

      // Check if the object store exists
      if (!db.objectStoreNames.contains(storeName)) {
        continue;
      }

      const total = await new Promise((resolve) => {
        try {
          const tx = db.transaction(storeName, 'readonly');
          const request = tx.objectStore(storeName).count();
          request.onsuccess = () => resolve(request.result);
          request.onerror = () => resolve(0);
        } catch (e) {
          resolve(0);
        }
      });

      const pending = await new Promise((resolve) => {
        try {
          const tx = db.transaction(storeName, 'readonly');
          const store = tx.objectStore(storeName);
          const index = store.index('status');
          const request = index.count('pending');
          request.onsuccess = () => resolve(request.result);
          request.onerror = () => resolve(0);
        } catch (e) {
          resolve(0);
        }
      });

      status[lowerKey] = { pending, total };
    }

    return status;
  } catch (e) {
    console.warn('[OfflineQueue] getQueueStatus error:', e);
    return {
      sos: { pending: 0, total: 0 },
      reports: { pending: 0, total: 0 },
      general: { pending: 0, total: 0 },
      lastSync: null,
    };
  }
}

/**
 * Update item status
 * @param {string} storeName - Store name
 * @param {number} id - Item ID
 * @param {string} newStatus - New status
 */
export async function updateItemStatus(storeName, id, newStatus) {
  const db = await openDB();

  return new Promise((resolve, reject) => {
    const tx = db.transaction(storeName, 'readwrite');
    const store = tx.objectStore(storeName);
    const getRequest = store.get(id);

    getRequest.onsuccess = () => {
      const item = getRequest.result;
      if (item) {
        item.status = newStatus;
        item.updatedAt = Date.now();
        const putRequest = store.put(item);
        putRequest.onsuccess = () => resolve(true);
        putRequest.onerror = () => reject(putRequest.error);
      } else {
        resolve(false);
      }
    };

    getRequest.onerror = () => reject(getRequest.error);
  });
}

/**
 * Remove item from queue
 * @param {string} storeName - Store name
 * @param {number} id - Item ID
 */
export async function removeItem(storeName, id) {
  const db = await openDB();

  return new Promise((resolve, reject) => {
    const tx = db.transaction(storeName, 'readwrite');
    const store = tx.objectStore(storeName);
    const request = store.delete(id);

    request.onsuccess = () => resolve(true);
    request.onerror = () => reject(request.error);
  });
}

/**
 * Clear all items from a queue
 * @param {string} storeName - Store name
 */
export async function clearQueue(storeName) {
  const db = await openDB();

  return new Promise((resolve, reject) => {
    const tx = db.transaction(storeName, 'readwrite');
    const store = tx.objectStore(storeName);
    const request = store.clear();

    request.onsuccess = () => resolve(true);
    request.onerror = () => reject(request.error);
  });
}

/**
 * Clear all queues
 */
export async function clearAllQueues() {
  for (const storeName of Object.values(STORES)) {
    await clearQueue(storeName);
  }
}

/**
 * Trigger background sync via service worker
 * @param {string} tag - Sync tag
 */
function triggerBackgroundSync(tag) {
  if (typeof navigator === 'undefined' || !('serviceWorker' in navigator)) {
    return;
  }

  navigator.serviceWorker.ready.then((registration) => {
    if ('sync' in registration) {
      registration.sync.register(tag).catch((err) => {
        console.warn('[OfflineQueue] Background sync registration failed:', err);
      });
    }
  });
}

/**
 * Manual sync - attempt to sync all pending items
 * Called when coming back online
 */
export async function syncPending() {
  if (!navigator.onLine) {
    console.log('[OfflineQueue] Cannot sync - offline');
    return { success: false, reason: 'offline' };
  }

  const results = {
    sos: { success: 0, failed: 0 },
    reports: { success: 0, failed: 0 },
    general: { success: 0, failed: 0 },
  };

  // Sync SOS (highest priority)
  const sosItems = await getPendingItems(STORES.SOS);
  for (const item of sosItems) {
    try {
      const response = await fetch('/api/v1/sos/trigger', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(item.token && { Authorization: `Bearer ${item.token}` }),
        },
        body: JSON.stringify(item.data),
      });

      if (response.ok) {
        await removeItem(STORES.SOS, item.id);
        results.sos.success++;
      } else {
        results.sos.failed++;
      }
    } catch (err) {
      results.sos.failed++;
    }
  }

  // Sync Reports
  const reportItems = await getPendingItems(STORES.REPORTS);
  for (const item of reportItems) {
    try {
      const response = await fetch('/api/v1/hazards/report', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(item.token && { Authorization: `Bearer ${item.token}` }),
        },
        body: JSON.stringify(item.data),
      });

      if (response.ok) {
        await removeItem(STORES.REPORTS, item.id);
        results.reports.success++;
      } else {
        results.reports.failed++;
      }
    } catch (err) {
      results.reports.failed++;
    }
  }

  // Sync General
  const generalItems = await getPendingItems(STORES.GENERAL);
  for (const item of generalItems) {
    try {
      const response = await fetch(item.endpoint, {
        method: item.method,
        headers: {
          'Content-Type': 'application/json',
          ...(item.token && { Authorization: `Bearer ${item.token}` }),
        },
        body: item.method !== 'GET' ? JSON.stringify(item.data) : undefined,
      });

      if (response.ok) {
        await removeItem(STORES.GENERAL, item.id);
        results.general.success++;
      } else {
        results.general.failed++;
      }
    } catch (err) {
      results.general.failed++;
    }
  }

  // Update last sync time
  localStorage.setItem('lastOfflineSync', new Date().toISOString());

  return { success: true, results };
}

// Export store names for reference
export { STORES };

export default {
  queueSOS,
  queueReport,
  queueAPICall,
  getPendingItems,
  getPendingCount,
  getQueueStatus,
  updateItemStatus,
  removeItem,
  clearQueue,
  clearAllQueues,
  syncPending,
  STORES,
};
