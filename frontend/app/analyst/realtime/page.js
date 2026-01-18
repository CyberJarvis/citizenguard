'use client';

import React, { useState, useEffect, useRef } from 'react';
import { useRouter } from 'next/navigation';
import dynamic from 'next/dynamic';
import useAuthStore from '@/context/AuthContext';
import DashboardLayout from '@/components/DashboardLayout';
import PageHeader from '@/components/PageHeader';
import {
  Waves,
  Wind,
  CloudRain,
  AlertTriangle,
  Activity,
  RefreshCw,
  Bell,
  BellOff,
  ChevronRight,
  ChevronLeft,
  ChevronDown,
  ChevronUp,
  MapPin,
  Thermometer,
  Droplets,
  Gauge,
  Eye,
  X,
  Shield,
  Compass,
  Layers,
  Play,
  Trash2,
  BarChart3,
  TrendingUp,
  Clock,
  Radio,
  Satellite,
  Navigation,
  Zap,
  Database,
  Settings,
  Filter
} from 'lucide-react';
import { getMultiHazardStatus, getMultiHazardAlerts, getMultiHazardHealth, getMultiHazardPublicLocations, getMultiHazardPublicAlerts } from '@/lib/api';
import { checkAndNotifyNewAlerts, requestNotificationPermission, isNotificationEnabled } from '@/lib/notifications';
import toast, { Toaster } from 'react-hot-toast';
import axios from 'axios';

// Dynamically import map components
const MapContainer = dynamic(() => import('react-leaflet').then((mod) => mod.MapContainer), { ssr: false });
const TileLayer = dynamic(() => import('react-leaflet').then((mod) => mod.TileLayer), { ssr: false });
const Marker = dynamic(() => import('react-leaflet').then((mod) => mod.Marker), { ssr: false });
const Popup = dynamic(() => import('react-leaflet').then((mod) => mod.Popup), { ssr: false });
const Circle = dynamic(() => import('react-leaflet').then((mod) => mod.Circle), { ssr: false });
const ZoomControl = dynamic(() => import('react-leaflet').then((mod) => mod.ZoomControl), { ssr: false });

// Alert level configuration
const ALERT_CONFIG = {
  5: { name: 'CRITICAL', color: '#ef4444', glow: 'rgba(239,68,68,0.6)', size: 52, pulse: true },
  4: { name: 'WARNING', color: '#f97316', glow: 'rgba(249,115,22,0.5)', size: 46, pulse: true },
  3: { name: 'WATCH', color: '#eab308', glow: 'rgba(234,179,8,0.4)', size: 40, pulse: false },
  2: { name: 'ADVISORY', color: '#3b82f6', glow: 'rgba(59,130,246,0.3)', size: 34, pulse: false },
  1: { name: 'NORMAL', color: '#22c55e', glow: 'rgba(34,197,94,0.2)', size: 28, pulse: false },
};

// Hazard icons
const HAZARD_ICONS = {
  cyclone: Wind,
  high_waves: Waves,
  coastal_flood: CloudRain,
  rip_currents: Activity,
  tsunami: Waves,
  storm_surge: Droplets,
};

// Map tile options
const MAP_TILES = {
  dark: {
    name: 'Dark',
    url: 'https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png',
    attribution: '&copy; CartoDB'
  },
  satellite: {
    name: 'Satellite',
    url: 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
    attribution: '&copy; Esri'
  },
  ocean: {
    name: 'Ocean',
    url: 'https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png',
    attribution: '&copy; CartoDB'
  },
  terrain: {
    name: 'Terrain',
    url: 'https://{s}.tile.opentopomap.org/{z}/{x}/{y}.png',
    attribution: '&copy; OpenTopoMap'
  }
};

