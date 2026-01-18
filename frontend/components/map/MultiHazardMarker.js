'use client';

import { Marker, Popup, Circle } from 'react-leaflet';
import { AlertTriangle, Waves, Wind, CloudRain, Activity, Droplets, MapPin } from 'lucide-react';

// Alert level configuration (1-5 scale)
const ALERT_LEVELS = {
  5: { name: 'CRITICAL', color: '#DC2626', size: 40, pulse: true },
  4: { name: 'WARNING', color: '#F97316', size: 35, pulse: false },
  3: { name: 'WATCH', color: '#FCD34D', size: 30, pulse: false },
  2: { name: 'ADVISORY', color: '#60A5FA', size: 28, pulse: false },
  1: { name: 'NORMAL', color: '#10B981', size: 25, pulse: false },
};

// Hazard type icons and labels
const HAZARD_TYPES = {
  tsunami: { icon: Waves, label: 'Tsunami', color: 'text-blue-600' },
  cyclone: { icon: Wind, label: 'Cyclone', color: 'text-purple-600' },
  high_waves: { icon: Waves, label: 'High Waves', color: 'text-cyan-600' },
  coastal_flood: { icon: CloudRain, label: 'Coastal Flood', color: 'text-teal-600' },
  rip_currents: { icon: Activity, label: 'Rip Currents', color: 'text-indigo-600' },
};

// Create custom icon for location marker
const createLocationIcon = (alertLevel, isPulsing = false) => {
  if (typeof window === 'undefined') return null;

  const L = require('leaflet');
  const config = ALERT_LEVELS[alertLevel] || ALERT_LEVELS[1];
  const size = config.size;

  const pulseAnimation = isPulsing ? `
    @keyframes pulse-marker {
      0%, 100% { transform: scale(1); opacity: 1; }
      50% { transform: scale(1.15); opacity: 0.8; }
    }
    animation: pulse-marker 2s ease-in-out infinite;
  ` : '';

  const iconHtml = `
    <div style="
      width: ${size}px;
      height: ${size}px;
      background: ${config.color};
      border: 3px solid white;
      border-radius: 50%;
      box-shadow: 0 2px 8px rgba(0,0,0,0.3), 0 0 0 2px ${config.color}33;
      display: flex;
      align-items: center;
      justify-content: center;
      ${pulseAnimation}
    ">
      <span style="color: white; font-size: ${size * 0.4}px; font-weight: bold;">
        ${alertLevel}
      </span>
    </div>
  `;

  return L.divIcon({
    html: iconHtml,
    className: 'multi-hazard-marker',
    iconSize: [size, size],
    iconAnchor: [size / 2, size / 2],
    popupAnchor: [0, -size / 2]
  });
};

// Format time ago
const formatTimeAgo = (dateString) => {
  if (!dateString) return 'Unknown';
  const date = new Date(dateString);
  const now = new Date();
  const diffMs = now - date;
  const diffMins = Math.floor(diffMs / 60000);

  if (diffMins < 1) return 'Just now';
  if (diffMins < 60) return `${diffMins}m ago`;
  const diffHours = Math.floor(diffMins / 60);
  if (diffHours < 24) return `${diffHours}h ago`;
  return date.toLocaleDateString();
};

