'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { motion, AnimatePresence } from 'framer-motion';
import ProtectedRoute from '@/components/ProtectedRoute';
import DashboardLayout from '@/components/DashboardLayout';
import useAuthStore from '@/context/AuthContext';
import Cookies from 'js-cookie';
import {
  FileText,
  Clock,
  CheckCircle,
  XCircle,
  AlertTriangle,
  MapPin,
  Calendar,
  Loader2,
  Eye,
  Trash2,
  Image as ImageIcon,
  Shield,
  Waves,
  Wind,
  Zap,
  Droplets,
  ArrowDownRight,
  Activity,
  ChevronDown,
  ChevronUp,
  Gauge,
  Info,
  Ticket,
  MessageSquare,
  Plus
} from 'lucide-react';
import toast, { Toaster } from 'react-hot-toast';
import { ThreatBadge } from '@/components/ThreatClassificationCard';
import VerificationStatus, { VerificationBadge } from '@/components/VerificationStatus';
import { formatDateIST, formatDateTimeIST } from '@/lib/dateUtils';
import PageHeader from '@/components/PageHeader';
import { getImageUrl } from '@/lib/api';

function MyReportsContent() {
  const router = useRouter();
  const { user } = useAuthStore();
  const [reports, setReports] = useState([]);
  const [filteredReports, setFilteredReports] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [activeFilter, setActiveFilter] = useState('all');
  const [expandedReports, setExpandedReports] = useState({});

  // Toggle expanded state for a report
  const toggleExpanded = (reportId) => {
    setExpandedReports(prev => ({
      ...prev,
      [reportId]: !prev[reportId]
    }));
  };

  // Fetch user's reports
  useEffect(() => {
    const fetchUserReports = async () => {
      try {
        setIsLoading(true);

        // Get token from cookies (stored as 'access_token')
        const token = Cookies.get('access_token');

        if (!token) {
          console.error('No access token found in cookies');
          toast.error('Please login to view your reports');
          router.push('/login');
          return;
        }

        console.log('Access token found:', token.substring(0, 20) + '...');

        const response = await fetch(
          `${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1'}/hazards/my-reports`,
          {
            headers: {
              'Authorization': `Bearer ${token}`,
              'Content-Type': 'application/json'
            }
          }
        );

        if (!response.ok) {
          const errorData = await response.json().catch(() => ({}));
          console.error('API Error:', response.status, errorData);

          if (response.status === 401) {
            toast.error('Session expired. Please login again.');
            Cookies.remove('access_token');
            Cookies.remove('refresh_token');
            router.push('/login');
            return;
          }

          throw new Error(errorData.detail || 'Failed to fetch reports');
        }

        const data = await response.json();
        console.log('User reports:', data);

        // Handle both array and object response formats
        let reportsArray = [];
        if (Array.isArray(data)) {
          reportsArray = data;
        } else if (data.reports && Array.isArray(data.reports)) {
          reportsArray = data.reports;
        } else if (data.data && Array.isArray(data.data)) {
          reportsArray = data.data;
        }

        console.log('Reports array:', reportsArray);

        // Transform the data
        const transformedReports = reportsArray.map(report => ({
          id: report._id || report.id,
          report_id: report.report_id,
          hazard_type: report.hazard_type,
          category: report.category,
          description: report.description,
          location: report.location?.address || 'Unknown Location',
          coordinates: report.location?.coordinates || [0, 0],
          image_url: report.image_url,
          verification_status: report.verification_status,
          verification_score: report.verification_score,
          verification_result: report.verification_result,
          verification_notes: report.verification_notes,
          rejection_reason: report.rejection_reason,
          created_at: report.created_at,
          likes: report.likes || 0,
          comments: report.comments || 0,
          views: report.views || 0,
          // Hazard classification data (from enrichment)
          hazard_classification: report.hazard_classification || null,
          environmental_snapshot: report.environmental_snapshot || null,
          threat_level: report.hazard_classification?.threat_level || null
        }));

        console.log('Transformed reports:', transformedReports);
        setReports(transformedReports);
        setFilteredReports(transformedReports);
      } catch (error) {
        console.error('Error fetching reports:', error);
        toast.error(error.message || 'Failed to load your reports');
        // Set empty array on error so UI shows empty state
        setReports([]);
        setFilteredReports([]);
      } finally {
        setIsLoading(false);
      }
    };

    fetchUserReports();
  }, [router]);

  // Filter reports based on status
  useEffect(() => {
    if (activeFilter === 'all') {
      setFilteredReports(reports);
    } else if (activeFilter === 'under_review') {
      // Combine pending, needs_manual_review, and ai_recommended statuses
      setFilteredReports(reports.filter(r =>
        r.verification_status === 'pending' ||
        r.verification_status === 'needs_manual_review' ||
        r.verification_status === 'ai_recommended'
      ));
    } else {
      setFilteredReports(reports.filter(r => r.verification_status === activeFilter));
    }
  }, [activeFilter, reports]);

  // Calculate stats - count pending, needs_manual_review, and ai_recommended together as "Under Review"
  const stats = {
    total: reports.length,
    under_review: reports.filter(r =>
      r.verification_status === 'pending' ||
      r.verification_status === 'needs_manual_review' ||
      r.verification_status === 'ai_recommended'
    ).length,
    verified: reports.filter(r => r.verification_status === 'verified').length,
    rejected: reports.filter(r => r.verification_status === 'rejected').length,
    auto_approved: reports.filter(r => r.verification_status === 'auto_approved').length,
    auto_rejected: reports.filter(r => r.verification_status === 'auto_rejected').length
  };

  const filters = [
    { id: 'all', label: 'All Reports', count: stats.total },
    { id: 'under_review', label: 'Under Review', count: stats.under_review },
    { id: 'verified', label: 'Verified', count: stats.verified },
    { id: 'rejected', label: 'Rejected', count: stats.rejected },
    { id: 'auto_approved', label: 'Accepted by AI', count: stats.auto_approved },
    { id: 'auto_rejected', label: 'Rejected by AI', count: stats.auto_rejected }
  ];

  const getStatusColor = (status) => {
    switch (status) {
      case 'verified':
        return 'bg-green-100 text-green-700 border-green-200';
      case 'pending':
      case 'needs_manual_review':
      case 'ai_recommended':
        return 'bg-yellow-100 text-yellow-700 border-yellow-200';
      case 'rejected':
        return 'bg-red-100 text-red-700 border-red-200';
      case 'auto_approved':
        return 'bg-[#e8f4fc] text-[#083a57] border-[#9ecbec]';
      case 'auto_rejected':
        return 'bg-purple-100 text-purple-700 border-purple-200';
      default:
        return 'bg-gray-100 text-gray-700 border-gray-200';
    }
  };

  const getStatusIcon = (status) => {
    switch (status) {
      case 'verified':
        return <CheckCircle className="w-4 h-4" />;
      case 'pending':
      case 'needs_manual_review':
      case 'ai_recommended':
        return <AlertTriangle className="w-4 h-4" />;
      case 'rejected':
        return <XCircle className="w-4 h-4" />;
      case 'auto_approved':
        return <CheckCircle className="w-4 h-4" />;
      case 'auto_rejected':
        return <AlertTriangle className="w-4 h-4" />;
      default:
        return <FileText className="w-4 h-4" />;
    }
  };

  const getStatusLabel = (status) => {
    switch (status) {
      case 'pending':
      case 'needs_manual_review':
      case 'ai_recommended':
        return 'Under Review';
      case 'auto_approved':
        return 'Accepted by AI';
      case 'auto_rejected':
        return 'Rejected by AI';
      default:
        return status;
    }
  };

  const formatDate = (dateString) => {
    return formatDateIST(dateString);
  };

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      className="p-4 lg:p-6 pb-24 lg:pb-8"
    >
      <Toaster position="top-center" />

      {/* Page Header */}
      <PageHeader
        showGreeting={true}
        subtitle="Track the status of your hazard reports"
      />

      {/* Mobile Header */}
      <motion.div
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        className="mb-6 lg:hidden"
      >
        <h1 className="text-2xl font-semibold text-slate-900 flex items-center gap-3">
          <div className="w-10 h-10 bg-gradient-to-br from-[#0d4a6f] to-[#083a57] rounded-xl flex items-center justify-center shadow-lg shadow-[#0d4a6f]/20">
            <FileText className="w-5 h-5 text-white" />
          </div>
          My Reports
        </h1>
        <p className="text-slate-500 mt-1 ml-13">Track the status of your hazard reports</p>
      </motion.div>

      {/* Stats Cards */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.1 }}
        className="grid grid-cols-2 lg:grid-cols-4 gap-3 mb-6"
      >
        <div className="bg-white rounded-2xl shadow-sm border border-slate-100 p-4 hover:shadow-md transition-shadow">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs text-slate-500 font-medium">Total</span>
            <div className="w-8 h-8 bg-[#e8f4fc] rounded-xl flex items-center justify-center">
              <FileText className="w-4 h-4 text-[#0d4a6f]" />
            </div>
          </div>
          <p className="text-2xl font-semibold text-slate-900">{stats.total}</p>
        </div>

        <div className="bg-white rounded-2xl shadow-sm border border-slate-100 p-4 hover:shadow-md transition-shadow">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs text-slate-500 font-medium">Under Review</span>
            <div className="w-8 h-8 bg-amber-100 rounded-xl flex items-center justify-center">
              <AlertTriangle className="w-4 h-4 text-amber-600" />
            </div>
          </div>
          <p className="text-2xl font-semibold text-amber-600">{stats.under_review}</p>
        </div>

        <div className="bg-white rounded-2xl shadow-sm border border-slate-100 p-4 hover:shadow-md transition-shadow">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs text-slate-500 font-medium">Verified</span>
            <div className="w-8 h-8 bg-emerald-100 rounded-xl flex items-center justify-center">
              <CheckCircle className="w-4 h-4 text-emerald-600" />
            </div>
          </div>
          <p className="text-2xl font-semibold text-emerald-600">{stats.verified}</p>
        </div>

        <div className="bg-white rounded-2xl shadow-sm border border-slate-100 p-4 hover:shadow-md transition-shadow">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs text-slate-500 font-medium">Rejected</span>
            <div className="w-8 h-8 bg-red-100 rounded-xl flex items-center justify-center">
              <XCircle className="w-4 h-4 text-red-600" />
            </div>
          </div>
          <p className="text-2xl font-semibold text-red-600">{stats.rejected}</p>
        </div>
      </motion.div>

      {/* Filter Tabs */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.2 }}
        className="bg-white rounded-2xl shadow-sm border border-slate-100 p-1.5 mb-6"
      >
        <div className="flex space-x-1 overflow-x-auto scrollbar-hide">
          {filters.map((filter) => (
            <button
              key={filter.id}
              onClick={() => setActiveFilter(filter.id)}
              className={`flex-1 min-w-fit px-4 py-2.5 rounded-xl text-sm font-medium transition-all ${activeFilter === filter.id
                  ? 'bg-[#0d4a6f] text-white shadow-sm'
                  : 'text-slate-600 hover:bg-slate-50'
                }`}
            >
              {filter.label}
              {filter.count > 0 && (
                <span className={`ml-2 px-2 py-0.5 rounded-full text-xs ${activeFilter === filter.id
                    ? 'bg-white/20'
                    : 'bg-slate-100'
                  }`}>
                  {filter.count}
                </span>
              )}
            </button>
          ))}
        </div>
      </motion.div>

      {/* Reports List */}
      {isLoading ? (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          className="bg-white rounded-2xl shadow-sm border border-slate-100 p-12 flex flex-col items-center justify-center"
        >
          <div className="relative w-16 h-16 mb-4">
            <div className="absolute inset-0 border-4 border-[#c5e1f5] rounded-full" />
            <div className="absolute inset-0 border-4 border-t-[#0d4a6f] rounded-full animate-spin" />
            <FileText className="absolute inset-0 m-auto w-6 h-6 text-[#1a6b9a]" />
          </div>
          <p className="text-slate-600 font-medium">Loading your reports...</p>
          <p className="text-slate-400 text-sm mt-1">Please wait</p>
        </motion.div>
      ) : filteredReports.length === 0 ? (
        <motion.div
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          className="bg-white rounded-2xl shadow-sm border border-slate-100 p-12 text-center"
        >
          <div className="w-20 h-20 bg-gradient-to-br from-slate-100 to-slate-50 rounded-2xl flex items-center justify-center mx-auto mb-5 shadow-inner">
            <FileText className="w-10 h-10 text-slate-300" />
          </div>
          <h3 className="text-xl font-semibold text-slate-900 mb-2">
            {activeFilter === 'all' ? 'No Reports Yet' : `No ${activeFilter} Reports`}
          </h3>
          <p className="text-slate-500 mb-6 max-w-sm mx-auto">
            {activeFilter === 'all'
              ? "You haven't submitted any hazard reports yet. Help keep your community safe!"
              : `You don't have any ${activeFilter} reports.`}
          </p>
          {activeFilter === 'all' && (
            <motion.button
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
              onClick={() => router.push('/report-hazard')}
              className="inline-flex items-center gap-2 px-6 py-3 bg-gradient-to-r from-orange-500 to-red-500 text-white rounded-xl font-semibold shadow-lg shadow-orange-500/25 hover:shadow-xl hover:shadow-orange-500/30 transition-all"
            >
              <Plus className="w-5 h-5" />
              Report Your First Hazard
            </motion.button>
          )}
        </motion.div>
      ) : (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.3 }}
          className="space-y-4"
        >
          <AnimatePresence>
            {filteredReports.map((report, index) => (
              <motion.div
                key={report.id}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -20 }}
                transition={{ delay: index * 0.05 }}
                className="bg-white rounded-2xl shadow-sm border border-slate-100 overflow-hidden hover:shadow-lg hover:border-slate-200 transition-all group"
              >
              <div className="flex flex-col md:flex-row">
                {/* Image */}
                <div className="relative w-full md:w-48 h-48 bg-slate-100 flex-shrink-0 overflow-hidden">
                  {report.image_url ? (
                    <img
                      src={getImageUrl(report.image_url)}
                      alt={report.hazard_type}
                      className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
                      onError={(e) => {
                        console.error('Image failed to load:', report.image_url);
                        e.target.style.display = 'none';
                        e.target.nextSibling.style.display = 'flex';
                      }}
                    />
                  ) : null}
                  <div className={`w-full h-full flex items-center justify-center bg-gradient-to-br from-slate-100 to-slate-50 ${report.image_url ? 'hidden' : ''}`}>
                    <ImageIcon className="w-12 h-12 text-slate-300" />
                  </div>
                </div>

                {/* Content */}
                <div className="flex-1 p-5">
                  <div className="flex items-start justify-between mb-3">
                    <div className="flex-1">
                      <div className="flex items-center flex-wrap gap-2 mb-2">
                        <h3 className="text-lg font-semibold text-slate-900 capitalize">
                          {report.hazard_type.replace('_', ' ')}
                        </h3>
                        <span className={`px-2.5 py-1 rounded-full text-xs font-semibold border flex items-center space-x-1 ${getStatusColor(report.verification_status)}`}>
                          {getStatusIcon(report.verification_status)}
                          <span className="capitalize">{getStatusLabel(report.verification_status)}</span>
                        </span>
                        {report.verification_score !== undefined && report.verification_score !== null && (
                          <span className={`px-2.5 py-1 rounded-full text-xs font-semibold flex items-center gap-1 ${
                            report.verification_score >= 85 ? 'bg-emerald-100 text-emerald-700' :
                            report.verification_score >= 40 ? 'bg-amber-100 text-amber-700' :
                            'bg-red-100 text-red-700'
                          }`}>
                            <Gauge className="w-3 h-3" />
                            {Math.round(report.verification_score)}%
                          </span>
                        )}
                        {report.threat_level && (
                          <ThreatBadge level={report.threat_level} size="sm" />
                        )}
                      </div>
                      <p className="text-sm text-slate-600 line-clamp-2 mb-3">
                        {report.description || 'No description provided'}
                      </p>
                      {/* Verification Status Message for Citizens */}
                      <VerificationStatusMessage report={report} />
                    </div>
                  </div>

                  <div className="flex flex-wrap items-center gap-4 text-xs text-slate-500">
                    <div className="flex items-center space-x-1">
                      <MapPin className="w-3.5 h-3.5 text-[#0d4a6f]" />
                      <span>{report.location}</span>
                    </div>
                    <div className="flex items-center space-x-1">
                      <Calendar className="w-3.5 h-3.5 text-slate-400" />
                      <span>{formatDate(report.created_at)}</span>
                    </div>
                    <div className="flex items-center space-x-1">
                      <AlertTriangle className="w-3.5 h-3.5 text-amber-500" />
                      <span className="capitalize">{report.category}</span>
                    </div>
                  </div>

                  {/* Stats & Expand Button */}
                  <div className="flex items-center justify-between mt-4 pt-4 border-t border-slate-100">
                    <div className="flex items-center space-x-4">
                      <div className="flex items-center space-x-1 text-xs text-slate-500">
                        <Eye className="w-3.5 h-3.5" />
                        <span>{report.views} views</span>
                      </div>
                      <div className="flex items-center space-x-1 text-xs text-slate-500">
                        <span>{report.likes}</span>
                      </div>
                      <div className="flex items-center space-x-1 text-xs text-slate-500">
                        <span>{report.comments}</span>
                      </div>
                    </div>
                    {report.hazard_classification && (
                      <button
                        onClick={() => toggleExpanded(report.id)}
                        className="flex items-center gap-1 text-xs text-[#0d4a6f] hover:text-[#083a57] font-medium transition-colors"
                      >
                        <Shield className="w-3.5 h-3.5" />
                        {expandedReports[report.id] ? 'Hide' : 'View'} Analysis
                        {expandedReports[report.id] ? (
                          <ChevronUp className="w-3.5 h-3.5" />
                        ) : (
                          <ChevronDown className="w-3.5 h-3.5" />
                        )}
                      </button>
                    )}
                  </div>

                  {/* Expanded Hazard Classification Details */}
                  <AnimatePresence>
                    {expandedReports[report.id] && report.hazard_classification && (
                    <motion.div
                      initial={{ opacity: 0, height: 0 }}
                      animate={{ opacity: 1, height: 'auto' }}
                      exit={{ opacity: 0, height: 0 }}
                      className="mt-4 p-4 bg-slate-50 rounded-xl border border-slate-100"
                    >
                      <h4 className="text-sm font-semibold text-slate-900 mb-3 flex items-center gap-2">
                        <Shield className="w-4 h-4 text-[#0d4a6f]" />
                        Hazard Analysis
                      </h4>

                      {/* Individual Threat Levels */}
                      <div className="grid grid-cols-5 gap-2 mb-4">
                        <ThreatIndicator
                          icon={Waves}
                          label="Tsunami"
                          level={report.hazard_classification.tsunami_threat}
                        />
                        <ThreatIndicator
                          icon={Wind}
                          label="Cyclone"
                          level={report.hazard_classification.cyclone_threat}
                        />
                        <ThreatIndicator
                          icon={Waves}
                          label="High Waves"
                          level={report.hazard_classification.high_waves_threat}
                        />
                        <ThreatIndicator
                          icon={Droplets}
                          label="Flood"
                          level={report.hazard_classification.coastal_flood_threat}
                        />
                        <ThreatIndicator
                          icon={ArrowDownRight}
                          label="Rip Current"
                          level={report.hazard_classification.rip_current_threat}
                        />
                      </div>

                      {/* Reasoning */}
                      {report.hazard_classification.reasoning && (
                        <p className="text-xs text-gray-600 mb-3">
                          <span className="font-semibold">Analysis: </span>
                          {report.hazard_classification.reasoning}
                        </p>
                      )}

                      {/* Recommendations */}
                      {report.hazard_classification.recommendations?.length > 0 && (
                        <div>
                          <p className="text-xs font-semibold text-slate-700 mb-2">Recommendations:</p>
                          <ul className="space-y-1">
                            {report.hazard_classification.recommendations.slice(0, 3).map((rec, idx) => (
                              <li key={idx} className="text-xs text-slate-600 flex items-start gap-2">
                                <span className="w-4 h-4 bg-[#e8f4fc] text-[#083a57] rounded-full flex items-center justify-center flex-shrink-0 text-[10px] font-semibold">
                                  {idx + 1}
                                </span>
                                {rec}
                              </li>
                            ))}
                          </ul>
                        </div>
                      )}

                      {/* Confidence */}
                      {report.hazard_classification.confidence && (
                        <div className="mt-3 pt-3 border-t border-slate-200 flex items-center justify-between">
                          <span className="text-xs text-slate-500">
                            Confidence: {Math.round(report.hazard_classification.confidence * 100)}%
                          </span>
                          {report.hazard_classification.classified_at && (
                            <span className="text-xs text-slate-400">
                              Analyzed {formatDateIST(report.hazard_classification.classified_at)}
                            </span>
                          )}
                        </div>
                      )}
                    </motion.div>
                  )}
                  </AnimatePresence>
                </div>
              </div>
            </motion.div>
          ))}
          </AnimatePresence>
        </motion.div>
      )}
    </motion.div>
  );
}

