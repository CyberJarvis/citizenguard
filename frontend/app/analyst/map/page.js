'use client';

import React, { useState, useCallback, useEffect, useRef } from 'react';
import dynamic from 'next/dynamic';
import {
  Waves,
  AlertTriangle,
  CloudLightning,
  Menu,
  X,
  Layers,
  RefreshCw,
  Bell,
  BellOff,
  ChevronUp,
  ChevronDown,
  MapPin,
  Navigation,
  Search,
  Home,
  Settings,
  Info,
  Compass,
  Activity,
  Thermometer,
  Droplets,
  Wind,
  Clock,
  ChevronRight,
  ChevronLeft,
  ArrowLeft,
  FileText,
  MessageCircle,
  Map,
  PanelRight,
  Play,
  Trash2
} from 'lucide-react';
import axios from 'axios';
import ProtectedRoute from '@/components/ProtectedRoute';
import { useMapData } from '@/hooks/useMapData';
import { getCycloneData } from '@/lib/api';
import { requestNotificationPermission, isNotificationEnabled, checkAndNotifyNewAlerts } from '@/lib/notifications';
import toast, { Toaster } from 'react-hot-toast';
import 'leaflet/dist/leaflet.css';
import '@/styles/map.css';

// Dynamic imports for map components (SSR-safe)
const OceanMap = dynamic(
  () => import('@/components/map/OceanMap').then((mod) => mod.OceanMap),
  {
    ssr: false,
    loading: () => <MapLoadingState />,
  }
);

const HeatmapLayer = dynamic(
  () => import('@/components/map/HeatmapLayer').then((mod) => mod.HeatmapLayer),
  { ssr: false }
);

const ClusterLayer = dynamic(
  () => import('@/components/map/ClusterLayer').then((mod) => mod.ClusterLayer),
  { ssr: false }
);

const CycloneLayer = dynamic(
  () => import('@/components/map/CycloneLayer').then((mod) => mod.CycloneLayer),
  { ssr: false }
);

const WaveTrackLayer = dynamic(
  () => import('@/components/map/WaveTrackLayer').then((mod) => mod.WaveTrackLayer),
  { ssr: false }
);

const LocationDetailModal = dynamic(
  () => import('@/components/map/LocationDetailModal').then((mod) => mod.LocationDetailModal),
  { ssr: false }
);

// Alert level configuration
const ALERT_CONFIG = {
  5: { name: 'CRITICAL', color: '#ef4444', bg: 'bg-red-500', gradient: 'linear-gradient(135deg, #ef4444 0%, #dc2626 100%)' },
  4: { name: 'WARNING', color: '#f97316', bg: 'bg-orange-500', gradient: 'linear-gradient(135deg, #f97316 0%, #ea580c 100%)' },
  3: { name: 'WATCH', color: '#eab308', bg: 'bg-yellow-500', gradient: 'linear-gradient(135deg, #eab308 0%, #ca8a04 100%)' },
  2: { name: 'ADVISORY', color: '#3b82f6', bg: 'bg-blue-500', gradient: 'linear-gradient(135deg, #3b82f6 0%, #2563eb 100%)' },
  1: { name: 'NORMAL', color: '#22c55e', bg: 'bg-emerald-500', gradient: 'linear-gradient(135deg, #22c55e 0%, #16a34a 100%)' },
};

// Hazard icons mapping
const HAZARD_ICONS = {
  cyclone: Wind,
  high_waves: Waves,
  coastal_flood: Droplets,
  rip_currents: Activity,
  tsunami: Waves,
  storm_surge: Droplets,
  earthquake: Activity,
  rip_current: Activity,
};

// Loading state component
function MapLoadingState() {
  return (
    <div className="flex items-center justify-center h-screen bg-slate-900">
      <div className="text-center">
        <div className="relative w-20 h-20 mx-auto mb-6">
          <div className="absolute inset-0 border-4 border-[#1a6b9a]/30 rounded-full animate-ping" />
          <div className="absolute inset-2 border-4 border-t-[#4391c4] border-r-transparent border-b-transparent border-l-transparent rounded-full animate-spin" />
          <Waves className="absolute inset-0 m-auto w-8 h-8 text-[#4391c4]" />
        </div>
        <p className="text-[#c5e1f5] text-lg font-medium">Loading Ocean Hazard Map...</p>
        <p className="text-slate-400 text-sm mt-2">Connecting to monitoring stations</p>
      </div>
    </div>
  );
}

