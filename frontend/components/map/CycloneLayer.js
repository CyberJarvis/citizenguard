'use client';

import { useEffect, useRef, useMemo } from 'react';
import { useMap } from 'react-leaflet';

// Cyclone category configuration (Saffir-Simpson scale adapted for Bay of Bengal)
const CYCLONE_CATEGORIES = {
  depression: { color: '#3b82f6', minWind: 0, maxWind: 33, label: 'Depression' },
  deep_depression: { color: '#06b6d4', minWind: 34, maxWind: 47, label: 'Deep Depression' },
  cyclonic_storm: { color: '#22c55e', minWind: 48, maxWind: 63, label: 'Cyclonic Storm' },
  severe_cyclonic: { color: '#eab308', minWind: 64, maxWind: 89, label: 'Severe Cyclonic' },
  very_severe: { color: '#f97316', minWind: 90, maxWind: 119, label: 'Very Severe' },
  extremely_severe: { color: '#ef4444', minWind: 120, maxWind: 166, label: 'Extremely Severe' },
  super_cyclone: { color: '#dc2626', minWind: 167, maxWind: 999, label: 'Super Cyclone' },
};

// Storm surge height colors
const SURGE_COLORS = {
  0.5: '#00ffff',   // Cyan - 0-0.5m
  1.0: '#00ff00',   // Green - 0.5-1m
  1.5: '#ffff00',   // Yellow - 1-1.5m
  2.0: '#ffa500',   // Orange - 1.5-2m
  3.0: '#ff0000',   // Red - 2-3m
  5.0: '#8b0000',   // Dark Red - 3-5m
  10.0: '#4b0082',  // Indigo - 5m+
};

// Get cyclone category from wind speed
const getCycloneCategory = (windSpeed) => {
  for (const [key, cat] of Object.entries(CYCLONE_CATEGORIES)) {
    if (windSpeed >= cat.minWind && windSpeed <= cat.maxWind) {
      return { key, ...cat };
    }
  }
  return { key: 'depression', ...CYCLONE_CATEGORIES.depression };
};

// Get surge color based on height
const getSurgeColor = (height) => {
  const thresholds = Object.keys(SURGE_COLORS).map(Number).sort((a, b) => a - b);
  for (const threshold of thresholds) {
    if (height <= threshold) return SURGE_COLORS[threshold];
  }
  return SURGE_COLORS[10.0];
};

/**
 * CycloneLayer - INCOIS-style cyclone and storm surge visualization
 * Features:
 * - Animated spiral cyclone symbol
 * - Track line with forecast cone
 * - Storm surge contours
 * - Wind radii circles
 * - Real-time position updates
 */
