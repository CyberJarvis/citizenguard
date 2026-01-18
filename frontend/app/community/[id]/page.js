'use client';

import { useState, useEffect, useCallback } from 'react';
import { useParams, useRouter } from 'next/navigation';
import Link from 'next/link';
import ProtectedRoute from '@/components/ProtectedRoute';
import DashboardLayout from '@/components/DashboardLayout';
import {
  ArrowLeft,
  Users,
  MapPin,
  Calendar,
  UserPlus,
  UserMinus,
  Settings,
  Loader2,
  CheckCircle,
  Edit,
  Trash2,
  Share2,
  CalendarDays,
  Award,
  Plus,
  MessageSquare,
  History
} from 'lucide-react';
import {
  getCommunityById,
  getCommunityMembers,
  joinCommunity,
  leaveCommunity,
  deleteCommunity,
  listEvents,
  getCommunityPosts
} from '@/lib/api';
import EventCard from '@/components/events/EventCard';
import CommunityPostCard from '@/components/community/CommunityPostCard';
import CreatePostModal from '@/components/community/CreatePostModal';
import { formatDateIST } from '@/lib/dateUtils';
import toast from 'react-hot-toast';
import Cookies from 'js-cookie';
import { jwtDecode } from 'jwt-decode';

const categoryColors = {
  cleanup: { bg: 'bg-blue-100', text: 'text-blue-700', label: 'Beach Cleanup' },
  animal_rescue: { bg: 'bg-green-100', text: 'text-green-700', label: 'Animal Rescue' },
  awareness: { bg: 'bg-purple-100', text: 'text-purple-700', label: 'Awareness' },
  general: { bg: 'bg-gray-100', text: 'text-gray-700', label: 'General' }
};

