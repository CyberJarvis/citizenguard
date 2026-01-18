'use client';

import { useState, useEffect, useRef } from 'react';
import { useRouter } from 'next/navigation';
import dynamic from 'next/dynamic';
import useAuthStore from '@/context/AuthContext';
import DashboardLayout from '@/components/DashboardLayout';
import PageHeader from '@/components/PageHeader';
import { useAnalystStore } from '@/stores/analystStore';
import { getGeoAnalytics } from '@/lib/api';
import 'leaflet/dist/leaflet.css';
import {
  MapPin,
  Filter,
  RefreshCw,
  ArrowLeft,
  ChevronDown,
  Loader2,
  Layers,
  Eye,
  EyeOff,
  AlertTriangle,
  Activity,
  Thermometer
} from 'lucide-react';
import toast from 'react-hot-toast';

// Dynamic imports for map components
const MapContainer = dynamic(
  () => import('react-leaflet').then((mod) => mod.MapContainer),
  { ssr: false }
);
const TileLayer = dynamic(
  () => import('react-leaflet').then((mod) => mod.TileLayer),
  { ssr: false }
);
const CircleMarker = dynamic(
  () => import('react-leaflet').then((mod) => mod.CircleMarker),
  { ssr: false }
);
const Popup = dynamic(
  () => import('react-leaflet').then((mod) => mod.Popup),
  { ssr: false }
);
const Tooltip = dynamic(
  () => import('react-leaflet').then((mod) => mod.Tooltip),
  { ssr: false }
);

// Dynamic import for ApexCharts
const Chart = dynamic(() => import('react-apexcharts'), { ssr: false });

const dateRangeOptions = [
  { value: '7days', label: 'Last 7 Days' },
  { value: '30days', label: 'Last 30 Days' },
  { value: '90days', label: 'Last 90 Days' },
  { value: '1year', label: 'Last Year' }
];

const hazardColors = {
  high_waves: '#3B82F6',
  strong_currents: '#10B981',
  storm_surge: '#F59E0B',
  jellyfish: '#EC4899',
  pollution: '#8B5CF6',
  water_temperature: '#EF4444'
};

const severityColors = {
  critical: '#EF4444',
  high: '#F97316',
  medium: '#F59E0B',
  low: '#22C55E'
};

