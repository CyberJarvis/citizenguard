'use client';

import { useState, useEffect } from 'react';
import { getPendingReportsCount } from '@/lib/offlineStorage';

export default function OfflineIndicator() {
  const [isOnline, setIsOnline] = useState(true);
  const [pendingCount, setPendingCount] = useState(0);
  const [showBanner, setShowBanner] = useState(false);
  const [isSyncing, setIsSyncing] = useState(false);

  useEffect(() => {
    // Set initial state
    setIsOnline(navigator.onLine);
    setShowBanner(!navigator.onLine);

    const handleOnline = () => {
      setIsOnline(true);
      // Show "Back online" message briefly
      setShowBanner(true);
      setTimeout(() => {
        setShowBanner(false);
      }, 3000);
    };

    const handleOffline = () => {
      setIsOnline(false);
      setShowBanner(true);
    };

    window.addEventListener('online', handleOnline);
    window.addEventListener('offline', handleOffline);

    // Listen for sync events
    const handleSyncStart = () => setIsSyncing(true);
    const handleSyncComplete = () => {
      setIsSyncing(false);
      loadPendingCount();
    };

    window.addEventListener('sync-start', handleSyncStart);
    window.addEventListener('sync-complete', handleSyncComplete);

    return () => {
      window.removeEventListener('online', handleOnline);
      window.removeEventListener('offline', handleOffline);
      window.removeEventListener('sync-start', handleSyncStart);
      window.removeEventListener('sync-complete', handleSyncComplete);
    };
  }, []);

  // Load pending count
  const loadPendingCount = async () => {
    try {
      const count = await getPendingReportsCount();
      setPendingCount(count);
    } catch (error) {
      console.error('Failed to load pending count:', error);
    }
  };

  useEffect(() => {
    loadPendingCount();
    // Refresh count periodically
    const interval = setInterval(loadPendingCount, 10000);
    return () => clearInterval(interval);
  }, []);

  if (!showBanner && pendingCount === 0) return null;

  return (
    <div className="fixed bottom-4 left-4 right-4 md:left-auto md:right-4 md:w-auto z-50">
      {/* Offline Banner */}
      {showBanner && (
        <div
          className={`mb-2 px-4 py-3 rounded-lg shadow-lg flex items-center justify-between ${
            isOnline
              ? 'bg-green-500 text-white'
              : 'bg-amber-500 text-white'
          }`}
        >
          <div className="flex items-center">
            {isOnline ? (
              <>
                <svg className="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                </svg>
                <span className="font-medium">Back online!</span>
              </>
            ) : (
              <>
                <svg className="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M18.364 5.636a9 9 0 010 12.728m0 0l-2.829-2.829m2.829 2.829L21 21M15.536 8.464a5 5 0 010 7.072m0 0l-2.829-2.829m-4.243 2.829a5 5 0 01-7.072-7.072m7.072 7.072L9 12m0 0L6.172 9.172m0 0a5 5 0 017.071-7.071M9 12l2.829 2.829" />
                </svg>
                <span className="font-medium">You're offline</span>
              </>
            )}
          </div>
          {!isOnline && (
            <button
              onClick={() => setShowBanner(false)}
              className="ml-4 text-white/80 hover:text-white"
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          )}
        </div>
      )}

      {/* Pending Sync Indicator */}
      {pendingCount > 0 && (
        <div className="px-4 py-3 rounded-lg shadow-lg bg-[#0d4a6f] text-white flex items-center">
          {isSyncing ? (
            <>
              <svg className="w-5 h-5 mr-2 animate-spin" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
              </svg>
              <span className="font-medium">Syncing reports...</span>
            </>
          ) : (
            <>
              <svg className="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              <span className="font-medium">
                {pendingCount} report{pendingCount > 1 ? 's' : ''} pending sync
              </span>
            </>
          )}
        </div>
      )}
    </div>
  );
}
