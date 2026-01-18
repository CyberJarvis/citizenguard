'use client';

import { useState } from 'react';
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
  Trash2,
  Trees,
  Megaphone,
  LifeBuoy,
  GraduationCap,
} from 'lucide-react';
import { registerForEvent, unregisterFromEvent, getEventTypeInfo, getEventStatusInfo } from '@/lib/api';
import toast from 'react-hot-toast';

const eventTypeIcons = {
  beach_cleanup: Trash2,
  mangrove_plantation: Trees,
  awareness_drive: Megaphone,
  rescue_operation: LifeBuoy,
  training_workshop: GraduationCap,
  emergency_response: AlertTriangle,
};

const eventTypeColors = {
  beach_cleanup: { bg: 'bg-blue-100', text: 'text-blue-700', border: 'border-blue-500' },
  mangrove_plantation: { bg: 'bg-green-100', text: 'text-green-700', border: 'border-green-500' },
  awareness_drive: { bg: 'bg-purple-100', text: 'text-purple-700', border: 'border-purple-500' },
  rescue_operation: { bg: 'bg-red-100', text: 'text-red-700', border: 'border-red-500' },
  training_workshop: { bg: 'bg-amber-100', text: 'text-amber-700', border: 'border-amber-500' },
  emergency_response: { bg: 'bg-rose-100', text: 'text-rose-700', border: 'border-rose-500' },
};

