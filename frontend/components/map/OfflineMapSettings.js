'use client';

import { useState } from 'react';
import { Download, Trash2, MapPin, Loader2, CheckCircle, HardDrive, Wifi } from 'lucide-react';
import { useOfflineTiles } from '@/hooks/useOfflineTiles';
import { useNetworkStatus } from '@/hooks/useNetworkStatus';

/**
 * Component for managing offline map tile downloads
 */
const OfflineMapSettings = ({ className = '' }) => {
  const {
    isDownloading,
    progress,
    cacheSize,
    error,
    downloadTilesForArea,
    downloadForCurrentLocation,
    clearTileCache,
    estimateTileCount,
    estimateDownloadSize,
  } = useOfflineTiles();

  const { isOnline, isSlowConnection } = useNetworkStatus();

  const [radius, setRadius] = useState(100);
  const [customLocation, setCustomLocation] = useState({ lat: '', lng: '' });
  const [useCustomLocation, setUseCustomLocation] = useState(false);
  const [isClearing, setIsClearing] = useState(false);
  const [downloadComplete, setDownloadComplete] = useState(false);

  const estimatedTiles = estimateTileCount(radius);
  const estimatedSize = estimateDownloadSize(estimatedTiles);

  const handleDownload = async () => {
    setDownloadComplete(false);

    let success;
    if (useCustomLocation && customLocation.lat && customLocation.lng) {
      success = await downloadTilesForArea(
        { lat: parseFloat(customLocation.lat), lng: parseFloat(customLocation.lng) },
        radius
      );
    } else {
      success = await downloadForCurrentLocation(radius);
    }

    if (success && !isDownloading) {
      setDownloadComplete(true);
      setTimeout(() => setDownloadComplete(false), 5000);
    }
  };

  const handleClear = async () => {
    setIsClearing(true);
    await clearTileCache();
    setIsClearing(false);
  };

  const progressPercent = progress.total > 0
    ? Math.round(((progress.cached + progress.failed) / progress.total) * 100)
    : 0;

  return (
    <div className={`bg-slate-800/90 backdrop-blur-sm rounded-xl border border-slate-700 p-4 ${className}`}>
      <div className="flex items-center gap-3 mb-4">
        <div className="p-2 bg-cyan-500/20 rounded-lg">
          <HardDrive className="w-5 h-5 text-cyan-400" />
        </div>
        <div>
          <h3 className="font-semibold text-white">Offline Maps</h3>
          <p className="text-xs text-slate-400">Download map tiles for offline use</p>
        </div>
      </div>

      {/* Connection status */}
      <div className={`flex items-center gap-2 mb-4 p-2 rounded-lg ${isOnline ? 'bg-green-500/10' : 'bg-red-500/10'}`}>
        <Wifi className={`w-4 h-4 ${isOnline ? 'text-green-400' : 'text-red-400'}`} />
        <span className={`text-sm ${isOnline ? 'text-green-400' : 'text-red-400'}`}>
          {isOnline ? (isSlowConnection ? 'Slow connection' : 'Online') : 'Offline'}
        </span>
        {cacheSize.entries > 0 && (
          <span className="text-sm text-slate-400 ml-auto">
            {cacheSize.entries} cached items
          </span>
        )}
      </div>

      {/* Radius selector */}
      <div className="mb-4">
        <label className="block text-sm text-slate-300 mb-2">Download radius</label>
        <div className="flex gap-2">
          {[50, 100, 200].map((r) => (
            <button
              key={r}
              onClick={() => setRadius(r)}
              className={`flex-1 py-2 px-3 rounded-lg text-sm font-medium transition-colors ${
                radius === r
                  ? 'bg-cyan-600 text-white'
                  : 'bg-slate-700 text-slate-300 hover:bg-slate-600'
              }`}
            >
              {r} km
            </button>
          ))}
        </div>
        <p className="text-xs text-slate-500 mt-2">
          Est. {estimatedTiles.toLocaleString()} tiles (~{estimatedSize} MB)
        </p>
      </div>

      {/* Location selection */}
      <div className="mb-4">
        <div className="flex items-center gap-2 mb-2">
          <input
            type="checkbox"
            id="useCustomLocation"
            checked={useCustomLocation}
            onChange={(e) => setUseCustomLocation(e.target.checked)}
            className="rounded border-slate-600 bg-slate-700 text-cyan-500 focus:ring-cyan-500"
          />
          <label htmlFor="useCustomLocation" className="text-sm text-slate-300">
            Use custom location
          </label>
        </div>

        {useCustomLocation && (
          <div className="grid grid-cols-2 gap-2">
            <input
              type="number"
              step="0.0001"
              placeholder="Latitude"
              value={customLocation.lat}
              onChange={(e) => setCustomLocation({ ...customLocation, lat: e.target.value })}
              className="px-3 py-2 bg-slate-700 border border-slate-600 rounded-lg text-white text-sm placeholder-slate-400 focus:outline-none focus:border-cyan-500"
            />
            <input
              type="number"
              step="0.0001"
              placeholder="Longitude"
              value={customLocation.lng}
              onChange={(e) => setCustomLocation({ ...customLocation, lng: e.target.value })}
              className="px-3 py-2 bg-slate-700 border border-slate-600 rounded-lg text-white text-sm placeholder-slate-400 focus:outline-none focus:border-cyan-500"
            />
          </div>
        )}
      </div>

      {/* Download progress */}
      {isDownloading && (
        <div className="mb-4">
          <div className="flex items-center justify-between text-sm text-slate-300 mb-1">
            <span>Downloading tiles...</span>
            <span>{progressPercent}%</span>
          </div>
          <div className="w-full bg-slate-700 rounded-full h-2">
            <div
              className="bg-cyan-500 h-2 rounded-full transition-all duration-300"
              style={{ width: `${progressPercent}%` }}
            />
          </div>
          <div className="flex justify-between text-xs text-slate-500 mt-1">
            <span>{progress.cached} cached</span>
            {progress.failed > 0 && (
              <span className="text-amber-400">{progress.failed} failed</span>
            )}
            <span>{progress.total} total</span>
          </div>
        </div>
      )}

      {/* Success message */}
      {downloadComplete && !isDownloading && (
        <div className="mb-4 p-3 bg-green-500/10 border border-green-500/30 rounded-lg flex items-center gap-2">
          <CheckCircle className="w-5 h-5 text-green-400" />
          <span className="text-sm text-green-400">Download complete!</span>
        </div>
      )}

      {/* Error message */}
      {error && (
        <div className="mb-4 p-3 bg-red-500/10 border border-red-500/30 rounded-lg text-sm text-red-400">
          {error}
        </div>
      )}

      {/* Action buttons */}
      <div className="flex gap-2">
        <button
          onClick={handleDownload}
          disabled={isDownloading || !isOnline}
          className="flex-1 flex items-center justify-center gap-2 px-4 py-3 bg-cyan-600 hover:bg-cyan-500 disabled:bg-slate-700 disabled:cursor-not-allowed text-white font-medium rounded-lg transition-colors"
        >
          {isDownloading ? (
            <>
              <Loader2 className="w-4 h-4 animate-spin" />
              Downloading...
            </>
          ) : (
            <>
              {useCustomLocation ? (
                <MapPin className="w-4 h-4" />
              ) : (
                <Download className="w-4 h-4" />
              )}
              {useCustomLocation ? 'Download Area' : 'Download My Area'}
            </>
          )}
        </button>

        <button
          onClick={handleClear}
          disabled={isClearing || cacheSize.entries === 0}
          className="px-4 py-3 bg-slate-700 hover:bg-slate-600 disabled:opacity-50 disabled:cursor-not-allowed text-slate-300 rounded-lg transition-colors"
          title="Clear cached tiles"
        >
          {isClearing ? (
            <Loader2 className="w-4 h-4 animate-spin" />
          ) : (
            <Trash2 className="w-4 h-4" />
          )}
        </button>
      </div>

      <p className="text-xs text-slate-500 mt-3 text-center">
        Tiles are cached for offline viewing. Re-download to update.
      </p>
    </div>
  );
};

export default OfflineMapSettings;
