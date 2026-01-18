'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import DashboardLayout from '@/components/DashboardLayout';
import PageHeader from '@/components/PageHeader';
import useAuthStore from '@/context/AuthContext';
import api from '@/lib/api';
import {
  TrendingUp,
  TrendingDown,
  AlertTriangle,
  CheckCircle,
  Clock,
  MapPin,
  Users,
  BarChart3,
  Calendar,
  Filter,
  Download,
  RefreshCw,
  Eye,
  Activity
} from 'lucide-react';

export default function AnalyticsPage() {
  const router = useRouter();
  const { user, isLoading: authLoading } = useAuthStore();

  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [analytics, setAnalytics] = useState(null);

  // Filters
  const [dateRange, setDateRange] = useState('7days');
  const [selectedRegion, setSelectedRegion] = useState('all');

  useEffect(() => {
    if (!authLoading && user) {
      if (user.role !== 'authority' && user.role !== 'authority_admin') {
        router.push('/dashboard');
      } else {
        fetchAnalytics();
      }
    }
  }, [user, authLoading, dateRange, selectedRegion]);

  const fetchAnalytics = async () => {
    try {
      setLoading(true);
      const response = await api.get('/authority/analytics', {
        params: {
          date_range: dateRange,
          region: selectedRegion !== 'all' ? selectedRegion : undefined
        }
      });
      setAnalytics(response.data);
    } catch (error) {
      console.error('Error fetching analytics:', error);
      // Set empty analytics to prevent crashes
      setAnalytics({
        metrics: {
          total_reports: 0,
          total_change: 0,
          pending_reports: 0,
          pending_percentage: 0,
          verified_reports: 0,
          verified_percentage: 0,
          high_priority: 0,
          high_priority_percentage: 0
        },
        timeline: [],
        by_status: { pending: 0, verified: 0, rejected: 0 },
        by_hazard_type: {},
        by_region: {},
        regions: [],
        performance: {
          avg_response_time: '0h',
          verification_rate: 0,
          active_reporters: 0
        },
        recent_activity: []
      });
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  const handleRefresh = () => {
    setRefreshing(true);
    fetchAnalytics();
  };

  const exportData = () => {
    // TODO: Implement export functionality
    alert('Export feature coming soon!');
  };

  if (authLoading || loading || !user) {
    return (
      <DashboardLayout>
        <div className="flex items-center justify-center min-h-screen">
          <div className="text-center">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-[#0d4a6f] mx-auto mb-4"></div>
            <p className="text-gray-600">Loading analytics...</p>
          </div>
        </div>
      </DashboardLayout>
    );
  }

  if (!analytics) {
    return (
      <DashboardLayout>
        <div className="p-6">
          <p className="text-red-600">Failed to load analytics data</p>
        </div>
      </DashboardLayout>
    );
  }

  return (
    <DashboardLayout>
      <div className="p-6 space-y-6">
        {/* Page Header - Desktop Only */}
        <PageHeader />

        {/* Header */}
        <div className="bg-gradient-to-r from-[#0d4a6f] to-[#083a57] rounded-2xl shadow-lg p-6 text-white relative overflow-hidden">
          <div className="absolute bottom-0 left-0 right-0 opacity-10">
            <svg viewBox="0 0 1440 120" className="w-full h-12">
              <path fill="white" d="M0,32L48,37.3C96,43,192,53,288,58.7C384,64,480,64,576,58.7C672,53,768,43,864,48C960,53,1056,75,1152,80C1248,85,1344,75,1392,69.3L1440,64L1440,120L1392,120C1344,120,1248,120,1152,120C1056,120,960,120,864,120C768,120,672,120,576,120C480,120,384,120,288,120C192,120,96,120,48,120L0,120Z"></path>
            </svg>
          </div>
          <div className="flex items-center justify-between relative z-10">
            <div>
              <h1 className="text-2xl font-bold mb-2">Analytics Dashboard</h1>
              <p className="text-[#9ecbec]">
                Comprehensive insights and trends for hazard reports
              </p>
            </div>
            <Activity className="w-14 h-14 text-[#9ecbec] opacity-50" />
          </div>
        </div>

        {/* Filters and Actions */}
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-4">
          <div className="flex items-center justify-between flex-wrap gap-4">
            <div className="flex items-center gap-4 flex-wrap">
              {/* Date Range Filter */}
              <div className="flex items-center gap-2">
                <Calendar className="w-5 h-5 text-gray-400" />
                <select
                  value={dateRange}
                  onChange={(e) => setDateRange(e.target.value)}
                  className="px-4 py-2 border border-gray-300 rounded-xl focus:ring-2 focus:ring-[#1a6b9a] bg-white"
                >
                  <option value="7days">Last 7 Days</option>
                  <option value="30days">Last 30 Days</option>
                  <option value="90days">Last 90 Days</option>
                  <option value="year">This Year</option>
                  <option value="all">All Time</option>
                </select>
              </div>

              {/* Region Filter */}
              <div className="flex items-center gap-2">
                <Filter className="w-5 h-5 text-gray-400" />
                <select
                  value={selectedRegion}
                  onChange={(e) => setSelectedRegion(e.target.value)}
                  className="px-4 py-2 border border-gray-300 rounded-xl focus:ring-2 focus:ring-[#1a6b9a] bg-white"
                >
                  <option value="all">All Regions</option>
                  {analytics.regions?.map((region) => (
                    <option key={region} value={region}>{region}</option>
                  ))}
                </select>
              </div>
            </div>

            {/* Action Buttons */}
            <div className="flex items-center gap-2">
              <button
                onClick={handleRefresh}
                disabled={refreshing}
                className="flex items-center gap-2 px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors disabled:opacity-50"
              >
                <RefreshCw className={`w-4 h-4 ${refreshing ? 'animate-spin' : ''}`} />
                Refresh
              </button>
              <button
                onClick={exportData}
                className="flex items-center gap-2 px-4 py-2 bg-[#0d4a6f] text-white rounded-xl hover:bg-[#083a57] transition-colors"
              >
                <Download className="w-4 h-4" />
                Export
              </button>
            </div>
          </div>
        </div>

        {/* Key Metrics */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          {/* Total Reports */}
          <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
            <div className="flex items-center justify-between mb-4">
              <div className="p-3 bg-[#e8f4fc] rounded-xl">
                <BarChart3 className="w-6 h-6 text-[#0d4a6f]" />
              </div>
              {analytics.metrics?.total_change >= 0 ? (
                <div className="flex items-center gap-1 text-green-600 text-sm font-medium">
                  <TrendingUp className="w-4 h-4" />
                  {analytics.metrics?.total_change}%
                </div>
              ) : (
                <div className="flex items-center gap-1 text-red-600 text-sm font-medium">
                  <TrendingDown className="w-4 h-4" />
                  {Math.abs(analytics.metrics?.total_change)}%
                </div>
              )}
            </div>
            <h3 className="text-2xl font-bold text-gray-900">{analytics.metrics?.total_reports || 0}</h3>
            <p className="text-sm text-gray-600 mt-1">Total Reports</p>
          </div>

          {/* Pending Reports */}
          <div className="bg-white rounded-xl shadow-sm border border-orange-200 p-6">
            <div className="flex items-center justify-between mb-4">
              <div className="p-3 bg-orange-100 rounded-xl">
                <Clock className="w-6 h-6 text-orange-600" />
              </div>
              <div className="text-sm font-medium text-gray-600">
                {analytics.metrics?.pending_percentage || 0}%
              </div>
            </div>
            <h3 className="text-2xl font-bold text-orange-600">{analytics.metrics?.pending_reports || 0}</h3>
            <p className="text-sm text-gray-600 mt-1">Pending Verification</p>
          </div>

          {/* Verified Reports */}
          <div className="bg-white rounded-xl shadow-sm border border-green-200 p-6">
            <div className="flex items-center justify-between mb-4">
              <div className="p-3 bg-green-100 rounded-xl">
                <CheckCircle className="w-6 h-6 text-green-600" />
              </div>
              <div className="text-sm font-medium text-gray-600">
                {analytics.metrics?.verified_percentage || 0}%
              </div>
            </div>
            <h3 className="text-2xl font-bold text-green-600">{analytics.metrics?.verified_reports || 0}</h3>
            <p className="text-sm text-gray-600 mt-1">Verified Reports</p>
          </div>

          {/* High Priority */}
          <div className="bg-white rounded-xl shadow-sm border border-red-200 p-6">
            <div className="flex items-center justify-between mb-4">
              <div className="p-3 bg-red-100 rounded-xl">
                <AlertTriangle className="w-6 h-6 text-red-600" />
              </div>
              <div className="text-sm font-medium text-gray-600">
                {analytics.metrics?.high_priority_percentage || 0}%
              </div>
            </div>
            <h3 className="text-2xl font-bold text-red-600">{analytics.metrics?.high_priority || 0}</h3>
            <p className="text-sm text-gray-600 mt-1">High Priority</p>
          </div>
        </div>

        {/* Charts Row 1 */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Reports Over Time */}
          <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-4 md:p-6">
            <h2 className="text-base md:text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
              <TrendingUp className="w-4 h-4 md:w-5 md:h-5 text-[#0d4a6f]" />
              <span className="truncate">Reports Over Time</span>
            </h2>
            <div className="h-48 md:h-64">
              {analytics.timeline && analytics.timeline.length > 0 ? (
                <div className="flex items-end justify-between h-full gap-2">
                  {analytics.timeline.map((day, index) => {
                    const maxCount = Math.max(...analytics.timeline.map(d => d.count));
                    const height = maxCount > 0 ? (day.count / maxCount) * 100 : 0;

                    return (
                      <div key={index} className="flex-1 flex flex-col items-center gap-2 group">
                        <div className="relative w-full">
                          <div
                            className="w-full bg-[#1a6b9a] rounded-t hover:bg-[#0d4a6f] transition-all cursor-pointer"
                            style={{
                              height: `${height}%`,
                              minHeight: day.count > 0 ? '8px' : '2px'
                            }}
                            title={`${day.count} reports on ${new Date(day.date).toLocaleDateString()}`}
                          >
                            <div className="absolute -top-8 left-1/2 transform -translate-x-1/2 bg-gray-900 text-white text-xs px-2 py-1 rounded opacity-0 group-hover:opacity-100 transition-opacity whitespace-nowrap">
                              {day.count} reports
                            </div>
                          </div>
                        </div>
                        <span className="text-xs text-gray-600 transform -rotate-45 origin-top-left mt-2">
                          {new Date(day.date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}
                        </span>
                      </div>
                    );
                  })}
                </div>
              ) : (
                <div className="flex items-center justify-center h-full text-gray-500">
                  <p>No data available for this period</p>
                </div>
              )}
            </div>
          </div>

          {/* Reports by Status */}
          <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-4 md:p-6">
            <h2 className="text-base md:text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
              <BarChart3 className="w-4 h-4 md:w-5 md:h-5 text-[#0d4a6f]" />
              <span className="truncate">Reports by Status</span>
            </h2>
            <div className="space-y-4">
              {analytics.by_status && Object.entries(analytics.by_status).map(([status, count]) => {
                const total = analytics.metrics?.total_reports || 1;
                const percentage = ((count / total) * 100).toFixed(1);
                const colors = {
                  pending: { bg: 'bg-orange-500', text: 'text-orange-600' },
                  verified: { bg: 'bg-green-500', text: 'text-green-600' },
                  rejected: { bg: 'bg-red-500', text: 'text-red-600' }
                };
                const color = colors[status] || { bg: 'bg-gray-500', text: 'text-gray-600' };

                return (
                  <div key={status}>
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-sm font-medium text-gray-700 capitalize">{status}</span>
                      <span className="text-sm font-bold text-gray-900">{count} ({percentage}%)</span>
                    </div>
                    <div className="w-full bg-gray-200 rounded-full h-3">
                      <div
                        className={`${color.bg} h-3 rounded-full transition-all duration-500`}
                        style={{ width: `${percentage}%` }}
                      ></div>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </div>

        {/* Charts Row 2 */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Reports by Hazard Type */}
          <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-4 md:p-6">
            <h2 className="text-base md:text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
              <AlertTriangle className="w-4 h-4 md:w-5 md:h-5 text-[#0d4a6f]" />
              <span className="truncate">Hazard Types</span>
            </h2>
            <div className="space-y-3 max-h-80 overflow-y-auto">
              {analytics.by_hazard_type && Object.entries(analytics.by_hazard_type)
                .sort((a, b) => b[1] - a[1])
                .map(([type, count]) => {
                  const total = analytics.metrics?.total_reports || 1;
                  const percentage = ((count / total) * 100).toFixed(1);

                  return (
                    <div key={type} className="flex items-center gap-3">
                      <div className="flex-1">
                        <div className="flex items-center justify-between mb-1">
                          <span className="text-sm font-medium text-gray-700">{type}</span>
                          <span className="text-sm font-bold text-gray-900">{count}</span>
                        </div>
                        <div className="w-full bg-gray-200 rounded-full h-2">
                          <div
                            className="bg-gradient-to-r from-[#1a6b9a] to-[#0d4a6f] h-2 rounded-full transition-all duration-500"
                            style={{ width: `${percentage}%` }}
                          ></div>
                        </div>
                      </div>
                    </div>
                  );
                })}
            </div>
          </div>

          {/* Top Regions */}
          <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-4 md:p-6">
            <h2 className="text-base md:text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
              <MapPin className="w-4 h-4 md:w-5 md:h-5 text-[#0d4a6f]" />
              <span className="truncate">Top Regions</span>
            </h2>
            <div className="space-y-3 max-h-80 overflow-y-auto">
              {analytics.by_region && Object.entries(analytics.by_region)
                .filter(([region]) => region && region !== 'Unknown')
                .sort((a, b) => b[1] - a[1])
                .slice(0, 10)
                .map(([region, count], index) => (
                  <div key={region} className="flex items-center gap-2">
                    <div className="flex-shrink-0 w-7 h-7 rounded-full bg-[#e8f4fc] flex items-center justify-center">
                      <span className="text-xs font-bold text-[#0d4a6f]">#{index + 1}</span>
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center justify-between gap-2">
                        <span className="text-sm font-medium text-gray-700 truncate">{region}</span>
                        <span className="text-xs font-bold text-gray-900 flex-shrink-0">{count}</span>
                      </div>
                    </div>
                  </div>
                ))}
              {analytics.by_region && Object.keys(analytics.by_region).filter(r => r && r !== 'Unknown').length === 0 && (
                <p className="text-gray-500 text-center py-4 text-sm">No regional data available</p>
              )}
            </div>
          </div>
        </div>

        {/* Performance Metrics */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Average Response Time */}
          <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
            <div className="flex items-center gap-3 mb-4">
              <div className="p-3 bg-[#e8f4fc] rounded-xl">
                <Clock className="w-6 h-6 text-[#0d4a6f]" />
              </div>
              <div>
                <h3 className="text-sm font-medium text-gray-600">Avg Response Time</h3>
                <p className="text-2xl font-bold text-gray-900">
                  {analytics.performance?.avg_response_time || '0h'}
                </p>
              </div>
            </div>
            <p className="text-sm text-gray-500">Time to verify reports</p>
          </div>

          {/* Verification Rate */}
          <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
            <div className="flex items-center gap-3 mb-4">
              <div className="p-3 bg-green-100 rounded-xl">
                <CheckCircle className="w-6 h-6 text-green-600" />
              </div>
              <div>
                <h3 className="text-sm font-medium text-gray-600">Verification Rate</h3>
                <p className="text-2xl font-bold text-gray-900">
                  {analytics.performance?.verification_rate || 0}%
                </p>
              </div>
            </div>
            <p className="text-sm text-gray-500">Reports verified vs total</p>
          </div>

          {/* Active Reporters */}
          <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
            <div className="flex items-center gap-3 mb-4">
              <div className="p-3 bg-[#e8f4fc] rounded-xl">
                <Users className="w-6 h-6 text-[#0d4a6f]" />
              </div>
              <div>
                <h3 className="text-sm font-medium text-gray-600">Active Reporters</h3>
                <p className="text-2xl font-bold text-gray-900">
                  {analytics.performance?.active_reporters || 0}
                </p>
              </div>
            </div>
            <p className="text-sm text-gray-500">Unique contributors</p>
          </div>
        </div>

        {/* Recent Activity */}
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-4 md:p-6">
          <h2 className="text-base md:text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
            <Activity className="w-4 h-4 md:w-5 md:h-5 text-[#0d4a6f]" />
            <span className="truncate">Recent Activity</span>
          </h2>
          <div className="space-y-2 max-h-96 overflow-y-auto">
            {analytics.recent_activity && analytics.recent_activity.length > 0 ? (
              analytics.recent_activity.slice(0, 15).map((activity, index) => {
                const shortName = activity.verified_by ?
                  activity.verified_by.split(' ')[0] + (activity.verified_by.split(' ')[1] ? ' ' + activity.verified_by.split(' ')[1][0] + '.' : '')
                  : null;

                return (
                  <div key={index} className="flex items-center gap-2 p-2 hover:bg-gray-50 rounded-lg transition-colors">
                    <div className={`p-1.5 rounded-lg flex-shrink-0 ${
                      activity.type === 'verified' ? 'bg-green-100' :
                      activity.type === 'rejected' ? 'bg-red-100' :
                      'bg-orange-100'
                    }`}>
                      {activity.type === 'verified' ? (
                        <CheckCircle className="w-3.5 h-3.5 text-green-600" />
                      ) : activity.type === 'rejected' ? (
                        <AlertTriangle className="w-3.5 h-3.5 text-red-600" />
                      ) : (
                        <Clock className="w-3.5 h-3.5 text-orange-600" />
                      )}
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="text-xs text-gray-900 truncate">
                        <span className="font-medium">{activity.hazard_type}</span>
                        {' '}
                        <span className={
                          activity.type === 'verified' ? 'text-green-600' :
                          activity.type === 'rejected' ? 'text-red-600' :
                          'text-orange-600'
                        }>
                          {activity.type}
                        </span>
                        {shortName && <span className="text-gray-600"> by {shortName}</span>}
                      </p>
                      <p className="text-xs text-gray-500">
                        {new Date(activity.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                      </p>
                    </div>
                  </div>
                );
              })
            ) : (
              <p className="text-gray-500 text-center py-4 text-sm">No recent activity</p>
            )}
          </div>
        </div>
      </div>
    </DashboardLayout>
  );
}
