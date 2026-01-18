'use client';

import { useState, useEffect } from 'react';
import { useParams, useRouter } from 'next/navigation';
import Link from 'next/link';
import {
  Calendar,
  MapPin,
  Users,
  Clock,
  AlertTriangle,
  CheckCircle,
  Loader2,
  UserPlus,
  UserMinus,
  Award,
  ArrowLeft,
  Share2,
  ExternalLink,
  User,
  XCircle,
  Check,
  Trash2,
  Trees,
  Megaphone,
  LifeBuoy,
  GraduationCap,
} from 'lucide-react';
import DashboardLayout from '@/components/DashboardLayout';
import useAuthStore from '@/context/AuthContext';
import {
  getEventById,
  registerForEvent,
  unregisterFromEvent,
  getEventRegistrations,
  markEventAttendance,
  completeEvent,
  cancelEvent,
  getEventTypeInfo,
  getEventStatusInfo
} from '@/lib/api';
import toast from 'react-hot-toast';

const eventTypeIcons = {
  beach_cleanup: Trash2,
  mangrove_plantation: Trees,
  awareness_drive: Megaphone,
  rescue_operation: LifeBuoy,
  training_workshop: GraduationCap,
  emergency_response: AlertTriangle,
};

export default function EventDetailPage() {
  const params = useParams();
  const router = useRouter();
  const { user, isAuthenticated } = useAuthStore();

  const [event, setEvent] = useState(null);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState(false);
  const [registrations, setRegistrations] = useState([]);
  const [loadingRegistrations, setLoadingRegistrations] = useState(false);
  const [selectedAttendees, setSelectedAttendees] = useState([]);
  const [showAttendanceModal, setShowAttendanceModal] = useState(false);

  const isOrganizer = event?.is_organizer;
  const isRegistered = event?.registration_status?.is_registered;

  useEffect(() => {
    loadEvent();
  }, [params.id]);

  useEffect(() => {
    if (event && isOrganizer) {
      loadRegistrations();
    }
  }, [event, isOrganizer]);

  const loadEvent = async () => {
    try {
      setLoading(true);
      const data = await getEventById(params.id);
      setEvent(data.event);
    } catch (error) {
      console.error('Failed to load event:', error);
      toast.error('Failed to load event');
    } finally {
      setLoading(false);
    }
  };

  const loadRegistrations = async () => {
    try {
      setLoadingRegistrations(true);
      const data = await getEventRegistrations(params.id);
      setRegistrations(data.registrations || []);
    } catch (error) {
      console.error('Failed to load registrations:', error);
    } finally {
      setLoadingRegistrations(false);
    }
  };

  const handleRegister = async () => {
    if (!isAuthenticated) {
      toast.error('Please login to register for events');
      router.push('/login');
      return;
    }

    try {
      setActionLoading(true);
      if (isRegistered) {
        await unregisterFromEvent(params.id);
        toast.success('Unregistered from event');
      } else {
        await registerForEvent(params.id);
        toast.success('Registered for event!');
      }
      loadEvent();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to update registration');
    } finally {
      setActionLoading(false);
    }
  };

  const handleMarkAttendance = async () => {
    if (selectedAttendees.length === 0) {
      toast.error('Select at least one attendee');
      return;
    }

    try {
      setActionLoading(true);
      const result = await markEventAttendance(params.id, selectedAttendees);
      toast.success(`Marked ${result.result.marked_count} attendees`);
      setShowAttendanceModal(false);
      setSelectedAttendees([]);
      loadEvent();
      loadRegistrations();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to mark attendance');
    } finally {
      setActionLoading(false);
    }
  };

  const handleCompleteEvent = async () => {
    if (!confirm('Are you sure you want to mark this event as completed?')) return;

    try {
      setActionLoading(true);
      await completeEvent(params.id);
      toast.success('Event completed successfully');
      loadEvent();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to complete event');
    } finally {
      setActionLoading(false);
    }
  };

  const handleCancelEvent = async () => {
    if (!confirm('Are you sure you want to cancel this event? This cannot be undone.')) return;

    try {
      setActionLoading(true);
      await cancelEvent(params.id);
      toast.success('Event cancelled');
      loadEvent();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to cancel event');
    } finally {
      setActionLoading(false);
    }
  };

  const formatDate = (dateStr) => {
    if (!dateStr) return 'TBD';
    const date = new Date(dateStr);
    return date.toLocaleDateString('en-IN', {
      weekday: 'long',
      day: 'numeric',
      month: 'long',
      year: 'numeric'
    });
  };

  const formatTime = (dateStr) => {
    if (!dateStr) return '';
    const date = new Date(dateStr);
    return date.toLocaleTimeString('en-IN', {
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  if (loading) {
    return (
      <DashboardLayout>
        <div className="min-h-screen bg-gray-50 flex items-center justify-center">
          <Loader2 className="h-8 w-8 animate-spin text-blue-600" />
        </div>
      </DashboardLayout>
    );
  }

  if (!event) {
    return (
      <DashboardLayout>
        <div className="min-h-screen bg-gray-50 flex items-center justify-center">
          <div className="text-center">
            <h2 className="text-xl font-semibold text-gray-800">Event not found</h2>
            <button
              onClick={() => router.push('/events')}
              className="mt-4 text-blue-600 hover:underline"
            >
              Back to Events
            </button>
          </div>
        </div>
      </DashboardLayout>
    );
  }

  const typeInfo = getEventTypeInfo(event.event_type);
  const statusInfo = getEventStatusInfo(event.status);
  const Icon = eventTypeIcons[event.event_type] || Calendar;
  const canRegister = event.status === 'published' && event.spots_left > 0 && !isOrganizer;

  return (
    <DashboardLayout>
      <div className="min-h-screen bg-gray-50">
        {/* Header */}
        <div className={`${event.is_emergency ? 'bg-gradient-to-r from-red-600 to-red-700' : 'bg-gradient-to-r from-blue-600 to-blue-700'} text-white`}>
          <div className="max-w-5xl mx-auto px-4 py-6 sm:px-6 lg:px-8">
            {/* Back Button */}
            <button
              onClick={() => router.back()}
              className="flex items-center gap-2 text-white/80 hover:text-white mb-4"
            >
              <ArrowLeft className="h-4 w-4" />
              Back
            </button>

            <div className="flex flex-col md:flex-row gap-6">
              {/* Event Icon */}
              <div className="w-24 h-24 bg-white/20 backdrop-blur-sm rounded-xl flex items-center justify-center">
                <Icon className="h-12 w-12 text-white" />
              </div>

              <div className="flex-1">
                <div className="flex flex-wrap items-center gap-3 mb-2">
                  <span className={`px-3 py-1 rounded-full text-sm font-medium ${statusInfo.bgColor} ${statusInfo.textColor}`}>
                    {statusInfo.label}
                  </span>
                  {event.is_emergency && (
                    <span className="px-3 py-1 rounded-full text-sm font-medium bg-red-500 text-white flex items-center gap-1">
                      <AlertTriangle className="h-4 w-4" />
                      Emergency
                    </span>
                  )}
                  <span className="px-3 py-1 rounded-full text-sm font-medium bg-white/20 text-white">
                    {typeInfo.label}
                  </span>
                </div>

                <h1 className="text-3xl font-bold">{event.title}</h1>

                <div className="flex items-center gap-4 mt-3 text-white/80">
                  <div className="flex items-center gap-2">
                    <Award className="h-5 w-5 text-amber-400" />
                    <span className="font-medium">+{event.points_per_attendee} points</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <Users className="h-5 w-5" />
                    <span>{event.registered_count}/{event.max_volunteers} registered</span>
                  </div>
                </div>
              </div>

              {/* Action Buttons */}
              <div className="flex flex-col gap-2">
                {!isOrganizer && canRegister && (
                  <button
                    onClick={handleRegister}
                    disabled={actionLoading}
                    className={`px-6 py-3 rounded-lg font-medium flex items-center justify-center gap-2 transition ${
                      isRegistered
                        ? 'bg-white/20 text-white hover:bg-white/30'
                        : 'bg-white text-blue-600 hover:bg-blue-50'
                    }`}
                  >
                    {actionLoading ? (
                      <Loader2 className="h-5 w-5 animate-spin" />
                    ) : isRegistered ? (
                      <>
                        <UserMinus className="h-5 w-5" />
                        Unregister
                      </>
                    ) : (
                      <>
                        <UserPlus className="h-5 w-5" />
                        Register Now
                      </>
                    )}
                  </button>
                )}

                {isRegistered && (
                  <div className="flex items-center gap-2 text-white bg-white/20 px-4 py-2 rounded-lg">
                    <CheckCircle className="h-5 w-5 text-green-400" />
                    <span>You're registered</span>
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>

        {/* Content */}
        <div className="max-w-5xl mx-auto px-4 py-8 sm:px-6 lg:px-8">
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
            {/* Main Content */}
            <div className="lg:col-span-2 space-y-6">
              {/* Description */}
              <div className="bg-white rounded-xl shadow-sm p-6">
                <h2 className="text-lg font-semibold text-gray-800 mb-4">About this Event</h2>
                <p className="text-gray-600 whitespace-pre-wrap">{event.description}</p>
              </div>

              {/* Community */}
              {event.community && (
                <Link href={`/community/${event.community.community_id}`}>
                  <div className="bg-white rounded-xl shadow-sm p-6 hover:shadow-md transition cursor-pointer">
                    <h2 className="text-lg font-semibold text-gray-800 mb-4">Organized by</h2>
                    <div className="flex items-center gap-4">
                      <div className="w-12 h-12 rounded-lg bg-blue-100 flex items-center justify-center">
                        {event.community.logo_url ? (
                          <img src={event.community.logo_url} alt="" className="w-full h-full object-cover rounded-lg" />
                        ) : (
                          <span className="text-xl font-bold text-blue-600">
                            {event.community.name?.charAt(0)}
                          </span>
                        )}
                      </div>
                      <div>
                        <div className="font-medium text-gray-800">{event.community.name}</div>
                        <div className="text-sm text-gray-500">by {event.organizer_name}</div>
                      </div>
                      <ExternalLink className="h-5 w-5 text-gray-400 ml-auto" />
                    </div>
                  </div>
                </Link>
              )}

              {/* Organizer Actions */}
              {isOrganizer && (
                <div className="bg-white rounded-xl shadow-sm p-6">
                  <h2 className="text-lg font-semibold text-gray-800 mb-4">Organizer Actions</h2>

                  <div className="grid grid-cols-2 gap-4">
                    <button
                      onClick={() => setShowAttendanceModal(true)}
                      disabled={event.status === 'cancelled' || event.status === 'completed'}
                      className="flex items-center justify-center gap-2 px-4 py-3 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      <Check className="h-5 w-5" />
                      Mark Attendance
                    </button>

                    <button
                      onClick={handleCompleteEvent}
                      disabled={event.status !== 'published' && event.status !== 'ongoing'}
                      className="flex items-center justify-center gap-2 px-4 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      <CheckCircle className="h-5 w-5" />
                      Complete Event
                    </button>

                    <button
                      onClick={handleCancelEvent}
                      disabled={event.status === 'completed' || event.status === 'cancelled'}
                      className="flex items-center justify-center gap-2 px-4 py-3 bg-red-600 text-white rounded-lg hover:bg-red-700 disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      <XCircle className="h-5 w-5" />
                      Cancel Event
                    </button>

                    <button
                      onClick={() => router.push(`/events/${params.id}/edit`)}
                      disabled={event.status === 'completed' || event.status === 'cancelled'}
                      className="flex items-center justify-center gap-2 px-4 py-3 bg-gray-600 text-white rounded-lg hover:bg-gray-700 disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      Edit Event
                    </button>
                  </div>

                  {/* Registrations List */}
                  <div className="mt-6">
                    <h3 className="font-medium text-gray-800 mb-3">
                      Registrations ({registrations.length})
                    </h3>
                    {loadingRegistrations ? (
                      <div className="flex justify-center py-4">
                        <Loader2 className="h-6 w-6 animate-spin text-blue-600" />
                      </div>
                    ) : registrations.length === 0 ? (
                      <p className="text-gray-500 text-center py-4">No registrations yet</p>
                    ) : (
                      <div className="max-h-64 overflow-y-auto space-y-2">
                        {registrations.map(reg => (
                          <div
                            key={reg.registration_id}
                            className="flex items-center justify-between p-3 bg-gray-50 rounded-lg"
                          >
                            <div className="flex items-center gap-3">
                              <div className="w-8 h-8 rounded-full bg-blue-100 flex items-center justify-center">
                                <User className="h-4 w-4 text-blue-600" />
                              </div>
                              <div>
                                <div className="font-medium text-gray-800">{reg.user_name}</div>
                                <div className="text-xs text-gray-500">{reg.user_email}</div>
                              </div>
                            </div>
                            <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                              reg.status === 'attended' ? 'bg-green-100 text-green-700' :
                              reg.status === 'no_show' ? 'bg-red-100 text-red-700' :
                              'bg-gray-100 text-gray-700'
                            }`}>
                              {reg.status}
                            </span>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              )}
            </div>

            {/* Sidebar */}
            <div className="space-y-6">
              {/* Event Details Card */}
              <div className="bg-white rounded-xl shadow-sm p-6">
                <h2 className="text-lg font-semibold text-gray-800 mb-4">Event Details</h2>

                <div className="space-y-4">
                  <div className="flex items-start gap-3">
                    <Calendar className="h-5 w-5 text-gray-400 mt-0.5" />
                    <div>
                      <div className="font-medium text-gray-800">{formatDate(event.event_date)}</div>
                      <div className="text-sm text-gray-500">{formatTime(event.event_date)}</div>
                    </div>
                  </div>

                  {event.event_end_date && (
                    <div className="flex items-start gap-3">
                      <Clock className="h-5 w-5 text-gray-400 mt-0.5" />
                      <div>
                        <div className="text-sm text-gray-500">Ends</div>
                        <div className="font-medium text-gray-800">{formatTime(event.event_end_date)}</div>
                      </div>
                    </div>
                  )}

                  <div className="flex items-start gap-3">
                    <MapPin className="h-5 w-5 text-gray-400 mt-0.5" />
                    <div>
                      <div className="font-medium text-gray-800">{event.location_address}</div>
                      <div className="text-sm text-gray-500">{event.coastal_zone}</div>
                    </div>
                  </div>

                  <div className="flex items-start gap-3">
                    <Users className="h-5 w-5 text-gray-400 mt-0.5" />
                    <div>
                      <div className="font-medium text-gray-800">
                        {event.registered_count} / {event.max_volunteers} volunteers
                      </div>
                      <div className={`text-sm ${event.spots_left > 0 ? 'text-green-600' : 'text-red-600'}`}>
                        {event.spots_left > 0 ? `${event.spots_left} spots left` : 'Event is full'}
                      </div>
                    </div>
                  </div>

                  {event.registration_deadline && (
                    <div className="flex items-start gap-3">
                      <AlertTriangle className="h-5 w-5 text-amber-500 mt-0.5" />
                      <div>
                        <div className="text-sm text-gray-500">Registration Deadline</div>
                        <div className="font-medium text-gray-800">{formatDate(event.registration_deadline)}</div>
                      </div>
                    </div>
                  )}
                </div>

                {/* Map Placeholder */}
                <div className="mt-6 h-40 bg-gray-100 rounded-lg flex items-center justify-center">
                  <a
                    href={`https://www.google.com/maps?q=${event.location_latitude},${event.location_longitude}`}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-blue-600 hover:underline flex items-center gap-2"
                  >
                    <MapPin className="h-5 w-5" />
                    Open in Google Maps
                  </a>
                </div>
              </div>

              {/* Share Card */}
              <div className="bg-white rounded-xl shadow-sm p-6">
                <h2 className="text-lg font-semibold text-gray-800 mb-4">Share Event</h2>
                <button
                  onClick={() => {
                    navigator.clipboard.writeText(window.location.href);
                    toast.success('Link copied to clipboard');
                  }}
                  className="w-full flex items-center justify-center gap-2 px-4 py-2 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200"
                >
                  <Share2 className="h-4 w-4" />
                  Copy Link
                </button>
              </div>
            </div>
          </div>
        </div>

        {/* Attendance Modal */}
        {showAttendanceModal && (
          <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
            <div className="bg-white rounded-xl max-w-lg w-full max-h-[80vh] overflow-hidden">
              <div className="p-6 border-b border-gray-200">
                <h2 className="text-xl font-semibold text-gray-800">Mark Attendance</h2>
                <p className="text-sm text-gray-500 mt-1">Select attendees who participated in the event</p>
              </div>

              <div className="p-6 max-h-[50vh] overflow-y-auto">
                {registrations.filter(r => r.status !== 'attended').length === 0 ? (
                  <p className="text-gray-500 text-center py-4">All registrations have been marked</p>
                ) : (
                  <div className="space-y-2">
                    {registrations.filter(r => r.status !== 'attended').map(reg => (
                      <label
                        key={reg.registration_id}
                        className="flex items-center gap-3 p-3 bg-gray-50 rounded-lg cursor-pointer hover:bg-gray-100"
                      >
                        <input
                          type="checkbox"
                          checked={selectedAttendees.includes(reg.user_id)}
                          onChange={(e) => {
                            if (e.target.checked) {
                              setSelectedAttendees([...selectedAttendees, reg.user_id]);
                            } else {
                              setSelectedAttendees(selectedAttendees.filter(id => id !== reg.user_id));
                            }
                          }}
                          className="w-5 h-5 text-blue-600 rounded"
                        />
                        <div className="flex-1">
                          <div className="font-medium text-gray-800">{reg.user_name}</div>
                          <div className="text-xs text-gray-500">{reg.user_email}</div>
                        </div>
                      </label>
                    ))}
                  </div>
                )}
              </div>

              <div className="p-6 border-t border-gray-200 flex justify-end gap-3">
                <button
                  onClick={() => { setShowAttendanceModal(false); setSelectedAttendees([]); }}
                  className="px-4 py-2 text-gray-700 hover:bg-gray-100 rounded-lg"
                >
                  Cancel
                </button>
                <button
                  onClick={handleMarkAttendance}
                  disabled={selectedAttendees.length === 0 || actionLoading}
                  className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:opacity-50 flex items-center gap-2"
                >
                  {actionLoading ? (
                    <Loader2 className="h-4 w-4 animate-spin" />
                  ) : (
                    <>
                      <Check className="h-4 w-4" />
                      Mark {selectedAttendees.length} Attendees
                    </>
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