// Verification status message for citizens
function VerificationStatusMessage({ report }) {
  const router = useRouter();
  const { verification_status, rejection_reason, verification_notes } = report;

  const getMessage = () => {
    switch (verification_status?.toLowerCase()) {
      case 'verified':
      case 'auto_approved':
        return {
          icon: CheckCircle,
          text: 'Your report has been verified and a ticket has been created.',
          color: 'text-emerald-700',
          bg: 'bg-emerald-50',
          border: 'border-emerald-200',
          showTicketButton: true
        };
      case 'pending':
      case 'needs_manual_review':
      case 'ai_recommended':
        return {
          icon: AlertTriangle,
          text: 'Your report is under review by an analyst for additional verification.',
          color: 'text-amber-700',
          bg: 'bg-amber-50',
          border: 'border-amber-200',
          showTicketButton: false
        };
      case 'rejected':
      case 'auto_rejected':
        return {
          icon: XCircle,
          text: rejection_reason || 'Your report did not pass verification. Please ensure reports are accurate and include clear details.',
          color: 'text-red-700',
          bg: 'bg-red-50',
          border: 'border-red-200',
          showTicketButton: false
        };
      default:
        return null;
    }
  };

  const message = getMessage();
  if (!message) return null;

  const Icon = message.icon;

  return (
    <div className={`rounded-xl p-3 ${message.bg} ${message.border} border mb-2`}>
      <div className="flex items-start justify-between gap-2">
        <div className="flex items-start gap-2 flex-1">
          <Icon className={`w-4 h-4 ${message.color} flex-shrink-0 mt-0.5`} />
          <div className="flex-1">
            <p className={`text-xs ${message.color}`}>{message.text}</p>
            {verification_notes && (
              <p className="text-xs text-slate-500 mt-1.5 italic">
                Note: {verification_notes}
              </p>
            )}
          </div>
        </div>
        {message.showTicketButton && (
          <motion.button
            whileHover={{ scale: 1.02 }}
            whileTap={{ scale: 0.98 }}
            onClick={(e) => {
              e.stopPropagation();
              router.push('/my-tickets');
            }}
            className="flex items-center gap-1 px-3 py-1.5 bg-[#0d4a6f] text-white text-xs font-medium rounded-lg hover:bg-[#083a57] transition-colors flex-shrink-0 shadow-sm"
          >
            <Ticket className="w-3 h-3" />
            View Ticket
          </motion.button>
        )}
      </div>
    </div>
  );
}