// Create marker icon
const createMarkerIcon = (alertLevel) => {
  if (typeof window === 'undefined') return null;
  const L = require('leaflet');
  const config = ALERT_CONFIG[alertLevel] || ALERT_CONFIG[1];

  const pulseCSS = config.pulse ? `
    animation: pulse-glow 2s ease-in-out infinite;
    @keyframes pulse-glow {
      0%, 100% { box-shadow: 0 0 0 0 ${config.glow}, 0 0 20px ${config.glow}; }
      50% { box-shadow: 0 0 0 15px transparent, 0 0 30px ${config.glow}; }
    }
  ` : '';

  const html = `
    <div style="
      width: ${config.size}px;
      height: ${config.size}px;
      background: linear-gradient(135deg, ${config.color} 0%, ${config.color}dd 100%);
      border: 3px solid rgba(255,255,255,0.95);
      border-radius: 50%;
      display: flex;
      align-items: center;
      justify-content: center;
      box-shadow: 0 4px 20px ${config.glow}, 0 0 30px ${config.glow};
      ${pulseCSS}
    ">
      <span style="
        color: white;
        font-size: ${config.size * 0.38}px;
        font-weight: 800;
        text-shadow: 0 2px 4px rgba(0,0,0,0.3);
      ">${alertLevel}</span>
    </div>
  `;

  return L.divIcon({
    html,
    className: 'analyst-marker',
    iconSize: [config.size, config.size],
    iconAnchor: [config.size / 2, config.size / 2],
    popupAnchor: [0, -config.size / 2]
  });
};

