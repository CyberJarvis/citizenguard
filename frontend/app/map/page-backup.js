'use client';

import { useState, useEffect, useMemo } from 'react';
import dynamic from 'next/dynamic';
import ProtectedRoute from '@/components/ProtectedRoute';
import DashboardLayout from '@/components/DashboardLayout';
import {
  Map as MapIcon,
  MapPin,
  Layers,
  Filter,
  Search,
  Loader2,
  AlertTriangle,
  Navigation,
  X,
  CheckCircle,
  Clock,
  XCircle,
  Eye,
  ThumbsUp,
  Calendar,
  Wind,
  Droplets,
  RefreshCw
} from 'lucide-react';
import { getHazardReports } from '@/lib/api';
import toast, { Toaster } from 'react-hot-toast';
import 'leaflet/dist/leaflet.css';

// Dynamically import Leaflet components (prevents SSR issues with Next.js)
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
const MarkerClusterGroup = dynamic(
  () => import('react-leaflet-cluster'),
  { ssr: false }
);

/**
 * HazardMap Component - Production-ready interactive map with OpenStreetMap
 * Features:
 * - Real-time hazard data from backend API
 * - Marker clustering for performance
 * - Interactive popups with full details
 * - Filtering by hazard type and category
 * - Search functionality
 * - User geolocation
 * - Custom color-coded markers
 * - Responsive design
 * - No API key required!
 */
