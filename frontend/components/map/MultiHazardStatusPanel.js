'use client';

import { useState } from 'react';
import {
  AlertTriangle,
  Waves,
  Wind,
  CloudRain,
  Activity,
  MapPin,
  Clock,
  ChevronDown,
  ChevronUp,
  RefreshCw,
  CheckCircle2,
  XCircle,
  Loader2
} from 'lucide-react';

// Alert level configuration (1-5 scale)
const ALERT_LEVELS = {
  5: { name: 'CRITICAL', color: 'bg-red-500', textColor: 'text-red-700', bgLight: 'bg-red-100' },
  4: { name: 'WARNING', color: 'bg-orange-500', textColor: 'text-orange-700', bgLight: 'bg-orange-100' },
  3: { name: 'WATCH', color: 'bg-yellow-400', textColor: 'text-yellow-700', bgLight: 'bg-yellow-100' },
  2: { name: 'ADVISORY', color: 'bg-blue-500', textColor: 'text-blue-700', bgLight: 'bg-blue-100' },
  1: { name: 'NORMAL', color: 'bg-green-500', textColor: 'text-green-700', bgLight: 'bg-green-100' },
};

// Hazard type icons and labels
const HAZARD_TYPES = {
  tsunami: { icon: Waves, label: 'Tsunami', color: 'text-blue-600' },
  cyclone: { icon: Wind, label: 'Cyclone', color: 'text-purple-600' },
  high_waves: { icon: Waves, label: 'High Waves', color: 'text-cyan-600' },
  coastal_flood: { icon: CloudRain, label: 'Coastal Flood', color: 'text-teal-600' },
  rip_currents: { icon: Activity, label: 'Rip Currents', color: 'text-indigo-600' },
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

export function MultiHazardStatusPanel({
  data,
  isConnected,
  isLoading,
  onRefresh,
  onLocationSelect,
  className = ''
}) {
  const [isExpanded, setIsExpanded] = useState(true);
  const [activeTab, setActiveTab] = useState('locations'); // 'locations', 'alerts', 'earthquakes'

  if (!data) {
    return (
      <div className={`bg-white rounded-xl border border-gray-200 ${className}`}>
        <div className="p-4 flex items-center justify-center">
          {isLoading ? (
            <Loader2 className="w-6 h-6 text-blue-600 animate-spin" />
          ) : (
            <p className="text-gray-500 text-sm">No MultiHazard data available</p>
          )}
        </div>
      </div>
    );
  }

  const { locations = [], alerts = [], summary, earthquakes = [] } = data;

  // Calculate summary stats
  const criticalCount = locations.filter(l => (l.max_alert_level || 1) >= 5).length;
  const warningCount = locations.filter(l => (l.max_alert_level || 1) === 4).length;
  const activeAlerts = alerts.filter(a => a.alert_level >= 4).length;

  return (
    <div className={`bg-white rounded-xl border border-gray-200 overflow-hidden ${className}`}>
      {/* Header */}
      <div
        className="p-4 border-b border-gray-200 flex items-center justify-between cursor-pointer hover:bg-gray-50"
        onClick={() => setIsExpanded(!isExpanded)}
      >
        <div className="flex items-center gap-3">
          <div className="p-2 bg-purple-100 rounded-lg">
            <Waves className="w-5 h-5 text-purple-600" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h3 className="font-semibold text-gray-900">MultiHazard Detection</h3>
              {isConnected ? (
                <span className="flex items-center gap-1 text-xs text-green-600">
                  <CheckCircle2 className="w-3 h-3" /> Connected
                </span>
              ) : (
                <span className="flex items-center gap-1 text-xs text-red-600">
                  <XCircle className="w-3 h-3" /> Offline
                </span>
              )}
            </div>
            <p className="text-xs text-gray-500">
              {locations.length} location{locations.length !== 1 ? 's' : ''} monitored
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          {onRefresh && (
            <button
              onClick={(e) => { e.stopPropagation(); onRefresh(); }}
              className="p-1.5 text-gray-500 hover:text-blue-600 hover:bg-blue-50 rounded-lg transition-colors"
              disabled={isLoading}
            >
              <RefreshCw className={`w-4 h-4 ${isLoading ? 'animate-spin' : ''}`} />
            </button>
          )}
          {isExpanded ? (
            <ChevronUp className="w-5 h-5 text-gray-400" />
          ) : (
            <ChevronDown className="w-5 h-5 text-gray-400" />
          )}
        </div>
      </div>

      {isExpanded && (
        <>
          {/* Quick Stats */}
          <div className="grid grid-cols-3 gap-2 p-3 bg-gray-50 border-b border-gray-200">
            <div className="text-center p-2 bg-white rounded-lg">
              <p className="text-lg font-bold text-red-600">{criticalCount}</p>
              <p className="text-[10px] text-gray-500 uppercase">Critical</p>
            </div>
            <div className="text-center p-2 bg-white rounded-lg">
              <p className="text-lg font-bold text-orange-600">{warningCount}</p>
              <p className="text-[10px] text-gray-500 uppercase">Warning</p>
            </div>
            <div className="text-center p-2 bg-white rounded-lg">
              <p className="text-lg font-bold text-blue-600">{activeAlerts}</p>
              <p className="text-[10px] text-gray-500 uppercase">Active</p>
            </div>
          </div>

          {/* Tabs */}
          <div className="flex border-b border-gray-200">
            <button
              onClick={() => setActiveTab('locations')}
              className={`flex-1 py-2 text-xs font-medium transition-colors ${
                activeTab === 'locations'
                  ? 'text-blue-600 border-b-2 border-blue-600 bg-blue-50'
                  : 'text-gray-500 hover:text-gray-700'
              }`}
            >
              Locations ({locations.length})
            </button>
            <button
              onClick={() => setActiveTab('alerts')}
              className={`flex-1 py-2 text-xs font-medium transition-colors ${
                activeTab === 'alerts'
                  ? 'text-blue-600 border-b-2 border-blue-600 bg-blue-50'
                  : 'text-gray-500 hover:text-gray-700'
              }`}
            >
              Alerts ({alerts.length})
            </button>
            <button
              onClick={() => setActiveTab('earthquakes')}
              className={`flex-1 py-2 text-xs font-medium transition-colors ${
                activeTab === 'earthquakes'
                  ? 'text-blue-600 border-b-2 border-blue-600 bg-blue-50'
                  : 'text-gray-500 hover:text-gray-700'
              }`}
            >
              Seismic ({earthquakes.length})
            </button>
          </div>

          {/* Content */}
          <div className="max-h-[300px] overflow-y-auto">
            {/* Locations Tab */}
            {activeTab === 'locations' && (
              <div className="divide-y divide-gray-100">
                {locations.length > 0 ? (
                  locations.map((location) => {
                    const alertLevel = location.max_alert_level || 1;
                    const config = ALERT_LEVELS[alertLevel] || ALERT_LEVELS[1];
                    const activeHazards = location.active_hazards || [];

                    return (
                      <button
                        key={location.location_id}
                        onClick={() => onLocationSelect?.(location)}
                        className="w-full p-3 text-left hover:bg-gray-50 transition-colors"
                      >
                        <div className="flex items-start gap-3">
                          <div className={`w-8 h-8 ${config.bgLight} rounded-full flex items-center justify-center flex-shrink-0`}>
                            <span className={`text-sm font-bold ${config.textColor}`}>{alertLevel}</span>
                          </div>
                          <div className="flex-1 min-w-0">
                            <div className="flex items-center justify-between">
                              <p className="font-medium text-gray-900 truncate">
                                {location.location_name || location.name}
                              </p>
                              <span className={`text-[10px] px-1.5 py-0.5 rounded ${config.bgLight} ${config.textColor}`}>
                                {config.name}
                              </span>
                            </div>
                            {activeHazards.length > 0 && (
                              <div className="flex flex-wrap gap-1 mt-1">
                                {activeHazards.slice(0, 3).map((hazard, idx) => {
                                  const hazardType = HAZARD_TYPES[hazard.hazard_type] || {
                                    label: hazard.hazard_type,
                                    color: 'text-gray-600'
                                  };
                                  return (
                                    <span
                                      key={idx}
                                      className="text-[10px] px-1.5 py-0.5 bg-gray-100 text-gray-600 rounded"
                                    >
                                      {hazardType.label}
                                    </span>
                                  );
                                })}
                                {activeHazards.length > 3 && (
                                  <span className="text-[10px] text-gray-400">
                                    +{activeHazards.length - 3} more
                                  </span>
                                )}
                              </div>
                            )}
                            <p className="text-[10px] text-gray-400 mt-1">
                              Updated {formatTimeAgo(location.last_updated)}
                            </p>
                          </div>
                        </div>
                      </button>
                    );
                  })
                ) : (
                  <div className="p-6 text-center text-gray-500 text-sm">
                    No locations monitored
                  </div>
                )}
              </div>
            )}

            {/* Alerts Tab */}
            {activeTab === 'alerts' && (
              <div className="divide-y divide-gray-100">
                {alerts.length > 0 ? (
                  alerts.map((alert, idx) => {
                    const config = ALERT_LEVELS[alert.alert_level] || ALERT_LEVELS[3];
                    const hazardType = HAZARD_TYPES[alert.hazard_type] || {
                      icon: AlertTriangle,
                      label: alert.hazard_type?.replace('_', ' ') || 'Unknown',
                      color: 'text-gray-600'
                    };
                    const HazardIcon = hazardType.icon;

                    return (
                      <div key={alert.alert_id || idx} className="p-3">
                        <div className="flex items-start gap-3">
                          <div className={`p-1.5 rounded-lg ${config.bgLight}`}>
                            <HazardIcon className={`w-4 h-4 ${hazardType.color}`} />
                          </div>
                          <div className="flex-1 min-w-0">
                            <div className="flex items-center justify-between">
                              <p className="font-medium text-sm text-gray-900">
                                {hazardType.label}
                              </p>
                              <span className={`text-[10px] px-1.5 py-0.5 rounded ${config.bgLight} ${config.textColor}`}>
                                L{alert.alert_level}
                              </span>
                            </div>
                            <p className="text-xs text-gray-600 mt-0.5">
                              {alert.location_name || 'Unknown location'}
                            </p>
                            {alert.confidence && (
                              <p className="text-[10px] text-gray-400 mt-1">
                                Confidence: {(alert.confidence * 100).toFixed(0)}%
                              </p>
                            )}
                            {alert.recommendations?.[0] && (
                              <p className="text-[10px] text-red-600 mt-1 font-medium">
                                {alert.recommendations[0]}
                              </p>
                            )}
                          </div>
                        </div>
                      </div>
                    );
                  })
                ) : (
                  <div className="p-6 text-center text-gray-500 text-sm">
                    No active alerts
                  </div>
                )}
              </div>
            )}

            {/* Earthquakes Tab */}
            {activeTab === 'earthquakes' && (
              <div className="divide-y divide-gray-100">
                {earthquakes.length > 0 ? (
                  earthquakes.map((quake, idx) => (
                    <div key={quake.id || idx} className="p-3">
                      <div className="flex items-start gap-3">
                        <div className={`w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 ${
                          quake.magnitude >= 6 ? 'bg-red-100' :
                          quake.magnitude >= 5 ? 'bg-orange-100' :
                          quake.magnitude >= 4 ? 'bg-yellow-100' : 'bg-blue-100'
                        }`}>
                          <span className={`text-sm font-bold ${
                            quake.magnitude >= 6 ? 'text-red-700' :
                            quake.magnitude >= 5 ? 'text-orange-700' :
                            quake.magnitude >= 4 ? 'text-yellow-700' : 'text-blue-700'
                          }`}>
                            {quake.magnitude?.toFixed(1)}
                          </span>
                        </div>
                        <div className="flex-1 min-w-0">
                          <p className="font-medium text-sm text-gray-900 truncate">
                            {quake.place || 'Unknown location'}
                          </p>
                          <p className="text-xs text-gray-500 mt-0.5">
                            Depth: {quake.depth?.toFixed(1)} km
                          </p>
                          <p className="text-[10px] text-gray-400 mt-1">
                            {formatTimeAgo(quake.time)}
                          </p>
                        </div>
                      </div>
                    </div>
                  ))
                ) : (
                  <div className="p-6 text-center text-gray-500 text-sm">
                    No recent seismic activity
                  </div>
                )}
              </div>
            )}
          </div>
        </>
      )}
    </div>
  );
}

export default MultiHazardStatusPanel;
