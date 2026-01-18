'use client';

import { useEffect, useState, Suspense } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import DashboardLayout from '@/components/DashboardLayout';
import PageHeader from '@/components/PageHeader';
import useAuthStore from '@/context/AuthContext';
import api, { getImageUrl } from '@/lib/api';
import {
  AlertTriangle,
  CheckCircle,
  XCircle,
  Clock,
  Filter,
  Search,
  ChevronRight,
  MapPin,
  Calendar,
  User,
  TrendingUp,
  AlertCircle,
  Gauge,
  Zap,
  Ticket
} from 'lucide-react';

// Loading fallback component
function LoadingFallback() {
  return (
    <DashboardLayout>
      <div className="flex items-center justify-center min-h-screen">
        <div className="animate-spin rounded-full h-12 w-12 border-t-4 border-b-4 border-[#0d4a6f]"></div>
      </div>
    </DashboardLayout>
  );
}

// Main verification panel component
function VerificationPanelContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { user, isLoading: authLoading } = useAuthStore();

  const [reports, setReports] = useState([]);
  const [summary, setSummary] = useState(null);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');

  // Filters
  const [statusFilter, setStatusFilter] = useState(searchParams.get('status') || 'pending');
  const [priorityFilter, setPriorityFilter] = useState(searchParams.get('priority') || 'all');
  const [typeFilter, setTypeFilter] = useState('all');
  const [sortBy, setSortBy] = useState('newest');

  // Pagination
  const [page, setPage] = useState(1);
  const [totalCount, setTotalCount] = useState(0);
  const limit = 20;

  // Check if user is authority or admin
  useEffect(() => {
    if (!authLoading && user) {
      if (user.role !== 'authority' && user.role !== 'authority_admin') {
        router.push('/dashboard');
      } else {
        fetchData();
      }
    }
  }, [user, authLoading, statusFilter, priorityFilter, typeFilter, sortBy, page]);

  const fetchData = async () => {
    try {
      setLoading(true);

      // Fetch summary stats
      const summaryResponse = await api.get('/authority/verification-panel/summary');
      setSummary(summaryResponse.data);

      // Fetch reports with filters
      const params = {
        skip: (page - 1) * limit,
        limit: limit,
        sort_by: sortBy
      };

      if (statusFilter !== 'all') params.verification_status = statusFilter;
      if (priorityFilter !== 'all') params.priority = priorityFilter;
      if (typeFilter !== 'all') params.hazard_type = typeFilter;
      if (searchQuery) params.search = searchQuery;

      const reportsResponse = await api.get('/authority/verification-panel/reports', { params });
      setReports(reportsResponse.data.reports);
      setTotalCount(reportsResponse.data.total);

    } catch (error) {
      console.error('Error fetching verification data:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleSearch = () => {
    setPage(1);
    fetchData();
  };

  const getPriorityColor = (priority) => {
    switch (priority) {
      case 'high': return 'text-red-600 bg-red-100';
      case 'medium': return 'text-orange-600 bg-orange-100';
      case 'low': return 'text-yellow-600 bg-yellow-100';
      default: return 'text-gray-600 bg-gray-100';
    }
  };

  const getStatusColor = (status) => {
    switch (status) {
      case 'verified': return 'text-green-600 bg-green-100';
      case 'rejected': return 'text-red-600 bg-red-100';
      case 'auto_approved': return 'text-[#0d4a6f] bg-[#e8f4fc]';
      case 'auto_rejected': return 'text-purple-600 bg-purple-100';
      case 'pending': return 'text-orange-600 bg-orange-100';
      default: return 'text-gray-600 bg-gray-100';
    }
  };

  const getStatusLabel = (status) => {
    switch (status) {
      case 'auto_approved': return 'Accepted by AI';
      case 'auto_rejected': return 'Rejected by AI';
      default: return status;
    }
  };

  const getRiskColor = (risk) => {
    switch (risk) {
      case 'critical': return 'text-red-700 bg-red-100';
      case 'high': return 'text-red-600 bg-red-50';
      case 'medium': return 'text-orange-600 bg-orange-50';
      case 'low': return 'text-yellow-600 bg-yellow-50';
      default: return 'text-gray-600 bg-gray-50';
    }
  };

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
          <h1 className="text-2xl font-bold mb-2 relative z-10">Verification Panel</h1>
          <p className="text-[#9ecbec] relative z-10">
            Review and verify citizen-submitted hazard reports
          </p>
        </div>

        {/* Summary Stats */}
        {summary && (
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <div className="bg-white rounded-xl shadow-sm border border-orange-200 p-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-gray-600">Pending</p>
                  <p className="text-2xl font-bold text-orange-600">{summary.pending}</p>
                </div>
                <Clock className="w-8 h-8 text-orange-600 opacity-50" />
              </div>
            </div>

            <div className="bg-white rounded-xl shadow-sm border border-red-200 p-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-gray-600">High Priority</p>
                  <p className="text-2xl font-bold text-red-600">{summary.high_priority}</p>
                </div>
                <AlertTriangle className="w-8 h-8 text-red-600 opacity-50" />
              </div>
            </div>

            <div className="bg-white rounded-xl shadow-sm border border-green-200 p-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-gray-600">Verified</p>
                  <p className="text-2xl font-bold text-green-600">{summary.verified}</p>
                </div>
                <CheckCircle className="w-8 h-8 text-green-600 opacity-50" />
              </div>
            </div>

            <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-gray-600">Rejected</p>
                  <p className="text-2xl font-bold text-gray-600">{summary.rejected}</p>
                </div>
                <XCircle className="w-8 h-8 text-gray-600 opacity-50" />
              </div>
            </div>
          </div>
        )}

        {/* Filters and Search */}
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4">
          <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
            {/* Search */}
            <div className="md:col-span-2">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-gray-400" />
                <input
                  type="text"
                  placeholder="Search reports..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  onKeyPress={(e) => e.key === 'Enter' && handleSearch()}
                  className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-xl focus:ring-2 focus:ring-[#1a6b9a] focus:border-transparent"
                />
              </div>
            </div>

            {/* Status Filter */}
            <select
              value={statusFilter}
              onChange={(e) => { setStatusFilter(e.target.value); setPage(1); }}
              className="px-4 py-2 border border-gray-300 rounded-xl focus:ring-2 focus:ring-[#1a6b9a]"
            >
              <option value="all">All Status</option>
              <option value="pending">Pending</option>
              <option value="verified">Verified</option>
              <option value="rejected">Rejected</option>
              <option value="auto_approved">Accepted by AI</option>
              <option value="auto_rejected">Rejected by AI</option>
            </select>

            {/* Priority Filter */}
            <select
              value={priorityFilter}
              onChange={(e) => { setPriorityFilter(e.target.value); setPage(1); }}
              className="px-4 py-2 border border-gray-300 rounded-xl focus:ring-2 focus:ring-[#1a6b9a]"
            >
              <option value="all">All Priority</option>
              <option value="high">High</option>
              <option value="medium">Medium</option>
              <option value="low">Low</option>
            </select>

            {/* Sort By */}
            <select
              value={sortBy}
              onChange={(e) => { setSortBy(e.target.value); setPage(1); }}
              className="px-4 py-2 border border-gray-300 rounded-xl focus:ring-2 focus:ring-[#1a6b9a]"
            >
              <option value="newest">Newest First</option>
              <option value="oldest">Oldest First</option>
              <option value="priority">High Priority</option>
              <option value="risk">High Risk</option>
            </select>
          </div>
        </div>

        {/* Reports List */}
        <div className="bg-white rounded-lg shadow-sm border border-gray-200">
          <div className="px-6 py-4 border-b border-gray-200">
            <h2 className="text-lg font-semibold text-gray-900">
              Reports ({totalCount})
            </h2>
          </div>

          <div className="divide-y divide-gray-200">
            {reports.length === 0 ? (
              <div className="p-12 text-center">
                <AlertCircle className="w-12 h-12 text-gray-400 mx-auto mb-4" />
                <p className="text-gray-600">No reports found matching your filters</p>
              </div>
            ) : (
              reports.map((report) => (
                <div
                  key={report.report_id}
                  onClick={() => router.push(`/authority/verification/${report.report_id}`)}
                  className="p-6 hover:bg-gray-50 cursor-pointer transition-colors"
                >
                  <div className="flex items-start gap-4">
                    {/* Hazard Image */}
                    <div className="flex-shrink-0">
                      <div className="relative w-40 h-32 rounded-lg overflow-hidden bg-gray-100 border-2 border-gray-200 shadow-sm">
                        {report.image_url ? (
                          <img
                            src={getImageUrl(report.image_url)}
                            alt={report.hazard_type}
                            className="w-full h-full object-cover"
                            onError={(e) => {
                              e.target.onerror = null;
                              e.target.src = 'data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMjAwIiBoZWlnaHQ9IjIwMCIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48cmVjdCB3aWR0aD0iMjAwIiBoZWlnaHQ9IjIwMCIgZmlsbD0iI2VlZSIvPjx0ZXh0IHg9IjUwJSIgeT0iNTAlIiBmb250LWZhbWlseT0iQXJpYWwiIGZvbnQtc2l6ZT0iMTQiIGZpbGw9IiM5OTkiIHRleHQtYW5jaG9yPSJtaWRkbGUiIGR5PSIuM2VtIj5ObyBJbWFnZTwvdGV4dD48L3N2Zz4=';
                            }}
                          />
                        ) : (
                          <div className="w-full h-full flex items-center justify-center">
                            <div className="text-center">
                              <AlertTriangle className="w-8 h-8 text-gray-400 mx-auto mb-1" />
                              <span className="text-xs text-gray-500">No Image</span>
                            </div>
                          </div>
                        )}

                        {/* Image Badge */}
                        {report.voice_note_url && (
                          <div className="absolute top-2 right-2 bg-[#0d4a6f] text-white rounded-full p-1.5 shadow-md" title="Has voice note">
                            <svg className="w-3 h-3" fill="currentColor" viewBox="0 0 20 20">
                              <path fillRule="evenodd" d="M7 4a3 3 0 016 0v4a3 3 0 11-6 0V4zm4 10.93A7.001 7.001 0 0017 8a1 1 0 10-2 0A5 5 0 015 8a1 1 0 00-2 0 7.001 7.001 0 006 6.93V17H6a1 1 0 100 2h8a1 1 0 100-2h-3v-2.07z" clipRule="evenodd" />
                            </svg>
                          </div>
                        )}
                      </div>
                    </div>

                    {/* Report Details */}
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-3 mb-2 flex-wrap">
                        <h3 className="text-lg font-semibold text-gray-900">
                          {report.hazard_type.replace('_', ' ').toUpperCase()}
                        </h3>

                        {/* Verification Score Badge - PROMINENT */}
                        {report.verification_score !== undefined && report.verification_score !== null && (
                          <span className={`px-3 py-1 text-sm font-bold rounded-full flex items-center gap-1 ${
                            report.verification_score >= 75 ? 'bg-green-100 text-green-700 ring-2 ring-green-300' :
                            report.verification_score >= 40 ? 'bg-yellow-100 text-yellow-700 ring-2 ring-yellow-300' :
                            'bg-red-100 text-red-700 ring-2 ring-red-300'
                          }`}>
                            <Gauge className="w-4 h-4" />
                            {report.verification_score.toFixed(1)}%
                          </span>
                        )}

                        {/* Status Badge */}
                        <span className={`px-2 py-1 text-xs font-medium rounded-full ${getStatusColor(report.verification_status)}`}>
                          {getStatusLabel(report.verification_status)}
                        </span>

                        {/* Priority Badge */}
                        {report.priority && (
                          <span className={`px-2 py-1 text-xs font-medium rounded-full ${getPriorityColor(report.priority)}`}>
                            {report.priority} priority
                          </span>
                        )}

                        {/* Risk Badge */}
                        {report.risk_level && (
                          <span className={`px-2 py-1 text-xs font-medium rounded-full ${getRiskColor(report.risk_level)}`}>
                            {report.risk_level} risk
                          </span>
                        )}

                        {/* Threat Level Badge */}
                        {report.hazard_classification?.threat_level && report.hazard_classification.threat_level !== 'no_threat' && (
                          <span className={`px-2 py-1 text-xs font-medium rounded-full flex items-center gap-1 ${
                            report.hazard_classification.threat_level === 'warning' ? 'bg-red-200 text-red-800' :
                            report.hazard_classification.threat_level === 'alert' ? 'bg-orange-200 text-orange-800' :
                            'bg-yellow-200 text-yellow-800'
                          }`}>
                            <Zap className="w-3 h-3" />
                            {report.hazard_classification.threat_level}
                          </span>
                        )}

                        {/* Ticket Badge */}
                        {report.has_ticket && (
                          <span className="px-2 py-1 text-xs font-medium rounded-full bg-indigo-100 text-indigo-700 flex items-center gap-1">
                            <Ticket className="w-3 h-3" />
                            Ticket
                          </span>
                        )}
                      </div>

                      {/* Description */}
                      <p className="text-gray-700 mb-3 line-clamp-2">
                        {report.description}
                      </p>

                      {/* Meta Info */}
                      <div className="flex items-center gap-4 text-sm text-gray-600 flex-wrap">
                        <div className="flex items-center gap-1">
                          <MapPin className="w-4 h-4" />
                          <span className="truncate max-w-xs" title={report.location?.address}>
                            {report.location?.region ||
                             report.location?.district ||
                             report.location?.address ||
                             `${report.location?.latitude?.toFixed(4)}, ${report.location?.longitude?.toFixed(4)}` ||
                             'Unknown'}
                          </span>
                        </div>
                        <div className="flex items-center gap-1">
                          <User className="w-4 h-4" />
                          <span>{report.reporter_name || 'Anonymous'}</span>
                        </div>
                        <div className="flex items-center gap-1">
                          <Calendar className="w-4 h-4" />
                          <span>{new Date(report.created_at).toLocaleDateString()}</span>
                        </div>
                        {report.nlp_risk_score && (
                          <div className="flex items-center gap-1">
                            <TrendingUp className="w-4 h-4" />
                            <span>NLP Score: {(report.nlp_risk_score * 100).toFixed(0)}%</span>
                          </div>
                        )}
                      </div>

                      {/* NLP Insights */}
                      {report.nlp_keywords && report.nlp_keywords.length > 0 && (
                        <div className="mt-2 flex items-center gap-2">
                          <span className="text-xs text-gray-500">Keywords:</span>
                          <div className="flex gap-1 flex-wrap">
                            {report.nlp_keywords.slice(0, 5).map((keyword, idx) => (
                              <span
                                key={idx}
                                className="px-2 py-0.5 text-xs bg-blue-100 text-blue-700 rounded"
                              >
                                {keyword}
                              </span>
                            ))}
                          </div>
                        </div>
                      )}
                    </div>

                    {/* Right Side - Action */}
                    <div className="flex-shrink-0">
                      <ChevronRight className="w-5 h-5 text-gray-400" />
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
                Showing {(page - 1) * limit + 1} to {Math.min(page * limit, totalCount)} of {totalCount} reports
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

// Default export with Suspense boundary
export default function VerificationPanel() {
  return (
    <Suspense fallback={<LoadingFallback />}>
      <VerificationPanelContent />
    </Suspense>
  );
}
