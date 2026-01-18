'use client';

import React from 'react';
import {
  Compass,
  ChevronRight,
  ChevronLeft,
  AlertTriangle,
  Waves,
  Wind,
  CloudRain,
  Activity,
  Droplets,
  MapPin,
  Clock,
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
 * MapInfoPanel - Right sidebar with locations and alerts
 */
export function MapInfoPanel({
  locations = [],
  alerts = [],
  reports = [],
  statistics = {},
  selectedLocation = null,
  onLocationSelect = () => {},
  isExpanded = true,
  onToggleExpand = () => {},
  lastUpdate = null,
  isConnected = false,
}) {
  // Sort locations by alert level (highest first)
  const sortedLocations = [...locations].sort(
    (a, b) => (b.alert_level || b.max_alert_level || 1) - (a.alert_level || a.max_alert_level || 1)
  );

  // Format time ago
  const formatTimeAgo = (date) => {
    if (!date) return 'Never';
    const seconds = Math.floor((new Date() - date) / 1000);
    if (seconds < 60) return 'Just now';
    if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`;
    if (seconds < 86400) return `${Math.floor(seconds / 3600)}h ago`;
    return `${Math.floor(seconds / 86400)}d ago`;
  };

  return (
    <div
      className={`map-sidebar ${!isExpanded ? 'collapsed' : ''}`}
    >
      <div className="glass-panel-dark h-full flex flex-col overflow-hidden">
        {/* Mobile Handle */}
        <div className="md:hidden map-sidebar-handle" onClick={onToggleExpand} />

        {/* Toggle Button (Desktop) */}
        <button
          onClick={onToggleExpand}
          className="absolute -left-10 top-1/2 -translate-y-1/2 p-2 glass-panel rounded-l-xl hidden md:flex hover:bg-slate-700/50 transition-colors"
        >
          {isExpanded ? (
            <ChevronRight className="w-5 h-5 text-slate-400" />
          ) : (
            <ChevronLeft className="w-5 h-5 text-slate-400" />
          )}
        </button>

        {/* Header */}
        <div className="p-4 md:p-4 border-b border-slate-700/50">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Compass className="w-5 h-5 text-cyan-400" />
              <h2 className="font-bold text-white">Coastal Monitor</h2>
            </div>
            <span className="text-xs text-slate-400">
              {locations.length} stations
            </span>
          </div>

          {/* Connection Status */}
          <div className="flex items-center gap-2 mt-2">
            <div
              className={`w-2 h-2 rounded-full ${
                isConnected ? 'bg-emerald-400 animate-pulse' : 'bg-red-400'
              }`}
            />
            <span className="text-xs text-slate-400">
              {isConnected ? 'Live' : 'Disconnected'} • Updated {formatTimeAgo(lastUpdate)}
            </span>
          </div>
        </div>

        {/* Statistics Bar */}
        <div className="p-3 bg-slate-800/30 border-b border-slate-700/50 grid grid-cols-3 gap-2">
          <div className="stat-card">
            <span className="stat-value text-red-400">
              {statistics.criticalAlerts || 0}
            </span>
            <span className="stat-label">Critical</span>
          </div>
          <div className="stat-card">
            <span className="stat-value text-orange-400">
              {statistics.warningAlerts || 0}
            </span>
            <span className="stat-label">Warning</span>
          </div>
          <div className="stat-card">
            <span className="stat-value text-yellow-400">
              {statistics.watchAlerts || 0}
            </span>
            <span className="stat-label">Watch</span>
          </div>
        </div>

        {/* Active Alerts Section */}
        {alerts.length > 0 && (
          <div className="p-3 border-b border-slate-700/50">
            <div className="flex items-center justify-between mb-2">
              <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
                Active Alerts
              </p>
              <span className="text-xs text-slate-500">{alerts.length}</span>
            </div>
            <div className="space-y-2 max-h-40 overflow-y-auto pr-1">
              {alerts.slice(0, 5).map((alert, idx) => {
                const config = ALERT_CONFIG[alert.alert_level] || ALERT_CONFIG[3];
                const HazardIcon = HAZARD_ICONS[alert.hazard_type] || AlertTriangle;
                const location = locations.find((l) => l.location_id === alert.location_id);

                return (
                  <div
                    key={alert.alert_id || idx}
                    className="location-item"
                    style={{ background: `${config.color}10` }}
                    onClick={() => location && onLocationSelect(location)}
                  >
                    <div
                      className="location-item-icon"
                      style={{ background: config.gradient }}
                    >
                      <HazardIcon className="w-5 h-5 text-white" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium text-white truncate">
                        {alert.location_name || location?.location_name || 'Unknown'}
                      </p>
                      <p className="text-xs text-slate-400 capitalize">
                        {alert.hazard_type?.replace(/_/g, ' ')}
                      </p>
                    </div>
                    <span
                      className="px-2 py-1 rounded-lg text-xs font-bold text-white"
                      style={{ background: config.gradient }}
                    >
                      L{alert.alert_level}
                    </span>
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {/* Locations List */}
        <div className="flex-1 overflow-y-auto map-sidebar-content">
          <div className="p-3">
            <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">
              Monitored Locations
            </p>
            <div className="space-y-1">
              {sortedLocations.map((location) => {
                const alertLevel = location.alert_level || location.max_alert_level || 1;
                const config = ALERT_CONFIG[alertLevel];
                const isSelected = selectedLocation?.location_id === location.location_id;

                return (
                  <button
                    key={location.location_id}
                    onClick={() => onLocationSelect(location)}
                    className={`location-item w-full text-left ${isSelected ? 'active' : ''}`}
                  >
                    <div
                      className="location-item-icon"
                      style={{ background: config.gradient }}
                    >
                      <span className="text-white font-bold text-sm">{alertLevel}</span>
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="font-medium text-white truncate text-sm">
                        {location.location_name || location.name}
                      </p>
                      <p className="text-xs text-slate-400">{location.region}</p>
                    </div>
                    <ChevronRight className="w-4 h-4 text-slate-500" />
                  </button>
                );
              })}
            </div>
          </div>
        </div>

        {/* Recent Reports Section (24h) */}
        {reports.length > 0 && (
          <div className="p-3 border-t border-slate-700/50 bg-slate-800/30">
            <div className="flex items-center gap-2 mb-1">
              <Clock className="w-3 h-3 text-cyan-400" />
              <p className="text-xs font-semibold text-slate-400">
                Last 24 Hours
              </p>
            </div>
            <p className="text-sm text-white">
              <span className="font-bold text-cyan-400">{reports.length}</span> citizen reports
            </p>
          </div>
        )}
      </div>
    </div>
  );
}

export default MapInfoPanel;
