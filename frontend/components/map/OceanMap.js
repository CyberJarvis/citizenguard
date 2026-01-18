'use client';

import React, { useState, useRef, useMemo, useCallback, useEffect } from 'react';
import dynamic from 'next/dynamic';
import { Waves } from 'lucide-react';

// Dynamic imports for Leaflet components (SSR-safe)
const MapContainer = dynamic(
  () => import('react-leaflet').then((mod) => mod.MapContainer),
  { ssr: false }
);
const TileLayer = dynamic(
  () => import('react-leaflet').then((mod) => mod.TileLayer),
  { ssr: false }
);
const ZoomControl = dynamic(
  () => import('react-leaflet').then((mod) => mod.ZoomControl),
  { ssr: false }
);
const Marker = dynamic(
  () => import('react-leaflet').then((mod) => mod.Marker),
  { ssr: false }
);
const Popup = dynamic(
  () => import('react-leaflet').then((mod) => mod.Popup),
  { ssr: false }
);
const Circle = dynamic(
  () => import('react-leaflet').then((mod) => mod.Circle),
  { ssr: false }
);

// Alert level configuration
export const ALERT_CONFIG = {
  5: {
    name: 'CRITICAL',
    color: '#ef4444',
    glow: 'rgba(239,68,68,0.6)',
    bg: 'bg-red-500',
    size: 48,
    pulse: true,
    gradient: 'linear-gradient(135deg, #ef4444 0%, #dc2626 100%)',
  },
  4: {
    name: 'WARNING',
    color: '#f97316',
    glow: 'rgba(249,115,22,0.5)',
    bg: 'bg-orange-500',
    size: 42,
    pulse: true,
    gradient: 'linear-gradient(135deg, #f97316 0%, #ea580c 100%)',
  },
  3: {
    name: 'WATCH',
    color: '#eab308',
    glow: 'rgba(234,179,8,0.4)',
    bg: 'bg-yellow-500',
    size: 36,
    pulse: false,
    gradient: 'linear-gradient(135deg, #eab308 0%, #ca8a04 100%)',
  },
  2: {
    name: 'ADVISORY',
    color: '#3b82f6',
    glow: 'rgba(59,130,246,0.3)',
    bg: 'bg-blue-500',
    size: 32,
    pulse: false,
    gradient: 'linear-gradient(135deg, #3b82f6 0%, #2563eb 100%)',
  },
  1: {
    name: 'NORMAL',
    color: '#22c55e',
    glow: 'rgba(34,197,94,0.2)',
    bg: 'bg-emerald-500',
    size: 28,
    pulse: false,
    gradient: 'linear-gradient(135deg, #22c55e 0%, #16a34a 100%)',
  },
};

// Map tile layer configurations
export const MAP_TILES = {
  // ESRI Ocean Basemap - Best for marine/coastal applications
  esriOcean: {
    name: 'ESRI Ocean',
    url: 'https://server.arcgisonline.com/ArcGIS/rest/services/Ocean/World_Ocean_Base/MapServer/tile/{z}/{y}/{x}',
    attribution: '&copy; <a href="https://www.esri.com/">Esri</a> | GEBCO, NOAA, National Geographic',
    maxZoom: 13,
  },
  // ESRI Ocean with Reference Labels overlay
  esriOceanRef: {
    name: 'ESRI Ocean (Labels)',
    url: 'https://server.arcgisonline.com/ArcGIS/rest/services/Ocean/World_Ocean_Base/MapServer/tile/{z}/{y}/{x}',
    attribution: '&copy; <a href="https://www.esri.com/">Esri</a> | GEBCO, NOAA',
    maxZoom: 13,
    overlay: 'https://server.arcgisonline.com/ArcGIS/rest/services/Ocean/World_Ocean_Reference/MapServer/tile/{z}/{y}/{x}',
  },
  dark: {
    name: 'Dark Mode',
    url: 'https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png',
    attribution: '&copy; <a href="https://carto.com/">CARTO</a>',
  },
  satellite: {
    name: 'Satellite',
    url: 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
    attribution: '&copy; <a href="https://www.esri.com/">Esri</a>',
  },
  // ESRI National Geographic - Beautiful land/ocean visualization
  natGeo: {
    name: 'National Geographic',
    url: 'https://server.arcgisonline.com/ArcGIS/rest/services/NatGeo_World_Map/MapServer/tile/{z}/{y}/{x}',
    attribution: '&copy; <a href="https://www.esri.com/">Esri</a> | National Geographic',
  },
  // ESRI Physical Map - Shows terrain and bathymetry
  physical: {
    name: 'Physical',
    url: 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Physical_Map/MapServer/tile/{z}/{y}/{x}',
    attribution: '&copy; <a href="https://www.esri.com/">Esri</a> | US National Park Service',
    maxZoom: 8,
  },
  terrain: {
    name: 'Terrain',
    url: 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Topo_Map/MapServer/tile/{z}/{y}/{x}',
    attribution: '&copy; <a href="https://www.esri.com/">Esri</a>',
  },
  // Light theme option
  light: {
    name: 'Light',
    url: 'https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png',
    attribution: '&copy; <a href="https://carto.com/">CARTO</a>',
  },
};

