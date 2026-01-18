'use client';

import { useEffect } from 'react';
import { useMap } from 'react-leaflet';

export function StormSurgeLayer({ data, intensity = 0.5 }) {
  const map = useMap();

  useEffect(() => {
    // Check if running in browser
    if (typeof window === 'undefined') return;
    if (!data || !data.surgeGrid || data.surgeGrid.length === 0) return;

    // Dynamic imports for browser-only libraries
    const L = require('leaflet');
    require('leaflet.heat');

    // Convert surge data to heatmap format [lat, lng, intensity]
    const heatData = data.surgeGrid.map(point => [
      point.lat,
      point.lon,
      point.surge // 0 to 1
    ]);

    // Create heatmap layer
    const heat = L.heatLayer(heatData, {
      radius: 25,
      blur: 35,
      maxZoom: 10,
      max: 1.0,
      gradient: {
        0.0: '#0000ff',    // Blue - no surge
        0.175: '#00ffff',  // Cyan
        0.35: '#00ff00',   // Green
        0.525: '#ffff00',  // Yellow
        0.7: '#ff0000'     // Red - high surge
      }
    }).addTo(map);

    // Draw cyclone track
    if (data.cyclone && data.cyclone.track) {
      const trackCoords = data.cyclone.track.map(point => [point.lat, point.lon]);

      // Draw track line
      const trackLine = L.polyline(trackCoords, {
        color: '#000000',
        weight: 3,
        opacity: 0.8,
        dashArray: '10, 10'
      }).addTo(map);

      // Add markers for each position
      data.cyclone.track.forEach((point, index) => {
        const isLatest = index === data.cyclone.track.length - 1;

        const icon = L.divIcon({
          html: `<div style="
            background: ${isLatest ? '#ff0000' : '#000000'};
            width: ${isLatest ? '20px' : '12px'};
            height: ${isLatest ? '20px' : '12px'};
            border-radius: 50%;
            border: 3px solid white;
            box-shadow: 0 0 5px rgba(0,0,0,0.5);
          "></div>`,
          className: 'cyclone-marker',
          iconSize: [isLatest ? 20 : 12, isLatest ? 20 : 12],
          iconAnchor: [isLatest ? 10 : 6, isLatest ? 10 : 6]
        });

        L.marker([point.lat, point.lon], { icon })
          .bindPopup(`
            <div class="p-2">
              <h3 class="font-bold text-sm mb-2">${data.cyclone.name}</h3>
              <p class="text-xs"><strong>Intensity:</strong> ${point.intensity}</p>
              <p class="text-xs"><strong>Time:</strong> ${new Date(point.time).toLocaleString()}</p>
              ${isLatest ? `
                <p class="text-xs mt-2"><strong>Max Wind:</strong> ${data.cyclone.maxWindSpeed} km/h</p>
                <p class="text-xs"><strong>Pressure:</strong> ${data.cyclone.centralPressure} hPa</p>
              ` : ''}
            </div>
          `)
          .addTo(map);
      });

      // Cleanup function
      return () => {
        map.removeLayer(heat);
        map.removeLayer(trackLine);
      };
    }

    return () => {
      map.removeLayer(heat);
    };
  }, [map, data, intensity]);

  return null;
}
