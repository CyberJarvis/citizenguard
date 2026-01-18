'use client';

import { useState, useCallback, useEffect, useRef } from 'react';

/**
 * Hook for managing offline map tiles
 * Communicates with service worker to cache tiles for offline use
 */
export function useOfflineTiles() {
  const [isDownloading, setIsDownloading] = useState(false);
  const [progress, setProgress] = useState({ cached: 0, failed: 0, total: 0 });
  const [cacheSize, setCacheSize] = useState({ entries: 0 });
  const [error, setError] = useState(null);

  const swRef = useRef(null);

  // Listen for service worker messages
  useEffect(() => {
    if (typeof navigator === 'undefined' || !('serviceWorker' in navigator)) {
      return;
    }

    const handleMessage = (event) => {
      const { type, payload } = event.data || {};

      switch (type) {
        case 'TILE_CACHE_PROGRESS':
          setProgress(payload);
          break;
        case 'TILE_CACHE_COMPLETE':
          setProgress(payload);
          setIsDownloading(false);
          break;
        case 'CACHE_SIZE':
          setCacheSize(payload);
          break;
      }
    };

    navigator.serviceWorker.addEventListener('message', handleMessage);

    // Get initial cache size
    getCacheSize();

    return () => {
      navigator.serviceWorker.removeEventListener('message', handleMessage);
    };
  }, []);

  /**
   * Download map tiles for a specific area
   * @param {Object} center - { lat, lng } center point
   * @param {number} radiusKm - Radius in kilometers (default: 100)
   * @param {Object} options - Additional options
   */
  const downloadTilesForArea = useCallback(async (center, radiusKm = 100, options = {}) => {
    if (typeof navigator === 'undefined' || !('serviceWorker' in navigator)) {
      setError('Service worker not supported');
      return false;
    }

    try {
      setError(null);
      setIsDownloading(true);
      setProgress({ cached: 0, failed: 0, total: 0 });

      const registration = await navigator.serviceWorker.ready;

      if (!registration.active) {
        throw new Error('Service worker not active');
      }

      // Send message to service worker to start caching
      registration.active.postMessage({
        type: 'CACHE_TILES',
        payload: {
          center,
          radiusKm,
          minZoom: options.minZoom || 5,
          maxZoom: options.maxZoom || 12,
          tileServer: options.tileServer || 'https://a.tile.openstreetmap.org',
        },
      });

      return true;
    } catch (err) {
      setError(err.message);
      setIsDownloading(false);
      return false;
    }
  }, []);

  /**
   * Download tiles for current location
   * @param {number} radiusKm - Radius in kilometers
   */
  const downloadForCurrentLocation = useCallback(async (radiusKm = 100) => {
    if (!navigator.geolocation) {
      setError('Geolocation not supported');
      return false;
    }

    return new Promise((resolve) => {
      navigator.geolocation.getCurrentPosition(
        async (position) => {
          const result = await downloadTilesForArea(
            { lat: position.coords.latitude, lng: position.coords.longitude },
            radiusKm
          );
          resolve(result);
        },
        (err) => {
          setError(`Location error: ${err.message}`);
          resolve(false);
        },
        { enableHighAccuracy: true, timeout: 10000 }
      );
    });
  }, [downloadTilesForArea]);

  /**
   * Clear all cached tiles
   */
  const clearTileCache = useCallback(async () => {
    if (typeof navigator === 'undefined' || !('serviceWorker' in navigator)) {
      return false;
    }

    try {
      const registration = await navigator.serviceWorker.ready;
      if (registration.active) {
        registration.active.postMessage({ type: 'CLEAR_TILE_CACHE' });
        setProgress({ cached: 0, failed: 0, total: 0 });
        setCacheSize({ entries: 0 });
        return true;
      }
      return false;
    } catch (err) {
      setError(err.message);
      return false;
    }
  }, []);

  /**
   * Get current cache size
   */
  const getCacheSize = useCallback(async () => {
    if (typeof navigator === 'undefined' || !('serviceWorker' in navigator)) {
      return;
    }

    try {
      const registration = await navigator.serviceWorker.ready;
      if (registration.active) {
        const messageChannel = new MessageChannel();
        messageChannel.port1.onmessage = (event) => {
          if (event.data.type === 'CACHE_SIZE') {
            setCacheSize(event.data.payload);
          }
        };
        registration.active.postMessage({ type: 'GET_CACHE_SIZE' }, [messageChannel.port2]);
      }
    } catch (err) {
      console.error('Failed to get cache size:', err);
    }
  }, []);

  /**
   * Calculate estimated tile count for an area
   * Useful for showing user before download
   */
  const estimateTileCount = useCallback((radiusKm, minZoom = 5, maxZoom = 12) => {
    let totalTiles = 0;

    for (let zoom = minZoom; zoom <= maxZoom; zoom++) {
      // Approximate tiles in radius at each zoom level
      const tilesPerDegree = Math.pow(2, zoom) / 360;
      const degreesRadius = radiusKm / 111; // ~111km per degree
      const tilesAcross = Math.ceil(degreesRadius * 2 * tilesPerDegree);
      totalTiles += tilesAcross * tilesAcross;
    }

    return totalTiles;
  }, []);

  /**
   * Estimate download size in MB
   */
  const estimateDownloadSize = useCallback((tileCount) => {
    // Average tile size is ~15KB
    return Math.round((tileCount * 15) / 1024);
  }, []);

  return {
    // State
    isDownloading,
    progress,
    cacheSize,
    error,

    // Actions
    downloadTilesForArea,
    downloadForCurrentLocation,
    clearTileCache,
    getCacheSize,

    // Utilities
    estimateTileCount,
    estimateDownloadSize,
  };
}

export default useOfflineTiles;