// Create custom marker icon (memoized)
export const createMarkerIcon = (alertLevel) => {
  if (typeof window === 'undefined') return null;
  const L = require('leaflet');
  const config = ALERT_CONFIG[alertLevel] || ALERT_CONFIG[1];

  const pulseAnimation = config.pulse
    ? `animation: marker-glow 2s ease-in-out infinite;`
    : '';

  const html = `
    <div class="ocean-marker ${config.pulse ? 'critical' : ''}" style="
      width: ${config.size}px;
      height: ${config.size}px;
      background: ${config.gradient};
      border: 3px solid rgba(255,255,255,0.9);
      border-radius: 50%;
      display: flex;
      align-items: center;
      justify-content: center;
      box-shadow: 0 4px 15px ${config.glow}, 0 0 25px ${config.glow};
      ${pulseAnimation}
    ">
      <span style="
        color: white;
        font-size: ${config.size * 0.4}px;
        font-weight: 700;
        text-shadow: 0 1px 3px rgba(0,0,0,0.3);
      ">${alertLevel}</span>
    </div>
  `;

  return L.divIcon({
    html,
    className: 'custom-hazard-marker',
    iconSize: [config.size, config.size],
    iconAnchor: [config.size / 2, config.size / 2],
    popupAnchor: [0, -config.size / 2],
  });
};

// Default map center (Indian Ocean region)
const DEFAULT_CENTER = [15.8, 80.2];
const DEFAULT_ZOOM = 5;

/**
 * OceanMap - Main map container component
 * Full-screen immersive ocean monitoring map
 */
