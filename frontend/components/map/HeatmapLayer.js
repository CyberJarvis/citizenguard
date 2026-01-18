'use client';

import { useEffect, useRef } from 'react';
import { useMap } from 'react-leaflet';

// Heatmap gradient configuration - Ocean themed
const HEATMAP_GRADIENT = {
  0.0: '#1a365d', // Deep blue (low)
  0.2: '#2b6cb0', // Blue
  0.4: '#38a169', // Green
  0.6: '#ecc94b', // Yellow
  0.8: '#ed8936', // Orange
  1.0: '#e53e3e', // Red (critical)
};

/**
 * HeatmapLayer - Leaflet heatmap visualization
 * Shows density and intensity of reports/alerts
 */
export function HeatmapLayer({
  points = [],
  radius = 25,
  blur = 30,
  maxZoom = 12,
  opacity = 0.7,
  gradient = HEATMAP_GRADIENT,
}) {
  const map = useMap();
  const heatLayerRef = useRef(null);
  const initAttemptRef = useRef(0);

  useEffect(() => {
    // Only run on client side
    if (typeof window === 'undefined') return;

    // Clean up existing layer
    if (heatLayerRef.current) {
      try {
        map.removeLayer(heatLayerRef.current);
      } catch (e) {
        // Ignore removal errors
      }
      heatLayerRef.current = null;
    }

    // Don't render if no points
    if (!points || points.length === 0) return;

    // Import leaflet.heat dynamically
    const initHeatmap = async () => {
      try {
        // Check if map is fully initialized
        if (!map || !map._loaded) {
          // Retry after a delay if map is not ready
          if (initAttemptRef.current < 10) {
            initAttemptRef.current++;
            setTimeout(initHeatmap, 200);
          }
          return;
        }

        // Check if map container has valid dimensions
        const container = map.getContainer?.();
        if (!container || container.clientHeight === 0 || container.clientWidth === 0) {
          // Retry after a delay if map is not ready
          if (initAttemptRef.current < 10) {
            initAttemptRef.current++;
            setTimeout(initHeatmap, 200);
          }
          return;
        }

        // Check if map panes are ready (prevents appendChild error)
        const overlayPane = map.getPane?.('overlayPane');
        if (!overlayPane) {
          if (initAttemptRef.current < 10) {
            initAttemptRef.current++;
            setTimeout(initHeatmap, 200);
          }
          return;
        }

        // Reset attempt counter on success
        initAttemptRef.current = 0;

        // Ensure leaflet is available
        const L = (await import('leaflet')).default;

        // Import the heat plugin
        await import('leaflet.heat');

        // Format points for heatmap: [lat, lng, intensity]
        const heatPoints = points.map((point) => {
          if (Array.isArray(point)) {
            return [point[0], point[1], point[2] || 0.5];
          }
          return [
            point.lat || point.latitude,
            point.lng || point.lon || point.longitude,
            point.intensity || point.weight || 0.5,
          ];
        }).filter((p) => p[0] && p[1] && !isNaN(p[0]) && !isNaN(p[1])); // Filter out invalid points

        if (heatPoints.length === 0) return;

        // Create heatmap layer
        const heatLayer = L.heatLayer(heatPoints, {
          radius,
          blur,
          maxZoom,
          gradient,
          max: 1.0,
          minOpacity: 0.1,
        });

        // Add to map (opacity is set via canvas style)
        heatLayer.addTo(map);
        heatLayerRef.current = heatLayer;
      } catch (error) {
        console.error('Error initializing heatmap:', error);
      }
    };

    // Delay initialization to ensure map is ready
    const timeoutId = setTimeout(initHeatmap, 100);

    // Cleanup on unmount
    return () => {
      clearTimeout(timeoutId);
      if (heatLayerRef.current) {
        try {
          map.removeLayer(heatLayerRef.current);
        } catch (e) {
          // Ignore removal errors
        }
        heatLayerRef.current = null;
      }
    };
  }, [map, points, radius, blur, maxZoom, gradient]);

  // Update opacity when it changes
  useEffect(() => {
    if (heatLayerRef.current) {
      // Heatmap doesn't have direct opacity control, so we recreate
      const canvas = map.getPane('overlayPane')?.querySelector('canvas');
      if (canvas) {
        canvas.style.opacity = opacity;
      }
    }
  }, [map, opacity]);

  return null;
}

export default HeatmapLayer;