export function MultiHazardMarker({ location, onLocationSelect }) {
  const alertLevel = location.max_alert_level || location.alert_level || 1;
  const config = ALERT_LEVELS[alertLevel] || ALERT_LEVELS[1];
  const activeHazards = location.active_hazards || [];

  // Circle radius based on alert level (in meters)
  const getCircleRadius = () => {
    switch (alertLevel) {
      case 5: return 50000; // 50km
      case 4: return 40000; // 40km
      case 3: return 30000; // 30km
      default: return 20000; // 20km
    }
  };

  return (
    <>
      {/* Background circle for visual impact */}
      <Circle
        center={[location.coordinates?.lat || location.lat, location.coordinates?.lon || location.lon]}
        radius={getCircleRadius()}
        pathOptions={{
          color: config.color,
          fillColor: config.color,
          fillOpacity: alertLevel >= 4 ? 0.15 : 0.08,
          weight: alertLevel >= 4 ? 2 : 1,
          dashArray: alertLevel < 3 ? '5, 5' : null
        }}
      />

      {/* Location marker */}
      <Marker
        position={[location.coordinates?.lat || location.lat, location.coordinates?.lon || location.lon]}
        icon={createLocationIcon(alertLevel, config.pulse)}
        eventHandlers={{
          click: () => onLocationSelect?.(location)
        }}
      >
        <Popup minWidth={280} maxWidth={350}>
          <div className="p-1">
            {/* Header */}
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-2">
                <MapPin className="w-5 h-5 text-gray-600" />
                <h3 className="font-bold text-base text-gray-900">
                  {location.location_name || location.name}
                </h3>
              </div>
              <span
                className="px-2 py-1 rounded-full text-xs font-bold text-white"
                style={{ backgroundColor: config.color }}
              >
                {config.name}
              </span>
            </div>

            {/* Risk Profile */}
            {location.risk_profile && (
              <div className="mb-3 text-xs text-gray-500">
                <span className="font-medium">Risk Profile:</span> {location.risk_profile}
              </div>
            )}

            {/* Active Hazards */}
            {activeHazards.length > 0 ? (
              <div className="mb-3">
                <h4 className="text-xs font-semibold text-gray-700 mb-2 uppercase tracking-wide">
                  Active Hazards ({activeHazards.length})
                </h4>
                <div className="space-y-2">
                  {activeHazards.map((hazard, idx) => {
                    const hazardType = HAZARD_TYPES[hazard.hazard_type] || {
                      icon: AlertTriangle,
                      label: hazard.hazard_type,
                      color: 'text-gray-600'
                    };
                    const HazardIcon = hazardType.icon;
                    const hazardConfig = ALERT_LEVELS[hazard.alert_level] || ALERT_LEVELS[3];

                    return (
                      <div
                        key={hazard.alert_id || idx}
                        className="flex items-start gap-2 p-2 bg-gray-50 rounded-lg"
                      >
                        <HazardIcon className={`w-4 h-4 mt-0.5 ${hazardType.color}`} />
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center justify-between">
                            <span className="font-medium text-sm text-gray-800">
                              {hazardType.label}
                            </span>
                            <span
                              className="px-1.5 py-0.5 rounded text-[10px] font-bold text-white"
                              style={{ backgroundColor: hazardConfig.color }}
                            >
                              L{hazard.alert_level}
                            </span>
                          </div>
                          {hazard.confidence && (
                            <div className="text-[10px] text-gray-500 mt-0.5">
                              Confidence: {(hazard.confidence * 100).toFixed(0)}%
                            </div>
                          )}
                          {hazard.recommendations && hazard.recommendations.length > 0 && (
                            <div className="text-[10px] text-red-600 mt-1 font-medium">
                              {hazard.recommendations[0]}
                            </div>
                          )}
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            ) : (
              <div className="mb-3 p-3 bg-green-50 rounded-lg text-center">
                <span className="text-green-700 text-sm font-medium">No Active Hazards</span>
                <p className="text-green-600 text-xs mt-1">Area is currently safe</p>
              </div>
            )}

            {/* Weather Info */}
            {location.weather && (
              <div className="mb-3 p-2 bg-blue-50 rounded-lg">
                <h4 className="text-xs font-semibold text-blue-700 mb-1">Current Conditions</h4>
                <div className="grid grid-cols-2 gap-2 text-xs text-blue-800">
                  {location.weather.wind_kph && (
                    <div>Wind: {location.weather.wind_kph.toFixed(0)} km/h</div>
                  )}
                  {location.weather.temp_c && (
                    <div>Temp: {location.weather.temp_c.toFixed(1)}°C</div>
                  )}
                  {location.weather.pressure_mb && (
                    <div>Pressure: {location.weather.pressure_mb} mb</div>
                  )}
                  {location.weather.humidity && (
                    <div>Humidity: {location.weather.humidity}%</div>
                  )}
                </div>
              </div>
            )}

            {/* Marine Info */}
            {location.marine && (
              <div className="mb-3 p-2 bg-cyan-50 rounded-lg">
                <h4 className="text-xs font-semibold text-cyan-700 mb-1">Marine Conditions</h4>
                <div className="grid grid-cols-2 gap-2 text-xs text-cyan-800">
                  {location.marine.sig_ht_mt && (
                    <div>Wave Height: {location.marine.sig_ht_mt}m</div>
                  )}
                  {location.marine.swell_ht_mt && (
                    <div>Swell: {location.marine.swell_ht_mt}m</div>
                  )}
                </div>
              </div>
            )}

            {/* Recommendations */}
            {location.recommendations && location.recommendations.length > 0 && (
              <div className="mb-3">
                <h4 className="text-xs font-semibold text-gray-700 mb-1">Recommendations</h4>
                <ul className="text-xs text-gray-600 space-y-1">
                  {location.recommendations.slice(0, 3).map((rec, idx) => (
                    <li key={idx} className="flex items-start gap-1">
                      <span className="text-amber-500">•</span>
                      <span>{rec}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {/* Footer */}
            <div className="pt-2 border-t border-gray-100 flex items-center justify-between text-[10px] text-gray-400">
              <span>
                {location.coordinates?.lat?.toFixed(4)}°N, {location.coordinates?.lon?.toFixed(4)}°E
              </span>
              <span>Updated {formatTimeAgo(location.last_updated || location.detected_at)}</span>
            </div>
          </div>
        </Popup>
      </Marker>
    </>
  );
}

// Export alert level config for use in legends
export { ALERT_LEVELS, HAZARD_TYPES };