export default function EventCard({
  event,
  isAuthenticated = false,
  onRegisterChange,
  compact = false
}) {
  const [isLoading, setIsLoading] = useState(false);
  const [isRegistered, setIsRegistered] = useState(event.registration_status?.is_registered || false);

  const eventType = event.event_type?.toLowerCase() || 'general';
  const typeConfig = eventTypeColors[eventType] || { bg: 'bg-gray-100', text: 'text-gray-700', border: 'border-gray-500' };
  const typeInfo = getEventTypeInfo(eventType);
  const statusInfo = getEventStatusInfo(event.status);
  const Icon = eventTypeIcons[eventType] || Calendar;

  // Format date
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

  const formatTime = (dateStr) => {
    if (!dateStr) return '';
    const date = new Date(dateStr);
    return date.toLocaleTimeString('en-IN', {
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  const handleRegister = async (e) => {
    e.preventDefault();
    e.stopPropagation();

    if (!isAuthenticated) {
      toast.error('Please login to register for events');
      return;
    }

    if (event.is_organizer) {
      toast.error('Organizers cannot register for their own events');
      return;
    }

    try {
      setIsLoading(true);

      if (isRegistered) {
        await unregisterFromEvent(event.event_id);
        toast.success('Unregistered from event');
        setIsRegistered(false);
      } else {
        await registerForEvent(event.event_id);
        toast.success('Registered for event!');
        setIsRegistered(true);
      }

      if (onRegisterChange) {
        onRegisterChange(event.event_id, !isRegistered);
      }
    } catch (error) {
      console.error('Error:', error);
      toast.error(error.response?.data?.detail || 'Failed to update registration');
    } finally {
      setIsLoading(false);
    }
  };

  const canRegister = event.status === 'published' && event.spots_left > 0;

  if (compact) {
    return (
      <Link href={`/events/${event.event_id}`}>
        <div className="bg-white rounded-lg border border-gray-200 p-4 hover:shadow-md transition cursor-pointer">
          <div className="flex items-center gap-3">
            <div className={`w-12 h-12 rounded-lg ${typeConfig.bg} flex items-center justify-center`}>
              <Icon className={`h-6 w-6 ${typeConfig.text}`} />
            </div>
            <div className="flex-1 min-w-0">
              <h3 className="font-medium text-gray-800 truncate">{event.title}</h3>
              <div className="flex items-center gap-2 text-sm text-gray-500">
                <Calendar className="h-3.5 w-3.5" />
                <span>{formatDate(event.event_date)}</span>
              </div>
            </div>
            {event.is_emergency && (
              <AlertTriangle className="h-5 w-5 text-red-500 flex-shrink-0" />
            )}
            {isRegistered && (
              <CheckCircle className="h-5 w-5 text-green-500 flex-shrink-0" />
            )}
          </div>
        </div>
      </Link>
    );
  }

  return (
    <Link href={`/events/${event.event_id}`}>
      <div className={`bg-white rounded-xl shadow-md overflow-hidden hover:shadow-lg transition cursor-pointer group ${event.is_emergency ? 'ring-2 ring-red-500' : ''}`}>
        {/* Header with Event Type */}
        <div className={`h-24 ${typeConfig.bg} relative flex items-center justify-center`}>
          <Icon className={`h-12 w-12 ${typeConfig.text} opacity-30 group-hover:opacity-50 transition`} />

          {/* Emergency Badge */}
          {event.is_emergency && (
            <div className="absolute top-3 left-3 px-2 py-1 rounded-full text-xs font-bold bg-red-500 text-white flex items-center gap-1 animate-pulse">
              <AlertTriangle className="h-3 w-3" />
              EMERGENCY
            </div>
          )}

          {/* Status Badge */}
          <div className={`absolute top-3 right-3 px-2 py-1 rounded-full text-xs font-medium ${statusInfo.bgColor} ${statusInfo.textColor}`}>
            {statusInfo.label}
          </div>

          {/* Points Badge */}
          <div className="absolute bottom-3 right-3 px-2 py-1 rounded-full text-xs font-medium bg-amber-500 text-white flex items-center gap-1">
            <Award className="h-3 w-3" />
            +{event.points_per_attendee} pts
          </div>
        </div>

        {/* Content */}
        <div className="p-4">
          {/* Event Type & Title */}
          <div className="mb-2">
            <span className={`text-xs font-medium ${typeConfig.text}`}>
              {typeInfo.label}
            </span>
            <h3 className="font-semibold text-gray-800 truncate group-hover:text-blue-600 transition">
              {event.title}
            </h3>
          </div>

          {/* Description */}
          <p className="text-sm text-gray-600 line-clamp-2 mb-3">
            {event.description}
          </p>

          {/* Date & Time */}
          <div className="flex items-center gap-2 text-sm text-gray-600 mb-2">
            <Calendar className="h-4 w-4 text-gray-400" />
            <span>{formatDate(event.event_date)}</span>
            {formatTime(event.event_date) && (
              <>
                <Clock className="h-4 w-4 text-gray-400 ml-2" />
                <span>{formatTime(event.event_date)}</span>
              </>
            )}
          </div>

          {/* Location */}
          <div className="flex items-center gap-2 text-sm text-gray-600 mb-3">
            <MapPin className="h-4 w-4 text-gray-400" />
            <span className="truncate">{event.location_address}</span>
          </div>

          {/* Stats */}
          <div className="flex items-center justify-between text-sm border-t border-gray-100 pt-3">
            <div className="flex items-center gap-1 text-gray-500">
              <Users className="h-4 w-4" />
              <span>{event.registered_count}/{event.max_volunteers}</span>
            </div>
            <div className="flex items-center gap-1 text-gray-500">
              <MapPin className="h-4 w-4" />
              <span>{event.coastal_zone}</span>
            </div>
            <div className={`text-xs font-medium ${event.spots_left > 0 ? 'text-green-600' : 'text-red-600'}`}>
              {event.spots_left > 0 ? `${event.spots_left} spots left` : 'Full'}
            </div>
          </div>

          {/* Register Button */}
          {isAuthenticated && !event.is_organizer && canRegister && (
            <button
              onClick={handleRegister}
              disabled={isLoading}
              className={`w-full mt-4 py-2 rounded-lg font-medium flex items-center justify-center gap-2 transition ${
                isRegistered
                  ? 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                  : 'bg-blue-600 text-white hover:bg-blue-700'
              } disabled:opacity-50`}
            >
              {isLoading ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : isRegistered ? (
                <>
                  <UserMinus className="h-4 w-4" />
                  Unregister
                </>
              ) : (
                <>
                  <UserPlus className="h-4 w-4" />
                  Register
                </>
              )}
            </button>
          )}

          {/* Organizer Badge */}
          {event.is_organizer && (
            <div className="mt-4 py-2 rounded-lg bg-amber-50 text-amber-700 text-center text-sm font-medium">
              You are organizing this event
            </div>
          )}

          {/* Full Event */}
          {!canRegister && event.status === 'published' && !event.is_organizer && (
            <div className="mt-4 py-2 rounded-lg bg-red-50 text-red-700 text-center text-sm font-medium">
              Event is full
            </div>
          )}
        </div>
      </div>
    </Link>
  );
}
