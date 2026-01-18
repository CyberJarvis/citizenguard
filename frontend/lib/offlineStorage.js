import { openDB } from 'idb';

const DB_NAME = 'coastguardian-offline';
const DB_VERSION = 1;

// Store names
const STORES = {
  PENDING_REPORTS: 'pending-reports',
  CACHED_DATA: 'cached-data',
  USER_PROFILE: 'user-profile',
};

// Initialize the database
async function initDB() {
  return openDB(DB_NAME, DB_VERSION, {
    upgrade(db) {
      // Store for pending hazard reports (to be synced)
      if (!db.objectStoreNames.contains(STORES.PENDING_REPORTS)) {
        const pendingStore = db.createObjectStore(STORES.PENDING_REPORTS, {
          keyPath: 'id',
          autoIncrement: true,
        });
        pendingStore.createIndex('createdAt', 'createdAt');
        pendingStore.createIndex('status', 'status');
      }

      // Store for cached API data
      if (!db.objectStoreNames.contains(STORES.CACHED_DATA)) {
        const cacheStore = db.createObjectStore(STORES.CACHED_DATA, {
          keyPath: 'key',
        });
        cacheStore.createIndex('expiry', 'expiry');
      }

      // Store for user profile data
      if (!db.objectStoreNames.contains(STORES.USER_PROFILE)) {
        db.createObjectStore(STORES.USER_PROFILE, {
          keyPath: 'id',
        });
      }
    },
  });
}

// Get database instance (singleton pattern)
let dbPromise = null;
function getDB() {
  if (!dbPromise) {
    dbPromise = initDB();
  }
  return dbPromise;
}

// ==================== PENDING REPORTS ====================

/**
 * Save a hazard report for later sync
 * @param {Object} reportData - The hazard report data
 * @returns {Promise<number>} - The ID of the saved report
 */
export async function savePendingReport(reportData) {
  const db = await getDB();
  const report = {
    ...reportData,
    createdAt: new Date().toISOString(),
    status: 'pending',
    retryCount: 0,
  };
  const id = await db.add(STORES.PENDING_REPORTS, report);
  return id;
}

/**
 * Get all pending reports
 * @returns {Promise<Array>} - Array of pending reports
 */
export async function getPendingReports() {
  const db = await getDB();
  return db.getAllFromIndex(STORES.PENDING_REPORTS, 'status', 'pending');
}

/**
 * Get count of pending reports
 * @returns {Promise<number>} - Count of pending reports
 */
export async function getPendingReportsCount() {
  const db = await getDB();
  const reports = await db.getAllFromIndex(STORES.PENDING_REPORTS, 'status', 'pending');
  return reports.length;
}

/**
 * Update a pending report's status
 * @param {number} id - Report ID
 * @param {string} status - New status ('pending', 'syncing', 'synced', 'failed')
 */
export async function updatePendingReportStatus(id, status, error = null) {
  const db = await getDB();
  const report = await db.get(STORES.PENDING_REPORTS, id);
  if (report) {
    report.status = status;
    if (error) {
      report.lastError = error;
      report.retryCount = (report.retryCount || 0) + 1;
    }
    if (status === 'synced') {
      report.syncedAt = new Date().toISOString();
    }
    await db.put(STORES.PENDING_REPORTS, report);
  }
}

/**
 * Delete a pending report (after successful sync)
 * @param {number} id - Report ID
 */
export async function deletePendingReport(id) {
  const db = await getDB();
  await db.delete(STORES.PENDING_REPORTS, id);
}

/**
 * Clear all synced reports
 */
export async function clearSyncedReports() {
  const db = await getDB();
  const tx = db.transaction(STORES.PENDING_REPORTS, 'readwrite');
  const store = tx.objectStore(STORES.PENDING_REPORTS);
  const allReports = await store.getAll();

  for (const report of allReports) {
    if (report.status === 'synced') {
      await store.delete(report.id);
    }
  }
  await tx.done;
}

// ==================== CACHED DATA ====================

/**
 * Cache API response data
 * @param {string} key - Cache key (usually the API endpoint)
 * @param {any} data - Data to cache
 * @param {number} ttlMinutes - Time to live in minutes
 */
export async function setCachedData(key, data, ttlMinutes = 60) {
  const db = await getDB();
  const expiry = new Date(Date.now() + ttlMinutes * 60 * 1000).toISOString();
  await db.put(STORES.CACHED_DATA, {
    key,
    data,
    expiry,
    cachedAt: new Date().toISOString(),
  });
}

/**
 * Get cached data if not expired
 * @param {string} key - Cache key
 * @returns {Promise<any|null>} - Cached data or null if expired/not found
 */
export async function getCachedData(key) {
  const db = await getDB();
  const cached = await db.get(STORES.CACHED_DATA, key);

  if (!cached) return null;

  // Check if expired
  if (new Date(cached.expiry) < new Date()) {
    await db.delete(STORES.CACHED_DATA, key);
    return null;
  }

  return cached.data;
}

/**
 * Clear all cached data
 */
export async function clearCachedData() {
  const db = await getDB();
  await db.clear(STORES.CACHED_DATA);
}

/**
 * Clean up expired cache entries
 */
export async function cleanupExpiredCache() {
  const db = await getDB();
  const tx = db.transaction(STORES.CACHED_DATA, 'readwrite');
  const store = tx.objectStore(STORES.CACHED_DATA);
  const allCached = await store.getAll();
  const now = new Date();

  for (const entry of allCached) {
    if (new Date(entry.expiry) < now) {
      await store.delete(entry.key);
    }
  }
  await tx.done;
}

// ==================== USER PROFILE ====================

/**
 * Save user profile for offline access
 * @param {Object} profile - User profile data
 */
export async function saveUserProfile(profile) {
  const db = await getDB();
  await db.put(STORES.USER_PROFILE, {
    id: 'current',
    ...profile,
    cachedAt: new Date().toISOString(),
  });
}

/**
 * Get cached user profile
 * @returns {Promise<Object|null>} - User profile or null
 */
export async function getUserProfile() {
  const db = await getDB();
  const profile = await db.get(STORES.USER_PROFILE, 'current');
  return profile || null;
}

/**
 * Clear user profile (on logout)
 */
export async function clearUserProfile() {
  const db = await getDB();
  await db.delete(STORES.USER_PROFILE, 'current');
}

// ==================== UTILITY FUNCTIONS ====================

/**
 * Check if we're online
 * @returns {boolean}
 */
export function isOnline() {
  return typeof navigator !== 'undefined' ? navigator.onLine : true;
}

/**
 * Clear all offline data (for logout)
 */
export async function clearAllOfflineData() {
  const db = await getDB();
  await Promise.all([
    db.clear(STORES.PENDING_REPORTS),
    db.clear(STORES.CACHED_DATA),
    db.clear(STORES.USER_PROFILE),
  ]);
}

/**
 * Get offline storage stats
 * @returns {Promise<Object>} - Storage statistics
 */
export async function getOfflineStorageStats() {
  const db = await getDB();
  const [pendingReports, cachedData] = await Promise.all([
    db.getAll(STORES.PENDING_REPORTS),
    db.getAll(STORES.CACHED_DATA),
  ]);

  return {
    pendingReportsCount: pendingReports.filter(r => r.status === 'pending').length,
    syncedReportsCount: pendingReports.filter(r => r.status === 'synced').length,
    failedReportsCount: pendingReports.filter(r => r.status === 'failed').length,
    cachedEntriesCount: cachedData.length,
  };
}

// Export store names for external use if needed
export { STORES };
