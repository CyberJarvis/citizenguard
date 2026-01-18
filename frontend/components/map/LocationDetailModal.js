'use client';

import React from 'react';
import {
  X,
  MapPin,
  Waves,
  Wind,
  CloudRain,
  Activity,
  Droplets,
  Thermometer,
  AlertTriangle,
  Shield,
  ExternalLink,
  Navigation,
} from 'lucide-react';
import { ALERT_CONFIG } from './OceanMap';

// Hazard icons mapping
const HAZARD_ICONS = {
  cyclone: Wind,
  high_waves: Waves,
  coastal_flood: CloudRain,
  rip_currents: Activity,
  tsunami: Waves,
  storm_surge: Droplets,
  earthquake: Activity,
  rip_current: Activity,
};

/**
 * LocationDetailModal - Detailed view of a monitoring location
 */
export function LocationDetailModal({
  location,
  alerts = [],
  onClose = () => {},
  onNavigate = () => {},
}) {
  if (!location) return null;

  const alertLevel = location.alert_level || location.max_alert_level || 1;
  const config = ALERT_CONFIG[alertLevel];
  const lat = location.coordinates?.lat || location.lat;
  const lon = location.coordinates?.lon || location.lon;

  // Get alerts for this location
  const locationAlerts = alerts.filter(
    (a) => a.location_id === location.location_id
  );

  // Get weather data if available
  const weather = location.current_weather || location.weather;
  const marine = location.marine_data || location.marine;

  return (
    <div className="detail-modal-overlay" onClick={onClose}>
      <div
        className="detail-modal glass-panel-dark"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div
          className="p-4 border-b border-slate-700/50"
          style={{ background: `${config.color}15` }}
        >
          <div className="flex items-start justify-between">
            <div className="flex items-center gap-3">
              <div
                className="w-12 h-12 rounded-xl flex items-center justify-center text-white font-bold text-lg"
                style={{ background: config.gradient }}
              >
                {alertLevel}
              </div>
              <div>
                <h2 className="font-bold text-white text-lg">
                  {location.location_name || location.name}
                </h2>
                <p className="text-sm text-slate-400">
                  {location.region}
                  {location.country ? `, ${location.country}` : ''}
                </p>
              </div>
            </div>
            <button
              onClick={onClose}
              className="p-2 rounded-lg hover:bg-slate-700/50 text-slate-400 hover:text-white transition-colors"
            >
              <X className="w-5 h-5" />
            </button>
          </div>

          {/* Status Badge */}
          <div className="mt-3 flex items-center gap-2">
            <span
              className="px-3 py-1 rounded-full text-xs font-bold text-white"
              style={{ background: config.gradient }}
            >
              {config.name}
            </span>
            {location.active_hazards?.length > 0 ? (
              <span className="text-xs text-slate-400">
                {location.active_hazards.length} active hazard
                {location.active_hazards.length > 1 ? 's' : ''}
              </span>
            ) : (
              <span className="text-xs text-emerald-400 flex items-center gap-1">
                <Shield className="w-3 h-3" />
                Area Safe
              </span>
            )}
          </div>
        </div>

        {/* Content */}
        <div className="p-4 space-y-4 max-h-[60vh] overflow-y-auto">
          {/* Active Hazards */}
          {location.active_hazards?.length > 0 && (
            <div>
              <h3 className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">
                Active Hazards
              </h3>
              <div className="space-y-2">
                {location.active_hazards.map((hazard, idx) => {
                  const HazardIcon = HAZARD_ICONS[hazard.hazard_type] || AlertTriangle;
                  const hConfig = ALERT_CONFIG[hazard.alert_level] || ALERT_CONFIG[3];

                  return (
                    <div
                      key={idx}
                      className="flex items-center gap-3 p-3 rounded-xl"
                      style={{ background: `${hConfig.color}10` }}
                    >
                      <div
                        className="w-10 h-10 rounded-lg flex items-center justify-center"
                        style={{ background: hConfig.gradient }}
                      >
                        <HazardIcon className="w-5 h-5 text-white" />
                      </div>
                      <div className="flex-1">
                        <p className="font-medium text-white capitalize">
                          {hazard.hazard_type?.replace(/_/g, ' ')}
                        </p>
                        {hazard.description && (
                          <p className="text-xs text-slate-400 mt-0.5">
                            {hazard.description}
                          </p>
                        )}
                      </div>
                      <span
                        className="px-2 py-1 rounded-lg text-xs font-bold text-white"
                        style={{ background: hConfig.gradient }}
                      >
                        L{hazard.alert_level}
                      </span>
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {/* Weather Data */}
          {weather && (
            <div>
              <h3 className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">
                Current Weather
              </h3>
              <div className="grid grid-cols-2 gap-2">
                {weather.temp_c !== undefined && (
                  <div className="stat-card">
                    <div className="flex items-center gap-2">
                      <Thermometer className="w-4 h-4 text-cyan-400" />
                      <span className="stat-label">Temperature</span>
                    </div>
                    <span className="stat-value text-lg">{weather.temp_c}°C</span>
                  </div>
                )}
                {weather.wind_kph !== undefined && (
                  <div className="stat-card">
                    <div className="flex items-center gap-2">
                      <Wind className="w-4 h-4 text-cyan-400" />
                      <span className="stat-label">Wind</span>
                    </div>
                    <span className="stat-value text-lg">
                      {weather.wind_kph} km/h
                    </span>
                  </div>
                )}
                {weather.humidity !== undefined && (
                  <div className="stat-card">
                    <div className="flex items-center gap-2">
                      <Droplets className="w-4 h-4 text-cyan-400" />
                      <span className="stat-label">Humidity</span>
                    </div>
                    <span className="stat-value text-lg">{weather.humidity}%</span>
                  </div>
                )}
                {weather.condition && (
                  <div className="stat-card">
                    <div className="flex items-center gap-2">
                      <CloudRain className="w-4 h-4 text-cyan-400" />
                      <span className="stat-label">Condition</span>
                    </div>
                    <span className="stat-value text-sm text-white">
                      {weather.condition}
                    </span>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Marine Data */}
          {marine && (
            <div>
              <h3 className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">
                Marine Conditions
              </h3>
              <div className="grid grid-cols-2 gap-2">
                {marine.sig_ht_mt !== undefined && (
                  <div className="stat-card">
                    <div className="flex items-center gap-2">
                      <Waves className="w-4 h-4 text-cyan-400" />
                      <span className="stat-label">Wave Height</span>
                    </div>
                    <span className="stat-value text-lg">{marine.sig_ht_mt}m</span>
                  </div>
                )}
                {marine.swell_ht_mt !== undefined && (
                  <div className="stat-card">
                    <div className="flex items-center gap-2">
                      <Activity className="w-4 h-4 text-cyan-400" />
                      <span className="stat-label">Swell</span>
                    </div>
                    <span className="stat-value text-lg">
                      {marine.swell_ht_mt}m
                    </span>
                  </div>
                )}
                {marine.water_temp_c !== undefined && (
                  <div className="stat-card">
                    <div className="flex items-center gap-2">
                      <Thermometer className="w-4 h-4 text-cyan-400" />
                      <span className="stat-label">Water Temp</span>
                    </div>
                    <span className="stat-value text-lg">
                      {marine.water_temp_c}°C
                    </span>
                  </div>
                )}
                {marine.tide_type && (
                  <div className="stat-card">
                    <div className="flex items-center gap-2">
                      <Waves className="w-4 h-4 text-cyan-400" />
                      <span className="stat-label">Tide</span>
                    </div>
                    <span className="stat-value text-sm text-white capitalize">
                      {marine.tide_type}
                    </span>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Coordinates & Actions */}
          <div className="pt-3 border-t border-slate-700/50">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2 text-sm text-slate-400">
                <MapPin className="w-4 h-4" />
                <span>
                  {lat?.toFixed(4)}°N, {lon?.toFixed(4)}°E
                </span>
              </div>
              <button
                onClick={() => onNavigate(location)}
                className="flex items-center gap-2 px-3 py-2 bg-cyan-500/20 hover:bg-cyan-500/30 rounded-lg text-cyan-400 text-sm font-medium transition-colors"
              >
                <Navigation className="w-4 h-4" />
                Navigate
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default LocationDetailModal;
