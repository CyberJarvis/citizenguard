'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import DashboardLayout from '@/components/DashboardLayout';
import PageHeader from '@/components/PageHeader';
import useAuthStore from '@/context/AuthContext';
import api from '@/lib/api';
import {
  AlertTriangle,
  Bell,
  Plus,
  Filter,
  Search,
  MapPin,
  Calendar,
  XCircle,
  CheckCircle,
  Clock,
  AlertCircle,
  Edit,
  Trash2
} from 'lucide-react';

export default function AlertsManagement() {
  const router = useRouter();
  const { user, isLoading: authLoading, initialize } = useAuthStore();

  const [alerts, setAlerts] = useState([]);
  const [summary, setSummary] = useState(null);
  const [loading, setLoading] = useState(true);

  // Filters
  const [statusFilter, setStatusFilter] = useState('active');
  const [severityFilter, setSeverityFilter] = useState('all');
  const [searchQuery, setSearchQuery] = useState('');

  // Pagination
  const [page, setPage] = useState(1);
  const [totalCount, setTotalCount] = useState(0);
  const limit = 20;

  // Initialize auth on mount
  useEffect(() => {
    initialize();
  }, [initialize]);

  // Check if user is authority or admin
  useEffect(() => {
    if (!authLoading && user) {
      if (user.role !== 'authority' && user.role !== 'authority_admin') {
        router.push('/dashboard');
      } else {
        fetchData();
      }
    }
  }, [user, authLoading, statusFilter, severityFilter, page]);

  const fetchData = async () => {
    try {
      setLoading(true);

      // Fetch summary
      const summaryResponse = await api.get('/alerts/active/summary');
      setSummary(summaryResponse.data);

      // Fetch alerts with filters
      const params = {
        skip: (page - 1) * limit,
        limit: limit,
        status_filter: statusFilter
      };

      if (severityFilter !== 'all') params.severity = severityFilter;

      const alertsResponse = await api.get('/alerts', { params });
      setAlerts(alertsResponse.data.alerts);
      setTotalCount(alertsResponse.data.total);

    } catch (error) {
      console.error('Error fetching alerts:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleCancelAlert = async (alertId) => {
    const reason = prompt('Please provide a reason for cancelling this alert (minimum 10 characters):');
    if (!reason) return;
    
    if (reason.length < 10) {
      alert('Cancellation reason must be at least 10 characters long.');
      return;
    }

    try {
      await api.post(`/alerts/${alertId}/cancel?reason=${encodeURIComponent(reason)}`);
      alert('Alert cancelled successfully');
      fetchData();
    } catch (error) {
      console.error('Error cancelling alert:', error);
      alert('Failed to cancel alert: ' + (error.response?.data?.detail || error.message));
    }
  };

  const handleDeleteAlert = async (alertId) => {
    if (!confirm('Are you sure you want to permanently delete this alert? This action cannot be undone.')) {
      return;
    }

    try {
      await api.delete(`/alerts/${alertId}`);
      alert('Alert deleted successfully');
      fetchData();
    } catch (error) {
      console.error('Error deleting alert:', error);
      alert('Failed to delete alert. Only admins can delete alerts.');
    }
  };

  const getSeverityColor = (severity) => {
    switch (severity) {
      case 'critical': return 'bg-red-700 text-white';
      case 'high': return 'bg-red-600 text-white';
      case 'medium': return 'bg-orange-600 text-white';
      case 'low': return 'bg-yellow-600 text-white';
      case 'info': return 'bg-[#1a6b9a] text-white';
      default: return 'bg-gray-600 text-white';
    }
  };

  const getStatusColor = (status) => {
    switch (status) {
      case 'active': return 'bg-green-100 text-green-700';
      case 'expired': return 'bg-gray-100 text-gray-700';
      case 'cancelled': return 'bg-red-100 text-red-700';
      default: return 'bg-gray-100 text-gray-700';
    }
  };

  // Show loading state while auth is initializing or data is loading
  if (authLoading || loading || !user) {
    return (
      <DashboardLayout>
        <div className="flex items-center justify-center min-h-screen">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-[#0d4a6f]"></div>
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
              <h1 className="text-2xl font-bold mb-2">Alert Management</h1>
              <p className="text-[#9ecbec]">
                Create and manage hazard alerts for affected regions
              </p>
            </div>
            <button
              onClick={() => router.push('/authority/alerts/create')}
              className="px-6 py-3 bg-white text-[#0d4a6f] rounded-xl font-medium hover:bg-[#e8f4fc] transition-colors flex items-center gap-2"
            >
              <Plus className="w-5 h-5" />
              Create Alert
            </button>
          </div>
        </div>

        {/* Summary Stats */}
        {summary && (
          <div className="grid grid-cols-1 md:grid-cols-6 gap-4">
            <div className="bg-white rounded-xl shadow-sm border border-[#c5e1f5] p-4">
              <p className="text-sm text-gray-600">Total Active</p>
              <p className="text-2xl font-bold text-[#0d4a6f]">{summary.total_active}</p>
            </div>
            <div className="bg-white rounded-xl shadow-sm border border-red-200 p-4">
              <p className="text-sm text-gray-600">Critical</p>
              <p className="text-2xl font-bold text-red-700">{summary.by_severity.critical}</p>
            </div>
            <div className="bg-white rounded-xl shadow-sm border border-red-200 p-4">
              <p className="text-sm text-gray-600">High</p>
              <p className="text-2xl font-bold text-red-600">{summary.by_severity.high}</p>
            </div>
            <div className="bg-white rounded-xl shadow-sm border border-orange-200 p-4">
              <p className="text-sm text-gray-600">Medium</p>
              <p className="text-2xl font-bold text-orange-600">{summary.by_severity.medium}</p>
            </div>
            <div className="bg-white rounded-xl shadow-sm border border-yellow-200 p-4">
              <p className="text-sm text-gray-600">Low</p>
              <p className="text-2xl font-bold text-yellow-600">{summary.by_severity.low}</p>
            </div>
            <div className="bg-white rounded-xl shadow-sm border border-[#c5e1f5] p-4">
              <p className="text-sm text-gray-600">Info</p>
              <p className="text-2xl font-bold text-[#1a6b9a]">{summary.by_severity.info}</p>
            </div>
          </div>
        )}

        {/* Filters */}
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-4">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <select
              value={statusFilter}
              onChange={(e) => { setStatusFilter(e.target.value); setPage(1); }}
              className="px-4 py-2 border border-gray-300 rounded-xl focus:ring-2 focus:ring-[#1a6b9a]"
            >
              <option value="all">All Status</option>
              <option value="active">Active</option>
              <option value="expired">Expired</option>
              <option value="cancelled">Cancelled</option>
            </select>

            <select
              value={severityFilter}
              onChange={(e) => { setSeverityFilter(e.target.value); setPage(1); }}
              className="px-4 py-2 border border-gray-300 rounded-xl focus:ring-2 focus:ring-[#1a6b9a]"
            >
              <option value="all">All Severity</option>
              <option value="critical">Critical</option>
              <option value="high">High</option>
              <option value="medium">Medium</option>
              <option value="low">Low</option>
              <option value="info">Info</option>
            </select>

            <button
              onClick={() => router.push('/authority/alerts/create')}
              className="px-4 py-2 bg-[#0d4a6f] text-white rounded-xl hover:bg-[#083a57] transition-colors flex items-center justify-center gap-2"
            >
              <Plus className="w-4 h-4" />
              New Alert
            </button>
          </div>
        </div>

        {/* Alerts List */}
        <div className="bg-white rounded-xl shadow-sm border border-gray-200">
          <div className="px-6 py-4 border-b border-gray-200">
            <h2 className="text-lg font-semibold text-gray-900">
              Alerts ({totalCount})
            </h2>
          </div>

          <div className="divide-y divide-gray-200">
            {alerts.length === 0 ? (
              <div className="p-12 text-center">
                <Bell className="w-12 h-12 text-gray-400 mx-auto mb-4" />
                <p className="text-gray-600">No alerts found</p>
                <button
                  onClick={() => router.push('/authority/alerts/create')}
                  className="mt-4 px-6 py-2 bg-[#0d4a6f] text-white rounded-xl hover:bg-[#083a57]"
                >
                  Create First Alert
                </button>
              </div>
            ) : (
              alerts.map((alert) => (
                <div key={alert.alert_id} className="p-6 hover:bg-gray-50 transition-colors">
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      {/* Header */}
                      <div className="flex items-center gap-3 mb-2">
                        <h3 className="text-xl font-semibold text-gray-900">
                          {alert.title}
                        </h3>

                        {/* Severity Badge */}
                        <span className={`px-3 py-1 text-sm font-bold rounded-lg ${getSeverityColor(alert.severity)}`}>
                          {alert.severity.toUpperCase()}
                        </span>

                        {/* Status Badge */}
                        <span className={`px-3 py-1 text-sm font-medium rounded-full ${getStatusColor(alert.status)}`}>
                          {alert.status}
                        </span>

                        {/* Priority Badge */}
                        {alert.priority && (
                          <span className="px-3 py-1 text-sm font-medium bg-purple-100 text-purple-700 rounded-full">
                            Priority {alert.priority}
                          </span>
                        )}
                      </div>

                      {/* Description */}
                      <p className="text-gray-700 mb-3">
                        {alert.description}
                      </p>

                      {/* Meta Info */}
                      <div className="flex items-center gap-4 text-sm text-gray-600 mb-3">
                        <div className="flex items-center gap-1">
                          <MapPin className="w-4 h-4" />
                          <span>{alert.regions?.join(', ') || 'No regions'}</span>
                        </div>
                        <div className="flex items-center gap-1">
                          <Calendar className="w-4 h-4" />
                          <span>Issued: {new Date(alert.issued_at).toLocaleDateString()}</span>
                        </div>
                        {alert.expires_at && (
                          <div className="flex items-center gap-1">
                            <Clock className="w-4 h-4" />
                            <span>Expires: {new Date(alert.expires_at).toLocaleDateString()}</span>
                          </div>
                        )}
                      </div>

                      {/* Creator Info */}
                      <div className="text-sm text-gray-600">
                        Created by: {alert.creator_name || alert.created_by}
                        {alert.creator_organization && ` (${alert.creator_organization})`}
                      </div>

                      {/* Instructions */}
                      {alert.instructions && (
                        <div className="mt-3 p-3 bg-[#e8f4fc] border border-[#c5e1f5] rounded-xl">
                          <p className="text-sm text-[#083a57] font-medium">Instructions:</p>
                          <p className="text-sm text-[#0d4a6f]">{alert.instructions}</p>
                        </div>
                      )}

                      {/* Tags */}
                      {alert.tags && alert.tags.length > 0 && (
                        <div className="mt-2 flex gap-2">
                          {alert.tags.map((tag, idx) => (
                            <span
                              key={idx}
                              className="px-2 py-1 text-xs bg-gray-100 text-gray-700 rounded"
                            >
                              {tag}
                            </span>
                          ))}
                        </div>
                      )}
                    </div>

                    {/* Actions */}
                    <div className="flex gap-2 ml-4">
                      {alert.status === 'active' && (
                        <button
                          onClick={() => handleCancelAlert(alert.alert_id)}
                          className="p-2 text-orange-600 hover:bg-orange-50 rounded-lg transition-colors"
                          title="Cancel Alert"
                        >
                          <XCircle className="w-5 h-5" />
                        </button>
                      )}
                      {user.role === 'authority_admin' && (
                        <button
                          onClick={() => handleDeleteAlert(alert.alert_id)}
                          className="p-2 text-red-600 hover:bg-red-50 rounded-lg transition-colors"
                          title="Delete Alert (Admin Only)"
                        >
                          <Trash2 className="w-5 h-5" />
                        </button>
                      )}
                    </div>
                  </div>
                </div>
              ))
            )}
          </div>

          {/* Pagination */}
          {totalCount > limit && (
            <div className="px-6 py-4 border-t border-gray-200 flex items-center justify-between">
              <p className="text-sm text-gray-600">
                Showing {(page - 1) * limit + 1} to {Math.min(page * limit, totalCount)} of {totalCount} alerts
              </p>
              <div className="flex gap-2">
                <button
                  onClick={() => setPage(page - 1)}
                  disabled={page === 1}
                  className="px-4 py-2 border border-gray-300 rounded-lg disabled:opacity-50 disabled:cursor-not-allowed hover:bg-gray-50"
                >
                  Previous
                </button>
                <button
                  onClick={() => setPage(page + 1)}
                  disabled={page * limit >= totalCount}
                  className="px-4 py-2 border border-gray-300 rounded-lg disabled:opacity-50 disabled:cursor-not-allowed hover:bg-gray-50"
                >
                  Next
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </DashboardLayout>
  );
}
