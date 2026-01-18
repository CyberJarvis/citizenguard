'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import dynamic from 'next/dynamic';
import useAuthStore from '@/context/AuthContext';
import DashboardLayout from '@/components/DashboardLayout';
import PageHeader from '@/components/PageHeader';
import { useAnalystStore } from '@/stores/analystStore';
import { getTrendAnalytics, getReportAnalytics } from '@/lib/api';
import {
  TrendingUp,
  TrendingDown,
  Calendar,
  Filter,
  Download,
  RefreshCw,
  BarChart3,
  ArrowLeft,
  ChevronDown,
  Loader2,
  Clock,
  Activity
} from 'lucide-react';
import toast from 'react-hot-toast';

// Dynamic import for ApexCharts
const Chart = dynamic(() => import('react-apexcharts'), { ssr: false });

const dateRangeOptions = [
  { value: '7days', label: 'Last 7 Days' },
  { value: '30days', label: 'Last 30 Days' },
  { value: '90days', label: 'Last 90 Days' },
  { value: '1year', label: 'Last Year' },
  { value: 'all', label: 'All Time' }
];

const groupByOptions = [
  { value: 'hour', label: 'By Hour' },
  { value: 'day', label: 'By Day' },
  { value: 'week', label: 'By Week' },
  { value: 'month', label: 'By Month' }
];

