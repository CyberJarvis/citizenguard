'use client';

import { useState } from 'react';
import Link from 'next/link';
import {
  Calendar,
  MapPin,
  Award,
  Download,
  Mail,
  CheckCircle,
  XCircle,
  Clock,
  Loader2,
  ExternalLink,
  Trophy,
  FileText
} from 'lucide-react';
import { generateCertificate, emailCertificate } from '@/lib/api';
import toast from 'react-hot-toast';

const statusConfig = {
  attended: {
    label: 'Attended',
    icon: CheckCircle,
    bg: 'bg-green-100',
    text: 'text-green-700',
    border: 'border-green-200'
  },
  no_show: {
    label: 'No Show',
    icon: XCircle,
    bg: 'bg-red-100',
    text: 'text-red-700',
    border: 'border-red-200'
  },
  registered: {
    label: 'Registered',
    icon: Clock,
    bg: 'bg-blue-100',
    text: 'text-blue-700',
    border: 'border-blue-200'
  },
  confirmed: {
    label: 'Confirmed',
    icon: CheckCircle,
    bg: 'bg-indigo-100',
    text: 'text-indigo-700',
    border: 'border-indigo-200'
  },
  cancelled: {
    label: 'Cancelled',
    icon: XCircle,
    bg: 'bg-gray-100',
    text: 'text-gray-700',
    border: 'border-gray-200'
  }
};

export default function EventHistoryCard({ registration, event }) {
  const [isGenerating, setIsGenerating] = useState(false);
  const [isEmailing, setIsEmailing] = useState(false);
  const [certificateGenerated, setCertificateGenerated] = useState(
    registration?.certificate_generated || false
  );
  const [certificateUrl, setCertificateUrl] = useState(
    registration?.certificate_url || null
  );

  const status = registration?.registration_status?.toLowerCase() || 'registered';
  const statusInfo = statusConfig[status] || statusConfig.registered;
  const StatusIcon = statusInfo.icon;

  const formatDate = (dateStr) => {
    if (!dateStr) return 'TBD';
    const date = new Date(dateStr);
    return date.toLocaleDateString('en-IN', {
      weekday: 'short',
      day: 'numeric',
      month: 'short',
      year: 'numeric'
    });
  };

  const handleGenerateCertificate = async () => {
    setIsGenerating(true);
    try {
      const response = await generateCertificate(event.event_id);
      if (response.success) {
        setCertificateGenerated(true);
        setCertificateUrl(response.certificate_url);
        toast.success('Certificate generated successfully!');
      } else {
        toast.error(response.message || 'Failed to generate certificate');
      }
    } catch (error) {
      console.error('Error generating certificate:', error);
      toast.error(error.response?.data?.detail || 'Failed to generate certificate');
    } finally {
      setIsGenerating(false);
    }
  };

  const handleEmailCertificate = async () => {
    setIsEmailing(true);
    try {
      const response = await emailCertificate(event.event_id);
      if (response.success) {
        toast.success('Certificate sent to your email!');
      } else {
        toast.error(response.message || 'Failed to send email');
      }
    } catch (error) {
      console.error('Error emailing certificate:', error);
      toast.error(error.response?.data?.detail || 'Failed to send email');
    } finally {
      setIsEmailing(false);
    }
  };

  const handleDownload = () => {
    if (certificateUrl) {
      const backendUrl = process.env.NEXT_PUBLIC_API_URL?.replace('/api/v1', '') || 'http://localhost:8000';
      window.open(`${backendUrl}${certificateUrl}`, '_blank');
    }
  };

  const canGetCertificate = status === 'attended';

  return (
    <div className={`bg-white rounded-xl border ${statusInfo.border} shadow-sm overflow-hidden hover:shadow-md transition`}>
      <div className="p-4">
        <div className="flex items-start gap-4">
          {/* Status Badge */}
          <div className={`w-12 h-12 rounded-lg ${statusInfo.bg} flex items-center justify-center flex-shrink-0`}>
            <StatusIcon className={`w-6 h-6 ${statusInfo.text}`} />
          </div>

          {/* Event Info */}
          <div className="flex-1 min-w-0">
            <div className="flex items-start justify-between gap-2">
              <div>
                <Link
                  href={`/events/${event.event_id}`}
                  className="font-semibold text-gray-800 hover:text-blue-600 transition line-clamp-1"
                >
                  {event.title}
                </Link>
                <p className={`text-xs font-medium ${statusInfo.text} ${statusInfo.bg} px-2 py-0.5 rounded-full inline-block mt-1`}>
                  {statusInfo.label}
                </p>
              </div>

              {/* Points Badge */}
              {registration?.points_awarded > 0 && (
                <div className="flex items-center gap-1 px-2 py-1 bg-amber-100 text-amber-700 rounded-full">
                  <Award className="w-4 h-4" />
                  <span className="text-sm font-medium">+{registration.points_awarded}</span>
                </div>
              )}
            </div>

            {/* Event Details */}
            <div className="flex flex-wrap items-center gap-3 mt-2 text-sm text-gray-500">
              <div className="flex items-center gap-1">
                <Calendar className="w-4 h-4" />
                <span>{formatDate(event.event_date)}</span>
              </div>
              {event.location_address && (
                <div className="flex items-center gap-1">
                  <MapPin className="w-4 h-4" />
                  <span className="truncate max-w-[200px]">{event.location_address}</span>
                </div>
              )}
            </div>

            {/* Certificate Actions - Only show for attended events */}
            {canGetCertificate && (
              <div className="flex flex-wrap items-center gap-2 mt-3">
                {certificateGenerated ? (
                  <>
                    <button
                      onClick={handleDownload}
                      className="flex items-center gap-1.5 px-3 py-1.5 bg-green-600 text-white rounded-lg text-sm font-medium hover:bg-green-700 transition"
                    >
                      <Download className="w-4 h-4" />
                      Download Certificate
                    </button>
                    <button
                      onClick={handleEmailCertificate}
                      disabled={isEmailing}
                      className="flex items-center gap-1.5 px-3 py-1.5 bg-blue-100 text-blue-700 rounded-lg text-sm font-medium hover:bg-blue-200 transition disabled:opacity-50"
                    >
                      {isEmailing ? (
                        <Loader2 className="w-4 h-4 animate-spin" />
                      ) : (
                        <Mail className="w-4 h-4" />
                      )}
                      Email Me
                    </button>
                  </>
                ) : (
                  <button
                    onClick={handleGenerateCertificate}
                    disabled={isGenerating}
                    className="flex items-center gap-1.5 px-3 py-1.5 bg-amber-500 text-white rounded-lg text-sm font-medium hover:bg-amber-600 transition disabled:opacity-50"
                  >
                    {isGenerating ? (
                      <Loader2 className="w-4 h-4 animate-spin" />
                    ) : (
                      <FileText className="w-4 h-4" />
                    )}
                    Generate Certificate
                  </button>
                )}

                <Link
                  href={`/events/${event.event_id}`}
                  className="flex items-center gap-1 px-3 py-1.5 text-gray-600 hover:text-gray-800 text-sm"
                >
                  <ExternalLink className="w-4 h-4" />
                  View Event
                </Link>
              </div>
            )}

            {/* Registration info for non-attended */}
            {!canGetCertificate && status !== 'cancelled' && (
              <div className="mt-3">
                <Link
                  href={`/events/${event.event_id}`}
                  className="flex items-center gap-1 text-sm text-blue-600 hover:text-blue-700"
                >
                  <ExternalLink className="w-4 h-4" />
                  View Event Details
                </Link>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