// Main map content component
function OceanMapContent() {
  // State
  const [mapStyle, setMapStyle] = useState('esriOcean');
  const [showHeatmap, setShowHeatmap] = useState(true);
  const [showClusters, setShowClusters] = useState(true);
  const [showCyclone, setShowCyclone] = useState(true);
  const [showSurge, setShowSurge] = useState(true);
  const [heatmapOpacity, setHeatmapOpacity] = useState(0.7);
  const [notificationsEnabled, setNotificationsEnabled] = useState(false);
  const [selectedLocation, setSelectedLocation] = useState(null);
  const [showDetailModal, setShowDetailModal] = useState(false);
  const [showOceanCurrents, setShowOceanCurrents] = useState(true);
  const [showWaveHeight, setShowWaveHeight] = useState(true);

  // Sidebar state - right panel open by default on desktop
  const [rightPanelOpen, setRightPanelOpen] = useState(true);
  const [leftNavOpen, setLeftNavOpen] = useState(false);
  const [activeTab, setActiveTab] = useState('locations'); // 'locations', 'alerts', 'layers'
  const [mobileSheetOpen, setMobileSheetOpen] = useState(false);
  const [mobileSheetHeight, setMobileSheetHeight] = useState('peek'); // 'peek', 'half', 'full'

  // Cyclone data state
  const [cycloneData, setCycloneData] = useState(null);
  const [surgeData, setSurgeData] = useState(null);
  const [hasCyclone, setHasCyclone] = useState(false);
  const [showDemoCyclone, setShowDemoCyclone] = useState(false);
  const [isDemo, setIsDemo] = useState(false);

  const mapRef = useRef(null);
  const previousAlertsRef = useRef([]);

  // Data hook
  const {
    locations,
    alerts,
    reports,
    heatmapPoints,
    statistics,
    isLoading,
    isRefreshing,
    isConnected,
    lastUpdate,
    refresh,
  } = useMapData({
    refreshInterval: 60000,
    hoursFilter: 24,
    autoRefresh: true,
  });

  // Initialize notifications
  useEffect(() => {
    setNotificationsEnabled(isNotificationEnabled());
  }, []);

  // Fetch cyclone data
  useEffect(() => {
    const fetchCycloneData = async () => {
      try {
        const response = await getCycloneData({
          includeForecast: true,
          includeSurge: true,
          includeDemo: showDemoCyclone,
        });

        if (response.success && response.hasActiveCyclone) {
          setCycloneData(response.cyclone);
          setSurgeData(response.surge);
          setHasCyclone(true);
          setIsDemo(response.isDemo || false);

          if (!response.isDemo) {
            toast.custom((t) => (
              <div className="flex items-center gap-3 px-4 py-3 bg-orange-500/90 backdrop-blur-xl rounded-xl text-white shadow-lg">
                <CloudLightning className="w-5 h-5" />
                <div>
                  <p className="font-bold text-sm">Active Cyclone Detected</p>
                  <p className="text-xs opacity-90">{response.cyclone?.name || 'Cyclone'} in Bay of Bengal</p>
                </div>
              </div>
            ), { duration: 5000 });
          }
        } else {
          setHasCyclone(false);
          setCycloneData(null);
          setSurgeData(null);
          setIsDemo(false);
        }
      } catch (error) {
        console.error('Failed to fetch cyclone data:', error);
      }
    };

    fetchCycloneData();
    const interval = setInterval(fetchCycloneData, 5 * 60 * 1000);
    return () => clearInterval(interval);
  }, [showDemoCyclone]);

  // Check for new alerts
  useEffect(() => {
    if (alerts.length > 0 && notificationsEnabled && previousAlertsRef.current.length > 0) {
      checkAndNotifyNewAlerts(alerts, previousAlertsRef.current, locations, { playSound: true });
    }
    previousAlertsRef.current = alerts;
  }, [alerts, notificationsEnabled, locations]);

  // Toggle notifications
  const handleToggleNotifications = useCallback(async () => {
    if (!notificationsEnabled) {
      const granted = await requestNotificationPermission();
      setNotificationsEnabled(granted);
      toast[granted ? 'success' : 'error'](granted ? 'Notifications enabled' : 'Permission denied');
    } else {
      setNotificationsEnabled(false);
      toast('Notifications muted', { icon: '🔕' });
    }
  }, [notificationsEnabled]);

  // Handle refresh
  const handleRefresh = useCallback(() => {
    refresh();
    toast.success('Refreshing data...');
  }, [refresh]);

  // Demo alerts functions
  const injectDemoAlerts = async () => {
    try {
      const response = await axios.post(`${process.env.NEXT_PUBLIC_API_URL}/multi-hazard/demo/inject-alerts`);
      if (response.data.success) {
        toast.success(`Injected ${response.data.alerts_created.length} demo alerts`);
        refresh();
      }
    } catch (error) {
      toast.error('Failed to inject demo alerts');
    }
  };

  const clearDemoAlerts = async () => {
    try {
      const response = await axios.post(`${process.env.NEXT_PUBLIC_API_URL}/multi-hazard/demo/clear-alerts`);
      if (response.data.success) {
        toast.success('Demo alerts cleared');
        refresh();
      }
    } catch (error) {
      toast.error('Failed to clear demo alerts');
    }
  };

  // Handle location selection
  const handleLocationSelect = useCallback((location) => {
    setSelectedLocation(location);
    // Close mobile sheet or show peek
    setMobileSheetHeight('peek');

    // Fly to location on map
    if (mapRef.current) {
      const lat = location.coordinates?.lat || location.lat;
      const lon = location.coordinates?.lon || location.lon;
      if (lat && lon) {
        mapRef.current.flyTo([lat, lon], 8, { duration: 1.5 });
      }
    }
  }, []);

  // Handle location detail view
  const handleViewDetail = useCallback((location) => {
    setSelectedLocation(location);
    setShowDetailModal(true);
  }, []);

  // Handle map ready
  const handleMapReady = useCallback((map) => {
    mapRef.current = map;
  }, []);

  // Go back home
  const handleGoHome = useCallback(() => {
    window.history.back();
  }, []);

  // Calculate overall status
  const getOverallStatus = useCallback(() => {
    if (alerts.length === 0) {
      return { level: 1, text: 'All Clear', config: ALERT_CONFIG[1] };
    }
    const maxLevel = Math.max(...alerts.map((a) => a.alert_level || 1));
    return {
      level: maxLevel,
      text: ALERT_CONFIG[maxLevel]?.name || 'NORMAL',
      config: ALERT_CONFIG[maxLevel] || ALERT_CONFIG[1],
    };
  }, [alerts]);

  // Sort locations by alert level
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

  const status = getOverallStatus();

  if (isLoading) {
    return <MapLoadingState />;
  }

  return (
    <div className="map-page-container">
      {/* ============== MAIN MAP ============== */}
      <OceanMap
        locations={locations}
        alerts={alerts}
        reports={reports}
        mapStyle={mapStyle}
        selectedLocation={selectedLocation}
        onLocationSelect={handleLocationSelect}
        onMapReady={handleMapReady}
      >
        {showHeatmap && heatmapPoints.length > 0 && (
          <HeatmapLayer points={heatmapPoints} opacity={heatmapOpacity} />
        )}
        {showClusters && reports.length > 0 && (
          <ClusterLayer reports={reports} onReportClick={handleViewDetail} />
        )}
        {showCyclone && cycloneData && (
          <CycloneLayer
            cycloneData={cycloneData}
            surgeData={showSurge ? surgeData : null}
            showTrack={true}
            showSurge={showSurge}
            showWindRadii={true}
            showForecastCone={true}
            animateCyclone={true}
            opacity={0.8}
          />
        )}
        {(showOceanCurrents || showWaveHeight) && (
          <WaveTrackLayer
            showCurrents={showOceanCurrents}
            showWaveHeight={showWaveHeight}
            opacity={0.9}
          />
        )}
      </OceanMap>

      {/* ============== DESKTOP: LEFT NAV (Website Navigation - Hidden by default) ============== */}
      <div className={`map-left-nav ${leftNavOpen ? 'open' : 'closed'}`}>
        {/* Nav Header */}
        <div className="left-nav-header">
          <div className="flex items-center gap-3">
            <img src="/logo.png" alt="Logo" className="w-8 h-8" />
            <div>
              <h1 className="text-base font-bold text-white">CoastGuardian</h1>
              <p className="text-xs text-slate-400">Analyst Portal</p>
            </div>
          </div>
          <button
            onClick={() => setLeftNavOpen(false)}
            className="p-2 hover:bg-slate-700/50 rounded-lg transition-colors"
          >
            <X className="w-5 h-5 text-slate-400" />
          </button>
        </div>

        {/* Navigation Links */}
        <nav className="left-nav-content">
          <a href="/analyst" className="left-nav-item">
            <Home className="w-5 h-5" />
            <span>AnalystDashboard</span>
          </a>
          <a href="/analyst/social-intelligence" className="left-nav-item">
            <AlertTriangle className="w-5 h-5" />
            <span>Social Intelligence</span>
          </a>
          <a href="/analyst/map" className="left-nav-item active">
            <Map className="w-5 h-5" />
            <span>Hazard Map</span>
          </a>
          <a href="/analyst/reports" className="left-nav-item">
            <MessageCircle className="w-5 h-5" />
            <span>All Reports</span>
          </a>
          <a href="/analyst/tickets" className="left-nav-item">
            <FileText className="w-5 h-5" />
            <span>Tickets</span>
          </a>
          <a href="/analyst/notes" className="left-nav-item">
            <FileText className="w-5 h-5" />
            <span>My Notes</span>
          </a>
          <a href="/analyst/exports" className="left-nav-item">
            <FileText className="w-5 h-5" />
            <span>Export Center</span>
          </a>
        </nav>
      </div>

      {/* Left Nav Toggle Button */}
      <button
        onClick={() => setLeftNavOpen(!leftNavOpen)}
        className={`left-nav-toggle ${leftNavOpen ? 'hidden' : ''}`}
        title="Open navigation"
      >
        <Menu className="w-5 h-5" />
      </button>

      {/* ============== DESKTOP: RIGHT SIDEBAR (Map Controls) ============== */}
      <div className={`map-right-sidebar ${rightPanelOpen ? 'open' : 'closed'}`}>
        {/* Sidebar Header */}
        <div className="sidebar-header">
          <div className="flex items-center gap-3">
            <Waves className="w-5 h-5 text-cyan-400" />
            <div>
              <h1 className="text-base font-bold text-white">Hazard Monitor</h1>
              <p className="text-xs text-slate-400">Live ocean data</p>
            </div>
          </div>
          <button
            onClick={() => setRightPanelOpen(false)}
            className="p-2 hover:bg-slate-700/50 rounded-lg transition-colors"
          >
            <X className="w-5 h-5 text-slate-400" />
          </button>
        </div>

        {/* Status Bar */}
        <div className="sidebar-status">
          <div className={`status-indicator ${status.config.bg}`}>
            <div className={`w-2 h-2 rounded-full bg-white ${status.level >= 4 ? 'animate-pulse' : ''}`} />
            <span className="font-semibold text-sm">{status.text}</span>
            {isConnected && <span className="text-xs opacity-80">• LIVE</span>}
          </div>
          <div className="flex items-center gap-2 text-xs text-slate-400 mt-2">
            <Clock className="w-3 h-3" />
            <span>Updated {formatTimeAgo(lastUpdate)}</span>
          </div>
        </div>

        {/* Quick Stats */}
        <div className="sidebar-stats">
          <div className="stat-box critical">
            <span className="stat-number">{statistics.criticalAlerts || 0}</span>
            <span className="stat-label">Critical</span>
          </div>
          <div className="stat-box warning">
            <span className="stat-number">{statistics.warningAlerts || 0}</span>
            <span className="stat-label">Warning</span>
          </div>
          <div className="stat-box watch">
            <span className="stat-number">{statistics.watchAlerts || 0}</span>
            <span className="stat-label">Watch</span>
          </div>
        </div>

        {/* Cyclone Alert Banner */}
        {hasCyclone && cycloneData && (
          <button
            onClick={() => {
              if (mapRef.current && cycloneData.currentPosition) {
                mapRef.current.flyTo(
                  [cycloneData.currentPosition.lat, cycloneData.currentPosition.lon],
                  6,
                  { duration: 1.5 }
                );
              }
            }}
            className="cyclone-banner"
          >
            <CloudLightning className="w-5 h-5 animate-pulse" />
            <div className="flex-1">
              <p className="font-bold text-sm">{cycloneData.name || 'CYCLONE'}</p>
              <p className="text-xs opacity-80">{cycloneData.maxWindSpeed} km/h winds</p>
            </div>
            {isDemo && <span className="demo-badge">DEMO</span>}
            <ChevronRight className="w-4 h-4" />
          </button>
        )}

        {/* Tab Navigation */}
        <div className="sidebar-tabs">
          <button
            className={`tab-btn ${activeTab === 'locations' ? 'active' : ''}`}
            onClick={() => setActiveTab('locations')}
          >
            <MapPin className="w-4 h-4" />
            <span>Locations</span>
          </button>
          <button
            className={`tab-btn ${activeTab === 'alerts' ? 'active' : ''}`}
            onClick={() => setActiveTab('alerts')}
          >
            <AlertTriangle className="w-4 h-4" />
            <span>Alerts</span>
            {alerts.length > 0 && <span className="tab-badge">{alerts.length}</span>}
          </button>
          <button
            className={`tab-btn ${activeTab === 'layers' ? 'active' : ''}`}
            onClick={() => setActiveTab('layers')}
          >
            <Layers className="w-4 h-4" />
            <span>Layers</span>
          </button>
        </div>

        {/* Tab Content */}
        <div className="sidebar-content">
          {/* Locations Tab */}
          {activeTab === 'locations' && (
            <div className="tab-content">
              <p className="section-title">{locations.length} Monitored Stations</p>
              <div className="location-list">
                {sortedLocations.map((location) => {
                  const alertLevel = location.alert_level || location.max_alert_level || 1;
                  const config = ALERT_CONFIG[alertLevel];
                  const isSelected = selectedLocation?.location_id === location.location_id;

                  return (
                    <button
                      key={location.location_id}
                      onClick={() => handleLocationSelect(location)}
                      className={`location-card ${isSelected ? 'selected' : ''}`}
                    >
                      <div
                        className="location-level"
                        style={{ background: config.gradient }}
                      >
                        {alertLevel}
                      </div>
                      <div className="location-info">
                        <p className="location-name">{location.location_name || location.name}</p>
                        <p className="location-region">{location.region}</p>
                      </div>
                      <ChevronRight className="w-4 h-4 text-slate-500" />
                    </button>
                  );
                })}
              </div>
            </div>
          )}

          {/* Alerts Tab */}
          {activeTab === 'alerts' && (
            <div className="tab-content">
              {alerts.length === 0 ? (
                <div className="empty-state">
                  <div className="empty-icon bg-emerald-500/20">
                    <Activity className="w-8 h-8 text-emerald-400" />
                  </div>
                  <p className="empty-title">All Clear</p>
                  <p className="empty-text">No active alerts at this time</p>
                </div>
              ) : (
                <>
                  <p className="section-title">{alerts.length} Active Alerts</p>
                  <div className="alert-list">
                    {alerts.map((alert, idx) => {
                      const config = ALERT_CONFIG[alert.alert_level] || ALERT_CONFIG[3];
                      const HazardIcon = HAZARD_ICONS[alert.hazard_type] || AlertTriangle;
                      const location = locations.find((l) => l.location_id === alert.location_id);

                      return (
                        <button
                          key={alert.alert_id || idx}
                          onClick={() => location && handleLocationSelect(location)}
                          className="alert-card"
                        >
                          <div
                            className="alert-icon"
                            style={{ background: config.gradient }}
                          >
                            <HazardIcon className="w-5 h-5 text-white" />
                          </div>
                          <div className="alert-info">
                            <p className="alert-location">
                              {alert.location_name || location?.location_name || 'Unknown'}
                            </p>
                            <p className="alert-type">
                              {alert.hazard_type?.replace(/_/g, ' ')}
                            </p>
                          </div>
                          <span
                            className="alert-level-badge"
                            style={{ background: config.gradient }}
                          >
                            L{alert.alert_level}
                          </span>
                        </button>
                      );
                    })}
                  </div>
                </>
              )}
            </div>
          )}

          {/* Layers Tab */}
          {activeTab === 'layers' && (
            <div className="tab-content">
              {/* Map Style */}
              <div className="layer-section">
                <p className="section-title">Map Style</p>
                <div className="style-grid">
                  {[
                    { id: 'esriOcean', name: 'Ocean', icon: '🌊' },
                    { id: 'dark', name: 'Dark', icon: '🌙' },
                    { id: 'satellite', name: 'Satellite', icon: '🛰️' },
                    { id: 'terrain', name: 'Terrain', icon: '⛰️' },
                  ].map((style) => (
                    <button
                      key={style.id}
                      onClick={() => setMapStyle(style.id)}
                      className={`style-btn ${mapStyle === style.id ? 'active' : ''}`}
                    >
                      <span className="style-icon">{style.icon}</span>
                      <span className="style-name">{style.name}</span>
                    </button>
                  ))}
                </div>
              </div>

              {/* Data Layers */}
              <div className="layer-section">
                <p className="section-title">Data Layers</p>
                <div className="toggle-list">
                  <label className="toggle-item">
                    <div className="toggle-info">
                      <Thermometer className="w-4 h-4 text-orange-400" />
                      <span>Heatmap</span>
                    </div>
                    <input
                      type="checkbox"
                      checked={showHeatmap}
                      onChange={() => setShowHeatmap(!showHeatmap)}
                      className="toggle-switch"
                    />
                  </label>
                  <label className="toggle-item">
                    <div className="toggle-info">
                      <Droplets className="w-4 h-4 text-blue-400" />
                      <span>Report Clusters</span>
                    </div>
                    <input
                      type="checkbox"
                      checked={showClusters}
                      onChange={() => setShowClusters(!showClusters)}
                      className="toggle-switch"
                    />
                  </label>
                  <label className="toggle-item">
                    <div className="toggle-info">
                      <CloudLightning className={`w-4 h-4 ${hasCyclone ? 'text-purple-400' : 'text-slate-400'}`} />
                      <span>Cyclone Track</span>
                      {hasCyclone && <span className="active-badge">ACTIVE</span>}
                    </div>
                    <input
                      type="checkbox"
                      checked={showCyclone}
                      onChange={() => setShowCyclone(!showCyclone)}
                      className="toggle-switch"
                    />
                  </label>
                  <label className="toggle-item">
                    <div className="toggle-info">
                      <Waves className="w-4 h-4 text-orange-400" />
                      <span>Storm Surge</span>
                    </div>
                    <input
                      type="checkbox"
                      checked={showSurge}
                      onChange={() => setShowSurge(!showSurge)}
                      className="toggle-switch"
                    />
                  </label>
                  <label className="toggle-item">
                    <div className="toggle-info">
                      <Navigation className="w-4 h-4 text-cyan-400" />
                      <span>Ocean Currents</span>
                    </div>
                    <input
                      type="checkbox"
                      checked={showOceanCurrents}
                      onChange={() => setShowOceanCurrents(!showOceanCurrents)}
                      className="toggle-switch"
                    />
                  </label>
                  <label className="toggle-item">
                    <div className="toggle-info">
                      <Activity className="w-4 h-4 text-teal-400" />
                      <span>Wave Height</span>
                    </div>
                    <input
                      type="checkbox"
                      checked={showWaveHeight}
                      onChange={() => setShowWaveHeight(!showWaveHeight)}
                      className="toggle-switch"
                    />
                  </label>
                </div>
              </div>

              {/* Demo Mode */}
              <div className="layer-section">
                <p className="section-title">Testing</p>
                <label className="toggle-item">
                  <div className="toggle-info">
                    <CloudLightning className="w-4 h-4 text-yellow-400" />
                    <span>Demo Cyclone</span>
                  </div>
                  <input
                    type="checkbox"
                    checked={showDemoCyclone}
                    onChange={() => setShowDemoCyclone(!showDemoCyclone)}
                    className="toggle-switch"
                  />
                </label>
                <div className="flex gap-2 mt-3">
                  <button
                    onClick={injectDemoAlerts}
                    className="flex-1 flex items-center justify-center gap-2 px-3 py-2 bg-emerald-600 hover:bg-emerald-700 rounded-lg text-white text-sm font-medium transition-colors"
                  >
                    <Play className="w-4 h-4" />
                    Inject Demo
                  </button>
                  <button
                    onClick={clearDemoAlerts}
                    className="flex-1 flex items-center justify-center gap-2 px-3 py-2 bg-slate-600 hover:bg-slate-500 rounded-lg text-white text-sm font-medium transition-colors"
                  >
                    <Trash2 className="w-4 h-4" />
                    Clear
                  </button>
                </div>
              </div>

              {/* Heatmap Intensity */}
              {showHeatmap && (
                <div className="layer-section">
                  <div className="flex justify-between items-center mb-2">
                    <p className="section-title">Heatmap Intensity</p>
                    <span className="text-xs text-slate-400">{Math.round(heatmapOpacity * 100)}%</span>
                  </div>
                  <input
                    type="range"
                    min="0"
                    max="100"
                    value={heatmapOpacity * 100}
                    onChange={(e) => setHeatmapOpacity(Number(e.target.value) / 100)}
                    className="intensity-slider"
                  />
                </div>
              )}
            </div>
          )}
        </div>

        {/* Sidebar Footer */}
        <div className="sidebar-footer">
          <button
            onClick={handleRefresh}
            disabled={isRefreshing}
            className="footer-btn"
          >
            <RefreshCw className={`w-4 h-4 ${isRefreshing ? 'animate-spin' : ''}`} />
          </button>
          <button
            onClick={handleToggleNotifications}
            className={`footer-btn ${notificationsEnabled ? 'active' : ''}`}
          >
            {notificationsEnabled ? <Bell className="w-4 h-4" /> : <BellOff className="w-4 h-4" />}
          </button>
          <div className="footer-reports">
            <span className="text-cyan-400 font-bold">{reports.length}</span>
            <span className="text-slate-400 text-xs">reports (24h)</span>
          </div>
        </div>
      </div>

      {/* ============== DESKTOP: Right Panel Toggle (when closed) ============== */}
      {!rightPanelOpen && (
        <button
          onClick={() => setRightPanelOpen(true)}
          className="right-panel-toggle hidden lg:flex"
          title="Open hazard panel"
        >
          <ChevronLeft className="w-5 h-5" />
        </button>
      )}

      {/* ============== MOBILE: Top Bar ============== */}
      <div className="mobile-top-bar lg:hidden">
        <button
          onClick={handleGoHome}
          className="mobile-btn"
        >
          <ArrowLeft className="w-5 h-5" />
        </button>

        <div className={`mobile-status ${status.config.bg}`}>
          <div className={`w-2 h-2 rounded-full bg-white ${status.level >= 4 ? 'animate-pulse' : ''}`} />
          <span className="font-semibold text-sm">{status.text}</span>
        </div>

        <button
          onClick={() => setRightPanelOpen(true)}
          className="mobile-btn"
        >
          <PanelRight className="w-5 h-5" />
        </button>
      </div>

      {/* ============== MOBILE: Bottom Sheet ============== */}
      <div className={`mobile-bottom-sheet ${mobileSheetHeight}`}>
        {/* Sheet Handle */}
        <div
          className="sheet-handle"
          onClick={() => {
            if (mobileSheetHeight === 'peek') setMobileSheetHeight('half');
            else if (mobileSheetHeight === 'half') setMobileSheetHeight('full');
            else setMobileSheetHeight('peek');
          }}
        >
          <div className="handle-bar" />
        </div>

        {/* Sheet Header */}
        <div className="sheet-header">
          <div className="sheet-stats">
            <div className="mini-stat critical">
              <AlertTriangle className="w-3 h-3" />
              <span>{statistics.criticalAlerts || 0}</span>
            </div>
            <div className="mini-stat warning">
              <AlertTriangle className="w-3 h-3" />
              <span>{statistics.warningAlerts || 0}</span>
            </div>
            <div className="mini-stat info">
              <MapPin className="w-3 h-3" />
              <span>{locations.length}</span>
            </div>
          </div>
          <div className="sheet-actions">
            <button
              onClick={handleRefresh}
              disabled={isRefreshing}
              className="sheet-action-btn"
            >
              <RefreshCw className={`w-4 h-4 ${isRefreshing ? 'animate-spin' : ''}`} />
            </button>
            <button
              onClick={handleToggleNotifications}
              className={`sheet-action-btn ${notificationsEnabled ? 'active' : ''}`}
            >
              {notificationsEnabled ? <Bell className="w-4 h-4" /> : <BellOff className="w-4 h-4" />}
            </button>
          </div>
        </div>

        {/* Sheet Content */}
        <div className="sheet-content">
          {/* Quick Location Pills */}
          <div className="quick-pills">
            {sortedLocations.slice(0, 10).map((location) => {
              const alertLevel = location.alert_level || location.max_alert_level || 1;
              const config = ALERT_CONFIG[alertLevel];
              const isSelected = selectedLocation?.location_id === location.location_id;

              return (
                <button
                  key={location.location_id}
                  onClick={() => handleLocationSelect(location)}
                  className={`location-pill ${isSelected ? 'selected' : ''}`}
                  style={{ borderColor: isSelected ? config.color : 'transparent' }}
                >
                  <span
                    className="pill-dot"
                    style={{ background: config.color }}
                  />
                  <span className="pill-name">{location.location_name || location.name}</span>
                </button>
              );
            })}
          </div>

          {/* Full Location List (visible in half/full modes) */}
          {(mobileSheetHeight === 'half' || mobileSheetHeight === 'full') && (
            <div className="full-location-list">
              <p className="list-title">All Stations</p>
              {sortedLocations.map((location) => {
                const alertLevel = location.alert_level || location.max_alert_level || 1;
                const config = ALERT_CONFIG[alertLevel];
                const isSelected = selectedLocation?.location_id === location.location_id;

                return (
                  <button
                    key={location.location_id}
                    onClick={() => handleLocationSelect(location)}
                    className={`mobile-location-item ${isSelected ? 'selected' : ''}`}
                  >
                    <div
                      className="item-level"
                      style={{ background: config.gradient }}
                    >
                      {alertLevel}
                    </div>
                    <div className="item-info">
                      <p className="item-name">{location.location_name || location.name}</p>
                      <p className="item-region">{location.region}</p>
                    </div>
                    <ChevronRight className="w-4 h-4 text-slate-500" />
                  </button>
                );
              })}
            </div>
          )}
        </div>
      </div>

      {/* ============== MOBILE: Floating Action Buttons ============== */}
      <div className="mobile-fab-container lg:hidden">
        <button
          onClick={() => setActiveTab('layers')}
          className="fab-btn"
        >
          <Layers className="w-5 h-5" />
        </button>
      </div>

      {/* ============== Sidebar Overlay (Mobile) ============== */}
      {(rightPanelOpen || leftNavOpen) && (
        <div
          className="sidebar-overlay lg:hidden"
          onClick={() => {
            setRightPanelOpen(false);
            setLeftNavOpen(false);
          }}
        />
      )}

      {/* Left Nav Overlay (Desktop) */}
      {leftNavOpen && (
        <div
          className="left-nav-overlay hidden lg:block"
          onClick={() => setLeftNavOpen(false)}
        />
      )}

      {/* ============== Location Detail Modal ============== */}
      {showDetailModal && selectedLocation && (
        <LocationDetailModal
          location={selectedLocation}
          alerts={alerts}
          onClose={() => setShowDetailModal(false)}
          onNavigate={(loc) => {
            handleLocationSelect(loc);
            setShowDetailModal(false);
          }}
        />
      )}

      {/* Toast Notifications */}
      <Toaster
        position="top-center"
        toastOptions={{
          style: {
            background: 'rgba(15, 23, 42, 0.95)',
            color: '#f1f5f9',
            border: '1px solid rgba(255, 255, 255, 0.1)',
            backdropFilter: 'blur(16px)',
            borderRadius: '12px',
          },
        }}
      />
    </div>
  );
}

// Wrapper with SSR handling
const MapWrapper = dynamic(() => Promise.resolve(OceanMapContent), {
  ssr: false,
  loading: () => <MapLoadingState />,
});

// Main page export
export default function OceanMapPage() {
  return (
    <ProtectedRoute>
      <MapWrapper />
    </ProtectedRoute>
  );
}