function TrendsAnalysisContent() {
  const router = useRouter();
  const { user } = useAuthStore();
  const { defaultDateRange } = useAnalystStore();

  const [dateRange, setDateRange] = useState(defaultDateRange);
  const [groupBy, setGroupBy] = useState('day');
  const [trendData, setTrendData] = useState(null);
  const [comparisonData, setComparisonData] = useState(null);
  const [hazardTrends, setHazardTrends] = useState(null);
  const [loading, setLoading] = useState(true);
  const [showFilters, setShowFilters] = useState(false);

  // Check authorization
  useEffect(() => {
    if (user && !['analyst', 'authority_admin'].includes(user.role)) {
      router.push('/dashboard');
    }
  }, [user, router]);

  // Fetch trend data
  const fetchTrendData = async () => {
    setLoading(true);
    try {
      const [trendsRes, analyticsRes] = await Promise.all([
        getTrendAnalytics({ date_range: dateRange, group_by: groupBy }),
        getReportAnalytics({ date_range: dateRange })
      ]);

      if (trendsRes.success) {
        setTrendData(trendsRes.data);
        setComparisonData(trendsRes.data.comparison);
      }

      if (analyticsRes.success) {
        setHazardTrends(analyticsRes.data.by_hazard_type);
      }
    } catch (error) {
      console.error('Error fetching trend data:', error);
      toast.error('Failed to load trend data');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchTrendData();
  }, [dateRange, groupBy]);

  // Main trend chart options
  const mainTrendOptions = {
    chart: {
      type: 'area',
      toolbar: { show: true, tools: { download: true, zoom: true, pan: true } },
      fontFamily: 'inherit',
      animations: { enabled: true, speed: 500 }
    },
    dataLabels: { enabled: false },
    stroke: { curve: 'smooth', width: 2 },
    fill: {
      type: 'gradient',
      gradient: { shadeIntensity: 1, opacityFrom: 0.4, opacityTo: 0.05 }
    },
    xaxis: {
      categories: trendData?.timeline?.map(d => {
        const date = new Date(d.date);
        if (groupBy === 'hour') return date.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' });
        if (groupBy === 'day') return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
        if (groupBy === 'week') return `Week ${date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}`;
        return date.toLocaleDateString('en-US', { month: 'short', year: '2-digit' });
      }) || [],
      labels: { style: { fontSize: '11px' }, rotate: -45, rotateAlways: groupBy !== 'month' }
    },
    yaxis: { labels: { style: { fontSize: '11px' } }, title: { text: 'Report Count' } },
    colors: ['#3B82F6', '#10B981', '#F59E0B'],
    legend: { position: 'top', horizontalAlign: 'right' },
    tooltip: { shared: true, intersect: false }
  };

  const mainTrendSeries = trendData?.timeline ? [
    { name: 'Total Reports', data: trendData.timeline.map(d => d.total || 0) },
    { name: 'Verified', data: trendData.timeline.map(d => d.verified || 0) },
    { name: 'Pending', data: trendData.timeline.map(d => d.pending || 0) }
  ] : [];

  // Verification rate trend
  const verificationTrendOptions = {
    chart: {
      type: 'line',
      toolbar: { show: false },
      fontFamily: 'inherit'
    },
    stroke: { curve: 'smooth', width: 3 },
    xaxis: {
      categories: trendData?.timeline?.map(d => {
        const date = new Date(d.date);
        return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
      }) || [],
      labels: { style: { fontSize: '10px' }, rotate: -45 }
    },
    yaxis: {
      labels: { style: { fontSize: '11px' }, formatter: (val) => `${val.toFixed(0)}%` },
      title: { text: 'Verification Rate' },
      min: 0,
      max: 100
    },
    colors: ['#10B981'],
    markers: { size: 4, hover: { size: 6 } }
  };

  const verificationRateSeries = trendData?.timeline ? [
    {
      name: 'Verification Rate',
      data: trendData.timeline.map(d => {
        const total = d.total || 0;
        const verified = d.verified || 0;
        return total > 0 ? ((verified / total) * 100).toFixed(1) : 0;
      })
    }
  ] : [];

  // Hazard type trends (stacked bar)
  const hazardTrendOptions = {
    chart: {
      type: 'bar',
      stacked: true,
      toolbar: { show: false },
      fontFamily: 'inherit'
    },
    plotOptions: {
      bar: { horizontal: false, borderRadius: 4, columnWidth: '70%' }
    },
    xaxis: {
      categories: Object.keys(hazardTrends || {}).map(h =>
        h.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())
      ),
      labels: { style: { fontSize: '10px' }, rotate: -45 }
    },
    yaxis: { labels: { style: { fontSize: '11px' } } },
    colors: ['#3B82F6', '#10B981', '#F59E0B', '#EF4444'],
    legend: { position: 'top' },
    dataLabels: { enabled: false }
  };

  // Summary metrics
  const summaryMetrics = trendData ? [
    {
      label: 'Total Reports',
      value: trendData.summary?.total_reports || 0,
      change: trendData.comparison?.total_change || 0,
      icon: BarChart3
    },
    {
      label: 'Avg Daily Reports',
      value: trendData.summary?.avg_daily || 0,
      change: trendData.comparison?.avg_change || 0,
      icon: Activity
    },
    {
      label: 'Peak Day',
      value: trendData.summary?.peak_count || 0,
      subtext: trendData.summary?.peak_date ? new Date(trendData.summary.peak_date).toLocaleDateString() : 'N/A',
      icon: TrendingUp
    },
    {
      label: 'Avg Response Time',
      value: `${trendData.summary?.avg_response_hours || 0}h`,
      change: trendData.comparison?.response_change || 0,
      icon: Clock
    }
  ] : [];

  if (loading && !trendData) {
    return (
      <DashboardLayout>
        <div className="flex items-center justify-center min-h-[60vh]">
          <div className="text-center">
            <Loader2 className="w-12 h-12 text-blue-600 animate-spin mx-auto mb-4" />
            <p className="text-gray-600">Loading trend analysis...</p>
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
              <h1 className="text-2xl font-bold text-gray-900">Trend Analysis</h1>
              <p className="text-gray-600 mt-1">Time-series patterns and insights</p>
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

            <select
              value={groupBy}
              onChange={(e) => setGroupBy(e.target.value)}
              className="px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 bg-white"
            >
              {groupByOptions.map(opt => (
                <option key={opt.value} value={opt.value}>{opt.label}</option>
              ))}
            </select>

            <button
              onClick={fetchTrendData}
              disabled={loading}
              className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
            >
              <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
              Refresh
            </button>
          </div>
        </div>

        {/* Summary Metrics */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          {summaryMetrics.map((metric, index) => (
            <div key={index} className="bg-white rounded-xl border border-gray-200 p-5">
              <div className="flex items-center justify-between">
                <div className="p-2 bg-blue-100 rounded-lg">
                  <metric.icon className="w-5 h-5 text-blue-600" />
                </div>
                {metric.change !== undefined && metric.change !== 0 && (
                  <span className={`flex items-center text-sm ${metric.change > 0 ? 'text-green-600' : 'text-red-600'}`}>
                    {metric.change > 0 ? <TrendingUp className="w-4 h-4 mr-1" /> : <TrendingDown className="w-4 h-4 mr-1" />}
                    {Math.abs(metric.change).toFixed(1)}%
                  </span>
                )}
              </div>
              <div className="mt-3">
                <p className="text-2xl font-bold text-gray-900">
                  {typeof metric.value === 'number' ? metric.value.toLocaleString() : metric.value}
                </p>
                <p className="text-sm text-gray-600">{metric.label}</p>
                {metric.subtext && <p className="text-xs text-gray-500 mt-1">{metric.subtext}</p>}
              </div>
            </div>
          ))}
        </div>

        {/* Main Trend Chart */}
        <div className="bg-white rounded-xl border border-gray-200 p-5">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-semibold text-gray-900">Report Volume Trend</h3>
            <div className="flex items-center gap-2">
              <button
                onClick={() => router.push('/analyst/exports')}
                className="flex items-center gap-1 px-3 py-1.5 text-sm text-gray-600 border border-gray-200 rounded-lg hover:bg-gray-50"
              >
                <Download className="w-4 h-4" />
                Export
              </button>
            </div>
          </div>
          {mainTrendSeries.length > 0 && mainTrendSeries[0].data.length > 0 ? (
            <Chart
              options={mainTrendOptions}
              series={mainTrendSeries}
              type="area"
              height={400}
            />
          ) : (
            <div className="h-[400px] flex items-center justify-center text-gray-500">
              No trend data available for the selected period
            </div>
          )}
        </div>

        {/* Secondary Charts */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Verification Rate Trend */}
          <div className="bg-white rounded-xl border border-gray-200 p-5">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">Verification Rate Over Time</h3>
            {verificationRateSeries.length > 0 && verificationRateSeries[0].data.length > 0 ? (
              <Chart
                options={verificationTrendOptions}
                series={verificationRateSeries}
                type="line"
                height={300}
              />
            ) : (
              <div className="h-[300px] flex items-center justify-center text-gray-500">
                No verification data available
              </div>
            )}
          </div>

          {/* Hazard Type Distribution */}
          <div className="bg-white rounded-xl border border-gray-200 p-5">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">Hazard Type Distribution</h3>
            {hazardTrends && Object.keys(hazardTrends).length > 0 ? (
              <Chart
                options={hazardTrendOptions}
                series={[{ name: 'Reports', data: Object.values(hazardTrends) }]}
                type="bar"
                height={300}
              />
            ) : (
              <div className="h-[300px] flex items-center justify-center text-gray-500">
                No hazard data available
              </div>
            )}
          </div>
        </div>

        {/* Period Comparison */}
        {comparisonData && (
          <div className="bg-white rounded-xl border border-gray-200 p-5">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">Period Comparison</h3>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-6">
              <div className="text-center p-4 bg-gray-50 rounded-lg">
                <p className="text-sm text-gray-600 mb-1">Current Period</p>
                <p className="text-3xl font-bold text-gray-900">
                  {comparisonData.current_period?.total?.toLocaleString() || 0}
                </p>
                <p className="text-sm text-gray-500">reports</p>
              </div>
              <div className="text-center p-4 bg-gray-50 rounded-lg">
                <p className="text-sm text-gray-600 mb-1">Previous Period</p>
                <p className="text-3xl font-bold text-gray-900">
                  {comparisonData.previous_period?.total?.toLocaleString() || 0}
                </p>
                <p className="text-sm text-gray-500">reports</p>
              </div>
              <div className="text-center p-4 bg-gray-50 rounded-lg">
                <p className="text-sm text-gray-600 mb-1">Change</p>
                <p className={`text-3xl font-bold ${comparisonData.percentage_change >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                  {comparisonData.percentage_change >= 0 ? '+' : ''}{comparisonData.percentage_change?.toFixed(1) || 0}%
                </p>
                <p className="text-sm text-gray-500">
                  {comparisonData.percentage_change >= 0 ? 'increase' : 'decrease'}
                </p>
              </div>
            </div>
          </div>
        )}

        {/* Insights */}
        {trendData?.insights && trendData.insights.length > 0 && (
          <div className="bg-gradient-to-r from-blue-50 to-indigo-50 rounded-xl border border-blue-200 p-5">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">Key Insights</h3>
            <ul className="space-y-2">
              {trendData.insights.map((insight, idx) => (
                <li key={idx} className="flex items-start gap-2 text-gray-700">
                  <TrendingUp className="w-5 h-5 text-blue-600 mt-0.5 flex-shrink-0" />
                  <span>{insight}</span>
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>
    </DashboardLayout>
  );
}

export default function TrendsAnalysis() {
  return <TrendsAnalysisContent />;
}
