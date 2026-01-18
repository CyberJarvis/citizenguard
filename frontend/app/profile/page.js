'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import ProtectedRoute from '@/components/ProtectedRoute';
import DashboardLayout from '@/components/DashboardLayout';
import EventHistoryCard from '@/components/events/EventHistoryCard';
import {
  User,
  Mail,
  Phone,
  MapPin,
  Award,
  TrendingUp,
  CheckCircle,
  AlertTriangle,
  Shield,
  Edit,
  Camera,
  Clock,
  Eye,
  ThumbsUp,
  FileText,
  Loader2,
  XCircle,
  Save,
  X,
  Trophy,
  Calendar,
  Star,
  Crown,
  Download,
  ExternalLink,
  Plus,
  Trash2,
  UserPlus,
  Bell
} from 'lucide-react';
import {
  getMyProfile,
  updateMyProfile,
  uploadProfilePicture,
  getUserStats,
  getMyHazardReports,
  getMyEvents,
  getMyRank,
  getAllBadges,
  getMyCertificates,
  getBadgeInfo
} from '@/lib/api';
import { formatDateIST } from '@/lib/dateUtils';
import toast from 'react-hot-toast';
import PageHeader from '@/components/PageHeader';

// Tab configuration
const tabs = [
  { id: 'overview', label: 'Overview', icon: User },
  { id: 'events', label: 'My Events', icon: Calendar },
  { id: 'badges', label: 'Badges', icon: Award },
  { id: 'certificates', label: 'Certificates', icon: FileText }
];

// Badge icon mapping
const badgeIcons = {
  Star: Star,
  Award: Award,
  Shield: Shield,
  Trophy: Trophy,
  Crown: Crown,
  AlertTriangle: AlertTriangle,
  Users: User
};