export function OceanMap({
  locations = [],
  alerts = [],
  reports = [],
  heatmapPoints = [],
  mapStyle = 'dark',
  showHeatmap = true,
  showClusters = true,
  selectedLocation = null,
  onLocationSelect = () => {},
  onMapReady = () => {},
  children,
}) {
  const mapRef = useRef(null);
  const [isMapReady, setIsMapReady] = useState(false);

  // Load Leaflet CSS on mount
  useEffect(() => {
    import('leaflet/dist/leaflet.css');
  }, []);

  // Handle map ready
  const handleMapReady = useCallback(() => {
    setIsMapReady(true);
    if (mapRef.current) {
      onMapReady(mapRef.current);
    }
  }, [onMapReady]);

  // Fly to location
  const flyToLocation = useCallback((location, zoom = 8) => {
    if (mapRef.current) {
      const lat = location.coordinates?.lat || location.lat;
      const lon = location.coordinates?.lon || location.lon;
      if (lat && lon) {
        mapRef.current.flyTo([lat, lon], zoom, { duration: 1.5 });
      }
    }
  }, []);

  // Expose flyTo method
  useEffect(() => {
    if (selectedLocation && isMapReady) {
      flyToLocation(selectedLocation);
    }
  }, [selectedLocation, isMapReady, flyToLocation]);

  // Memoized marker icons
  const markerIcons = useMemo(() => {
    const icons = {};
    for (let level = 1; level <= 5; level++) {
      icons[level] = createMarkerIcon(level);
    }
    return icons;
  }, []);

  // Current tile layer
  const currentTile = MAP_TILES[mapStyle] || MAP_TILES.dark;

  return (
    <div className="ocean-map-container">
      <MapContainer
        center={DEFAULT_CENTER}
        zoom={DEFAULT_ZOOM}
        style={{ height: '100%', width: '100%' }}
        zoomControl={false}
        ref={mapRef}
        whenReady={handleMapReady}
        maxZoom={currentTile.maxZoom || 18}
      >
        <TileLayer
          url={currentTile.url}
          attribution={currentTile.attribution}
          maxZoom={currentTile.maxZoom || 18}
        />
        {/* Overlay layer for labeled maps (e.g., ESRI Ocean Reference) */}
        {currentTile.overlay && (
          <TileLayer
            url={currentTile.overlay}
            maxZoom={currentTile.maxZoom || 18}
          />
        )}
        <ZoomControl position="bottomright" />

        {/* Render location markers */}
        {locations.map((location) => {
          const alertLevel = location.alert_level || location.max_alert_level || 1;
          const lat = location.coordinates?.lat || location.lat;
          const lon = location.coordinates?.lon || location.lon;
          const config = ALERT_CONFIG[alertLevel];

          if (!lat || !lon) return null;

          return (
            <React.Fragment key={location.location_id}>
              {/* Glow circle for high alerts */}
              {alertLevel >= 3 && (
                <Circle
                  center={[lat, lon]}
                  radius={alertLevel >= 5 ? 80000 : alertLevel >= 4 ? 60000 : 40000}
                  pathOptions={{
                    color: config.color,
                    fillColor: config.color,
                    fillOpacity: 0.12,
                    weight: 2,
                    opacity: 0.5,
                  }}
                />
              )}

              <Marker
                position={[lat, lon]}
                icon={markerIcons[alertLevel]}
                eventHandlers={{
                  click: () => onLocationSelect(location),
                }}
              >
                <Popup className="ocean-popup" maxWidth={340}>
                  <div className="p-4">
                    <div className="flex items-center justify-between mb-3">
                      <h3 className="font-bold text-lg text-white">
                        {location.location_name || location.name}
                      </h3>
                      <span
                        className="px-3 py-1 rounded-full text-xs font-bold text-white"
                        style={{ background: config.gradient }}
                      >
                        {config.name}
                      </span>
                    </div>

                    <p className="text-sm text-slate-400 mb-3">
                      {location.region}
                      {location.country ? `, ${location.country}` : ''}
                    </p>

                    {location.active_hazards?.length > 0 && (
                      <div className="space-y-2 mb-3">
                        <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide">
                          Active Hazards
                        </p>
                        {location.active_hazards.map((hazard, idx) => {
                          const hConfig = ALERT_CONFIG[hazard.alert_level] || ALERT_CONFIG[3];
                          return (
                            <div
                              key={idx}
                              className="flex items-center gap-2 p-2 bg-slate-800/50 rounded-lg"
                            >
                              <Waves
                                className="w-4 h-4"
                                style={{ color: hConfig.color }}
                              />
                              <span className="flex-1 text-sm font-medium text-slate-300">
                                {hazard.hazard_type?.replace(/_/g, ' ')}
                              </span>
                              <span
                                className="px-2 py-0.5 rounded text-xs font-bold text-white"
                                style={{ background: hConfig.gradient }}
                              >
                                L{hazard.alert_level}
                              </span>
                            </div>
                          );
                        })}
                      </div>
                    )}

                    {(!location.active_hazards || location.active_hazards.length === 0) && (
                      <div className="flex items-center gap-2 p-3 bg-emerald-500/10 rounded-lg mb-3">
                        <div className="w-2 h-2 rounded-full bg-emerald-400" />
                        <span className="text-sm font-medium text-emerald-400">
                          Area is Safe
                        </span>
                      </div>
                    )}

                    <div className="text-xs text-slate-500 pt-2 border-t border-slate-700/50">
                      {lat?.toFixed(4)}°N, {lon?.toFixed(4)}°E
                    </div>
                  </div>
                </Popup>
              </Marker>
            </React.Fragment>
          );
        })}

        {/* Additional children (heatmap, clusters, etc.) */}
        {children}
      </MapContainer>

      {/* Inline styles for marker animations */}
      <style jsx global>{`
        @keyframes marker-glow {
          0%,
          100% {
            box-shadow: 0 0 0 0 rgba(239, 68, 68, 0.7);
          }
          50% {
            box-shadow: 0 0 0 20px rgba(239, 68, 68, 0);
          }
        }

        .custom-hazard-marker {
          background: transparent !important;
          border: none !important;
        }

        .ocean-popup .leaflet-popup-content-wrapper {
          background: rgba(10, 15, 26, 0.95);
          backdrop-filter: blur(20px);
          -webkit-backdrop-filter: blur(20px);
          border: 1px solid rgba(255, 255, 255, 0.08);
          border-radius: 16px;
          box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.5);
          padding: 0;
          color: #f1f5f9;
        }

        .ocean-popup .leaflet-popup-tip {
          background: rgba(10, 15, 26, 0.95);
          border: 1px solid rgba(255, 255, 255, 0.08);
          border-top: none;
          border-left: none;
        }

        .ocean-popup .leaflet-popup-content {
          margin: 0;
          min-width: 280px;
        }

        .leaflet-control-zoom {
          border: none !important;
          box-shadow: 0 10px 40px -10px rgba(0, 0, 0, 0.5) !important;
          border-radius: 12px !important;
          overflow: hidden;
        }

        .leaflet-control-zoom a {
          background: rgba(15, 23, 42, 0.9) !important;
          backdrop-filter: blur(16px);
          -webkit-backdrop-filter: blur(16px);
          color: #94a3b8 !important;
          border: none !important;
          width: 40px !important;
          height: 40px !important;
          line-height: 40px !important;
          font-size: 18px !important;
        }

        .leaflet-control-zoom a:first-child {
          border-radius: 12px 12px 0 0 !important;
        }

        .leaflet-control-zoom a:last-child {
          border-radius: 0 0 12px 12px !important;
        }

        .leaflet-control-zoom a:hover {
          background: rgba(30, 41, 59, 0.95) !important;
          color: white !important;
        }
      `}</style>
    </div>
  );
}

export default OceanMap;