function GeoAnalysisContent() {
  const router = useRouter();
  const { user } = useAuthStore();
  const { defaultDateRange } = useAnalystStore();

  const [dateRange, setDateRange] = useState(defaultDateRange);
  const [geoData, setGeoData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [showFilters, setShowFilters] = useState(false);
  const [mapReady, setMapReady] = useState(false);

  // Map view options
  const [viewMode, setViewMode] = useState('cluster'); // 'cluster', 'heatmap', 'markers'
  const [hazardFilter, setHazardFilter] = useState('all');
  const [severityFilter, setSeverityFilter] = useState('all');
  const [showLegend, setShowLegend] = useState(true);

  // Selected region
  const [selectedRegion, setSelectedRegion] = useState(null);

  // Check authorization
  useEffect(() => {
    if (user && !['analyst', 'authority_admin'].includes(user.role)) {
      router.push('/dashboard');
    }
  }, [user, router]);

  // Map ready effect
  useEffect(() => {
    setMapReady(true);
  }, []);

  // Fetch geo data
  const fetchGeoData = async () => {
    setLoading(true);
    try {
      const response = await getGeoAnalytics({
        date_range: dateRange,
        hazard_type: hazardFilter !== 'all' ? hazardFilter : undefined,
        min_severity: severityFilter !== 'all' ? severityFilter : undefined
      });

      if (response.success) {
        setGeoData(response.data);
      }
    } catch (error) {
      console.error('Error fetching geo data:', error);
      toast.error('Failed to load geo data');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchGeoData();
  }, [dateRange, hazardFilter, severityFilter]);

  // Filter report points based on current filters
  const filteredPoints = geoData?.report_points?.filter(point => {
    if (hazardFilter !== 'all' && point.hazard_type !== hazardFilter) return false;
    if (severityFilter !== 'all' && point.severity !== severityFilter) return false;
    return true;
  }) || [];

  // Get point color based on view mode
  const getPointColor = (point) => {
    if (viewMode === 'markers') {
      return hazardColors[point.hazard_type] || '#6B7280';
    }
    return severityColors[point.severity] || '#6B7280';
  };

  // Get point radius based on severity
  const getPointRadius = (point) => {
    const baseRadius = 8;
    if (point.severity === 'critical') return baseRadius + 4;
    if (point.severity === 'high') return baseRadius + 2;
    if (point.severity === 'medium') return baseRadius;
    return baseRadius - 2;
  };

  // Regional stats chart
  const regionalChartOptions = {
    chart: {
      type: 'bar',
      toolbar: { show: false },
      fontFamily: 'inherit'
    },
    plotOptions: {
      bar: { horizontal: true, borderRadius: 4, barHeight: '60%' }
    },
    dataLabels: { enabled: false },
    xaxis: {
      categories: geoData?.regional_stats?.slice(0, 10).map(r => r.region) || []
    },
    colors: ['#3B82F6'],
    grid: { borderColor: '#E5E7EB' }
  };

  // Hotspot severity chart
  const hotspotChartOptions = {
    chart: {
      type: 'donut',
      fontFamily: 'inherit'
    },
    labels: ['Critical', 'High', 'Medium', 'Low'],
    colors: ['#EF4444', '#F97316', '#F59E0B', '#22C55E'],
    legend: { position: 'bottom' },
    dataLabels: {
      enabled: true,
      formatter: (val) => `${val.toFixed(0)}%`
    },
    plotOptions: {
      pie: {
        donut: { size: '55%' }
      }
    }
  };

  const hotspotSeries = geoData?.severity_distribution
    ? [
        geoData.severity_distribution.critical || 0,
        geoData.severity_distribution.high || 0,
        geoData.severity_distribution.medium || 0,
        geoData.severity_distribution.low || 0
      ]
    : [];

  if (loading && !geoData) {
    return (
      <DashboardLayout>
        <div className="flex items-center justify-center min-h-[60vh]">
          <div className="text-center">
            <Loader2 className="w-12 h-12 text-blue-600 animate-spin mx-auto mb-4" />
            <p className="text-gray-600">Loading geo analysis...</p>
          </div>
        </div>
      </DashboardLayout>
    );
  }

  return (
    <DashboardLayout>
      <div className="p-4 lg:p-6 space-y-6">
        {/* Page Header - Desktop Only */}
        <PageHeader />

        {/* Header */}
        <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
          <div className="flex items-center gap-4">
            <button
              onClick={() => router.push('/analyst/analytics')}
              className="p-2 hover:bg-gray-100 rounded-lg"
            >
              <ArrowLeft className="w-5 h-5 text-gray-600" />
            </button>
            <div>
              <h1 className="text-2xl font-bold text-gray-900">Geo Analysis</h1>
              <p className="text-gray-600 mt-1">Spatial distribution and hotspots</p>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <select
              value={dateRange}
              onChange={(e) => setDateRange(e.target.value)}
              className="px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 bg-white"
            >
              {dateRangeOptions.map(opt => (
                <option key={opt.value} value={opt.value}>{opt.label}</option>
              ))}
            </select>

            <button
              onClick={() => setShowFilters(!showFilters)}
              className="flex items-center gap-2 px-3 py-2 border border-gray-200 rounded-lg hover:bg-gray-50"
            >
              <Filter className="w-4 h-4" />
              <span className="text-sm">Filters</span>
              <ChevronDown className={`w-4 h-4 transition-transform ${showFilters ? 'rotate-180' : ''}`} />
            </button>

            <button
              onClick={fetchGeoData}
              disabled={loading}
              className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
            >
              <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
              Refresh
            </button>
          </div>
        </div>

        {/* Filters panel */}
        {showFilters && (
          <div className="bg-white rounded-xl border border-gray-200 p-4">
            <div className="grid grid-cols-1 sm:grid-cols-4 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">View Mode</label>
                <select
                  value={viewMode}
                  onChange={(e) => setViewMode(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                >
                  <option value="cluster">Clustered</option>
                  <option value="markers">By Hazard Type</option>
                  <option value="heatmap">Severity Heatmap</option>
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Hazard Type</label>
                <select
                  value={hazardFilter}
                  onChange={(e) => setHazardFilter(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                >
                  <option value="all">All Hazards</option>
                  <option value="high_waves">High Waves</option>
                  <option value="strong_currents">Strong Currents</option>
                  <option value="storm_surge">Storm Surge</option>
                  <option value="jellyfish">Jellyfish</option>
                  <option value="pollution">Pollution</option>
                  <option value="water_temperature">Water Temperature</option>
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Severity</label>
                <select
                  value={severityFilter}
                  onChange={(e) => setSeverityFilter(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                >
                  <option value="all">All Severity</option>
                  <option value="critical">Critical</option>
                  <option value="high">High</option>
                  <option value="medium">Medium</option>
                  <option value="low">Low</option>
                </select>
              </div>
              <div className="flex items-end gap-2">
                <button
                  onClick={() => setShowLegend(!showLegend)}
                  className={`flex items-center gap-2 px-3 py-2 border rounded-lg ${
                    showLegend ? 'border-blue-300 bg-blue-50 text-blue-600' : 'border-gray-200 text-gray-600'
                  }`}
                >
                  {showLegend ? <Eye className="w-4 h-4" /> : <EyeOff className="w-4 h-4" />}
                  Legend
                </button>
                <button
                  onClick={() => {
                    setHazardFilter('all');
                    setSeverityFilter('all');
                  }}
                  className="px-3 py-2 text-sm text-gray-600 border border-gray-200 rounded-lg hover:bg-gray-50"
                >
                  Clear
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Summary Stats */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          <div className="bg-white rounded-xl border border-gray-200 p-4">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-blue-100 rounded-lg">
                <MapPin className="w-5 h-5 text-blue-600" />
              </div>
              <div>
                <p className="text-2xl font-bold text-gray-900">
                  {geoData?.total_points?.toLocaleString() || 0}
                </p>
                <p className="text-sm text-gray-600">Total Reports</p>
              </div>
            </div>
          </div>
          <div className="bg-white rounded-xl border border-gray-200 p-4">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-purple-100 rounded-lg">
                <Layers className="w-5 h-5 text-purple-600" />
              </div>
              <div>
                <p className="text-2xl font-bold text-gray-900">
                  {geoData?.regional_stats?.length || 0}
                </p>
                <p className="text-sm text-gray-600">Active Regions</p>
              </div>
            </div>
          </div>
          <div className="bg-white rounded-xl border border-gray-200 p-4">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-red-100 rounded-lg">
                <AlertTriangle className="w-5 h-5 text-red-600" />
              </div>
              <div>
                <p className="text-2xl font-bold text-gray-900">
                  {geoData?.hotspots?.length || 0}
                </p>
                <p className="text-sm text-gray-600">Hotspot Areas</p>
              </div>
            </div>
          </div>
          <div className="bg-white rounded-xl border border-gray-200 p-4">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-amber-100 rounded-lg">
                <Activity className="w-5 h-5 text-amber-600" />
              </div>
              <div>
                <p className="text-2xl font-bold text-gray-900">
                  {filteredPoints.length}
                </p>
                <p className="text-sm text-gray-600">Filtered Results</p>
              </div>
            </div>
          </div>
        </div>

        {/* Main Map Section */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-2 bg-white rounded-xl border border-gray-200 overflow-hidden">
            <div className="p-4 border-b border-gray-200 flex items-center justify-between">
              <h3 className="font-semibold text-gray-900">Report Distribution Map</h3>
              <span className="text-sm text-gray-500">{filteredPoints.length} points</span>
            </div>
            <div className="h-[500px] relative">
              {mapReady && typeof window !== 'undefined' && (
                <MapContainer
                  center={[15.3, 80.5]}
                  zoom={6}
                  style={{ height: '100%', width: '100%' }}
                  className="z-0"
                >
                  <TileLayer
                    attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
                    url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
                  />

                  {filteredPoints.map((point, idx) => (
                    <CircleMarker
                      key={point.report_id || idx}
                      center={[point.lat, point.lng]}
                      radius={getPointRadius(point)}
                      pathOptions={{
                        color: getPointColor(point),
                        fillColor: getPointColor(point),
                        fillOpacity: 0.6,
                        weight: 2
                      }}
                    >
                      <Popup>
                        <div className="p-2 min-w-[200px]">
                          <h4 className="font-semibold text-gray-900 mb-2">
                            {point.hazard_type?.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}
                          </h4>
                          <div className="space-y-1 text-sm">
                            <p><span className="text-gray-500">Location:</span> {point.location || 'Unknown'}</p>
                            <p><span className="text-gray-500">Severity:</span>
                              <span className={`ml-1 px-2 py-0.5 rounded-full text-xs ${
                                point.severity === 'critical' ? 'bg-red-100 text-red-700' :
                                point.severity === 'high' ? 'bg-orange-100 text-orange-700' :
                                point.severity === 'medium' ? 'bg-amber-100 text-amber-700' :
                                'bg-green-100 text-green-700'
                              }`}>
                                {point.severity}
                              </span>
                            </p>
                            <p><span className="text-gray-500">Status:</span> {point.status}</p>
                            <p><span className="text-gray-500">Date:</span> {new Date(point.created_at).toLocaleDateString()}</p>
                          </div>
                        </div>
                      </Popup>
                      <Tooltip>
                        {point.hazard_type?.replace(/_/g, ' ')} - {point.severity}
                      </Tooltip>
                    </CircleMarker>
                  ))}
                </MapContainer>
              )}

              {/* Legend overlay */}
              {showLegend && (
                <div className="absolute bottom-4 left-4 bg-white rounded-lg shadow-lg p-3 z-[1000]">
                  <h4 className="font-medium text-gray-900 text-sm mb-2">
                    {viewMode === 'markers' ? 'Hazard Types' : 'Severity'}
                  </h4>
                  <div className="space-y-1">
                    {viewMode === 'markers' ? (
                      Object.entries(hazardColors).map(([type, color]) => (
                        <div key={type} className="flex items-center gap-2 text-xs">
                          <div className="w-3 h-3 rounded-full" style={{ backgroundColor: color }} />
                          <span className="text-gray-600">
                            {type.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}
                          </span>
                        </div>
                      ))
                    ) : (
                      Object.entries(severityColors).map(([severity, color]) => (
                        <div key={severity} className="flex items-center gap-2 text-xs">
                          <div className="w-3 h-3 rounded-full" style={{ backgroundColor: color }} />
                          <span className="text-gray-600 capitalize">{severity}</span>
                        </div>
                      ))
                    )}
                  </div>
                </div>
              )}

              {loading && (
                <div className="absolute inset-0 bg-white/50 flex items-center justify-center z-[1000]">
                  <Loader2 className="w-8 h-8 text-blue-600 animate-spin" />
                </div>
              )}
            </div>
          </div>

          {/* Sidebar Stats */}
          <div className="space-y-6">
            {/* Severity Distribution */}
            <div className="bg-white rounded-xl border border-gray-200 p-5">
              <h3 className="font-semibold text-gray-900 mb-4">Severity Distribution</h3>
              {hotspotSeries.some(v => v > 0) ? (
                <Chart
                  options={hotspotChartOptions}
                  series={hotspotSeries}
                  type="donut"
                  height={220}
                />
              ) : (
                <div className="h-[220px] flex items-center justify-center text-gray-500">
                  No data available
                </div>
              )}
            </div>

            {/* Hotspot Areas */}
            <div className="bg-white rounded-xl border border-gray-200">
              <div className="p-4 border-b border-gray-200">
                <h3 className="font-semibold text-gray-900">Hotspot Areas</h3>
              </div>
              <div className="max-h-[250px] overflow-y-auto">
                {geoData?.hotspots?.length > 0 ? (
                  geoData.hotspots.slice(0, 10).map((hotspot, idx) => (
                    <div
                      key={idx}
                      className="p-3 border-b border-gray-100 hover:bg-gray-50 cursor-pointer"
                      onClick={() => setSelectedRegion(hotspot)}
                    >
                      <div className="flex items-center justify-between">
                        <div>
                          <p className="font-medium text-gray-900">{hotspot.name || hotspot.region}</p>
                          <p className="text-sm text-gray-500">{hotspot.report_count} reports</p>
                        </div>
                        <span className={`px-2 py-1 text-xs rounded-full ${
                          hotspot.severity_level === 'critical' ? 'bg-red-100 text-red-700' :
                          hotspot.severity_level === 'high' ? 'bg-orange-100 text-orange-700' :
                          'bg-amber-100 text-amber-700'
                        }`}>
                          {hotspot.severity_level || 'moderate'}
                        </span>
                      </div>
                    </div>
                  ))
                ) : (
                  <div className="p-8 text-center text-gray-500">
                    No hotspots identified
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>

        {/* Regional Stats Chart */}
        <div className="bg-white rounded-xl border border-gray-200 p-5">
          <h3 className="font-semibold text-gray-900 mb-4">Top Regions by Report Count</h3>
          {geoData?.regional_stats?.length > 0 ? (
            <Chart
              options={regionalChartOptions}
              series={[{ data: geoData.regional_stats.slice(0, 10).map(r => r.count) }]}
              type="bar"
              height={300}
            />
          ) : (
            <div className="h-[300px] flex items-center justify-center text-gray-500">
              No regional data available
            </div>
          )}
        </div>
      </div>
    </DashboardLayout>
  );
}

export default function GeoAnalysis() {
  return <GeoAnalysisContent />;
}
