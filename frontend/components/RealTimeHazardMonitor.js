'use client';

import { useState, useEffect, useCallback, useRef } from 'react';
import {
  Activity,
  AlertTriangle,
  AlertCircle,
  Eye,
  CheckCircle,
  Shield,
  Waves,
  Wind,
  Zap,
  MapPin,
  Clock,
  RefreshCw,
  ChevronDown,
  ChevronUp,
  Radio,
  Globe,
  TrendingUp,
  AlertOctagon,
  Satellite
} from 'lucide-react';
import {
  getMultiHazardHealth,
  getPublicHazardAlerts,
  getHazardSummary,
  getThreatLevelColor,
  getThreatLevelInfo
} from '@/lib/api';

/**
 * Real-time Hazard Monitoring Widget
 * Displays live hazard monitoring status from the multi-hazard detection system
 */
export default function RealTimeHazardMonitor({
  latitude = null,
  longitude = null,
  compact = false,
  showHeader = true,
  refreshInterval = 60000, // 1 minute default
  onHazardDetected = null
}) {
  const [monitoringStatus, setMonitoringStatus] = useState(null);
  const [currentHazards, setCurrentHazards] = useState(null);
  const [serviceHealth, setServiceHealth] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [expanded, setExpanded] = useState(!compact);
  const [lastUpdate, setLastUpdate] = useState(null);
  const [isRefreshing, setIsRefreshing] = useState(false);

  // Track previously notified alerts to prevent duplicate notifications
  // Use sessionStorage to persist across page navigations within the same session
  const notifiedAlertIdsRef = useRef(new Set());
  const hasShownInitialNotificationRef = useRef(false);

  // Initialize refs from sessionStorage on mount
  useEffect(() => {
    if (typeof window !== 'undefined') {
      const storedIds = sessionStorage.getItem('notifiedHazardAlerts');
      if (storedIds) {
        try {
          const parsed = JSON.parse(storedIds);
          notifiedAlertIdsRef.current = new Set(parsed);
        } catch (e) {
          // Ignore parse errors
        }
      }
      hasShownInitialNotificationRef.current = sessionStorage.getItem('hazardAlertShown') === 'true';
    }
  }, []);

  // Fetch monitoring data
  const fetchMonitoringData = useCallback(async (showRefresh = false) => {
    try {
      if (showRefresh) setIsRefreshing(true);
      setError(null);

      // Fetch all data in parallel (using public endpoints for citizen access)
      const [healthRes, alertsRes] = await Promise.allSettled([
        getMultiHazardHealth(),
        getPublicHazardAlerts({ limit: 10 })
      ]);

      // Process health response (contains monitoring status)
      if (healthRes.status === 'fulfilled') {
        const healthData = healthRes.value;
        setServiceHealth(healthData);

        // Build monitoring status from health data
        setMonitoringStatus({
          monitoring_active: healthData.is_monitoring,
          active_sources: healthData.locations_count || 0,
          last_scan: healthData.last_cycle,
          coverage_area: 'Indian Ocean Region'
        });
      }

      // Process alerts response
      if (alertsRes.status === 'fulfilled') {
        const alertsData = alertsRes.value;

        // Map alert_level to severity for frontend compatibility
        const mapAlertLevel = (level) => {
          // alert_level: 1=LOW, 2=MODERATE, 3=HIGH, 4=SEVERE, 5=CRITICAL
          if (level >= 4) return 'warning';
          if (level >= 3) return 'alert';
          if (level >= 2) return 'watch';
          return 'no_threat';
        };

        // Build current hazards from alerts
        const rawAlerts = alertsData.alerts || [];
        // Normalize alert fields for frontend
        const alerts = rawAlerts.map(a => ({
          ...a,
          severity: a.severity || mapAlertLevel(a.alert_level),
          location: a.location_name || a.location
        }));

        const cycloneAlerts = alerts.filter(a => a.hazard_type === 'cyclone');
        const tsunamiAlerts = alerts.filter(a => a.hazard_type === 'tsunami');
        const earthquakeAlerts = alerts.filter(a => a.hazard_type === 'earthquake');

        setCurrentHazards({
          alerts: alerts,
          cyclone_threat: cycloneAlerts.length > 0 ? cycloneAlerts[0].severity || 'watch' : 'no_threat',
          tsunami_threat: tsunamiAlerts.length > 0 ? tsunamiAlerts[0].severity || 'watch' : 'no_threat',
          earthquake_threat: earthquakeAlerts.length > 0 ? earthquakeAlerts[0].severity || 'watch' : 'no_threat'
        });

        // Only notify for NEW alerts that haven't been shown yet
        // This prevents the notification from appearing on every page switch/refresh
        if (alerts.length > 0 && onHazardDetected) {
          // Generate unique IDs for alerts (use combination of type, location, and timestamp)
          const newAlerts = alerts.filter(alert => {
            const alertId = `${alert.hazard_type || alert.type}_${alert.location || ''}_${alert.alert_level || ''}`;
            if (!notifiedAlertIdsRef.current.has(alertId)) {
              notifiedAlertIdsRef.current.add(alertId);
              return true;
            }
            return false;
          });

          // Only call onHazardDetected if there are genuinely new alerts
          // AND we haven't shown the initial notification yet in this session
          if (newAlerts.length > 0 && !hasShownInitialNotificationRef.current) {
            hasShownInitialNotificationRef.current = true;
            // Persist to sessionStorage so it survives page navigation
            if (typeof window !== 'undefined') {
              sessionStorage.setItem('hazardAlertShown', 'true');
              sessionStorage.setItem('notifiedHazardAlerts', JSON.stringify([...notifiedAlertIdsRef.current]));
            }
            onHazardDetected(alerts);
          }
        }
      }

      setLastUpdate(new Date());
    } catch (err) {
      console.error('Hazard monitoring fetch error:', err);
      setError(err.message || 'Failed to fetch monitoring data');
    } finally {
      setLoading(false);
      setIsRefreshing(false);
    }
  }, [latitude, longitude, onHazardDetected]);

  // Initial fetch and interval setup
  useEffect(() => {
    fetchMonitoringData();

    const interval = setInterval(() => {
      fetchMonitoringData();
    }, refreshInterval);

    return () => clearInterval(interval);
  }, [fetchMonitoringData, refreshInterval]);

  // Get overall threat level
  const getOverallThreatLevel = () => {
    if (!currentHazards) return 'no_threat';

    const levels = ['warning', 'alert', 'watch', 'no_threat'];
    for (const level of levels) {
      if (
        currentHazards.cyclone_threat === level ||
        currentHazards.tsunami_threat === level ||
        currentHazards.earthquake_threat === level
      ) {
        return level;
      }
    }
    return 'no_threat';
  };

  // Get threat config based on level
  const getThreatConfig = (level) => {
    switch (level?.toLowerCase()) {
      case 'warning':
        return {
          icon: AlertTriangle,
          bg: 'bg-gradient-to-br from-red-500 to-red-600',
          lightBg: 'bg-red-50',
          border: 'border-red-200',
          text: 'text-white',
          lightText: 'text-red-700',
          dot: 'bg-red-500',
          pulse: true
        };
      case 'alert':
        return {
          icon: AlertCircle,
          bg: 'bg-gradient-to-br from-orange-500 to-orange-600',
          lightBg: 'bg-orange-50',
          border: 'border-orange-200',
          text: 'text-white',
          lightText: 'text-orange-700',
          dot: 'bg-orange-500',
          pulse: false
        };
      case 'watch':
        return {
          icon: Eye,
          bg: 'bg-gradient-to-br from-yellow-500 to-yellow-600',
          lightBg: 'bg-yellow-50',
          border: 'border-yellow-200',
          text: 'text-white',
          lightText: 'text-yellow-700',
          dot: 'bg-yellow-500',
          pulse: false
        };
      case 'no_threat':
      default:
        return {
          icon: CheckCircle,
          bg: 'bg-gradient-to-br from-green-500 to-green-600',
          lightBg: 'bg-green-50',
          border: 'border-green-200',
          text: 'text-white',
          lightText: 'text-green-700',
          dot: 'bg-green-500',
          pulse: false
        };
    }
  };

  // Loading state
  if (loading) {
    return (
      <div className="bg-white rounded-2xl shadow-lg border border-gray-200 p-6">
        <div className="flex items-center justify-center py-8">
          <div className="flex flex-col items-center gap-3">
            <div className="relative">
              <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-sky-500"></div>
              <Radio className="absolute inset-0 m-auto w-6 h-6 text-sky-500" />
            </div>
            <p className="text-sm text-gray-500">Connecting to monitoring systems...</p>
          </div>
        </div>
      </div>
    );
  }

  // Error state
  if (error && !monitoringStatus && !currentHazards) {
    return (
      <div className="bg-white rounded-2xl shadow-lg border border-gray-200 p-6">
        <div className="text-center py-6">
          <AlertOctagon className="w-12 h-12 text-orange-500 mx-auto mb-3" />
          <p className="text-sm font-medium text-gray-900 mb-1">Monitoring Unavailable</p>
          <p className="text-xs text-gray-500 mb-4">{error}</p>
          <button
            onClick={() => fetchMonitoringData(true)}
            className="px-4 py-2 text-sm font-medium text-sky-600 bg-sky-50 rounded-lg hover:bg-sky-100 transition-colors"
          >
            Retry Connection
          </button>
        </div>
      </div>
    );
  }

  const overallLevel = getOverallThreatLevel();
  const config = getThreatConfig(overallLevel);
  const ThreatIcon = config.icon;
  const threatInfo = getThreatLevelInfo(overallLevel);

  return (
    <div className="bg-white rounded-2xl shadow-lg border border-gray-200 overflow-hidden">
      {/* Header */}
      {showHeader && (
        <div
          className={`p-4 ${config.bg} ${config.text} cursor-pointer ${config.pulse ? 'animate-pulse' : ''}`}
          onClick={() => setExpanded(!expanded)}
        >
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="w-12 h-12 rounded-xl bg-white/20 flex items-center justify-center">
                <ThreatIcon className="w-6 h-6" />
              </div>
              <div>
                <p className="text-sm opacity-90">Real-time Monitoring</p>
                <h3 className="text-xl font-bold tracking-wide">
                  {threatInfo.label}
                </h3>
              </div>
            </div>
            <div className="flex items-center gap-3">
              <div className="flex items-center gap-2 text-sm opacity-90">
                <Radio className={`w-4 h-4 ${serviceHealth?.status === 'healthy' ? 'animate-pulse' : ''}`} />
                <span>{serviceHealth?.status === 'healthy' ? 'Live' : 'Offline'}</span>
              </div>
              {compact && (
                expanded ? <ChevronUp className="w-5 h-5 opacity-70" /> : <ChevronDown className="w-5 h-5 opacity-70" />
              )}
            </div>
          </div>
        </div>
      )}

      {/* Content */}
      {expanded && (
        <div className="p-4 space-y-4">
          {/* Hazard Type Grid */}
          <div className="grid grid-cols-3 gap-3">
            <HazardTypeCard
              icon={Wind}
              label="Cyclone"
              level={currentHazards?.cyclone_threat || 'no_threat'}
              active={monitoringStatus?.monitoring_active}
            />
            <HazardTypeCard
              icon={Waves}
              label="Tsunami"
              level={currentHazards?.tsunami_threat || 'no_threat'}
              active={monitoringStatus?.monitoring_active}
            />
            <HazardTypeCard
              icon={Zap}
              label="Earthquake"
              level={currentHazards?.earthquake_threat || 'no_threat'}
              active={monitoringStatus?.monitoring_active}
            />
          </div>

          {/* Active Alerts */}
          {currentHazards?.alerts && currentHazards.alerts.length > 0 && (
            <div className="bg-red-50 rounded-xl p-4 border border-red-200">
              <h4 className="text-sm font-bold text-red-800 mb-3 flex items-center gap-2">
                <AlertTriangle className="w-4 h-4" />
                Active Alerts ({currentHazards.alerts.length})
              </h4>
              <div className="space-y-2">
                {currentHazards.alerts.slice(0, 3).map((alert, index) => (
                  <AlertItem key={index} alert={alert} />
                ))}
              </div>
            </div>
          )}

          {/* Monitoring Status */}
          {monitoringStatus && (
            <div className="bg-gray-50 rounded-xl p-4">
              <h4 className="text-sm font-bold text-gray-900 mb-3 flex items-center gap-2">
                <Satellite className="w-4 h-4 text-sky-600" />
                System Status
              </h4>
              <div className="grid grid-cols-2 gap-3">
                <StatusItem
                  label="Monitoring"
                  value={monitoringStatus.monitoring_active ? 'Active' : 'Inactive'}
                  status={monitoringStatus.monitoring_active}
                />
                <StatusItem
                  label="Data Sources"
                  value={`${monitoringStatus.active_sources || 0} online`}
                  status={monitoringStatus.active_sources > 0}
                />
                <StatusItem
                  label="Last Scan"
                  value={monitoringStatus.last_scan ? formatTimeAgo(monitoringStatus.last_scan) : 'N/A'}
                  status={true}
                />
                <StatusItem
                  label="Coverage"
                  value={monitoringStatus.coverage_area || 'Global'}
                  status={true}
                />
              </div>
            </div>
          )}

          {/* Data Sources */}
          {serviceHealth?.data_sources && (
            <div className="border-t border-gray-100 pt-4">
              <h4 className="text-xs font-semibold text-gray-500 mb-2 flex items-center gap-2">
                <Globe className="w-3 h-3" />
                DATA SOURCES
              </h4>
              <div className="flex flex-wrap gap-2">
                {Object.entries(serviceHealth.data_sources).map(([source, status]) => (
                  <DataSourceBadge key={source} name={source} status={status} />
                ))}
              </div>
            </div>
          )}

          {/* Footer */}
          <div className="flex items-center justify-between text-xs text-gray-400 pt-2 border-t border-gray-100">
            <div className="flex items-center gap-1">
              <Clock className="w-3 h-3" />
              <span>
                {lastUpdate ? `Updated ${lastUpdate.toLocaleTimeString()}` : 'Waiting for update...'}
              </span>
            </div>
            <button
              onClick={() => fetchMonitoringData(true)}
              disabled={isRefreshing}
              className="flex items-center gap-1 text-sky-500 hover:text-sky-600 disabled:opacity-50"
            >
              <RefreshCw className={`w-3 h-3 ${isRefreshing ? 'animate-spin' : ''}`} />
              Refresh
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

// Hazard type card component
function HazardTypeCard({ icon: Icon, label, level, active }) {
  const getCardStyle = (level) => {
    switch (level?.toLowerCase()) {
      case 'warning':
        return { bg: 'bg-red-100', text: 'text-red-700', icon: 'text-red-600', dot: 'bg-red-500' };
      case 'alert':
        return { bg: 'bg-orange-100', text: 'text-orange-700', icon: 'text-orange-600', dot: 'bg-orange-500' };
      case 'watch':
        return { bg: 'bg-yellow-100', text: 'text-yellow-700', icon: 'text-yellow-600', dot: 'bg-yellow-500' };
      default:
        return { bg: 'bg-green-100', text: 'text-green-700', icon: 'text-green-600', dot: 'bg-green-500' };
    }
  };

  const style = getCardStyle(level);

  return (
    <div className={`${style.bg} rounded-xl p-3 text-center relative`}>
      {active && (
        <div className="absolute top-2 right-2">
          <span className={`w-2 h-2 rounded-full ${style.dot} inline-block animate-pulse`}></span>
        </div>
      )}
      <Icon className={`w-6 h-6 ${style.icon} mx-auto mb-2`} />
      <p className="text-xs font-medium text-gray-600 mb-1">{label}</p>
      <p className={`text-xs font-bold ${style.text} uppercase`}>
        {level?.replace('_', ' ') || 'OK'}
      </p>
    </div>
  );
}

// Alert item component
function AlertItem({ alert }) {
  const getAlertIcon = (type) => {
    switch (type?.toLowerCase()) {
      case 'cyclone': return Wind;
      case 'tsunami': return Waves;
      case 'earthquake': return Zap;
      default: return AlertTriangle;
    }
  };

  const Icon = getAlertIcon(alert.type);

  return (
    <div className="flex items-start gap-3 bg-white rounded-lg p-3 border border-red-100">
      <div className="p-1.5 bg-red-100 rounded-lg">
        <Icon className="w-4 h-4 text-red-600" />
      </div>
      <div className="flex-1 min-w-0">
        <p className="text-sm font-semibold text-gray-900 truncate">
          {alert.title || `${alert.type} Alert`}
        </p>
        {alert.location && (
          <p className="text-xs text-gray-500 flex items-center gap-1 mt-0.5">
            <MapPin className="w-3 h-3" />
            {alert.location}
          </p>
        )}
        {alert.magnitude && (
          <p className="text-xs text-gray-500 mt-0.5">
            Magnitude: {alert.magnitude}
          </p>
        )}
      </div>
      {alert.severity && (
        <span className={`px-2 py-0.5 text-xs font-bold rounded-full ${
          alert.severity === 'high' ? 'bg-red-500 text-white' :
          alert.severity === 'medium' ? 'bg-orange-500 text-white' :
          'bg-yellow-500 text-white'
        }`}>
          {alert.severity.toUpperCase()}
        </span>
      )}
    </div>
  );
}

// Status item component
function StatusItem({ label, value, status }) {
  return (
    <div className="flex items-center gap-2">
      <span className={`w-2 h-2 rounded-full ${status ? 'bg-green-500' : 'bg-gray-300'}`}></span>
      <div>
        <p className="text-xs text-gray-500">{label}</p>
        <p className="text-sm font-medium text-gray-900">{value}</p>
      </div>
    </div>
  );
}

// Data source badge component
function DataSourceBadge({ name, status }) {
  const isOnline = status === 'online' || status === true || status === 'healthy';

  return (
    <span className={`inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium ${
      isOnline ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-500'
    }`}>
      <span className={`w-1.5 h-1.5 rounded-full ${isOnline ? 'bg-green-500' : 'bg-gray-400'}`}></span>
      {formatSourceName(name)}
    </span>
  );
}

// Utility function to format source names
function formatSourceName(name) {
  const names = {
    'usgs': 'USGS',
    'noaa': 'NOAA',
    'jma': 'JMA',
    'incois': 'INCOIS',
    'imd': 'IMD',
    'gdacs': 'GDACS',
    'weather_api': 'Weather API'
  };
  return names[name?.toLowerCase()] || name;
}

// Utility function to format time ago
function formatTimeAgo(timestamp) {
  const now = new Date();
  const then = new Date(timestamp);
  const diff = Math.floor((now - then) / 1000);

  if (diff < 60) return 'Just now';
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
  if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
  return then.toLocaleDateString();
}

/**
 * Compact Monitoring Badge
 * For displaying monitoring status inline
 */
export function MonitoringBadge({ level = 'no_threat', showLabel = true, size = 'md' }) {
  const config = {
    warning: { bg: 'bg-red-500', text: 'text-white', icon: AlertTriangle },
    alert: { bg: 'bg-orange-500', text: 'text-white', icon: AlertCircle },
    watch: { bg: 'bg-yellow-500', text: 'text-white', icon: Eye },
    no_threat: { bg: 'bg-green-500', text: 'text-white', icon: CheckCircle }
  };

  const sizeClasses = {
    sm: 'px-2 py-0.5 text-xs',
    md: 'px-3 py-1 text-sm',
    lg: 'px-4 py-2 text-base'
  };

  const badgeConfig = config[level?.toLowerCase()] || config.no_threat;
  const Icon = badgeConfig.icon;

  return (
    <span className={`inline-flex items-center gap-1 ${badgeConfig.bg} ${badgeConfig.text} ${sizeClasses[size]} rounded-full font-semibold`}>
      <Icon className={size === 'sm' ? 'w-3 h-3' : size === 'lg' ? 'w-5 h-5' : 'w-4 h-4'} />
      {showLabel && (
        <span className="uppercase tracking-wide">
          {level?.replace('_', ' ') || 'Safe'}
        </span>
      )}
    </span>
  );
}

/**
 * Mini Hazard Status Indicator
 * Tiny indicator for headers/navbars
 */
export function HazardStatusIndicator({ onClick }) {
  const [status, setStatus] = useState('loading');
  const [threatLevel, setThreatLevel] = useState('no_threat');

  useEffect(() => {
    const checkStatus = async () => {
      try {
        const [healthRes, alertsRes] = await Promise.all([
          getMultiHazardHealth(),
          getPublicHazardAlerts({ limit: 5 })
        ]);

        if (healthRes?.status === 'healthy') {
          setStatus('online');

          // Determine highest threat from alerts
          const alerts = alertsRes?.alerts || [];
          if (alerts.length > 0) {
            // Find highest severity alert
            const severityOrder = { warning: 3, alert: 2, watch: 1 };
            let highestLevel = 'no_threat';
            let highestScore = 0;

            for (const alert of alerts) {
              const score = severityOrder[alert.severity] || 0;
              if (score > highestScore) {
                highestScore = score;
                highestLevel = alert.severity;
              }
            }
            setThreatLevel(highestLevel);
          } else {
            setThreatLevel('no_threat');
          }
        } else {
          setStatus('offline');
        }
      } catch {
        setStatus('offline');
      }
    };

    checkStatus();
    const interval = setInterval(checkStatus, 60000);
    return () => clearInterval(interval);
  }, []);

  const getColor = () => {
    if (status === 'loading') return 'bg-gray-400';
    if (status === 'offline') return 'bg-gray-400';
    switch (threatLevel) {
      case 'warning': return 'bg-red-500 animate-pulse';
      case 'alert': return 'bg-orange-500';
      case 'watch': return 'bg-yellow-500';
      default: return 'bg-green-500';
    }
  };

  return (
    <button
      onClick={onClick}
      className="relative flex items-center gap-2 px-3 py-1.5 bg-gray-100 hover:bg-gray-200 rounded-full transition-colors"
      title="Hazard Monitoring Status"
    >
      <span className={`w-2.5 h-2.5 rounded-full ${getColor()}`}></span>
      <span className="text-xs font-medium text-gray-700">
        {status === 'loading' ? 'Loading...' : status === 'offline' ? 'Offline' : threatLevel === 'no_threat' ? 'All Clear' : threatLevel.replace('_', ' ').toUpperCase()}
      </span>
    </button>
  );
}
