'use client';

import { useState } from 'react';
import {
  CheckCircle,
  XCircle,
  Clock,
  AlertTriangle,
  Shield,
  ChevronDown,
  ChevronUp,
  Loader2,
  RefreshCw,
  Zap,
  TrendingUp,
  MapPin,
  Sun,
  FileText,
  Image as ImageIcon,
  User
} from 'lucide-react';

/**
 * Verification Status Component
 * Displays the verification status of a hazard report with score and breakdown
 */
export default function VerificationStatus({
  report,
  showDetails = false,
  compact = false,
  onRerunVerification = null
}) {
  const [expanded, setExpanded] = useState(showDetails);

  if (!report) return null;

  const {
    verification_status,
    verification_score,
    verification_result,
    verification_notes,
    rejection_reason
  } = report;

  // Get status configuration
  const getStatusConfig = (status) => {
    switch (status?.toLowerCase()) {
      case 'verified':
        return {
          icon: CheckCircle,
          label: 'Verified',
          description: 'This report has been verified and approved',
          bg: 'bg-gradient-to-br from-green-500 to-emerald-600',
          lightBg: 'bg-green-50',
          text: 'text-white',
          lightText: 'text-green-700',
          border: 'border-green-500',
          badge: 'bg-green-100 text-green-800'
        };
      case 'pending':
      case 'ai_recommended':
        // Treat pending and ai_recommended same as needs_manual_review
        return {
          icon: AlertTriangle,
          label: 'Under Review',
          description: 'This report is being reviewed by an analyst',
          bg: 'bg-gradient-to-br from-yellow-500 to-amber-600',
          lightBg: 'bg-yellow-50',
          text: 'text-white',
          lightText: 'text-yellow-700',
          border: 'border-yellow-500',
          badge: 'bg-yellow-100 text-yellow-800'
        };
      case 'needs_manual_review':
        return {
          icon: AlertTriangle,
          label: 'Under Review',
          description: 'This report is being reviewed by an analyst',
          bg: 'bg-gradient-to-br from-yellow-500 to-amber-600',
          lightBg: 'bg-yellow-50',
          text: 'text-white',
          lightText: 'text-yellow-700',
          border: 'border-yellow-500',
          badge: 'bg-yellow-100 text-yellow-800'
        };
      case 'rejected':
        return {
          icon: XCircle,
          label: 'Rejected',
          description: rejection_reason || 'This report did not pass verification',
          bg: 'bg-gradient-to-br from-red-500 to-rose-600',
          lightBg: 'bg-red-50',
          text: 'text-white',
          lightText: 'text-red-700',
          border: 'border-red-500',
          badge: 'bg-red-100 text-red-800'
        };
      case 'auto_rejected':
        return {
          icon: XCircle,
          label: 'Auto-Rejected',
          description: rejection_reason || 'Automatically rejected by the verification system',
          bg: 'bg-gradient-to-br from-red-600 to-red-700',
          lightBg: 'bg-red-50',
          text: 'text-white',
          lightText: 'text-red-700',
          border: 'border-red-600',
          badge: 'bg-red-100 text-red-800'
        };
      default:
        return {
          icon: Shield,
          label: 'Unknown',
          description: 'Verification status unknown',
          bg: 'bg-gradient-to-br from-gray-500 to-gray-600',
          lightBg: 'bg-gray-50',
          text: 'text-white',
          lightText: 'text-gray-700',
          border: 'border-gray-500',
          badge: 'bg-gray-100 text-gray-800'
        };
    }
  };

  const config = getStatusConfig(verification_status);
  const StatusIcon = config.icon;
  const score = verification_score || 0;

  // Get score color based on thresholds (85% auto-approve, 40% minimum review)
  const getScoreColor = (score) => {
    if (score >= 85) return 'text-green-600';
    if (score >= 40) return 'text-yellow-600';
    return 'text-red-600';
  };

  // Get progress bar color
  const getProgressColor = (score) => {
    if (score >= 85) return 'bg-green-500';
    if (score >= 40) return 'bg-yellow-500';
    return 'bg-red-500';
  };

  // Compact badge version
  if (compact) {
    return (
      <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold ${config.badge}`}>
        <StatusIcon className="w-3.5 h-3.5" />
        {config.label}
        {score > 0 && (
          <span className="ml-1 opacity-75">({Math.round(score)}%)</span>
        )}
      </span>
    );
  }

  return (
    <div className="bg-white rounded-xl shadow-md border border-gray-200 overflow-hidden">
      {/* Header with status - Prominent Green Banner for Verified */}
      <div
        className={`p-5 ${config.bg} ${config.text} cursor-pointer relative overflow-hidden`}
        onClick={() => setExpanded(!expanded)}
      >
        <div className="flex items-center justify-between relative z-10">
          <div className="flex items-center gap-4">
            <div className="w-12 h-12 rounded-full bg-white/20 flex items-center justify-center backdrop-blur-sm">
              <StatusIcon className="w-7 h-7" />
            </div>
            <div>
              <h3 className="text-2xl font-bold">{config.label}</h3>
              <p className="text-sm opacity-90 mt-0.5">{config.description}</p>
            </div>
          </div>
          <div className="flex items-center gap-3">
            {score > 0 && (
              <div className="text-right flex items-center gap-2">
                <div>
                  <p className="text-3xl font-bold">{Math.round(score)}%</p>
                  <p className="text-xs opacity-75">Score</p>
                </div>
                <TrendingUp className="w-6 h-6 opacity-80" />
              </div>
            )}
            {expanded ? (
              <ChevronUp className="w-5 h-5 opacity-70" />
            ) : (
              <ChevronDown className="w-5 h-5 opacity-70" />
            )}
          </div>
        </div>
      </div>

      {/* Expanded content */}
      {expanded && (
        <div className="p-6 space-y-6">
          {/* Score bar - Enhanced with better styling */}
          {score > 0 && (
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-sm font-semibold text-gray-700">Verification Score</span>
                <span className={`text-lg font-bold ${getScoreColor(score)}`}>
                  {Math.round(score)}%
                </span>
              </div>
              <div className="w-full bg-gray-200 rounded-full h-3 overflow-hidden">
                <div
                  className={`h-full rounded-full transition-all duration-500 ${getProgressColor(score)}`}
                  style={{ width: `${Math.min(100, score)}%` }}
                />
              </div>
              <div className="flex justify-between text-xs text-gray-500">
                <span>0% (Reject)</span>
                <span className="text-yellow-600 font-medium">40% (Review)</span>
                <span className="text-green-600 font-medium">85% (Auto-Approve)</span>
                <span>100%</span>
              </div>
            </div>
          )}

          {/* Layer summary if available - Enhanced card design */}
          {verification_result?.layer_results && (
            <div className="space-y-3">
              <h4 className="text-sm font-semibold text-gray-700 flex items-center gap-2">
                <Shield className="w-4 h-4 text-blue-600" />
                Verification Layers
              </h4>
              <div className="grid grid-cols-5 gap-3">
                {verification_result.layer_results.map((layer, index) => (
                  <LayerMiniCard key={index} layer={layer} />
                ))}
              </div>
            </div>
          )}

          {/* Decision reason - Enhanced styling */}
          {verification_result?.decision_reason && (
            <div className={`rounded-xl p-4 ${config.lightBg} border ${config.border}`}>
              <p className={`text-sm font-medium ${config.lightText}`}>
                <span className="font-bold">Decision: </span>
                {verification_result.decision_reason}
              </p>
            </div>
          )}

          {/* Verification notes */}
          {verification_notes && (
            <div className="bg-gray-50 rounded-lg p-3 border border-gray-200">
              <p className="text-sm text-gray-600">
                <span className="font-semibold">Notes: </span>
                {verification_notes}
              </p>
            </div>
          )}

          {/* Action buttons */}
          {onRerunVerification && verification_status !== 'verified' && (
            <div className="pt-2 border-t border-gray-100">
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  onRerunVerification(report.report_id || report.id);
                }}
                className="flex items-center gap-2 px-3 py-2 text-sm font-medium text-sky-600 bg-sky-50 rounded-lg hover:bg-sky-100 transition-colors"
              >
                <RefreshCw className="w-4 h-4" />
                Re-run Verification
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

/**
 * Mini card for displaying a single verification layer
 */
function LayerMiniCard({ layer }) {
  const getLayerIcon = (name) => {
    switch (name?.toLowerCase()) {
      case 'geofence':
        return MapPin;
      case 'weather':
        return Sun;
      case 'text':
        return FileText;
      case 'image':
        return ImageIcon;
      case 'reporter':
        return User;
      default:
        return Shield;
    }
  };

  const getStatusColor = (status, score) => {
    const scoreNum = Math.round((score || 0) * 100);
    switch (status?.toLowerCase()) {
      case 'pass':
      case 'passed':
        if (scoreNum >= 80) {
          return 'bg-green-50 text-green-700 border-green-200';
        } else {
          return 'bg-green-50 text-green-600 border-green-100';
        }
      case 'fail':
      case 'failed':
        return 'bg-red-50 text-red-700 border-red-200';
      case 'skip':
      case 'skipped':
        return 'bg-gray-50 text-gray-500 border-gray-200';
      default:
        return 'bg-gray-50 text-gray-600 border-gray-200';
    }
  };

  const score = Math.round((layer.score || 0) * 100);
  const LayerIcon = getLayerIcon(layer.layer_name);
  const statusColor = getStatusColor(layer.status, layer.score);

  return (
    <div className={`rounded-xl p-3 text-center border-2 ${statusColor} transition-all hover:shadow-md`}>
      <div className="flex justify-center mb-2">
        <LayerIcon className={`w-6 h-6 ${
          layer.status === 'pass' ? 'text-green-600' :
          layer.status === 'fail' ? 'text-red-600' :
          'text-gray-400'
        }`} />
      </div>
      <p className="text-xs font-semibold capitalize mb-1">
        {layer.layer_name?.replace('_', ' ')}
      </p>
      <p className={`text-base font-bold ${
        layer.status === 'pass' ? 'text-green-700' :
        layer.status === 'fail' ? 'text-red-700' :
        'text-gray-500'
      }`}>
        {layer.status === 'skipped' ? 'N/A' : `${score}%`}
      </p>
    </div>
  );
}

/**
 * Verification Status Badge - Compact inline version
 */
export function VerificationBadge({ status, score, size = 'md' }) {
  const config = {
    verified: { bg: 'bg-green-500', icon: CheckCircle },
    pending: { bg: 'bg-yellow-500', icon: AlertTriangle },  // Treat as review needed
    ai_recommended: { bg: 'bg-yellow-500', icon: AlertTriangle },  // Treat as review needed
    needs_manual_review: { bg: 'bg-yellow-500', icon: AlertTriangle },
    rejected: { bg: 'bg-red-500', icon: XCircle },
    auto_rejected: { bg: 'bg-red-600', icon: XCircle }
  };

  const sizeClasses = {
    sm: 'px-2 py-0.5 text-xs gap-1',
    md: 'px-2.5 py-1 text-sm gap-1.5',
    lg: 'px-3 py-1.5 text-base gap-2'
  };

  const iconSizes = {
    sm: 'w-3 h-3',
    md: 'w-4 h-4',
    lg: 'w-5 h-5'
  };

  const statusConfig = config[status?.toLowerCase()] || config.needs_manual_review;
  const Icon = statusConfig.icon;

  // Normalize label - treat pending and ai_recommended as "Under Review"
  const normalizedStatus = status?.toLowerCase();
  let label;
  if (normalizedStatus === 'pending' || normalizedStatus === 'ai_recommended' || normalizedStatus === 'needs_manual_review') {
    label = 'Under Review';
  } else {
    label = status?.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase()) || 'Under Review';
  }

  return (
    <span className={`inline-flex items-center ${statusConfig.bg} text-white rounded-full font-medium ${sizeClasses[size]}`}>
      <Icon className={iconSizes[size]} />
      <span>{label}</span>
      {score !== undefined && score > 0 && (
        <span className="opacity-80">({Math.round(score)}%)</span>
      )}
    </span>
  );
}

/**
 * Auto-approval indicator
 */
export function AutoApprovalIndicator({ eligible, score }) {
  if (!eligible) return null;

  return (
    <div className="inline-flex items-center gap-1.5 px-2 py-1 bg-green-100 text-green-700 rounded-full text-xs font-medium">
      <Zap className="w-3 h-3" />
      <span>Auto-Approved</span>
      {score && <span className="opacity-75">({Math.round(score)}%)</span>}
    </div>
  );
}
