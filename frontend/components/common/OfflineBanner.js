'use client';

import { useState } from 'react';
import { WifiOff, RefreshCw, CloudOff, CheckCircle, X, AlertTriangle } from 'lucide-react';
import { useNetworkStatus } from '@/hooks/useNetworkStatus';

/**
 * Banner component that shows offline status and pending sync items
 */
const OfflineBanner = ({ className = '' }) => {
  const {
    isOnline,
    wasOffline,
    isSlowConnection,
    pendingCount,
    hasPending,
    lastSyncFormatted,
    isSyncing,
    syncError,
    triggerSync,
  } = useNetworkStatus();

  const [dismissed, setDismissed] = useState(false);
  const [showSuccess, setShowSuccess] = useState(false);

  // Handle manual sync
  const handleSync = async () => {
    const result = await triggerSync();
    if (result.success) {
      setShowSuccess(true);
      setTimeout(() => setShowSuccess(false), 3000);
    }
  };

  // Don't show if online with no pending items and not recently offline
  if (isOnline && !hasPending && !wasOffline && !showSuccess) {
    return null;
  }

  // If dismissed, only show again if status changes
  if (dismissed && isOnline && !hasPending) {
    return null;
  }

  // Success message after sync
  if (showSuccess && isOnline && !hasPending) {
    return (
      <div className={`bg-green-500/90 backdrop-blur-sm text-white px-4 py-2 flex items-center justify-center gap-2 text-sm ${className}`}>
        <CheckCircle className="w-4 h-4" />
        <span>All items synced successfully!</span>
        <button
          onClick={() => setShowSuccess(false)}
          className="ml-2 p-1 hover:bg-white/10 rounded"
        >
          <X className="w-4 h-4" />
        </button>
      </div>
    );
  }

  // Offline banner
  if (!isOnline) {
    return (
      <div className={`bg-slate-800 backdrop-blur-sm text-white px-4 py-3 ${className}`}>
        <div className="flex items-center justify-between max-w-6xl mx-auto">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-red-500/20 rounded-lg">
              <WifiOff className="w-5 h-5 text-red-400" />
            </div>
            <div>
              <p className="font-medium">You're offline</p>
              <p className="text-sm text-slate-400">
                {hasPending
                  ? `${pendingCount} item${pendingCount > 1 ? 's' : ''} queued for sync`
                  : 'Cached content available'}
              </p>
            </div>
          </div>
          <div className="text-right text-sm text-slate-400">
            <span>Last sync: {lastSyncFormatted}</span>
          </div>
        </div>
      </div>
    );
  }

  // Slow connection warning
  if (isSlowConnection) {
    return (
      <div className={`bg-amber-500/90 backdrop-blur-sm text-amber-950 px-4 py-2 flex items-center justify-center gap-2 text-sm ${className}`}>
        <AlertTriangle className="w-4 h-4" />
        <span>Slow connection detected. Some features may be delayed.</span>
        <button
          onClick={() => setDismissed(true)}
          className="ml-2 p-1 hover:bg-black/10 rounded"
        >
          <X className="w-4 h-4" />
        </button>
      </div>
    );
  }

  // Online with pending items banner
  if (hasPending) {
    return (
      <div className={`bg-cyan-600/90 backdrop-blur-sm text-white px-4 py-3 ${className}`}>
        <div className="flex items-center justify-between max-w-6xl mx-auto">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-white/10 rounded-lg">
              <CloudOff className="w-5 h-5" />
            </div>
            <div>
              <p className="font-medium">
                {pendingCount} pending item{pendingCount > 1 ? 's' : ''} to sync
              </p>
              <p className="text-sm text-cyan-100">
                Items queued while offline are ready to upload
              </p>
            </div>
          </div>
          <div className="flex items-center gap-3">
            {syncError && (
              <span className="text-sm text-red-200">{syncError}</span>
            )}
            <button
              onClick={handleSync}
              disabled={isSyncing}
              className="flex items-center gap-2 px-4 py-2 bg-white/20 hover:bg-white/30 disabled:opacity-50 rounded-lg font-medium transition-colors"
            >
              <RefreshCw className={`w-4 h-4 ${isSyncing ? 'animate-spin' : ''}`} />
              {isSyncing ? 'Syncing...' : 'Sync Now'}
            </button>
            <button
              onClick={() => setDismissed(true)}
              className="p-2 hover:bg-white/10 rounded"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>
    );
  }

  return null;
};

export default OfflineBanner;
