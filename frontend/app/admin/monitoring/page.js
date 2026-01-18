'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import DashboardLayout from '@/components/DashboardLayout';
import PageHeader from '@/components/PageHeader';
import useAuthStore from '@/context/AuthContext';
import api from '@/lib/api';
import { formatDateTimeIST } from '@/lib/dateUtils';
import toast from 'react-hot-toast';
import {
  Server,
  Database,
  Activity,
  AlertTriangle,
  CheckCircle,
  XCircle,
  Clock,
  Zap,
  RefreshCw,
  HardDrive,
  Cpu,
  Shield,
  TrendingUp,
  ChevronLeft,
  ChevronRight,
  Eye,
  X
} from 'lucide-react';

export default function AdminMonitoringPage() {
  const router = useRouter();
  const { user, isLoading: authLoading } = useAuthStore();

  // Health state
  const [health, setHealth] = useState(null);
  const [healthLoading, setHealthLoading] = useState(true);

  // API stats state
  const [apiStats, setApiStats] = useState(null);
  const [apiStatsLoading, setApiStatsLoading] = useState(true);

  // Error logs state
  const [errorLogs, setErrorLogs] = useState([]);
  const [errorsLoading, setErrorsLoading] = useState(false);
  const [errorsTotalPages, setErrorsTotalPages] = useState(1);
  const [errorsPage, setErrorsPage] = useState(1);

  // Database stats state
  const [dbStats, setDbStats] = useState(null);
  const [dbStatsLoading, setDbStatsLoading] = useState(true);

  // Modal state
  const [selectedError, setSelectedError] = useState(null);

  // Refreshing state
  const [refreshing, setRefreshing] = useState(false);

  useEffect(() => {
    if (!authLoading && user) {
      if (user.role !== 'authority_admin') {
        toast.error('Access denied. Admin privileges required.');
        router.push('/dashboard');
      } else {
        fetchAllData();
      }
    }
  }, [user, authLoading, router]);

  const fetchAllData = async () => {
    await Promise.all([
      fetchHealth(),
      fetchApiStats(),
      fetchErrorLogs(),
      fetchDbStats()
    ]);
  };

  const handleRefresh = async () => {
    setRefreshing(true);
    await fetchAllData();
    setRefreshing(false);
    toast.success('Data refreshed');
  };

  const fetchHealth = async () => {
    try {
      setHealthLoading(true);
      const response = await api.get('/admin/monitoring/health');
      setHealth(response.data.data);
    } catch (error) {
      console.error('Error fetching health:', error);
    } finally {
      setHealthLoading(false);
    }
  };

  const fetchApiStats = async () => {
    try {
      setApiStatsLoading(true);
      const response = await api.get('/admin/monitoring/api-stats');
      setApiStats(response.data.data);
    } catch (error) {
      console.error('Error fetching API stats:', error);
    } finally {
      setApiStatsLoading(false);
    }
  };

  const fetchErrorLogs = async () => {
    try {
      setErrorsLoading(true);
      const params = new URLSearchParams({
        page: errorsPage.toString(),
        limit: '10'
      });
      const response = await api.get(`/admin/monitoring/errors?${params}`);
      // Backend returns { success: true, data: { errors: [], pagination: {} } }
      const responseData = response.data?.data || response.data || {};
      const errorsData = responseData.errors || responseData || [];
      setErrorLogs(Array.isArray(errorsData) ? errorsData : []);
      setErrorsTotalPages(responseData.pagination?.total_pages || 1);
    } catch (error) {
      console.error('Error fetching error logs:', error);
      setErrorLogs([]);
    } finally {
      setErrorsLoading(false);
    }
  };

  const fetchDbStats = async () => {
    try {
      setDbStatsLoading(true);
      const response = await api.get('/admin/monitoring/database');
      setDbStats(response.data.data);
    } catch (error) {
      console.error('Error fetching database stats:', error);
    } finally {
      setDbStatsLoading(false);
    }
  };

  useEffect(() => {
    if (!authLoading && user?.role === 'authority_admin') {
      fetchErrorLogs();
    }
  }, [errorsPage]);

  const getHealthStatusColor = (status) => {
    switch (status) {
      case 'healthy': return 'text-green-600 bg-green-100';
      case 'warning': return 'text-amber-600 bg-amber-100';
      case 'critical': return 'text-red-600 bg-red-100';
      default: return 'text-gray-600 bg-gray-100';
    }
  };

  const getHealthIcon = (status) => {
    switch (status) {
      case 'healthy': return <CheckCircle className="w-5 h-5 text-green-600" />;
      case 'warning': return <AlertTriangle className="w-5 h-5 text-amber-600" />;
      case 'critical': return <XCircle className="w-5 h-5 text-red-600" />;
      default: return <Activity className="w-5 h-5 text-gray-600" />;
    }
  };

  const formatBytes = (bytes) => {
    if (!bytes) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
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
                  <Server className="w-6 h-6" />
                </div>
                System Monitoring
              </h1>
              <p className="text-[#9ecbec] mt-1">
                Monitor system health, performance, and error logs
              </p>
            </div>
            <button
              onClick={handleRefresh}
              disabled={refreshing}
              className="flex items-center gap-2 px-4 py-2 bg-white/10 border border-white/20 hover:bg-white/20 rounded-xl transition-colors"
            >
              <RefreshCw className={`w-4 h-4 ${refreshing ? 'animate-spin' : ''}`} />
              Refresh
            </button>
          </div>
        </div>

        {/* System Health Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Overall Health */}
          <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
            <h2 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
              <Activity className="w-5 h-5 text-[#0d4a6f]" />
              System Health
            </h2>
            {healthLoading ? (
              <div className="text-center py-8">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-[#0d4a6f] mx-auto"></div>
              </div>
            ) : health ? (
              <div className="space-y-4">
                {/* Overall Status */}
                <div className="flex items-center justify-between p-4 bg-gray-50 rounded-lg">
                  <span className="font-medium text-gray-700">Overall Status</span>
                  <span className={`px-3 py-1 rounded-full text-sm font-medium flex items-center gap-2 ${getHealthStatusColor(health.overall_status)}`}>
                    {getHealthIcon(health.overall_status)}
                    {health.overall_status?.toUpperCase()}
                  </span>
                </div>

                {/* Components */}
                {health.components && Object.entries(health.components).map(([name, data]) => (
                  <div key={name} className="flex items-center justify-between p-3 border border-gray-100 rounded-lg">
                    <div className="flex items-center gap-3">
                      {name === 'database' && <Database className="w-5 h-5 text-gray-500" />}
                      {name === 'api' && <Zap className="w-5 h-5 text-gray-500" />}
                      {name === 'storage' && <HardDrive className="w-5 h-5 text-gray-500" />}
                      {name === 'cache' && <Cpu className="w-5 h-5 text-gray-500" />}
                      <span className="font-medium text-gray-700 capitalize">{name}</span>
                    </div>
                    <div className="flex items-center gap-3">
                      {data.response_time && (
                        <span className="text-sm text-gray-500">{data.response_time}ms</span>
                      )}
                      <span className={`px-2 py-1 rounded-full text-xs font-medium ${getHealthStatusColor(data.status)}`}>
                        {data.status}
                      </span>
                    </div>
                  </div>
                ))}

                {/* Last Check */}
                <p className="text-xs text-gray-500 text-right">
                  Last checked: {formatDate(health.timestamp)}
                </p>
              </div>
            ) : (
              <p className="text-gray-500 text-center py-8">Health data not available</p>
            )}
          </div>

          {/* API Statistics */}
          <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
            <h2 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
              <TrendingUp className="w-5 h-5 text-[#0d4a6f]" />
              API Statistics (24h)
            </h2>
            {apiStatsLoading ? (
              <div className="text-center py-8">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-[#0d4a6f] mx-auto"></div>
              </div>
            ) : apiStats ? (
              <div className="space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  <div className="p-4 bg-blue-50 rounded-lg">
                    <p className="text-sm text-blue-600 mb-1">Total Requests</p>
                    <p className="text-2xl font-bold text-blue-700">{apiStats.total_requests || 0}</p>
                  </div>
                  <div className="p-4 bg-green-50 rounded-lg">
                    <p className="text-sm text-green-600 mb-1">Successful</p>
                    <p className="text-2xl font-bold text-green-700">{apiStats.successful_requests || 0}</p>
                  </div>
                  <div className="p-4 bg-red-50 rounded-lg">
                    <p className="text-sm text-red-600 mb-1">Failed</p>
                    <p className="text-2xl font-bold text-red-700">{apiStats.failed_requests || 0}</p>
                  </div>
                  <div className="p-4 bg-amber-50 rounded-lg">
                    <p className="text-sm text-amber-600 mb-1">Avg Response</p>
                    <p className="text-2xl font-bold text-amber-700">{apiStats.avg_response_time || 0}ms</p>
                  </div>
                </div>

                {/* Top Endpoints */}
                {apiStats.top_endpoints?.length > 0 && (
                  <div>
                    <p className="text-sm font-medium text-gray-700 mb-2">Top Endpoints</p>
                    <div className="space-y-2">
                      {apiStats.top_endpoints.slice(0, 5).map((endpoint, idx) => (
                        <div key={idx} className="flex items-center justify-between text-sm">
                          <span className="text-gray-600 truncate flex-1 mr-4">
                            {endpoint.endpoint}
                          </span>
                          <span className="text-gray-900 font-medium">{endpoint.count}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            ) : (
              <p className="text-gray-500 text-center py-8">API stats not available</p>
            )}
          </div>
        </div>

        {/* Database Stats */}
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
            <Database className="w-5 h-5 text-[#0d4a6f]" />
            Database Statistics
          </h2>
          {dbStatsLoading ? (
            <div className="text-center py-8">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-[#0d4a6f] mx-auto"></div>
            </div>
          ) : dbStats ? (
            <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-4">
              {dbStats.collections && Object.entries(dbStats.collections).map(([name, data]) => (
                <div key={name} className="p-4 bg-gray-50 rounded-lg">
                  <p className="text-xs text-gray-500 mb-1 capitalize">{name.replace('_', ' ')}</p>
                  <p className="text-xl font-bold text-gray-900">{data.count || 0}</p>
                  {data.size && (
                    <p className="text-xs text-gray-400 mt-1">{formatBytes(data.size)}</p>
                  )}
                </div>
              ))}
              {!dbStats.collections && (
                <p className="col-span-full text-gray-500 text-center py-4">No collection data available</p>
              )}
            </div>
          ) : (
            <p className="text-gray-500 text-center py-8">Database stats not available</p>
          )}
        </div>

        {/* Error Logs */}
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
            <AlertTriangle className="w-5 h-5 text-red-600" />
            Recent Errors
          </h2>
          {errorsLoading ? (
            <div className="text-center py-8">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-[#0d4a6f] mx-auto"></div>
            </div>
          ) : errorLogs.length === 0 ? (
            <div className="text-center py-8 text-gray-500">
              <CheckCircle className="w-12 h-12 mx-auto mb-4 text-green-500" />
              <p>No errors logged</p>
            </div>
          ) : (
            <>
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead className="bg-gray-50">
                    <tr>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Time</th>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Level</th>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Message</th>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Endpoint</th>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Actions</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-200">
                    {errorLogs.map((error) => (
                      <tr key={error.error_id} className="hover:bg-gray-50">
                        <td className="px-4 py-3 text-sm text-gray-500">
                          <div className="flex items-center gap-1">
                            <Clock className="w-3 h-3" />
                            {formatDate(error.timestamp)}
                          </div>
                        </td>
                        <td className="px-4 py-3">
                          <span className={`px-2 py-1 text-xs font-medium rounded-full ${
                            error.level === 'error' ? 'bg-red-100 text-red-700' :
                            error.level === 'warning' ? 'bg-amber-100 text-amber-700' :
                            'bg-blue-100 text-blue-700'
                          }`}>
                            {error.level}
                          </span>
                        </td>
                        <td className="px-4 py-3 text-sm text-gray-600 max-w-xs truncate">
                          {error.message}
                        </td>
                        <td className="px-4 py-3 text-sm text-gray-500 font-mono">
                          {error.request_path || error.endpoint || 'N/A'}
                        </td>
                        <td className="px-4 py-3">
                          <button
                            onClick={() => setSelectedError(error)}
                            className="p-1 text-gray-500 hover:text-[#0d4a6f] transition-colors"
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

              {/* Pagination */}
              {errorsTotalPages > 1 && (
                <div className="flex items-center justify-between pt-4 border-t border-gray-100 mt-4">
                  <p className="text-sm text-gray-500">
                    Page {errorsPage} of {errorsTotalPages}
                  </p>
                  <div className="flex items-center gap-2">
                    <button
                      onClick={() => setErrorsPage(p => Math.max(1, p - 1))}
                      disabled={errorsPage === 1}
                      className="p-2 border rounded-lg disabled:opacity-50 disabled:cursor-not-allowed hover:bg-gray-50"
                    >
                      <ChevronLeft className="w-4 h-4" />
                    </button>
                    <button
                      onClick={() => setErrorsPage(p => Math.min(errorsTotalPages, p + 1))}
                      disabled={errorsPage === errorsTotalPages}
                      className="p-2 border rounded-lg disabled:opacity-50 disabled:cursor-not-allowed hover:bg-gray-50"
                    >
                      <ChevronRight className="w-4 h-4" />
                    </button>
                  </div>
                </div>
              )}
            </>
          )}
        </div>
      </div>

      {/* Error Detail Modal */}
      {selectedError && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-xl max-w-2xl w-full max-h-[90vh] overflow-y-auto">
            <div className="p-6 border-b border-gray-200 flex items-center justify-between">
              <h2 className="text-xl font-semibold text-gray-900">Error Details</h2>
              <button
                onClick={() => setSelectedError(null)}
                className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
              >
                <X className="w-5 h-5" />
              </button>
            </div>
            <div className="p-6 space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <p className="text-sm text-gray-500">Error ID</p>
                  <p className="font-mono text-sm">{selectedError.error_id}</p>
                </div>
                <div>
                  <p className="text-sm text-gray-500">Level</p>
                  <span className={`px-2 py-1 text-xs font-medium rounded-full ${
                    selectedError.level === 'error' ? 'bg-red-100 text-red-700' :
                    selectedError.level === 'warning' ? 'bg-amber-100 text-amber-700' :
                    'bg-blue-100 text-blue-700'
                  }`}>
                    {selectedError.level}
                  </span>
                </div>
                <div>
                  <p className="text-sm text-gray-500">Timestamp</p>
                  <p>{formatDate(selectedError.timestamp)}</p>
                </div>
                <div>
                  <p className="text-sm text-gray-500">Endpoint</p>
                  <p className="font-mono text-sm">{selectedError.request_path || selectedError.endpoint || 'N/A'}</p>
                </div>
                {selectedError.user_id && (
                  <div>
                    <p className="text-sm text-gray-500">User ID</p>
                    <p className="font-mono text-sm">{selectedError.user_id}</p>
                  </div>
                )}
                {selectedError.method && (
                  <div>
                    <p className="text-sm text-gray-500">HTTP Method</p>
                    <p className="font-mono text-sm">{selectedError.method}</p>
                  </div>
                )}
              </div>

              <div>
                <p className="text-sm text-gray-500 mb-1">Message</p>
                <p className="text-gray-900 bg-gray-50 rounded-lg p-3">{selectedError.message}</p>
              </div>

              {selectedError.stack_trace && (
                <div>
                  <p className="text-sm text-gray-500 mb-1">Stack Trace</p>
                  <pre className="text-xs text-gray-700 bg-gray-900 text-gray-100 rounded-lg p-4 overflow-x-auto">
                    {selectedError.stack_trace}
                  </pre>
                </div>
              )}

              {selectedError.request_body && (
                <div>
                  <p className="text-sm text-gray-500 mb-1">Request Body</p>
                  <pre className="text-xs bg-gray-50 rounded-lg p-3 overflow-x-auto">
                    {JSON.stringify(selectedError.request_body, null, 2)}
                  </pre>
                </div>
              )}

              {selectedError.metadata && (
                <div>
                  <p className="text-sm text-gray-500 mb-1">Additional Metadata</p>
                  <pre className="text-xs bg-gray-50 rounded-lg p-3 overflow-x-auto">
                    {JSON.stringify(selectedError.metadata, null, 2)}
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
