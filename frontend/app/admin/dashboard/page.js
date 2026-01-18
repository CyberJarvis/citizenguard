'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import DashboardLayout from '@/components/DashboardLayout';
import useAuthStore from '@/context/AuthContext';
import api from '@/lib/api';
import toast from 'react-hot-toast';
import { motion } from 'framer-motion';
import {
  Users,
  FileText,
  AlertTriangle,
  Activity,
  Shield,
  TrendingUp,
  Clock,
  CheckCircle2,
  XCircle,
  Server,
  Database,
  Zap,
  RefreshCw,
  ChevronRight,
  Settings,
  UserCog,
  ClipboardList,
  Trash2
} from 'lucide-react';
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

export default function AdminDashboardPage() {
  const router = useRouter();
  const { user, isLoading: authLoading } = useAuthStore();
  const [dashboardData, setDashboardData] = useState(null);
  const [systemHealth, setSystemHealth] = useState(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  useEffect(() => {
    if (!authLoading && user) {
      if (user.role !== 'authority_admin') {
        toast.error('Access denied. Admin privileges required.');
        router.push('/dashboard');
      } else {
        fetchDashboardData();
      }
    }
  }, [user, authLoading, router]);

  const fetchDashboardData = async () => {
    try {
      setLoading(true);
      const [dashboardRes, healthRes] = await Promise.all([
        api.get('/admin/dashboard'),
        api.get('/admin/monitoring/health')
      ]);

      setDashboardData(dashboardRes.data.data);
      setSystemHealth(healthRes.data.data);
    } catch (error) {
      console.error('Error fetching dashboard:', error);
      toast.error('Failed to load dashboard data');
    } finally {
      setLoading(false);
    }
  };

  const handleRefresh = async () => {
    setRefreshing(true);
    await fetchDashboardData();
    setRefreshing(false);
    toast.success('Dashboard refreshed');
  };

  const getHealthStatusColor = (status) => {
    switch (status) {
      case 'healthy': return { bg: 'bg-emerald-500', light: 'bg-emerald-50', text: 'text-emerald-700' };
      case 'warning': return { bg: 'bg-amber-500', light: 'bg-amber-50', text: 'text-amber-700' };
      case 'critical': return { bg: 'bg-red-500', light: 'bg-red-50', text: 'text-red-700' };
      default: return { bg: 'bg-slate-500', light: 'bg-slate-50', text: 'text-slate-700' };
    }
  };

  if (authLoading || loading || !user) {
    return (
      <DashboardLayout>
        <div className="flex items-center justify-center min-h-screen">
          <div className="text-center">
            <div className="w-16 h-16 rounded-full border-4 border-slate-100 border-t-[#0d4a6f] animate-spin mx-auto"></div>
            <p className="text-slate-500 mt-4">Loading admin dashboard...</p>
          </div>
        </div>
      </DashboardLayout>
    );
  }

  const stats = dashboardData || {
    users: { total: 0, active: 0, banned: 0, new_today: 0, new_this_week: 0, by_role: {} },
    reports: { total: 0, pending: 0, verified: 0, today: 0, verification_rate: 0 },
    alerts: { total: 0, active: 0, critical: 0 },
    system: { logins_24h: 0, errors_24h: 0, unresolved_errors: 0, admin_actions_week: 0 }
  };

  const quickActions = [
    {
      id: 'users',
      icon: Users,
      title: 'Manage Users',
      description: `${stats.users.total} users`,
      color: 'from-[#0d4a6f] to-[#083a57]',
      onClick: () => router.push('/admin/users')
    },
    {
      id: 'content',
      icon: Trash2,
      title: 'Content Management',
      description: 'Manage all content',
      color: 'from-red-500 to-red-600',
      onClick: () => router.push('/admin/content')
    },
    {
      id: 'reports',
      icon: ClipboardList,
      title: 'Content Moderation',
      description: `${stats.reports.pending} pending`,
      color: 'from-[#1a6b9a] to-[#0d4a6f]',
      onClick: () => router.push('/admin/reports')
    },
    {
      id: 'monitoring',
      icon: Server,
      title: 'System Health',
      description: 'Monitor status',
      color: 'from-emerald-500 to-emerald-600',
      onClick: () => router.push('/admin/monitoring')
    },
    {
      id: 'audit',
      icon: Database,
      title: 'Audit Logs',
      description: 'Activity history',
      color: 'from-[#4391c4] to-[#1a6b9a]',
      onClick: () => router.push('/admin/audit-logs')
    }
  ];

  return (
    <DashboardLayout>
      <div className="p-3 lg:p-6 w-full pb-24 lg:pb-6">
        {/* Mobile Greeting */}
        <div className="lg:hidden mb-4">
          <h1 className="text-2xl font-semibold text-slate-900">
            {getGreeting()}, <span className="text-[#0d4a6f]">{user?.name?.split(' ')[0] || 'Admin'}</span>!
          </h1>
          <p className="text-slate-500 text-sm mt-1">System Administration</p>
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

                <div className="flex items-center justify-between relative z-10">
                  <div>
                    <h1 className="text-2xl font-bold mb-1 flex items-center gap-3">
                      <Shield className="w-7 h-7" />
                      Admin Dashboard
                    </h1>
                    <p className="text-[#c5e1f5]">
                      System overview and management console
                    </p>
                  </div>
                  <button
                    onClick={handleRefresh}
                    disabled={refreshing}
                    className="flex items-center gap-2 px-4 py-2 bg-white/20 hover:bg-white/30 rounded-xl transition-colors backdrop-blur-sm"
                  >
                    <RefreshCw className={`w-4 h-4 ${refreshing ? 'animate-spin' : ''}`} />
                    <span className="text-sm font-medium">Refresh</span>
                  </button>
                </div>
              </div>

              {/* Stats Row */}
              <div className="grid grid-cols-4 divide-x divide-slate-100">
                <div className="p-4 text-center cursor-pointer hover:bg-[#e8f4fc] transition" onClick={() => router.push('/admin/users')}>
                  <Users className="w-5 h-5 text-[#0d4a6f] mx-auto mb-1" />
                  <div className="text-lg font-semibold text-slate-900">{stats.users.total}</div>
                  <div className="text-xs text-slate-500">Total Users</div>
                </div>
                <div className="p-4 text-center cursor-pointer hover:bg-[#e8f4fc] transition" onClick={() => router.push('/admin/reports')}>
                  <Clock className="w-5 h-5 text-amber-500 mx-auto mb-1" />
                  <div className="text-lg font-semibold text-slate-900">{stats.reports.pending}</div>
                  <div className="text-xs text-slate-500">Pending</div>
                </div>
                <div className="p-4 text-center">
                  <AlertTriangle className="w-5 h-5 text-red-500 mx-auto mb-1" />
                  <div className="text-lg font-semibold text-slate-900">{stats.alerts.active}</div>
                  <div className="text-xs text-slate-500">Active Alerts</div>
                </div>
                <div className="p-4 text-center">
                  <Activity className="w-5 h-5 text-emerald-500 mx-auto mb-1" />
                  <div className="text-lg font-semibold text-slate-900">{stats.system.logins_24h}</div>
                  <div className="text-xs text-slate-500">Logins (24h)</div>
                </div>
              </div>
            </motion.div>

            {/* HERO Action Button - User Management */}
            <motion.button
              variants={scaleIn}
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
              onClick={() => router.push('/admin/users')}
              className="w-full bg-gradient-to-r from-[#0d4a6f] to-[#1a6b9a] rounded-2xl p-6 flex items-center justify-between text-white shadow-xl hover:shadow-2xl transition-all"
            >
              <div className="flex items-center gap-4">
                <div className="w-14 h-14 bg-white/20 rounded-xl flex items-center justify-center backdrop-blur-sm">
                  <UserCog className="w-7 h-7 text-white" />
                </div>
                <div className="text-left">
                  <h3 className="text-xl font-semibold">User Management</h3>
                  <p className="text-white/80 text-sm">{stats.users.total} users • {stats.users.new_this_week} new this week</p>
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

            {/* Users by Role */}
            <motion.div variants={fadeInUp} className="bg-white rounded-2xl shadow-sm border border-slate-100 p-5">
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-2">
                  <Users className="w-5 h-5 text-[#0d4a6f]" />
                  <h2 className="text-lg font-semibold text-slate-900">Users by Role</h2>
                </div>
                <button
                  onClick={() => router.push('/admin/users')}
                  className="text-sm text-[#0d4a6f] hover:text-[#083a57] font-medium flex items-center gap-1"
                >
                  View All <ChevronRight className="w-4 h-4" />
                </button>
              </div>
              <div className="space-y-3">
                {Object.entries(stats.users.by_role || {}).map(([role, count]) => {
                  const total = stats.users.total || 1;
                  const percentage = ((count / total) * 100).toFixed(1);
                  const roleColors = {
                    authority_admin: { bg: 'bg-[#0d4a6f]', light: 'bg-[#e8f4fc]', text: 'text-[#0d4a6f]' },
                    authority: { bg: 'bg-[#1a6b9a]', light: 'bg-[#e8f4fc]', text: 'text-[#1a6b9a]' },
                    analyst: { bg: 'bg-emerald-500', light: 'bg-emerald-50', text: 'text-emerald-700' },
                    verified_organizer: { bg: 'bg-purple-500', light: 'bg-purple-50', text: 'text-purple-700' },
                    citizen: { bg: 'bg-slate-500', light: 'bg-slate-50', text: 'text-slate-700' }
                  };
                  const colors = roleColors[role] || roleColors.citizen;

                  return (
                    <div key={role}>
                      <div className="flex items-center justify-between mb-1">
                        <span className={`px-3 py-1 rounded-full text-xs font-medium ${colors.light} ${colors.text}`}>
                          {role.replace(/_/g, ' ').toUpperCase()}
                        </span>
                        <div className="flex items-center gap-2">
                          <span className="text-lg font-semibold text-slate-900">{count}</span>
                          <span className="text-sm text-slate-500">({percentage}%)</span>
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
                {Object.keys(stats.users.by_role || {}).length === 0 && (
                  <p className="text-slate-500 text-center py-4">No user data available</p>
                )}
              </div>
              <div className="mt-4 pt-4 border-t border-slate-100 flex justify-between text-sm">
                <span className="text-emerald-600 font-medium">Active: {stats.users.active}</span>
                <span className="text-red-600 font-medium">Banned: {stats.users.banned}</span>
              </div>
            </motion.div>

            {/* Quick Stats Row */}
            <motion.div variants={fadeInUp} className="grid grid-cols-2 sm:grid-cols-4 gap-3">
              <div className="bg-white rounded-2xl shadow-sm border border-slate-100 p-4">
                <div className="flex items-center gap-3">
                  <div className="p-2 bg-emerald-50 rounded-xl">
                    <CheckCircle2 className="w-5 h-5 text-emerald-600" />
                  </div>
                  <div>
                    <p className="text-xs text-slate-500">Verified Reports</p>
                    <p className="text-lg font-bold text-slate-900">{stats.reports.verified}</p>
                  </div>
                </div>
              </div>
              <div className="bg-white rounded-2xl shadow-sm border border-slate-100 p-4">
                <div className="flex items-center gap-3">
                  <div className="p-2 bg-[#e8f4fc] rounded-xl">
                    <Clock className="w-5 h-5 text-[#0d4a6f]" />
                  </div>
                  <div>
                    <p className="text-xs text-slate-500">Reports Today</p>
                    <p className="text-lg font-bold text-slate-900">{stats.reports.today}</p>
                  </div>
                </div>
              </div>
              <div className="bg-white rounded-2xl shadow-sm border border-slate-100 p-4">
                <div className="flex items-center gap-3">
                  <div className="p-2 bg-amber-50 rounded-xl">
                    <XCircle className="w-5 h-5 text-amber-600" />
                  </div>
                  <div>
                    <p className="text-xs text-slate-500">Errors (24h)</p>
                    <p className="text-lg font-bold text-slate-900">{stats.system.errors_24h}</p>
                  </div>
                </div>
              </div>
              <div className="bg-white rounded-2xl shadow-sm border border-slate-100 p-4">
                <div className="flex items-center gap-3">
                  <div className="p-2 bg-[#e8f4fc] rounded-xl">
                    <TrendingUp className="w-5 h-5 text-[#0d4a6f]" />
                  </div>
                  <div>
                    <p className="text-xs text-slate-500">New Users Today</p>
                    <p className="text-lg font-bold text-slate-900">{stats.users.new_today}</p>
                  </div>
                </div>
              </div>
            </motion.div>
          </div>

          {/* Right Column - Sidebar */}
          <motion.div
            variants={fadeInUp}
            className="hidden lg:block lg:col-span-1 lg:sticky lg:top-6 space-y-4 lg:max-h-[calc(100vh-3rem)] lg:overflow-y-auto scrollbar-hide"
          >
            {/* System Health */}
            <div className="bg-white rounded-2xl shadow-sm border border-slate-100 p-5">
              <div className="flex items-center gap-2 mb-4">
                <Server className="w-5 h-5 text-[#0d4a6f]" />
                <h2 className="text-base font-semibold text-slate-900">System Health</h2>
              </div>
              <div className="space-y-3">
                {systemHealth?.components && Object.entries(systemHealth.components).map(([name, data]) => {
                  const colors = getHealthStatusColor(data.status);
                  return (
                    <div key={name} className="flex items-center justify-between p-3 bg-slate-50 rounded-xl">
                      <div className="flex items-center gap-3">
                        {name === 'database' && <Database className="w-5 h-5 text-slate-600" />}
                        {name === 'api' && <Zap className="w-5 h-5 text-slate-600" />}
                        {name === 'storage' && <Server className="w-5 h-5 text-slate-600" />}
                        <span className="font-medium text-slate-700 capitalize">{name}</span>
                      </div>
                      <span className={`px-3 py-1 rounded-full text-xs font-medium ${colors.light} ${colors.text}`}>
                        {data.status || 'Unknown'}
                      </span>
                    </div>
                  );
                })}
                {!systemHealth?.components && (
                  <p className="text-slate-500 text-center py-4">Health data not available</p>
                )}
              </div>
              {systemHealth?.overall_status && (
                <div className="mt-4 pt-4 border-t border-slate-100">
                  <div className="flex items-center justify-between">
                    <span className="text-slate-600 font-medium">Overall Status</span>
                    <span className={`px-3 py-1 rounded-full text-xs font-medium ${getHealthStatusColor(systemHealth.overall_status).light} ${getHealthStatusColor(systemHealth.overall_status).text}`}>
                      {systemHealth.overall_status.toUpperCase()}
                    </span>
                  </div>
                </div>
              )}
              <button
                onClick={() => router.push('/admin/monitoring')}
                className="w-full mt-4 py-3 px-4 bg-[#e8f4fc] hover:bg-[#d0e8f5] text-[#0d4a6f] rounded-xl font-medium transition-all"
              >
                View Detailed Health
              </button>
            </div>

            {/* Quick Links */}
            <div className="bg-white rounded-2xl shadow-sm border border-slate-100 p-5">
              <h3 className="text-base font-semibold text-slate-900 mb-4">Quick Links</h3>
              <div className="space-y-2">
                <button
                  onClick={() => router.push('/admin/organizer-applications')}
                  className="w-full p-3 bg-purple-50 hover:bg-purple-100 rounded-xl transition-colors flex items-center gap-3"
                >
                  <UserCog className="w-5 h-5 text-purple-600" />
                  <div className="text-left">
                    <p className="text-sm font-medium text-slate-900">Organizer Applications</p>
                    <p className="text-xs text-slate-500">Review pending requests</p>
                  </div>
                </button>
                <button
                  onClick={() => router.push('/admin/settings')}
                  className="w-full p-3 bg-[#e8f4fc] hover:bg-[#d0e8f5] rounded-xl transition-colors flex items-center gap-3"
                >
                  <Settings className="w-5 h-5 text-[#0d4a6f]" />
                  <div className="text-left">
                    <p className="text-sm font-medium text-slate-900">System Settings</p>
                    <p className="text-xs text-slate-500">Configure system</p>
                  </div>
                </button>
              </div>
            </div>

            {/* Admin Activity */}
            <div className="bg-gradient-to-br from-[#e8f4fc] to-emerald-50 rounded-2xl shadow-sm border border-[#c5e1f5] p-5">
              <div className="flex items-center space-x-2 mb-3">
                <Activity className="w-5 h-5 text-[#0d4a6f]" />
                <h3 className="text-base font-semibold text-slate-900">Admin Activity</h3>
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div className="bg-white/70 rounded-xl p-3 text-center">
                  <p className="text-2xl font-bold text-[#0d4a6f]">{stats.system.admin_actions_week}</p>
                  <p className="text-xs text-slate-600">Actions (7d)</p>
                </div>
                <div className="bg-white/70 rounded-xl p-3 text-center">
                  <p className="text-2xl font-bold text-emerald-600">{stats.reports.verification_rate}%</p>
                  <p className="text-xs text-slate-600">Verify Rate</p>
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