export function CycloneLayer({
  cycloneData = null,
  surgeData = null,
  showTrack = true,
  showSurge = true,
  showWindRadii = true,
  showForecastCone = true,
  animateCyclone = true,
  opacity = 0.8,
}) {
  const map = useMap();
  const layersRef = useRef([]);
  const animationRef = useRef(null);

  // Cleanup layers
  const clearLayers = () => {
    layersRef.current.forEach(layer => {
      try {
        map.removeLayer(layer);
      } catch (e) {}
    });
    layersRef.current = [];
    if (animationRef.current) {
      cancelAnimationFrame(animationRef.current);
    }
  };

  useEffect(() => {
    if (typeof window === 'undefined') return;
    if (!cycloneData) return;

    const L = require('leaflet');
    clearLayers();

    const { currentPosition, track, forecast, windRadii, name, maxWindSpeed, centralPressure, movementSpeed, movementDirection } = cycloneData;
    const category = getCycloneCategory(maxWindSpeed || 0);

    // 1. Draw Storm Surge Contours
    if (showSurge && surgeData && surgeData.contours) {
      surgeData.contours.forEach(contour => {
        const color = getSurgeColor(contour.height);
        const polygon = L.polygon(contour.coordinates, {
          color: color,
          fillColor: color,
          fillOpacity: 0.3 * opacity,
          weight: 2,
          opacity: 0.8,
        });
        polygon.bindTooltip(`Storm Surge: ${contour.height}m`, { sticky: true });
        polygon.addTo(map);
        layersRef.current.push(polygon);
      });
    }

    // 2. Draw Forecast Uncertainty Cone
    if (showForecastCone && forecast && forecast.length > 0) {
      const coneCoords = [];
      const leftSide = [];
      const rightSide = [];

      forecast.forEach((point, index) => {
        const uncertainty = 50 + (index * 30); // Increasing uncertainty km
        const lat = point.lat;
        const lon = point.lon;

        // Calculate offset points for cone
        const latOffset = uncertainty / 111; // ~111km per degree
        const lonOffset = uncertainty / (111 * Math.cos(lat * Math.PI / 180));

        leftSide.push([lat + latOffset * 0.7, lon - lonOffset]);
        rightSide.unshift([lat - latOffset * 0.7, lon + lonOffset]);
      });

      const conePolygon = L.polygon([...leftSide, ...rightSide], {
        color: '#94a3b8',
        fillColor: '#64748b',
        fillOpacity: 0.15 * opacity,
        weight: 1,
        dashArray: '5, 5',
      });
      conePolygon.addTo(map);
      layersRef.current.push(conePolygon);
    }

    // 3. Draw Historical Track
    if (showTrack && track && track.length > 0) {
      const trackCoords = track.map(p => [p.lat, p.lon]);

      // Main track line
      const trackLine = L.polyline(trackCoords, {
        color: '#1e293b',
        weight: 4,
        opacity: 0.9,
      });
      trackLine.addTo(map);
      layersRef.current.push(trackLine);

      // Track points with category colors
      track.forEach((point, index) => {
        const pointCat = getCycloneCategory(point.windSpeed || 0);
        const circle = L.circleMarker([point.lat, point.lon], {
          radius: 6,
          color: '#ffffff',
          fillColor: pointCat.color,
          fillOpacity: 1,
          weight: 2,
        });
        circle.bindPopup(`
          <div class="p-2 min-w-[180px]">
            <p class="text-xs text-slate-400">${new Date(point.time).toLocaleString()}</p>
            <p class="text-sm font-semibold mt-1">${pointCat.label}</p>
            <p class="text-xs">Wind: ${point.windSpeed || 'N/A'} km/h</p>
            <p class="text-xs">Pressure: ${point.pressure || 'N/A'} hPa</p>
          </div>
        `);
        circle.addTo(map);
        layersRef.current.push(circle);
      });
    }

    // 4. Draw Forecast Track
    if (forecast && forecast.length > 0) {
      const forecastCoords = [[currentPosition.lat, currentPosition.lon], ...forecast.map(p => [p.lat, p.lon])];

      const forecastLine = L.polyline(forecastCoords, {
        color: '#ef4444',
        weight: 3,
        opacity: 0.8,
        dashArray: '10, 8',
      });
      forecastLine.addTo(map);
      layersRef.current.push(forecastLine);

      // Forecast points
      forecast.forEach((point, index) => {
        const size = 8 - index; // Smaller for further forecasts
        const circle = L.circleMarker([point.lat, point.lon], {
          radius: Math.max(size, 4),
          color: '#ef4444',
          fillColor: '#fca5a5',
          fillOpacity: 0.6,
          weight: 2,
        });
        circle.bindPopup(`
          <div class="p-2">
            <p class="text-xs text-slate-400">Forecast +${(index + 1) * 12}h</p>
            <p class="text-xs">${new Date(point.time).toLocaleString()}</p>
            <p class="text-xs mt-1">Expected Wind: ${point.windSpeed || 'N/A'} km/h</p>
          </div>
        `);
        circle.addTo(map);
        layersRef.current.push(circle);
      });
    }

    // 5. Draw Wind Radii
    if (showWindRadii && windRadii && currentPosition) {
      const radiiConfig = [
        { key: 'gale', wind: 34, color: '#22c55e', label: '34kt winds' },
        { key: 'storm', wind: 48, color: '#eab308', label: '48kt winds' },
        { key: 'hurricane', wind: 64, color: '#ef4444', label: '64kt winds' },
      ];

      radiiConfig.forEach(config => {
        const radius = windRadii[config.key];
        if (radius) {
          // If radius is object with quadrants
          if (typeof radius === 'object') {
            const avgRadius = (radius.ne + radius.se + radius.sw + radius.nw) / 4;
            const circle = L.circle([currentPosition.lat, currentPosition.lon], {
              radius: avgRadius * 1852, // Convert nautical miles to meters
              color: config.color,
              fillColor: config.color,
              fillOpacity: 0.1 * opacity,
              weight: 2,
              dashArray: '8, 4',
            });
            circle.bindTooltip(config.label, { permanent: false });
            circle.addTo(map);
            layersRef.current.push(circle);
          } else {
            const circle = L.circle([currentPosition.lat, currentPosition.lon], {
              radius: radius * 1852,
              color: config.color,
              fillColor: config.color,
              fillOpacity: 0.1 * opacity,
              weight: 2,
              dashArray: '8, 4',
            });
            circle.addTo(map);
            layersRef.current.push(circle);
          }
        }
      });
    }

    // 6. Draw Main Cyclone Symbol (Animated Spiral)
    if (currentPosition) {
      // Create animated cyclone icon
      const createCycloneIcon = (rotation = 0) => {
        const size = Math.min(80, 40 + (maxWindSpeed || 50) / 3);

        return L.divIcon({
          html: `
            <div class="cyclone-symbol" style="
              width: ${size}px;
              height: ${size}px;
              position: relative;
            ">
              <!-- Outer glow -->
              <div style="
                position: absolute;
                inset: -10px;
                background: radial-gradient(circle, ${category.color}40 0%, transparent 70%);
                border-radius: 50%;
                animation: cyclone-pulse 2s ease-in-out infinite;
              "></div>

              <!-- Spiral SVG -->
              <svg viewBox="0 0 100 100" style="
                width: 100%;
                height: 100%;
                transform: rotate(${rotation}deg);
                filter: drop-shadow(0 0 8px ${category.color});
              ">
                <!-- Spiral arms -->
                <path d="M50 50 Q60 30 50 15 Q35 25 40 50 Q45 70 65 75 Q75 65 70 50 Q65 35 50 35 Q40 40 45 50"
                      fill="none"
                      stroke="${category.color}"
                      stroke-width="4"
                      stroke-linecap="round"/>
                <path d="M50 50 Q40 70 50 85 Q65 75 60 50 Q55 30 35 25 Q25 35 30 50 Q35 65 50 65 Q60 60 55 50"
                      fill="none"
                      stroke="${category.color}"
                      stroke-width="4"
                      stroke-linecap="round"/>

                <!-- Eye -->
                <circle cx="50" cy="50" r="8" fill="${category.color}" stroke="white" stroke-width="2"/>
                <circle cx="50" cy="50" r="4" fill="white"/>
              </svg>

              <!-- Category indicator -->
              <div style="
                position: absolute;
                bottom: -24px;
                left: 50%;
                transform: translateX(-50%);
                background: ${category.color};
                color: white;
                padding: 2px 8px;
                border-radius: 10px;
                font-size: 10px;
                font-weight: bold;
                white-space: nowrap;
                box-shadow: 0 2px 8px rgba(0,0,0,0.3);
              ">${name || 'CYCLONE'}</div>
            </div>
          `,
          className: 'cyclone-marker-icon',
          iconSize: [size, size],
          iconAnchor: [size / 2, size / 2],
          popupAnchor: [0, -size / 2 - 10],
        });
      };

      // Create marker
      const cycloneMarker = L.marker([currentPosition.lat, currentPosition.lon], {
        icon: createCycloneIcon(0),
        zIndexOffset: 1000,
      });

      cycloneMarker.bindPopup(`
        <div class="p-3 min-w-[220px]">
          <div class="flex items-center justify-between mb-2">
            <h3 class="font-bold text-lg">${name || 'CYCLONE'}</h3>
            <span class="px-2 py-1 rounded text-xs font-bold text-white" style="background: ${category.color}">
              ${category.label}
            </span>
          </div>

          <div class="grid grid-cols-2 gap-2 text-sm">
            <div class="bg-slate-100 dark:bg-slate-800 p-2 rounded">
              <p class="text-xs text-slate-500">Max Wind</p>
              <p class="font-bold">${maxWindSpeed || 'N/A'} km/h</p>
            </div>
            <div class="bg-slate-100 dark:bg-slate-800 p-2 rounded">
              <p class="text-xs text-slate-500">Pressure</p>
              <p class="font-bold">${centralPressure || 'N/A'} hPa</p>
            </div>
            <div class="bg-slate-100 dark:bg-slate-800 p-2 rounded">
              <p class="text-xs text-slate-500">Movement</p>
              <p class="font-bold">${movementDirection || 'N/A'}° @ ${movementSpeed || 'N/A'} km/h</p>
            </div>
            <div class="bg-slate-100 dark:bg-slate-800 p-2 rounded">
              <p class="text-xs text-slate-500">Position</p>
              <p class="font-bold text-xs">${currentPosition.lat.toFixed(2)}°N, ${currentPosition.lon.toFixed(2)}°E</p>
            </div>
          </div>

          <p class="text-xs text-slate-400 mt-2 text-center">
            Last Updated: ${new Date(currentPosition.time || Date.now()).toLocaleString()}
          </p>
        </div>
      `);

      cycloneMarker.addTo(map);
      layersRef.current.push(cycloneMarker);

      // Animate rotation
      if (animateCyclone) {
        let rotation = 0;
        const animate = () => {
          rotation = (rotation + 2) % 360;
          cycloneMarker.setIcon(createCycloneIcon(rotation));
          animationRef.current = requestAnimationFrame(animate);
        };
        animate();
      }
    }

    return () => clearLayers();
  }, [map, cycloneData, surgeData, showTrack, showSurge, showWindRadii, showForecastCone, animateCyclone, opacity]);

  return null;
}

// CSS for animations (add to map.css)
export const cycloneStyles = `
  @keyframes cyclone-pulse {
    0%, 100% { transform: scale(1); opacity: 0.6; }
    50% { transform: scale(1.2); opacity: 0.3; }
  }

  .cyclone-marker-icon {
    background: transparent !important;
    border: none !important;
  }

  .cyclone-symbol svg {
    transition: transform 0.1s linear;
  }
`;

export default CycloneLayer;
