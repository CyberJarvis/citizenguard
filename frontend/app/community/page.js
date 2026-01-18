'use client';

import { useEffect, useState, useCallback } from 'react';
import Link from 'next/link';
import ProtectedRoute from '@/components/ProtectedRoute';
import DashboardLayout from '@/components/DashboardLayout';
import CommunityCard from '@/components/community/CommunityCard';
import FloatingChatButton from '@/components/chat/FloatingChatButton';
import {
  Users,
  Search,
  Filter,
  Plus,
  MapPin,
  Loader2,
  ChevronDown,
  RefreshCw,
  Award,
  UserPlus,
  Building2,
  X
} from 'lucide-react';
import {
  listCommunities,
  getMyCommunities,
  getMyOrganizedCommunities,
  getCommunityFilterOptions,
  checkOrganizerEligibility
} from '@/lib/api';
import toast from 'react-hot-toast';
import Cookies from 'js-cookie';
import { jwtDecode } from 'jwt-decode';
import PageHeader from '@/components/PageHeader';

const TABS = [
  { id: 'browse', label: 'Browse All', icon: Building2 },
  { id: 'my', label: 'My Communities', icon: Users },
  { id: 'apply', label: 'Become Organizer', icon: Award }
];

function CommunityHubContent() {
  const [currentUser, setCurrentUser] = useState(null);
  const [activeTab, setActiveTab] = useState('browse');
  const [communities, setCommunities] = useState([]);
  const [myCommunities, setMyCommunities] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isLoadingMy, setIsLoadingMy] = useState(false);
  const [total, setTotal] = useState(0);
  const [myTotal, setMyTotal] = useState(0);

  // Filters
  const [filterOptions, setFilterOptions] = useState(null);
  const [showFilters, setShowFilters] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedZone, setSelectedZone] = useState('');
  const [selectedState, setSelectedState] = useState('');
  const [selectedCategory, setSelectedCategory] = useState('');

  // Organizer eligibility
  const [eligibility, setEligibility] = useState(null);
  const [isCheckingEligibility, setIsCheckingEligibility] = useState(false);

  // Pagination
  const [page, setPage] = useState(0);
  const limit = 12;

  // Get current user from token
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

  // Load filter options
  useEffect(() => {
    const loadFilters = async () => {
      try {
        const response = await getCommunityFilterOptions();
        if (response.success) {
          setFilterOptions({
            coastal_zones: response.coastal_zones,
            states: response.states,
            categories: response.categories
          });
        }
      } catch (error) {
        console.error('Error loading filters:', error);
      }
    };
    loadFilters();
  }, []);

  // Load communities based on active tab
  const loadCommunities = useCallback(async () => {
    setIsLoading(true);
    try {
      const params = {
        skip: page * limit,
        limit
      };
      if (searchQuery) params.search = searchQuery;
      if (selectedZone) params.coastal_zone = selectedZone;
      if (selectedState) params.state = selectedState;
      if (selectedCategory) params.category = selectedCategory;

      const response = await listCommunities(params);
      if (response.success) {
        setCommunities(response.communities);
        setTotal(response.total);
      }
    } catch (error) {
      console.error('Error loading communities:', error);
      toast.error('Failed to load communities');
    } finally {
      setIsLoading(false);
    }
  }, [page, searchQuery, selectedZone, selectedState, selectedCategory]);

  const loadMyCommunities = useCallback(async () => {
    if (!currentUser) return;
    setIsLoadingMy(true);
    try {
      const response = await getMyCommunities(0, 50);
      if (response.success) {
        setMyCommunities(response.communities);
        setMyTotal(response.total);
      }
    } catch (error) {
      console.error('Error loading my communities:', error);
      toast.error('Failed to load your communities');
    } finally {
      setIsLoadingMy(false);
    }
  }, [currentUser]);

  const checkEligibility = useCallback(async () => {
    if (!currentUser) return;
    setIsCheckingEligibility(true);
    try {
      const response = await checkOrganizerEligibility();
      setEligibility(response);
    } catch (error) {
      console.error('Error checking eligibility:', error);
    } finally {
      setIsCheckingEligibility(false);
    }
  }, [currentUser]);

  useEffect(() => {
    if (activeTab === 'browse') {
      loadCommunities();
    } else if (activeTab === 'my' && currentUser) {
      loadMyCommunities();
    } else if (activeTab === 'apply' && currentUser) {
      checkEligibility();
    }
  }, [activeTab, loadCommunities, loadMyCommunities, checkEligibility, currentUser]);

  // Reset page on filter change
  useEffect(() => {
    setPage(0);
  }, [searchQuery, selectedZone, selectedState, selectedCategory]);

  const handleJoinLeave = (communityId, isNowMember) => {
    // Update local state
    setCommunities(prev =>
      prev.map(c =>
        c.community_id === communityId
          ? { ...c, is_member: isNowMember, member_count: c.member_count + (isNowMember ? 1 : -1) }
          : c
      )
    );
    // Refresh my communities if needed
    if (activeTab === 'my') {
      loadMyCommunities();
    }
  };

  const clearFilters = () => {
    setSearchQuery('');
    setSelectedZone('');
    setSelectedState('');
    setSelectedCategory('');
  };

  const hasActiveFilters = searchQuery || selectedZone || selectedState || selectedCategory;

  const isOrganizer = currentUser?.role === 'VERIFIED_ORGANIZER' ||
                      currentUser?.role === 'AUTHORITY' ||
                      currentUser?.role === 'AUTHORITY_ADMIN';

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Top Icons Bar */}
      <div className="px-4 pt-4 lg:px-6 lg:pt-4">
        <PageHeader />
      </div>

      {/* Header */}
      <div className="bg-gradient-to-r from-[#0d4a6f] to-[#083a57] text-white">
        <div className="max-w-7xl mx-auto px-4 py-6 sm:px-6 lg:px-8">
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
            <div>
              <h1 className="text-2xl sm:text-3xl font-semibold">Community Hub</h1>
              <p className="text-cyan-100 mt-1">
                Join coastal conservation communities and make a difference
              </p>
            </div>
            {isOrganizer && (
              <Link
                href="/community/create"
                className="inline-flex items-center gap-2 px-4 py-2.5 bg-white text-[#0d4a6f] rounded-lg font-medium hover:bg-cyan-50 transition shadow-sm"
              >
                <Plus className="w-5 h-5" />
                Create Community
              </Link>
            )}
          </div>

          {/* Tabs */}
          <div className="mt-6 flex gap-1 bg-[#1a6b9a]/30 p-1 rounded-lg w-fit">
            {TABS.map(tab => {
              // Hide apply tab if already organizer
              if (tab.id === 'apply' && isOrganizer) return null;

              const Icon = tab.icon;
              return (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  className={`flex items-center gap-2 px-4 py-2 rounded-md text-sm font-medium transition ${
                    activeTab === tab.id
                      ? 'bg-white text-[#0d4a6f] shadow-sm'
                      : 'text-white hover:bg-[#1a6b9a]/50'
                  }`}
                >
                  <Icon className="w-4 h-4" />
                  <span className="hidden sm:inline">{tab.label}</span>
                </button>
              );
            })}
          </div>
        </div>
      </div>

      {/* Content */}
      <div className="max-w-7xl mx-auto px-4 py-6 sm:px-6 lg:px-8">
        {/* Browse Tab */}
        {activeTab === 'browse' && (
          <>
            {/* Search & Filter Bar */}
            <div className="mb-6 flex flex-col sm:flex-row gap-4">
              {/* Search */}
              <div className="relative flex-1">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
                <input
                  type="text"
                  placeholder="Search communities..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="w-full pl-10 pr-4 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-[#1a6b9a] focus:border-[#1a6b9a]"
                />
              </div>

              {/* Filter Toggle */}
              <button
                onClick={() => setShowFilters(!showFilters)}
                className={`flex items-center gap-2 px-4 py-2.5 border rounded-lg font-medium transition ${
                  showFilters || hasActiveFilters
                    ? 'bg-[#e8f4fc] border-[#9ecbec] text-[#0d4a6f]'
                    : 'bg-white border-gray-300 text-gray-700 hover:bg-gray-50'
                }`}
              >
                <Filter className="w-5 h-5" />
                Filters
                {hasActiveFilters && (
                  <span className="bg-[#0d4a6f] text-white text-xs px-1.5 py-0.5 rounded-full">
                    {[selectedZone, selectedState, selectedCategory].filter(Boolean).length}
                  </span>
                )}
              </button>

              {/* Refresh */}
              <button
                onClick={loadCommunities}
                disabled={isLoading}
                className="flex items-center gap-2 px-4 py-2.5 bg-white border border-gray-300 rounded-lg font-medium text-gray-700 hover:bg-gray-50 transition disabled:opacity-50"
              >
                <RefreshCw className={`w-5 h-5 ${isLoading ? 'animate-spin' : ''}`} />
                <span className="hidden sm:inline">Refresh</span>
              </button>
            </div>

            {/* Filter Panel */}
            {showFilters && filterOptions && (
              <div className="mb-6 p-4 bg-white rounded-lg border border-gray-200 shadow-sm">
                <div className="flex items-center justify-between mb-4">
                  <h3 className="font-medium text-gray-800">Filter Communities</h3>
                  {hasActiveFilters && (
                    <button
                      onClick={clearFilters}
                      className="text-sm text-[#0d4a6f] hover:text-[#083a57] flex items-center gap-1"
                    >
                      <X className="w-4 h-4" />
                      Clear all
                    </button>
                  )}
                </div>
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                  {/* Coastal Zone */}
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Coastal Zone
                    </label>
                    <select
                      value={selectedZone}
                      onChange={(e) => setSelectedZone(e.target.value)}
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-[#1a6b9a] focus:border-[#1a6b9a]"
                    >
                      <option value="">All Zones</option>
                      {filterOptions.coastal_zones.map(zone => (
                        <option key={zone} value={zone}>{zone}</option>
                      ))}
                    </select>
                  </div>

                  {/* State */}
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      State
                    </label>
                    <select
                      value={selectedState}
                      onChange={(e) => setSelectedState(e.target.value)}
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-[#1a6b9a] focus:border-[#1a6b9a]"
                    >
                      <option value="">All States</option>
                      {filterOptions.states.map(state => (
                        <option key={state} value={state}>{state}</option>
                      ))}
                    </select>
                  </div>

                  {/* Category */}
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Category
                    </label>
                    <select
                      value={selectedCategory}
                      onChange={(e) => setSelectedCategory(e.target.value)}
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-[#1a6b9a] focus:border-[#1a6b9a]"
                    >
                      <option value="">All Categories</option>
                      {filterOptions.categories.map(cat => (
                        <option key={cat.value} value={cat.value}>{cat.label}</option>
                      ))}
                    </select>
                  </div>
                </div>
              </div>
            )}

            {/* Results Info */}
            <div className="mb-4 flex items-center justify-between">
              <p className="text-sm text-gray-600">
                {isLoading ? 'Loading...' : `${total} communities found`}
              </p>
            </div>

            {/* Communities Grid */}
            {isLoading ? (
              <div className="flex items-center justify-center py-12">
                <Loader2 className="w-8 h-8 text-[#0d4a6f] animate-spin" />
              </div>
            ) : communities.length === 0 ? (
              <div className="text-center py-12 bg-white rounded-lg border border-gray-200">
                <Building2 className="w-12 h-12 text-gray-400 mx-auto mb-3" />
                <h3 className="text-lg font-semibold text-gray-800 mb-1">No communities found</h3>
                <p className="text-gray-600 mb-4">
                  {hasActiveFilters
                    ? 'Try adjusting your filters or search query'
                    : 'Be the first to create a community!'}
                </p>
                {hasActiveFilters && (
                  <button
                    onClick={clearFilters}
                    className="text-[#0d4a6f] hover:text-[#083a57] font-medium"
                  >
                    Clear filters
                  </button>
                )}
              </div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                {communities.map(community => (
                  <CommunityCard
                    key={community.community_id}
                    community={community}
                    isAuthenticated={!!currentUser}
                    onJoinLeave={handleJoinLeave}
                  />
                ))}
              </div>
            )}

            {/* Pagination */}
            {total > limit && (
              <div className="mt-8 flex items-center justify-center gap-4">
                <button
                  onClick={() => setPage(p => Math.max(0, p - 1))}
                  disabled={page === 0}
                  className="px-4 py-2 bg-white border border-gray-300 rounded-lg font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  Previous
                </button>
                <span className="text-sm text-gray-600">
                  Page {page + 1} of {Math.ceil(total / limit)}
                </span>
                <button
                  onClick={() => setPage(p => p + 1)}
                  disabled={(page + 1) * limit >= total}
                  className="px-4 py-2 bg-white border border-gray-300 rounded-lg font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  Next
                </button>
              </div>
            )}
          </>
        )}

        {/* My Communities Tab */}
        {activeTab === 'my' && (
          <>
            {!currentUser ? (
              <div className="text-center py-12 bg-white rounded-lg border border-gray-200">
                <Users className="w-12 h-12 text-gray-400 mx-auto mb-3" />
                <h3 className="text-lg font-semibold text-gray-800 mb-1">Login Required</h3>
                <p className="text-gray-600 mb-4">
                  Please login to see your communities
                </p>
                <Link
                  href="/login"
                  className="inline-flex items-center gap-2 px-4 py-2 bg-[#0d4a6f] text-white rounded-lg font-medium hover:bg-[#083a57] transition"
                >
                  Login
                </Link>
              </div>
            ) : isLoadingMy ? (
              <div className="flex items-center justify-center py-12">
                <Loader2 className="w-8 h-8 text-[#0d4a6f] animate-spin" />
              </div>
            ) : myCommunities.length === 0 ? (
              <div className="text-center py-12 bg-white rounded-lg border border-gray-200">
                <Users className="w-12 h-12 text-gray-400 mx-auto mb-3" />
                <h3 className="text-lg font-semibold text-gray-800 mb-1">No communities yet</h3>
                <p className="text-gray-600 mb-4">
                  Join communities to participate in coastal conservation efforts
                </p>
                <button
                  onClick={() => setActiveTab('browse')}
                  className="inline-flex items-center gap-2 px-4 py-2 bg-[#0d4a6f] text-white rounded-lg font-medium hover:bg-[#083a57] transition"
                >
                  <Search className="w-4 h-4" />
                  Browse Communities
                </button>
              </div>
            ) : (
              <>
                <p className="text-sm text-gray-600 mb-4">
                  You are a member of {myTotal} {myTotal === 1 ? 'community' : 'communities'}
                </p>
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                  {myCommunities.map(community => (
                    <CommunityCard
                      key={community.community_id}
                      community={community}
                      isAuthenticated={true}
                      onJoinLeave={handleJoinLeave}
                    />
                  ))}
                </div>
              </>
            )}
          </>
        )}

        {/* Apply Tab */}
        {activeTab === 'apply' && !isOrganizer && (
          <>
            {!currentUser ? (
              <div className="text-center py-12 bg-white rounded-lg border border-gray-200">
                <Award className="w-12 h-12 text-gray-400 mx-auto mb-3" />
                <h3 className="text-lg font-semibold text-gray-800 mb-1">Login Required</h3>
                <p className="text-gray-600 mb-4">
                  Please login to apply as an organizer
                </p>
                <Link
                  href="/login"
                  className="inline-flex items-center gap-2 px-4 py-2 bg-[#0d4a6f] text-white rounded-lg font-medium hover:bg-[#083a57] transition"
                >
                  Login
                </Link>
              </div>
            ) : isCheckingEligibility ? (
              <div className="flex items-center justify-center py-12">
                <Loader2 className="w-8 h-8 text-[#0d4a6f] animate-spin" />
              </div>
            ) : (
              <div className="max-w-2xl mx-auto">
                <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
                  {/* Header */}
                  <div className="bg-gradient-to-r from-amber-500 to-orange-500 p-6 text-white">
                    <div className="flex items-center gap-4">
                      <div className="w-16 h-16 bg-white/20 rounded-full flex items-center justify-center">
                        <Award className="w-8 h-8" />
                      </div>
                      <div>
                        <h2 className="text-xl font-semibold">Become a Verified Organizer</h2>
                        <p className="text-amber-100">Lead coastal conservation efforts in your community</p>
                      </div>
                    </div>
                  </div>

                  {/* Content */}
                  <div className="p-6">
                    {eligibility?.existing_application?.status === 'pending' ? (
                      <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4 mb-6">
                        <h3 className="font-semibold text-yellow-800 mb-1">Application Pending</h3>
                        <p className="text-sm text-yellow-700">
                          Your organizer application is being reviewed. You will be notified once a decision is made.
                        </p>
                      </div>
                    ) : eligibility?.eligible ? (
                      <>
                        <div className="bg-green-50 border border-green-200 rounded-lg p-4 mb-6">
                          <h3 className="font-semibold text-green-800 mb-1">You're Eligible!</h3>
                          <p className="text-sm text-green-700">
                            Your credibility score of {eligibility.credibility_score}% qualifies you to apply.
                          </p>
                        </div>

                        <h3 className="font-medium text-gray-800 mb-3">As an organizer, you can:</h3>
                        <ul className="space-y-2 mb-6">
                          {[
                            'Create and manage communities',
                            'Organize beach cleanup events',
                            'Respond to hazard alerts with events',
                            'Mark volunteer attendance',
                            'Issue participation certificates'
                          ].map((benefit, i) => (
                            <li key={i} className="flex items-center gap-2 text-gray-600">
                              <div className="w-5 h-5 bg-[#e8f4fc] rounded-full flex items-center justify-center">
                                <svg className="w-3 h-3 text-[#0d4a6f]" fill="currentColor" viewBox="0 0 20 20">
                                  <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                                </svg>
                              </div>
                              {benefit}
                            </li>
                          ))}
                        </ul>

                        <Link
                          href="/community/apply"
                          className="w-full inline-flex items-center justify-center gap-2 px-4 py-3 bg-[#0d4a6f] text-white rounded-lg font-medium hover:bg-[#083a57] transition"
                        >
                          <UserPlus className="w-5 h-5" />
                          Apply Now
                        </Link>
                      </>
                    ) : (
                      <>
                        <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-6">
                          <h3 className="font-semibold text-red-800 mb-1">Not Yet Eligible</h3>
                          <p className="text-sm text-red-700">
                            You need a credibility score of at least {eligibility?.required_score || 80}% to apply.
                            Your current score is {eligibility?.credibility_score || 0}%.
                          </p>
                        </div>

                        <h3 className="font-medium text-gray-800 mb-3">How to increase your credibility:</h3>
                        <ul className="space-y-2 mb-6">
                          {[
                            'Submit accurate hazard reports',
                            'Participate in community events',
                            'Get your reports verified by authorities',
                            'Maintain consistent activity on the platform'
                          ].map((tip, i) => (
                            <li key={i} className="flex items-center gap-2 text-gray-600">
                              <div className="w-5 h-5 bg-gray-100 rounded-full flex items-center justify-center text-xs font-medium text-gray-500">
                                {i + 1}
                              </div>
                              {tip}
                            </li>
                          ))}
                        </ul>

                        {/* Progress Bar */}
                        <div className="mt-4">
                          <div className="flex justify-between text-sm mb-1">
                            <span className="text-gray-600">Your Progress</span>
                            <span className="font-medium text-gray-800">
                              {eligibility?.credibility_score || 0}% / {eligibility?.required_score || 80}%
                            </span>
                          </div>
                          <div className="h-3 bg-gray-200 rounded-full overflow-hidden">
                            <div
                              className="h-full bg-[#0d4a6f] rounded-full transition-all"
                              style={{
                                width: `${Math.min(100, ((eligibility?.credibility_score || 0) / (eligibility?.required_score || 80)) * 100)}%`
                              }}
                            />
                          </div>
                        </div>
                      </>
                    )}
                  </div>
                </div>
              </div>
            )}
          </>
        )}
      </div>

      {/* Floating Chat Button */}
      <FloatingChatButton />
    </div>
  );
}

export default function CommunityPage() {
  return (
    <ProtectedRoute>
      <DashboardLayout>
        <CommunityHubContent />
      </DashboardLayout>
    </ProtectedRoute>
  );
}
