'use client';

import { useState, useEffect, useCallback, Suspense } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import useAuthStore from '@/context/AuthContext';
import DashboardLayout from '@/components/DashboardLayout';
import PageHeader from '@/components/PageHeader';
import VerificationStatus, { VerificationBadge } from '@/components/VerificationStatus';
import LayerBreakdown from '@/components/LayerBreakdown';
import useVerification, { useVerificationHealth } from '@/hooks/useVerification';
import { getAnalystReports, getAnalystReportDetail, getUploadUrl, getVerificationDetails } from '@/lib/api';
import {
  Search,
  Filter,
  RefreshCw,
  ChevronLeft,
  ChevronRight,
  ChevronDown,
  X,
  FileText,
  MapPin,
  Calendar,
  AlertTriangle,
  CheckCircle2,
  Clock,
  XCircle,
  Eye,
  Download,
  SortAsc,
  SortDesc,
  Loader2,
  AlertCircle,
  Image as ImageIcon,
  User,
  Tag,
  LayoutGrid,
  LayoutList,
  Gauge,
  Zap,
  Ticket,
  Activity,
  Shield,
  ThumbsUp,
  ThumbsDown,
  RotateCcw,
  TrendingUp,
  TrendingDown,
  ExternalLink,
  Bell,
  CheckCheck
} from 'lucide-react';
import toast from 'react-hot-toast';
import { ExportButton } from '@/components/export';

const severityColors = {
  critical: { bg: 'bg-red-100', text: 'text-red-700', border: 'border-red-200', dot: 'bg-red-500' },
  high: { bg: 'bg-orange-100', text: 'text-orange-700', border: 'border-orange-200', dot: 'bg-orange-500' },
  medium: { bg: 'bg-amber-100', text: 'text-amber-700', border: 'border-amber-200', dot: 'bg-amber-500' },
  low: { bg: 'bg-green-100', text: 'text-green-700', border: 'border-green-200', dot: 'bg-green-500' }
};

const statusConfig = {
  pending: { icon: Clock, color: 'text-amber-600', bg: 'bg-amber-100', label: 'Pending' },
  verified: { icon: CheckCircle2, color: 'text-green-600', bg: 'bg-green-100', label: 'Verified' },
  rejected: { icon: XCircle, color: 'text-red-600', bg: 'bg-red-100', label: 'Rejected' },
  auto_approved: { icon: CheckCircle2, color: 'text-[#0d4a6f]', bg: 'bg-[#c5e1f5]', label: 'AI Approved' },
  auto_rejected: { icon: AlertCircle, color: 'text-purple-600', bg: 'bg-purple-100', label: 'AI Rejected' },
  needs_manual_review: { icon: AlertTriangle, color: 'text-orange-600', bg: 'bg-orange-100', label: 'Needs Review' },
  investigating: { icon: Search, color: 'text-blue-600', bg: 'bg-blue-100', label: 'Investigating' }
};

const priorityBands = [
  { label: 'Critical', min: 0, max: 40, color: 'bg-red-500', textColor: 'text-red-600', bgLight: 'bg-red-100' },
  { label: 'Review', min: 40, max: 60, color: 'bg-yellow-500', textColor: 'text-yellow-600', bgLight: 'bg-yellow-100' },
  { label: 'Borderline', min: 60, max: 75, color: 'bg-green-500', textColor: 'text-green-600', bgLight: 'bg-green-100' }
];

function UnifiedReportsPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { user } = useAuthStore();

  // Active tab: 'all' for all reports, 'queue' for verification queue only
  const [activeTab, setActiveTab] = useState('all');

  // Read tab from URL params (for redirect from old verification-queue page)
  useEffect(() => {
    const tab = searchParams.get('tab');
    if (tab === 'queue') {
      setActiveTab('queue');
    }
  }, [searchParams]);

  // Get verification queue data
  const {
    queue: verificationQueue,
    queueLoading,
    queueError,
    refreshQueue,
    processing,
    approve,
    reject,
    rerun,
    stats: verificationStats,
    statsLoading,
    thresholds
  } = useVerification({ limit: 50, autoRefresh: true, refreshInterval: 60000 });

  const { health, loading: healthLoading } = useVerificationHealth();

  // Reports state (all reports)
  const [reports, setReports] = useState([]);
  const [reportsLoading, setReportsLoading] = useState(true);
  const [pagination, setPagination] = useState({
    page: 1,
    limit: 20,
    total_count: 0,
    total_pages: 0
  });

  // Filters
  const [filters, setFilters] = useState({
    hazard_type: '',
    status: '',
    severity: '',
    region: '',
    date_from: '',
    date_to: '',
    search: '',
    score_min: '',
    score_max: ''
  });
  const [filterOptions, setFilterOptions] = useState({
    hazard_types: [],
    regions: [],
    statuses: ['pending', 'verified', 'rejected', 'auto_approved', 'auto_rejected', 'needs_manual_review', 'investigating'],
    severities: ['low', 'medium', 'high', 'critical']
  });
  const [sortConfig, setSortConfig] = useState({ field: 'created_at', order: 'desc' });
  const [showFilters, setShowFilters] = useState(false);
  const [viewMode, setViewMode] = useState('table');

  // Modal states
  const [selectedReport, setSelectedReport] = useState(null);
  const [reportDetail, setReportDetail] = useState(null);
  const [loadingDetail, setLoadingDetail] = useState(false);
  const [decisionModal, setDecisionModal] = useState({ show: false, type: null, reportId: null });
  const [decisionReason, setDecisionReason] = useState('');

  // Auth check
  useEffect(() => {
    if (user && !['analyst', 'authority_admin'].includes(user.role)) {
      router.push('/dashboard');
    }
  }, [user, router]);

  // Fetch all reports
  const fetchReports = useCallback(async (page = 1) => {
    setReportsLoading(true);
    try {
      const params = {
        page,
        limit: pagination.limit,
        sort_by: sortConfig.field,
        sort_order: sortConfig.order
      };

      // Add active filters
      Object.entries(filters).forEach(([key, value]) => {
        if (value && !['score_min', 'score_max'].includes(key)) {
          params[key] = value;
        }
      });

      const response = await getAnalystReports(params);

      if (response.success) {
        let filteredReports = response.data.reports || [];

        // Apply score filters client-side
        if (filters.score_min) {
          filteredReports = filteredReports.filter(r => (r.verification_score || 0) >= parseFloat(filters.score_min));
        }
        if (filters.score_max) {
          filteredReports = filteredReports.filter(r => (r.verification_score || 0) <= parseFloat(filters.score_max));
        }

        setReports(filteredReports);
        setPagination(prev => ({
          ...prev,
          ...response.data.pagination
        }));
        if (response.data.filters) {
          setFilterOptions(prev => ({
            ...prev,
            hazard_types: response.data.filters.hazard_types || prev.hazard_types,
            regions: response.data.filters.regions || prev.regions,
            statuses: ['pending', 'verified', 'rejected', 'auto_approved', 'auto_rejected', 'needs_manual_review', 'investigating'],
            severities: response.data.filters.severities || prev.severities
          }));
        }
      }
    } catch (error) {
      console.error('Error fetching reports:', error);
      toast.error('Failed to load reports');
    } finally {
      setReportsLoading(false);
    }
  }, [filters, sortConfig, pagination.limit]);

  useEffect(() => {
    if (activeTab === 'all') {
      fetchReports(1);
    }
  }, [activeTab, filters, sortConfig]);

  // Get display data based on active tab
  const displayReports = activeTab === 'queue' ? verificationQueue : reports;
  const isLoading = activeTab === 'queue' ? queueLoading : reportsLoading;
  const hasError = activeTab === 'queue' ? queueError : null;

  // Queue stats
  const queueCount = verificationQueue.length;
  const avgQueueScore = queueCount > 0
    ? (verificationQueue.reduce((sum, r) => sum + (r.composite_score || r.verification_score || 0), 0) / queueCount).toFixed(1)
    : 0;

  const priorityBreakdown = priorityBands.map(band => ({
    ...band,
    count: verificationQueue.filter(r => {
      const score = r.composite_score || r.verification_score || 0;
      return score >= band.min && score < band.max;
    }).length
  }));

  // Fetch report detail
  const fetchReportDetail = async (reportId) => {
    setLoadingDetail(true);
    try {
      // Try verification details first for richer data
      const data = await getVerificationDetails(reportId);
      setReportDetail(data);
    } catch (error) {
      // Fallback to regular detail
      try {
        const response = await getAnalystReportDetail(reportId);
        if (response.success) {
          setReportDetail(response.data);
        }
      } catch (err) {
        console.error('Error fetching report detail:', err);
        toast.error('Failed to load report details');
      }
    } finally {
      setLoadingDetail(false);
    }
  };

  // Handle filter change
  const handleFilterChange = (key, value) => {
    setFilters(prev => ({ ...prev, [key]: value }));
  };

  // Clear all filters
  const clearFilters = () => {
    setFilters({
      hazard_type: '',
      status: '',
      severity: '',
      region: '',
      date_from: '',
      date_to: '',
      search: '',
      score_min: '',
      score_max: ''
    });
  };

  // Handle sort
  const handleSort = (field) => {
    setSortConfig(prev => ({
      field,
      order: prev.field === field && prev.order === 'desc' ? 'asc' : 'desc'
    }));
  };

  // Handle page change
  const handlePageChange = (newPage) => {
    if (newPage >= 1 && newPage <= pagination.total_pages) {
      fetchReports(newPage);
    }
  };

  // Open report detail modal
  const openReportDetail = (report) => {
    setSelectedReport(report);
    fetchReportDetail(report.report_id || report.id);
  };

  // Close modal
  const closeModal = () => {
    setSelectedReport(null);
    setReportDetail(null);
  };

  // Handle decision (approve/reject)
  const handleDecision = async () => {
    if (!decisionModal.reportId) return;

    const getValidReason = (userReason, defaultReason) => {
      const trimmed = (userReason || '').trim();
      return trimmed.length >= 10 ? trimmed : defaultReason;
    };

    try {
      if (decisionModal.type === 'approve') {
        const reason = getValidReason(decisionReason, 'Approved by analyst after manual review');
        await approve(decisionModal.reportId, reason);
        toast.success('Report approved successfully! Ticket created.');
      } else if (decisionModal.type === 'reject') {
        const reason = getValidReason(decisionReason, 'Rejected by analyst after manual review');
        await reject(decisionModal.reportId, reason);
        toast.success('Report rejected successfully');
      }
      setDecisionModal({ show: false, type: null, reportId: null });
      setDecisionReason('');
      closeModal();
      // Refresh both reports and queue
      refreshQueue();
      if (activeTab === 'all') {
        fetchReports(pagination.page);
      }
    } catch (error) {
      toast.error(error.message || 'Failed to process decision');
    }
  };

  // Handle rerun
  const handleRerun = async (reportId) => {
    try {
      await rerun(reportId);
      toast.success('Verification re-run initiated');
      if (selectedReport) {
        fetchReportDetail(reportId);
      }
    } catch (error) {
      toast.error(error.message || 'Failed to re-run verification');
    }
  };

  // Open decision modal
  const openDecisionModal = (type, reportId) => {
    setDecisionModal({ show: true, type, reportId });
    setDecisionReason('');
  };

  // Helper functions
  const formatDate = (dateStr) => {
    if (!dateStr) return 'N/A';
    const date = new Date(dateStr);
    return date.toLocaleDateString('en-IN', {
      day: '2-digit',
      month: 'short',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  const formatHazardType = (type) => {
    if (!type) return 'Unknown';
    return type.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
  };

  const getTimeInQueue = (createdAt) => {
    if (!createdAt) return 'Unknown';
    const created = new Date(createdAt);
    const now = new Date();
    const diffMs = now - created;
    const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
    const diffDays = Math.floor(diffHours / 24);

    if (diffDays > 0) return `${diffDays}d ${diffHours % 24}h`;
    if (diffHours > 0) return `${diffHours}h`;
    const diffMins = Math.floor(diffMs / (1000 * 60));
    return `${diffMins}m`;
  };

  const getScoreColor = (score) => {
    if (score >= 75) return 'text-green-600 bg-green-100';
    if (score >= 40) return 'text-yellow-600 bg-yellow-100';
    return 'text-red-600 bg-red-100';
  };

  const activeFiltersCount = Object.values(filters).filter(v => v).length;

  // Check if report needs action
  const needsAction = (report) => {
    // In queue tab, all items need action
    if (activeTab === 'queue') return true;
    const status = report.verification_status || report.status;
    return status === 'needs_manual_review' || status === 'pending';
  };

  // Get display location from report
  const getDisplayLocation = (report) => {
    // Verification queue items have location_name directly
    if (report.location_name && report.location_name !== 'Unknown location') {
      return report.location_name;
    }
    // Try various location field patterns
    // Backend uses: latitude, longitude, address, region, district
    if (report.location?.district) return report.location.district;
    if (report.location?.address) return report.location.address;
    if (report.location?.region) return report.location.region;
    if (report.location?.city) return report.location.city;
    if (report.location?.name) return report.location.name;
    if (report.district) return report.district;
    if (report.region) return report.region;
    if (report.city) return report.city;
    if (report.address) return report.address;
    // Try to get from coordinates if available
    if (report.location?.latitude && report.location?.longitude) {
      return `${Number(report.location.latitude).toFixed(4)}, ${Number(report.location.longitude).toFixed(4)}`;
    }
    if (report.latitude && report.longitude) {
      return `${Number(report.latitude).toFixed(4)}, ${Number(report.longitude).toFixed(4)}`;
    }
    return 'Unknown';
  };

  // Get location sub-text (state/region)
  const getLocationSubtext = (report) => {
    // If we showed district, show region as subtext
    if (report.location?.district && report.location?.region) return report.location.region;
    if (report.location?.state) return report.location.state;
    if (report.location?.region && !report.location?.district) return ''; // Already shown as main
    if (report.location?.country) return report.location.country;
    if (report.state) return report.state;
    if (report.country) return report.country;
    return '';
  };

  // Refresh handler
  const handleRefresh = () => {
    refreshQueue();
    if (activeTab === 'all') {
      fetchReports(pagination.page);
    }
  };

  return (
    <DashboardLayout>
      <div className="p-4 lg:p-6 space-y-6 bg-gray-50 min-h-screen">
        {/* Page Header - Desktop Only */}
        <PageHeader />

        {/* Header */}
        <div className="bg-gradient-to-r from-[#0d4a6f] to-[#083a57] rounded-2xl shadow-lg p-6 text-white relative overflow-hidden">
          <div className="absolute bottom-0 left-0 right-0 opacity-10">
            <svg viewBox="0 0 1440 120" className="w-full h-12">
              <path fill="white" d="M0,32L48,37.3C96,43,192,53,288,58.7C384,64,480,64,576,58.7C672,53,768,43,864,42.7C960,43,1056,53,1152,58.7C1248,64,1344,64,1392,64L1440,64L1440,120L1392,120C1344,120,1248,120,1152,120C1056,120,960,120,864,120C768,120,672,120,576,120C480,120,384,120,288,120C192,120,96,120,48,120L0,120Z"></path>
            </svg>
          </div>
          <div className="relative z-10 flex flex-col lg:flex-row justify-between items-start lg:items-center gap-4">
            <div>
              <h1 className="text-2xl font-semibold flex items-center gap-2">
                <div className="p-2 bg-white/20 rounded-xl backdrop-blur-sm">
                  <FileText className="w-6 h-6 text-white" />
                </div>
                Reports & Verification
              </h1>
              <p className="text-[#9ecbec] mt-1">
                Unified view of all reports with verification capabilities
              </p>
            </div>
            <div className="flex flex-wrap items-center gap-3">
              {/* Search */}
              <div className="relative">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
                <input
                  type="text"
                  placeholder="Search reports..."
                  value={filters.search}
                  onChange={(e) => handleFilterChange('search', e.target.value)}
                  className="pl-10 pr-4 py-2.5 w-64 bg-white/10 border border-white/20 rounded-xl focus:ring-2 focus:ring-white/50 focus:border-white/50 text-sm text-white placeholder-white/60"
                />
                {filters.search && (
                  <button
                    onClick={() => handleFilterChange('search', '')}
                    className="absolute right-3 top-1/2 -translate-y-1/2"
                  >
                    <X className="w-4 h-4 text-gray-400 hover:text-gray-600" />
                  </button>
                )}
              </div>

              {/* Filter Button */}
              <button
                onClick={() => setShowFilters(!showFilters)}
                className={`flex items-center gap-2 px-4 py-2.5 border rounded-xl text-sm font-medium transition-colors ${
                  showFilters || activeFiltersCount > 0
                    ? 'bg-white/20 border-white/30 text-white'
                    : 'bg-white/10 border-white/20 text-white hover:bg-white/20'
                }`}
              >
                <Filter className="w-4 h-4" />
                Filters
                {activeFiltersCount > 0 && (
                  <span className="bg-white text-[#0d4a6f] text-xs rounded-full w-5 h-5 flex items-center justify-center">
                    {activeFiltersCount}
                  </span>
                )}
                <ChevronDown className={`w-4 h-4 transition-transform ${showFilters ? 'rotate-180' : ''}`} />
              </button>

              {/* Export Button */}
              <ExportButton
                dataType="reports"
                currentFilters={filters}
                size="md"
              />

              {/* View Toggle */}
              <div className="flex bg-white/10 rounded-xl p-1">
                <button
                  onClick={() => setViewMode('table')}
                  className={`p-2 rounded-lg transition-colors ${
                    viewMode === 'table' ? 'bg-white shadow-sm text-[#0d4a6f]' : 'text-white/70 hover:text-white'
                  }`}
                >
                  <LayoutList className="w-4 h-4" />
                </button>
                <button
                  onClick={() => setViewMode('grid')}
                  className={`p-2 rounded-lg transition-colors ${
                    viewMode === 'grid' ? 'bg-white shadow-sm text-[#0d4a6f]' : 'text-white/70 hover:text-white'
                  }`}
                >
                  <LayoutGrid className="w-4 h-4" />
                </button>
              </div>

              {/* Refresh */}
              <button
                onClick={handleRefresh}
                disabled={isLoading}
                className="flex items-center gap-2 px-4 py-2.5 bg-white/10 border border-white/20 text-white rounded-xl hover:bg-white/20 disabled:opacity-50 text-sm font-medium"
              >
                <RefreshCw className={`w-4 h-4 ${isLoading ? 'animate-spin' : ''}`} />
                Refresh
              </button>
            </div>
          </div>
        </div>

        {/* Tabs and Filters Card */}
        <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-6">
          {/* Tab Navigation */}
          <div className="flex gap-2">
            <button
              onClick={() => setActiveTab('all')}
              className={`flex items-center gap-2 px-5 py-2.5 rounded-xl text-sm font-medium transition-all ${
                activeTab === 'all'
                  ? 'bg-gradient-to-r from-[#0d4a6f] to-[#083a57] text-white shadow-sm'
                  : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
              }`}
            >
              <FileText className="w-4 h-4" />
              All Reports
              {pagination.total_count > 0 && (
                <span className={`px-2 py-0.5 rounded-full text-xs ${
                  activeTab === 'all' ? 'bg-white/20' : 'bg-gray-200'
                }`}>
                  {pagination.total_count}
                </span>
              )}
            </button>
            <button
              onClick={() => setActiveTab('queue')}
              className={`flex items-center gap-2 px-5 py-2.5 rounded-xl text-sm font-medium transition-all ${
                activeTab === 'queue'
                  ? 'bg-gradient-to-r from-amber-500 to-orange-500 text-white shadow-sm'
                  : 'bg-amber-50 text-amber-700 hover:bg-amber-100 border border-amber-200'
              }`}
            >
              <Shield className="w-4 h-4" />
              Verification Queue
              {queueCount > 0 && (
                <span className={`px-2 py-0.5 rounded-full text-xs font-bold ${
                  activeTab === 'queue' ? 'bg-white/20' : 'bg-amber-200'
                }`}>
                  {queueCount}
                </span>
              )}
            </button>
          </div>

          {/* Filters Panel */}
          {showFilters && (
            <div className="mt-6 pt-6 border-t border-gray-100">
              <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-8 gap-4">
                {/* Hazard Type */}
                <div>
                  <label className="block text-xs font-medium text-gray-600 mb-1.5">Hazard Type</label>
                  <select
                    value={filters.hazard_type}
                    onChange={(e) => handleFilterChange('hazard_type', e.target.value)}
                    className="w-full px-3 py-2 bg-gray-50 border border-gray-200 rounded-lg text-sm focus:ring-2 focus:ring-blue-500"
                  >
                    <option value="">All Types</option>
                    {filterOptions.hazard_types.map(type => (
                      <option key={type} value={type}>{formatHazardType(type)}</option>
                    ))}
                  </select>
                </div>

                {/* Status */}
                <div>
                  <label className="block text-xs font-medium text-gray-600 mb-1.5">Status</label>
                  <select
                    value={filters.status}
                    onChange={(e) => handleFilterChange('status', e.target.value)}
                    className="w-full px-3 py-2 bg-gray-50 border border-gray-200 rounded-lg text-sm focus:ring-2 focus:ring-blue-500"
                  >
                    <option value="">All Status</option>
                    {filterOptions.statuses.map(status => (
                      <option key={status} value={status}>{statusConfig[status]?.label || status}</option>
                    ))}
                  </select>
                </div>

                {/* Severity */}
                <div>
                  <label className="block text-xs font-medium text-gray-600 mb-1.5">Severity</label>
                  <select
                    value={filters.severity}
                    onChange={(e) => handleFilterChange('severity', e.target.value)}
                    className="w-full px-3 py-2 bg-gray-50 border border-gray-200 rounded-lg text-sm focus:ring-2 focus:ring-blue-500"
                  >
                    <option value="">All Severity</option>
                    {filterOptions.severities.map(sev => (
                      <option key={sev} value={sev}>{sev.charAt(0).toUpperCase() + sev.slice(1)}</option>
                    ))}
                  </select>
                </div>

                {/* Region */}
                <div>
                  <label className="block text-xs font-medium text-gray-600 mb-1.5">Region</label>
                  <select
                    value={filters.region}
                    onChange={(e) => handleFilterChange('region', e.target.value)}
                    className="w-full px-3 py-2 bg-gray-50 border border-gray-200 rounded-lg text-sm focus:ring-2 focus:ring-blue-500"
                  >
                    <option value="">All Regions</option>
                    {filterOptions.regions.map(region => (
                      <option key={region} value={region}>{region}</option>
                    ))}
                  </select>
                </div>

                {/* Score Min */}
                <div>
                  <label className="block text-xs font-medium text-gray-600 mb-1.5">Min Score</label>
                  <input
                    type="number"
                    min="0"
                    max="100"
                    value={filters.score_min}
                    onChange={(e) => handleFilterChange('score_min', e.target.value)}
                    placeholder="0"
                    className="w-full px-3 py-2 bg-gray-50 border border-gray-200 rounded-lg text-sm focus:ring-2 focus:ring-blue-500"
                  />
                </div>

                {/* Score Max */}
                <div>
                  <label className="block text-xs font-medium text-gray-600 mb-1.5">Max Score</label>
                  <input
                    type="number"
                    min="0"
                    max="100"
                    value={filters.score_max}
                    onChange={(e) => handleFilterChange('score_max', e.target.value)}
                    placeholder="100"
                    className="w-full px-3 py-2 bg-gray-50 border border-gray-200 rounded-lg text-sm focus:ring-2 focus:ring-blue-500"
                  />
                </div>

                {/* Date From */}
                <div>
                  <label className="block text-xs font-medium text-gray-600 mb-1.5">From Date</label>
                  <input
                    type="date"
                    value={filters.date_from}
                    onChange={(e) => handleFilterChange('date_from', e.target.value)}
                    className="w-full px-3 py-2 bg-gray-50 border border-gray-200 rounded-lg text-sm focus:ring-2 focus:ring-blue-500"
                  />
                </div>

                {/* Date To */}
                <div>
                  <label className="block text-xs font-medium text-gray-600 mb-1.5">To Date</label>
                  <input
                    type="date"
                    value={filters.date_to}
                    onChange={(e) => handleFilterChange('date_to', e.target.value)}
                    className="w-full px-3 py-2 bg-gray-50 border border-gray-200 rounded-lg text-sm focus:ring-2 focus:ring-blue-500"
                  />
                </div>
              </div>

              {activeFiltersCount > 0 && (
                <div className="mt-4 flex items-center justify-between">
                  <div className="flex flex-wrap gap-2">
                    {Object.entries(filters).map(([key, value]) => {
                      if (!value) return null;
                      return (
                        <span
                          key={key}
                          className="inline-flex items-center gap-1 px-3 py-1 bg-blue-50 text-blue-700 text-sm rounded-full"
                        >
                          <span className="font-medium">{key.replace(/_/g, ' ')}:</span> {value}
                          <button onClick={() => handleFilterChange(key, '')}>
                            <X className="w-3 h-3" />
                          </button>
                        </span>
                      );
                    })}
                  </div>
                  <button
                    onClick={clearFilters}
                    className="text-sm text-gray-600 hover:text-gray-800 font-medium"
                  >
                    Clear All
                  </button>
                </div>
              )}
            </div>
          )}
        </div>

        {/* Stats Cards - Only show for Queue tab */}
        {activeTab === 'queue' && (
          <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
            {/* Total Pending */}
            <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-4">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-purple-100 rounded-lg">
                  <Clock className="w-5 h-5 text-purple-600" />
                </div>
                <div>
                  <p className="text-sm text-gray-500">Pending Review</p>
                  <p className="text-2xl font-semibold text-gray-900">{queueCount}</p>
                </div>
              </div>
            </div>

            {/* Average Score */}
            <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-4">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-blue-100 rounded-lg">
                  <Gauge className="w-5 h-5 text-blue-600" />
                </div>
                <div>
                  <p className="text-sm text-gray-500">Avg Score</p>
                  <p className="text-2xl font-semibold text-gray-900">{avgQueueScore}%</p>
                </div>
              </div>
            </div>

            {/* Priority Breakdown */}
            {priorityBreakdown.map((band, idx) => (
              <div key={idx} className="bg-white rounded-xl shadow-sm border border-gray-100 p-4">
                <div className="flex items-center gap-3">
                  <div className={`p-2 ${band.bgLight} rounded-lg`}>
                    <div className={`w-5 h-5 ${band.color} rounded-full`} />
                  </div>
                  <div>
                    <p className="text-sm text-gray-500">{band.label}</p>
                    <p className={`text-2xl font-semibold ${band.textColor}`}>{band.count}</p>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Content */}
        {isLoading && displayReports.length === 0 ? (
          <div className="flex items-center justify-center py-20">
            <div className="text-center">
              <Loader2 className="w-12 h-12 text-[#0d4a6f] animate-spin mx-auto mb-4" />
              <p className="text-gray-600">Loading reports...</p>
            </div>
          </div>
        ) : hasError ? (
          <div className="bg-red-50 rounded-2xl p-6 text-center">
            <AlertCircle className="w-12 h-12 text-red-500 mx-auto mb-4" />
            <h3 className="text-lg font-medium text-red-800 mb-2">Error Loading Data</h3>
            <p className="text-red-600">{hasError}</p>
            <button
              onClick={handleRefresh}
              className="mt-4 px-4 py-2 bg-red-600 text-white rounded-xl hover:bg-red-700"
            >
              Try Again
            </button>
          </div>
        ) : displayReports.length === 0 ? (
          <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-12">
            <div className="text-center">
              {activeTab === 'queue' ? (
                <>
                  <CheckCircle2 className="w-16 h-16 text-green-400 mx-auto mb-4" />
                  <h3 className="text-lg font-medium text-gray-600 mb-2">Queue is Empty</h3>
                  <p className="text-gray-500 max-w-md mx-auto">
                    All reports have been processed. Great job!
                  </p>
                </>
              ) : (
                <>
                  <FileText className="w-16 h-16 text-gray-300 mx-auto mb-4" />
                  <h3 className="text-lg font-medium text-gray-600 mb-2">No Reports Found</h3>
                  <p className="text-gray-500 max-w-md mx-auto">
                    {activeFiltersCount > 0
                      ? 'No reports match your current filters. Try adjusting your filters.'
                      : 'There are no hazard reports in the system yet.'}
                  </p>
                  {activeFiltersCount > 0 && (
                    <button
                      onClick={clearFilters}
                      className="mt-4 px-4 py-2 bg-[#0d4a6f] text-white rounded-xl hover:bg-[#083a57] text-sm font-medium"
                    >
                      Clear Filters
                    </button>
                  )}
                </>
              )}
            </div>
          </div>
        ) : viewMode === 'table' ? (
          /* Table View */
          <div className="bg-white rounded-2xl shadow-sm border border-gray-100 overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead className="bg-gray-50 border-b border-gray-100">
                  <tr>
                    <th className="px-6 py-4 text-left">
                      <button
                        onClick={() => handleSort('hazard_type')}
                        className="flex items-center gap-2 text-xs font-semibold text-gray-600 uppercase tracking-wider hover:text-gray-900"
                      >
                        Hazard Type
                        {sortConfig.field === 'hazard_type' && (
                          sortConfig.order === 'desc' ? <SortDesc className="w-3 h-3" /> : <SortAsc className="w-3 h-3" />
                        )}
                      </button>
                    </th>
                    <th className="px-6 py-4 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider">
                      Location
                    </th>
                    <th className="px-6 py-4 text-left">
                      <button
                        onClick={() => handleSort('severity')}
                        className="flex items-center gap-2 text-xs font-semibold text-gray-600 uppercase tracking-wider hover:text-gray-900"
                      >
                        Severity
                        {sortConfig.field === 'severity' && (
                          sortConfig.order === 'desc' ? <SortDesc className="w-3 h-3" /> : <SortAsc className="w-3 h-3" />
                        )}
                      </button>
                    </th>
                    <th className="px-6 py-4 text-left">
                      <button
                        onClick={() => handleSort('verification_score')}
                        className="flex items-center gap-2 text-xs font-semibold text-gray-600 uppercase tracking-wider hover:text-gray-900"
                      >
                        <Gauge className="w-3 h-3" />
                        AI Score
                        {sortConfig.field === 'verification_score' && (
                          sortConfig.order === 'desc' ? <SortDesc className="w-3 h-3" /> : <SortAsc className="w-3 h-3" />
                        )}
                      </button>
                    </th>
                    <th className="px-6 py-4 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider">
                      Status
                    </th>
                    <th className="px-6 py-4 text-left">
                      <button
                        onClick={() => handleSort('created_at')}
                        className="flex items-center gap-2 text-xs font-semibold text-gray-600 uppercase tracking-wider hover:text-gray-900"
                      >
                        Date
                        {sortConfig.field === 'created_at' && (
                          sortConfig.order === 'desc' ? <SortDesc className="w-3 h-3" /> : <SortAsc className="w-3 h-3" />
                        )}
                      </button>
                    </th>
                    <th className="px-6 py-4 text-right text-xs font-semibold text-gray-600 uppercase tracking-wider">
                      Actions
                    </th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {displayReports.map((report) => {
                    const severity = severityColors[report.severity] || severityColors.medium;
                    const reportStatus = report.verification_status || report.status || 'pending';
                    const status = statusConfig[reportStatus] || statusConfig.pending;
                    const StatusIcon = status.icon;
                    const score = report.composite_score || report.verification_score;
                    const showActions = needsAction(report);

                    return (
                      <tr
                        key={report.report_id || report.id}
                        className={`hover:bg-gray-50 transition-colors cursor-pointer ${showActions ? 'bg-amber-50/30' : ''}`}
                        onClick={() => openReportDetail(report)}
                      >
                        <td className="px-6 py-4">
                          <div className="flex items-center gap-3">
                            <div className={`w-2 h-2 rounded-full ${severity.dot}`} />
                            <div>
                              <div className="flex items-center gap-2">
                                <p className="font-medium text-gray-900">{formatHazardType(report.hazard_type)}</p>
                                {report.has_images && (
                                  <span className="inline-flex items-center gap-1 px-1.5 py-0.5 bg-blue-50 text-blue-600 text-xs rounded">
                                    <ImageIcon className="w-3 h-3" />
                                    {report.image_count || report.images?.length || 1}
                                  </span>
                                )}
                                {showActions && (
                                  <span className="inline-flex items-center gap-1 px-1.5 py-0.5 bg-amber-100 text-amber-700 text-xs rounded font-medium">
                                    <AlertTriangle className="w-3 h-3" />
                                    Action Needed
                                  </span>
                                )}
                              </div>
                              <p className="text-xs text-gray-500 truncate max-w-xs">{report.description}</p>
                            </div>
                          </div>
                        </td>
                        <td className="px-6 py-4">
                          <div className="flex items-start gap-2">
                            <MapPin className="w-4 h-4 text-gray-400 mt-0.5 flex-shrink-0" />
                            <div>
                              <p className="text-sm text-gray-900">{getDisplayLocation(report)}</p>
                              <p className="text-xs text-gray-500">{getLocationSubtext(report)}</p>
                            </div>
                          </div>
                        </td>
                        <td className="px-6 py-4">
                          <span className={`inline-flex items-center px-2.5 py-1 rounded-full text-xs font-medium ${severity.bg} ${severity.text}`}>
                            {report.severity?.charAt(0).toUpperCase() + report.severity?.slice(1) || 'Medium'}
                          </span>
                        </td>
                        <td className="px-6 py-4">
                          {score !== undefined && score !== null ? (
                            <div className="flex flex-col items-start gap-1">
                              <div className={`flex items-center gap-1.5 px-2.5 py-1 rounded-full text-sm font-semibold ${getScoreColor(score)}`}>
                                <Gauge className="w-3 h-3" />
                                {typeof score === 'number' ? score.toFixed(1) : score}%
                              </div>
                              {(report.has_ticket || report.ticket_id) && (
                                <span className="inline-flex items-center gap-1 px-1.5 py-0.5 bg-indigo-50 text-indigo-600 text-xs rounded">
                                  <Ticket className="w-3 h-3" />
                                  Ticket
                                </span>
                              )}
                            </div>
                          ) : (
                            <span className="text-gray-400 text-sm">N/A</span>
                          )}
                        </td>
                        <td className="px-6 py-4">
                          <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium ${status.bg} ${status.color}`}>
                            <StatusIcon className="w-3 h-3" />
                            {status.label}
                          </span>
                        </td>
                        <td className="px-6 py-4">
                          <div className="flex items-center gap-2 text-sm text-gray-600">
                            <Calendar className="w-4 h-4 text-gray-400" />
                            <div>
                              <p>{formatDate(report.created_at)}</p>
                              {activeTab === 'queue' && (
                                <p className="text-xs text-amber-600">{getTimeInQueue(report.created_at)} in queue</p>
                              )}
                            </div>
                          </div>
                        </td>
                        <td className="px-6 py-4">
                          <div className="flex items-center justify-end gap-2">
                            <button
                              onClick={(e) => {
                                e.stopPropagation();
                                openReportDetail(report);
                              }}
                              className="p-2 text-[#0d4a6f] hover:bg-[#e8f4fc] rounded-lg transition-colors"
                              title="View Details"
                            >
                              <Eye className="w-4 h-4" />
                            </button>
                            {showActions && (
                              <>
                                <button
                                  onClick={(e) => {
                                    e.stopPropagation();
                                    openDecisionModal('approve', report.report_id || report.id);
                                  }}
                                  disabled={processing}
                                  className="p-2 text-green-600 hover:bg-green-50 rounded-lg transition-colors disabled:opacity-50"
                                  title="Approve"
                                >
                                  <ThumbsUp className="w-4 h-4" />
                                </button>
                                <button
                                  onClick={(e) => {
                                    e.stopPropagation();
                                    openDecisionModal('reject', report.report_id || report.id);
                                  }}
                                  disabled={processing}
                                  className="p-2 text-red-600 hover:bg-red-50 rounded-lg transition-colors disabled:opacity-50"
                                  title="Reject"
                                >
                                  <ThumbsDown className="w-4 h-4" />
                                </button>
                              </>
                            )}
                          </div>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>
        ) : (
          /* Grid View */
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {displayReports.map((report) => {
              const severity = severityColors[report.severity] || severityColors.medium;
              const reportStatus = report.verification_status || report.status || 'pending';
              const status = statusConfig[reportStatus] || statusConfig.pending;
              const StatusIcon = status.icon;
              const score = report.composite_score || report.verification_score;
              const showActions = needsAction(report);

              return (
                <div
                  key={report.report_id || report.id}
                  onClick={() => openReportDetail(report)}
                  className={`relative bg-white rounded-2xl shadow-sm border ${showActions ? 'border-amber-200 ring-2 ring-amber-100' : 'border-gray-100'} p-5 hover:shadow-md transition-all cursor-pointer`}
                >
                  {/* Score Badge */}
                  {score !== undefined && score !== null && (
                    <div className={`absolute -top-2 -right-2 px-2.5 py-1 rounded-full text-xs font-semibold shadow-lg ${
                      score >= 75 ? 'bg-green-500 text-white' :
                      score >= 40 ? 'bg-yellow-500 text-white' :
                      'bg-red-500 text-white'
                    }`}>
                      {typeof score === 'number' ? score.toFixed(0) : score}%
                    </div>
                  )}

                  {/* Action Needed Badge */}
                  {showActions && (
                    <div className="absolute -top-2 -left-2 px-2.5 py-1 rounded-full text-xs font-semibold bg-amber-500 text-white shadow-lg flex items-center gap-1">
                      <AlertTriangle className="w-3 h-3" />
                      Review
                    </div>
                  )}

                  <div className="flex items-start justify-between mb-3">
                    <div className="flex items-center gap-2">
                      <div className={`w-3 h-3 rounded-full ${severity.dot}`} />
                      <h3 className="font-semibold text-gray-900">{formatHazardType(report.hazard_type)}</h3>
                    </div>
                    <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium ${status.bg} ${status.color}`}>
                      <StatusIcon className="w-3 h-3" />
                      {status.label}
                    </span>
                  </div>

                  {/* Image preview */}
                  {(report.has_images || (report.images && report.images.length > 0)) && (
                    <div className="mb-3 -mx-1">
                      <div className="flex gap-1 overflow-hidden rounded-lg">
                        {(report.images || []).slice(0, 3).map((img, idx) => (
                          <div key={idx} className="flex-1 aspect-video bg-gray-100 overflow-hidden">
                            <img
                              src={getUploadUrl(img)}
                              alt={`Preview ${idx + 1}`}
                              className="w-full h-full object-cover"
                              onError={(e) => { e.target.style.display = 'none'; }}
                            />
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  <p className="text-sm text-gray-600 line-clamp-2 mb-4">{report.description || 'No description provided'}</p>

                  <div className="space-y-2 mb-4">
                    <div className="flex items-center gap-2 text-sm text-gray-600">
                      <MapPin className="w-4 h-4 text-gray-400" />
                      <span className="truncate">{getDisplayLocation(report)}</span>
                    </div>
                    <div className="flex items-center gap-2 text-sm text-gray-600">
                      <Calendar className="w-4 h-4 text-gray-400" />
                      <span>{formatDate(report.created_at)}</span>
                    </div>
                    {activeTab === 'queue' && (
                      <div className="flex items-center gap-2 text-sm text-amber-600">
                        <Clock className="w-4 h-4" />
                        <span>{getTimeInQueue(report.created_at)} in queue</span>
                      </div>
                    )}
                  </div>

                  <div className="flex items-center justify-between pt-3 border-t border-gray-100">
                    <span className={`inline-flex items-center px-2.5 py-1 rounded-full text-xs font-medium ${severity.bg} ${severity.text}`}>
                      {report.severity?.charAt(0).toUpperCase() + report.severity?.slice(1) || 'Medium'}
                    </span>
                    <div className="flex items-center gap-1">
                      {showActions && (
                        <>
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              openDecisionModal('approve', report.report_id || report.id);
                            }}
                            disabled={processing}
                            className="p-2 text-green-600 hover:bg-green-50 rounded-lg transition-colors disabled:opacity-50"
                          >
                            <ThumbsUp className="w-4 h-4" />
                          </button>
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              openDecisionModal('reject', report.report_id || report.id);
                            }}
                            disabled={processing}
                            className="p-2 text-red-600 hover:bg-red-50 rounded-lg transition-colors disabled:opacity-50"
                          >
                            <ThumbsDown className="w-4 h-4" />
                          </button>
                        </>
                      )}
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          openReportDetail(report);
                        }}
                        className="p-2 text-[#0d4a6f] hover:bg-[#e8f4fc] rounded-lg transition-colors"
                      >
                        <Eye className="w-4 h-4" />
                      </button>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}

        {/* Pagination - Only for All Reports tab */}
        {activeTab === 'all' && !isLoading && displayReports.length > 0 && (
          <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-4">
            <div className="flex flex-col sm:flex-row items-center justify-between gap-4">
              <p className="text-sm text-gray-600">
                Showing <span className="font-medium">{((pagination.page - 1) * pagination.limit) + 1}</span> to{' '}
                <span className="font-medium">{Math.min(pagination.page * pagination.limit, pagination.total_count)}</span> of{' '}
                <span className="font-medium">{pagination.total_count}</span> reports
              </p>

              <div className="flex items-center gap-2">
                <button
                  onClick={() => handlePageChange(pagination.page - 1)}
                  disabled={!pagination.has_prev}
                  className="p-2 border border-gray-200 rounded-xl hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  <ChevronLeft className="w-5 h-5" />
                </button>

                <div className="flex items-center gap-1">
                  {Array.from({ length: Math.min(5, pagination.total_pages) }, (_, i) => {
                    let pageNum;
                    if (pagination.total_pages <= 5) {
                      pageNum = i + 1;
                    } else if (pagination.page <= 3) {
                      pageNum = i + 1;
                    } else if (pagination.page >= pagination.total_pages - 2) {
                      pageNum = pagination.total_pages - 4 + i;
                    } else {
                      pageNum = pagination.page - 2 + i;
                    }

                    return (
                      <button
                        key={pageNum}
                        onClick={() => handlePageChange(pageNum)}
                        className={`w-10 h-10 rounded-xl text-sm font-medium transition-colors ${
                          pagination.page === pageNum
                            ? 'bg-[#0d4a6f] text-white'
                            : 'hover:bg-gray-100 text-gray-700'
                        }`}
                      >
                        {pageNum}
                      </button>
                    );
                  })}
                </div>

                <button
                  onClick={() => handlePageChange(pagination.page + 1)}
                  disabled={!pagination.has_next}
                  className="p-2 border border-gray-200 rounded-xl hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  <ChevronRight className="w-5 h-5" />
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Report Detail Modal */}
        {selectedReport && (
          <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-[99999] p-4 overflow-y-auto">
            <div className="bg-white rounded-2xl shadow-xl max-w-4xl w-full max-h-[95vh] overflow-hidden my-4">
              {/* Modal Header */}
              <div className={`flex items-center justify-between p-6 border-b border-gray-100 ${
                needsAction(selectedReport)
                  ? 'bg-gradient-to-r from-amber-500 to-orange-500'
                  : 'bg-gradient-to-r from-[#0d4a6f] to-[#083a57]'
              } text-white`}>
                <div>
                  <h2 className="text-xl font-bold flex items-center gap-2">
                    {needsAction(selectedReport) && <AlertTriangle className="w-5 h-5" />}
                    {needsAction(selectedReport) ? 'Verification Review' : 'Report Details'}
                  </h2>
                  <p className="text-sm text-white/80">ID: {selectedReport.report_id || selectedReport.id}</p>
                </div>
                <button
                  onClick={closeModal}
                  className="p-2 hover:bg-white/20 rounded-lg transition-colors"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>

              {/* Modal Content */}
              <div className="p-6 overflow-y-auto max-h-[calc(95vh-200px)]">
                {loadingDetail ? (
                  <div className="flex items-center justify-center py-12">
                    <Loader2 className="w-8 h-8 text-blue-600 animate-spin" />
                  </div>
                ) : reportDetail ? (
                  <div className="space-y-6">
                    {/* Verification Status */}
                    {(reportDetail.verification_score !== undefined || reportDetail.verification_result) && (
                      <VerificationStatus
                        report={reportDetail}
                        showDetails={true}
                        onRerunVerification={handleRerun}
                      />
                    )}

                    {/* Layer Breakdown */}
                    {reportDetail.verification_result?.layer_results && (
                      <LayerBreakdown
                        layers={reportDetail.verification_result.layer_results}
                        showDetails={true}
                      />
                    )}

                    {/* Report Info */}
                    <div className="bg-gray-50 rounded-xl p-4">
                      <h4 className="text-sm font-semibold text-gray-700 mb-3 flex items-center gap-2">
                        <FileText className="w-4 h-4 text-gray-500" />
                        Report Information
                      </h4>
                      <div className="grid grid-cols-2 gap-4">
                        <div>
                          <p className="text-xs text-gray-500">Hazard Type</p>
                          <p className="font-medium text-gray-900">{formatHazardType(reportDetail.hazard_type)}</p>
                        </div>
                        <div>
                          <p className="text-xs text-gray-500">Severity</p>
                          <span className={`inline-flex items-center px-2.5 py-1 rounded-full text-xs font-medium ${severityColors[reportDetail.severity]?.bg || 'bg-gray-100'} ${severityColors[reportDetail.severity]?.text || 'text-gray-600'}`}>
                            {reportDetail.severity?.charAt(0).toUpperCase() + reportDetail.severity?.slice(1) || 'Unknown'}
                          </span>
                        </div>
                        <div className="col-span-2">
                          <p className="text-xs text-gray-500">Description</p>
                          <p className="text-gray-700">{reportDetail.description || 'No description provided'}</p>
                        </div>
                      </div>
                    </div>

                    {/* Location */}
                    <div className="bg-gray-50 rounded-xl p-4">
                      <h4 className="text-sm font-semibold text-gray-700 mb-3 flex items-center gap-2">
                        <MapPin className="w-4 h-4 text-gray-500" />
                        Location
                      </h4>
                      <p className="text-gray-900">{reportDetail.location?.address || 'Address not available'}</p>
                      <p className="text-sm text-gray-500">
                        {[reportDetail.location?.city, reportDetail.location?.state].filter(Boolean).join(', ')}
                      </p>
                      {reportDetail.location?.lat && reportDetail.location?.lng && (
                        <p className="text-xs text-gray-400 mt-1">
                          Coordinates: {reportDetail.location.lat.toFixed(4)}, {reportDetail.location.lng.toFixed(4)}
                        </p>
                      )}
                    </div>

                    {/* Images */}
                    {reportDetail.images && reportDetail.images.length > 0 && (
                      <div>
                        <h4 className="text-sm font-semibold text-gray-700 mb-3 flex items-center gap-2">
                          <ImageIcon className="w-4 h-4 text-gray-500" />
                          Attached Images ({reportDetail.images.length})
                        </h4>
                        <div className="grid grid-cols-3 gap-3">
                          {reportDetail.images.map((img, idx) => (
                            <div
                              key={idx}
                              className="aspect-square rounded-xl overflow-hidden bg-gray-100 cursor-pointer group relative"
                              onClick={() => window.open(getUploadUrl(img), '_blank')}
                            >
                              <img
                                src={getUploadUrl(img)}
                                alt={`Image ${idx + 1}`}
                                className="w-full h-full object-cover group-hover:scale-105 transition-transform"
                                onError={(e) => { e.target.style.display = 'none'; }}
                              />
                              <div className="absolute inset-0 bg-black/0 group-hover:bg-black/30 flex items-center justify-center transition-colors">
                                <ExternalLink className="w-6 h-6 text-white opacity-0 group-hover:opacity-100 transition-opacity" />
                              </div>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}

                    {/* AI Score & Insight Section */}
                    {(reportDetail.verification_score !== undefined || reportDetail.hazard_classification) && (
                      <div className="bg-gradient-to-r from-indigo-50 to-purple-50 rounded-xl p-4 border border-indigo-100">
                        <h4 className="text-sm font-semibold text-indigo-700 mb-3 flex items-center gap-2">
                          <Gauge className="w-4 h-4 text-indigo-600" />
                          AI Analysis
                        </h4>
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                          {/* AI Score */}
                          <div className="bg-white rounded-lg p-3 shadow-sm">
                            <p className="text-xs text-gray-500 mb-1">Verification Score</p>
                            <div className="flex items-center gap-2">
                              <div className={`text-2xl font-semibold ${
                                (reportDetail.verification_score || 0) >= 75 ? 'text-green-600' :
                                (reportDetail.verification_score || 0) >= 40 ? 'text-yellow-600' :
                                'text-red-600'
                              }`}>
                                {reportDetail.verification_score != null ? `${reportDetail.verification_score.toFixed(1)}%` : 'N/A'}
                              </div>
                              <div className={`px-2 py-0.5 rounded text-xs font-medium ${
                                (reportDetail.verification_score || 0) >= 75 ? 'bg-green-100 text-green-700' :
                                (reportDetail.verification_score || 0) >= 40 ? 'bg-yellow-100 text-yellow-700' :
                                'bg-red-100 text-red-700'
                              }`}>
                                {(reportDetail.verification_score || 0) >= 75 ? 'High Confidence' :
                                 (reportDetail.verification_score || 0) >= 40 ? 'Review Needed' :
                                 'Low Confidence'}
                              </div>
                            </div>
                          </div>

                          {/* Threat Level */}
                          {reportDetail.hazard_classification?.threat_level && (
                            <div className="bg-white rounded-lg p-3 shadow-sm">
                              <p className="text-xs text-gray-500 mb-1">Threat Level</p>
                              <div className="flex items-center gap-2">
                                <Zap className={`w-5 h-5 ${
                                  reportDetail.hazard_classification.threat_level === 'warning' ? 'text-red-600' :
                                  reportDetail.hazard_classification.threat_level === 'alert' ? 'text-orange-600' :
                                  reportDetail.hazard_classification.threat_level === 'watch' ? 'text-yellow-600' :
                                  'text-green-600'
                                }`} />
                                <span className={`text-lg font-semibold uppercase ${
                                  reportDetail.hazard_classification.threat_level === 'warning' ? 'text-red-600' :
                                  reportDetail.hazard_classification.threat_level === 'alert' ? 'text-orange-600' :
                                  reportDetail.hazard_classification.threat_level === 'watch' ? 'text-yellow-600' :
                                  'text-green-600'
                                }`}>
                                  {reportDetail.hazard_classification.threat_level}
                                </span>
                              </div>
                            </div>
                          )}
                        </div>

                        {/* AI Insight/Reasoning */}
                        {(reportDetail.hazard_classification?.reasoning || reportDetail.verification_result?.recommendation) && (
                          <div className="mt-3 bg-white rounded-lg p-3 shadow-sm">
                            <p className="text-xs text-gray-500 mb-1">AI Insight</p>
                            <p className="text-sm text-gray-700">
                              {reportDetail.hazard_classification?.reasoning || reportDetail.verification_result?.recommendation || 'No detailed insight available'}
                            </p>
                          </div>
                        )}

                        {/* Recommendations */}
                        {reportDetail.hazard_classification?.recommendations && reportDetail.hazard_classification.recommendations.length > 0 && (
                          <div className="mt-3 bg-white rounded-lg p-3 shadow-sm">
                            <p className="text-xs text-gray-500 mb-2">Recommendations</p>
                            <ul className="space-y-1">
                              {reportDetail.hazard_classification.recommendations.slice(0, 3).map((rec, idx) => (
                                <li key={idx} className="text-sm text-gray-700 flex items-start gap-2">
                                  <CheckCircle2 className="w-4 h-4 text-green-500 mt-0.5 flex-shrink-0" />
                                  {rec}
                                </li>
                              ))}
                            </ul>
                          </div>
                        )}
                      </div>
                    )}

                    {/* Reporter Info */}
                    <div className="bg-gray-50 rounded-xl p-4">
                      <h4 className="text-sm font-semibold text-gray-700 mb-3 flex items-center gap-2">
                        <User className="w-4 h-4 text-gray-500" />
                        Reporter Information
                      </h4>
                      <div className="flex items-start gap-4">
                        <div className="w-12 h-12 bg-blue-100 rounded-full flex items-center justify-center flex-shrink-0">
                          <User className="w-6 h-6 text-blue-600" />
                        </div>
                        <div className="flex-1 grid grid-cols-1 md:grid-cols-2 gap-3">
                          <div>
                            <p className="text-xs text-gray-500">Name</p>
                            <p className="font-medium text-gray-900">
                              {reportDetail.reporter?.name || reportDetail.reporter?.user_name || 'Unknown'}
                            </p>
                          </div>
                          {reportDetail.reporter?.email && (
                            <div>
                              <p className="text-xs text-gray-500">Email</p>
                              <p className="text-sm text-gray-700">{reportDetail.reporter.email}</p>
                            </div>
                          )}
                          {reportDetail.reporter?.phone && (
                            <div>
                              <p className="text-xs text-gray-500">Phone</p>
                              <p className="text-sm text-gray-700">{reportDetail.reporter.phone}</p>
                            </div>
                          )}
                          <div>
                            <p className="text-xs text-gray-500">Total Reports</p>
                            <p className="text-sm font-medium text-gray-700">
                              {reportDetail.reporter?.reports_count || 0} reports submitted
                            </p>
                          </div>
                          {reportDetail.reporter?.credibility_score !== undefined && (
                            <div>
                              <p className="text-xs text-gray-500">Credibility Score</p>
                              <div className="flex items-center gap-2">
                                <div className={`w-16 h-2 rounded-full bg-gray-200 overflow-hidden`}>
                                  <div
                                    className={`h-full rounded-full ${
                                      reportDetail.reporter.credibility_score >= 70 ? 'bg-green-500' :
                                      reportDetail.reporter.credibility_score >= 40 ? 'bg-yellow-500' :
                                      'bg-red-500'
                                    }`}
                                    style={{ width: `${Math.min(100, reportDetail.reporter.credibility_score)}%` }}
                                  />
                                </div>
                                <span className="text-sm font-medium text-gray-700">
                                  {reportDetail.reporter.credibility_score}
                                </span>
                              </div>
                            </div>
                          )}
                        </div>
                      </div>
                    </div>

                    {/* Timestamps */}
                    <div className="grid grid-cols-2 gap-4">
                      <div className="bg-gray-50 p-4 rounded-xl">
                        <p className="text-xs text-gray-500 mb-1">Created</p>
                        <p className="text-sm font-medium text-gray-900">{formatDate(reportDetail.created_at)}</p>
                      </div>
                      {(reportDetail.verification?.verified_at || reportDetail.verified_at) && (
                        <div className="bg-gray-50 p-4 rounded-xl">
                          <p className="text-xs text-gray-500 mb-1">Verified</p>
                          <p className="text-sm font-medium text-gray-900">{formatDate(reportDetail.verification?.verified_at || reportDetail.verified_at)}</p>
                        </div>
                      )}
                    </div>
                  </div>
                ) : (
                  <div className="text-center py-12">
                    <AlertCircle className="w-12 h-12 text-gray-300 mx-auto mb-4" />
                    <p className="text-gray-600">Failed to load report details</p>
                  </div>
                )}
              </div>

              {/* Modal Footer - Actions */}
              {reportDetail && needsAction(selectedReport) && (
                <div className="p-6 border-t border-gray-100 bg-gray-50">
                  <div className="flex items-center justify-between">
                    <button
                      onClick={() => handleRerun(selectedReport.report_id || selectedReport.id)}
                      disabled={processing}
                      className="flex items-center gap-2 px-4 py-2.5 text-sm font-medium text-purple-700 bg-purple-100 rounded-xl hover:bg-purple-200 disabled:opacity-50 transition-colors"
                    >
                      <RotateCcw className="w-4 h-4" />
                      Re-run Verification
                    </button>
                    <div className="flex items-center gap-3">
                      <button
                        onClick={() => openDecisionModal('reject', selectedReport.report_id || selectedReport.id)}
                        disabled={processing}
                        className="flex items-center gap-2 px-6 py-2.5 text-sm font-medium text-white bg-red-600 rounded-xl hover:bg-red-700 disabled:opacity-50 transition-colors"
                      >
                        <ThumbsDown className="w-4 h-4" />
                        Reject
                      </button>
                      <button
                        onClick={() => openDecisionModal('approve', selectedReport.report_id || selectedReport.id)}
                        disabled={processing}
                        className="flex items-center gap-2 px-6 py-2.5 text-sm font-medium text-white bg-green-600 rounded-xl hover:bg-green-700 disabled:opacity-50 transition-colors"
                      >
                        <ThumbsUp className="w-4 h-4" />
                        Approve
                      </button>
                    </div>
                  </div>
                </div>
              )}
            </div>
          </div>
        )}

        {/* Decision Confirmation Modal */}
        {decisionModal.show && (
          <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-[60] p-4">
            <div className="bg-white rounded-2xl shadow-xl max-w-md w-full p-6">
              <div className="text-center mb-6">
                {decisionModal.type === 'approve' ? (
                  <div className="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-4">
                    <ThumbsUp className="w-8 h-8 text-green-600" />
                  </div>
                ) : (
                  <div className="w-16 h-16 bg-red-100 rounded-full flex items-center justify-center mx-auto mb-4">
                    <ThumbsDown className="w-8 h-8 text-red-600" />
                  </div>
                )}
                <h3 className="text-xl font-semibold text-gray-900">
                  {decisionModal.type === 'approve' ? 'Approve Report' : 'Reject Report'}
                </h3>
                <p className="text-gray-500 mt-2">
                  {decisionModal.type === 'approve'
                    ? 'This will verify the report and create a ticket for authorities.'
                    : 'This will reject the report and notify the reporter.'}
                </p>
              </div>

              <div className="mb-6">
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Reason (optional - min 10 characters if provided)
                </label>
                <textarea
                  value={decisionReason}
                  onChange={(e) => setDecisionReason(e.target.value)}
                  placeholder={decisionModal.type === 'approve'
                    ? 'e.g., Report verified after manual review...'
                    : 'e.g., Insufficient evidence, duplicate report...'}
                  className="w-full px-4 py-3 border border-gray-200 rounded-xl focus:ring-2 focus:ring-blue-500 focus:border-blue-500 resize-none"
                  rows={3}
                />
                {decisionReason.trim().length > 0 && decisionReason.trim().length < 10 && (
                  <p className="text-xs text-amber-600 mt-1">
                    Reason is too short. Default reason will be used.
                  </p>
                )}
              </div>

              <div className="flex items-center gap-3">
                <button
                  onClick={() => setDecisionModal({ show: false, type: null, reportId: null })}
                  className="flex-1 px-4 py-2.5 text-sm font-medium text-gray-700 bg-gray-100 rounded-xl hover:bg-gray-200 transition-colors"
                >
                  Cancel
                </button>
                <button
                  onClick={handleDecision}
                  disabled={processing}
                  className={`flex-1 px-4 py-2.5 text-sm font-medium text-white rounded-xl transition-colors disabled:opacity-50 ${
                    decisionModal.type === 'approve'
                      ? 'bg-green-600 hover:bg-green-700'
                      : 'bg-red-600 hover:bg-red-700'
                  }`}
                >
                  {processing ? (
                    <Loader2 className="w-4 h-4 animate-spin mx-auto" />
                  ) : (
                    `Confirm ${decisionModal.type === 'approve' ? 'Approval' : 'Rejection'}`
                  )}
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </DashboardLayout>
  );
}

// Wrap with Suspense for useSearchParams
export default function ReportsPage() {
  return (
    <Suspense fallback={
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="text-center">
          <Loader2 className="w-8 h-8 animate-spin text-blue-600 mx-auto mb-4" />
          <p className="text-gray-600">Loading reports...</p>
        </div>
      </div>
    }>
      <UnifiedReportsPage />
    </Suspense>
  );
}
