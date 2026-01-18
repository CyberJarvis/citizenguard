'use client';

import { useState, useEffect } from 'react';
import {
  Cloud,
  Wind,
  Droplets,
  Waves,
  Thermometer,
  Eye,
  Gauge,
  Sun,
  Moon,
  Activity,
  MapPin,
  RefreshCw,
  ChevronDown,
  ChevronUp,
  AlertTriangle
} from 'lucide-react';
import { fetchEnvironmentalData, formatEnvironmentalData } from '@/lib/api';

/**
 * Environmental Data Card Component
 * Displays weather, marine, seismic, and astronomy data for a location
 */
export default function EnvironmentalDataCard({
  latitude,
  longitude,
  initialData = null,
  compact = false,
  showRefresh = true,
  onDataLoaded = null
}) {
  const [data, setData] = useState(initialData);
  const [loading, setLoading] = useState(!initialData);
  const [error, setError] = useState(null);
  const [expanded, setExpanded] = useState(!compact);
  const [lastUpdated, setLastUpdated] = useState(null);

  // Fetch environmental data
  const fetchData = async () => {
    if (!latitude || !longitude) return;

    try {
      setLoading(true);
      setError(null);

      const response = await fetchEnvironmentalData(latitude, longitude);

      if (response.success) {
        setData(response.snapshot);
        setLastUpdated(new Date(response.fetched_at));
        if (onDataLoaded) {
          onDataLoaded(response.snapshot);
        }
      } else {
        setError('Failed to fetch environmental data');
      }
    } catch (err) {
      console.error('Environmental data fetch error:', err);
      setError(err.message || 'Failed to load environmental data');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (!initialData && latitude && longitude) {
      fetchData();
    }
  }, [latitude, longitude, initialData]);

  // Format the data for display
  const formatted = data ? formatEnvironmentalData(data) : null;

  if (loading) {
    return (
      <div className="bg-white rounded-2xl shadow-lg border border-gray-200 p-6">
        <div className="flex items-center justify-center py-8">
          <div className="flex flex-col items-center gap-3">
            <div className="animate-spin rounded-full h-10 w-10 border-t-2 border-b-2 border-sky-500"></div>
            <p className="text-sm text-gray-500">Fetching environmental data...</p>
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-white rounded-2xl shadow-lg border border-gray-200 p-6">
        <div className="text-center py-6">
          <AlertTriangle className="w-12 h-12 text-orange-500 mx-auto mb-3" />
          <p className="text-sm font-medium text-gray-900 mb-1">Unable to Load Data</p>
          <p className="text-xs text-gray-500 mb-4">{error}</p>
          {showRefresh && (
            <button
              onClick={fetchData}
              className="px-4 py-2 text-sm font-medium text-sky-600 bg-sky-50 rounded-lg hover:bg-sky-100 transition-colors"
            >
              Try Again
            </button>
          )}
        </div>
      </div>
    );
  }

  if (!data) {
    return (
      <div className="bg-white rounded-2xl shadow-lg border border-gray-200 p-6">
        <div className="text-center py-6">
          <MapPin className="w-12 h-12 text-gray-300 mx-auto mb-3" />
          <p className="text-sm text-gray-500">No location data available</p>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-2xl shadow-lg border border-gray-200 overflow-hidden">
      {/* Header */}
      <div
        className="p-4 bg-gradient-to-r from-sky-50 to-blue-50 border-b border-gray-200 cursor-pointer"
        onClick={() => setExpanded(!expanded)}
      >
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-sky-100 flex items-center justify-center">
              <Cloud className="w-5 h-5 text-sky-600" />
            </div>
            <div>
              <h3 className="text-base font-bold text-gray-900">Environmental Conditions</h3>
              {lastUpdated && (
                <p className="text-xs text-gray-500">
                  Updated {lastUpdated.toLocaleTimeString()}
                </p>
              )}
            </div>
          </div>
          <div className="flex items-center gap-2">
            {showRefresh && (
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  fetchData();
                }}
                className="p-2 text-gray-500 hover:text-sky-600 hover:bg-sky-50 rounded-lg transition-colors"
                disabled={loading}
              >
                <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
              </button>
            )}
            {compact && (
              expanded ? <ChevronUp className="w-5 h-5 text-gray-400" /> : <ChevronDown className="w-5 h-5 text-gray-400" />
            )}
          </div>
        </div>
      </div>

      {/* Content */}
      {expanded && (
        <div className="p-4 space-y-4">
          {/* Weather Section */}
          {formatted?.weather && (
            <div className="bg-gradient-to-br from-blue-50 to-sky-50 rounded-xl p-4">
              <h4 className="text-sm font-bold text-gray-900 mb-3 flex items-center gap-2">
                <Cloud className="w-4 h-4 text-blue-500" />
                Weather
              </h4>
              <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
                <DataItem
                  icon={Thermometer}
                  label="Temperature"
                  value={formatted.weather.temperature}
                  subValue={`Feels ${formatted.weather.feelsLike}`}
                  iconColor="text-red-500"
                />
                <DataItem
                  icon={Wind}
                  label="Wind"
                  value={formatted.weather.wind}
                  subValue={formatted.weather.gusts ? `Gusts ${formatted.weather.gusts}` : null}
                  iconColor="text-blue-500"
                />
                <DataItem
                  icon={Gauge}
                  label="Pressure"
                  value={formatted.weather.pressure}
                  iconColor="text-purple-500"
                />
                <DataItem
                  icon={Droplets}
                  label="Humidity"
                  value={formatted.weather.humidity}
                  iconColor="text-cyan-500"
                />
                <DataItem
                  icon={Eye}
                  label="Visibility"
                  value={formatted.weather.visibility}
                  iconColor="text-gray-500"
                />
                <DataItem
                  icon={Cloud}
                  label="Condition"
                  value={formatted.weather.condition || 'N/A'}
                  iconColor="text-sky-500"
                />
              </div>
            </div>
          )}

          {/* Marine Section */}
          {formatted?.marine && (
            <div className="bg-gradient-to-br from-cyan-50 to-teal-50 rounded-xl p-4">
              <h4 className="text-sm font-bold text-gray-900 mb-3 flex items-center gap-2">
                <Waves className="w-4 h-4 text-cyan-500" />
                Marine Conditions
              </h4>
              <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
                {formatted.marine.waveHeight && (
                  <DataItem
                    icon={Waves}
                    label="Wave Height"
                    value={formatted.marine.waveHeight}
                    iconColor="text-cyan-500"
                  />
                )}
                {formatted.marine.swellHeight && (
                  <DataItem
                    icon={Waves}
                    label="Swell Height"
                    value={formatted.marine.swellHeight}
                    subValue={formatted.marine.swellDirection}
                    iconColor="text-blue-500"
                  />
                )}
                {formatted.marine.swellPeriod && (
                  <DataItem
                    icon={Activity}
                    label="Swell Period"
                    value={formatted.marine.swellPeriod}
                    iconColor="text-indigo-500"
                  />
                )}
                {formatted.marine.waterTemp && (
                  <DataItem
                    icon={Thermometer}
                    label="Water Temp"
                    value={formatted.marine.waterTemp}
                    iconColor="text-teal-500"
                  />
                )}
                {formatted.marine.tideType && (
                  <DataItem
                    icon={Waves}
                    label="Tide"
                    value={formatted.marine.tideType}
                    subValue={formatted.marine.tideHeight}
                    iconColor="text-slate-500"
                  />
                )}
              </div>
            </div>
          )}

          {/* Seismic Section */}
          {formatted?.seismic && formatted.seismic.magnitude && (
            <div className={`rounded-xl p-4 ${
              data.seismic?.tsunami === 1
                ? 'bg-gradient-to-br from-red-50 to-orange-50 border-2 border-red-200'
                : 'bg-gradient-to-br from-orange-50 to-amber-50'
            }`}>
              <h4 className="text-sm font-bold text-gray-900 mb-3 flex items-center gap-2">
                <Activity className="w-4 h-4 text-orange-500" />
                Recent Seismic Activity
                {data.seismic?.tsunami === 1 && (
                  <span className="px-2 py-0.5 text-xs font-bold bg-red-500 text-white rounded animate-pulse">
                    TSUNAMI WARNING
                  </span>
                )}
              </h4>
              <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
                <DataItem
                  icon={Activity}
                  label="Magnitude"
                  value={formatted.seismic.magnitude}
                  iconColor="text-orange-500"
                  highlight={parseFloat(data.seismic?.magnitude) >= 5}
                />
                {formatted.seismic.depth && (
                  <DataItem
                    icon={MapPin}
                    label="Depth"
                    value={formatted.seismic.depth}
                    iconColor="text-amber-500"
                  />
                )}
                {formatted.seismic.distance && (
                  <DataItem
                    icon={MapPin}
                    label="Distance"
                    value={formatted.seismic.distance}
                    iconColor="text-yellow-500"
                  />
                )}
              </div>
              {formatted.seismic.location && (
                <p className="text-xs text-gray-600 mt-3 flex items-center gap-1">
                  <MapPin className="w-3 h-3" />
                  {formatted.seismic.location}
                </p>
              )}
            </div>
          )}

          {/* Astronomy Section */}
          {formatted?.astronomy && (
            <div className="bg-gradient-to-br from-indigo-50 to-purple-50 rounded-xl p-4">
              <h4 className="text-sm font-bold text-gray-900 mb-3 flex items-center gap-2">
                {formatted.astronomy.isDay ? (
                  <Sun className="w-4 h-4 text-yellow-500" />
                ) : (
                  <Moon className="w-4 h-4 text-indigo-500" />
                )}
                Astronomy
              </h4>
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                <DataItem
                  icon={Sun}
                  label="Sunrise"
                  value={formatted.astronomy.sunrise}
                  iconColor="text-yellow-500"
                />
                <DataItem
                  icon={Sun}
                  label="Sunset"
                  value={formatted.astronomy.sunset}
                  iconColor="text-orange-500"
                />
                <DataItem
                  icon={Moon}
                  label="Moon Phase"
                  value={formatted.astronomy.moonPhase}
                  iconColor="text-indigo-500"
                />
              </div>
            </div>
          )}

          {/* No Data Available */}
          {!formatted?.weather && !formatted?.marine && !formatted?.seismic && (
            <div className="text-center py-4">
              <p className="text-sm text-gray-500">No environmental data available for this location</p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// Helper component for displaying data items
function DataItem({ icon: Icon, label, value, subValue, iconColor = 'text-gray-500', highlight = false }) {
  return (
    <div className={`flex items-start gap-2 ${highlight ? 'bg-white/50 p-2 rounded-lg border border-orange-200' : ''}`}>
      <div className={`p-1.5 rounded-lg ${highlight ? 'bg-orange-100' : 'bg-white/60'}`}>
        <Icon className={`w-4 h-4 ${highlight ? 'text-orange-600' : iconColor}`} />
      </div>
      <div className="min-w-0">
        <p className="text-xs text-gray-500">{label}</p>
        <p className={`text-sm font-semibold ${highlight ? 'text-orange-700' : 'text-gray-900'} truncate`}>
          {value || 'N/A'}
        </p>
        {subValue && (
          <p className="text-xs text-gray-400 truncate">{subValue}</p>
        )}
      </div>
    </div>
  );
}
