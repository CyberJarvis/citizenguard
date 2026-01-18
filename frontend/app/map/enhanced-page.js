'use client';

import { useState, useEffect, useMemo, useCallback, useRef } from 'react';
import dynamic from 'next/dynamic';
import ProtectedRoute from '@/components/ProtectedRoute';
import DashboardLayout from '@/components/DashboardLayout';
import { getImageUrl } from '@/lib/api';
import {
  Map as MapIcon,
  MapPin,
  Filter,
  Search,
  Loader2,
  AlertTriangle,
  Navigation,
  X,
  RefreshCw,
  Bell,
  Activity,
  Waves,
  Wind as WindIcon,
  CloudRain,
  AlertCircle,
  Info,
  ChevronRight,
  ChevronDown,
  Eye,
  ThumbsUp,
  TrendingUp
} from 'lucide-react';
import {
  getHazardReports,
  getCurrentMonitoringData,
  getRecentEarthquakes
} from '@/lib/api';
import toast, { Toaster } from 'react-hot-toast';
import 'leaflet/dist/leaflet.css';

// Dynamically import Leaflet components (prevents SSR issues)
const MapContainer = dynamic(
  () => import('react-leaflet').then((mod) => mod.MapContainer),
  { ssr: false }
);
const TileLayer = dynamic(
  () => import('react-leaflet').then((mod) => mod.TileLayer),
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

/**
 * Enhanced HazardMap Component
 *
 * Features:
 * - ML-detected hazards from monitoring system (color-coded by alert level)
 * - User-reported hazards
 * - Earthquake markers
 * - Real-time auto-refresh (5 minutes)
 * - Alert statistics panel
 * - Advanced filtering
 * - Pulsing animations for critical alerts
 * - Interactive popups
 * - Responsive design
 */
function EnhancedMapContent() {
  // ============== STATE MANAGEMENT ==============

  // Data states
  const [userReports, setUserReports] = useState([]);
  const [monitoringData, setMonitoringData] = useState(null);
  const [earthquakes, setEarthquakes] = useState([]);

  // UI states
  const [isLoading, setIsLoading] = useState(true);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [error, setError] = useState(null);
  const [userLocation, setUserLocation] = useState(null);
  const [mapCenter, setMapCenter] = useState([15.0, 77.0]); // Center of India
  const [mapZoom, setMapZoom] = useState(5);
  const [searchQuery, setSearchQuery] = useState('');
  const [isMapReady, setIsMapReady] = useState(false);
  const [showSidePanel, setShowSidePanel] = useState(true);
  const [showFilters, setShowFilters] = useState(false);

  // Filter states
  const [filters, setFilters] = useState({
    showUserReports: true,
    showMLDetections: true,
    showEarthquakes: true,
    hazardTypes: {
      tsunami: true,
      cyclone: true,
      high_waves: true,
      flood: true
    },
    minAlertLevel: 1
  });

  // Auto-refresh
  const [lastUpdateTime, setLastUpdateTime] = useState(null);
  const refreshIntervalRef = useRef(null);

  // ============== DATA FETCHING ==============

  /**
   * Fetch all data (monitoring, user reports, earthquakes)
   */
  const fetchAllData = useCallback(async (showRefreshIndicator = false) => {
    try {
      if (showRefreshIndicator) {
        setIsRefreshing(true);
      } else {
        setIsLoading(true);
      }
      setError(null);

      // Fetch in parallel for performance
      const [monitoringResponse, userReportsResponse, earthquakesResponse] = await Promise.all([
        getCurrentMonitoringData().catch(err => {
          console.error('Monitoring data fetch failed:', err);
          return null;
        }),
        getHazardReports({ page: 1, page_size: 100 }).catch(err => {
          console.error('User reports fetch failed:', err);
          return { reports: [] };
        }),
        getRecentEarthquakes({ hours: 24, min_magnitude: 4.0 }).catch(err => {
          console.error('Earthquakes fetch failed:', err);
          return [];
        })
      ]);

      // Update states
      if (monitoringResponse) {
        setMonitoringData(monitoringResponse);
      }

      if (userReportsResponse && userReportsResponse.reports) {
        const validReports = userReportsResponse.reports.filter(
          report => report.location && report.location.latitude && report.location.longitude
        );
        setUserReports(validReports);
      }

      if (earthquakesResponse) {
        setEarthquakes(earthquakesResponse);
      }

      setLastUpdateTime(new Date());

      // Check for critical alerts and notify
      if (monitoringResponse && monitoringResponse.summary.critical_alerts > 0) {
        const criticalLocations = Object.values(monitoringResponse.locations)
          .filter(loc => loc.max_alert === 5)
          .map(loc => loc.name);

        if (criticalLocations.length > 0) {
          toast.error(
            `🚨 CRITICAL ALERT: ${criticalLocations.join(', ')}`,
            { duration: 10000, icon: '⚠️' }
          );
        }
      }

    } catch (err) {
      console.error('Error fetching data:', err);
      setError('Failed to load hazard data. Please try refreshing.');
      toast.error('Failed to load data');
    } finally {
      setIsLoading(false);
      setIsRefreshing(false);
    }
  }, []);

  /**
   * Initial data load and setup auto-refresh
   */
  useEffect(() => {
    fetchAllData();

    // Setup auto-refresh every 5 minutes
    refreshIntervalRef.current = setInterval(() => {
      fetchAllData(true);
    }, 5 * 60 * 1000); // 5 minutes

    // Cleanup
    return () => {
      if (refreshIntervalRef.current) {
        clearInterval(refreshIntervalRef.current);
      }
    };
  }, [fetchAllData]);

  /**
   * Manual refresh handler
   */
  const handleRefresh = () => {
    fetchAllData(true);
    toast.success('Refreshing data...');
  };

  /**
   * Get user location
   */
  const getUserLocation = () => {
    if (!navigator.geolocation) {
      toast.error('Geolocation is not supported by your browser');
      return;
    }

    toast.loading('Getting your location...');

    navigator.geolocation.getCurrentPosition(
      (position) => {
        const { latitude, longitude } = position.coords;
        setUserLocation({ lat: latitude, lon: longitude });
        setMapCenter([latitude, longitude]);
        setMapZoom(10);
        toast.dismiss();
        toast.success('Location detected!');
      },
      (error) => {
        toast.dismiss();
        toast.error('Unable to get your location');
        console.error('Geolocation error:', error);
      },
      {
        enableHighAccuracy: true,
        timeout: 15000,
        maximumAge: 0
      }
    );
  };

  // ============== UTILITY FUNCTIONS ==============

  /**
   * Get color for alert level
   */
  const getAlertColor = (alertLevel) => {
    const colors = {
      5: '#DC2626', // Critical - Red
      4: '#F97316', // High - Orange
      3: '#FCD34D', // Warning - Yellow
      2: '#60A5FA', // Low - Blue
      1: '#10B981'  // Normal - Green
    };
    return colors[alertLevel] || colors[1];
  };

  /**
   * Get marker size for alert level
   */
  const getMarkerSize = (alertLevel) => {
    const sizes = {
      5: 40,
      4: 35,
      3: 30,
      2: 25,
      1: 25
    };
    return sizes[alertLevel] || 25;
  };

  /**
   * Create custom icon for ML monitoring locations
   */
  const createMLIcon = (alertLevel, isPulsing = false) => {
    if (typeof window === 'undefined') return null;

    const L = require('leaflet');
    const color = getAlertColor(alertLevel);
    const size = getMarkerSize(alertLevel);

    const pulseClass = isPulsing ? 'pulse-marker' : '';

    const html = `
      <div class="ml-marker ${pulseClass}" style="
        width: ${size}px;
        height: ${size}px;
        background: linear-gradient(135deg, ${color}, ${color}dd);
        border: 3px solid white;
        border-radius: 50%;
        box-shadow: 0 4px 12px rgba(0,0,0,0.3), 0 0 0 4px ${color}44;
        display: flex;
        align-items: center;
        justify-content: center;
        color: white;
        font-weight: bold;
        font-size: ${size * 0.4}px;
        position: relative;
        z-index: ${alertLevel * 100};
      ">
        ${alertLevel}
      </div>
    `;

    return L.divIcon({
      html,
      className: '',
      iconSize: [size, size],
      iconAnchor: [size / 2, size / 2],
      popupAnchor: [0, -size / 2]
    });
  };

  /**
   * Create custom icon for user reports
   */
  const createUserReportIcon = (hazardType) => {
    if (typeof window === 'undefined') return null;

    const L = require('leaflet');
    const colorMap = {
      'High Waves': '#EF4444',
      'Rip Current': '#DC2626',
      'Storm Surge/Cyclone Effects': '#B91C1C',
      'Flooded Coastline': '#3B82F6',
      'Beached Aquatic Animal': '#10B981',
      'Oil Spill': '#8B5CF6',
      'Fisher Nets Entanglement': '#F59E0B',
      'Ship Wreck': '#6B7280',
      'Chemical Spill': '#DC2626',
      'Plastic Pollution': '#10B981'
    };

    const color = colorMap[hazardType] || '#6B7280';

    const html = `
      <div style="
        width: 30px;
        height: 40px;
        background: ${color};
        clip-path: polygon(50% 100%, 0% 20%, 0% 0%, 100% 0%, 100% 20%);
        border: 2px solid white;
        box-shadow: 0 2px 8px rgba(0,0,0,0.3);
        display: flex;
        align-items: center;
        justify-content: center;
        color: white;
        font-size: 16px;
        transform: rotate(-45deg);
        position: relative;
      ">
        <span style="transform: rotate(45deg);">⚠</span>
      </div>
    `;

    return L.divIcon({
      html,
      className: '',
      iconSize: [30, 40],
      iconAnchor: [15, 40],
      popupAnchor: [0, -40]
    });
  };

  /**
   * Create earthquake icon
   */
  const createEarthquakeIcon = (magnitude) => {
    if (typeof window === 'undefined') return null;

    const L = require('leaflet');
    let color = '#FCD34D'; // Yellow for 4-6
    if (magnitude >= 7) color = '#DC2626'; // Red for 7+
    else if (magnitude >= 6) color = '#F97316'; // Orange for 6-7

    const size = Math.min(magnitude * 5, 40);

    const html = `
      <div style="
        width: ${size}px;
        height: ${size}px;
        background: ${color};
        border: 2px solid white;
        border-radius: 50%;
        box-shadow: 0 2px 8px rgba(0,0,0,0.3);
        display: flex;
        align-items: center;
        justify-content: center;
        color: white;
        font-weight: bold;
        font-size: ${size * 0.4}px;
      ">
        ${magnitude.toFixed(1)}
      </div>
    `;

    return L.divIcon({
      html,
      className: '',
      iconSize: [size, size],
      iconAnchor: [size / 2, size / 2],
      popupAnchor: [0, -size / 2]
    });
  };

  // ============== FILTERED DATA ==============

  const filteredMLLocations = useMemo(() => {
    if (!monitoringData || !filters.showMLDetections) return [];

    return Object.entries(monitoringData.locations)
      .filter(([_, location]) => {
        // Filter by minimum alert level
        if (location.max_alert < filters.minAlertLevel) return false;

        // Filter by hazard type
        const hazards = location.current_hazards;
        const hasActiveHazard =
          (filters.hazardTypes.tsunami && hazards.tsunami) ||
          (filters.hazardTypes.cyclone && hazards.cyclone) ||
          (filters.hazardTypes.high_waves && hazards.high_waves) ||
          (filters.hazardTypes.flood && hazards.flood);

        return hasActiveHazard || location.max_alert >= 4; // Always show high/critical
      })
      .map(([id, location]) => ({ id, ...location }));
  }, [monitoringData, filters]);

  const filteredUserReports = useMemo(() => {
    if (!filters.showUserReports) return [];

    return userReports.filter(report => {
      if (searchQuery && !report.hazard_type.toLowerCase().includes(searchQuery.toLowerCase())) {
        return false;
      }
      return true;
    });
  }, [userReports, filters.showUserReports, searchQuery]);

  const filteredEarthquakes = useMemo(() => {
    return filters.showEarthquakes ? earthquakes : [];
  }, [earthquakes, filters.showEarthquakes]);

  // ============== RENDER HELPER FUNCTIONS ==============

  const renderHazardBadge = (hazard, type) => {
    const icons = {
      tsunami: '🌊',
      cyclone: '🌀',
      high_waves: '🌊',
      flood: '💧'
    };

    return (
      <div className="flex items-center gap-2 text-sm p-2 bg-gray-50 rounded">
        <span>{icons[type]}</span>
        <div className="flex-1">
          <div className="font-semibold">{type.replace('_', ' ').toUpperCase()}</div>
          <div className="text-xs text-gray-600">
            Alert Level: {hazard.alert_level}
            {hazard.probability && ` • ${(hazard.probability * 100).toFixed(0)}% probability`}
          </div>
        </div>
      </div>
    );
  };

  // ============== RENDER ==============

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-screen bg-gray-50">
        <div className="text-center">
          <Loader2 className="w-12 h-12 animate-spin text-blue-600 mx-auto mb-4" />
          <p className="text-gray-600">Loading hazard monitoring data...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="relative w-full h-screen bg-gray-100">
      {/* CSS for pulsing animation */}
      <style jsx global>{`
        @keyframes pulse-marker {
          0%, 100% {
            opacity: 1;
            transform: scale(1);
          }
          50% {
            opacity: 0.6;
            transform: scale(1.2);
          }
        }

        .pulse-marker {
          animation: pulse-marker 2s ease-in-out infinite;
        }

        .leaflet-container {
          height: 100vh;
          width: 100%;
          z-index: 0;
        }
      `}</style>

      {/* Top Control Bar */}
      <div className="absolute top-4 left-4 right-4 z-[1000] flex flex-wrap gap-2">
        {/* Search Bar */}
        <div className="flex-1 min-w-[200px] max-w-md">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-5 h-5" />
            <input
              type="text"
              placeholder="Search hazards..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-10 pr-4 py-3 rounded-lg shadow-lg bg-white/95 backdrop-blur-sm border-0 focus:ring-2 focus:ring-blue-500"
            />
          </div>
        </div>

        {/* Action Buttons */}
        <button
          onClick={handleRefresh}
          disabled={isRefreshing}
          className="px-4 py-3 bg-white/95 backdrop-blur-sm rounded-lg shadow-lg hover:bg-gray-50 transition-colors flex items-center gap-2"
        >
          <RefreshCw className={`w-5 h-5 ${isRefreshing ? 'animate-spin' : ''}`} />
          <span className="hidden sm:inline">Refresh</span>
        </button>

        <button
          onClick={getUserLocation}
          className="px-4 py-3 bg-blue-600 text-white rounded-lg shadow-lg hover:bg-blue-700 transition-colors flex items-center gap-2"
        >
          <Navigation className="w-5 h-5" />
          <span className="hidden sm:inline">My Location</span>
        </button>

        <button
          onClick={() => setShowFilters(!showFilters)}
          className="px-4 py-3 bg-white/95 backdrop-blur-sm rounded-lg shadow-lg hover:bg-gray-50 transition-colors flex items-center gap-2"
        >
          <Filter className="w-5 h-5" />
          <span className="hidden sm:inline">Filters</span>
        </button>

        <button
          onClick={() => setShowSidePanel(!showSidePanel)}
          className="px-4 py-3 bg-white/95 backdrop-blur-sm rounded-lg shadow-lg hover:bg-gray-50 transition-colors flex items-center gap-2 lg:hidden"
        >
          <Activity className="w-5 h-5" />
        </button>
      </div>

      {/* Filters Panel */}
      {showFilters && (
        <div className="absolute top-20 left-4 z-[1000] bg-white/95 backdrop-blur-sm rounded-lg shadow-xl p-4 w-80 max-h-[80vh] overflow-y-auto">
          <div className="flex items-center justify-between mb-4">
            <h3 className="font-bold text-lg">Filters</h3>
            <button onClick={() => setShowFilters(false)}>
              <X className="w-5 h-5" />
            </button>
          </div>

          {/* Layer Toggles */}
          <div className="space-y-3 mb-4">
            <h4 className="font-semibold text-sm text-gray-700">Display Layers</h4>

            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={filters.showMLDetections}
                onChange={(e) => setFilters({ ...filters, showMLDetections: e.target.checked })}
                className="w-4 h-4 rounded border-gray-300"
              />
              <span>ML Detected Hazards</span>
            </label>

            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={filters.showUserReports}
                onChange={(e) => setFilters({ ...filters, showUserReports: e.target.checked })}
                className="w-4 h-4 rounded border-gray-300"
              />
              <span>User Reports</span>
            </label>

            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={filters.showEarthquakes}
                onChange={(e) => setFilters({ ...filters, showEarthquakes: e.target.checked })}
                className="w-4 h-4 rounded border-gray-300"
              />
              <span>Earthquakes</span>
            </label>
          </div>

          {/* Hazard Type Filters */}
          <div className="space-y-3 mb-4 pb-4 border-b">
            <h4 className="font-semibold text-sm text-gray-700">Hazard Types</h4>

            {Object.keys(filters.hazardTypes).map((type) => (
              <label key={type} className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={filters.hazardTypes[type]}
                  onChange={(e) => setFilters({
                    ...filters,
                    hazardTypes: { ...filters.hazardTypes, [type]: e.target.checked }
                  })}
                  className="w-4 h-4 rounded border-gray-300"
                />
                <span className="capitalize">{type.replace('_', ' ')}</span>
              </label>
            ))}
          </div>

          {/* Alert Level Filter */}
          <div className="space-y-2">
            <h4 className="font-semibold text-sm text-gray-700">Minimum Alert Level</h4>
            <select
              value={filters.minAlertLevel}
              onChange={(e) => setFilters({ ...filters, minAlertLevel: parseInt(e.target.value) })}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg"
            >
              <option value="1">All (Level 1+)</option>
              <option value="2">Low (Level 2+)</option>
              <option value="3">Warning (Level 3+)</option>
              <option value="4">High (Level 4+)</option>
              <option value="5">Critical Only (Level 5)</option>
            </select>
          </div>
        </div>
      )}

      {/* Side Panel */}
      {showSidePanel && monitoringData && (
        <div className="absolute top-4 right-4 z-[1000] bg-white/95 backdrop-blur-sm rounded-lg shadow-xl w-80 max-h-[90vh] overflow-y-auto hidden lg:block">
          <div className="p-4 border-b">
            <h2 className="font-bold text-xl flex items-center gap-2">
              <Activity className="w-6 h-6 text-blue-600" />
              Alert Status
            </h2>
            {lastUpdateTime && (
              <p className="text-xs text-gray-500 mt-1">
                Last updated: {lastUpdateTime.toLocaleTimeString()}
              </p>
            )}
          </div>

          {/* Alert Summary */}
          <div className="p-4 space-y-3 border-b">
            <div className="flex items-center justify-between p-3 bg-red-50 rounded-lg">
              <div className="flex items-center gap-2">
                <div className="w-3 h-3 bg-red-600 rounded-full"></div>
                <span className="font-semibold">Critical</span>
              </div>
              <span className="text-2xl font-bold text-red-600">
                {monitoringData.summary.critical_alerts}
              </span>
            </div>

            <div className="flex items-center justify-between p-3 bg-orange-50 rounded-lg">
              <div className="flex items-center gap-2">
                <div className="w-3 h-3 bg-orange-600 rounded-full"></div>
                <span className="font-semibold">High</span>
              </div>
              <span className="text-2xl font-bold text-orange-600">
                {monitoringData.summary.high_alerts}
              </span>
            </div>

            <div className="flex items-center justify-between p-3 bg-yellow-50 rounded-lg">
              <div className="flex items-center gap-2">
                <div className="w-3 h-3 bg-yellow-500 rounded-full"></div>
                <span className="font-semibold">Warning</span>
              </div>
              <span className="text-2xl font-bold text-yellow-600">
                {monitoringData.summary.warning_alerts}
              </span>
            </div>

            <div className="flex items-center justify-between p-3 bg-green-50 rounded-lg">
              <div className="flex items-center gap-2">
                <div className="w-3 h-3 bg-green-600 rounded-full"></div>
                <span className="font-semibold">Normal</span>
              </div>
              <span className="text-2xl font-bold text-green-600">
                {monitoringData.summary.normal_alerts}
              </span>
            </div>
          </div>

          {/* Active Hazards */}
          <div className="p-4 border-b">
            <h3 className="font-bold mb-3 flex items-center gap-2">
              <AlertTriangle className="w-5 h-5 text-orange-600" />
              Active Hazards
            </h3>
            <div className="space-y-2 text-sm">
              {monitoringData.summary.active_tsunamis > 0 && (
                <div className="flex items-center justify-between p-2 bg-blue-50 rounded">
                  <span>🌊 Tsunami</span>
                  <span className="font-semibold">{monitoringData.summary.active_tsunamis} locations</span>
                </div>
              )}
              {monitoringData.summary.active_cyclones > 0 && (
                <div className="flex items-center justify-between p-2 bg-purple-50 rounded">
                  <span>🌀 Cyclone</span>
                  <span className="font-semibold">{monitoringData.summary.active_cyclones} locations</span>
                </div>
              )}
              {monitoringData.summary.active_high_waves > 0 && (
                <div className="flex items-center justify-between p-2 bg-cyan-50 rounded">
                  <span>🌊 High Waves</span>
                  <span className="font-semibold">{monitoringData.summary.active_high_waves} locations</span>
                </div>
              )}
              {monitoringData.summary.active_floods > 0 && (
                <div className="flex items-center justify-between p-2 bg-blue-50 rounded">
                  <span>💧 Flood</span>
                  <span className="font-semibold">{monitoringData.summary.active_floods} locations</span>
                </div>
              )}
            </div>
          </div>

          {/* Critical/High Alert Locations */}
          {filteredMLLocations.length > 0 && (
            <div className="p-4">
              <h3 className="font-bold mb-3 flex items-center gap-2">
                <MapPin className="w-5 h-5 text-red-600" />
                Affected Regions
              </h3>
              <div className="space-y-2">
                {filteredMLLocations
                  .filter(loc => loc.max_alert >= 3)
                  .sort((a, b) => b.max_alert - a.max_alert)
                  .slice(0, 5)
                  .map((location) => (
                    <div
                      key={location.id}
                      className="p-2 border-l-4 rounded"
                      style={{ borderColor: getAlertColor(location.max_alert) }}
                    >
                      <div className="flex items-center justify-between">
                        <span className="font-semibold">{location.name}</span>
                        <span
                          className="text-xs px-2 py-1 rounded text-white"
                          style={{ backgroundColor: getAlertColor(location.max_alert) }}
                        >
                          {location.status}
                        </span>
                      </div>
                    </div>
                  ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Legend */}
      <div className="absolute bottom-6 left-4 z-[1000] bg-white/95 backdrop-blur-sm rounded-lg shadow-xl p-4 max-w-xs">
        <h3 className="font-bold mb-3 text-sm">Legend</h3>
        <div className="space-y-2 text-xs">
          <div className="flex items-center gap-2">
            <div className="w-5 h-5 bg-red-600 rounded-full"></div>
            <span>Critical Alert (Level 5)</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-5 h-5 bg-orange-500 rounded-full"></div>
            <span>High Alert (Level 4)</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-5 h-5 bg-yellow-400 rounded-full"></div>
            <span>Warning (Level 3)</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-5 h-5 bg-blue-400 rounded-full"></div>
            <span>Low (Level 2)</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-5 h-5 bg-green-500 rounded-full"></div>
            <span>Normal (Level 1)</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-5 h-5 bg-gray-600" style={{ clipPath: 'polygon(50% 100%, 0% 20%, 0% 0%, 100% 0%, 100% 20%)' }}></div>
            <span>User Report</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-5 h-5 bg-yellow-400 rounded-full border-2 border-white"></div>
            <span>Earthquake</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-5 h-5 bg-blue-500 rounded-full"></div>
            <span>Your Location</span>
          </div>
        </div>
      </div>

      {/* Map */}
      {isMapReady !== false && (
        <MapContainer
          center={mapCenter}
          zoom={mapZoom}
          className="h-full w-full"
          whenReady={() => setIsMapReady(true)}
        >
          <TileLayer
            attribution='&copy; <a href="https://carto.com/">CartoDB</a>'
            url="https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png"
          />

          {/* ML Monitoring Location Markers */}
          {filteredMLLocations.map((location) => {
            const icon = createMLIcon(location.max_alert, location.max_alert === 5);

            return (
              <Marker
                key={`ml-${location.id}`}
                position={[location.coordinates.lat, location.coordinates.lon]}
                icon={icon}
              >
                <Popup maxWidth={400} className="custom-popup">
                  <div className="p-2">
                    <div className="flex items-start justify-between mb-3">
                      <div>
                        <h3 className="font-bold text-lg">{location.name}</h3>
                        <p className="text-sm text-gray-600">{location.country}</p>
                        {location.population && (
                          <p className="text-xs text-gray-500">
                            Population: {location.population.toLocaleString()}
                          </p>
                        )}
                      </div>
                      <span
                        className="px-3 py-1 rounded-full text-white text-sm font-semibold"
                        style={{ backgroundColor: getAlertColor(location.max_alert) }}
                      >
                        {location.status}
                      </span>
                    </div>

                    {/* Hazards */}
                    <div className="space-y-2 mb-3">
                      <h4 className="font-semibold text-sm">Detected Hazards:</h4>
                      {location.current_hazards.tsunami && renderHazardBadge(location.current_hazards.tsunami, 'tsunami')}
                      {location.current_hazards.cyclone && renderHazardBadge(location.current_hazards.cyclone, 'cyclone')}
                      {location.current_hazards.high_waves && renderHazardBadge(location.current_hazards.high_waves, 'high_waves')}
                      {location.current_hazards.flood && renderHazardBadge(location.current_hazards.flood, 'flood')}
                    </div>

                    {/* Recommendations */}
                    {location.recommendations && location.recommendations.length > 0 && (
                      <div className="bg-blue-50 p-3 rounded mt-3">
                        <h4 className="font-semibold text-sm mb-2 flex items-center gap-1">
                          <Info className="w-4 h-4" />
                          Recommendations:
                        </h4>
                        <ul className="text-xs space-y-1">
                          {location.recommendations.map((rec, idx) => (
                            <li key={idx} className="flex items-start gap-1">
                              <span>•</span>
                              <span>{rec}</span>
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}

                    <p className="text-xs text-gray-500 mt-3">
                      Last updated: {new Date(location.last_updated).toLocaleString()}
                    </p>
                  </div>
                </Popup>
              </Marker>
            );
          })}

          {/* User Report Markers */}
          {filteredUserReports.map((report) => {
            const icon = createUserReportIcon(report.hazard_type);

            return (
              <Marker
                key={`user-${report._id}`}
                position={[report.location.latitude, report.location.longitude]}
                icon={icon}
              >
                <Popup maxWidth={350}>
                  <div className="p-2">
                    <div className="flex items-start justify-between mb-2">
                      <div>
                        <h3 className="font-bold">{report.hazard_type}</h3>
                        <p className="text-xs text-gray-600">{report.category}</p>
                      </div>
                      <span className="px-2 py-1 bg-blue-100 text-blue-800 rounded text-xs">
                        User Report
                      </span>
                    </div>

                    {report.image_url && (
                      <img
                        src={getImageUrl(report.image_url)}
                        alt="Hazard"
                        className="w-full h-32 object-cover rounded mb-2"
                      />
                    )}

                    {report.description && (
                      <p className="text-sm text-gray-700 mb-2 line-clamp-3">
                        {report.description}
                      </p>
                    )}

                    <div className="flex items-center gap-4 text-xs text-gray-600 mb-2">
                      <span className="flex items-center gap-1">
                        <Eye className="w-3 h-3" />
                        {report.views}
                      </span>
                      <span className="flex items-center gap-1">
                        <ThumbsUp className="w-3 h-3" />
                        {report.likes}
                      </span>
                    </div>

                    <p className="text-xs text-gray-500">
                      Reported: {new Date(report.created_at).toLocaleString()}
                    </p>
                  </div>
                </Popup>
              </Marker>
            );
          })}

          {/* Earthquake Markers */}
          {filteredEarthquakes.map((earthquake) => {
            const icon = createEarthquakeIcon(earthquake.magnitude);

            return (
              <Marker
                key={`eq-${earthquake.earthquake_id}`}
                position={[earthquake.coordinates.lat, earthquake.coordinates.lon]}
                icon={icon}
              >
                <Popup>
                  <div className="p-2">
                    <h3 className="font-bold text-lg mb-2">
                      Earthquake M{earthquake.magnitude.toFixed(1)}
                    </h3>
                    <div className="space-y-1 text-sm">
                      <p><strong>Depth:</strong> {earthquake.depth_km.toFixed(1)} km</p>
                      <p><strong>Location:</strong> {earthquake.location_description}</p>
                      <p><strong>Time:</strong> {new Date(earthquake.timestamp).toLocaleString()}</p>
                      {earthquake.distance_from_coast_km && (
                        <p><strong>Distance from coast:</strong> {earthquake.distance_from_coast_km.toFixed(0)} km</p>
                      )}
                    </div>
                  </div>
                </Popup>
              </Marker>
            );
          })}

          {/* User Location Marker */}
          {userLocation && (
            <Circle
              center={[userLocation.lat, userLocation.lon]}
              radius={500}
              pathOptions={{
                color: '#3B82F6',
                fillColor: '#3B82F6',
                fillOpacity: 0.3
              }}
            >
              <Popup>
                <div className="p-2">
                  <p className="font-semibold">Your Location</p>
                </div>
              </Popup>
            </Circle>
          )}
        </MapContainer>
      )}

      <Toaster position="top-right" />
    </div>
  );
}

export default function EnhancedMapPage() {
  return (
    <ProtectedRoute>
      <DashboardLayout>
        <EnhancedMapContent />
      </DashboardLayout>
    </ProtectedRoute>
  );
}