function MapViewContent() {
  // State management
  const [hazards, setHazards] = useState([]);
  const [filteredHazards, setFilteredHazards] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);
  const [userLocation, setUserLocation] = useState(null);
  const [mapCenter, setMapCenter] = useState([19.2183, 72.9781]); // Thane, Maharashtra [lat, lng]
  const [mapZoom, setMapZoom] = useState(12);
  const [searchQuery, setSearchQuery] = useState('');
  const [isMapReady, setIsMapReady] = useState(false);
  const [isGettingLocation, setIsGettingLocation] = useState(false);

  // Filter states
  const [filters, setFilters] = useState({
    hazardType: '',
    category: ''
  });
  const [showFilters, setShowFilters] = useState(false);

  // Hazard types for filter dropdown
  const hazardTypes = [
    'High Waves',
    'Rip Current',
    'Storm Surge/Cyclone Effects',
    'Flooded Coastline',
    'Beached Aquatic Animal',
    'Oil Spill',
    'Fisher Nets Entanglement',
    'Ship Wreck',
    'Chemical Spill',
    'Plastic Pollution'
  ];

  /**
   * Get marker color based on hazard type
   */
  const getMarkerColor = (hazardType) => {
    const colors = {
      'High Waves': '#EF4444', // red
      'Rip Current': '#DC2626', // dark red
      'Storm Surge/Cyclone Effects': '#B91C1C', // darker red
      'Flooded Coastline': '#3B82F6', // blue
      'Beached Aquatic Animal': '#10B981', // green
      'Oil Spill': '#8B5CF6', // purple
      'Fisher Nets Entanglement': '#F59E0B', // amber
      'Ship Wreck': '#6B7280', // gray
      'Chemical Spill': '#DC2626', // dark red
      'Plastic Pollution': '#059669' // emerald
    };
    return colors[hazardType] || '#3B82F6';
  };

  /**
   * Create custom icon for markers - improved design with better visibility
   */
  const createCustomIcon = (hazard) => {
    if (typeof window === 'undefined') return null;

    const L = require('leaflet');
    const color = getMarkerColor(hazard.hazard_type);

    return L.divIcon({
      className: 'custom-marker',
      html: `
        <div style="
          background: linear-gradient(135deg, ${color} 0%, ${color}dd 100%);
          width: 40px;
          height: 40px;
          border-radius: 50% 50% 50% 0;
          transform: rotate(-45deg);
          border: 4px solid white;
          box-shadow: 0 4px 12px rgba(0,0,0,0.4), 0 0 0 2px ${color}44;
          transition: all 0.3s ease;
        ">
          <div style="
            position: absolute;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%) rotate(45deg);
            color: white;
            font-size: 20px;
            font-weight: bold;
            text-shadow: 0 2px 4px rgba(0,0,0,0.3);
          ">
            ⚠
          </div>
        </div>
      `,
      iconSize: [40, 40],
      iconAnchor: [20, 40],
      popupAnchor: [0, -40]
    });
  };

  /**
   * Create user location icon with pulsing animation
   */
  const createUserIcon = () => {
    if (typeof window === 'undefined') return null;

    const L = require('leaflet');

    return L.divIcon({
      className: 'user-marker',
      html: `
        <style>
          @keyframes pulse {
            0% { transform: scale(1); opacity: 1; }
            50% { transform: scale(1.5); opacity: 0.5; }
            100% { transform: scale(1); opacity: 1; }
          }
        </style>
        <div style="position: relative; width: 28px; height: 28px;">
          <div style="
            position: absolute;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            background-color: #3B82F6;
            width: 28px;
            height: 28px;
            border-radius: 50%;
            border: 5px solid white;
            box-shadow: 0 3px 12px rgba(59, 130, 246, 0.6);
            animation: pulse 2s infinite;
          "></div>
          <div style="
            position: absolute;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            background-color: #3B82F6;
            width: 18px;
            height: 18px;
            border-radius: 50%;
            border: 3px solid white;
          "></div>
        </div>
      `,
      iconSize: [28, 28],
      iconAnchor: [14, 14]
    });
  };

  /**
   * Fetch hazard data from API
   * Fetches multiple pages if needed (backend limits to 100 per page)
   */
  const fetchHazards = async () => {
    try {
      setIsLoading(true);
      setError(null);

      console.log('Fetching hazards from API...');

      // Fetch first page to get total count
      const firstResponse = await getHazardReports({
        page: 1,
        page_size: 100
      });

      console.log('First page response:', firstResponse);

      if (firstResponse && firstResponse.reports) {
        let allHazards = [...firstResponse.reports];
        const totalPages = Math.ceil(firstResponse.total / 100);

        // Fetch remaining pages if needed
        if (totalPages > 1) {
          console.log(`Fetching ${totalPages - 1} more pages...`);

          const pagePromises = [];
          for (let page = 2; page <= Math.min(totalPages, 10); page++) {
            pagePromises.push(
              getHazardReports({
                page,
                page_size: 100
              })
            );
          }

          const additionalResponses = await Promise.all(pagePromises);
          additionalResponses.forEach(response => {
            if (response && response.reports) {
              allHazards = [...allHazards, ...response.reports];
            }
          });
        }

        // Filter out hazards without location data
        const validHazards = allHazards.filter(
          hazard => hazard.location?.latitude && hazard.location?.longitude
        );

        console.log(`✅ Loaded ${validHazards.length} hazards with valid locations out of ${allHazards.length} total`);
        console.log('📍 Hazard details:', validHazards.map(h => ({
          id: h.report_id,
          type: h.hazard_type,
          location: h.location.address,
          coords: [h.location.latitude, h.location.longitude],
          status: h.verification_status
        })));

        setHazards(validHazards);
        setFilteredHazards(validHazards);

        // Center map on first hazard if available, otherwise use user location or default
        if (validHazards.length > 0 && !userLocation) {
          const firstHazard = validHazards[0];
          setMapCenter([firstHazard.location.latitude, firstHazard.location.longitude]);
          console.log('🗺️ Map centered on first hazard:', firstHazard.location);
        }

        if (validHazards.length > 0) {
          toast.success(`✅ Loaded ${validHazards.length} real-time hazards on map`);
        } else {
          toast('ℹ️ No hazards to display. The map is clear!', {
            icon: 'ℹ️',
          });
        }
      } else {
        console.log('No hazards data in response');
        setHazards([]);
        setFilteredHazards([]);
        toast('No hazards found', {
          icon: 'ℹ️',
        });
      }
    } catch (err) {
      console.error('Error fetching hazards:', err);
      console.error('Error details:', err.response?.data || err.message);
      setError('Failed to load hazard data');
      toast.error('Failed to load hazards. Please try again.');
    } finally {
      setIsLoading(false);
    }
  };

  // Fetch hazards on mount
  useEffect(() => {
    fetchHazards();
    setIsMapReady(true);
  }, []);

  /**
   * Get user's current location
   */
  const getUserLocation = () => {
    if ('geolocation' in navigator) {
      setIsGettingLocation(true);
      const loadingToast = toast.loading('Detecting your location...');

      navigator.geolocation.getCurrentPosition(
        (position) => {
          const location = [position.coords.latitude, position.coords.longitude];
          console.log('User location detected:', location);
          setUserLocation(location);
          setMapCenter(location);
          setMapZoom(14);
          toast.dismiss(loadingToast);
          toast.success('Location detected!');
          setIsGettingLocation(false);
        },
        (error) => {
          console.error('Geolocation error:', error);
          toast.dismiss(loadingToast);

          let errorMessage = 'Unable to detect location';
          switch(error.code) {
            case error.PERMISSION_DENIED:
              errorMessage = 'Location permission denied. Please enable location access.';
              break;
            case error.POSITION_UNAVAILABLE:
              errorMessage = 'Location information unavailable';
              break;
            case error.TIMEOUT:
              errorMessage = 'Location request timed out';
              break;
          }
          toast.error(errorMessage);
          setIsGettingLocation(false);
        },
        {
          enableHighAccuracy: true,
          timeout: 15000,
          maximumAge: 0
        }
      );
    } else {
      toast.error('Geolocation not supported by your browser');
    }
  };

  /**
   * Apply filters to hazards
   */
  useEffect(() => {
    let filtered = [...hazards];

    if (filters.hazardType) {
      filtered = filtered.filter(h => h.hazard_type === filters.hazardType);
    }

    if (filters.category) {
      filtered = filtered.filter(h => h.category === filters.category);
    }

    if (searchQuery) {
      const query = searchQuery.toLowerCase();
      filtered = filtered.filter(h =>
        h.hazard_type?.toLowerCase().includes(query) ||
        h.location?.address?.toLowerCase().includes(query) ||
        h.description?.toLowerCase().includes(query)
      );
    }

    setFilteredHazards(filtered);
  }, [hazards, filters, searchQuery]);

  /**
   * Get status badge styling
   */
  const getStatusBadge = (status) => {
    const badges = {
      verified: { bg: 'bg-green-100', text: 'text-green-700', label: 'Verified' },
      pending: { bg: 'bg-yellow-100', text: 'text-yellow-700', label: 'Pending' },
      rejected: { bg: 'bg-red-100', text: 'text-red-700', label: 'Rejected' }
    };
    return badges[status] || badges.pending;
  };

  /**
   * Format date to readable format
   */
  const formatDate = (dateString) => {
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  /**
   * Reset all filters
   */
  const resetFilters = () => {
    setFilters({
      hazardType: '',
      category: ''
    });
    setSearchQuery('');
    toast.success('Filters cleared');
  };

  return (
    <div className="p-4 lg:p-8">
      <Toaster position="top-center" />

      <div className="max-w-7xl mx-auto">
        {/* Page Header */}
        <div className="mb-6">
          <div className="flex items-center justify-between flex-wrap gap-4">
            <div>
              <h1 className="text-3xl font-bold text-gray-900 flex items-center">
                <MapIcon className="w-8 h-8 mr-3 text-blue-600" />
                Hazard Map
              </h1>
              <p className="text-gray-600 mt-1">
                Real-time visualization of {filteredHazards.length} hazard{filteredHazards.length !== 1 ? 's' : ''} on OpenStreetMap
              </p>
            </div>
            <div className="flex items-center space-x-3">
              <button
                onClick={fetchHazards}
                disabled={isLoading}
                className="px-4 py-2 bg-white border border-gray-300 hover:bg-gray-50 text-gray-700 rounded-xl font-semibold transition-colors flex items-center space-x-2 disabled:opacity-50"
              >
                <RefreshCw className={`w-4 h-4 ${isLoading ? 'animate-spin' : ''}`} />
                <span>Refresh</span>
              </button>
              <button
                onClick={getUserLocation}
                disabled={isLoading || isGettingLocation}
                className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-xl font-semibold transition-colors flex items-center space-x-2 disabled:opacity-50"
              >
                {isGettingLocation ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    <span>Locating...</span>
                  </>
                ) : (
                  <>
                    <Navigation className="w-4 h-4" />
                    <span>My Location</span>
                  </>
                )}
              </button>
            </div>
          </div>
        </div>

        {/* Map Container */}
        <div className="bg-white rounded-2xl shadow-lg border border-gray-200 overflow-hidden">
          {/* Map Toolbar */}
          <div className="bg-gray-50 border-b border-gray-200 p-4">
            <div className="flex flex-wrap items-center gap-3">
              {/* Filter Button */}
              <button
                onClick={() => setShowFilters(!showFilters)}
                className={`px-4 py-2 border rounded-lg text-sm font-medium transition-all flex items-center space-x-2 ${
                  showFilters || Object.values(filters).some(f => f)
                    ? 'bg-blue-100 border-blue-300 text-blue-700'
                    : 'bg-white border-gray-300 text-gray-700 hover:bg-gray-50'
                }`}
              >
                <Filter className="w-4 h-4" />
                <span>Filters</span>
                {Object.values(filters).some(f => f) && (
                  <span className="w-2 h-2 bg-blue-600 rounded-full"></span>
                )}
              </button>

              {/* Search Box */}
              <div className="flex-1 min-w-[200px] max-w-md">
                <div className="relative">
                  <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-gray-400" />
                  <input
                    type="text"
                    placeholder="Search hazards or locations..."
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                  {searchQuery && (
                    <button
                      onClick={() => setSearchQuery('')}
                      className="absolute right-3 top-1/2 transform -translate-y-1/2"
                    >
                      <X className="w-4 h-4 text-gray-400 hover:text-gray-600" />
                    </button>
                  )}
                </div>
              </div>

              {/* Stats */}
              <div className="ml-auto flex items-center space-x-2 text-sm text-gray-600">
                <MapPin className="w-4 h-4" />
                <span className="font-medium">
                  {filteredHazards.length} of {hazards.length} hazards
                </span>
              </div>
            </div>

            {/* Filter Dropdowns */}
            {showFilters && (
              <div className="mt-4 grid grid-cols-1 sm:grid-cols-3 gap-3 pt-4 border-t border-gray-200">
                {/* Hazard Type Filter */}
                <div>
                  <label className="block text-xs font-medium text-gray-700 mb-1">Hazard Type</label>
                  <select
                    value={filters.hazardType}
                    onChange={(e) => setFilters({...filters, hazardType: e.target.value})}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                  >
                    <option value="">All Types</option>
                    {hazardTypes.map(type => (
                      <option key={type} value={type}>{type}</option>
                    ))}
                  </select>
                </div>

                {/* Category Filter */}
                <div>
                  <label className="block text-xs font-medium text-gray-700 mb-1">Category</label>
                  <select
                    value={filters.category}
                    onChange={(e) => setFilters({...filters, category: e.target.value})}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                  >
                    <option value="">All Categories</option>
                    <option value="natural">Natural Hazards</option>
                    <option value="humanMade">Human-Made Hazards</option>
                  </select>
                </div>

                {/* Reset Button */}
                <div className="flex items-end">
                  <button
                    onClick={resetFilters}
                    className="w-full px-3 py-2 bg-gray-100 hover:bg-gray-200 text-gray-700 rounded-lg text-sm font-medium transition-colors"
                  >
                    Reset Filters
                  </button>
                </div>
              </div>
            )}
          </div>

          {/* Leaflet Map */}
          <div className="relative h-[600px]">
            {/* Floating Info Panel */}
            {!isLoading && !error && isMapReady && (
              <div className="absolute top-4 right-4 z-[1000] bg-white rounded-xl shadow-lg border border-gray-200 p-4 min-w-[200px]">
                <div className="space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-medium text-gray-600">Total Hazards</span>
                    <span className="text-lg font-bold text-gray-900">{filteredHazards.length}</span>
                  </div>
                  {userLocation && (
                    <div className="flex items-center space-x-2 text-xs text-green-600">
                      <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></div>
                      <span>Location Detected</span>
                    </div>
                  )}
                  <div className="pt-2 border-t border-gray-200">
                    <div className="text-xs text-gray-500">
                      <div className="flex items-center space-x-1">
                        <div className="w-2 h-2 bg-blue-500 rounded-full"></div>
                        <span>Real-time Data</span>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            )}

            {/* No Hazards Message */}
            {!isLoading && !error && isMapReady && filteredHazards.length === 0 && (
              <div className="absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 z-[999] bg-white rounded-xl shadow-lg border border-gray-200 p-6 text-center">
                <CheckCircle className="w-12 h-12 text-green-500 mx-auto mb-3" />
                <h3 className="text-lg font-bold text-gray-900 mb-2">All Clear!</h3>
                <p className="text-gray-600 text-sm">No hazards reported in this area.</p>
              </div>
            )}

            {isLoading && (
              <div className="absolute inset-0 bg-white bg-opacity-90 z-[1000] flex items-center justify-center">
                <div className="text-center">
                  <Loader2 className="w-12 h-12 text-blue-600 animate-spin mx-auto mb-4" />
                  <p className="text-gray-600">Loading map data...</p>
                </div>
              </div>
            )}

            {error && (
              <div className="absolute inset-0 bg-white z-[1000] flex items-center justify-center">
                <div className="text-center">
                  <AlertTriangle className="w-12 h-12 text-red-500 mx-auto mb-4" />
                  <p className="text-gray-600 mb-4">{error}</p>
                  <button
                    onClick={fetchHazards}
                    className="px-4 py-2 bg-blue-600 text-white rounded-xl hover:bg-blue-700 transition-colors"
                  >
                    Retry
                  </button>
                </div>
              </div>
            )}

            {isMapReady && (
              <MapContainer
                center={mapCenter}
                zoom={mapZoom}
                style={{ height: '100%', width: '100%' }}
                scrollWheelZoom={true}
                zoomControl={true}
                key={`${mapCenter[0]}-${mapCenter[1]}-${mapZoom}`}
              >
                {/* Using CartoDB Voyager tiles for better clarity and detail */}
                <TileLayer
                  attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>'
                  url="https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png"
                  maxZoom={20}
                />

                {/* User Location Marker */}
                {userLocation && (
                  <Marker position={userLocation} icon={createUserIcon()}>
                    <Popup>
                      <div className="text-center">
                        <p className="font-bold text-blue-600">Your Location</p>
                      </div>
                    </Popup>
                  </Marker>
                )}

                {/* Hazard Markers with Clustering */}
                <MarkerClusterGroup
                  chunkedLoading
                  maxClusterRadius={50}
                  spiderfyOnMaxZoom={true}
                  showCoverageOnHover={false}
                >
                  {filteredHazards.map((hazard) => (
                    <Marker
                      key={hazard.report_id}
                      position={[hazard.location.latitude, hazard.location.longitude]}
                      icon={createCustomIcon(hazard)}
                    >
                      <Popup maxWidth={300} className="hazard-popup">
                        <div className="p-2">
                          {/* Title & Status */}
                          <div className="flex items-start justify-between mb-2">
                            <h3 className="font-bold text-gray-900 text-sm pr-2">{hazard.hazard_type}</h3>
                            <span className={`px-2 py-0.5 ${getStatusBadge(hazard.verification_status).bg} ${getStatusBadge(hazard.verification_status).text} text-xs font-semibold rounded-full whitespace-nowrap`}>
                              {getStatusBadge(hazard.verification_status).label}
                            </span>
                          </div>

                          {/* Image */}
                          {hazard.image_url && (
                            <img
                              src={hazard.image_url}
                              alt={hazard.hazard_type}
                              className="w-full h-32 object-cover rounded-lg mb-2"
                            />
                          )}

                          {/* Location */}
                          <div className="flex items-start space-x-2 text-xs text-gray-600 mb-2">
                            <MapPin className="w-3 h-3 mt-0.5 flex-shrink-0" />
                            <span className="line-clamp-2">{hazard.location.address}</span>
                          </div>

                          {/* Description */}
                          {hazard.description && (
                            <p className="text-xs text-gray-700 mb-2 line-clamp-3">
                              {hazard.description}
                            </p>
                          )}

                          {/* Weather Info */}
                          {hazard.weather && (
                            <div className="flex items-center space-x-3 text-xs text-gray-600 mb-2 pb-2 border-b border-gray-200">
                              {hazard.weather.wind && (
                                <div className="flex items-center space-x-1">
                                  <Wind className="w-3 h-3" />
                                  <span>{hazard.weather.wind} km/h</span>
                                </div>
                              )}
                              {hazard.weather.humidity && (
                                <div className="flex items-center space-x-1">
                                  <Droplets className="w-3 h-3" />
                                  <span>{hazard.weather.humidity}%</span>
                                </div>
                              )}
                              {hazard.weather.temperature && (
                                <span>{hazard.weather.temperature}°C</span>
                              )}
                            </div>
                          )}

                          {/* Stats & Date */}
                          <div className="flex items-center justify-between text-xs text-gray-500 mb-2">
                            <div className="flex items-center space-x-3">
                              <div className="flex items-center space-x-1">
                                <Eye className="w-3 h-3" />
                                <span>{hazard.views || 0}</span>
                              </div>
                              <div className="flex items-center space-x-1">
                                <ThumbsUp className="w-3 h-3" />
                                <span>{hazard.likes || 0}</span>
                              </div>
                            </div>
                            <div className="flex items-center space-x-1">
                              <Calendar className="w-3 h-3" />
                              <span>{formatDate(hazard.created_at)}</span>
                            </div>
                          </div>

                          {/* View Details Button */}
                          <button
                            onClick={() => window.location.href = `/my-reports`}
                            className="w-full px-3 py-1.5 bg-blue-600 hover:bg-blue-700 text-white text-xs font-semibold rounded-lg transition-colors"
                          >
                            View Full Details
                          </button>
                        </div>
                      </Popup>
                    </Marker>
                  ))}
                </MarkerClusterGroup>
              </MapContainer>
            )}
          </div>

          {/* Legend */}
          <div className="bg-gray-50 border-t border-gray-200 p-4">
            <h4 className="text-sm font-semibold text-gray-900 mb-3 flex items-center">
              <Layers className="w-4 h-4 mr-2" />
              Legend
            </h4>
            <div className="flex flex-wrap gap-4 text-xs">
              <div className="flex items-center space-x-2">
                <div className="w-3 h-3 bg-red-500 rounded-full"></div>
                <span className="text-gray-700">High Risk (Waves, Currents)</span>
              </div>
              <div className="flex items-center space-x-2">
                <div className="w-3 h-3 bg-blue-500 rounded-full"></div>
                <span className="text-gray-700">Water Related</span>
              </div>
              <div className="flex items-center space-x-2">
                <div className="w-3 h-3 bg-purple-500 rounded-full"></div>
                <span className="text-gray-700">Pollution</span>
              </div>
              <div className="flex items-center space-x-2">
                <div className="w-3 h-3 bg-green-500 rounded-full"></div>
                <span className="text-gray-700">Wildlife/Environment</span>
              </div>
              <div className="flex items-center space-x-2">
                <div className="w-3 h-3 bg-amber-500 rounded-full"></div>
                <span className="text-gray-700">Human Activity</span>
              </div>
              <div className="flex items-center space-x-2">
                <div className="w-3 h-3 bg-blue-600 rounded-full border-2 border-white"></div>
                <span className="text-gray-700">Your Location</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default function MapPage() {
  return (
    <ProtectedRoute>
      <DashboardLayout>
        <MapViewContent />
      </DashboardLayout>
    </ProtectedRoute>
  );
}