function AnalystMapContent() {
  const router = useRouter();
  const { user } = useAuthStore();
  const [locations, setLocations] = useState([]);
  const [alerts, setAlerts] = useState([]);
  const [earthquakes, setEarthquakes] = useState([]);
  const [previousAlerts, setPreviousAlerts] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [lastUpdate, setLastUpdate] = useState(null);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [isConnected, setIsConnected] = useState(false);
  const [notificationsEnabled, setNotificationsEnabled] = useState(false);

  // UI State
  const [showLeftPanel, setShowLeftPanel] = useState(true);
  const [showRightPanel, setShowRightPanel] = useState(true);
  const [selectedLocation, setSelectedLocation] = useState(null);
  const [mapStyle, setMapStyle] = useState('dark');
  const [activeTab, setActiveTab] = useState('alerts');
  const [showLayerMenu, setShowLayerMenu] = useState(false);

  // Data Layers
  const [layers, setLayers] = useState({
    hazards: true,
    earthquakes: true,
    heatmap: false,
    riskZones: true
  });

  const mapRef = useRef(null);
  const refreshInterval = useRef(null);

  // Auth check
  useEffect(() => {
    if (user && !['analyst', 'authority_admin'].includes(user.role)) {
      router.push('/dashboard');
    }
  }, [user, router]);

  useEffect(() => {
    import('leaflet/dist/leaflet.css');
    setNotificationsEnabled(isNotificationEnabled());
  }, []);

  useEffect(() => {
    loadData();
    refreshInterval.current = setInterval(loadData, 30 * 1000); // 30s for analyst
    return () => clearInterval(refreshInterval.current);
  }, []);

  const loadData = async () => {
    try {
      const health = await getMultiHazardHealth();
      setIsConnected(health.status === 'healthy');

      if (health.status === 'healthy') {
        let locs = [], alts = [], eqs = [];

        try {
          const status = await getMultiHazardStatus();
          alts = await getMultiHazardAlerts();
          // Convert dict to array if needed
          if (status.locations && typeof status.locations === 'object' && !Array.isArray(status.locations)) {
            locs = Object.entries(status.locations).map(([id, loc]) => ({ location_id: id, ...loc }));
          } else {
            locs = status.locations || [];
          }
          eqs = status.recent_earthquakes || status.earthquakes || [];
        } catch (authError) {
          console.log('Falling back to public endpoints');
          const locationsData = await getMultiHazardPublicLocations();
          locs = locationsData.locations || [];
          const alertsData = await getMultiHazardPublicAlerts();
          alts = alertsData.alerts || [];
        }

        if (alerts.length > 0 && notificationsEnabled) {
          checkAndNotifyNewAlerts(alts, previousAlerts, locs, { playSound: true });
        }

        setPreviousAlerts(alts);
        setLocations(locs);
        setAlerts(alts);
        setEarthquakes(eqs);
        setLastUpdate(new Date());
      }
    } catch (error) {
      console.error('Error loading data:', error);
      setIsConnected(false);
    }
    setIsLoading(false);
  };

  const handleRefresh = async () => {
    setIsRefreshing(true);
    await loadData();
    setIsRefreshing(false);
    toast.success('Data refreshed');
  };

  const injectDemoAlerts = async () => {
    try {
      const response = await axios.post(`${process.env.NEXT_PUBLIC_API_URL}/multi-hazard/demo/inject-alerts`);
      if (response.data.success) {
        toast.success(`Injected ${response.data.alerts_created.length} demo alerts`);
        await loadData();
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
        await loadData();
      }
    } catch (error) {
      toast.error('Failed to clear demo alerts');
    }
  };

  const toggleNotifications = async () => {
    if (!notificationsEnabled) {
      const granted = await requestNotificationPermission();
      setNotificationsEnabled(granted);
      toast[granted ? 'success' : 'error'](granted ? 'Notifications enabled' : 'Permission denied');
    } else {
      setNotificationsEnabled(false);
      toast('Notifications muted', { icon: '🔕' });
    }
  };

  const flyToLocation = (location) => {
    setSelectedLocation(location);
    if (mapRef.current) {
      const lat = location.coordinates?.lat || location.lat;
      const lon = location.coordinates?.lon || location.lon;
      mapRef.current.flyTo([lat, lon], 9, { duration: 1.5 });
    }
  };

  // Stats
  const stats = {
    total: locations.length,
    critical: alerts.filter(a => a.alert_level >= 5).length,
    warning: alerts.filter(a => a.alert_level === 4).length,
    watch: alerts.filter(a => a.alert_level === 3).length,
    safe: locations.filter(l => (l.alert_level || 1) <= 2).length,
    earthquakes: earthquakes.length
  };

  const getOverallStatus = () => {
    if (stats.critical > 0) return { level: 5, text: 'CRITICAL', bg: 'bg-red-500' };
    if (stats.warning > 0) return { level: 4, text: 'WARNING', bg: 'bg-orange-500' };
    if (stats.watch > 0) return { level: 3, text: 'WATCH', bg: 'bg-yellow-500' };
    return { level: 1, text: 'ALL CLEAR', bg: 'bg-emerald-500' };
  };

  const status = getOverallStatus();

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-screen bg-slate-950">
        <div className="text-center">
          <div className="relative w-24 h-24 mx-auto mb-6">
            <div className="absolute inset-0 border-4 border-purple-500/30 rounded-full animate-ping"></div>
            <div className="absolute inset-2 border-4 border-t-purple-400 border-r-transparent border-b-transparent border-l-transparent rounded-full animate-spin"></div>
            <Radio className="absolute inset-0 m-auto w-10 h-10 text-purple-400" />
          </div>
          <p className="text-purple-100 text-lg font-medium">Analyst Command Center</p>
          <p className="text-slate-400 text-sm mt-2">Initializing real-time monitoring...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="relative w-full h-[calc(100vh-4rem)] bg-slate-950 overflow-hidden">
      {/* Map */}
      <div className="absolute inset-0">
        <MapContainer
          center={[15.8, 80.2]}
          zoom={5}
          style={{ height: '100%', width: '100%' }}
          zoomControl={false}
          ref={mapRef}
        >
          <TileLayer {...MAP_TILES[mapStyle]} />
          <ZoomControl position="bottomright" />

          {/* Hazard Markers */}
          {layers.hazards && locations.map(location => {
            const alertLevel = location.alert_level || location.max_alert_level || 1;
            const lat = location.coordinates?.lat || location.lat;
            const lon = location.coordinates?.lon || location.lon;
            const config = ALERT_CONFIG[alertLevel];

            return (
              <React.Fragment key={location.location_id}>
                {/* Risk zone circle */}
                {layers.riskZones && alertLevel >= 3 && (
                  <Circle
                    center={[lat, lon]}
                    radius={alertLevel >= 5 ? 100000 : alertLevel >= 4 ? 75000 : 50000}
                    pathOptions={{
                      color: config.color,
                      fillColor: config.color,
                      fillOpacity: 0.12,
                      weight: 2,
                      opacity: 0.5,
                      dashArray: alertLevel < 4 ? '10, 5' : null
                    }}
                  />
                )}

                <Marker
                  position={[lat, lon]}
                  icon={createMarkerIcon(alertLevel)}
                  eventHandlers={{
                    click: () => {
                      setSelectedLocation(location);
                      setShowRightPanel(true);
                    }
                  }}
                >
                  <Popup className="analyst-popup" maxWidth={400}>
                    <div className="p-2">
                      <div className="flex items-center justify-between mb-3">
                        <h3 className="font-bold text-lg text-slate-800">
                          {location.location_name || location.name}
                        </h3>
                        <span
                          className="px-3 py-1 rounded-full text-xs font-bold text-white"
                          style={{ backgroundColor: config.color }}
                        >
                          {config.name}
                        </span>
                      </div>

                      <div className="grid grid-cols-2 gap-2 mb-3 text-sm">
                        <div className="p-2 bg-slate-50 rounded-lg">
                          <p className="text-slate-500 text-xs">Region</p>
                          <p className="font-medium text-slate-700">{location.region}</p>
                        </div>
                        <div className="p-2 bg-slate-50 rounded-lg">
                          <p className="text-slate-500 text-xs">Risk Profile</p>
                          <p className="font-medium text-slate-700">{location.risk_profile || 'N/A'}</p>
                        </div>
                      </div>

                      {location.active_hazards?.length > 0 && (
                        <div className="space-y-2">
                          <p className="text-xs font-semibold text-slate-600 uppercase">Active Hazards</p>
                          {location.active_hazards.map((hazard, idx) => {
                            const HazardIcon = HAZARD_ICONS[hazard.hazard_type] || AlertTriangle;
                            const hConfig = ALERT_CONFIG[hazard.alert_level] || ALERT_CONFIG[3];
                            return (
                              <div key={idx} className="flex items-center gap-2 p-2 bg-slate-50 rounded-lg">
                                <HazardIcon className="w-4 h-4" style={{ color: hConfig.color }} />
                                <div className="flex-1">
                                  <span className="text-sm font-medium text-slate-700">
                                    {hazard.hazard_type?.replace('_', ' ')}
                                  </span>
                                  {hazard.confidence && (
                                    <span className="text-xs text-slate-400 ml-2">
                                      {(hazard.confidence * 100).toFixed(0)}% conf
                                    </span>
                                  )}
                                </div>
                                <span
                                  className="px-2 py-0.5 rounded text-xs font-bold text-white"
                                  style={{ backgroundColor: hConfig.color }}
                                >
                                  L{hazard.alert_level}
                                </span>
                              </div>
                            );
                          })}
                        </div>
                      )}

                      {(!location.active_hazards || location.active_hazards.length === 0) && (
                        <div className="flex items-center gap-2 p-3 bg-emerald-50 rounded-lg">
                          <Shield className="w-5 h-5 text-emerald-500" />
                          <span className="text-sm font-medium text-emerald-700">No Active Hazards</span>
                        </div>
                      )}

                      <div className="text-xs text-slate-400 pt-3 mt-3 border-t border-slate-100 flex justify-between">
                        <span>{lat?.toFixed(4)}°N, {lon?.toFixed(4)}°E</span>
                        <span>ID: {location.location_id}</span>
                      </div>
                    </div>
                  </Popup>
                </Marker>
              </React.Fragment>
            );
          })}
        </MapContainer>
      </div>

      {/* Top Bar */}
      <div className="absolute top-4 left-4 right-4 z-[1000] flex items-center justify-between">
        {/* Left - Status & Toggle */}
        <div className="flex items-center gap-3">
          <button
            onClick={() => setShowLeftPanel(!showLeftPanel)}
            className="p-3 bg-slate-900/95 backdrop-blur-xl rounded-xl text-slate-300 hover:text-white shadow-2xl border border-slate-700/50"
          >
            {showLeftPanel ? <ChevronLeft className="w-5 h-5" /> : <ChevronRight className="w-5 h-5" />}
          </button>

          <div className={`flex items-center gap-3 px-5 py-3 rounded-2xl backdrop-blur-xl shadow-2xl border border-slate-700/50 ${status.bg} ${status.level >= 4 ? 'animate-pulse' : ''}`}>
            <Radio className="w-5 h-5 text-white" />
            <span className="font-bold text-white tracking-wide">{status.text}</span>
            <span className="text-white/70 text-sm">• ANALYST MODE</span>
          </div>
        </div>

        {/* Center - Quick Stats */}
        <div className="hidden lg:flex items-center gap-2">
          <div className="flex items-center gap-2 px-4 py-2.5 bg-slate-900/95 backdrop-blur-xl rounded-xl border border-slate-700/50 shadow-lg">
            <MapPin className="w-4 h-4 text-cyan-400" />
            <span className="font-bold text-white">{stats.total}</span>
            <span className="text-slate-400 text-sm">stations</span>
          </div>
          {stats.critical > 0 && (
            <div className="flex items-center gap-2 px-4 py-2.5 bg-red-500/90 backdrop-blur-xl rounded-xl shadow-lg animate-pulse">
              <AlertTriangle className="w-4 h-4 text-white" />
              <span className="font-bold text-white">{stats.critical}</span>
              <span className="text-white/80 text-sm">critical</span>
            </div>
          )}
          {stats.warning > 0 && (
            <div className="flex items-center gap-2 px-4 py-2.5 bg-orange-500/90 backdrop-blur-xl rounded-xl shadow-lg">
              <AlertTriangle className="w-4 h-4 text-white" />
              <span className="font-bold text-white">{stats.warning}</span>
              <span className="text-white/80 text-sm">warning</span>
            </div>
          )}
          {stats.earthquakes > 0 && (
            <div className="flex items-center gap-2 px-4 py-2.5 bg-purple-500/90 backdrop-blur-xl rounded-xl shadow-lg">
              <Zap className="w-4 h-4 text-white" />
              <span className="font-bold text-white">{stats.earthquakes}</span>
              <span className="text-white/80 text-sm">seismic</span>
            </div>
          )}
        </div>

        {/* Right - Actions */}
        <div className="flex items-center gap-2">
          <button
            onClick={injectDemoAlerts}
            className="hidden sm:flex items-center gap-2 px-4 py-2.5 bg-emerald-600 hover:bg-emerald-700 rounded-xl text-white font-medium shadow-lg transition-colors"
          >
            <Play className="w-4 h-4" />
            Demo
          </button>
          <button
            onClick={clearDemoAlerts}
            className="hidden sm:flex items-center gap-2 px-4 py-2.5 bg-slate-700 hover:bg-slate-600 rounded-xl text-white font-medium shadow-lg transition-colors"
          >
            <Trash2 className="w-4 h-4" />
            Clear
          </button>

          <div className="h-8 w-px bg-slate-700 mx-1"></div>

          <button
            onClick={toggleNotifications}
            className={`p-3 rounded-xl backdrop-blur-xl shadow-lg border border-slate-700/50 transition-all ${
              notificationsEnabled ? 'bg-cyan-500 text-white' : 'bg-slate-900/95 text-slate-300 hover:text-white'
            }`}
          >
            {notificationsEnabled ? <Bell className="w-5 h-5" /> : <BellOff className="w-5 h-5" />}
          </button>
          <button
            onClick={handleRefresh}
            disabled={isRefreshing}
            className="p-3 bg-slate-900/95 backdrop-blur-xl rounded-xl text-slate-300 hover:text-white shadow-lg border border-slate-700/50 transition-all disabled:opacity-50"
          >
            <RefreshCw className={`w-5 h-5 ${isRefreshing ? 'animate-spin' : ''}`} />
          </button>
          <button
            onClick={() => setShowRightPanel(!showRightPanel)}
            className="p-3 bg-slate-900/95 backdrop-blur-xl rounded-xl text-slate-300 hover:text-white shadow-lg border border-slate-700/50"
          >
            {showRightPanel ? <ChevronRight className="w-5 h-5" /> : <ChevronLeft className="w-5 h-5" />}
          </button>
        </div>
      </div>

      {/* Left Panel - Analysis Tools */}
      <div className={`absolute top-20 left-4 bottom-4 w-72 z-[1000] transition-transform duration-300 ${
        showLeftPanel ? 'translate-x-0' : '-translate-x-[calc(100%+1rem)]'
      }`}>
        <div className="h-full bg-slate-900/95 backdrop-blur-xl rounded-2xl shadow-2xl border border-slate-700/50 overflow-hidden flex flex-col">
          {/* Header */}
          <div className="p-4 border-b border-slate-700/50">
            <div className="flex items-center gap-2">
              <BarChart3 className="w-5 h-5 text-purple-400" />
              <h2 className="font-bold text-white">Analysis Panel</h2>
            </div>
          </div>

          {/* Stats Grid */}
          <div className="p-3 border-b border-slate-700/50">
            <div className="grid grid-cols-2 gap-2">
              <div className="p-3 bg-slate-800/50 rounded-xl text-center">
                <p className="text-2xl font-bold text-white">{stats.total}</p>
                <p className="text-xs text-slate-400">Stations</p>
              </div>
              <div className="p-3 bg-slate-800/50 rounded-xl text-center">
                <p className="text-2xl font-bold text-emerald-400">{stats.safe}</p>
                <p className="text-xs text-slate-400">Safe</p>
              </div>
              <div className="p-3 bg-red-500/20 rounded-xl text-center">
                <p className="text-2xl font-bold text-red-400">{stats.critical}</p>
                <p className="text-xs text-slate-400">Critical</p>
              </div>
              <div className="p-3 bg-orange-500/20 rounded-xl text-center">
                <p className="text-2xl font-bold text-orange-400">{stats.warning}</p>
                <p className="text-xs text-slate-400">Warning</p>
              </div>
            </div>
          </div>

          {/* Layer Controls */}
          <div className="p-3 border-b border-slate-700/50">
            <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">Data Layers</p>
            <div className="space-y-2">
              {Object.entries(layers).map(([key, enabled]) => (
                <button
                  key={key}
                  onClick={() => setLayers(prev => ({ ...prev, [key]: !prev[key] }))}
                  className={`w-full flex items-center justify-between p-2.5 rounded-xl transition-colors ${
                    enabled ? 'bg-purple-500/20 text-purple-300' : 'bg-slate-800/50 text-slate-400'
                  }`}
                >
                  <span className="text-sm font-medium capitalize">{key.replace(/([A-Z])/g, ' $1')}</span>
                  <div className={`w-4 h-4 rounded ${enabled ? 'bg-purple-500' : 'bg-slate-600'}`} />
                </button>
              ))}
            </div>
          </div>

          {/* Map Style */}
          <div className="p-3 border-b border-slate-700/50">
            <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">Map Style</p>
            <div className="grid grid-cols-2 gap-2">
              {Object.entries(MAP_TILES).map(([key, tile]) => (
                <button
                  key={key}
                  onClick={() => setMapStyle(key)}
                  className={`p-2 rounded-xl text-xs font-medium transition-colors ${
                    mapStyle === key
                      ? 'bg-cyan-500 text-white'
                      : 'bg-slate-800/50 text-slate-400 hover:text-white'
                  }`}
                >
                  {tile.name}
                </button>
              ))}
            </div>
          </div>

          {/* Recent Activity */}
          <div className="flex-1 overflow-y-auto p-3">
            <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">Recent Activity</p>
            <div className="space-y-2">
              {alerts.slice(0, 5).map((alert, idx) => {
                const config = ALERT_CONFIG[alert.alert_level] || ALERT_CONFIG[3];
                return (
                  <div
                    key={alert.alert_id || idx}
                    className="p-2 bg-slate-800/50 rounded-lg cursor-pointer hover:bg-slate-700/50"
                    onClick={() => {
                      const loc = locations.find(l => l.location_id === alert.location_id);
                      if (loc) flyToLocation(loc);
                    }}
                  >
                    <div className="flex items-center gap-2">
                      <div className="w-2 h-2 rounded-full" style={{ backgroundColor: config.color }} />
                      <span className="text-sm text-white font-medium truncate">{alert.location_name}</span>
                    </div>
                    <p className="text-xs text-slate-400 mt-1 pl-4">
                      {alert.hazard_type?.replace('_', ' ')} • L{alert.alert_level}
                    </p>
                  </div>
                );
              })}
              {alerts.length === 0 && (
                <div className="text-center py-6 text-slate-500">
                  <Shield className="w-8 h-8 mx-auto mb-2 opacity-50" />
                  <p className="text-sm">No active alerts</p>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Right Panel - Location Details */}
      <div className={`absolute top-20 right-4 bottom-4 w-80 z-[1000] transition-transform duration-300 ${
        showRightPanel ? 'translate-x-0' : 'translate-x-[calc(100%+1rem)]'
      }`}>
        <div className="h-full bg-slate-900/95 backdrop-blur-xl rounded-2xl shadow-2xl border border-slate-700/50 overflow-hidden flex flex-col">
          {/* Tabs */}
          <div className="flex border-b border-slate-700/50">
            {['alerts', 'locations', 'seismic'].map(tab => (
              <button
                key={tab}
                onClick={() => setActiveTab(tab)}
                className={`flex-1 py-3 text-sm font-medium transition-colors ${
                  activeTab === tab
                    ? 'text-cyan-400 border-b-2 border-cyan-400 bg-slate-800/30'
                    : 'text-slate-400 hover:text-white'
                }`}
              >
                {tab.charAt(0).toUpperCase() + tab.slice(1)}
              </button>
            ))}
          </div>

          {/* Content */}
          <div className="flex-1 overflow-y-auto p-3">
            {activeTab === 'alerts' && (
              <div className="space-y-2">
                {alerts.length > 0 ? alerts.map((alert, idx) => {
                  const config = ALERT_CONFIG[alert.alert_level] || ALERT_CONFIG[3];
                  const HazardIcon = HAZARD_ICONS[alert.hazard_type] || AlertTriangle;
                  return (
                    <div
                      key={alert.alert_id || idx}
                      className="p-3 bg-slate-800/50 rounded-xl cursor-pointer hover:bg-slate-700/50"
                      onClick={() => {
                        const loc = locations.find(l => l.location_id === alert.location_id);
                        if (loc) flyToLocation(loc);
                      }}
                    >
                      <div className="flex items-start gap-3">
                        <div className="p-2 rounded-lg" style={{ backgroundColor: `${config.color}20` }}>
                          <HazardIcon className="w-5 h-5" style={{ color: config.color }} />
                        </div>
                        <div className="flex-1">
                          <div className="flex items-center justify-between">
                            <h4 className="font-medium text-white">{alert.hazard_type?.replace('_', ' ')}</h4>
                            <span
                              className="px-2 py-0.5 rounded text-xs font-bold text-white"
                              style={{ backgroundColor: config.color }}
                            >
                              L{alert.alert_level}
                            </span>
                          </div>
                          <p className="text-sm text-slate-400 mt-1">{alert.location_name}</p>
                          {alert.recommendations?.[0] && (
                            <p className="text-xs text-red-400 mt-2">{alert.recommendations[0]}</p>
                          )}
                        </div>
                      </div>
                    </div>
                  );
                }) : (
                  <div className="text-center py-12 text-slate-500">
                    <Shield className="w-12 h-12 mx-auto mb-3 opacity-50" />
                    <p className="font-medium">No Active Alerts</p>
                    <p className="text-sm mt-1">All stations reporting normal</p>
                  </div>
                )}
              </div>
            )}

            {activeTab === 'locations' && (
              <div className="space-y-1">
                {locations
                  .sort((a, b) => (b.alert_level || 1) - (a.alert_level || 1))
                  .map(location => {
                    const alertLevel = location.alert_level || location.max_alert_level || 1;
                    const config = ALERT_CONFIG[alertLevel];
                    const isSelected = selectedLocation?.location_id === location.location_id;

                    return (
                      <button
                        key={location.location_id}
                        onClick={() => flyToLocation(location)}
                        className={`w-full flex items-center gap-3 p-3 rounded-xl text-left transition-all ${
                          isSelected ? 'bg-cyan-500/20 border border-cyan-500/50' : 'hover:bg-slate-800/50'
                        }`}
                      >
                        <div
                          className="w-10 h-10 rounded-full flex items-center justify-center text-white font-bold text-sm flex-shrink-0"
                          style={{ backgroundColor: config.color }}
                        >
                          {alertLevel}
                        </div>
                        <div className="flex-1 min-w-0">
                          <p className="font-medium text-white truncate">{location.location_name || location.name}</p>
                          <p className="text-xs text-slate-400">{location.region}</p>
                        </div>
                        <ChevronRight className="w-4 h-4 text-slate-500 flex-shrink-0" />
                      </button>
                    );
                  })}
              </div>
            )}

            {activeTab === 'seismic' && (
              <div className="space-y-2">
                {earthquakes.length > 0 ? earthquakes.map((eq, idx) => (
                  <div key={eq.id || idx} className="p-3 bg-slate-800/50 rounded-xl">
                    <div className="flex items-start gap-3">
                      <div className={`w-12 h-12 rounded-xl flex items-center justify-center font-bold text-white ${
                        eq.magnitude >= 6 ? 'bg-red-500' :
                        eq.magnitude >= 5 ? 'bg-orange-500' :
                        eq.magnitude >= 4 ? 'bg-yellow-500' : 'bg-blue-500'
                      }`}>
                        {eq.magnitude?.toFixed(1)}
                      </div>
                      <div className="flex-1">
                        <p className="font-medium text-white">{eq.place || 'Unknown location'}</p>
                        <p className="text-sm text-slate-400 mt-1">Depth: {eq.depth?.toFixed(1)} km</p>
                        <p className="text-xs text-slate-500 mt-1">
                          {eq.time ? new Date(eq.time).toLocaleString() : 'N/A'}
                        </p>
                      </div>
                    </div>
                  </div>
                )) : (
                  <div className="text-center py-12 text-slate-500">
                    <Zap className="w-12 h-12 mx-auto mb-3 opacity-50" />
                    <p className="font-medium">No Recent Seismic Activity</p>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Bottom Legend */}
      <div className="absolute bottom-4 left-1/2 -translate-x-1/2 z-[1000]">
        <div className="bg-slate-900/95 backdrop-blur-xl rounded-2xl shadow-2xl border border-slate-700/50 px-6 py-3 flex items-center gap-6">
          {Object.entries(ALERT_CONFIG).reverse().map(([level, config]) => (
            <div key={level} className="flex items-center gap-2">
              <div className="w-4 h-4 rounded-full" style={{ backgroundColor: config.color }} />
              <span className="text-xs text-slate-300 font-medium">{config.name}</span>
            </div>
          ))}
          <div className="h-4 w-px bg-slate-700" />
          <div className="flex items-center gap-2">
            <div className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
            <span className="text-xs text-slate-400">
              Live • {lastUpdate?.toLocaleTimeString() || 'N/A'}
            </span>
          </div>
        </div>
      </div>

      <Toaster
        position="top-center"
        toastOptions={{
          style: {
            background: '#1e293b',
            color: '#f1f5f9',
            border: '1px solid #334155'
          }
        }}
      />

      <style jsx global>{`
        .analyst-marker {
          background: transparent !important;
          border: none !important;
        }
        .analyst-popup .leaflet-popup-content-wrapper {
          background: white;
          border-radius: 16px;
          box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.25);
        }
        .analyst-popup .leaflet-popup-tip {
          background: white;
        }
        .leaflet-control-zoom {
          border: none !important;
          box-shadow: 0 10px 40px -10px rgba(0,0,0,0.5) !important;
        }
        .leaflet-control-zoom a {
          background: rgba(15, 23, 42, 0.95) !important;
          color: #94a3b8 !important;
          border: none !important;
          backdrop-filter: blur(12px);
        }
        .leaflet-control-zoom a:hover {
          background: rgba(30, 41, 59, 0.95) !important;
          color: white !important;
        }
      `}</style>
    </div>
  );
}

// Wrapper
const AnalystMapWrapper = dynamic(
  () => Promise.resolve(AnalystMapContent),
  {
    ssr: false,
    loading: () => (
      <div className="flex items-center justify-center h-screen bg-slate-950">
        <div className="text-center">
          <Radio className="w-12 h-12 text-purple-400 mx-auto mb-4 animate-pulse" />
          <p className="text-slate-400">Loading Analyst Dashboard...</p>
        </div>
      </div>
    )
  }
);

export default function RealtimeMonitoring() {
  return (
    <DashboardLayout>
      <div className="p-4 lg:p-6">
        {/* Page Header - Desktop Only */}
        <PageHeader />
      </div>
      <AnalystMapWrapper />
    </DashboardLayout>
  );
}
