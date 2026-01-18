'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import dynamic from 'next/dynamic';
import useAuthStore from '@/context/AuthContext';
import DashboardLayout from '@/components/DashboardLayout';
import {
  Activity,
  TrendingUp,
  TrendingDown,
  AlertTriangle,
  CheckCircle2,
  Clock,
  MapPin,
  FileText,
  Download,
  RefreshCw,
  BarChart3,
  PieChart,
  Map,
  Brain,
  Loader2,
  Globe,
  Radio,
  ChevronRight,
  Ticket,
  Waves
} from 'lucide-react';
import { motion } from 'framer-motion';
import toast from 'react-hot-toast';
import { getAnalystDashboard, getReportAnalytics, getTrendAnalytics } from '@/lib/api';
import { useAnalystStore, useAnalyticsDataStore } from '@/stores/analystStore';
import PageHeader from '@/components/PageHeader';

// Dynamic import for ApexCharts (client-side only)
const Chart = dynamic(() => import('react-apexcharts'), { ssr: false });

// Animation variants
const fadeInUp = {
  hidden: { opacity: 0, y: 20 },
  visible: { opacity: 1, y: 0, transition: { duration: 0.4 } }
};

const staggerContainer = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: { staggerChildren: 0.1 }
  }
};

const scaleIn = {
  hidden: { opacity: 0, scale: 0.9 },
  visible: { opacity: 1, scale: 1, transition: { duration: 0.3 } }
};

// Get greeting based on time of day
const getGreeting = () => {
  const hour = new Date().getHours();
  if (hour < 12) return 'Good Morning';
  if (hour < 17) return 'Good Afternoon';
  return 'Good Evening';
};

