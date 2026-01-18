'use client';

import { useState, useEffect } from 'react';
import ProtectedRoute from '@/components/ProtectedRoute';
import DashboardLayout from '@/components/DashboardLayout';
import PageHeader from '@/components/PageHeader';
import {
  Users,
  CheckCircle,
  XCircle,
  Clock,
  Eye,
  FileText,
  Loader2,
  Search,
  Filter,
  ChevronLeft,
  ChevronRight,
  Award,
  MapPin,
  Mail,
  Phone,
  Calendar,
  AlertTriangle
} from 'lucide-react';
import {
  getOrganizerApplications,
  getOrganizerApplicationDetail,
  approveOrganizerApplication,
  rejectOrganizerApplication,
  getOrganizerStatistics
} from '@/lib/api';
import { formatDateIST, formatDateTimeIST } from '@/lib/dateUtils';
import toast from 'react-hot-toast';

function OrganizerApplicationsContent() {
  // State
  const [applications, setApplications] = useState([]);
  const [stats, setStats] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(0);
  const [statusFilter, setStatusFilter] = useState('pending');
  const limit = 10;

  // Detail modal state
  const [selectedApp, setSelectedApp] = useState(null);
  const [isLoadingDetail, setIsLoadingDetail] = useState(false);
  const [showDetailModal, setShowDetailModal] = useState(false);

  // Action state
  const [isProcessing, setIsProcessing] = useState(false);
  const [rejectionReason, setRejectionReason] = useState('');
  const [showRejectModal, setShowRejectModal] = useState(false);

  // Load applications
  const loadApplications = async () => {
    try {
      setIsLoading(true);
      const response = await getOrganizerApplications({
        status_filter: statusFilter || undefined,
        skip: page * limit,
        limit
      });
      setApplications(response.applications || []);
      setTotal(response.total || 0);
    } catch (error) {
      console.error('Error loading applications:', error);
      toast.error('Failed to load applications');
    } finally {
      setIsLoading(false);
    }
  };

  // Load statistics
  const loadStats = async () => {
    try {
      const response = await getOrganizerStatistics();
      setStats(response.statistics);
    } catch (error) {
      console.error('Error loading statistics:', error);
    }
  };

  useEffect(() => {
    loadApplications();
    loadStats();
  }, [statusFilter, page]);

  // View application detail
  const viewDetail = async (applicationId) => {
    try {
      setIsLoadingDetail(true);
      setShowDetailModal(true);
      const response = await getOrganizerApplicationDetail(applicationId);
      setSelectedApp(response.application);
    } catch (error) {
      console.error('Error loading detail:', error);
      toast.error('Failed to load application details');
      setShowDetailModal(false);
    } finally {
      setIsLoadingDetail(false);
    }
  };

  // Approve application
  const handleApprove = async (applicationId) => {
    if (!confirm('Are you sure you want to approve this application? The user will become a Verified Organizer.')) {
      return;
    }

    try {
      setIsProcessing(true);
      await approveOrganizerApplication(applicationId);
      toast.success('Application approved successfully!');
      setShowDetailModal(false);
      loadApplications();
      loadStats();
    } catch (error) {
      console.error('Error approving:', error);
      toast.error(error.response?.data?.detail || 'Failed to approve application');
    } finally {
      setIsProcessing(false);
    }
  };

  // Reject application
  const handleReject = async () => {
    if (!rejectionReason || rejectionReason.length < 10) {
      toast.error('Please provide a detailed rejection reason (at least 10 characters)');
      return;
    }

    try {
      setIsProcessing(true);
      await rejectOrganizerApplication(selectedApp.application_id, rejectionReason);
      toast.success('Application rejected');
      setShowRejectModal(false);
      setShowDetailModal(false);
      setRejectionReason('');
      loadApplications();
      loadStats();
    } catch (error) {
      console.error('Error rejecting:', error);
      toast.error(error.response?.data?.detail || 'Failed to reject application');
    } finally {
      setIsProcessing(false);
    }
  };

  // Status badge component
  const StatusBadge = ({ status }) => {
    const config = {
      pending: { bg: 'bg-yellow-100', text: 'text-yellow-800', label: 'Pending' },
      approved: { bg: 'bg-green-100', text: 'text-green-800', label: 'Approved' },
      rejected: { bg: 'bg-red-100', text: 'text-red-800', label: 'Rejected' }
    };
    const c = config[status] || config.pending;
    return (
      <span className={`px-2 py-1 rounded-full text-xs font-medium ${c.bg} ${c.text}`}>
        {c.label}
      </span>
    );
  };

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <PageHeader />
      
      {/* Header */}
      <div className="bg-gradient-to-r from-[#0d4a6f] to-[#083a57] rounded-2xl shadow-lg p-6 text-white relative overflow-hidden">
        <div className="absolute bottom-0 left-0 right-0 opacity-10">
          <svg viewBox="0 0 1440 120" className="w-full h-12">
            <path fill="white" d="M0,32L48,37.3C96,43,192,53,288,58.7C384,64,480,64,576,58.7C672,53,768,43,864,42.7C960,43,1056,53,1152,58.7C1248,64,1344,64,1392,64L1440,64L1440,120L1392,120C1344,120,1248,120,1152,120C1056,120,960,120,864,120C768,120,672,120,576,120C480,120,384,120,288,120C192,120,96,120,48,120L0,120Z"></path>
          </svg>
        </div>
        <div className="relative z-10">
          <h1 className="text-2xl font-bold flex items-center gap-3">
            <div className="p-2 bg-white/20 rounded-xl backdrop-blur-sm">
              <Users className="w-6 h-6" />
            </div>
            Organizer Applications
          </h1>
          <p className="text-[#9ecbec] mt-1">Review and manage organizer applications</p>
        </div>
      </div>

      {/* Stats Cards */}
      {stats && (
        <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
          <div className="bg-white rounded-xl shadow p-4">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-[#e8f4fc] rounded-lg">
                <Users className="h-5 w-5 text-[#0d4a6f]" />
              </div>
              <div>
                <p className="text-2xl font-bold text-gray-800">{stats.total}</p>
                <p className="text-sm text-gray-500">Total</p>
              </div>
            </div>
          </div>
          <div className="bg-white rounded-xl shadow p-4">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-yellow-100 rounded-lg">
                <Clock className="h-5 w-5 text-yellow-600" />
              </div>
              <div>
                <p className="text-2xl font-bold text-gray-800">{stats.pending}</p>
                <p className="text-sm text-gray-500">Pending</p>
              </div>
            </div>
          </div>
          <div className="bg-white rounded-xl shadow p-4">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-green-100 rounded-lg">
                <CheckCircle className="h-5 w-5 text-green-600" />
              </div>
              <div>
                <p className="text-2xl font-bold text-gray-800">{stats.approved}</p>
                <p className="text-sm text-gray-500">Approved</p>
              </div>
            </div>
          </div>
          <div className="bg-white rounded-xl shadow p-4">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-red-100 rounded-lg">
                <XCircle className="h-5 w-5 text-red-600" />
              </div>
              <div>
                <p className="text-2xl font-bold text-gray-800">{stats.rejected}</p>
                <p className="text-sm text-gray-500">Rejected</p>
              </div>
            </div>
          </div>
          <div className="bg-white rounded-xl shadow p-4">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-purple-100 rounded-lg">
                <Award className="h-5 w-5 text-purple-600" />
              </div>
              <div>
                <p className="text-2xl font-bold text-gray-800">{stats.active_organizers}</p>
                <p className="text-sm text-gray-500">Active Organizers</p>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Filters */}
      <div className="bg-white rounded-xl shadow p-4">
        <div className="flex flex-wrap gap-4 items-center">
          <div className="flex items-center gap-2">
            <Filter className="h-4 w-4 text-gray-500" />
            <span className="text-sm text-gray-600">Filter by Status:</span>
          </div>
          <div className="flex gap-2">
            {['all', 'pending', 'approved', 'rejected'].map((status) => (
              <button
                key={status}
                onClick={() => { setStatusFilter(status === 'all' ? '' : status); setPage(0); }}
                className={`px-4 py-2 rounded-lg text-sm font-medium transition ${
                  (status === 'all' && !statusFilter) || statusFilter === status
                    ? 'bg-blue-600 text-white'
                    : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                }`}
              >
                {status.charAt(0).toUpperCase() + status.slice(1)}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Applications Table */}
      <div className="bg-white rounded-xl shadow overflow-hidden">
        {isLoading ? (
          <div className="flex items-center justify-center py-12">
            <Loader2 className="h-8 w-8 animate-spin text-blue-500" />
          </div>
        ) : applications.length === 0 ? (
          <div className="text-center py-12">
            <Users className="h-12 w-12 text-gray-400 mx-auto mb-4" />
            <p className="text-gray-600">No applications found</p>
          </div>
        ) : (
          <>
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead className="bg-gray-50 border-b">
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Applicant</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Location</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Credibility</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Status</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Applied</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-200">
                  {applications.map((app) => (
                    <tr key={app.application_id} className="hover:bg-gray-50">
                      <td className="px-6 py-4">
                        <div>
                          <p className="font-medium text-gray-800">{app.name}</p>
                          <p className="text-sm text-gray-500">{app.email}</p>
                        </div>
                      </td>
                      <td className="px-6 py-4">
                        <div className="flex items-center gap-1 text-gray-600">
                          <MapPin className="h-4 w-4" />
                          <span>{app.coastal_zone}, {app.state}</span>
                        </div>
                      </td>
                      <td className="px-6 py-4">
                        <span className={`font-medium ${app.credibility_at_application >= 80 ? 'text-green-600' : 'text-orange-600'}`}>
                          {app.credibility_at_application}
                        </span>
                      </td>
                      <td className="px-6 py-4">
                        <StatusBadge status={app.status} />
                      </td>
                      <td className="px-6 py-4 text-sm text-gray-600">
                        {formatDateIST(app.applied_at)}
                      </td>
                      <td className="px-6 py-4">
                        <button
                          onClick={() => viewDetail(app.application_id)}
                          className="flex items-center gap-1 px-3 py-1.5 bg-blue-100 text-blue-700 rounded-lg hover:bg-blue-200 transition text-sm"
                        >
                          <Eye className="h-4 w-4" />
                          View
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {/* Pagination */}
            <div className="px-6 py-4 border-t flex items-center justify-between">
              <p className="text-sm text-gray-600">
                Showing {page * limit + 1} to {Math.min((page + 1) * limit, total)} of {total} applications
              </p>
              <div className="flex gap-2">
                <button
                  onClick={() => setPage(p => Math.max(0, p - 1))}
                  disabled={page === 0}
                  className="p-2 rounded-lg bg-gray-100 hover:bg-gray-200 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  <ChevronLeft className="h-4 w-4" />
                </button>
                <button
                  onClick={() => setPage(p => p + 1)}
                  disabled={(page + 1) * limit >= total}
                  className="p-2 rounded-lg bg-gray-100 hover:bg-gray-200 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  <ChevronRight className="h-4 w-4" />
                </button>
              </div>
            </div>
          </>
        )}
      </div>

      {/* Detail Modal */}
      {showDetailModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-xl shadow-xl max-w-2xl w-full max-h-[90vh] overflow-y-auto">
            {isLoadingDetail ? (
              <div className="flex items-center justify-center py-20">
                <Loader2 className="h-8 w-8 animate-spin text-blue-500" />
              </div>
            ) : selectedApp && (
              <>
                <div className="p-6 border-b">
                  <div className="flex items-center justify-between">
                    <div>
                      <h2 className="text-xl font-bold text-gray-800">Application Details</h2>
                      <p className="text-sm text-gray-500">{selectedApp.application_id}</p>
                    </div>
                    <StatusBadge status={selectedApp.status} />
                  </div>
                </div>

                <div className="p-6 space-y-6">
                  {/* Personal Info */}
                  <div>
                    <h3 className="text-sm font-medium text-gray-500 uppercase mb-3">Personal Information</h3>
                    <div className="grid grid-cols-2 gap-4">
                      <div className="flex items-center gap-3">
                        <Users className="h-5 w-5 text-gray-400" />
                        <div>
                          <p className="text-sm text-gray-500">Name</p>
                          <p className="font-medium">{selectedApp.name}</p>
                        </div>
                      </div>
                      <div className="flex items-center gap-3">
                        <Mail className="h-5 w-5 text-gray-400" />
                        <div>
                          <p className="text-sm text-gray-500">Email</p>
                          <p className="font-medium">{selectedApp.email}</p>
                        </div>
                      </div>
                      <div className="flex items-center gap-3">
                        <Phone className="h-5 w-5 text-gray-400" />
                        <div>
                          <p className="text-sm text-gray-500">Phone</p>
                          <p className="font-medium">{selectedApp.phone}</p>
                        </div>
                      </div>
                      <div className="flex items-center gap-3">
                        <Award className="h-5 w-5 text-gray-400" />
                        <div>
                          <p className="text-sm text-gray-500">Credibility Score</p>
                          <p className={`font-medium ${selectedApp.credibility_at_application >= 80 ? 'text-green-600' : 'text-orange-600'}`}>
                            {selectedApp.credibility_at_application}
                          </p>
                        </div>
                      </div>
                    </div>
                  </div>

                  {/* Location */}
                  <div>
                    <h3 className="text-sm font-medium text-gray-500 uppercase mb-3">Location</h3>
                    <div className="grid grid-cols-2 gap-4">
                      <div className="flex items-center gap-3">
                        <MapPin className="h-5 w-5 text-gray-400" />
                        <div>
                          <p className="text-sm text-gray-500">Coastal Zone</p>
                          <p className="font-medium">{selectedApp.coastal_zone}</p>
                        </div>
                      </div>
                      <div>
                        <p className="text-sm text-gray-500">State</p>
                        <p className="font-medium">{selectedApp.state}</p>
                      </div>
                    </div>
                  </div>

                  {/* Aadhaar Document */}
                  <div>
                    <h3 className="text-sm font-medium text-gray-500 uppercase mb-3">Identity Document</h3>
                    <a
                      href={`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1'}/organizer/admin/applications/${selectedApp.application_id}/aadhaar`}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="inline-flex items-center gap-2 px-4 py-2 bg-gray-100 hover:bg-gray-200 rounded-lg transition"
                    >
                      <FileText className="h-5 w-5 text-gray-600" />
                      View Aadhaar Document
                    </a>
                  </div>

                  {/* Timeline */}
                  <div>
                    <h3 className="text-sm font-medium text-gray-500 uppercase mb-3">Timeline</h3>
                    <div className="space-y-2">
                      <div className="flex items-center gap-3">
                        <Calendar className="h-5 w-5 text-gray-400" />
                        <div>
                          <p className="text-sm text-gray-500">Applied</p>
                          <p className="font-medium">{formatDateTimeIST(selectedApp.applied_at)}</p>
                        </div>
                      </div>
                      {selectedApp.reviewed_at && (
                        <div className="flex items-center gap-3">
                          <CheckCircle className="h-5 w-5 text-gray-400" />
                          <div>
                            <p className="text-sm text-gray-500">Reviewed by {selectedApp.reviewed_by_name}</p>
                            <p className="font-medium">{formatDateTimeIST(selectedApp.reviewed_at)}</p>
                          </div>
                        </div>
                      )}
                    </div>
                  </div>

                  {/* Rejection Reason */}
                  {selectedApp.status === 'rejected' && selectedApp.rejection_reason && (
                    <div className="bg-red-50 border border-red-200 rounded-lg p-4">
                      <div className="flex items-start gap-3">
                        <AlertTriangle className="h-5 w-5 text-red-600 mt-0.5" />
                        <div>
                          <p className="font-medium text-red-800">Rejection Reason</p>
                          <p className="text-red-700 mt-1">{selectedApp.rejection_reason}</p>
                        </div>
                      </div>
                    </div>
                  )}
                </div>

                {/* Actions */}
                <div className="p-6 border-t bg-gray-50 flex gap-3 justify-end">
                  <button
                    onClick={() => setShowDetailModal(false)}
                    className="px-4 py-2 text-gray-600 hover:text-gray-800 transition"
                  >
                    Close
                  </button>
                  {selectedApp.status === 'pending' && (
                    <>
                      <button
                        onClick={() => setShowRejectModal(true)}
                        disabled={isProcessing}
                        className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition disabled:opacity-50"
                      >
                        Reject
                      </button>
                      <button
                        onClick={() => handleApprove(selectedApp.application_id)}
                        disabled={isProcessing}
                        className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition disabled:opacity-50 flex items-center gap-2"
                      >
                        {isProcessing ? <Loader2 className="h-4 w-4 animate-spin" /> : <CheckCircle className="h-4 w-4" />}
                        Approve
                      </button>
                    </>
                  )}
                </div>
              </>
            )}
          </div>
        </div>
      )}

      {/* Reject Modal */}
      {showRejectModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-xl shadow-xl max-w-md w-full">
            <div className="p-6 border-b">
              <h2 className="text-xl font-bold text-gray-800">Reject Application</h2>
              <p className="text-sm text-gray-500 mt-1">Please provide a reason for rejection</p>
            </div>
            <div className="p-6">
              <textarea
                value={rejectionReason}
                onChange={(e) => setRejectionReason(e.target.value)}
                className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-500 focus:border-red-500 resize-none"
                rows={4}
                placeholder="Enter detailed reason for rejection..."
              />
              <p className="text-sm text-gray-500 mt-2">Minimum 10 characters required</p>
            </div>
            <div className="p-6 border-t bg-gray-50 flex gap-3 justify-end">
              <button
                onClick={() => { setShowRejectModal(false); setRejectionReason(''); }}
                className="px-4 py-2 text-gray-600 hover:text-gray-800 transition"
              >
                Cancel
              </button>
              <button
                onClick={handleReject}
                disabled={isProcessing || rejectionReason.length < 10}
                className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition disabled:opacity-50 flex items-center gap-2"
              >
                {isProcessing ? <Loader2 className="h-4 w-4 animate-spin" /> : <XCircle className="h-4 w-4" />}
                Reject Application
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default function OrganizerApplicationsPage() {
  return (
    <ProtectedRoute requiredRole="authority_admin">
      <DashboardLayout>
        <div className="py-6 px-4">
          <OrganizerApplicationsContent />
        </div>
      </DashboardLayout>
    </ProtectedRoute>
  );
}