// Threat indicator helper component
function ThreatIndicator({ icon: Icon, label, level }) {
  const getIndicatorColor = (level) => {
    switch (level?.toLowerCase()) {
      case 'warning':
        return { bg: 'bg-red-100', text: 'text-red-700', dot: 'bg-red-500' };
      case 'alert':
        return { bg: 'bg-orange-100', text: 'text-orange-700', dot: 'bg-orange-500' };
      case 'watch':
        return { bg: 'bg-amber-100', text: 'text-amber-700', dot: 'bg-amber-500' };
      case 'no_threat':
      default:
        return { bg: 'bg-emerald-100', text: 'text-emerald-700', dot: 'bg-emerald-500' };
    }
  };

  const color = getIndicatorColor(level);

  return (
    <div className={`${color.bg} rounded-xl p-2 text-center`}>
      <Icon className={`w-4 h-4 ${color.text} mx-auto mb-1`} />
      <p className="text-[10px] font-medium text-slate-600 truncate">{label}</p>
      <div className="flex items-center justify-center gap-1 mt-1">
        <span className={`w-1.5 h-1.5 rounded-full ${color.dot}`}></span>
        <span className={`text-[10px] font-semibold ${color.text} uppercase`}>
          {level?.replace('_', ' ') || 'OK'}
        </span>
      </div>
    </div>
  );
}

export default function MyReportsPage() {
  return (
    <ProtectedRoute>
      <DashboardLayout>
        <MyReportsContent />
      </DashboardLayout>
    </ProtectedRoute>
  );
}