function AnalystDashboardContent() {
  const router = useRouter();
  const { user } = useAuthStore();
  const { defaultDateRange } = useAnalystStore();
  const { dashboardData, setDashboardData, dashboardLoading, setDashboardLoading } = useAnalyticsDataStore();

  const [trendData, setTrendData] = useState(null);
  const [hazardDistribution, setHazardDistribution] = useState(null);
  const [statusBreakdown, setStatusBreakdown] = useState(null);
  const [regionBreakdown, setRegionBreakdown] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [lastRefresh, setLastRefresh] = useState(null);

  // Check authorization
  useEffect(() => {
    if (user && !['analyst', 'authority_admin'].includes(user.role)) {
      router.push('/dashboard');
    }
  }, [user, router]);

  // Fetch dashboard data
  const fetchDashboardData = async () => {
    setIsLoading(true);
    setDashboardLoading(true);

    try {
      const [dashboardRes, analyticsRes, trendsRes] = await Promise.all([
        getAnalystDashboard(),
        getReportAnalytics({ date_range: defaultDateRange }),
        getTrendAnalytics({ date_range: '7days', group_by: 'day' })
      ]);

      if (dashboardRes.success) {
        setDashboardData(dashboardRes.data);
      }

      if (analyticsRes.success) {
        setHazardDistribution(analyticsRes.data.by_hazard_type);
        setStatusBreakdown(analyticsRes.data.by_status);
        setRegionBreakdown(analyticsRes.data.by_region);
      }

      if (trendsRes.success) {
        setTrendData(trendsRes.data.timeline);
      }

      setLastRefresh(new Date());
    } catch (error) {
      console.error('Error fetching dashboard data:', error);
      toast.error('Failed to load dashboard data');
    } finally {
      setIsLoading(false);
      setDashboardLoading(false);
    }
  };

  useEffect(() => {
    fetchDashboardData();
  }, [defaultDateRange]);

  // Stats cards data
  const stats = dashboardData ? [
    {
      name: 'Total Reports',
      value: dashboardData.total_reports?.toLocaleString() || '0',
      change: '+12%',
      changeType: 'increase',
      icon: FileText,
      color: 'from-[#0d4a6f] to-[#1a6b9a]',
      bgLight: 'bg-[#e8f4fc]'
    },
    {
      name: 'Pending Verification',
      value: dashboardData.pending_reports?.toLocaleString() || '0',
      change: `${dashboardData.pending_reports || 0} awaiting`,
      changeType: 'neutral',
      icon: Clock,
      color: 'from-amber-500 to-orange-500',
      bgLight: 'bg-amber-50'
    },
    {
      name: 'Verified Reports',
      value: dashboardData.verified_reports?.toLocaleString() || '0',
      change: `${dashboardData.verification_rate || 0}% rate`,
      changeType: 'increase',
      icon: CheckCircle2,
      color: 'from-emerald-500 to-green-600',
      bgLight: 'bg-emerald-50'
    },
    {
      name: 'Active Alerts',
      value: dashboardData.active_alerts?.toLocaleString() || '0',
      change: `${dashboardData.critical_alerts || 0} critical`,
      changeType: dashboardData?.critical_alerts > 0 ? 'warning' : 'neutral',
      icon: AlertTriangle,
      color: dashboardData?.critical_alerts > 0 ? 'from-red-500 to-red-600' : 'from-slate-400 to-slate-500',
      bgLight: dashboardData?.critical_alerts > 0 ? 'bg-red-50' : 'bg-slate-50'
    }
  ] : [];

  // Trend chart options
  const trendChartOptions = {
    chart: {
      type: 'area',
      toolbar: { show: false },
      fontFamily: 'inherit'
    },
    dataLabels: { enabled: false },
    stroke: { curve: 'smooth', width: 2 },
    fill: {
      type: 'gradient',
      gradient: {
        shadeIntensity: 1,
        opacityFrom: 0.4,
        opacityTo: 0.1
      }
    },
    xaxis: {
      categories: trendData?.map(d => d.date.split('-').slice(1).join('/')) || [],
      labels: { style: { fontSize: '11px' } }
    },
    yaxis: {
      labels: { style: { fontSize: '11px' } }
    },
    colors: ['#0d4a6f', '#10B981'],
    legend: { position: 'top' },
    tooltip: { shared: true }
  };

  const trendChartSeries = [
    {
      name: 'Total Reports',
      data: trendData?.map(d => d.total) || []
    },
    {
      name: 'Verified',
      data: trendData?.map(d => d.verified) || []
    }
  ];

  // Hazard distribution chart
  const hazardChartOptions = {
    chart: {
      type: 'donut',
      fontFamily: 'inherit'
    },
    labels: hazardDistribution ? Object.keys(hazardDistribution).map(h =>
      h.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())
    ) : [],
    colors: ['#0d4a6f', '#1a6b9a', '#4391c4', '#F59E0B', '#EF4444', '#8B5CF6', '#06B6D4'],
    legend: {
      position: 'bottom',
      fontSize: '12px'
    },
    dataLabels: {
      enabled: true,
      formatter: (val) => `${val.toFixed(1)}%`
    },
    plotOptions: {
      pie: {
        donut: {
          size: '60%',
          labels: {
            show: true,
            total: {
              show: true,
              label: 'Total',
              formatter: (w) => w.globals.seriesTotals.reduce((a, b) => a + b, 0)
            }
          }
        }
      }
    }
  };

  const hazardChartSeries = hazardDistribution ? Object.values(hazardDistribution) : [];

  const quickActions = [
    {
      id: 'smi',
      icon: Radio,
      title: 'Social Intelligence',
      description: 'Monitor feeds',
      color: 'from-[#0d4a6f] to-[#083a57]',
      onClick: () => router.push('/analyst/social-intelligence')
    },
    {
      id: 'map',
      icon: Map,
      title: 'Hazard Map',
      description: 'Live view',
      color: 'from-[#1a6b9a] to-[#0d4a6f]',
      onClick: () => router.push('/analyst/map')
    },
    {
      id: 'reports',
      icon: FileText,
      title: 'All Reports',
      description: 'View & filter',
      color: 'from-[#4391c4] to-[#1a6b9a]',
      onClick: () => router.push('/analyst/reports')
    },
    {
      id: 'tickets',
      icon: Ticket,
      title: 'Tickets',
      description: 'Manage tickets',
      color: 'from-[#1a6b9a] to-emerald-600',
      onClick: () => router.push('/analyst/tickets')
    }
  ];

  if (isLoading && !dashboardData) {
    return (
      <DashboardLayout>
        <div className="flex items-center justify-center min-h-[60vh]">
          <div className="text-center">
            <div className="w-16 h-16 rounded-full border-4 border-slate-100 border-t-[#0d4a6f] animate-spin mx-auto"></div>
            <p className="text-slate-500 mt-4">Loading analyst dashboard...</p>
          </div>
        </div>
      </DashboardLayout>
    );
  }

  return (
    <DashboardLayout>
      <div className="p-3 lg:p-6 w-full pb-24 lg:pb-6">
        {/* Mobile Greeting */}
        <div className="lg:hidden mb-4">
          <h1 className="text-2xl font-semibold text-slate-900">
            {getGreeting()}, <span className="text-[#0d4a6f]">{user?.name?.split(' ')[0] || 'Analyst'}</span>!
          </h1>
          <p className="text-slate-500 text-sm mt-1">Analyst Dashboard</p>
        </div>

        {/* Page Header - Desktop Only */}
        <PageHeader />

        {/* Two Column Layout */}
        <motion.div
          className="grid grid-cols-1 lg:grid-cols-3 gap-4 lg:items-start"
          initial="hidden"
          animate="visible"
          variants={staggerContainer}
        >
          {/* Left Column - Main Content */}
          <div className="lg:col-span-2 space-y-4 lg:max-h-[calc(100vh-6rem)] lg:overflow-y-auto lg:pr-2 scrollbar-hide">

            {/* Welcome Banner */}
            <motion.div
              variants={fadeInUp}
              className="bg-white rounded-2xl shadow-sm border border-slate-100 overflow-hidden"
            >
              <div className="bg-gradient-to-r from-[#0d4a6f] to-[#083a57] p-5 text-white relative overflow-hidden">
                {/* Decorative Wave Elements */}
                <div className="absolute bottom-0 left-0 right-0 opacity-10">
                  <svg viewBox="0 0 1440 120" className="w-full h-16">
                    <path fill="white" d="M0,32L48,37.3C96,43,192,53,288,58.7C384,64,480,64,576,58.7C672,53,768,43,864,48C960,53,1056,75,1152,80C1248,85,1344,75,1392,69.3L1440,64L1440,120L1392,120C1344,120,1248,120,1152,120C1056,120,960,120,864,120C768,120,672,120,576,120C480,120,384,120,288,120C192,120,96,120,48,120L0,120Z"></path>
                  </svg>
                </div>
                <div className="absolute top-2 right-4 opacity-20">
                  <Activity className="w-20 h-20" />
                </div>

                <div className="flex items-center justify-between relative z-10">
                  <div>
                    <h1 className="text-2xl font-bold mb-1">Analyst Dashboard</h1>
                    <p className="text-[#c5e1f5]">
                      Welcome back, {user?.name || 'Analyst'}
                    </p>
                  </div>
                  <button
                    onClick={fetchDashboardData}
                    disabled={isLoading}
                    className="flex items-center gap-2 px-4 py-2 bg-white/20 hover:bg-white/30 rounded-xl transition-colors backdrop-blur-sm"
                  >
                    <RefreshCw className={`w-4 h-4 ${isLoading ? 'animate-spin' : ''}`} />
                    <span className="text-sm font-medium">Refresh</span>
                  </button>
                </div>
              </div>

              {/* Stats Row */}
              <div className="grid grid-cols-4 divide-x divide-slate-100">
                {stats.map((stat, index) => (
                  <div key={index} className="p-4 text-center hover:bg-[#e8f4fc] transition cursor-pointer">
                    <stat.icon className={`w-5 h-5 mx-auto mb-1 ${
                      stat.changeType === 'warning' ? 'text-red-500' :
                      stat.changeType === 'increase' ? 'text-emerald-500' :
                      stat.name === 'Pending Verification' ? 'text-amber-500' : 'text-[#0d4a6f]'
                    }`} />
                    <div className="text-lg font-semibold text-slate-900">{stat.value}</div>
                    <div className="text-xs text-slate-500">{stat.name}</div>
                  </div>
                ))}
              </div>
            </motion.div>

            {/* HERO Action Button - Social Intelligence */}
            <motion.button
              variants={scaleIn}
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
              onClick={() => router.push('/analyst/social-intelligence')}
              className="w-full bg-gradient-to-r from-[#0d4a6f] to-[#1a6b9a] rounded-2xl p-6 flex items-center justify-between text-white shadow-xl hover:shadow-2xl transition-all"
            >
              <div className="flex items-center gap-4">
                <div className="w-14 h-14 bg-white/20 rounded-xl flex items-center justify-center backdrop-blur-sm">
                  <Radio className="w-7 h-7 text-white" />
                </div>
                <div className="text-left">
                  <h3 className="text-xl font-semibold">Social Intelligence</h3>
                  <p className="text-white/80 text-sm">Monitor social media for hazard alerts</p>
                </div>
              </div>
              <div className="w-12 h-12 bg-white/20 rounded-full flex items-center justify-center">
                <ChevronRight className="w-6 h-6 text-white" strokeWidth={3} />
              </div>
            </motion.button>

            {/* Quick Actions Grid */}
            <motion.div variants={fadeInUp} className="grid grid-cols-2 sm:grid-cols-4 gap-3">
              {quickActions.map((action) => {
                const Icon = action.icon;
                return (
                  <motion.button
                    key={action.id}
                    variants={scaleIn}
                    whileHover={{ scale: 1.03, y: -2 }}
                    whileTap={{ scale: 0.97 }}
                    onClick={action.onClick}
                    className="bg-white rounded-2xl shadow-sm border border-slate-100 hover:shadow-md hover:border-[#9ecbec] transition-all p-4 flex flex-col items-center justify-center text-center min-h-[100px]"
                  >
                    <div className={`w-12 h-12 bg-gradient-to-br ${action.color} rounded-xl flex items-center justify-center mb-3 shadow-sm`}>
                      <Icon className="w-6 h-6 text-white" strokeWidth={2} />
                    </div>
                    <h3 className="font-semibold text-slate-800 text-sm">{action.title}</h3>
                    <p className="text-xs text-slate-500 mt-1">{action.description}</p>
                  </motion.button>
                );
              })}
            </motion.div>

            {/* Trend Chart */}
            <motion.div variants={fadeInUp} className="bg-white rounded-2xl shadow-sm border border-slate-100 p-5">
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-2">
                  <TrendingUp className="w-5 h-5 text-[#0d4a6f]" />
                  <h3 className="text-lg font-semibold text-slate-900">Report Trends</h3>
                </div>
                <span className="text-xs text-slate-500 bg-[#e8f4fc] px-2 py-1 rounded-full">Last 7 Days</span>
              </div>
              {trendData && trendData.length > 0 ? (
                <Chart
                  options={trendChartOptions}
                  series={trendChartSeries}
                  type="area"
                  height={280}
                />
              ) : (
                <div className="h-[280px] flex items-center justify-center text-slate-500">
                  <div className="text-center">
                    <TrendingUp className="w-12 h-12 text-slate-300 mx-auto mb-2" />
                    <p>No trend data available</p>
                  </div>
                </div>
              )}
            </motion.div>

            {/* Hazard Distribution */}
            <motion.div variants={fadeInUp} className="bg-white rounded-2xl shadow-sm border border-slate-100 p-5">
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-2">
                  <PieChart className="w-5 h-5 text-[#0d4a6f]" />
                  <h3 className="text-lg font-semibold text-slate-900">Hazard Types</h3>
                </div>
              </div>
              {hazardChartSeries.length > 0 ? (
                <Chart
                  options={hazardChartOptions}
                  series={hazardChartSeries}
                  type="donut"
                  height={280}
                />
              ) : (
                <div className="h-[280px] flex items-center justify-center text-slate-500">
                  <div className="text-center">
                    <PieChart className="w-12 h-12 text-slate-300 mx-auto mb-2" />
                    <p>No hazard data available</p>
                  </div>
                </div>
              )}
            </motion.div>
          </div>

          {/* Right Column - Sidebar */}
          <motion.div
            variants={fadeInUp}
            className="hidden lg:block lg:col-span-1 lg:sticky lg:top-6 space-y-4 lg:max-h-[calc(100vh-3rem)] lg:overflow-y-auto scrollbar-hide"
          >
            {/* Status Breakdown */}
            <div className="bg-white rounded-2xl shadow-sm border border-slate-100 p-5">
              <div className="flex items-center gap-2 mb-4">
                <BarChart3 className="w-5 h-5 text-[#0d4a6f]" />
                <h3 className="text-base font-semibold text-slate-900">Status Breakdown</h3>
              </div>
              {statusBreakdown && Object.keys(statusBreakdown).length > 0 ? (
                <div className="space-y-3">
                  {Object.entries(statusBreakdown).map(([status, count]) => {
                    const total = Object.values(statusBreakdown).reduce((a, b) => a + b, 0);
                    const percentage = total > 0 ? ((count / total) * 100).toFixed(1) : 0;
                    const statusColors = {
                      verified: { bg: 'bg-emerald-500', light: 'bg-emerald-50', text: 'text-emerald-700' },
                      pending: { bg: 'bg-amber-500', light: 'bg-amber-50', text: 'text-amber-700' },
                      rejected: { bg: 'bg-red-500', light: 'bg-red-50', text: 'text-red-700' },
                      under_review: { bg: 'bg-[#0d4a6f]', light: 'bg-[#e8f4fc]', text: 'text-[#0d4a6f]' }
                    };
                    const colors = statusColors[status] || { bg: 'bg-slate-500', light: 'bg-slate-50', text: 'text-slate-700' };

                    return (
                      <div key={status}>
                        <div className="flex items-center justify-between mb-1">
                          <div className="flex items-center gap-2">
                            <span className={`w-3 h-3 rounded-full ${colors.bg}`}></span>
                            <span className="text-sm font-medium text-slate-700 capitalize">
                              {status.replace(/_/g, ' ')}
                            </span>
                          </div>
                          <div className="flex items-center gap-2">
                            <span className={`text-xs px-2 py-0.5 rounded-full ${colors.light} ${colors.text}`}>
                              {count}
                            </span>
                            <span className="text-sm text-slate-500">{percentage}%</span>
                          </div>
                        </div>
                        <div className="h-2 bg-slate-100 rounded-full overflow-hidden">
                          <div
                            className={`h-full ${colors.bg} transition-all duration-500`}
                            style={{ width: `${percentage}%` }}
                          ></div>
                        </div>
                      </div>
                    );
                  })}
                </div>
              ) : (
                <div className="h-[150px] flex items-center justify-center text-slate-500">
                  <p className="text-sm">No status data available</p>
                </div>
              )}
            </div>

            {/* Top Regions */}
            <div className="bg-white rounded-2xl shadow-sm border border-slate-100 p-5">
              <div className="flex items-center gap-2 mb-4">
                <Globe className="w-5 h-5 text-[#0d4a6f]" />
                <h3 className="text-base font-semibold text-slate-900">Top Regions</h3>
              </div>
              {regionBreakdown && Object.keys(regionBreakdown).length > 0 ? (
                <div className="space-y-3">
                  {Object.entries(regionBreakdown)
                    .sort((a, b) => b[1] - a[1])
                    .slice(0, 5)
                    .map(([region, count], index) => {
                      const maxCount = Math.max(...Object.values(regionBreakdown));
                      const percentage = maxCount > 0 ? ((count / maxCount) * 100) : 0;

                      return (
                        <div key={region}>
                          <div className="flex items-center justify-between mb-1">
                            <div className="flex items-center gap-2">
                              <span className="text-sm font-medium text-slate-500 w-4">{index + 1}.</span>
                              <MapPin className="w-4 h-4 text-slate-400" />
                              <span className="text-sm font-medium text-slate-700 truncate max-w-[120px]">
                                {region}
                              </span>
                            </div>
                            <span className="text-sm font-semibold text-slate-900">{count}</span>
                          </div>
                          <div className="h-2 bg-slate-100 rounded-full overflow-hidden ml-6">
                            <div
                              className="h-full bg-gradient-to-r from-[#0d4a6f] to-[#1a6b9a] transition-all duration-500"
                              style={{ width: `${percentage}%` }}
                            ></div>
                          </div>
                        </div>
                      );
                    })}
                </div>
              ) : (
                <div className="h-[150px] flex items-center justify-center text-slate-500">
                  <p className="text-sm">No region data available</p>
                </div>
              )}
            </div>

            {/* Real-time Monitoring CTA */}
            <div className="bg-gradient-to-br from-[#e8f4fc] to-emerald-50 rounded-2xl shadow-sm border border-[#c5e1f5] p-5">
              <div className="flex items-center space-x-2 mb-3">
                <Activity className="w-5 h-5 text-[#0d4a6f]" />
                <h3 className="text-base font-semibold text-slate-900">Live Monitoring</h3>
              </div>
              <p className="text-sm text-slate-600 mb-4">
                {dashboardData?.monitored_locations || 14} coastal locations being monitored in real-time
              </p>
              <button
                onClick={() => router.push('/analyst/realtime')}
                className="w-full py-3 px-4 bg-[#0d4a6f] hover:bg-[#083a57] text-white rounded-xl font-medium transition-all flex items-center justify-center gap-2"
              >
                <Activity className="w-4 h-4" />
                View Live Data
              </button>
            </div>

            {/* Quick Links */}
            <div className="bg-white rounded-2xl shadow-sm border border-slate-100 p-5">
              <h3 className="text-base font-semibold text-slate-900 mb-4">Quick Links</h3>
              <div className="space-y-2">
                <button
                  onClick={() => router.push('/analyst/notes')}
                  className="w-full p-3 bg-[#e8f4fc] hover:bg-[#d0e8f5] rounded-xl transition-colors flex items-center gap-3"
                >
                  <FileText className="w-5 h-5 text-[#0d4a6f]" />
                  <div className="text-left">
                    <p className="text-sm font-medium text-slate-900">My Notes</p>
                    <p className="text-xs text-slate-500">Personal annotations</p>
                  </div>
                </button>
                <button
                  onClick={() => router.push('/analyst/exports')}
                  className="w-full p-3 bg-purple-50 hover:bg-purple-100 rounded-xl transition-colors flex items-center gap-3"
                >
                  <Download className="w-5 h-5 text-purple-600" />
                  <div className="text-left">
                    <p className="text-sm font-medium text-slate-900">Export Center</p>
                    <p className="text-xs text-slate-500">Export & reports</p>
                  </div>
                </button>
              </div>
            </div>
          </motion.div>
        </motion.div>

        {/* Hide Scrollbar Styles */}
        <style jsx>{`
          .scrollbar-hide {
            -ms-overflow-style: none;
            scrollbar-width: none;
          }
          .scrollbar-hide::-webkit-scrollbar {
            display: none;
          }
        `}</style>
      </div>
    </DashboardLayout>
  );
}

export default function AnalystDashboard() {
  return <AnalystDashboardContent />;
}