function CommunityDetailContent() {
  const params = useParams();
  const router = useRouter();
  const communityId = params.id;

  const [currentUser, setCurrentUser] = useState(null);
  const [community, setCommunity] = useState(null);
  const [statistics, setStatistics] = useState(null);
  const [members, setMembers] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isLoadingMembers, setIsLoadingMembers] = useState(false);
  const [isJoining, setIsJoining] = useState(false);
  const [showDeleteModal, setShowDeleteModal] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);
  const [events, setEvents] = useState([]);
  const [pastEvents, setPastEvents] = useState([]);
  const [posts, setPosts] = useState([]);
  const [isLoadingEvents, setIsLoadingEvents] = useState(false);
  const [isLoadingPastEvents, setIsLoadingPastEvents] = useState(false);
  const [isLoadingPosts, setIsLoadingPosts] = useState(false);
  const [showCreatePostModal, setShowCreatePostModal] = useState(false);
  const [activeTab, setActiveTab] = useState('upcoming'); // 'upcoming' | 'past'

  // Get current user
  useEffect(() => {
    const token = Cookies.get('access_token');
    if (token) {
      try {
        const decoded = jwtDecode(token);
        setCurrentUser({
          user_id: decoded.sub || decoded.user_id,
          name: decoded.name || decoded.user_name || 'User',
          role: (decoded.role || 'CITIZEN').toUpperCase()
        });
      } catch (err) {
        console.error('Error decoding token:', err);
      }
    }
  }, []);

  // Load community data
  const loadCommunity = useCallback(async () => {
    setIsLoading(true);
    try {
      const response = await getCommunityById(communityId);
      if (response.success) {
        setCommunity(response.community);
        setStatistics(response.statistics);
      }
    } catch (error) {
      console.error('Error loading community:', error);
      if (error.response?.status === 404) {
        toast.error('Community not found');
        router.push('/community');
      } else {
        toast.error('Failed to load community');
      }
    } finally {
      setIsLoading(false);
    }
  }, [communityId, router]);

  // Load members
  const loadMembers = useCallback(async () => {
    setIsLoadingMembers(true);
    try {
      const response = await getCommunityMembers(communityId, 0, 20);
      if (response.success) {
        setMembers(response.members);
      }
    } catch (error) {
      console.error('Error loading members:', error);
    } finally {
      setIsLoadingMembers(false);
    }
  }, [communityId]);

  // Load community events (upcoming)
  const loadEvents = useCallback(async () => {
    setIsLoadingEvents(true);
    try {
      const response = await listEvents({
        community_id: communityId,
        upcoming_only: true,
        limit: 5
      });
      if (response.success) {
        setEvents(response.events || []);
      }
    } catch (error) {
      console.error('Error loading events:', error);
    } finally {
      setIsLoadingEvents(false);
    }
  }, [communityId]);

  // Load past/completed events
  const loadPastEvents = useCallback(async () => {
    setIsLoadingPastEvents(true);
    try {
      // Fetch completed events specifically
      const response = await listEvents({
        community_id: communityId,
        status: 'completed',
        limit: 20
      });
      if (response.success) {
        setPastEvents(response.events || []);
      }
    } catch (error) {
      console.error('Error loading past events:', error);
    } finally {
      setIsLoadingPastEvents(false);
    }
  }, [communityId]);

  // Load community posts
  const loadPosts = useCallback(async () => {
    setIsLoadingPosts(true);
    try {
      const response = await getCommunityPosts(communityId, 0, 10);
      if (response.success) {
        setPosts(response.posts || []);
      }
    } catch (error) {
      console.error('Error loading posts:', error);
    } finally {
      setIsLoadingPosts(false);
    }
  }, [communityId]);

  useEffect(() => {
    loadCommunity();
    loadMembers();
    loadEvents();
    loadPastEvents();
    loadPosts();
  }, [loadCommunity, loadMembers, loadEvents, loadPastEvents, loadPosts]);

  // Backend base URL for images
  const getImageUrl = (path) => {
    if (!path) return null;
    if (path.startsWith('http')) return path;
    const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';
    return `${apiUrl.replace('/api/v1', '')}${path}`;
  };

  const handleJoinLeave = async () => {
    if (!currentUser) {
      toast.error('Please login to join communities');
      router.push('/login');
      return;
    }

    if (community.is_organizer) {
      toast.error('Organizers cannot leave their own community');
      return;
    }

    setIsJoining(true);
    try {
      if (community.is_member) {
        await leaveCommunity(communityId);
        toast.success('Left the community');
        setCommunity(prev => ({
          ...prev,
          is_member: false,
          member_count: prev.member_count - 1
        }));
      } else {
        await joinCommunity(communityId);
        toast.success('Joined the community!');
        setCommunity(prev => ({
          ...prev,
          is_member: true,
          member_count: prev.member_count + 1
        }));
      }
      loadMembers(); // Refresh member list
    } catch (error) {
      console.error('Error:', error);
      toast.error(error.response?.data?.detail || 'Failed to update membership');
    } finally {
      setIsJoining(false);
    }
  };

  const handleDelete = async () => {
    setIsDeleting(true);
    try {
      await deleteCommunity(communityId);
      toast.success('Community deleted successfully');
      router.push('/community');
    } catch (error) {
      console.error('Error deleting community:', error);
      toast.error(error.response?.data?.detail || 'Failed to delete community');
    } finally {
      setIsDeleting(false);
      setShowDeleteModal(false);
    }
  };

  const handleShare = async () => {
    const url = window.location.href;
    if (navigator.share) {
      try {
        await navigator.share({
          title: community.name,
          text: community.description,
          url
        });
      } catch (err) {
        if (err.name !== 'AbortError') {
          navigator.clipboard.writeText(url);
          toast.success('Link copied to clipboard!');
        }
      }
    } else {
      navigator.clipboard.writeText(url);
      toast.success('Link copied to clipboard!');
    }
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <Loader2 className="w-8 h-8 text-blue-600 animate-spin" />
      </div>
    );
  }

  if (!community) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-center">
          <h2 className="text-xl font-semibold text-gray-800 mb-2">Community not found</h2>
          <Link href="/community" className="text-blue-600 hover:underline">
            Back to Community Hub
          </Link>
        </div>
      </div>
    );
  }

  const categoryConfig = categoryColors[community.category] || categoryColors.general;
  const isOwner = community.is_organizer || currentUser?.role === 'AUTHORITY_ADMIN';

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Cover Image */}
      <div className="relative h-48 sm:h-64 bg-gradient-to-br from-blue-500 to-blue-600">
        {community.cover_image_url && (
          <img
            src={getImageUrl(community.cover_image_url)}
            alt={community.name}
            className="w-full h-full object-cover"
          />
        )}
        {/* Back Button */}
        <Link
          href="/community"
          className="absolute top-4 left-4 flex items-center gap-2 px-3 py-1.5 bg-white/90 backdrop-blur-sm rounded-lg text-gray-700 hover:bg-white transition"
        >
          <ArrowLeft className="w-4 h-4" />
          <span className="hidden sm:inline">Back</span>
        </Link>

        {/* Actions */}
        <div className="absolute top-4 right-4 flex items-center gap-2">
          <button
            onClick={handleShare}
            className="p-2 bg-white/90 backdrop-blur-sm rounded-lg text-gray-700 hover:bg-white transition"
          >
            <Share2 className="w-5 h-5" />
          </button>
          {isOwner && (
            <>
              <Link
                href={`/community/${communityId}/edit`}
                className="p-2 bg-white/90 backdrop-blur-sm rounded-lg text-gray-700 hover:bg-white transition"
              >
                <Edit className="w-5 h-5" />
              </Link>
              <button
                onClick={() => setShowDeleteModal(true)}
                className="p-2 bg-red-500/90 backdrop-blur-sm rounded-lg text-white hover:bg-red-600 transition"
              >
                <Trash2 className="w-5 h-5" />
              </button>
            </>
          )}
        </div>

        {/* Category Badge */}
        <div className={`absolute bottom-4 left-4 px-3 py-1 rounded-full text-sm font-medium ${categoryConfig.bg} ${categoryConfig.text}`}>
          {categoryConfig.label}
        </div>

        {/* Member Badge */}
        {community.is_member && (
          <div className="absolute bottom-4 right-4 px-3 py-1 rounded-full text-sm font-medium bg-green-500 text-white flex items-center gap-1">
            <CheckCircle className="w-4 h-4" />
            Member
          </div>
        )}
      </div>

      <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 -mt-12 relative z-10">
        {/* Header Card */}
        <div className="bg-white rounded-xl shadow-lg p-6 mb-6">
          <div className="flex flex-col sm:flex-row gap-6">
            {/* Logo */}
            <div className="w-24 h-24 rounded-xl bg-white border border-gray-200 flex items-center justify-center shadow-sm flex-shrink-0 -mt-16 sm:-mt-20">
              {community.logo_url ? (
                <img
                  src={getImageUrl(community.logo_url)}
                  alt={community.name}
                  className="w-full h-full object-cover rounded-xl"
                />
              ) : (
                <span className="text-4xl font-bold text-blue-600">
                  {community.name.charAt(0)}
                </span>
              )}
            </div>

            {/* Info */}
            <div className="flex-1">
              <h1 className="text-2xl sm:text-3xl font-bold text-gray-900">{community.name}</h1>
              <p className="text-gray-600 mt-1">Organized by {community.organizer_name}</p>

              {/* Stats */}
              <div className="flex flex-wrap items-center gap-4 mt-4 text-sm text-gray-600">
                <div className="flex items-center gap-1">
                  <Users className="w-4 h-4" />
                  <span>{community.member_count} members</span>
                </div>
                <div className="flex items-center gap-1">
                  <MapPin className="w-4 h-4" />
                  <span>{community.coastal_zone}, {community.state}</span>
                </div>
                <div className="flex items-center gap-1">
                  <Calendar className="w-4 h-4" />
                  <span>Created {formatDateIST(community.created_at)}</span>
                </div>
              </div>
            </div>

            {/* Join Button */}
            {currentUser && !community.is_organizer && (
              <div className="flex-shrink-0">
                <button
                  onClick={handleJoinLeave}
                  disabled={isJoining}
                  className={`flex items-center gap-2 px-6 py-2.5 rounded-lg font-medium transition ${
                    community.is_member
                      ? 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                      : 'bg-blue-600 text-white hover:bg-blue-700'
                  } disabled:opacity-50`}
                >
                  {isJoining ? (
                    <Loader2 className="w-5 h-5 animate-spin" />
                  ) : community.is_member ? (
                    <>
                      <UserMinus className="w-5 h-5" />
                      Leave
                    </>
                  ) : (
                    <>
                      <UserPlus className="w-5 h-5" />
                      Join Community
                    </>
                  )}
                </button>
              </div>
            )}
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Main Content */}
          <div className="lg:col-span-2 space-y-6">
            {/* About */}
            <div className="bg-white rounded-xl shadow-sm p-6">
              <h2 className="text-lg font-semibold text-gray-800 mb-3">About</h2>
              <p className="text-gray-600 whitespace-pre-wrap">{community.description}</p>
            </div>

            {/* Events Section */}
            <div className="bg-white rounded-xl shadow-sm p-6">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-lg font-semibold text-gray-800">Events</h2>
                {isOwner && (
                  <Link
                    href={`/events/create?community=${communityId}`}
                    className="text-sm text-blue-600 hover:text-blue-700 font-medium"
                  >
                    + Create Event
                  </Link>
                )}
              </div>

              {/* Event Tabs */}
              <div className="flex gap-2 mb-4 border-b border-gray-200">
                <button
                  onClick={() => setActiveTab('upcoming')}
                  className={`px-4 py-2 text-sm font-medium border-b-2 transition ${
                    activeTab === 'upcoming'
                      ? 'border-blue-600 text-blue-600'
                      : 'border-transparent text-gray-500 hover:text-gray-700'
                  }`}
                >
                  <div className="flex items-center gap-2">
                    <Calendar className="w-4 h-4" />
                    Upcoming ({events.length})
                  </div>
                </button>
                <button
                  onClick={() => setActiveTab('past')}
                  className={`px-4 py-2 text-sm font-medium border-b-2 transition ${
                    activeTab === 'past'
                      ? 'border-blue-600 text-blue-600'
                      : 'border-transparent text-gray-500 hover:text-gray-700'
                  }`}
                >
                  <div className="flex items-center gap-2">
                    <History className="w-4 h-4" />
                    Past ({pastEvents.length})
                  </div>
                </button>
              </div>

              {/* Upcoming Events */}
              {activeTab === 'upcoming' && (
                <>
                  {isLoadingEvents ? (
                    <div className="flex justify-center py-8">
                      <Loader2 className="w-6 h-6 text-blue-600 animate-spin" />
                    </div>
                  ) : events.length > 0 ? (
                    <div className="space-y-4">
                      {events.map(event => (
                        <EventCard
                          key={event.event_id}
                          event={event}
                          isAuthenticated={!!currentUser}
                          compact={true}
                          onRegisterChange={() => loadEvents()}
                        />
                      ))}
                      {events.length >= 5 && (
                        <Link
                          href={`/events?community_id=${communityId}`}
                          className="block text-center text-sm text-blue-600 hover:text-blue-700 font-medium py-2"
                        >
                          View all events
                        </Link>
                      )}
                    </div>
                  ) : (
                    <div className="text-center py-8">
                      <CalendarDays className="w-12 h-12 text-gray-300 mx-auto mb-3" />
                      <p className="text-gray-500">No upcoming events</p>
                      <p className="text-sm text-gray-400">Events will appear here once created</p>
                    </div>
                  )}
                </>
              )}

              {/* Past Events */}
              {activeTab === 'past' && (
                <>
                  {isLoadingPastEvents ? (
                    <div className="flex justify-center py-8">
                      <Loader2 className="w-6 h-6 text-blue-600 animate-spin" />
                    </div>
                  ) : pastEvents.length > 0 ? (
                    <div className="space-y-4">
                      {pastEvents.map(event => (
                        <EventCard
                          key={event.event_id}
                          event={event}
                          isAuthenticated={!!currentUser}
                          compact={true}
                          onRegisterChange={() => loadPastEvents()}
                        />
                      ))}
                      {pastEvents.length >= 10 && (
                        <Link
                          href={`/events?community_id=${communityId}`}
                          className="block text-center text-sm text-blue-600 hover:text-blue-700 font-medium py-2"
                        >
                          View all past events
                        </Link>
                      )}
                    </div>
                  ) : (
                    <div className="text-center py-8">
                      <History className="w-12 h-12 text-gray-300 mx-auto mb-3" />
                      <p className="text-gray-500">No past events yet</p>
                      <p className="text-sm text-gray-400">Completed events will appear here</p>
                    </div>
                  )}
                </>
              )}
            </div>

            {/* Community Posts Section */}
            <div className="bg-white rounded-xl shadow-sm p-6">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-lg font-semibold text-gray-800">Community Posts</h2>
                {(community.is_member || community.is_organizer) && (
                  <button
                    onClick={() => setShowCreatePostModal(true)}
                    className="flex items-center gap-2 px-3 py-1.5 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 transition"
                  >
                    <Plus className="w-4 h-4" />
                    Create Post
                  </button>
                )}
              </div>

              {isLoadingPosts ? (
                <div className="flex justify-center py-8">
                  <Loader2 className="w-6 h-6 text-blue-600 animate-spin" />
                </div>
              ) : posts.length > 0 ? (
                <div className="space-y-4">
                  {posts.map(post => (
                    <CommunityPostCard
                      key={post.post_id}
                      post={post}
                      communityId={communityId}
                      currentUserId={currentUser?.user_id}
                      isOrganizer={community.is_organizer}
                      onUpdate={() => loadPosts()}
                      onDelete={(postId) => setPosts(prev => prev.filter(p => p.post_id !== postId))}
                    />
                  ))}
                </div>
              ) : (
                <div className="text-center py-8">
                  <MessageSquare className="w-12 h-12 text-gray-300 mx-auto mb-3" />
                  <p className="text-gray-500">No posts yet</p>
                  <p className="text-sm text-gray-400 mb-4">
                    {(community.is_member || community.is_organizer)
                      ? 'Be the first to share something with the community!'
                      : 'Join the community to create posts'}
                  </p>
                  {(community.is_member || community.is_organizer) && (
                    <button
                      onClick={() => setShowCreatePostModal(true)}
                      className="inline-flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 transition"
                    >
                      <Plus className="w-4 h-4" />
                      Create First Post
                    </button>
                  )}
                </div>
              )}
            </div>
          </div>

          {/* Sidebar */}
          <div className="space-y-6">
            {/* Statistics */}
            <div className="bg-white rounded-xl shadow-sm p-6">
              <h2 className="text-lg font-semibold text-gray-800 mb-4">Statistics</h2>
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <span className="text-gray-600">Members</span>
                  <span className="font-semibold text-gray-800">{statistics?.member_count || community.member_count}</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-gray-600">Total Events</span>
                  <span className="font-semibold text-gray-800">{statistics?.total_events || 0}</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-gray-600">Completed Events</span>
                  <span className="font-semibold text-gray-800">{statistics?.completed_events || 0}</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-gray-600">Total Volunteers</span>
                  <span className="font-semibold text-gray-800">{statistics?.total_volunteers || 0}</span>
                </div>
              </div>
            </div>

            {/* Members */}
            <div className="bg-white rounded-xl shadow-sm p-6">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-lg font-semibold text-gray-800">Members</h2>
                <span className="text-sm text-gray-500">{community.member_count}</span>
              </div>

              {isLoadingMembers ? (
                <div className="flex justify-center py-4">
                  <Loader2 className="w-6 h-6 text-blue-600 animate-spin" />
                </div>
              ) : members.length === 0 ? (
                <p className="text-gray-500 text-center py-4">No members yet</p>
              ) : (
                <div className="space-y-3">
                  {members.slice(0, 10).map(member => (
                    <div key={member.user_id} className="flex items-center gap-3">
                      <div className="w-10 h-10 rounded-full bg-gradient-to-br from-blue-500 to-blue-600 flex items-center justify-center text-white font-medium">
                        {member.name?.charAt(0) || 'U'}
                      </div>
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium text-gray-800 truncate">
                          {member.name}
                          {member.is_organizer && (
                            <span className="ml-2 text-xs bg-amber-100 text-amber-700 px-1.5 py-0.5 rounded">
                              Organizer
                            </span>
                          )}
                        </p>
                        <div className="flex items-center gap-1 text-xs text-gray-500">
                          <Award className="w-3 h-3" />
                          <span>{member.credibility_score}% credibility</span>
                        </div>
                      </div>
                    </div>
                  ))}
                  {members.length > 10 && (
                    <button className="w-full text-sm text-blue-600 hover:text-blue-700 font-medium py-2">
                      View all {community.member_count} members
                    </button>
                  )}
                </div>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Delete Modal */}
      {showDeleteModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-xl max-w-md w-full p-6">
            <h3 className="text-lg font-semibold text-gray-800 mb-2">Delete Community</h3>
            <p className="text-gray-600 mb-6">
              Are you sure you want to delete "{community.name}"? This action cannot be undone.
            </p>
            <div className="flex justify-end gap-3">
              <button
                onClick={() => setShowDeleteModal(false)}
                className="px-4 py-2 border border-gray-300 rounded-lg font-medium text-gray-700 hover:bg-gray-50"
              >
                Cancel
              </button>
              <button
                onClick={handleDelete}
                disabled={isDeleting}
                className="px-4 py-2 bg-red-600 text-white rounded-lg font-medium hover:bg-red-700 disabled:opacity-50 flex items-center gap-2"
              >
                {isDeleting ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    Deleting...
                  </>
                ) : (
                  <>
                    <Trash2 className="w-4 h-4" />
                    Delete
                  </>
                )}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Create Post Modal */}
      <CreatePostModal
        isOpen={showCreatePostModal}
        onClose={() => setShowCreatePostModal(false)}
        communityId={communityId}
        isOrganizer={community?.is_organizer}
        onPostCreated={() => loadPosts()}
      />
    </div>
  );
}

export default function CommunityDetailPage() {
  return (
    <ProtectedRoute>
      <DashboardLayout>
        <CommunityDetailContent />
      </DashboardLayout>
    </ProtectedRoute>
  );
}
