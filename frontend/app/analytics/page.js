'use client';

import ProtectedRoute from '@/components/ProtectedRoute';
import DashboardLayout from '@/components/DashboardLayout';
import { BarChart3, TrendingUp, TrendingDown, Activity, Calendar, MapPin, AlertTriangle, Users, Eye, CheckCircle } from 'lucide-react';

function AnalyticsContent() {
  const keyMetrics = [
    {
      name: 'Total Reports',
      value: '1,234',
      change: '+12.5%',
      trend: 'up',
      icon: AlertTriangle,
      color: 'from-blue-500 to-cyan-500',
    },
    {
      name: 'Active Users',
      value: '856',
      change: '+8.2%',
      trend: 'up',
      icon: Users,
      color: 'from-green-500 to-emerald-500',
    },
    {
      name: 'Verification Rate',
      value: '78%',
      change: '-2.1%',
      trend: 'down',
      icon: CheckCircle,
      color: 'from-purple-500 to-pink-500',
    },
    {
      name: 'Avg Response Time',
      value: '2.4h',
      change: '-15.3%',
      trend: 'up',
      icon: Activity,
      color: 'from-orange-500 to-red-500',
    },
  ];

  const topHazardTypes = [
    { type: 'Rip Current', count: 342, percentage: 28 },
    { type: 'Jellyfish', count: 289, percentage: 23 },
    { type: 'Sharp Objects', count: 198, percentage: 16 },
    { type: 'Pollution', count: 167, percentage: 14 },
    { type: 'Other', count: 238, percentage: 19 },
  ];

  const topLocations = [
    { location: 'Juhu Beach', reports: 145 },
    { location: 'Marine Drive', reports: 98 },
    { location: 'Versova Beach', reports: 87 },
    { location: 'Aksa Beach', reports: 62 },
    { location: 'Girgaum Chowpatty', reports: 51 },
  ];

  return (
    <div className="p-4 lg:p-8">
      <div className="max-w-7xl mx-auto">
        {/* Page Header */}
        <div className="mb-8 flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold text-gray-900 mb-2">Analytics Dashboard</h1>
            <p className="text-gray-600">Insights and trends from hazard reports</p>
          </div>
          <div className="flex items-center space-x-3">
            <button className="px-4 py-2 bg-white border border-gray-300 rounded-xl text-sm font-medium text-gray-700 hover:bg-gray-50 flex items-center space-x-2">
              <Calendar className="w-4 h-4" />
              <span>Last 30 days</span>
            </button>
            <button className="px-4 py-2 bg-gradient-to-r from-blue-600 to-blue-700 text-white rounded-xl font-semibold hover:from-blue-700 hover:to-blue-800 transition-all shadow-lg shadow-blue-200">
              Export Report
            </button>
          </div>
        </div>

        {/* Key Metrics */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
          {keyMetrics.map((metric) => {
            const Icon = metric.icon;
            const TrendIcon = metric.trend === 'up' ? TrendingUp : TrendingDown;
            const trendColor = metric.trend === 'up' ? 'text-green-600' : 'text-red-600';

            return (
              <div key={metric.name} className="bg-white rounded-2xl shadow-sm border border-gray-200 p-6">
                <div className="flex items-center justify-between mb-4">
                  <div className={`w-12 h-12 bg-gradient-to-br ${metric.color} rounded-xl flex items-center justify-center`}>
                    <Icon className="w-6 h-6 text-white" />
                  </div>
                  <div className={`flex items-center space-x-1 ${trendColor}`}>
                    <TrendIcon className="w-4 h-4" />
                    <span className="text-sm font-semibold">{metric.change}</span>
                  </div>
                </div>
                <p className="text-sm text-gray-600 mb-1">{metric.name}</p>
                <p className="text-3xl font-bold text-gray-900">{metric.value}</p>
              </div>
            );
          })}
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
          {/* Reports Trend Chart Placeholder */}
          <div className="bg-white rounded-2xl shadow-sm border border-gray-200 p-6">
            <h3 className="text-lg font-bold text-gray-900 mb-4 flex items-center">
              <BarChart3 className="w-5 h-5 mr-2 text-blue-600" />
              Reports Over Time
            </h3>
            <div className="h-64 flex items-center justify-center bg-gradient-to-br from-blue-50 to-cyan-50 rounded-xl">
              <div className="text-center">
                <Activity className="w-12 h-12 text-blue-600 mx-auto mb-3" />
                <p className="text-gray-600 font-medium">Chart Visualization Coming Soon</p>
                <p className="text-sm text-gray-500">Time-series analysis of hazard reports</p>
              </div>
            </div>
          </div>

          {/* Top Hazard Types */}
          <div className="bg-white rounded-2xl shadow-sm border border-gray-200 p-6">
            <h3 className="text-lg font-bold text-gray-900 mb-4 flex items-center">
              <AlertTriangle className="w-5 h-5 mr-2 text-orange-600" />
              Top Hazard Types
            </h3>
            <div className="space-y-4">
              {topHazardTypes.map((hazard, index) => (
                <div key={hazard.type}>
                  <div className="flex items-center justify-between mb-2">
                    <div className="flex items-center space-x-3">
                      <span className="text-sm font-semibold text-gray-900">{index + 1}</span>
                      <span className="text-sm text-gray-700">{hazard.type}</span>
                    </div>
                    <span className="text-sm font-semibold text-gray-900">{hazard.count}</span>
                  </div>
                  <div className="w-full bg-gray-200 rounded-full h-2">
                    <div
                      className="bg-gradient-to-r from-orange-500 to-red-500 h-2 rounded-full"
                      style={{ width: `${hazard.percentage}%` }}
                    ></div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Top Locations */}
          <div className="bg-white rounded-2xl shadow-sm border border-gray-200 p-6">
            <h3 className="text-lg font-bold text-gray-900 mb-4 flex items-center">
              <MapPin className="w-5 h-5 mr-2 text-green-600" />
              Top Locations
            </h3>
            <div className="space-y-3">
              {topLocations.map((location, index) => (
                <div key={location.location} className="flex items-center justify-between p-3 bg-gray-50 rounded-xl hover:bg-gray-100 transition-colors">
                  <div className="flex items-center space-x-3">
                    <div className="w-8 h-8 bg-gradient-to-br from-green-500 to-emerald-500 rounded-lg flex items-center justify-center">
                      <span className="text-white text-sm font-bold">{index + 1}</span>
                    </div>
                    <span className="text-sm font-medium text-gray-900">{location.location}</span>
                  </div>
                  <span className="text-sm font-semibold text-gray-700">{location.reports} reports</span>
                </div>
              ))}
            </div>
          </div>

          {/* User Engagement */}
          <div className="bg-white rounded-2xl shadow-sm border border-gray-200 p-6">
            <h3 className="text-lg font-bold text-gray-900 mb-4 flex items-center">
              <Eye className="w-5 h-5 mr-2 text-purple-600" />
              User Engagement
            </h3>
            <div className="space-y-4">
              <div className="p-4 bg-gradient-to-r from-purple-50 to-pink-50 rounded-xl">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm text-gray-700">Daily Active Users</span>
                  <span className="text-lg font-bold text-gray-900">342</span>
                </div>
                <div className="w-full bg-purple-200 rounded-full h-2">
                  <div className="bg-gradient-to-r from-purple-500 to-pink-500 h-2 rounded-full" style={{ width: '68%' }}></div>
                </div>
              </div>

              <div className="p-4 bg-gradient-to-r from-blue-50 to-cyan-50 rounded-xl">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm text-gray-700">Reports per User</span>
                  <span className="text-lg font-bold text-gray-900">1.4</span>
                </div>
                <div className="w-full bg-blue-200 rounded-full h-2">
                  <div className="bg-gradient-to-r from-blue-500 to-cyan-500 h-2 rounded-full" style={{ width: '42%' }}></div>
                </div>
              </div>

              <div className="p-4 bg-gradient-to-r from-green-50 to-emerald-50 rounded-xl">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm text-gray-700">Avg. Session Duration</span>
                  <span className="text-lg font-bold text-gray-900">5m 32s</span>
                </div>
                <div className="w-full bg-green-200 rounded-full h-2">
                  <div className="bg-gradient-to-r from-green-500 to-emerald-500 h-2 rounded-full" style={{ width: '55%' }}></div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default function AnalyticsPage() {
  return (
    <ProtectedRoute>
      <DashboardLayout>
        <AnalyticsContent />
      </DashboardLayout>
    </ProtectedRoute>
  );
}
