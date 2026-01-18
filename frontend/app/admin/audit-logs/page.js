'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import DashboardLayout from '@/components/DashboardLayout';
import PageHeader from '@/components/PageHeader';
import useAuthStore from '@/context/AuthContext';
import api from '@/lib/api';
import { formatDateTimeIST } from '@/lib/dateUtils';
import toast from 'react-hot-toast';
// import { ExportButton } from '@/components/export';
import {
  ClipboardList,
  Shield,
  RefreshCw,
  Download,
  Search,
  Filter,
  ChevronLeft,
  ChevronRight,
  Eye,
  X,
  User,
  Clock,
  Activity,
  FileText,
  Settings,
  UserPlus,
  UserMinus,
  Edit,
  Trash2,
  Lock,
  Unlock,
  Calendar
} from 'lucide-react';

export default function AdminAuditLogsPage() {
  const router = useRouter();
  const { user, isLoading: authLoading } = useAuthStore();

  // Tab state
  const [activeTab, setActiveTab] = useState('all');

  // All logs state
  const [logs, setLogs] = useState([]);
  const [logsLoading, setLogsLoading] = useState(false);
  const [logsTotalPages, setLogsTotalPages] = useState(1);
  const [logsPage, setLogsPage] = useState(1);
  const [totalLogs, setTotalLogs] = useState(0);

  // Admin activity logs state
  const [adminLogs, setAdminLogs] = useState([]);
  const [adminLogsLoading, setAdminLogsLoading] = useState(false);
  const [adminLogsTotalPages, setAdminLogsTotalPages] = useState(1);
  const [adminLogsPage, setAdminLogsPage] = useState(1);

  // Filters
  const [actionFilter, setActionFilter] = useState('all');
  const [searchQuery, setSearchQuery] = useState('');
  const [dateRange, setDateRange] = useState('7days');

  // Stats
  const [stats, setStats] = useState(null);
  const [statsLoading, setStatsLoading] = useState(true);

  // Modal
  const [selectedLog, setSelectedLog] = useState(null);

  // Export state
  const [exporting, setExporting] = useState(false);

  const actionTypes = [
    { value: 'all', label: 'All Actions' },
    { value: 'user_created', label: 'User Created' },
    { value: 'user_updated', label: 'User Updated' },
    { value: 'user_deleted', label: 'User Deleted' },
    { value: 'user_banned', label: 'User Banned' },
    { value: 'user_unbanned', label: 'User Unbanned' },
    { value: 'role_changed', label: 'Role Changed' },
    { value: 'setting_updated', label: 'Setting Updated' },
    { value: 'content_deleted', label: 'Content Deleted' },
    { value: 'login', label: 'Login' },
    { value: 'logout', label: 'Logout' }
  ];

  useEffect(() => {
    if (!authLoading && user) {
      if (user.role !== 'authority_admin') {
        toast.error('Access denied. Admin privileges required.');
        router.push('/dashboard');
      } else {
        fetchStats();
        fetchData();
      }
    }
  }, [user, authLoading, router, activeTab]);

  const fetchData = () => {
    if (activeTab === 'all') {
      fetchLogs();
    } else if (activeTab === 'admin') {
      fetchAdminLogs();
    }
  };

  const fetchStats = async () => {
    try {
      setStatsLoading(true);
      const response = await api.get('/admin/audit-logs/stats');
      setStats(response.data.data);
    } catch (error) {
      console.error('Error fetching audit stats:', error);
    } finally {
      setStatsLoading(false);
    }
  };

  const fetchLogs = async () => {
    try {
      setLogsLoading(true);
      const params = new URLSearchParams({
        page: logsPage.toString(),
        limit: '20',
        date_range: dateRange
      });
      if (actionFilter !== 'all') {
        params.append('action', actionFilter);
      }
      if (searchQuery) {
        params.append('search', searchQuery);
      }

      const response = await api.get(`/admin/audit-logs?${params}`);
      // Backend returns { success: true, data: { logs: [], pagination: {} } }
      const responseData = response.data?.data || response.data || {};
      const logsData = responseData.logs || responseData || [];
      setLogs(Array.isArray(logsData) ? logsData : []);
      setLogsTotalPages(responseData.pagination?.total_pages || 1);
      setTotalLogs(responseData.pagination?.total_count || 0);
    } catch (error) {
      console.error('Error fetching logs:', error);
      toast.error('Failed to load audit logs');
      setLogs([]);
    } finally {
      setLogsLoading(false);
    }
  };

  const fetchAdminLogs = async () => {
    try {
      setAdminLogsLoading(true);
      const params = new URLSearchParams({
        page: adminLogsPage.toString(),
        limit: '20'
      });

      const response = await api.get(`/admin/audit-logs/admin-activity?${params}`);
      // Backend returns { success: true, data: { logs: [], pagination: {} } }
      const responseData = response.data?.data || response.data || {};
      const logsData = responseData.logs || responseData || [];
      setAdminLogs(Array.isArray(logsData) ? logsData : []);
      setAdminLogsTotalPages(responseData.pagination?.total_pages || 1);
    } catch (error) {
      console.error('Error fetching admin logs:', error);
      toast.error('Failed to load admin activity logs');
      setAdminLogs([]);
    } finally {
      setAdminLogsLoading(false);
    }
  };

  useEffect(() => {
    if (!authLoading && user?.role === 'authority_admin' && activeTab === 'all') {
      fetchLogs();
    }
  }, [logsPage, actionFilter, dateRange]);

  useEffect(() => {
    if (!authLoading && user?.role === 'authority_admin' && activeTab === 'admin') {
      fetchAdminLogs();
    }
  }, [adminLogsPage]);

  const handleSearch = () => {
    setLogsPage(1);
    fetchLogs();
  };

  const handleExport = async () => {
    try {
      setExporting(true);
      const params = new URLSearchParams({
        format: 'csv',
        date_range: dateRange
      });
      if (actionFilter !== 'all') {
        params.append('action', actionFilter);
      }

      const response = await api.get(`/admin/audit-logs/export?${params}`, {
        responseType: 'blob'
      });

      // Create download link
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `audit-logs-${new Date().toISOString().split('T')[0]}.csv`);
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);

      toast.success('Export downloaded successfully');
    } catch (error) {
      toast.error('Failed to export audit logs');
    } finally {
      setExporting(false);
    }
  };

  const getActionIcon = (action) => {
    const icons = {
      user_created: <UserPlus className="w-4 h-4 text-green-600" />,
      user_updated: <Edit className="w-4 h-4 text-blue-600" />,
      user_deleted: <UserMinus className="w-4 h-4 text-red-600" />,
      user_banned: <Lock className="w-4 h-4 text-red-600" />,
      user_unbanned: <Unlock className="w-4 h-4 text-green-600" />,
      role_changed: <Shield className="w-4 h-4 text-sky-600" />,
      setting_updated: <Settings className="w-4 h-4 text-amber-600" />,
      content_deleted: <Trash2 className="w-4 h-4 text-red-600" />,
      login: <User className="w-4 h-4 text-blue-600" />,
      logout: <User className="w-4 h-4 text-gray-600" />
    };
    return icons[action] || <Activity className="w-4 h-4 text-gray-600" />;
  };

  const getActionBadgeColor = (action) => {
    const colors = {
      user_created: 'bg-green-100 text-green-700',
      user_updated: 'bg-blue-100 text-blue-700',
      user_deleted: 'bg-red-100 text-red-700',
      user_banned: 'bg-red-100 text-red-700',
      user_unbanned: 'bg-green-100 text-green-700',
      role_changed: 'bg-sky-100 text-sky-700',
      setting_updated: 'bg-amber-100 text-amber-700',
      content_deleted: 'bg-red-100 text-red-700',
      login: 'bg-blue-100 text-blue-700',
      logout: 'bg-gray-100 text-gray-700'
    };
    return colors[action] || 'bg-gray-100 text-gray-700';
  };

  const formatDate = (dateString) => {
    if (!dateString) return 'N/A';
    return formatDateTimeIST(dateString);
  };

  if (authLoading || !user) {
    return (
      <DashboardLayout>
        <div className="flex items-center justify-center min-h-screen">
          <div className="text-center">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-[#0d4a6f] mx-auto mb-4"></div>
            <p className="text-gray-600">Loading...</p>
          </div>
        </div>
      </DashboardLayout>
    );
  }

  return (
    <DashboardLayout>
      <div className="p-6 space-y-6">
        {/* Page Header */}
        <PageHeader />

        {/* Header */}
        <div className="bg-gradient-to-r from-[#0d4a6f] to-[#083a57] rounded-2xl shadow-lg p-6 text-white relative overflow-hidden">
          <div className="absolute bottom-0 left-0 right-0 opacity-10">
            <svg viewBox="0 0 1440 120" className="w-full h-12">
              <path fill="white" d="M0,32L48,37.3C96,43,192,53,288,58.7C384,64,480,64,576,58.7C672,53,768,43,864,42.7C960,43,1056,53,1152,58.7C1248,64,1344,64,1392,64L1440,64L1440,120L1392,120C1344,120,1248,120,1152,120C1056,120,960,120,864,120C768,120,672,120,576,120C480,120,384,120,288,120C192,120,96,120,48,120L0,120Z"></path>
            </svg>
          </div>
          <div className="relative z-10 flex items-center justify-between">
            <div>
              <h1 className="text-2xl font-bold flex items-center gap-3">
                <div className="p-2 bg-white/20 rounded-xl backdrop-blur-sm">
                  <ClipboardList className="w-6 h-6" />
                </div>
                Audit Logs
              </h1>
              <p className="text-[#9ecbec] mt-1">
                Track all system activities and admin actions
              </p>
            </div>
            <div className="flex items-center gap-2">
              <button
                onClick={handleExport}
                disabled={exporting}
                className="flex items-center gap-2 px-4 py-2 bg-white/10 border border-white/20 hover:bg-white/20 rounded-xl transition-colors"
              >
                <Download className={`w-4 h-4 ${exporting ? 'animate-pulse' : ''}`} />
                Export CSV
              </button>
              <button
                onClick={fetchData}
                className="flex items-center gap-2 px-4 py-2 bg-white/10 border border-white/20 hover:bg-white/20 rounded-xl transition-colors"
              >
                <RefreshCw className="w-4 h-4" />
                Refresh
              </button>
            </div>
          </div>
        </div>

        {/* Stats Cards */}
        {!statsLoading && stats && (
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-blue-100 rounded-lg">
                  <Activity className="w-5 h-5 text-blue-600" />
                </div>
                <div>
                  <p className="text-sm text-gray-500">Total Events</p>
                  <p className="text-xl font-bold text-gray-900">{stats.total_events || 0}</p>
                </div>
              </div>
            </div>
            <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-green-100 rounded-lg">
                  <User className="w-5 h-5 text-green-600" />
                </div>
                <div>
                  <p className="text-sm text-gray-500">Logins Today</p>
                  <p className="text-xl font-bold text-gray-900">{stats.logins_today || 0}</p>
                </div>
              </div>
            </div>
            <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-sky-100 rounded-lg">
                  <Shield className="w-5 h-5 text-sky-600" />
                </div>
                <div>
                  <p className="text-sm text-gray-500">Admin Actions</p>
                  <p className="text-xl font-bold text-gray-900">{stats.admin_actions || 0}</p>
                </div>
              </div>
            </div>
            <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-red-100 rounded-lg">
                  <Lock className="w-5 h-5 text-red-600" />
                </div>
                <div>
                  <p className="text-sm text-gray-500">Security Events</p>
                  <p className="text-xl font-bold text-gray-900">{stats.security_events || 0}</p>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Tabs and Content */}
        <div className="bg-white rounded-xl shadow-sm border border-gray-200">
          {/* Tabs */}
          <div className="border-b border-gray-200">
            <nav className="flex -mb-px">
              <button
                onClick={() => setActiveTab('all')}
                className={`px-6 py-4 text-sm font-medium border-b-2 transition-colors flex items-center gap-2 ${activeTab === 'all'
                    ? 'border-sky-500 text-sky-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                  }`}
              >
                <FileText className="w-4 h-4" />
                All Logs
              </button>
              <button
                onClick={() => setActiveTab('admin')}
                className={`px-6 py-4 text-sm font-medium border-b-2 transition-colors flex items-center gap-2 ${activeTab === 'admin'
                    ? 'border-sky-500 text-sky-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                  }`}
              >
                <Shield className="w-4 h-4" />
                Admin Activity
              </button>
            </nav>
          </div>

          <div className="p-6">
            {/* All Logs Tab */}
            {activeTab === 'all' && (
              <div className="space-y-4">
                {/* Filters */}
                <div className="flex flex-wrap items-center gap-4">
                  <div className="flex items-center gap-2 flex-1 min-w-[200px]">
                    <Search className="w-4 h-4 text-gray-400" />
                    <input
                      type="text"
                      value={searchQuery}
                      onChange={(e) => setSearchQuery(e.target.value)}
                      onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
                      placeholder="Search by user or action..."
                      className="flex-1 border border-gray-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-sky-500 focus:border-sky-500"
                    />
                  </div>
                  <div className="flex items-center gap-2">
                    <Filter className="w-4 h-4 text-gray-500" />
                    <select
                      value={actionFilter}
                      onChange={(e) => {
                        setActionFilter(e.target.value);
                        setLogsPage(1);
                      }}
                      className="border border-gray-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-sky-500 focus:border-sky-500"
                    >
                      {actionTypes.map(action => (
                        <option key={action.value} value={action.value}>{action.label}</option>
                      ))}
                    </select>
                  </div>
                  <div className="flex items-center gap-2">
                    <Calendar className="w-4 h-4 text-gray-500" />
                    <select
                      value={dateRange}
                      onChange={(e) => {
                        setDateRange(e.target.value);
                        setLogsPage(1);
                      }}
                      className="border border-gray-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-sky-500 focus:border-sky-500"
                    >
                      <option value="24hours">Last 24 Hours</option>
                      <option value="7days">Last 7 Days</option>
                      <option value="30days">Last 30 Days</option>
                      <option value="90days">Last 90 Days</option>
                    </select>
                  </div>

                  {/* Export Button */}
                  {/* <ExportButton
                    dataType="audit_logs"
                    currentFilters={{ action: actionFilter, date_range: dateRange }}
                    size="md"
                  /> */}
                </div>

                {/* Logs Table */}
                {logsLoading ? (
                  <div className="text-center py-12">
                    <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-sky-500 mx-auto"></div>
                  </div>
                ) : logs.length === 0 ? (
                  <div className="text-center py-12 text-gray-500">
                    <ClipboardList className="w-12 h-12 mx-auto mb-4 opacity-50" />
                    <p>No audit logs found</p>
                  </div>
                ) : (
                  <div className="overflow-x-auto">
                    <table className="w-full">
                      <thead className="bg-gray-50">
                        <tr>
                          <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Timestamp</th>
                          <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Action</th>
                          <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">User</th>
                          <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Details</th>
                          <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">IP Address</th>
                          <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Actions</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-gray-200">
                        {logs.map((log, idx) => (
                          <tr key={log.log_id || `log-${idx}`} className="hover:bg-gray-50">
                            <td className="px-4 py-3 text-sm text-gray-500">
                              <div className="flex items-center gap-1">
                                <Clock className="w-3 h-3" />
                                {formatDate(log.timestamp)}
                              </div>
                            </td>
                            <td className="px-4 py-3">
                              <div className="flex items-center gap-2">
                                {getActionIcon(log.action)}
                                <span className={`px-2 py-1 text-xs font-medium rounded-full ${getActionBadgeColor(log.action)}`}>
                                  {log.action?.replace('_', ' ')}
                                </span>
                              </div>
                            </td>
                            <td className="px-4 py-3 text-sm text-gray-600">
                              {log.user_name || log.user_id?.substring(0, 8) || 'System'}
                            </td>
                            <td className="px-4 py-3 text-sm text-gray-600 max-w-xs truncate">
                              {typeof log.details === 'object' ? JSON.stringify(log.details) : (log.details || 'No details')}
                            </td>
                            <td className="px-4 py-3 text-sm text-gray-500 font-mono">
                              {log.ip_address || 'N/A'}
                            </td>
                            <td className="px-4 py-3">
                              <button
                                onClick={() => setSelectedLog(log)}
                                className="p-1 text-gray-500 hover:text-sky-600 transition-colors"
                                title="View Details"
                              >
                                <Eye className="w-4 h-4" />
                              </button>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}

                {/* Pagination */}
                {logsTotalPages > 1 && (
                  <div className="flex items-center justify-between pt-4">
                    <p className="text-sm text-gray-500">
                      Showing page {logsPage} of {logsTotalPages} ({totalLogs} total)
                    </p>
                    <div className="flex items-center gap-2">
                      <button
                        onClick={() => setLogsPage(p => Math.max(1, p - 1))}
                        disabled={logsPage === 1}
                        className="p-2 border rounded-lg disabled:opacity-50 disabled:cursor-not-allowed hover:bg-gray-50"
                      >
                        <ChevronLeft className="w-4 h-4" />
                      </button>
                      <button
                        onClick={() => setLogsPage(p => Math.min(logsTotalPages, p + 1))}
                        disabled={logsPage === logsTotalPages}
                        className="p-2 border rounded-lg disabled:opacity-50 disabled:cursor-not-allowed hover:bg-gray-50"
                      >
                        <ChevronRight className="w-4 h-4" />
                      </button>
                    </div>
                  </div>
                )}
              </div>
            )}

            {/* Admin Activity Tab */}
            {activeTab === 'admin' && (
              <div className="space-y-4">
                {/* Admin Logs Table */}
                {adminLogsLoading ? (
                  <div className="text-center py-12">
                    <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-sky-500 mx-auto"></div>
                  </div>
                ) : adminLogs.length === 0 ? (
                  <div className="text-center py-12 text-gray-500">
                    <Shield className="w-12 h-12 mx-auto mb-4 opacity-50" />
                    <p>No admin activity logs found</p>
                  </div>
                ) : (
                  <div className="space-y-3">
                    {adminLogs.map((log) => (
                      <div
                        key={log.log_id}
                        className="bg-gray-50 rounded-lg p-4 hover:bg-gray-100 transition-colors"
                      >
                        <div className="flex items-start justify-between">
                          <div className="flex items-start gap-3">
                            <div className={`p-2 rounded-lg ${getActionBadgeColor(log.action)}`}>
                              {getActionIcon(log.action)}
                            </div>
                            <div>
                              <div className="flex items-center gap-2 mb-1">
                                <span className="font-medium text-gray-900">
                                  {log.admin_name || 'Admin'}
                                </span>
                                <span className={`px-2 py-0.5 text-xs font-medium rounded-full ${getActionBadgeColor(log.action)}`}>
                                  {log.action?.replace('_', ' ')}
                                </span>
                              </div>
                              <p className="text-sm text-gray-600">
                                {log.target_type}: {log.target_name || log.target_id || 'N/A'}
                              </p>
                              {log.details && Object.keys(log.details).length > 0 && (
                                <p className="text-xs text-gray-500 mt-1">
                                  {JSON.stringify(log.details).substring(0, 100)}...
                                </p>
                              )}
                            </div>
                          </div>
                          <div className="text-right">
                            <p className="text-xs text-gray-500">{formatDate(log.timestamp)}</p>
                            {log.success === false && (
                              <span className="text-xs text-red-600">Failed</span>
                            )}
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                )}

                {/* Pagination */}
                {adminLogsTotalPages > 1 && (
                  <div className="flex items-center justify-between pt-4">
                    <p className="text-sm text-gray-500">
                      Page {adminLogsPage} of {adminLogsTotalPages}
                    </p>
                    <div className="flex items-center gap-2">
                      <button
                        onClick={() => setAdminLogsPage(p => Math.max(1, p - 1))}
                        disabled={adminLogsPage === 1}
                        className="p-2 border rounded-lg disabled:opacity-50 disabled:cursor-not-allowed hover:bg-gray-50"
                      >
                        <ChevronLeft className="w-4 h-4" />
                      </button>
                      <button
                        onClick={() => setAdminLogsPage(p => Math.min(adminLogsTotalPages, p + 1))}
                        disabled={adminLogsPage === adminLogsTotalPages}
                        className="p-2 border rounded-lg disabled:opacity-50 disabled:cursor-not-allowed hover:bg-gray-50"
                      >
                        <ChevronRight className="w-4 h-4" />
                      </button>
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Log Detail Modal */}
      {selectedLog && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-xl max-w-2xl w-full max-h-[90vh] overflow-y-auto">
            <div className="p-6 border-b border-gray-200 flex items-center justify-between">
              <h2 className="text-xl font-semibold text-gray-900">Log Details</h2>
              <button
                onClick={() => setSelectedLog(null)}
                className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
              >
                <X className="w-5 h-5" />
              </button>
            </div>
            <div className="p-6 space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <p className="text-sm text-gray-500">Log ID</p>
                  <p className="font-mono text-sm">{selectedLog.log_id}</p>
                </div>
                <div>
                  <p className="text-sm text-gray-500">Timestamp</p>
                  <p>{formatDate(selectedLog.timestamp)}</p>
                </div>
                <div>
                  <p className="text-sm text-gray-500">Action</p>
                  <span className={`px-2 py-1 text-xs font-medium rounded-full ${getActionBadgeColor(selectedLog.action)}`}>
                    {selectedLog.action?.replace('_', ' ')}
                  </span>
                </div>
                <div>
                  <p className="text-sm text-gray-500">User</p>
                  <p>{selectedLog.user_name || selectedLog.user_id || 'System'}</p>
                </div>
                {selectedLog.ip_address && (
                  <div>
                    <p className="text-sm text-gray-500">IP Address</p>
                    <p className="font-mono text-sm">{selectedLog.ip_address}</p>
                  </div>
                )}
                {selectedLog.user_agent && (
                  <div className="col-span-2">
                    <p className="text-sm text-gray-500">User Agent</p>
                    <p className="text-sm text-gray-700 truncate">{selectedLog.user_agent}</p>
                  </div>
                )}
              </div>

              {selectedLog.details && Object.keys(selectedLog.details).length > 0 && (
                <div>
                  <p className="text-sm text-gray-500 mb-1">Details</p>
                  <pre className="text-xs bg-gray-50 rounded-lg p-3 overflow-x-auto">
                    {JSON.stringify(selectedLog.details, null, 2)}
                  </pre>
                </div>
              )}

              {selectedLog.previous_value && (
                <div>
                  <p className="text-sm text-gray-500 mb-1">Previous Value</p>
                  <pre className="text-xs bg-red-50 text-red-800 rounded-lg p-3 overflow-x-auto">
                    {typeof selectedLog.previous_value === 'object'
                      ? JSON.stringify(selectedLog.previous_value, null, 2)
                      : selectedLog.previous_value}
                  </pre>
                </div>
              )}

              {selectedLog.new_value && (
                <div>
                  <p className="text-sm text-gray-500 mb-1">New Value</p>
                  <pre className="text-xs bg-green-50 text-green-800 rounded-lg p-3 overflow-x-auto">
                    {typeof selectedLog.new_value === 'object'
                      ? JSON.stringify(selectedLog.new_value, null, 2)
                      : selectedLog.new_value}
                  </pre>
                </div>
              )}

              {selectedLog.error_message && (
                <div>
                  <p className="text-sm text-gray-500 mb-1">Error Message</p>
                  <p className="text-red-700 bg-red-50 rounded-lg p-3">{selectedLog.error_message}</p>
                </div>
              )}

              {selectedLog.metadata && (
                <div>
                  <p className="text-sm text-gray-500 mb-1">Additional Metadata</p>
                  <pre className="text-xs bg-gray-50 rounded-lg p-3 overflow-x-auto">
                    {JSON.stringify(selectedLog.metadata, null, 2)}
                  </pre>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </DashboardLayout>
  );
}
