'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import DashboardLayout from '@/components/DashboardLayout';
import PageHeader from '@/components/PageHeader';
import useAuthStore from '@/context/AuthContext';
import api, { getImageUrl } from '@/lib/api';
import { formatDateTimeIST } from '@/lib/dateUtils';
import toast from 'react-hot-toast';
import {
  FileText,
  AlertTriangle,
  MessageSquare,
  Shield,
  Search,
  Filter,
  Trash2,
  Eye,
  ChevronLeft,
  ChevronRight,
  X,
  MapPin,
  Clock,
  User,
  RefreshCw,
  CheckCircle,
  XCircle,
  AlertCircle,
  ShieldCheck
} from 'lucide-react';
import Link from 'next/link';

export default function AdminReportsPage() {
  const router = useRouter();
  const { user, isLoading: authLoading } = useAuthStore();

  // Tab state
  const [activeTab, setActiveTab] = useState('reports');

  // Reports state
  const [reports, setReports] = useState([]);
  const [reportsLoading, setReportsLoading] = useState(false);
  const [reportsTotalPages, setReportsTotalPages] = useState(1);
  const [reportsPage, setReportsPage] = useState(1);
  const [reportsStatusFilter, setReportsStatusFilter] = useState('all');

  // Alerts state
  const [alerts, setAlerts] = useState([]);
  const [alertsLoading, setAlertsLoading] = useState(false);
  const [alertsTotalPages, setAlertsTotalPages] = useState(1);
  const [alertsPage, setAlertsPage] = useState(1);
  const [alertsStatusFilter, setAlertsStatusFilter] = useState('all');
  const [alertsSeverityFilter, setAlertsSeverityFilter] = useState('all');

  // Chat messages state
  const [messages, setMessages] = useState([]);
  const [messagesLoading, setMessagesLoading] = useState(false);
  const [messagesTotalPages, setMessagesTotalPages] = useState(1);
  const [messagesPage, setMessagesPage] = useState(1);

  // Modal states
  const [selectedReport, setSelectedReport] = useState(null);
  const [selectedAlert, setSelectedAlert] = useState(null);
  const [deleteConfirm, setDeleteConfirm] = useState(null);

  useEffect(() => {
    if (!authLoading && user) {
      if (user.role !== 'authority_admin') {
        toast.error('Access denied. Admin privileges required.');
        router.push('/dashboard');
      } else {
        fetchData();
      }
    }
  }, [user, authLoading, router, activeTab]);

  const fetchData = () => {
    if (activeTab === 'reports') {
      fetchReports();
    } else if (activeTab === 'alerts') {
      fetchAlerts();
    } else if (activeTab === 'messages') {
      fetchMessages();
    }
  };

  const fetchReports = async () => {
    try {
      setReportsLoading(true);
      const params = new URLSearchParams({
        page: reportsPage.toString(),
        limit: '20'
      });
      if (reportsStatusFilter !== 'all') {
        params.append('status', reportsStatusFilter);
      }

      const response = await api.get(`/admin/reports?${params}`);
      // Backend returns { success: true, data: { reports: [], pagination: {} } }
      const responseData = response.data?.data || response.data || {};
      const reportsData = responseData.reports || responseData || [];
      setReports(Array.isArray(reportsData) ? reportsData : []);
      setReportsTotalPages(responseData.pagination?.total_pages || response.data?.pagination?.total_pages || 1);
    } catch (error) {
      console.error('Error fetching reports:', error);
      toast.error('Failed to load reports');
      setReports([]);
    } finally {
      setReportsLoading(false);
    }
  };

  const fetchAlerts = async () => {
    try {
      setAlertsLoading(true);
      const params = new URLSearchParams({
        page: alertsPage.toString(),
        limit: '20'
      });
      if (alertsStatusFilter !== 'all') {
        params.append('status', alertsStatusFilter);
      }
      if (alertsSeverityFilter !== 'all') {
        params.append('severity', alertsSeverityFilter);
      }

      const response = await api.get(`/admin/alerts?${params}`);
      // Backend returns { success: true, data: { alerts: [], pagination: {} } }
      const responseData = response.data?.data || response.data || {};
      const alertsData = responseData.alerts || responseData || [];
      setAlerts(Array.isArray(alertsData) ? alertsData : []);
      setAlertsTotalPages(responseData.pagination?.total_pages || response.data?.pagination?.total_pages || 1);
    } catch (error) {
      console.error('Error fetching alerts:', error);
      toast.error('Failed to load alerts');
      setAlerts([]);
    } finally {
      setAlertsLoading(false);
    }
  };

  const fetchMessages = async () => {
    try {
      setMessagesLoading(true);
      const params = new URLSearchParams({
        page: messagesPage.toString(),
        limit: '20'
      });

      const response = await api.get(`/admin/chat/messages?${params}`);
      // Backend returns { success: true, data: { messages: [], pagination: {} } }
      const responseData = response.data?.data || response.data || {};
      const messagesData = responseData.messages || responseData || [];
      setMessages(Array.isArray(messagesData) ? messagesData : []);
      setMessagesTotalPages(responseData.pagination?.total_pages || response.data?.pagination?.total_pages || 1);
    } catch (error) {
      console.error('Error fetching messages:', error);
      toast.error('Failed to load chat messages');
      setMessages([]);
    } finally {
      setMessagesLoading(false);
    }
  };

  const handleDeleteReport = async (reportId) => {
    try {
      await api.delete(`/admin/reports/${reportId}`);
      toast.success('Report deleted successfully');
      setDeleteConfirm(null);
      fetchReports();
    } catch (error) {
      toast.error('Failed to delete report');
    }
  };

  const handleDeleteAlert = async (alertId) => {
    try {
      await api.delete(`/admin/alerts/${alertId}`);
      toast.success('Alert deleted successfully');
      setDeleteConfirm(null);
      fetchAlerts();
    } catch (error) {
      toast.error('Failed to delete alert');
    }
  };

  const handleDeleteMessage = async (messageId) => {
    try {
      await api.delete(`/admin/chat/messages/${messageId}`);
      toast.success('Message deleted successfully');
      setDeleteConfirm(null);
      fetchMessages();
    } catch (error) {
      toast.error('Failed to delete message');
    }
  };

  useEffect(() => {
    if (!authLoading && user?.role === 'authority_admin') {
      if (activeTab === 'reports') fetchReports();
    }
  }, [reportsPage, reportsStatusFilter]);

  useEffect(() => {
    if (!authLoading && user?.role === 'authority_admin') {
      if (activeTab === 'alerts') fetchAlerts();
    }
  }, [alertsPage, alertsStatusFilter, alertsSeverityFilter]);

  useEffect(() => {
    if (!authLoading && user?.role === 'authority_admin') {
      if (activeTab === 'messages') fetchMessages();
    }
  }, [messagesPage]);

  const getStatusBadge = (status) => {
    const styles = {
      pending: 'bg-amber-100 text-amber-700',
      verified: 'bg-green-100 text-green-700',
      rejected: 'bg-red-100 text-red-700',
      auto_approved: 'bg-[#e8f4fc] text-[#083a57]',
      auto_rejected: 'bg-purple-100 text-purple-700',
      under_review: 'bg-blue-100 text-blue-700',
      active: 'bg-green-100 text-green-700',
      resolved: 'bg-gray-100 text-gray-700',
      expired: 'bg-gray-100 text-gray-500'
    };
    return styles[status] || 'bg-gray-100 text-gray-700';
  };

  const getStatusLabel = (status) => {
    const labels = {
      auto_approved: 'Accepted by AI',
      auto_rejected: 'Rejected by AI',
      pending: 'Pending',
      verified: 'Verified',
      rejected: 'Rejected',
      under_review: 'Under Review'
    };
    return labels[status] || status;
  };

  const getSeverityBadge = (severity) => {
    const styles = {
      critical: 'bg-red-100 text-red-700',
      high: 'bg-orange-100 text-orange-700',
      medium: 'bg-amber-100 text-amber-700',
      low: 'bg-green-100 text-green-700'
    };
    return styles[severity] || 'bg-gray-100 text-gray-700';
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
                  <Shield className="w-6 h-6" />
                </div>
                Content Moderation
              </h1>
              <p className="text-[#9ecbec] mt-1">
                Review and moderate reports, alerts, and chat messages
              </p>
            </div>
            <div className="flex items-center gap-3">
              <Link
                href="/analyst/verification-queue"
                className="flex items-center gap-2 px-4 py-2 bg-amber-500 hover:bg-amber-600 text-white rounded-xl transition-colors font-medium"
              >
                <ShieldCheck className="w-4 h-4" />
                Verification Queue
              </Link>
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

        {/* Tabs */}
        <div className="bg-white rounded-xl shadow-sm border border-gray-200">
          <div className="border-b border-gray-200">
            <nav className="flex -mb-px">
              <button
                onClick={() => setActiveTab('reports')}
                className={`px-6 py-4 text-sm font-medium border-b-2 transition-colors flex items-center gap-2 ${
                  activeTab === 'reports'
                    ? 'border-[#0d4a6f] text-[#0d4a6f]'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                }`}
              >
                <FileText className="w-4 h-4" />
                Reports
              </button>
              <button
                onClick={() => setActiveTab('alerts')}
                className={`px-6 py-4 text-sm font-medium border-b-2 transition-colors flex items-center gap-2 ${
                  activeTab === 'alerts'
                    ? 'border-[#0d4a6f] text-[#0d4a6f]'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                }`}
              >
                <AlertTriangle className="w-4 h-4" />
                Alerts
              </button>
              <button
                onClick={() => setActiveTab('messages')}
                className={`px-6 py-4 text-sm font-medium border-b-2 transition-colors flex items-center gap-2 ${
                  activeTab === 'messages'
                    ? 'border-[#0d4a6f] text-[#0d4a6f]'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                }`}
              >
                <MessageSquare className="w-4 h-4" />
                Chat Messages
              </button>
            </nav>
          </div>

          <div className="p-6">
            {/* Reports Tab */}
            {activeTab === 'reports' && (
              <div className="space-y-4">
                {/* Filters */}
                <div className="flex items-center gap-4">
                  <div className="flex items-center gap-2">
                    <Filter className="w-4 h-4 text-gray-500" />
                    <select
                      value={reportsStatusFilter}
                      onChange={(e) => {
                        setReportsStatusFilter(e.target.value);
                        setReportsPage(1);
                      }}
                      className="border border-gray-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
                    >
                      <option value="all">All Status</option>
                      <option value="pending">Pending</option>
                      <option value="verified">Verified</option>
                      <option value="rejected">Rejected</option>
                      <option value="auto_approved">Accepted by AI</option>
                      <option value="auto_rejected">Rejected by AI</option>
                      <option value="under_review">Under Review</option>
                    </select>
                  </div>
                </div>

                {/* Reports Table */}
                {reportsLoading ? (
                  <div className="text-center py-12">
                    <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-sky-500 mx-auto"></div>
                  </div>
                ) : reports.length === 0 ? (
                  <div className="text-center py-12 text-gray-500">
                    <FileText className="w-12 h-12 mx-auto mb-4 opacity-50" />
                    <p>No reports found</p>
                  </div>
                ) : (
                  <div className="overflow-x-auto">
                    <table className="w-full">
                      <thead className="bg-gray-50">
                        <tr>
                          <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Report ID</th>
                          <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Type</th>
                          <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Reporter</th>
                          <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Location</th>
                          <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Status</th>
                          <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Created</th>
                          <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Actions</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-gray-200">
                        {reports.map((report) => (
                          <tr key={report.report_id} className="hover:bg-gray-50">
                            <td className="px-4 py-3 text-sm font-mono text-gray-900">
                              {report.report_id?.substring(0, 12) || 'N/A'}
                            </td>
                            <td className="px-4 py-3 text-sm text-gray-600 capitalize">
                              {report.hazard_type?.replace(/_/g, ' ') || 'Unknown'}
                            </td>
                            <td className="px-4 py-3 text-sm text-gray-600">
                              {report.user_id?.substring(0, 10) || 'Anonymous'}
                            </td>
                            <td className="px-4 py-3 text-sm text-gray-600">
                              <div className="flex items-center gap-1">
                                <MapPin className="w-3 h-3" />
                                {report.location?.district || report.location?.state || 'Unknown'}
                              </div>
                            </td>
                            <td className="px-4 py-3">
                              <span className={`px-2 py-1 text-xs font-medium rounded-full ${getStatusBadge(report.verification_status || report.status)}`}>
                                {getStatusLabel(report.verification_status || report.status || 'pending')}
                              </span>
                            </td>
                            <td className="px-4 py-3 text-sm text-gray-500">
                              {formatDate(report.created_at)}
                            </td>
                            <td className="px-4 py-3">
                              <div className="flex items-center gap-2">
                                <button
                                  onClick={() => setSelectedReport(report)}
                                  className="p-1 text-gray-500 hover:text-sky-600 transition-colors"
                                  title="View Details"
                                >
                                  <Eye className="w-4 h-4" />
                                </button>
                                <button
                                  onClick={() => setDeleteConfirm({ type: 'report', id: report.report_id })}
                                  className="p-1 text-gray-500 hover:text-red-600 transition-colors"
                                  title="Delete"
                                >
                                  <Trash2 className="w-4 h-4" />
                                </button>
                              </div>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}

                {/* Pagination */}
                {reportsTotalPages > 1 && (
                  <div className="flex items-center justify-between pt-4">
                    <p className="text-sm text-gray-500">
                      Page {reportsPage} of {reportsTotalPages}
                    </p>
                    <div className="flex items-center gap-2">
                      <button
                        onClick={() => setReportsPage(p => Math.max(1, p - 1))}
                        disabled={reportsPage === 1}
                        className="p-2 border rounded-lg disabled:opacity-50 disabled:cursor-not-allowed hover:bg-gray-50"
                      >
                        <ChevronLeft className="w-4 h-4" />
                      </button>
                      <button
                        onClick={() => setReportsPage(p => Math.min(reportsTotalPages, p + 1))}
                        disabled={reportsPage === reportsTotalPages}
                        className="p-2 border rounded-lg disabled:opacity-50 disabled:cursor-not-allowed hover:bg-gray-50"
                      >
                        <ChevronRight className="w-4 h-4" />
                      </button>
                    </div>
                  </div>
                )}
              </div>
            )}

            {/* Alerts Tab */}
            {activeTab === 'alerts' && (
              <div className="space-y-4">
                {/* Filters */}
                <div className="flex items-center gap-4">
                  <div className="flex items-center gap-2">
                    <Filter className="w-4 h-4 text-gray-500" />
                    <select
                      value={alertsStatusFilter}
                      onChange={(e) => {
                        setAlertsStatusFilter(e.target.value);
                        setAlertsPage(1);
                      }}
                      className="border border-gray-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
                    >
                      <option value="all">All Status</option>
                      <option value="active">Active</option>
                      <option value="resolved">Resolved</option>
                      <option value="expired">Expired</option>
                    </select>
                  </div>
                  <select
                    value={alertsSeverityFilter}
                    onChange={(e) => {
                      setAlertsSeverityFilter(e.target.value);
                      setAlertsPage(1);
                    }}
                    className="border border-gray-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
                  >
                    <option value="all">All Severity</option>
                    <option value="critical">Critical</option>
                    <option value="high">High</option>
                    <option value="medium">Medium</option>
                    <option value="low">Low</option>
                  </select>
                </div>

                {/* Alerts Table */}
                {alertsLoading ? (
                  <div className="text-center py-12">
                    <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-sky-500 mx-auto"></div>
                  </div>
                ) : alerts.length === 0 ? (
                  <div className="text-center py-12 text-gray-500">
                    <AlertTriangle className="w-12 h-12 mx-auto mb-4 opacity-50" />
                    <p>No alerts found</p>
                  </div>
                ) : (
                  <div className="overflow-x-auto">
                    <table className="w-full">
                      <thead className="bg-gray-50">
                        <tr>
                          <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Alert ID</th>
                          <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Title</th>
                          <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Severity</th>
                          <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Status</th>
                          <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Issued By</th>
                          <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Created</th>
                          <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Actions</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-gray-200">
                        {alerts.map((alert) => (
                          <tr key={alert.alert_id} className="hover:bg-gray-50">
                            <td className="px-4 py-3 text-sm font-mono text-gray-900">
                              {alert.alert_id?.substring(0, 8)}...
                            </td>
                            <td className="px-4 py-3 text-sm text-gray-600">
                              {alert.title || 'Untitled Alert'}
                            </td>
                            <td className="px-4 py-3">
                              <span className={`px-2 py-1 text-xs font-medium rounded-full ${getSeverityBadge(alert.severity)}`}>
                                {alert.severity}
                              </span>
                            </td>
                            <td className="px-4 py-3">
                              <span className={`px-2 py-1 text-xs font-medium rounded-full ${getStatusBadge(alert.status)}`}>
                                {alert.status}
                              </span>
                            </td>
                            <td className="px-4 py-3 text-sm text-gray-600">
                              {alert.created_by || 'System'}
                            </td>
                            <td className="px-4 py-3 text-sm text-gray-500">
                              {formatDate(alert.created_at)}
                            </td>
                            <td className="px-4 py-3">
                              <div className="flex items-center gap-2">
                                <button
                                  onClick={() => setSelectedAlert(alert)}
                                  className="p-1 text-gray-500 hover:text-sky-600 transition-colors"
                                  title="View Details"
                                >
                                  <Eye className="w-4 h-4" />
                                </button>
                                <button
                                  onClick={() => setDeleteConfirm({ type: 'alert', id: alert.alert_id })}
                                  className="p-1 text-gray-500 hover:text-red-600 transition-colors"
                                  title="Delete"
                                >
                                  <Trash2 className="w-4 h-4" />
                                </button>
                              </div>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}

                {/* Pagination */}
                {alertsTotalPages > 1 && (
                  <div className="flex items-center justify-between pt-4">
                    <p className="text-sm text-gray-500">
                      Page {alertsPage} of {alertsTotalPages}
                    </p>
                    <div className="flex items-center gap-2">
                      <button
                        onClick={() => setAlertsPage(p => Math.max(1, p - 1))}
                        disabled={alertsPage === 1}
                        className="p-2 border rounded-lg disabled:opacity-50 disabled:cursor-not-allowed hover:bg-gray-50"
                      >
                        <ChevronLeft className="w-4 h-4" />
                      </button>
                      <button
                        onClick={() => setAlertsPage(p => Math.min(alertsTotalPages, p + 1))}
                        disabled={alertsPage === alertsTotalPages}
                        className="p-2 border rounded-lg disabled:opacity-50 disabled:cursor-not-allowed hover:bg-gray-50"
                      >
                        <ChevronRight className="w-4 h-4" />
                      </button>
                    </div>
                  </div>
                )}
              </div>
            )}

            {/* Messages Tab */}
            {activeTab === 'messages' && (
              <div className="space-y-4">
                {/* Messages Table */}
                {messagesLoading ? (
                  <div className="text-center py-12">
                    <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-sky-500 mx-auto"></div>
                  </div>
                ) : messages.length === 0 ? (
                  <div className="text-center py-12 text-gray-500">
                    <MessageSquare className="w-12 h-12 mx-auto mb-4 opacity-50" />
                    <p>No chat messages found</p>
                  </div>
                ) : (
                  <div className="space-y-3">
                    {messages.map((message) => (
                      <div
                        key={message.message_id}
                        className="bg-gray-50 rounded-lg p-4 flex items-start justify-between"
                      >
                        <div className="flex-1">
                          <div className="flex items-center gap-2 mb-2">
                            <User className="w-4 h-4 text-gray-500" />
                            <span className="font-medium text-gray-900">
                              {message.user_name || 'Unknown User'}
                            </span>
                            <span className="text-xs text-gray-500">
                              {formatDate(message.timestamp)}
                            </span>
                          </div>
                          <p className="text-gray-700">{message.content}</p>
                          {message.room_id && (
                            <p className="text-xs text-gray-500 mt-2">
                              Room: {message.room_id.substring(0, 8)}...
                            </p>
                          )}
                        </div>
                        <button
                          onClick={() => setDeleteConfirm({ type: 'message', id: message.message_id })}
                          className="p-2 text-gray-400 hover:text-red-600 transition-colors"
                          title="Delete Message"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </div>
                    ))}
                  </div>
                )}

                {/* Pagination */}
                {messagesTotalPages > 1 && (
                  <div className="flex items-center justify-between pt-4">
                    <p className="text-sm text-gray-500">
                      Page {messagesPage} of {messagesTotalPages}
                    </p>
                    <div className="flex items-center gap-2">
                      <button
                        onClick={() => setMessagesPage(p => Math.max(1, p - 1))}
                        disabled={messagesPage === 1}
                        className="p-2 border rounded-lg disabled:opacity-50 disabled:cursor-not-allowed hover:bg-gray-50"
                      >
                        <ChevronLeft className="w-4 h-4" />
                      </button>
                      <button
                        onClick={() => setMessagesPage(p => Math.min(messagesTotalPages, p + 1))}
                        disabled={messagesPage === messagesTotalPages}
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

      {/* Report Detail Modal */}
      {selectedReport && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-[60] p-4">
          <div className="bg-white rounded-xl max-w-2xl w-full max-h-[90vh] overflow-y-auto">
            <div className="p-6 border-b border-gray-200 flex items-center justify-between">
              <h2 className="text-xl font-semibold text-gray-900">Report Details</h2>
              <button
                onClick={() => setSelectedReport(null)}
                className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
              >
                <X className="w-5 h-5" />
              </button>
            </div>
            <div className="p-6 space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <p className="text-sm text-gray-500">Report ID</p>
                  <p className="font-mono text-sm">{selectedReport.report_id}</p>
                </div>
                <div>
                  <p className="text-sm text-gray-500">Status</p>
                  <span className={`px-2 py-1 text-xs font-medium rounded-full ${getStatusBadge(selectedReport.verification_status || selectedReport.status)}`}>
                    {getStatusLabel(selectedReport.verification_status || selectedReport.status || 'pending')}
                  </span>
                </div>
                <div>
                  <p className="text-sm text-gray-500">Hazard Type</p>
                  <p className="capitalize">{selectedReport.hazard_type?.replace('_', ' ')}</p>
                </div>
                <div>
                  <p className="text-sm text-gray-500">Reporter ID</p>
                  <p className="font-mono text-sm">{selectedReport.user_id || 'Anonymous'}</p>
                </div>
                <div>
                  <p className="text-sm text-gray-500">Created At</p>
                  <p>{formatDate(selectedReport.created_at)}</p>
                </div>
                <div>
                  <p className="text-sm text-gray-500">Location</p>
                  <p>{selectedReport.location?.district}, {selectedReport.location?.state}</p>
                </div>
                {selectedReport.risk_level && (
                  <div>
                    <p className="text-sm text-gray-500">Risk Level</p>
                    <span className={`px-2 py-1 text-xs font-medium rounded-full ${
                      selectedReport.risk_level === 'high' ? 'bg-red-100 text-red-700' :
                      selectedReport.risk_level === 'medium' ? 'bg-amber-100 text-amber-700' :
                      'bg-green-100 text-green-700'
                    }`}>
                      {selectedReport.risk_level}
                    </span>
                  </div>
                )}
                {selectedReport.verified_by && (
                  <div>
                    <p className="text-sm text-gray-500">Verified By</p>
                    <p className="font-mono text-sm">{selectedReport.verified_by}</p>
                  </div>
                )}
              </div>
              {selectedReport.description && (
                <div>
                  <p className="text-sm text-gray-500 mb-1">Description</p>
                  <p className="text-gray-700 bg-gray-50 rounded-lg p-3">{selectedReport.description}</p>
                </div>
              )}
              {selectedReport.image_url && (
                <div>
                  <p className="text-sm text-gray-500 mb-2">Media</p>
                  <div className="grid grid-cols-3 gap-2">
                    <img
                      src={getImageUrl(selectedReport.image_url)}
                      alt="Report Media"
                      className="w-full h-32 object-cover rounded-lg cursor-pointer hover:opacity-90 transition-opacity"
                      onClick={() => window.open(getImageUrl(selectedReport.image_url), '_blank')}
                    />
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Alert Detail Modal */}
      {selectedAlert && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-[60] p-4">
          <div className="bg-white rounded-xl max-w-2xl w-full max-h-[90vh] overflow-y-auto">
            <div className="p-6 border-b border-gray-200 flex items-center justify-between">
              <h2 className="text-xl font-semibold text-gray-900">Alert Details</h2>
              <button
                onClick={() => setSelectedAlert(null)}
                className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
              >
                <X className="w-5 h-5" />
              </button>
            </div>
            <div className="p-6 space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <p className="text-sm text-gray-500">Alert ID</p>
                  <p className="font-mono text-sm">{selectedAlert.alert_id}</p>
                </div>
                <div>
                  <p className="text-sm text-gray-500">Severity</p>
                  <span className={`px-2 py-1 text-xs font-medium rounded-full ${getSeverityBadge(selectedAlert.severity)}`}>
                    {selectedAlert.severity}
                  </span>
                </div>
                <div>
                  <p className="text-sm text-gray-500">Status</p>
                  <span className={`px-2 py-1 text-xs font-medium rounded-full ${getStatusBadge(selectedAlert.status)}`}>
                    {selectedAlert.status}
                  </span>
                </div>
                <div>
                  <p className="text-sm text-gray-500">Created By</p>
                  <p>{selectedAlert.created_by || 'System'}</p>
                </div>
                <div>
                  <p className="text-sm text-gray-500">Created At</p>
                  <p>{formatDate(selectedAlert.created_at)}</p>
                </div>
                <div>
                  <p className="text-sm text-gray-500">Expires At</p>
                  <p>{formatDate(selectedAlert.expires_at)}</p>
                </div>
              </div>
              <div>
                <p className="text-sm text-gray-500 mb-1">Title</p>
                <p className="text-lg font-medium">{selectedAlert.title}</p>
              </div>
              {selectedAlert.description && (
                <div>
                  <p className="text-sm text-gray-500 mb-1">Description</p>
                  <p className="text-gray-700 bg-gray-50 rounded-lg p-3">{selectedAlert.description}</p>
                </div>
              )}
              {selectedAlert.regions?.length > 0 && (
                <div>
                  <p className="text-sm text-gray-500 mb-2">Affected Regions</p>
                  <div className="flex flex-wrap gap-2">
                    {selectedAlert.regions.map((region, idx) => (
                      <span key={idx} className="px-3 py-1 bg-gray-100 rounded-full text-sm">
                        {region}
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Delete Confirmation Modal */}
      {deleteConfirm && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-[60] p-4">
          <div className="bg-white rounded-xl max-w-md w-full p-6">
            <div className="flex items-center gap-3 mb-4">
              <div className="p-3 bg-red-100 rounded-full">
                <AlertCircle className="w-6 h-6 text-red-600" />
              </div>
              <div>
                <h3 className="text-lg font-semibold text-gray-900">Confirm Delete</h3>
                <p className="text-sm text-gray-500">
                  Are you sure you want to delete this {deleteConfirm.type}?
                </p>
              </div>
            </div>
            <p className="text-sm text-gray-600 mb-6">
              This action cannot be undone. The {deleteConfirm.type} will be permanently removed from the system.
            </p>
            <div className="flex justify-end gap-3">
              <button
                onClick={() => setDeleteConfirm(null)}
                className="px-4 py-2 text-gray-700 border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={() => {
                  if (deleteConfirm.type === 'report') {
                    handleDeleteReport(deleteConfirm.id);
                  } else if (deleteConfirm.type === 'alert') {
                    handleDeleteAlert(deleteConfirm.id);
                  } else if (deleteConfirm.type === 'message') {
                    handleDeleteMessage(deleteConfirm.id);
                  }
                }}
                className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors"
              >
                Delete
              </button>
            </div>
          </div>
        </div>
      )}
    </DashboardLayout>
  );
}
