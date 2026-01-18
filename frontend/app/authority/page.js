'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import DashboardLayout from '@/components/DashboardLayout';
import useAuthStore from '@/context/AuthContext';
import api from '@/lib/api';
import {
  AlertTriangle,
  CheckCircle,
  Users,
  Bell,
  TrendingUp,
  Clock,
  Shield,
  FileText,
  Map,
  MessageCircle,
  Ticket,
  Plus,
  ChevronRight,
  Loader2,
  Waves,
  MapPin
} from 'lucide-react';
import { motion } from 'framer-motion';
import PageHeader from '@/components/PageHeader';

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

export default function AuthorityDashboard() {
  const router = useRouter();
  const { user, isLoading: authLoading } = useAuthStore();
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);

  // Check if user is authority or admin
  useEffect(() => {
    if (!authLoading && user) {
      if (user.role !== 'authority' && user.role !== 'authority_admin') {
        router.push('/dashboard');
      } else {
        fetchDashboardStats();
      }
    }
  }, [user, authLoading]);

  const fetchDashboardStats = async () => {
    try {
      setLoading(true);
      const response = await api.get('/authority/dashboard/stats');
      setStats(response.data);
    } catch (error) {
      console.error('Error fetching dashboard stats:', error);
    } finally {
      setLoading(false);
    }
  };

  if (authLoading || loading || !user) {
    return (
      <DashboardLayout>
        <div className="flex items-center justify-center min-h-screen">
          <div className="text-center">
            <div className="w-16 h-16 rounded-full border-4 border-slate-100 border-t-[#0d4a6f] animate-spin mx-auto"></div>
            <p className="text-slate-500 mt-4">Loading dashboard...</p>
          </div>
        </div>
      </DashboardLayout>
    );
  }

  if (!stats) {
    return (
      <DashboardLayout>
        <div className="flex items-center justify-center min-h-screen">
          <div className="text-center">
            <AlertTriangle className="w-12 h-12 text-amber-500 mx-auto mb-4" />
            <p className="text-gray-600">Failed to load dashboard data</p>
            <button
              onClick={fetchDashboardStats}
              className="mt-4 px-4 py-2 bg-[#0d4a6f] text-white rounded-xl hover:bg-[#083a57] transition"
            >
              Try Again
            </button>
          </div>
        </div>
      </DashboardLayout>
    );
  }

  const quickActions = [
    {
      id: 'verify',
      icon: FileText,
      title: 'Verify Reports',
      description: `${stats.reports.pending} pending`,
      color: 'from-[#0d4a6f] to-[#083a57]',
      onClick: () => router.push('/authority/reports')
    },
    {
      id: 'tickets',
      icon: Ticket,
      title: 'Tickets',
      description: 'Manage tickets',
      color: 'from-[#1a6b9a] to-[#0d4a6f]',
      onClick: () => router.push('/authority/tickets')
    },
    {
      id: 'alerts',
      icon: Bell,
      title: 'Alerts',
      description: `${stats.alerts.active} active`,
      color: 'from-[#4391c4] to-[#1a6b9a]',
      onClick: () => router.push('/authority/alerts')
    },
    {
      id: 'map',
      icon: Map,
      title: 'Hazard Map',
      description: 'Live view',
      color: 'from-[#1a6b9a] to-emerald-600',
      onClick: () => router.push('/authority/map')
    }
  ];

  return (
    <DashboardLayout>
      <div className="p-3 lg:p-6 w-full pb-24 lg:pb-6">
        {/* Mobile Greeting */}
        <div className="lg:hidden mb-4">
          <h1 className="text-2xl font-semibold text-slate-900">
            {getGreeting()}, <span className="text-[#0d4a6f]">{stats.user?.name?.split(' ')[0] || 'Officer'}</span>!
          </h1>
          <p className="text-slate-500 text-sm mt-1">Authority Dashboard</p>
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
                  <Shield className="w-20 h-20" />
                </div>

                <div className="relative z-10">
                  <h1 className="text-2xl font-bold mb-1">Authority Dashboard</h1>
                  <p className="text-[#c5e1f5]">
                    Welcome back, {stats.user?.name || 'Officer'}
                  </p>
                  <p className="text-sm text-[#9ecbec] mt-1">
                    {stats.user?.designation} • {stats.user?.organization}
                  </p>
                </div>
              </div>

              {/* Stats Row */}
              <div className="grid grid-cols-4 divide-x divide-slate-100">
                <div className="p-4 text-center cursor-pointer hover:bg-[#e8f4fc] transition" onClick={() => router.push('/authority/reports')}>
                  <Clock className="w-5 h-5 text-amber-500 mx-auto mb-1" />
                  <div className="text-lg font-semibold text-slate-900">{stats.reports.pending}</div>
                  <div className="text-xs text-slate-500">Pending</div>
                </div>
                <div className="p-4 text-center cursor-pointer hover:bg-[#e8f4fc] transition" onClick={() => router.push('/authority/reports?priority=high')}>
                  <AlertTriangle className="w-5 h-5 text-red-500 mx-auto mb-1" />
                  <div className="text-lg font-semibold text-slate-900">{stats.reports.high_priority}</div>
                  <div className="text-xs text-slate-500">High Priority</div>
                </div>
                <div className="p-4 text-center">
                  <CheckCircle className="w-5 h-5 text-emerald-500 mx-auto mb-1" />
                  <div className="text-lg font-semibold text-slate-900">{stats.reports.recently_verified}</div>
                  <div className="text-xs text-slate-500">Verified (7d)</div>
                </div>
                <div className="p-4 text-center cursor-pointer hover:bg-[#e8f4fc] transition" onClick={() => router.push('/authority/alerts')}>
                  <Bell className="w-5 h-5 text-[#0d4a6f] mx-auto mb-1" />
                  <div className="text-lg font-semibold text-slate-900">{stats.alerts.active}</div>
                  <div className="text-xs text-slate-500">Active Alerts</div>
                </div>
              </div>
            </motion.div>

            {/* HERO Action Button - Verify Reports */}
            <motion.button
              variants={scaleIn}
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
              onClick={() => router.push('/authority/reports')}
              className="w-full bg-gradient-to-r from-amber-500 to-orange-500 rounded-2xl p-6 flex items-center justify-between text-white shadow-xl hover:shadow-2xl transition-all"
            >
              <div className="flex items-center gap-4">
                <div className="w-14 h-14 bg-white/20 rounded-xl flex items-center justify-center backdrop-blur-sm">
                  <FileText className="w-7 h-7 text-white" />
                </div>
                <div className="text-left">
                  <h3 className="text-xl font-semibold">Verify Reports</h3>
                  <p className="text-white/80 text-sm">{stats.reports.pending} reports awaiting verification</p>
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

            {/* Activity Chart */}
            {stats.activity && stats.activity.length > 0 && (
              <motion.div variants={fadeInUp} className="bg-white rounded-2xl shadow-sm border border-slate-100 p-5">
                <div className="flex items-center gap-2 mb-4">
                  <TrendingUp className="w-5 h-5 text-[#0d4a6f]" />
                  <h2 className="text-lg font-semibold text-slate-900">Report Trends</h2>
                  <span className="text-xs text-slate-500 bg-[#e8f4fc] px-2 py-1 rounded-full ml-auto">Last 7 Days</span>
                </div>
                <div className="flex items-end justify-between gap-2 h-32">
                  {stats.activity.map((day, index) => {
                    const maxCount = Math.max(...stats.activity.map(d => d.count));
                    const heightPercent = maxCount > 0 ? (day.count / maxCount) * 100 : 0;
                    return (
                      <div key={index} className="flex-1 flex flex-col items-center gap-2">
                        <div
                          className="w-full bg-gradient-to-t from-[#0d4a6f] to-[#1a6b9a] rounded-t-lg hover:from-[#1a6b9a] hover:to-[#4391c4] transition-colors cursor-pointer"
                          style={{
                            height: `${heightPercent}%`,
                            minHeight: day.count > 0 ? '8px' : '2px'
                          }}
                          title={`${day.count} reports`}
                        />
                        <span className="text-xs text-slate-600">
                          {new Date(day.date).getDate()}
                        </span>
                      </div>
                    );
                  })}
                </div>
              </motion.div>
            )}

            {/* Verification Panel */}
            <motion.div variants={fadeInUp} className="bg-white rounded-2xl shadow-sm border border-slate-100 p-5">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-lg font-semibold text-slate-900 flex items-center gap-2">
                  <FileText className="w-5 h-5 text-[#0d4a6f]" />
                  Verification Queue
                </h2>
                <button
                  onClick={() => router.push('/authority/reports')}
                  className="text-sm text-[#0d4a6f] hover:text-[#083a57] font-medium flex items-center gap-1"
                >
                  View All <ChevronRight className="w-4 h-4" />
                </button>
              </div>
              <p className="text-sm text-slate-600 mb-4">
                Review and verify citizen-submitted hazard reports
              </p>
              <div className="space-y-3">
                <button
                  onClick={() => router.push('/authority/reports')}
                  className="w-full flex items-center justify-between p-4 bg-amber-50 hover:bg-amber-100 rounded-xl transition-colors border border-amber-100"
                >
                  <div className="flex items-center gap-3">
                    <Clock className="w-5 h-5 text-amber-600" />
                    <span className="text-sm font-medium text-slate-900">
                      {stats.reports.pending} reports pending verification
                    </span>
                  </div>
                  <ChevronRight className="w-5 h-5 text-amber-600" />
                </button>
                <button
                  onClick={() => router.push('/authority/reports?priority=high')}
                  className="w-full flex items-center justify-between p-4 bg-red-50 hover:bg-red-100 rounded-xl transition-colors border border-red-100"
                >
                  <div className="flex items-center gap-3">
                    <AlertTriangle className="w-5 h-5 text-red-600" />
                    <span className="text-sm font-medium text-slate-900">
                      {stats.reports.high_priority} high priority reports
                    </span>
                  </div>
                  <ChevronRight className="w-5 h-5 text-red-600" />
                </button>
              </div>
            </motion.div>
          </div>

          {/* Right Column - Sidebar */}
          <motion.div
            variants={fadeInUp}
            className="hidden lg:block lg:col-span-1 lg:sticky lg:top-6 space-y-4 lg:max-h-[calc(100vh-3rem)] lg:overflow-y-auto scrollbar-hide"
          >
            {/* Create Alert Card */}
            <div className="bg-white rounded-2xl shadow-sm border border-slate-100 p-5">
              <div className="flex items-center space-x-2 mb-4">
                <div className="w-10 h-10 bg-gradient-to-br from-[#0d4a6f] to-[#1a6b9a] rounded-xl flex items-center justify-center">
                  <Bell className="w-5 h-5 text-white" />
                </div>
                <h3 className="text-lg font-semibold text-slate-900">Alert Management</h3>
              </div>
              <p className="text-sm text-slate-600 mb-4">
                Create and manage hazard alerts for affected regions
              </p>
              <button
                onClick={() => router.push('/authority/alerts/create')}
                className="w-full py-3 px-4 bg-gradient-to-r from-[#0d4a6f] to-[#1a6b9a] hover:from-[#083a57] hover:to-[#0d4a6f] text-white rounded-xl font-medium shadow-sm transition-all flex items-center justify-center gap-2"
              >
                <Plus className="w-5 h-5" />
                Create New Alert
              </button>
              <button
                onClick={() => router.push('/authority/alerts')}
                className="w-full mt-3 py-3 px-4 bg-[#e8f4fc] hover:bg-[#d0e8f5] text-[#0d4a6f] rounded-xl font-medium transition-all"
              >
                View All Alerts ({stats.alerts.active} active)
              </button>
            </div>

            {/* Quick Links */}
            <div className="bg-white rounded-2xl shadow-sm border border-slate-100 p-5">
              <h3 className="text-base font-semibold text-slate-900 mb-4">Quick Links</h3>
              <div className="space-y-2">
                <button
                  onClick={() => router.push('/authority/map')}
                  className="w-full p-3 bg-[#e8f4fc] hover:bg-[#d0e8f5] rounded-xl transition-colors flex items-center gap-3"
                >
                  <Map className="w-5 h-5 text-[#0d4a6f]" />
                  <div className="text-left">
                    <p className="text-sm font-medium text-slate-900">Hazard Map</p>
                    <p className="text-xs text-slate-500">Monitor all regions</p>
                  </div>
                </button>
                <button
                  onClick={() => router.push('/community')}
                  className="w-full p-3 bg-emerald-50 hover:bg-emerald-100 rounded-xl transition-colors flex items-center gap-3"
                >
                  <MessageCircle className="w-5 h-5 text-emerald-600" />
                  <div className="text-left">
                    <p className="text-sm font-medium text-slate-900">Community Chat</p>
                    <p className="text-xs text-slate-500">Connect with citizens</p>
                  </div>
                </button>
                <button
                  onClick={() => router.push('/authority/analytics')}
                  className="w-full p-3 bg-purple-50 hover:bg-purple-100 rounded-xl transition-colors flex items-center gap-3"
                >
                  <TrendingUp className="w-5 h-5 text-purple-600" />
                  <div className="text-left">
                    <p className="text-sm font-medium text-slate-900">Analytics</p>
                    <p className="text-xs text-slate-500">View insights & trends</p>
                  </div>
                </button>
              </div>
            </div>

            {/* User Stats */}
            <div className="bg-gradient-to-br from-[#e8f4fc] to-emerald-50 rounded-2xl shadow-sm border border-[#c5e1f5] p-5">
              <div className="flex items-center space-x-2 mb-4">
                <Users className="w-5 h-5 text-[#0d4a6f]" />
                <h3 className="text-base font-semibold text-slate-900">Platform Stats</h3>
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div className="bg-white/70 rounded-xl p-3 text-center">
                  <p className="text-2xl font-bold text-[#0d4a6f]">{stats.users?.total || 0}</p>
                  <p className="text-xs text-slate-600">Total Users</p>
                </div>
                <div className="bg-white/70 rounded-xl p-3 text-center">
                  <p className="text-2xl font-bold text-emerald-600">{stats.reports?.recently_verified || 0}</p>
                  <p className="text-xs text-slate-600">Verified (7d)</p>
                </div>
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
