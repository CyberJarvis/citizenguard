'use client';

import { useState, useEffect, Suspense } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { useForm } from 'react-hook-form';
import {
  Calendar,
  MapPin,
  Users,
  Clock,
  AlertTriangle,
  ArrowLeft,
  Loader2,
  Trash2,
  Trees,
  Megaphone,
  LifeBuoy,
  GraduationCap,
  Info
} from 'lucide-react';
import DashboardLayout from '@/components/DashboardLayout';
import useAuthStore from '@/context/AuthContext';
import {
  createEvent,
  getEventFilterOptions,
  getMyOrganizedCommunities
} from '@/lib/api';
import toast from 'react-hot-toast';

const eventTypes = [
  { value: 'beach_cleanup', label: 'Beach Cleanup', icon: Trash2, description: 'Organize beach cleaning activities' },
  { value: 'mangrove_plantation', label: 'Mangrove Plantation', icon: Trees, description: 'Plant mangroves to protect coastlines' },
  { value: 'awareness_drive', label: 'Awareness Drive', icon: Megaphone, description: 'Educate communities about ocean conservation' },
  { value: 'rescue_operation', label: 'Rescue Operation', icon: LifeBuoy, description: 'Coordinate marine animal rescues' },
  { value: 'training_workshop', label: 'Training Workshop', icon: GraduationCap, description: 'Conduct skills training sessions' },
  { value: 'emergency_response', label: 'Emergency Response', icon: AlertTriangle, description: 'Respond to coastal emergencies' },
];

function CreateEventForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { user, isAuthenticated } = useAuthStore();

  const [loading, setLoading] = useState(false);
  const [communities, setCommunities] = useState([]);
  const [loadingCommunities, setLoadingCommunities] = useState(true);
  const [selectedType, setSelectedType] = useState('beach_cleanup');

  const {
    register,
    handleSubmit,
    watch,
    setValue,
    formState: { errors }
  } = useForm({
    defaultValues: {
      community_id: searchParams.get('community') || '',
      title: '',
      description: '',
      event_type: 'beach_cleanup',
      location_address: '',
      location_latitude: '',
      location_longitude: '',
      event_date: '',
      event_end_date: '',
      registration_deadline: '',
      max_volunteers: 50,
      is_emergency: false,
    }
  });

  const isOrganizer = user?.role === 'verified_organizer' || user?.role === 'authority' || user?.role === 'authority_admin';

  useEffect(() => {
    if (!isAuthenticated || !isOrganizer) {
      toast.error('You need to be a verified organizer to create events');
      router.push('/events');
      return;
    }
    loadCommunities();
  }, [isAuthenticated, isOrganizer]);

  // Pre-fill from URL params (for hazard-to-event flow)
  useEffect(() => {
    const prefillTitle = searchParams.get('title');
    const prefillType = searchParams.get('type');
    const prefillEmergency = searchParams.get('emergency');
    const prefillLat = searchParams.get('lat');
    const prefillLng = searchParams.get('lng');
    const prefillAddress = searchParams.get('address');

    if (prefillTitle) setValue('title', prefillTitle);
    if (prefillType) {
      setValue('event_type', prefillType);
      setSelectedType(prefillType);
    }
    if (prefillEmergency === 'true') setValue('is_emergency', true);
    if (prefillLat) setValue('location_latitude', prefillLat);
    if (prefillLng) setValue('location_longitude', prefillLng);
    if (prefillAddress) setValue('location_address', prefillAddress);
  }, [searchParams, setValue]);

  const loadCommunities = async () => {
    try {
      setLoadingCommunities(true);
      const data = await getMyOrganizedCommunities(0, 100);
      setCommunities(data.communities || []);

      // Auto-select if only one community
      if (data.communities?.length === 1 && !searchParams.get('community')) {
        setValue('community_id', data.communities[0].community_id);
      }
    } catch (error) {
      console.error('Failed to load communities:', error);
      toast.error('Failed to load your communities');
    } finally {
      setLoadingCommunities(false);
    }
  };

  const onSubmit = async (data) => {
    if (!data.community_id) {
      toast.error('Please select a community');
      return;
    }

    try {
      setLoading(true);

      // Format datetime fields
      const eventData = {
        ...data,
        event_type: selectedType,
        location_latitude: parseFloat(data.location_latitude),
        location_longitude: parseFloat(data.location_longitude),
        max_volunteers: parseInt(data.max_volunteers),
        event_date: new Date(data.event_date).toISOString(),
        event_end_date: data.event_end_date ? new Date(data.event_end_date).toISOString() : null,
        registration_deadline: data.registration_deadline ? new Date(data.registration_deadline).toISOString() : null,
      };

      const result = await createEvent(eventData);

      if (result.success) {
        toast.success('Event created successfully!');
        router.push(`/events/${result.event.event_id}`);
      }
    } catch (error) {
      console.error('Failed to create event:', error);
      toast.error(error.response?.data?.detail || 'Failed to create event');
    } finally {
      setLoading(false);
    }
  };

  const watchEventDate = watch('event_date');
  const watchIsEmergency = watch('is_emergency');

  // Get user's location
  const handleGetLocation = () => {
    if (navigator.geolocation) {
      navigator.geolocation.getCurrentPosition(
        (position) => {
          setValue('location_latitude', position.coords.latitude.toFixed(6));
          setValue('location_longitude', position.coords.longitude.toFixed(6));
          toast.success('Location captured');
        },
        (error) => {
          toast.error('Failed to get location');
        }
      );
    } else {
      toast.error('Geolocation is not supported');
    }
  };

  if (!isAuthenticated || !isOrganizer) {
    return null;
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <div className="bg-gradient-to-r from-[#0d4a6f] to-[#083a57] text-white">
        <div className="max-w-3xl mx-auto px-4 py-6 sm:px-6 lg:px-8">
          <button
            onClick={() => router.back()}
            className="flex items-center gap-2 text-white/80 hover:text-white mb-4"
          >
            <ArrowLeft className="h-4 w-4" />
            Back
          </button>
          <h1 className="text-3xl font-semibold">Create Event</h1>
          <p className="mt-1 text-cyan-100">
            Organize a volunteer event for your community
          </p>
        </div>
      </div>

      <div className="max-w-3xl mx-auto px-4 py-8 sm:px-6 lg:px-8">
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
          {/* Community Selection */}
          <div className="bg-white rounded-xl shadow-sm p-6">
            <h2 className="text-lg font-semibold text-gray-800 mb-4">Select Community</h2>

            {loadingCommunities ? (
              <div className="flex items-center justify-center py-8">
                <Loader2 className="h-6 w-6 animate-spin text-[#0d4a6f]" />
              </div>
            ) : communities.length === 0 ? (
              <div className="text-center py-8">
                <p className="text-gray-500 mb-4">You need to create a community first</p>
                <button
                  type="button"
                  onClick={() => router.push('/community/create')}
                  className="text-[#0d4a6f] hover:underline"
                >
                  Create Community
                </button>
              </div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {communities.map(community => (
                  <label
                    key={community.community_id}
                    className={`flex items-center gap-3 p-4 rounded-lg border-2 cursor-pointer transition ${
                      watch('community_id') === community.community_id
                        ? 'border-[#0d4a6f] bg-[#e8f4fc]'
                        : 'border-gray-200 hover:border-gray-300'
                    }`}
                  >
                    <input
                      type="radio"
                      value={community.community_id}
                      {...register('community_id', { required: 'Please select a community' })}
                      className="hidden"
                    />
                    <div className="w-12 h-12 rounded-lg bg-[#e8f4fc] flex items-center justify-center">
                      <span className="text-xl font-semibold text-[#0d4a6f]">
                        {community.name.charAt(0)}
                      </span>
                    </div>
                    <div>
                      <div className="font-medium text-gray-800">{community.name}</div>
                      <div className="text-sm text-gray-500">{community.coastal_zone}</div>
                    </div>
                  </label>
                ))}
              </div>
            )}
            {errors.community_id && (
              <p className="text-red-500 text-sm mt-2">{errors.community_id.message}</p>
            )}
          </div>

          {/* Event Type */}
          <div className="bg-white rounded-xl shadow-sm p-6">
            <h2 className="text-lg font-semibold text-gray-800 mb-4">Event Type</h2>

            <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
              {eventTypes.map(type => {
                const Icon = type.icon;
                return (
                  <button
                    key={type.value}
                    type="button"
                    onClick={() => {
                      setSelectedType(type.value);
                      setValue('event_type', type.value);
                    }}
                    className={`flex flex-col items-center gap-2 p-4 rounded-lg border-2 transition ${
                      selectedType === type.value
                        ? 'border-[#0d4a6f] bg-[#e8f4fc]'
                        : 'border-gray-200 hover:border-gray-300'
                    }`}
                  >
                    <Icon className={`h-8 w-8 ${selectedType === type.value ? 'text-[#0d4a6f]' : 'text-gray-400'}`} />
                    <span className="text-sm font-medium text-gray-800 text-center">{type.label}</span>
                  </button>
                );
              })}
            </div>
          </div>

          {/* Event Details */}
          <div className="bg-white rounded-xl shadow-sm p-6">
            <h2 className="text-lg font-semibold text-gray-800 mb-4">Event Details</h2>

            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Event Title *
                </label>
                <input
                  type="text"
                  {...register('title', {
                    required: 'Title is required',
                    minLength: { value: 5, message: 'Title must be at least 5 characters' }
                  })}
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-[#1a6b9a] focus:border-transparent"
                  placeholder="e.g., Juhu Beach Cleanup Drive"
                />
                {errors.title && (
                  <p className="text-red-500 text-sm mt-1">{errors.title.message}</p>
                )}
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Description *
                </label>
                <textarea
                  {...register('description', {
                    required: 'Description is required',
                    minLength: { value: 20, message: 'Description must be at least 20 characters' }
                  })}
                  rows={4}
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-[#1a6b9a] focus:border-transparent"
                  placeholder="Describe the event, what volunteers will be doing, what to bring, etc."
                />
                {errors.description && (
                  <p className="text-red-500 text-sm mt-1">{errors.description.message}</p>
                )}
              </div>

              {/* Emergency Toggle */}
              <div className={`p-4 rounded-lg ${watchIsEmergency ? 'bg-red-50 border border-red-200' : 'bg-gray-50'}`}>
                <label className="flex items-center gap-3 cursor-pointer">
                  <input
                    type="checkbox"
                    {...register('is_emergency')}
                    className="w-5 h-5 text-red-600 rounded focus:ring-red-500"
                  />
                  <div>
                    <span className="font-medium text-gray-800 flex items-center gap-2">
                      <AlertTriangle className="h-4 w-4 text-red-500" />
                      Emergency Response Event
                    </span>
                    <p className="text-sm text-gray-500">
                      Mark this if responding to an active hazard. Awards 2x points.
                    </p>
                  </div>
                </label>
              </div>
            </div>
          </div>

          {/* Location */}
          <div className="bg-white rounded-xl shadow-sm p-6">
            <h2 className="text-lg font-semibold text-gray-800 mb-4">Location</h2>

            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Address *
                </label>
                <input
                  type="text"
                  {...register('location_address', { required: 'Address is required' })}
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-[#1a6b9a] focus:border-transparent"
                  placeholder="Full address of the event location"
                />
                {errors.location_address && (
                  <p className="text-red-500 text-sm mt-1">{errors.location_address.message}</p>
                )}
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Latitude *
                  </label>
                  <input
                    type="text"
                    {...register('location_latitude', {
                      required: 'Latitude is required',
                      pattern: { value: /^-?\d+\.?\d*$/, message: 'Invalid latitude' }
                    })}
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-[#1a6b9a] focus:border-transparent"
                    placeholder="e.g., 19.0883"
                  />
                  {errors.location_latitude && (
                    <p className="text-red-500 text-sm mt-1">{errors.location_latitude.message}</p>
                  )}
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Longitude *
                  </label>
                  <input
                    type="text"
                    {...register('location_longitude', {
                      required: 'Longitude is required',
                      pattern: { value: /^-?\d+\.?\d*$/, message: 'Invalid longitude' }
                    })}
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-[#1a6b9a] focus:border-transparent"
                    placeholder="e.g., 72.8263"
                  />
                  {errors.location_longitude && (
                    <p className="text-red-500 text-sm mt-1">{errors.location_longitude.message}</p>
                  )}
                </div>
              </div>

              <button
                type="button"
                onClick={handleGetLocation}
                className="flex items-center gap-2 px-4 py-2 text-[#0d4a6f] hover:bg-[#e8f4fc] rounded-lg"
              >
                <MapPin className="h-4 w-4" />
                Use My Current Location
              </button>
            </div>
          </div>

          {/* Date & Time */}
          <div className="bg-white rounded-xl shadow-sm p-6">
            <h2 className="text-lg font-semibold text-gray-800 mb-4">Date & Time</h2>

            <div className="space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Event Date & Time *
                  </label>
                  <input
                    type="datetime-local"
                    {...register('event_date', { required: 'Event date is required' })}
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-[#1a6b9a] focus:border-transparent"
                  />
                  {errors.event_date && (
                    <p className="text-red-500 text-sm mt-1">{errors.event_date.message}</p>
                  )}
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    End Date & Time (Optional)
                  </label>
                  <input
                    type="datetime-local"
                    {...register('event_end_date')}
                    min={watchEventDate}
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-[#1a6b9a] focus:border-transparent"
                  />
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Registration Deadline (Optional)
                </label>
                <input
                  type="datetime-local"
                  {...register('registration_deadline')}
                  max={watchEventDate}
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-[#1a6b9a] focus:border-transparent"
                />
                <p className="text-sm text-gray-500 mt-1">
                  Leave empty to allow registration until event starts
                </p>
              </div>
            </div>
          </div>

          {/* Capacity */}
          <div className="bg-white rounded-xl shadow-sm p-6">
            <h2 className="text-lg font-semibold text-gray-800 mb-4">Capacity</h2>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Maximum Volunteers *
              </label>
              <input
                type="number"
                {...register('max_volunteers', {
                  required: 'Max volunteers is required',
                  min: { value: 1, message: 'Must be at least 1' },
                  max: { value: 500, message: 'Maximum is 500' }
                })}
                className="w-full md:w-48 px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-[#1a6b9a] focus:border-transparent"
              />
              {errors.max_volunteers && (
                <p className="text-red-500 text-sm mt-1">{errors.max_volunteers.message}</p>
              )}
            </div>
          </div>

          {/* Points Info */}
          <div className="bg-amber-50 rounded-xl p-6">
            <div className="flex items-start gap-3">
              <Info className="h-5 w-5 text-amber-600 mt-0.5" />
              <div>
                <h3 className="font-medium text-amber-800">Points & Rewards</h3>
                <p className="text-sm text-amber-700 mt-1">
                  Volunteers who attend will earn <strong>{watchIsEmergency ? '100' : '50'} points</strong>.
                  {watchIsEmergency && ' Emergency events award double points!'}
                  You'll also earn <strong>10 bonus points</strong> per attendee as the organizer.
                </p>
              </div>
            </div>
          </div>

          {/* Submit */}
          <div className="flex items-center justify-end gap-4">
            <button
              type="button"
              onClick={() => router.back()}
              className="px-6 py-3 text-gray-700 hover:bg-gray-100 rounded-lg font-medium"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={loading || communities.length === 0}
              className="px-6 py-3 bg-[#0d4a6f] text-white rounded-lg font-medium hover:bg-[#083a57] disabled:opacity-50 flex items-center gap-2"
            >
              {loading ? (
                <>
                  <Loader2 className="h-5 w-5 animate-spin" />
                  Creating...
                </>
              ) : (
                <>
                  <Calendar className="h-5 w-5" />
                  Create Event
                </>
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

// Loading fallback for Suspense
function CreateEventLoading() {
  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center">
      <div className="text-center">
        <Loader2 className="h-8 w-8 animate-spin text-[#0d4a6f] mx-auto mb-4" />
        <p className="text-gray-500">Loading...</p>
      </div>
    </div>
  );
}

export default function CreateEventPage() {
  return (
    <DashboardLayout>
      <Suspense fallback={<CreateEventLoading />}>
        <CreateEventForm />
      </Suspense>
    </DashboardLayout>
  );
}
