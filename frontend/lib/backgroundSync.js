import {
  getPendingReports,
  updatePendingReportStatus,
  deletePendingReport,
  isOnline,
} from './offlineStorage';
import api from './api';

// Maximum retry attempts before marking as failed
const MAX_RETRIES = 3;

// Sync interval in milliseconds (30 seconds)
const SYNC_INTERVAL = 30000;

let syncInProgress = false;
let syncInterval = null;

/**
 * Dispatch custom event for sync status updates
 */
function dispatchSyncEvent(eventName, detail = {}) {
  if (typeof window !== 'undefined') {
    window.dispatchEvent(new CustomEvent(eventName, { detail }));
  }
}

/**
 * Submit a single report to the server
 * @param {Object} report - The pending report to submit
 * @returns {Promise<boolean>} - Success status
 */
async function submitReport(report) {
  try {
    // Prepare the form data
    const formData = new FormData();

    // Add all report fields
    formData.append('hazard_type', report.hazard_type);
    formData.append('description', report.description);
    formData.append('latitude', report.latitude);
    formData.append('longitude', report.longitude);
    formData.append('location_description', report.location_description || '');
    formData.append('severity', report.severity);

    // If there's a photo stored as base64, convert back to file
    if (report.photo_base64) {
      const response = await fetch(report.photo_base64);
      const blob = await response.blob();
      const file = new File([blob], 'hazard_photo.jpg', { type: 'image/jpeg' });
      formData.append('photo', file);
    }

    // Submit to the API
    const apiResponse = await api.post('/hazards', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });

    return apiResponse.status === 200 || apiResponse.status === 201;
  } catch (error) {
    console.error('Failed to submit report:', error);
    throw error;
  }
}

/**
 * Sync all pending reports to the server
 * @returns {Promise<Object>} - Sync results
 */
export async function syncPendingReports() {
  if (!isOnline()) {
    console.log('Offline - skipping sync');
    return { synced: 0, failed: 0, pending: 0 };
  }

  if (syncInProgress) {
    console.log('Sync already in progress');
    return { synced: 0, failed: 0, pending: 0 };
  }

  syncInProgress = true;
  dispatchSyncEvent('sync-start');

  const results = {
    synced: 0,
    failed: 0,
    pending: 0,
  };

  try {
    const pendingReports = await getPendingReports();
    results.pending = pendingReports.length;

    if (pendingReports.length === 0) {
      console.log('No pending reports to sync');
      return results;
    }

    console.log(`Syncing ${pendingReports.length} pending reports...`);

    for (const report of pendingReports) {
      try {
        // Mark as syncing
        await updatePendingReportStatus(report.id, 'syncing');

        // Submit the report
        await submitReport(report);

        // Success - delete from pending
        await deletePendingReport(report.id);
        results.synced++;

        console.log(`Successfully synced report ${report.id}`);
        dispatchSyncEvent('report-synced', { reportId: report.id });
      } catch (error) {
        const errorMessage = error.response?.data?.detail || error.message;

        // Check if we've exceeded max retries
        if ((report.retryCount || 0) >= MAX_RETRIES - 1) {
          await updatePendingReportStatus(report.id, 'failed', errorMessage);
          results.failed++;
          console.error(`Report ${report.id} failed permanently after ${MAX_RETRIES} retries`);
        } else {
          // Mark back as pending for retry
          await updatePendingReportStatus(report.id, 'pending', errorMessage);
          console.warn(`Report ${report.id} failed, will retry. Error: ${errorMessage}`);
        }
      }
    }

    console.log(`Sync complete: ${results.synced} synced, ${results.failed} failed`);
  } catch (error) {
    console.error('Sync error:', error);
  } finally {
    syncInProgress = false;
    dispatchSyncEvent('sync-complete', results);
  }

  return results;
}

/**
 * Start automatic background sync
 */
export function startBackgroundSync() {
  if (typeof window === 'undefined') return;

  // Clear any existing interval
  stopBackgroundSync();

  // Start periodic sync
  syncInterval = setInterval(() => {
    if (isOnline()) {
      syncPendingReports();
    }
  }, SYNC_INTERVAL);

  // Also sync immediately when coming online
  window.addEventListener('online', handleOnline);

  // Initial sync if online
  if (isOnline()) {
    setTimeout(syncPendingReports, 5000); // Wait 5s for app to initialize
  }

  console.log('Background sync started');
}

/**
 * Stop automatic background sync
 */
export function stopBackgroundSync() {
  if (syncInterval) {
    clearInterval(syncInterval);
    syncInterval = null;
  }
  if (typeof window !== 'undefined') {
    window.removeEventListener('online', handleOnline);
  }
  console.log('Background sync stopped');
}

/**
 * Handle coming back online
 */
function handleOnline() {
  console.log('Back online - triggering sync');
  // Wait a moment for connection to stabilize
  setTimeout(syncPendingReports, 2000);
}

/**
 * Register service worker sync (if supported)
 */
export async function registerPeriodicSync() {
  if (typeof window === 'undefined' || !('serviceWorker' in navigator)) {
    return false;
  }

  try {
    const registration = await navigator.serviceWorker.ready;

    // Check if periodic background sync is supported
    if ('periodicSync' in registration) {
      const status = await navigator.permissions.query({
        name: 'periodic-background-sync',
      });

      if (status.state === 'granted') {
        await registration.periodicSync.register('sync-reports', {
          minInterval: 60 * 60 * 1000, // 1 hour minimum
        });
        console.log('Periodic background sync registered');
        return true;
      }
    }

    // Fallback to one-time sync if available
    if ('sync' in registration) {
      await registration.sync.register('sync-reports');
      console.log('One-time sync registered');
      return true;
    }
  } catch (error) {
    console.error('Failed to register background sync:', error);
  }

  return false;
}

/**
 * Manual trigger for sync (e.g., from a button)
 */
export async function triggerManualSync() {
  if (!isOnline()) {
    return { success: false, message: 'You are offline' };
  }

  const results = await syncPendingReports();
  return {
    success: true,
    message: `Synced ${results.synced} reports`,
    results,
  };
}

/**
 * Check sync status
 */
export function isSyncInProgress() {
  return syncInProgress;
}

export default {
  syncPendingReports,
  startBackgroundSync,
  stopBackgroundSync,
  registerPeriodicSync,
  triggerManualSync,
  isSyncInProgress,
};