function ProfileContent() {
  // Profile state
  const [profile, setProfile] = useState(null);
  const [stats, setStats] = useState(null);
  const [isLoadingProfile, setIsLoadingProfile] = useState(true);
  const [profileError, setProfileError] = useState(null);

  // Edit mode state
  const [isEditing, setIsEditing] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [isUploadingPicture, setIsUploadingPicture] = useState(false);
  const [editedProfile, setEditedProfile] = useState({});

  // Tab state
  const [activeTab, setActiveTab] = useState('overview');

  // Hazard reports state
  const [reports, setReports] = useState([]);
  const [isLoadingReports, setIsLoadingReports] = useState(true);

  // Events state
  const [events, setEvents] = useState([]);
  const [isLoadingEvents, setIsLoadingEvents] = useState(false);
  const [eventsPage, setEventsPage] = useState(0);
  const [hasMoreEvents, setHasMoreEvents] = useState(true);
  const [eventFilter, setEventFilter] = useState('all');

  // Points & Rank state
  const [rankData, setRankData] = useState(null);
  const [allBadges, setAllBadges] = useState([]);
  const [isLoadingBadges, setIsLoadingBadges] = useState(false);

  // Certificates state
  const [certificates, setCertificates] = useState([]);
  const [isLoadingCertificates, setIsLoadingCertificates] = useState(false);

  // Emergency contacts state
  const [emergencyContacts, setEmergencyContacts] = useState([]);
  const [newContact, setNewContact] = useState({ name: '', phone: '', relationship: '' });

  // Backend URL for images
  const getBackendBaseUrl = () => {
    const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';
    return apiUrl.replace('/api/v1', '');
  };

  const getImageUrl = (path) => {
    if (!path) return null;
    if (path.startsWith('http')) return path;
    return `${getBackendBaseUrl()}${path}`;
  };

  // Load profile data and stats on mount
  useEffect(() => {
    const loadProfileData = async () => {
      try {
        setIsLoadingProfile(true);
        setProfileError(null);

        const [profileData, statsData] = await Promise.all([
          getMyProfile(),
          getUserStats()
        ]);

        setProfile(profileData);
        setStats(statsData);
        setEmergencyContacts(profileData.emergency_contacts || []);
        setEditedProfile({
          name: profileData.name,
          phone: profileData.phone || '',
          bio: profileData.bio || '',
          location: {
            state: profileData.location?.state || profileData.location?.region || '',
            city: profileData.location?.city || '',
            region: profileData.location?.region || profileData.location?.state || ''
          },
          emergency_contacts: profileData.emergency_contacts || []
        });
      } catch (error) {
        console.error('Error loading profile:', error);
        setProfileError('Failed to load profile data');
        toast.error('Failed to load profile');
      } finally {
        setIsLoadingProfile(false);
      }
    };

    loadProfileData();
  }, []);

  // Fetch hazard reports
  useEffect(() => {
    const fetchUserReports = async () => {
      try {
        setIsLoadingReports(true);
        const response = await getMyHazardReports();
        if (response.data && response.data.reports) {
          setReports(response.data.reports);
        } else {
          setReports([]);
        }
      } catch (error) {
        console.error('Error fetching user reports:', error);
      } finally {
        setIsLoadingReports(false);
      }
    };

    fetchUserReports();
  }, []);

  // Fetch events when tab changes to events
  useEffect(() => {
    if (activeTab === 'events' && events.length === 0) {
      fetchEvents();
    }
  }, [activeTab]);

  // Fetch badges and rank when tab changes to badges
  useEffect(() => {
    if (activeTab === 'badges' && allBadges.length === 0) {
      fetchBadgesAndRank();
    }
  }, [activeTab]);

  // Fetch certificates when tab changes to certificates
  useEffect(() => {
    if (activeTab === 'certificates' && certificates.length === 0) {
      fetchCertificates();
    }
  }, [activeTab]);

  const fetchEvents = async (reset = false) => {
    try {
      setIsLoadingEvents(true);
      const page = reset ? 0 : eventsPage;
      const response = await getMyEvents(page * 10, 10);

      if (response.success) {
        const newEvents = response.registrations || [];
        if (reset) {
          setEvents(newEvents);
          setEventsPage(1);
        } else {
          setEvents(prev => [...prev, ...newEvents]);
          setEventsPage(prev => prev + 1);
        }
        setHasMoreEvents(newEvents.length === 10);
      }
    } catch (error) {
      console.error('Error fetching events:', error);
      toast.error('Failed to load events');
    } finally {
      setIsLoadingEvents(false);
    }
  };

  const fetchBadgesAndRank = async () => {
    try {
      setIsLoadingBadges(true);
      const [rankResponse, badgesResponse] = await Promise.all([
        getMyRank(),
        getAllBadges()
      ]);

      if (rankResponse.success) {
        setRankData(rankResponse);
      }
      if (badgesResponse.success) {
        setAllBadges(badgesResponse.badges || []);
      }
    } catch (error) {
      console.error('Error fetching badges:', error);
    } finally {
      setIsLoadingBadges(false);
    }
  };

  const fetchCertificates = async () => {
    try {
      setIsLoadingCertificates(true);
      const response = await getMyCertificates(0, 50);
      if (response.success) {
        setCertificates(response.certificates || []);
      }
    } catch (error) {
      console.error('Error fetching certificates:', error);
    } finally {
      setIsLoadingCertificates(false);
    }
  };

  const handleEdit = () => {
    setIsEditing(true);
    setEditedProfile({
      name: profile.name,
      phone: profile.phone || '',
      bio: profile.bio || '',
      emergency_contacts: profile.emergency_contacts || []
    });
  };

  const handleCancel = () => {
    setIsEditing(false);
  };

  const handleSave = async () => {
    try {
      setIsSaving(true);
      const updated = await updateMyProfile(editedProfile);
      setProfile(updated);
      setEmergencyContacts(updated.emergency_contacts || editedProfile.emergency_contacts || []);
      setIsEditing(false);
      toast.success('Profile updated successfully');
    } catch (error) {
      console.error('Error updating profile:', error);
      toast.error(error.response?.data?.detail || 'Failed to update profile');
    } finally {
      setIsSaving(false);
    }
  };

  const handleProfilePictureChange = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;

    if (!file.type.startsWith('image/')) {
      toast.error('Please select an image file');
      return;
    }

    if (file.size > 5 * 1024 * 1024) {
      toast.error('Image size must be less than 5MB');
      return;
    }

    try {
      setIsUploadingPicture(true);
      const result = await uploadProfilePicture(file);
      setProfile(prev => ({
        ...prev,
        profile_picture: result.picture_url
      }));
      toast.success('Profile picture updated');
    } catch (error) {
      console.error('Error uploading profile picture:', error);
      toast.error(error.response?.data?.detail || 'Failed to upload picture');
    } finally {
      setIsUploadingPicture(false);
    }
  };

  const getInitials = (name) => {
    return name
      ?.split(' ')
      .map(n => n[0])
      .join('')
      .toUpperCase()
      .slice(0, 2) || '??';
  };

  const formatDate = (dateString) => {
    const date = new Date(dateString);
    const now = new Date();
    const diffMs = now - date;
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);

    if (diffMins < 60) {
      return `${diffMins} ${diffMins === 1 ? 'minute' : 'minutes'} ago`;
    } else if (diffHours < 24) {
      return `${diffHours} ${diffHours === 1 ? 'hour' : 'hours'} ago`;
    } else if (diffDays < 7) {
      return `${diffDays} ${diffDays === 1 ? 'day' : 'days'} ago`;
    } else {
      return date.toLocaleDateString('en-US', {
        month: 'short',
        day: 'numeric',
        year: 'numeric'
      });
    }
  };

  const getStatusBadge = (status) => {
    const badges = {
      verified: { bg: 'bg-green-100', text: 'text-green-700', label: 'Verified', icon: CheckCircle },
      pending: { bg: 'bg-yellow-100', text: 'text-yellow-700', label: 'Pending', icon: Clock },
      rejected: { bg: 'bg-red-100', text: 'text-red-700', label: 'Rejected', icon: XCircle }
    };
    return badges[status] || badges.pending;
  };

  // Filter events based on status
  const filteredEvents = events.filter(reg => {
    if (eventFilter === 'all') return true;
    return reg.registration_status?.toLowerCase() === eventFilter;
  });

  // Loading state
  if (isLoadingProfile) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-center">
          <Loader2 className="w-10 h-10 text-[#0d4a6f] animate-spin mx-auto mb-3" />
          <p className="text-gray-600">Loading profile...</p>
        </div>
      </div>
    );
  }

  // Error state
  if (profileError && !profile) {
    return (
      <div className="flex items-center justify-center min-h-screen p-4">
        <div className="bg-white rounded-lg shadow-md p-6 max-w-md w-full text-center">
          <XCircle className="w-12 h-12 text-red-500 mx-auto mb-3" />
          <h2 className="text-lg font-semibold text-gray-900 mb-2">Error Loading Profile</h2>
          <p className="text-gray-600 mb-4">{profileError}</p>
          <button
            onClick={() => window.location.reload()}
            className="px-4 py-2 bg-[#0d4a6f] text-white rounded-lg hover:bg-[#083a57] transition"
          >
            Try Again
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 pb-24">
      {/* Top Icons Bar */}
      <div className="px-4 pt-4 lg:px-6">
        <PageHeader />
      </div>

      {/* Header with Profile Picture */}
      <div className="relative">
        <div className="h-40 sm:h-48 bg-gradient-to-br from-[#0d4a6f] via-[#1a6b9a] to-[#083a57] relative">
          <button
            onClick={() => window.history.back()}
            className="absolute top-4 left-4 w-10 h-10 bg-white/20 backdrop-blur-sm rounded-full flex items-center justify-center text-white hover:bg-white/30 transition-colors"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
            </svg>
          </button>

          <div className="absolute top-4 right-4">
            {!isEditing ? (
              <button
                onClick={handleEdit}
                className="px-4 py-2 bg-white/90 backdrop-blur-sm text-[#0d4a6f] rounded-full font-semibold shadow-lg hover:bg-white transition-all flex items-center gap-2"
              >
                <Edit className="w-4 h-4" />
                <span className="hidden sm:inline">Edit</span>
              </button>
            ) : (
              <div className="flex gap-2">
                <button
                  onClick={handleCancel}
                  disabled={isSaving}
                  className="px-4 py-2 bg-white/90 backdrop-blur-sm text-gray-700 rounded-full font-semibold shadow-lg hover:bg-white transition-all disabled:opacity-50"
                >
                  <X className="w-4 h-4" />
                </button>
                <button
                  onClick={handleSave}
                  disabled={isSaving}
                  className="px-4 py-2 bg-white/90 backdrop-blur-sm text-blue-600 rounded-full font-semibold shadow-lg hover:bg-white transition-all disabled:opacity-50 flex items-center gap-2"
                >
                  {isSaving ? (
                    <Loader2 className="w-4 h-4 animate-spin" />
                  ) : (
                    <>
                      <Save className="w-4 h-4" />
                      <span className="hidden sm:inline">Save</span>
                    </>
                  )}
                </button>
              </div>
            )}
          </div>
        </div>

        {/* Profile Picture */}
        <div className="absolute -bottom-16 sm:-bottom-20 left-1/2 transform -translate-x-1/2">
          <div className="relative">
            {profile?.profile_picture ? (
              <img
                src={getImageUrl(profile.profile_picture)}
                alt={profile.name}
                className="w-32 h-32 sm:w-40 sm:h-40 rounded-3xl border-4 border-white shadow-2xl object-cover"
                onError={(e) => {
                  e.target.style.display = 'none';
                  e.target.nextElementSibling.style.display = 'flex';
                }}
              />
            ) : null}
            <div className={`w-32 h-32 sm:w-40 sm:h-40 bg-gradient-to-br from-[#1a6b9a] to-[#0d4a6f] rounded-3xl border-4 border-white shadow-2xl flex items-center justify-center ${profile?.profile_picture ? 'hidden' : ''}`}>
              <span className="text-5xl sm:text-6xl font-semibold text-white">
                {getInitials(profile?.name)}
              </span>
            </div>
            <label className="absolute bottom-2 right-2 w-12 h-12 bg-[#0d4a6f] hover:bg-[#083a57] rounded-full flex items-center justify-center shadow-xl transition-colors cursor-pointer ring-4 ring-white">
              <input
                type="file"
                accept="image/*"
                className="hidden"
                onChange={handleProfilePictureChange}
                disabled={isUploadingPicture}
              />
              {isUploadingPicture ? (
                <Loader2 className="w-6 h-6 text-white animate-spin" />
              ) : (
                <Camera className="w-6 h-6 text-white" />
              )}
            </label>
          </div>
        </div>
      </div>

      {/* Profile Content */}
      <div className="px-4 pt-20 sm:pt-24 max-w-7xl mx-auto">
        {/* Name and Role */}
        <div className="text-center mb-6">
          {isEditing ? (
            <input
              type="text"
              value={editedProfile.name}
              onChange={(e) => setEditedProfile(prev => ({ ...prev, name: e.target.value }))}
              placeholder="Your name"
              className="text-2xl sm:text-3xl font-semibold text-gray-900 border-2 border-gray-300 rounded-xl px-4 py-2 focus:outline-none focus:ring-2 focus:ring-[#1a6b9a] focus:border-transparent w-full max-w-xs mx-auto text-center mb-2"
            />
          ) : (
            <h1 className="text-2xl sm:text-3xl font-semibold text-gray-900 mb-2">
              {profile?.name || 'User'}
            </h1>
          )}
          <div className="flex items-center justify-center gap-2 flex-wrap">
            <span className="inline-flex items-center px-3 py-1 rounded-full text-sm font-medium bg-[#e8f4fc] text-[#0d4a6f]">
              {profile?.role || 'CITIZEN'}
            </span>
            {profile?.email_verified && (
              <span className="inline-flex items-center gap-1 px-3 py-1 rounded-full text-sm font-medium bg-green-100 text-green-700">
                <CheckCircle className="w-4 h-4" />
                Verified
              </span>
            )}
            {rankData && (
              <span className="inline-flex items-center gap-1 px-3 py-1 rounded-full text-sm font-medium bg-amber-100 text-amber-700">
                <Trophy className="w-4 h-4" />
                Rank #{rankData.rank || '-'}
              </span>
            )}
          </div>
        </div>

        {/* Points Summary Card */}
        {rankData && (
          <div className="bg-gradient-to-r from-amber-500 to-orange-500 rounded-2xl p-4 mb-6 text-white">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="w-12 h-12 bg-white/20 rounded-xl flex items-center justify-center">
                  <Trophy className="w-6 h-6" />
                </div>
                <div>
                  <p className="text-white/80 text-sm">Total Points</p>
                  <p className="text-2xl font-semibold">{rankData.total_points || 0}</p>
                </div>
              </div>
              <div className="text-right">
                <p className="text-white/80 text-sm">Events Attended</p>
                <p className="text-2xl font-semibold">{typeof rankData.events_attended === 'object' ? (rankData.events_attended?.events_attended || 0) : (rankData.events_attended || 0)}</p>
              </div>
            </div>
          </div>
        )}

        {/* Tab Navigation */}
        <div className="bg-white rounded-2xl shadow-sm border border-gray-200 mb-6 overflow-x-auto">
          <div className="flex min-w-max">
            {tabs.map(tab => {
              const TabIcon = tab.icon;
              return (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  className={`flex-1 min-w-[100px] flex items-center justify-center gap-2 px-4 py-4 text-sm font-medium transition-colors border-b-2 ${
                    activeTab === tab.id
                      ? 'border-[#0d4a6f] text-[#0d4a6f] bg-[#e8f4fc]/50'
                      : 'border-transparent text-gray-600 hover:text-gray-900 hover:bg-gray-50'
                  }`}
                >
                  <TabIcon className="w-4 h-4" />
                  <span className="hidden sm:inline">{tab.label}</span>
                </button>
              );
            })}
          </div>
        </div>

        {/* Tab Content */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 lg:gap-6">
          {/* Main Content Area */}
          <div className="lg:col-span-2 space-y-4">
            {/* Overview Tab */}
            {activeTab === 'overview' && (
              <>
                {/* Stats Grid */}
                {stats && (
                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 sm:gap-4">
                    <div className="bg-white rounded-xl sm:rounded-2xl shadow-sm border border-gray-200 p-4 sm:p-5">
                      <div className="w-10 h-10 sm:w-12 sm:h-12 bg-gradient-to-br from-blue-500 to-cyan-500 rounded-lg sm:rounded-xl flex items-center justify-center mb-3">
                        <AlertTriangle className="w-5 h-5 sm:w-6 sm:h-6 text-white" />
                      </div>
                      <p className="text-2xl sm:text-3xl font-semibold text-gray-900">{stats.total_reports}</p>
                      <p className="text-xs sm:text-sm text-gray-600 mt-1">Total Reports</p>
                    </div>
                    <div className="bg-white rounded-xl sm:rounded-2xl shadow-sm border border-gray-200 p-4 sm:p-5">
                      <div className="w-10 h-10 sm:w-12 sm:h-12 bg-gradient-to-br from-green-500 to-emerald-500 rounded-lg sm:rounded-xl flex items-center justify-center mb-3">
                        <CheckCircle className="w-5 h-5 sm:w-6 sm:h-6 text-white" />
                      </div>
                      <p className="text-2xl sm:text-3xl font-semibold text-gray-900">{stats.verified_reports}</p>
                      <p className="text-xs sm:text-sm text-gray-600 mt-1">Verified</p>
                    </div>
                    <div className="bg-white rounded-xl sm:rounded-2xl shadow-sm border border-gray-200 p-4 sm:p-5">
                      <div className="w-10 h-10 sm:w-12 sm:h-12 bg-gradient-to-br from-purple-500 to-pink-500 rounded-lg sm:rounded-xl flex items-center justify-center mb-3">
                        <TrendingUp className="w-5 h-5 sm:w-6 sm:h-6 text-white" />
                      </div>
                      <p className="text-2xl sm:text-3xl font-semibold text-gray-900">{stats.credibility_score}</p>
                      <p className="text-xs sm:text-sm text-gray-600 mt-1">Credibility</p>
                    </div>
                    <div className="bg-white rounded-xl sm:rounded-2xl shadow-sm border border-gray-200 p-4 sm:p-5">
                      <div className="w-10 h-10 sm:w-12 sm:h-12 bg-gradient-to-br from-yellow-500 to-orange-500 rounded-lg sm:rounded-xl flex items-center justify-center mb-3">
                        <Clock className="w-5 h-5 sm:w-6 sm:h-6 text-white" />
                      </div>
                      <p className="text-2xl sm:text-3xl font-semibold text-gray-900">{stats.pending_reports}</p>
                      <p className="text-xs sm:text-sm text-gray-600 mt-1">Pending</p>
                    </div>
                  </div>
                )}

                {/* Contact Information Card */}
                <div className="bg-white rounded-2xl shadow-sm border border-gray-200 p-5 sm:p-6">
                  <h3 className="text-lg font-semibold text-gray-900 mb-4">Contact Information</h3>
                  <div className="space-y-4">
                    <div className="flex items-start gap-3">
                      <div className="w-10 h-10 bg-[#e8f4fc] rounded-xl flex items-center justify-center flex-shrink-0">
                        <Mail className="w-5 h-5 text-[#0d4a6f]" />
                      </div>
                      <div className="flex-1 min-w-0">
                        <p className="text-xs text-gray-500 mb-1">Email Address</p>
                        <p className="text-sm font-medium text-gray-900 truncate">{profile?.email || 'Not set'}</p>
                        {profile?.email_verified && (
                          <p className="text-xs text-green-600 mt-1 flex items-center gap-1">
                            <CheckCircle className="w-3 h-3" />
                            Verified
                          </p>
                        )}
                      </div>
                    </div>
                    <div className="flex items-start gap-3">
                      <div className="w-10 h-10 bg-green-50 rounded-xl flex items-center justify-center flex-shrink-0">
                        <Phone className="w-5 h-5 text-green-600" />
                      </div>
                      <div className="flex-1 min-w-0">
                        <p className="text-xs text-gray-500 mb-1">Phone Number</p>
                        {isEditing ? (
                          <input
                            type="tel"
                            value={editedProfile.phone}
                            onChange={(e) => setEditedProfile(prev => ({ ...prev, phone: e.target.value }))}
                            placeholder="+1234567890"
                            className="w-full text-sm font-medium text-gray-900 border-2 border-gray-300 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-[#1a6b9a] focus:border-transparent"
                          />
                        ) : (
                          <p className="text-sm font-medium text-gray-900">{profile?.phone || 'Not set'}</p>
                        )}
                      </div>
                    </div>
                    <div className="flex items-start gap-3">
                      <div className="w-10 h-10 bg-purple-50 rounded-xl flex items-center justify-center flex-shrink-0">
                        <MapPin className="w-5 h-5 text-purple-600" />
                      </div>
                      <div className="flex-1 min-w-0">
                        <p className="text-xs text-gray-500 mb-1">Location</p>
                        <p className="text-sm font-medium text-gray-900">
                          {profile?.location?.city && profile?.location?.state
                            ? `${profile.location.city}, ${profile.location.state}`
                            : profile?.location?.state || 'Not set'}
                        </p>
                      </div>
                    </div>
                  </div>
                </div>

                {/* Bio Card */}
                <div className="bg-white rounded-2xl shadow-sm border border-gray-200 p-5 sm:p-6">
                  <h3 className="text-lg font-semibold text-gray-900 mb-3">About</h3>
                  {isEditing ? (
                    <textarea
                      value={editedProfile.bio}
                      onChange={(e) => setEditedProfile(prev => ({ ...prev, bio: e.target.value }))}
                      placeholder="Tell us about yourself..."
                      className="w-full text-sm text-gray-700 border-2 border-gray-300 rounded-xl px-4 py-3 focus:outline-none focus:ring-2 focus:ring-[#1a6b9a] focus:border-transparent resize-none"
                      rows={4}
                      maxLength={500}
                    />
                  ) : (
                    <p className="text-sm text-gray-700 leading-relaxed whitespace-pre-wrap">
                      {profile?.bio || 'No bio added yet. Click Edit to add one.'}
                    </p>
                  )}
                </div>

                {/* My Reports Section */}
                {!isLoadingReports && reports.length > 0 && (
                  <div className="bg-white rounded-2xl shadow-sm border border-gray-200 p-5 sm:p-6">
                    <div className="flex items-center justify-between mb-4">
                      <h3 className="text-lg font-semibold text-gray-900 flex items-center gap-2">
                        <FileText className="w-5 h-5 text-[#0d4a6f]" />
                        Recent Reports
                      </h3>
                      <span className="text-sm text-gray-500">{reports.length} total</span>
                    </div>
                    <div className="space-y-3">
                      {reports.slice(0, 3).map((report) => {
                        const statusBadge = getStatusBadge(report.verification_status);
                        const StatusIcon = statusBadge.icon;
                        return (
                          <div key={report.report_id} className="border border-gray-200 rounded-xl p-4 hover:border-blue-300 transition-all">
                            <div className="flex items-center justify-between mb-2">
                              <h4 className="font-semibold text-gray-900 text-sm">{report.hazard_type}</h4>
                              <span className={`px-2 py-0.5 ${statusBadge.bg} ${statusBadge.text} text-xs font-semibold rounded-full flex items-center gap-1`}>
                                <StatusIcon className="w-3 h-3" />
                                {statusBadge.label}
                              </span>
                            </div>
                            <div className="flex items-center gap-3 text-xs text-gray-600">
                              <span className="flex items-center gap-1">
                                <Clock className="w-3 h-3" />
                                {formatDate(report.created_at)}
                              </span>
                            </div>
                          </div>
                        );
                      })}
                    </div>
                    {reports.length > 3 && (
                      <Link href="/my-reports" className="block mt-4 text-center text-sm text-[#0d4a6f] font-semibold hover:text-[#083a57]">
                        View all {reports.length} reports
                      </Link>
                    )}
                  </div>
                )}
              </>
            )}

            {/* Events Tab */}
            {activeTab === 'events' && (
              <div className="space-y-4">
                {/* Filter Buttons */}
                <div className="bg-white rounded-2xl shadow-sm border border-gray-200 p-4">
                  <div className="flex flex-wrap gap-2">
                    {['all', 'attended', 'registered', 'confirmed', 'no_show', 'cancelled'].map(filter => (
                      <button
                        key={filter}
                        onClick={() => setEventFilter(filter)}
                        className={`px-3 py-1.5 rounded-lg text-sm font-medium transition ${
                          eventFilter === filter
                            ? 'bg-[#0d4a6f] text-white'
                            : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                        }`}
                      >
                        {filter === 'all' ? 'All' : filter.replace('_', ' ').replace(/^\w/, c => c.toUpperCase())}
                      </button>
                    ))}
                  </div>
                </div>

                {/* Events List */}
                {isLoadingEvents && events.length === 0 ? (
                  <div className="bg-white rounded-2xl shadow-sm border border-gray-200 p-8 text-center">
                    <Loader2 className="w-8 h-8 text-[#0d4a6f] animate-spin mx-auto mb-3" />
                    <p className="text-gray-600">Loading events...</p>
                  </div>
                ) : filteredEvents.length === 0 ? (
                  <div className="bg-white rounded-2xl shadow-sm border border-gray-200 p-8 text-center">
                    <Calendar className="w-12 h-12 text-gray-400 mx-auto mb-3" />
                    <h3 className="text-lg font-semibold text-gray-900 mb-2">No Events Found</h3>
                    <p className="text-gray-600 mb-4">
                      {eventFilter === 'all'
                        ? "You haven't registered for any events yet."
                        : `No ${eventFilter.replace('_', ' ')} events found.`}
                    </p>
                    <Link
                      href="/events"
                      className="inline-flex items-center gap-2 px-4 py-2 bg-[#0d4a6f] text-white rounded-lg hover:bg-[#083a57] transition"
                    >
                      <Calendar className="w-4 h-4" />
                      Browse Events
                    </Link>
                  </div>
                ) : (
                  <div className="space-y-3">
                    {filteredEvents.map((registration) => (
                      <EventHistoryCard
                        key={registration.registration_id}
                        registration={registration}
                        event={registration.event}
                      />
                    ))}

                    {hasMoreEvents && (
                      <button
                        onClick={() => fetchEvents()}
                        disabled={isLoadingEvents}
                        className="w-full py-3 bg-gray-100 text-gray-700 rounded-xl hover:bg-gray-200 transition font-medium disabled:opacity-50"
                      >
                        {isLoadingEvents ? (
                          <Loader2 className="w-5 h-5 animate-spin mx-auto" />
                        ) : (
                          'Load More'
                        )}
                      </button>
                    )}
                  </div>
                )}
              </div>
            )}

            {/* Badges Tab */}
            {activeTab === 'badges' && (
              <div className="space-y-4">
                {isLoadingBadges ? (
                  <div className="bg-white rounded-2xl shadow-sm border border-gray-200 p-8 text-center">
                    <Loader2 className="w-8 h-8 text-[#0d4a6f] animate-spin mx-auto mb-3" />
                    <p className="text-gray-600">Loading badges...</p>
                  </div>
                ) : (
                  <>
                    {/* Earned Badges */}
                    <div className="bg-white rounded-2xl shadow-sm border border-gray-200 p-5 sm:p-6">
                      <h3 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
                        <Award className="w-5 h-5 text-amber-500" />
                        Earned Badges ({rankData?.badges?.length || 0})
                      </h3>
                      {rankData?.badges?.length > 0 ? (
                        <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
                          {rankData.badges.filter(b => typeof b === 'string').map((badgeId, idx) => {
                            const badge = getBadgeInfo(badgeId);
                            const BadgeIcon = badgeIcons[badge.icon] || Award;
                            return (
                              <div
                                key={badgeId || idx}
                                className="bg-gradient-to-br from-amber-50 to-yellow-50 border-2 border-amber-200 rounded-xl p-4 text-center"
                              >
                                <div className={`w-14 h-14 mx-auto mb-3 rounded-full bg-gradient-to-br from-amber-400 to-yellow-500 flex items-center justify-center shadow-lg`}>
                                  <BadgeIcon className="w-7 h-7 text-white" />
                                </div>
                                <h4 className="font-semibold text-gray-900 text-sm mb-1">{badge.name}</h4>
                                <p className="text-xs text-gray-600">{badge.description}</p>
                              </div>
                            );
                          })}
                        </div>
                      ) : (
                        <div className="text-center py-6">
                          <Award className="w-12 h-12 text-gray-300 mx-auto mb-3" />
                          <p className="text-gray-600">No badges earned yet. Attend events to earn badges!</p>
                        </div>
                      )}
                    </div>

                    {/* All Badges */}
                    <div className="bg-white rounded-2xl shadow-sm border border-gray-200 p-5 sm:p-6">
                      <h3 className="text-lg font-semibold text-gray-900 mb-4">All Badges</h3>
                      <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
                        {allBadges.map((badge) => {
                          const isEarned = rankData?.badges?.includes(badge.badge_id);
                          const badgeInfo = getBadgeInfo(badge.badge_id);
                          const BadgeIcon = badgeIcons[badgeInfo.icon] || Award;
                          return (
                            <div
                              key={badge.badge_id}
                              className={`rounded-xl p-4 text-center transition ${
                                isEarned
                                  ? 'bg-gradient-to-br from-amber-50 to-yellow-50 border-2 border-amber-200'
                                  : 'bg-gray-50 border-2 border-gray-200 opacity-60'
                              }`}
                            >
                              <div className={`w-12 h-12 mx-auto mb-3 rounded-full flex items-center justify-center ${
                                isEarned
                                  ? 'bg-gradient-to-br from-amber-400 to-yellow-500 shadow-lg'
                                  : 'bg-gray-300'
                              }`}>
                                <BadgeIcon className={`w-6 h-6 ${isEarned ? 'text-white' : 'text-gray-500'}`} />
                              </div>
                              <h4 className="font-semibold text-gray-900 text-sm mb-1">{badge.name}</h4>
                              <p className="text-xs text-gray-600">{badge.description}</p>
                              {!isEarned && badge.requirement && (
                                <p className="text-xs text-[#0d4a6f] mt-2 font-medium">
                                  {badge.requirement.events_attended ? `${badge.requirement.events_attended} events needed` : JSON.stringify(badge.requirement)}
                                </p>
                              )}
                            </div>
                          );
                        })}
                      </div>
                    </div>
                  </>
                )}
              </div>
            )}

            {/* Certificates Tab */}
            {activeTab === 'certificates' && (
              <div className="space-y-4">
                {isLoadingCertificates ? (
                  <div className="bg-white rounded-2xl shadow-sm border border-gray-200 p-8 text-center">
                    <Loader2 className="w-8 h-8 text-[#0d4a6f] animate-spin mx-auto mb-3" />
                    <p className="text-gray-600">Loading certificates...</p>
                  </div>
                ) : certificates.length === 0 ? (
                  <div className="bg-white rounded-2xl shadow-sm border border-gray-200 p-8 text-center">
                    <FileText className="w-12 h-12 text-gray-400 mx-auto mb-3" />
                    <h3 className="text-lg font-semibold text-gray-900 mb-2">No Certificates Yet</h3>
                    <p className="text-gray-600 mb-4">
                      Attend events to earn certificates of participation.
                    </p>
                    <Link
                      href="/events"
                      className="inline-flex items-center gap-2 px-4 py-2 bg-[#0d4a6f] text-white rounded-lg hover:bg-[#083a57] transition"
                    >
                      <Calendar className="w-4 h-4" />
                      Browse Events
                    </Link>
                  </div>
                ) : (
                  <div className="space-y-3">
                    {certificates.map((cert) => (
                      <div
                        key={cert.certificate_id}
                        className="bg-white rounded-xl shadow-sm border border-gray-200 p-4 hover:shadow-md transition"
                      >
                        <div className="flex items-start gap-4">
                          <div className="w-12 h-12 bg-gradient-to-br from-amber-400 to-yellow-500 rounded-xl flex items-center justify-center flex-shrink-0">
                            <Award className="w-6 h-6 text-white" />
                          </div>
                          <div className="flex-1 min-w-0">
                            <h4 className="font-semibold text-gray-900 mb-1">{cert.event_title}</h4>
                            <p className="text-sm text-gray-600 mb-2">
                              Issued on {formatDateIST(cert.generated_at)}
                            </p>
                            <p className="text-xs text-gray-500 font-mono">ID: {cert.certificate_id}</p>
                          </div>
                          <div className="flex flex-col gap-2">
                            <a
                              href={`${getBackendBaseUrl()}${cert.certificate_url}`}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="flex items-center gap-1.5 px-3 py-1.5 bg-green-600 text-white rounded-lg text-sm font-medium hover:bg-green-700 transition"
                            >
                              <Download className="w-4 h-4" />
                              Download
                            </a>
                            <Link
                              href={`/certificates/verify/${cert.certificate_id}`}
                              className="flex items-center gap-1.5 px-3 py-1.5 bg-gray-100 text-gray-700 rounded-lg text-sm font-medium hover:bg-gray-200 transition"
                            >
                              <ExternalLink className="w-4 h-4" />
                              Verify
                            </Link>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>

          {/* Right Sidebar */}
          <div className="lg:col-span-1 space-y-4">
            {/* Emergency Contacts Card - Always Visible */}
            <div className="bg-white rounded-2xl shadow-sm border-2 border-red-200 p-5">
              <div className="flex items-center justify-between mb-3">
                <h3 className="text-base font-semibold text-gray-900 flex items-center gap-2">
                  <Bell className="w-5 h-5 text-red-500" />
                  Emergency Contacts
                </h3>
                <span className="text-xs text-red-600 bg-red-50 px-2 py-1 rounded-full font-medium">
                  SOS
                </span>
              </div>

              <p className="text-xs text-gray-500 mb-3">
                These contacts receive SMS alerts when you trigger SOS.
              </p>

              {/* Existing Contacts */}
              {(isEditing ? editedProfile.emergency_contacts : emergencyContacts)?.length > 0 ? (
                <div className="space-y-2 mb-3">
                  {(isEditing ? editedProfile.emergency_contacts : emergencyContacts).map((contact, index) => (
                    <div key={index} className="flex items-center gap-2 p-2 bg-red-50 rounded-lg border border-red-100">
                      <div className="w-8 h-8 bg-red-100 rounded-full flex items-center justify-center flex-shrink-0">
                        <User className="w-4 h-4 text-red-600" />
                      </div>
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium text-gray-900 truncate">{contact.name}</p>
                        <p className="text-xs text-gray-500 truncate">{contact.phone}</p>
                      </div>
                      {isEditing && (
                        <button
                          onClick={() => {
                            setEditedProfile(prev => ({
                              ...prev,
                              emergency_contacts: prev.emergency_contacts.filter((_, i) => i !== index)
                            }));
                          }}
                          className="p-1 text-red-600 hover:bg-red-100 rounded transition"
                        >
                          <Trash2 className="w-3 h-3" />
                        </button>
                      )}
                    </div>
                  ))}
                </div>
              ) : (
                <div className="text-center py-4 bg-gray-50 rounded-lg mb-3">
                  <UserPlus className="w-8 h-8 text-gray-400 mx-auto mb-1" />
                  <p className="text-xs text-gray-500">No emergency contacts</p>
                </div>
              )}

              {/* Add New Contact Form (only in edit mode) */}
              {isEditing && (
                <div className="border-t border-gray-200 pt-3">
                  <p className="text-xs font-medium text-gray-600 mb-2">Add Contact</p>
                  <div className="space-y-2">
                    <input
                      type="text"
                      value={newContact.name}
                      onChange={(e) => setNewContact(prev => ({ ...prev, name: e.target.value }))}
                      placeholder="Name"
                      className="w-full text-sm border border-gray-300 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-red-500 focus:border-transparent"
                    />
                    <input
                      type="tel"
                      value={newContact.phone}
                      onChange={(e) => setNewContact(prev => ({ ...prev, phone: e.target.value }))}
                      placeholder="Phone (10 digits)"
                      className="w-full text-sm border border-gray-300 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-red-500 focus:border-transparent"
                    />
                    <select
                      value={newContact.relationship}
                      onChange={(e) => setNewContact(prev => ({ ...prev, relationship: e.target.value }))}
                      className="w-full text-sm border border-gray-300 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-red-500 focus:border-transparent"
                    >
                      <option value="">Relationship</option>
                      <option value="family">Family</option>
                      <option value="spouse">Spouse</option>
                      <option value="friend">Friend</option>
                      <option value="colleague">Colleague</option>
                      <option value="other">Other</option>
                    </select>
                    <button
                      onClick={() => {
                        if (newContact.name && newContact.phone) {
                          setEditedProfile(prev => ({
                            ...prev,
                            emergency_contacts: [...(prev.emergency_contacts || []), newContact]
                          }));
                          setNewContact({ name: '', phone: '', relationship: '' });
                          toast.success('Contact added');
                        } else {
                          toast.error('Please fill name and phone');
                        }
                      }}
                      className="w-full py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition font-medium text-sm flex items-center justify-center gap-1"
                    >
                      <Plus className="w-4 h-4" />
                      Add Contact
                    </button>
                  </div>
                </div>
              )}

              {!isEditing && (
                <p className="text-xs text-gray-400 text-center mt-2">
                  Click "Edit Profile" to manage contacts
                </p>
              )}
            </div>

            {/* Credibility Score Card */}
            {stats && (
              <div className="bg-gradient-to-br from-[#0d4a6f] to-[#1a6b9a] rounded-2xl shadow-xl p-6 text-white ">
                <div className="flex items-center justify-between mb-4">
                  <div className="flex items-center gap-2">
                    <Shield className="w-6 h-6" />
                    <h3 className="text-lg font-bold">Credibility Score</h3>
                  </div>
                </div>
                <div className="mb-4">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-4xl font-semibold">{stats.credibility_score}</span>
                    <span className="text-blue-100">/ 100</span>
                  </div>
                  <div className="w-full bg-white/20 rounded-full h-3">
                    <div
                      className="bg-white h-3 rounded-full transition-all duration-500"
                      style={{ width: `${stats.credibility_score}%` }}
                    ></div>
                  </div>
                </div>
                <div className="grid grid-cols-2 gap-3 pt-3 border-t border-white/20">
                  <div>
                    <p className="text-blue-100 text-xs mb-1">Total Reports</p>
                    <p className="text-xl font-semibold">{stats.total_reports}</p>
                  </div>
                  <div>
                    <p className="text-blue-100 text-xs mb-1">Verified</p>
                    <p className="text-xl font-semibold">{stats.verified_reports}</p>
                  </div>
                </div>
              </div>
            )}

            {/* Quick Actions Card */}
            <div className="bg-white rounded-2xl shadow-sm border border-gray-200 p-6">
              <h3 className="text-lg font-semibold text-gray-900 mb-4">Quick Actions</h3>
              <div className="space-y-3">
                <Link
                  href="/report-hazard"
                  className="w-full px-4 py-3 bg-gradient-to-r from-orange-500 to-red-500 text-white rounded-xl hover:from-orange-600 hover:to-red-600 transition-all font-semibold shadow-md flex items-center justify-center gap-2"
                >
                  <AlertTriangle className="w-5 h-5" />
                  Report Hazard
                </Link>
                <Link
                  href="/events"
                  className="w-full px-4 py-3 bg-blue-50 text-blue-600 rounded-xl hover:bg-blue-100 transition-all font-semibold flex items-center justify-center gap-2"
                >
                  <Calendar className="w-5 h-5" />
                  Browse Events
                </Link>
                <Link
                  href="/leaderboard"
                  className="w-full px-4 py-3 bg-amber-50 text-amber-600 rounded-xl hover:bg-amber-100 transition-all font-semibold flex items-center justify-center gap-2"
                >
                  <Trophy className="w-5 h-5" />
                  Leaderboard
                </Link>
              </div>
            </div>

            {/* Member Info Card */}
            <div className="bg-gradient-to-br from-gray-50 to-gray-100 rounded-2xl shadow-sm border border-gray-200 p-6">
              <h3 className="text-lg font-semibold text-gray-900 mb-3">Member Since</h3>
              <div className="flex items-center gap-3">
                <div className="w-12 h-12 bg-[#0d4a6f] rounded-xl flex items-center justify-center">
                  <User className="w-6 h-6 text-white" />
                </div>
                <div>
                  <p className="text-sm font-semibold text-gray-900">
                    {formatDateIST(profile?.created_at)}
                  </p>
                  <p className="text-xs text-gray-600">
                    {Math.floor((new Date() - new Date(profile?.created_at)) / (1000 * 60 * 60 * 24))} days
                  </p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default function ProfilePage() {
  return (
    <ProtectedRoute>
      <DashboardLayout>
        <ProfileContent />
      </DashboardLayout>
    </ProtectedRoute>
  );
}
