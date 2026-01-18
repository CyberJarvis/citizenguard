'use client';

import { useState, useEffect, useCallback, useRef } from 'react';
import { getPendingCount, syncPending } from '@/lib/offlineQueue';

/**
 * Hook for monitoring network status and managing offline queue sync
 */
export function useNetworkStatus() {
  const [isOnline, setIsOnline] = useState(true);
  const [wasOffline, setWasOffline] = useState(false);
  const [connectionType, setConnectionType] = useState('unknown');
  const [isSlowConnection, setIsSlowConnection] = useState(false);
  const [pendingCount, setPendingCount] = useState(0);
  const [lastSyncTime, setLastSyncTime] = useState(null);
  const [isSyncing, setIsSyncing] = useState(false);
  const [syncError, setSyncError] = useState(null);

  const syncTimeoutRef = useRef(null);

  // Update pending count
  const updatePendingCount = useCallback(async () => {
    try {
      const count = await getPendingCount();
      setPendingCount(count);
    } catch (err) {
      console.error('Failed to get pending count:', err);
    }
  }, []);

  // Manual sync trigger
  const triggerSync = useCallback(async () => {
    if (!isOnline || isSyncing) return { success: false };

    setIsSyncing(true);
    setSyncError(null);

    try {
      const result = await syncPending();
      if (result.success) {
        setLastSyncTime(new Date());
        await updatePendingCount();
      }
      return result;
    } catch (err) {
      setSyncError(err.message);
      return { success: false, error: err.message };
    } finally {
      setIsSyncing(false);
    }
  }, [isOnline, isSyncing, updatePendingCount]);

  // Handle coming back online
  const handleOnline = useCallback(() => {
    setIsOnline(true);

    if (wasOffline) {
      // Auto-sync after a short delay when coming back online
      syncTimeoutRef.current = setTimeout(() => {
        triggerSync();
      }, 2000);
    }
  }, [wasOffline, triggerSync]);

  // Handle going offline
  const handleOffline = useCallback(() => {
    setIsOnline(false);
    setWasOffline(true);

    if (syncTimeoutRef.current) {
      clearTimeout(syncTimeoutRef.current);
    }
  }, []);

  // Update connection info
  const updateConnectionInfo = useCallback(() => {
    if (typeof navigator === 'undefined') return;

    const connection = navigator.connection || navigator.mozConnection || navigator.webkitConnection;

    if (connection) {
      setConnectionType(connection.effectiveType || 'unknown');

      // Consider slow if 2g or slow-2g, or if downlink is very low
      const isSlow =
        connection.effectiveType === 'slow-2g' ||
        connection.effectiveType === '2g' ||
        (connection.downlink && connection.downlink < 0.5);

      setIsSlowConnection(isSlow);
    }
  }, []);

  // Initialize and set up listeners
  useEffect(() => {
    if (typeof window === 'undefined') return;

    // Set initial state
    setIsOnline(navigator.onLine);
    updateConnectionInfo();
    updatePendingCount();

    // Get last sync time from storage
    const stored = localStorage.getItem('lastOfflineSync');
    if (stored) {
      setLastSyncTime(new Date(stored));
    }

    // Add event listeners
    window.addEventListener('online', handleOnline);
    window.addEventListener('offline', handleOffline);

    // Connection change listener
    const connection = navigator.connection || navigator.mozConnection || navigator.webkitConnection;
    if (connection) {
      connection.addEventListener('change', updateConnectionInfo);
    }

    // Listen for service worker sync messages
    if ('serviceWorker' in navigator) {
      navigator.serviceWorker.addEventListener('message', (event) => {
        const { type } = event.data || {};
        if (type === 'SOS_SYNCED' || type === 'REPORT_SYNCED') {
          updatePendingCount();
        }
      });
    }

    // Periodic pending count update
    const interval = setInterval(updatePendingCount, 30000);

    return () => {
      window.removeEventListener('online', handleOnline);
      window.removeEventListener('offline', handleOffline);

      if (connection) {
        connection.removeEventListener('change', updateConnectionInfo);
      }

      if (syncTimeoutRef.current) {
        clearTimeout(syncTimeoutRef.current);
      }

      clearInterval(interval);
    };
  }, [handleOnline, handleOffline, updateConnectionInfo, updatePendingCount]);

  // Format last sync time for display
  const formatLastSync = useCallback(() => {
    if (!lastSyncTime) return 'Never';

    const now = new Date();
    const diff = now - lastSyncTime;
    const minutes = Math.floor(diff / 60000);
    const hours = Math.floor(diff / 3600000);

    if (minutes < 1) return 'Just now';
    if (minutes < 60) return `${minutes}m ago`;
    if (hours < 24) return `${hours}h ago`;
    return lastSyncTime.toLocaleDateString();
  }, [lastSyncTime]);

  return {
    // Status
    isOnline,
    wasOffline,
    connectionType,
    isSlowConnection,

    // Queue
    pendingCount,
    hasPending: pendingCount > 0,

    // Sync
    lastSyncTime,
    lastSyncFormatted: formatLastSync(),
    isSyncing,
    syncError,

    // Actions
    triggerSync,
    updatePendingCount,
  };
}

export default useNetworkStatus;
