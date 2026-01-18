'use client';

import { useEffect, useState } from 'react';
import { useRouter, useParams } from 'next/navigation';
import DashboardLayout from '@/components/DashboardLayout';
import PageHeader from '@/components/PageHeader';
import useAuthStore from '@/context/AuthContext';
import api, { getImageUrl } from '@/lib/api';
import {
  AlertTriangle,
  CheckCircle,
  XCircle,
  MapPin,
  Calendar,
  User,
  Phone,
  Mail,
  FileText,
  TrendingUp,
  Brain,
  Shield,
  Clock,
  ChevronLeft,
  Image as ImageIcon,
  Award,
  Target,
  Gauge,
  Layers,
  Ticket,
  Zap,
  Activity
} from 'lucide-react';

export default function VerifyReport() {
  const router = useRouter();
  const params = useParams();
  const { user, isLoading: authLoading } = useAuthStore();

  const [report, setReport] = useState(null);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);

  // Verification form state
  const [decision, setDecision] = useState('verified');
  const [riskLevel, setRiskLevel] = useState('');
  const [urgency, setUrgency] = useState('');
  const [notes, setNotes] = useState('');
  const [actionRequired, setActionRequired] = useState(false);
  const [rejectionReason, setRejectionReason] = useState('');

  // Check if user is authority or admin
  useEffect(() => {
    if (!authLoading && user) {
      if (user.role !== 'authority' && user.role !== 'authority_admin') {
        router.push('/dashboard');
      } else {
        fetchReport();
      }
    }
  }, [user, authLoading, params.id]);

  const fetchReport = async () => {
    try {
      setLoading(true);
      const response = await api.get(`/authority/verification-panel/reports/${params.id}`);
      setReport(response.data);

      // Pre-fill form with existing data if already verified
      if (response.data.risk_level) setRiskLevel(response.data.risk_level);
      if (response.data.urgency) setUrgency(response.data.urgency);
      if (response.data.verification_notes) setNotes(response.data.verification_notes);
      if (response.data.requires_immediate_action) setActionRequired(response.data.requires_immediate_action);

    } catch (error) {
      console.error('Error fetching report:', error);
      alert('Failed to load report details');
      router.push('/authority/verification');
    } finally {
      setLoading(false);
    }
  };

  const handleSubmitVerification = async () => {
    try {
      // Validation
      if (!riskLevel) {
        alert('Please select a risk level');
        return;
      }
      if (!urgency) {
        alert('Please select urgency level');
        return;
      }
      if (decision === 'rejected' && !rejectionReason) {
        alert('Please provide a rejection reason');
        return;
      }

      setSubmitting(true);

      const verificationData = {
        status: decision,
        risk_level: riskLevel,
        urgency: urgency,
        notes: notes,
        requires_immediate_action: actionRequired
      };

      if (decision === 'rejected') {
        verificationData.rejection_reason = rejectionReason;
      }

      const response = await api.post(`/authority/verification-panel/reports/${params.id}/verify`, verificationData);

      // If a ticket was created, navigate to it
      if (response.data.ticket_id && decision === 'verified') {
        alert(`Report verified successfully! Ticket ${response.data.ticket_id} has been created.`);
        router.push(`/authority/tickets/${response.data.ticket_id}`);
      } else {
        alert(`Report ${decision === 'verified' ? 'verified' : 'rejected'} successfully`);
        router.push('/authority/verification');
      }

    } catch (error) {
      console.error('Error submitting verification:', error);
      alert('Failed to submit verification');
    } finally {
      setSubmitting(false);
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

  if (!report) {
    return (
      <DashboardLayout>
        <div className="p-6">
          <p className="text-red-600">Report not found</p>
        </div>
      </DashboardLayout>
    );
  }

  return (
    <DashboardLayout>
      <div className="p-6 space-y-6">
        {/* Page Header - Desktop Only */}
        <PageHeader />

        {/* Header with Back Button */}
        <div className="flex items-center gap-4">
          <button
            onClick={() => router.push('/authority/verification')}
            className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
          >
            <ChevronLeft className="w-6 h-6" />
          </button>
          <div className="flex-1">
            <h1 className="text-2xl font-bold text-gray-900">Review Report</h1>
            <p className="text-gray-600">Report ID: {report.report_id}</p>
          </div>
          <div className={`px-4 py-2 rounded-lg font-medium ${
            report.verification_status === 'verified' ? 'bg-green-100 text-green-700' :
            report.verification_status === 'rejected' ? 'bg-red-100 text-red-700' :
            'bg-orange-100 text-orange-700'
          }`}>
            {report.verification_status.toUpperCase()}
          </div>
        </div>

        {/* VERIFICATION SCORE SECTION - PROMINENT DISPLAY */}
        {report.verification_score !== undefined && report.verification_score !== null && (
          <div className="bg-gradient-to-r from-[#0d4a6f] to-[#083a57] rounded-2xl shadow-lg p-6 text-white relative overflow-hidden">
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-3">
                <div className="p-3 bg-white/20 rounded-xl">
                  <Gauge className="w-8 h-8" />
                </div>
                <div>
                  <h2 className="text-xl font-bold">AI Verification Score</h2>
                  <p className="text-[#9ecbec] text-sm">6-Layer Verification Pipeline Result</p>
                </div>
              </div>
              <div className="text-right">
                <div className="text-5xl font-bold">
                  {report.verification_score?.toFixed(1)}%
                </div>
                <div className={`text-sm font-medium px-3 py-1 rounded-full mt-1 inline-block ${
                  report.verification_score >= 75 ? 'bg-green-400/30 text-green-100' :
                  report.verification_score >= 40 ? 'bg-yellow-400/30 text-yellow-100' :
                  'bg-red-400/30 text-red-100'
                }`}>
                  {report.verification_score >= 75 ? 'Auto-Approved' :
                   report.verification_score >= 40 ? 'Manual Review' :
                   'Auto-Rejected'}
                </div>
              </div>
            </div>

            {/* Score Breakdown */}
            {report.verification_result?.layer_results && (
              <div className="grid grid-cols-5 gap-3 mt-6">
                {report.verification_result.layer_results.map((layer, idx) => {
                  const layerScore = (layer.score * 100).toFixed(0);
                  const isPassed = layer.status === 'pass';
                  const layerIcons = {
                    'geofence': '📍',
                    'weather': '🌤️',
                    'text': '📝',
                    'image': '🖼️',
                    'reporter': '👤'
                  };
                  return (
                    <div key={idx} className={`bg-white/10 rounded-lg p-3 text-center ${!isPassed && layer.status !== 'skipped' ? 'ring-2 ring-red-400' : ''}`}>
                      <div className="text-2xl mb-1">{layerIcons[layer.layer_name] || '📊'}</div>
                      <div className="text-xs text-blue-100 capitalize mb-1">{layer.layer_name}</div>
                      <div className={`text-lg font-bold ${isPassed ? 'text-green-300' : layer.status === 'skipped' ? 'text-gray-400' : 'text-red-300'}`}>
                        {layer.status === 'skipped' ? 'N/A' : `${layerScore}%`}
                      </div>
                      <div className={`text-xs mt-1 px-2 py-0.5 rounded-full ${
                        isPassed ? 'bg-green-400/20 text-green-200' :
                        layer.status === 'skipped' ? 'bg-gray-400/20 text-gray-300' :
                        'bg-red-400/20 text-red-200'
                      }`}>
                        {isPassed ? '✓ Pass' : layer.status === 'skipped' ? '○ Skipped' : '✗ Fail'}
                      </div>
                    </div>
                  );
                })}
              </div>
            )}

            {/* Decision Info */}
            {report.verification_result?.decision && (
              <div className="mt-4 pt-4 border-t border-white/20 flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Activity className="w-4 h-4" />
                  <span className="text-sm">AI Decision:</span>
                  <span className="font-semibold capitalize">{report.verification_result.decision.replace('_', ' ')}</span>
                </div>
                {report.verification_result.processing_time_ms && (
                  <div className="text-sm text-blue-200">
                    Processed in {report.verification_result.processing_time_ms}ms
                  </div>
                )}
              </div>
            )}
          </div>
        )}

        {/* Threat Level Alert */}
        {report.hazard_classification?.threat_level && report.hazard_classification.threat_level !== 'no_threat' && (
          <div className={`rounded-xl p-4 flex items-center gap-4 ${
            report.hazard_classification.threat_level === 'warning' ? 'bg-red-100 border-2 border-red-400' :
            report.hazard_classification.threat_level === 'alert' ? 'bg-orange-100 border-2 border-orange-400' :
            'bg-yellow-100 border-2 border-yellow-400'
          }`}>
            <div className={`p-3 rounded-xl ${
              report.hazard_classification.threat_level === 'warning' ? 'bg-red-200' :
              report.hazard_classification.threat_level === 'alert' ? 'bg-orange-200' :
              'bg-yellow-200'
            }`}>
              <Zap className={`w-6 h-6 ${
                report.hazard_classification.threat_level === 'warning' ? 'text-red-700' :
                report.hazard_classification.threat_level === 'alert' ? 'text-orange-700' :
                'text-yellow-700'
              }`} />
            </div>
            <div className="flex-1">
              <div className={`text-lg font-bold ${
                report.hazard_classification.threat_level === 'warning' ? 'text-red-800' :
                report.hazard_classification.threat_level === 'alert' ? 'text-orange-800' :
                'text-yellow-800'
              }`}>
                {report.hazard_classification.threat_level.toUpperCase()} THREAT LEVEL
              </div>
              <div className="text-sm text-gray-700">
                {report.hazard_classification.reasoning || `Detected ${report.hazard_classification.hazard_type || 'potential hazard'}`}
              </div>
            </div>
            {report.hazard_classification.confidence && (
              <div className="text-right">
                <div className="text-sm text-gray-600">Confidence</div>
                <div className="text-xl font-bold">{(report.hazard_classification.confidence * 100).toFixed(0)}%</div>
              </div>
            )}
          </div>
        )}

        {/* Ticket Status Banner */}
        {report.has_ticket && report.ticket_id && (
          <div className="bg-indigo-50 border border-indigo-200 rounded-xl p-4 flex items-center gap-4">
            <div className="p-2 bg-indigo-100 rounded-lg">
              <Ticket className="w-6 h-6 text-indigo-600" />
            </div>
            <div className="flex-1">
              <div className="text-indigo-800 font-semibold">Support Ticket Created</div>
              <div className="text-sm text-indigo-600">Ticket ID: {report.ticket_id}</div>
            </div>
            <div className={`px-3 py-1 rounded-full text-sm font-medium ${
              report.ticket_status === 'open' ? 'bg-green-100 text-green-700' :
              report.ticket_status === 'in_progress' ? 'bg-blue-100 text-blue-700' :
              report.ticket_status === 'resolved' ? 'bg-gray-100 text-gray-700' :
              'bg-gray-100 text-gray-700'
            }`}>
              {report.ticket_status?.toUpperCase() || 'OPEN'}
            </div>
          </div>
        )}

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Left Column - Report Details */}
          <div className="lg:col-span-2 space-y-6">
            {/* Basic Information */}
            <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
              <h2 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
                <FileText className="w-5 h-5 text-[#0d4a6f]" />
                Report Details
              </h2>

              <div className="space-y-4">
                <div>
                  <label className="text-sm font-medium text-gray-600">Hazard Type</label>
                  <p className="text-lg font-semibold text-gray-900 capitalize">
                    {report.hazard_type.replace('_', ' ')}
                  </p>
                </div>

                <div>
                  <label className="text-sm font-medium text-gray-600">Description</label>
                  <p className="text-gray-900 whitespace-pre-wrap">{report.description}</p>
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="text-sm font-medium text-gray-600">Severity</label>
                    <p className={`text-lg font-semibold capitalize ${
                      report.severity === 'high' ? 'text-red-600' :
                      report.severity === 'medium' ? 'text-orange-600' :
                      'text-yellow-600'
                    }`}>
                      {report.severity}
                    </p>
                  </div>

                  <div>
                    <label className="text-sm font-medium text-gray-600">Priority</label>
                    <p className={`text-lg font-semibold capitalize ${
                      report.priority === 'high' ? 'text-red-600' :
                      report.priority === 'medium' ? 'text-orange-600' :
                      'text-yellow-600'
                    }`}>
                      {report.priority || 'Not Set'}
                    </p>
                  </div>
                </div>

                <div>
                  <label className="text-sm font-medium text-gray-600">Reported At</label>
                  <div className="flex items-center gap-2 text-gray-900">
                    <Calendar className="w-4 h-4" />
                    <span>{new Date(report.created_at).toLocaleString()}</span>
                  </div>
                </div>
              </div>
            </div>

            {/* Location Information */}
            <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
              <h2 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
                <MapPin className="w-5 h-5 text-[#0d4a6f]" />
                Location Details
              </h2>

              <div className="space-y-3">
                {/* Coordinates */}
                {report.location?.latitude && report.location?.longitude && (
                  <div>
                    <label className="text-sm font-medium text-gray-600">Coordinates</label>
                    <div className="flex items-center gap-2">
                      <p className="text-gray-900 font-mono">
                        {report.location.latitude.toFixed(6)}, {report.location.longitude.toFixed(6)}
                      </p>
                      <a
                        href={`https://www.google.com/maps?q=${report.location.latitude},${report.location.longitude}`}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-blue-600 hover:text-blue-700 text-sm underline"
                      >
                        View on Map
                      </a>
                    </div>
                  </div>
                )}

                {/* Address */}
                {report.location?.address && (
                  <div>
                    <label className="text-sm font-medium text-gray-600">Address</label>
                    <p className="text-gray-900">{report.location.address}</p>
                  </div>
                )}

                {/* Region (if available) */}
                {report.location?.region && (
                  <div>
                    <label className="text-sm font-medium text-gray-600">Region/State</label>
                    <p className="text-gray-900">{report.location.region}</p>
                  </div>
                )}

                {/* District (if available) */}
                {report.location?.district && (
                  <div>
                    <label className="text-sm font-medium text-gray-600">District/City</label>
                    <p className="text-gray-900">{report.location.district}</p>
                  </div>
                )}
              </div>
            </div>

            {/* Reporter Information (PII) */}
            <div className="bg-amber-50 rounded-xl border border-amber-200 p-6">
              <div className="flex items-center gap-2 mb-4">
                <Shield className="w-5 h-5 text-amber-600" />
                <h2 className="text-lg font-semibold text-gray-900">
                  Reporter Information (PII)
                </h2>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="text-sm font-medium text-gray-600 flex items-center gap-1">
                    <User className="w-4 h-4" />
                    Name
                  </label>
                  <p className="text-gray-900">{report.reporter_name || 'Anonymous'}</p>
                </div>

                {report.reporter_email && (
                  <div>
                    <label className="text-sm font-medium text-gray-600 flex items-center gap-1">
                      <Mail className="w-4 h-4" />
                      Email
                    </label>
                    <p className="text-gray-900">{report.reporter_email}</p>
                  </div>
                )}

                {report.reporter_phone && (
                  <div>
                    <label className="text-sm font-medium text-gray-600 flex items-center gap-1">
                      <Phone className="w-4 h-4" />
                      Phone
                    </label>
                    <p className="text-gray-900">{report.reporter_phone}</p>
                  </div>
                )}

                <div>
                  <label className="text-sm font-medium text-gray-600 flex items-center gap-1">
                    <Award className="w-4 h-4" />
                    Credibility Score
                  </label>
                  <p className="text-gray-900 font-semibold">{report.credibility_score || 0}</p>
                </div>
              </div>
            </div>

            {/* NLP Insights */}
            {(report.nlp_sentiment || report.nlp_keywords || report.nlp_risk_score) && (
              <div className="bg-[#e8f4fc] rounded-xl border border-[#c5e1f5] p-6">
                <h2 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
                  <Brain className="w-5 h-5 text-[#0d4a6f]" />
                  NLP Analysis
                </h2>

                <div className="space-y-4">
                  {report.nlp_sentiment && (
                    <div>
                      <label className="text-sm font-medium text-gray-600">Sentiment</label>
                      <p className={`text-lg font-semibold capitalize ${
                        report.nlp_sentiment === 'negative' ? 'text-red-600' :
                        report.nlp_sentiment === 'positive' ? 'text-green-600' :
                        'text-gray-600'
                      }`}>
                        {report.nlp_sentiment}
                      </p>
                    </div>
                  )}

                  {report.nlp_risk_score !== undefined && (
                    <div>
                      <label className="text-sm font-medium text-gray-600">NLP Risk Score</label>
                      <div className="flex items-center gap-3">
                        <div className="flex-1 bg-gray-200 rounded-full h-3">
                          <div
                            className={`h-3 rounded-full ${
                              report.nlp_risk_score > 0.7 ? 'bg-red-600' :
                              report.nlp_risk_score > 0.4 ? 'bg-orange-600' :
                              'bg-green-600'
                            }`}
                            style={{ width: `${report.nlp_risk_score * 100}%` }}
                          />
                        </div>
                        <span className="text-lg font-semibold">
                          {(report.nlp_risk_score * 100).toFixed(0)}%
                        </span>
                      </div>
                    </div>
                  )}

                  {report.nlp_keywords && report.nlp_keywords.length > 0 && (
                    <div>
                      <label className="text-sm font-medium text-gray-600 mb-2 block">Keywords</label>
                      <div className="flex flex-wrap gap-2">
                        {report.nlp_keywords.map((keyword, idx) => (
                          <span
                            key={idx}
                            className="px-3 py-1 bg-[#e8f4fc] text-[#0d4a6f] rounded-full text-sm"
                          >
                            {keyword}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}

                  {report.nlp_summary && (
                    <div>
                      <label className="text-sm font-medium text-gray-600">AI Summary</label>
                      <p className="text-gray-900">{report.nlp_summary}</p>
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* Hazard Image & Media */}
            <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
              <h2 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
                <ImageIcon className="w-5 h-5 text-[#0d4a6f]" />
                Hazard Evidence
              </h2>

              <div className="space-y-4">
                {/* Main Image */}
                {report.image_url && (
                  <div className="relative group">
                    <div className="relative rounded-lg overflow-hidden border-2 border-gray-200 shadow-lg">
                      <img
                        src={getImageUrl(report.image_url)}
                        alt={report.hazard_type}
                        className="w-full h-96 object-contain bg-gray-50"
                        onError={(e) => {
                          e.target.onerror = null;
                          e.target.src = 'data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMjAwIiBoZWlnaHQ9IjIwMCIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48cmVjdCB3aWR0aD0iMjAwIiBoZWlnaHQ9IjIwMCIgZmlsbD0iI2VlZSIvPjx0ZXh0IHg9IjUwJSIgeT0iNTAlIiBmb250LWZhbWlseT0iQXJpYWwiIGZvbnQtc2l6ZT0iMTQiIGZpbGw9IiM5OTkiIHRleHQtYW5jaG9yPSJtaWRkbGUiIGR5PSIuM2VtIj5JbWFnZSBOb3QgRm91bmQ8L3RleHQ+PC9zdmc+';
                        }}
                      />

                      {/* Image Info Overlay */}
                      <div className="absolute bottom-0 left-0 right-0 bg-gradient-to-t from-black/70 to-transparent p-4">
                        <p className="text-white text-sm font-medium">
                          Reported: {new Date(report.created_at).toLocaleString()}
                        </p>
                      </div>

                      {/* Zoom Button */}
                      <button
                        onClick={() => window.open(getImageUrl(report.image_url), '_blank')}
                        className="absolute top-4 right-4 bg-white/90 hover:bg-white text-gray-700 p-2 rounded-lg shadow-md transition-all opacity-0 group-hover:opacity-100"
                        title="View full size"
                      >
                        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0zM10 7v3m0 0v3m0-3h3m-3 0H7" />
                        </svg>
                      </button>
                    </div>
                  </div>
                )}

                {/* Voice Note */}
                {report.voice_note_url && (
                  <div className="bg-[#e8f4fc] border border-[#c5e1f5] rounded-xl p-4">
                    <div className="flex items-center gap-3 mb-2">
                      <div className="bg-[#0d4a6f] text-white p-2 rounded-xl">
                        <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
                          <path fillRule="evenodd" d="M7 4a3 3 0 016 0v4a3 3 0 11-6 0V4zm4 10.93A7.001 7.001 0 0017 8a1 1 0 10-2 0A5 5 0 015 8a1 1 0 00-2 0 7.001 7.001 0 006 6.93V17H6a1 1 0 100 2h8a1 1 0 100-2h-3v-2.07z" clipRule="evenodd" />
                        </svg>
                      </div>
                      <div className="flex-1">
                        <p className="font-medium text-gray-900">Voice Note Attached</p>
                        <p className="text-sm text-gray-600">Additional details from reporter</p>
                      </div>
                    </div>
                    <audio
                      controls
                      className="w-full mt-2"
                      src={`http://localhost:8000${report.voice_note_url}`}
                    >
                      Your browser does not support the audio element.
                    </audio>
                  </div>
                )}

                {!report.image_url && !report.voice_note_url && (
                  <div className="text-center py-8 text-gray-500">
                    <ImageIcon className="w-12 h-12 mx-auto mb-2 text-gray-400" />
                    <p>No media attached to this report</p>
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* Right Column - Verification Form */}
          <div className="lg:col-span-1">
            <div className="bg-white rounded-xl shadow-lg border border-gray-200 p-6 sticky top-6">
              <h2 className="text-lg font-semibold text-[#0d4a6f] mb-4">
                Verification Decision
              </h2>

              <div className="space-y-4">
                {/* Decision */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Decision
                  </label>
                  <div className="flex gap-2">
                    <button
                      onClick={() => setDecision('verified')}
                      className={`flex-1 py-2 px-4 rounded-lg font-medium transition-colors ${
                        decision === 'verified'
                          ? 'bg-green-600 text-white'
                          : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                      }`}
                    >
                      <CheckCircle className="w-4 h-4 inline mr-1" />
                      Verify
                    </button>
                    <button
                      onClick={() => setDecision('rejected')}
                      className={`flex-1 py-2 px-4 rounded-lg font-medium transition-colors ${
                        decision === 'rejected'
                          ? 'bg-red-600 text-white'
                          : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                      }`}
                    >
                      <XCircle className="w-4 h-4 inline mr-1" />
                      Reject
                    </button>
                  </div>
                </div>

                {/* Rejection Reason (only if rejecting) */}
                {decision === 'rejected' && (
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Rejection Reason *
                    </label>
                    <textarea
                      value={rejectionReason}
                      onChange={(e) => setRejectionReason(e.target.value)}
                      className="w-full px-3 py-2 border border-gray-300 rounded-xl focus:ring-2 focus:ring-red-500"
                      rows="3"
                      placeholder="Explain why this report is being rejected..."
                    />
                  </div>
                )}

                {/* Risk Level */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Risk Level *
                  </label>
                  <select
                    value={riskLevel}
                    onChange={(e) => setRiskLevel(e.target.value)}
                    className="w-full px-3 py-2 border border-gray-300 rounded-xl focus:ring-2 focus:ring-[#1a6b9a]"
                  >
                    <option value="">Select risk level</option>
                    <option value="low">Low</option>
                    <option value="medium">Medium</option>
                    <option value="high">High</option>
                    <option value="critical">Critical</option>
                  </select>
                </div>

                {/* Urgency */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Urgency *
                  </label>
                  <select
                    value={urgency}
                    onChange={(e) => setUrgency(e.target.value)}
                    className="w-full px-3 py-2 border border-gray-300 rounded-xl focus:ring-2 focus:ring-[#1a6b9a]"
                  >
                    <option value="">Select urgency</option>
                    <option value="low">Low - Can wait</option>
                    <option value="medium">Medium - Address soon</option>
                    <option value="high">High - Urgent attention</option>
                    <option value="critical">Critical - Immediate action</option>
                  </select>
                </div>

                {/* Immediate Action Required */}
                <div className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    id="actionRequired"
                    checked={actionRequired}
                    onChange={(e) => setActionRequired(e.target.checked)}
                    className="w-4 h-4 text-[#0d4a6f] border-gray-300 rounded focus:ring-[#1a6b9a]"
                  />
                  <label htmlFor="actionRequired" className="text-sm font-medium text-gray-700">
                    Requires Immediate Action
                  </label>
                </div>

                {/* Verification Notes */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Verification Notes
                  </label>
                  <textarea
                    value={notes}
                    onChange={(e) => setNotes(e.target.value)}
                    className="w-full px-3 py-2 border border-gray-300 rounded-xl focus:ring-2 focus:ring-[#1a6b9a]"
                    rows="4"
                    placeholder="Add any notes or observations about this report..."
                  />
                </div>

                {/* Submit Button */}
                <button
                  onClick={handleSubmitVerification}
                  disabled={submitting}
                  className={`w-full py-3 px-4 rounded-lg font-medium text-white transition-colors ${
                    decision === 'verified'
                      ? 'bg-green-600 hover:bg-green-700'
                      : 'bg-red-600 hover:bg-red-700'
                  } disabled:opacity-50 disabled:cursor-not-allowed`}
                >
                  {submitting ? (
                    <span>Submitting...</span>
                  ) : (
                    <span>
                      {decision === 'verified' ? 'Verify Report' : 'Reject Report'}
                    </span>
                  )}
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </DashboardLayout>
  );
}
