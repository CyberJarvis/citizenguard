'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import {
  Calendar,
  Plus,
  Filter,
  Search,
  MapPin,
  AlertTriangle,
  Users,
  Award,
  Loader2,
  RefreshCw,
  ChevronLeft,
  ChevronRight,
  X
} from 'lucide-react';
import DashboardLayout from '@/components/DashboardLayout';
import EventCard from '@/components/events/EventCard';
import useAuthStore from '@/context/AuthContext';
import {
  listEvents,
  getEventFilterOptions,
  getMyEvents,
  getMyOrganizedEvents,
  getLeaderboard,
  getMyPoints,
  getBadgeInfo
} from '@/lib/api';
import toast from 'react-hot-toast';

export default function EventsPage() {
  const router = useRouter();
  const { user, isAuthenticated } = useAuthStore();
  const [activeTab, setActiveTab] = useState('all');
  const [events, setEvents] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filterOptions, setFilterOptions] = useState(null);

  // Filters
  const [filters, setFilters] = useState({
    coastal_zone: '',
    event_type: '',
    is_emergency: null,
    upcoming_only: true,
  });
  const [showFilters, setShowFilters] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');

  // Pagination
  const [page, setPage] = useState(0);
  const [total, setTotal] = useState(0);
  const limit = 12;

  // Leaderboard & Points
  const [leaderboard, setLeaderboard] = useState([]);
  const [myPoints, setMyPoints] = useState(null);

  const isOrganizer = user?.role === 'verified_organizer' || user?.role === 'authority' || user?.role === 'authority_admin';

  useEffect(() => {
    loadFilterOptions();
    loadLeaderboard();
    if (isAuthenticated) {
      loadMyPoints();
    }
  }, [isAuthenticated]);

  useEffect(() => {
    loadEvents();
  }, [activeTab, filters, page]);

  const loadFilterOptions = async () => {
    try {
      const data = await getEventFilterOptions();
      setFilterOptions(data);
    } catch (error) {
      console.error('Failed to load filter options:', error);
    }
  };

  const loadEvents = async () => {
    try {
      setLoading(true);

      let data;
      if (activeTab === 'my-events' && isAuthenticated) {
        data = await getMyEvents(page * limit, limit);
      } else if (activeTab === 'organized' && isAuthenticated && isOrganizer) {
        data = await getMyOrganizedEvents(page * limit, limit);
      } else {
        data = await listEvents({
          ...filters,
          skip: page * limit,
          limit,
        });
      }

      if (activeTab === 'my-events') {
        // Transform data format for my events
        setEvents(data.events?.map(e => e.event) || []);
      } else {
        setEvents(data.events || []);
      }
      setTotal(data.total || 0);
    } catch (error) {
      console.error('Failed to load events:', error);
      toast.error('Failed to load events');
    } finally {
      setLoading(false);
    }
  };

  const loadLeaderboard = async () => {
    try {
      const data = await getLeaderboard(0, 5);
      setLeaderboard(data.leaderboard || []);
    } catch (error) {
      console.error('Failed to load leaderboard:', error);
    }
  };

  const loadMyPoints = async () => {
    try {
      const data = await getMyPoints();
      setMyPoints(data.points);
    } catch (error) {
      console.error('Failed to load points:', error);
    }
  };

  const handleFilterChange = (key, value) => {
    setFilters(prev => ({ ...prev, [key]: value }));
    setPage(0);
  };

  const clearFilters = () => {
    setFilters({
      coastal_zone: '',
      event_type: '',
      is_emergency: null,
      upcoming_only: true,
    });
    setPage(0);
  };

  const totalPages = Math.ceil(total / limit);

  const tabs = [
    { id: 'all', label: 'All Events', icon: Calendar },
    ...(isAuthenticated ? [{ id: 'my-events', label: 'My Registrations', icon: Users }] : []),
    ...(isOrganizer ? [{ id: 'organized', label: 'My Events', icon: Award }] : []),
  ];

  return (
    <DashboardLayout>
      <div className="min-h-screen bg-gray-50">
        {/* Header */}
        <div className="bg-gradient-to-r from-[#0d4a6f] to-[#083a57] text-white relative overflow-hidden">
          <div className="absolute bottom-0 left-0 right-0 opacity-10">
            <svg viewBox="0 0 1440 120" className="w-full h-12">
              <path fill="white" d="M0,32L48,37.3C96,43,192,53,288,58.7C384,64,480,64,576,58.7C672,53,768,43,864,42.7C960,43,1056,53,1152,58.7C1248,64,1344,64,1392,64L1440,64L1440,120L1392,120C1344,120,1248,120,1152,120C1056,120,960,120,864,120C768,120,672,120,576,120C480,120,384,120,288,120C192,120,96,120,48,120L0,120Z"></path>
            </svg>
          </div>
          <div className="max-w-7xl mx-auto px-4 py-8 sm:px-6 lg:px-8 relative z-10">
            <div className="flex flex-col md:flex-row md:items-center md:justify-between">
              <div>
                <h1 className="text-3xl font-bold flex items-center gap-3">
                  <div className="p-2 bg-white/20 rounded-xl backdrop-blur-sm">
                    <Calendar className="w-6 h-6" />
                  </div>
                  Community Events
                </h1>
                <p className="mt-1 text-[#9ecbec]">
                  Join volunteer events and make a difference for our coasts
                </p>
              </div>
              {isOrganizer && (
                <button
                  onClick={() => router.push('/events/create')}
                  className="mt-4 md:mt-0 inline-flex items-center gap-2 px-4 py-2 bg-white text-[#0d4a6f] rounded-xl font-medium hover:bg-[#e8f4fc] transition"
                >
                  <Plus className="h-5 w-5" />
                  Create Event
                </button>
              )}
            </div>

            {/* Stats Cards */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mt-6">
              <div className="bg-white/10 backdrop-blur-sm rounded-xl p-4 border border-white/10">
                <div className="text-2xl font-bold">{total}</div>
                <div className="text-sm text-[#9ecbec]">Total Events</div>
              </div>
              {myPoints && (
                <>
                  <div className="bg-white/10 backdrop-blur-sm rounded-xl p-4 border border-white/10">
                    <div className="text-2xl font-bold">{myPoints.total_points}</div>
                    <div className="text-sm text-[#9ecbec]">Your Points</div>
                  </div>
                  <div className="bg-white/10 backdrop-blur-sm rounded-xl p-4 border border-white/10">
                    <div className="text-2xl font-bold">{myPoints.events_attended}</div>
                    <div className="text-sm text-[#9ecbec]">Events Attended</div>
                  </div>
                  <div className="bg-white/10 backdrop-blur-sm rounded-xl p-4 border border-white/10">
                    <div className="text-2xl font-bold">{myPoints.badge_count}</div>
                    <div className="text-sm text-[#9ecbec]">Badges Earned</div>
                  </div>
                </>
              )}
            </div>
          </div>
        </div>

        <div className="max-w-7xl mx-auto px-4 py-6 sm:px-6 lg:px-8">
          <div className="flex flex-col lg:flex-row gap-6">
            {/* Main Content */}
            <div className="flex-1">
              {/* Tabs */}
              <div className="flex gap-2 mb-6 overflow-x-auto pb-2">
                {tabs.map(tab => {
                  const TabIcon = tab.icon;
                  return (
                    <button
                      key={tab.id}
                      onClick={() => { setActiveTab(tab.id); setPage(0); }}
                      className={`flex items-center gap-2 px-4 py-2 rounded-xl font-medium whitespace-nowrap transition ${
                        activeTab === tab.id
                          ? 'bg-gradient-to-r from-[#0d4a6f] to-[#083a57] text-white'
                          : 'bg-white text-gray-600 hover:bg-gray-100'
                      }`}
                    >
                      <TabIcon className="h-4 w-4" />
                      {tab.label}
                    </button>
                  );
                })}
              </div>

              {/* Filters Bar */}
              {activeTab === 'all' && (
                <div className="bg-white rounded-lg shadow-sm p-4 mb-6">
                  <div className="flex flex-wrap gap-4 items-center">
                    {/* Search */}
                    <div className="flex-1 min-w-[200px]">
                      <div className="relative">
                        <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400" />
                        <input
                          type="text"
                          placeholder="Search events..."
                          value={searchQuery}
                          onChange={(e) => setSearchQuery(e.target.value)}
                          className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-xl focus:ring-2 focus:ring-[#1a6b9a] focus:border-transparent"
                        />
                      </div>
                    </div>

                    {/* Filter Toggle */}
                    <button
                      onClick={() => setShowFilters(!showFilters)}
                      className={`flex items-center gap-2 px-4 py-2 rounded-lg border ${
                        showFilters ? 'bg-blue-50 border-blue-500 text-blue-600' : 'border-gray-300 text-gray-600'
                      }`}
                    >
                      <Filter className="h-4 w-4" />
                      Filters
                    </button>

                    {/* Upcoming Only Toggle */}
                    <label className="flex items-center gap-2 cursor-pointer">
                      <input
                        type="checkbox"
                        checked={filters.upcoming_only}
                        onChange={(e) => handleFilterChange('upcoming_only', e.target.checked)}
                        className="w-4 h-4 text-blue-600 rounded focus:ring-blue-500"
                      />
                      <span className="text-sm text-gray-600">Upcoming only</span>
                    </label>

                    {/* Emergency Only */}
                    <label className="flex items-center gap-2 cursor-pointer">
                      <input
                        type="checkbox"
                        checked={filters.is_emergency === true}
                        onChange={(e) => handleFilterChange('is_emergency', e.target.checked ? true : null)}
                        className="w-4 h-4 text-red-600 rounded focus:ring-red-500"
                      />
                      <span className="text-sm text-gray-600 flex items-center gap-1">
                        <AlertTriangle className="h-4 w-4 text-red-500" />
                        Emergency
                      </span>
                    </label>
                  </div>

                  {/* Expanded Filters */}
                  {showFilters && filterOptions && (
                    <div className="mt-4 pt-4 border-t border-gray-200 grid grid-cols-1 md:grid-cols-3 gap-4">
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">Coastal Zone</label>
                        <select
                          value={filters.coastal_zone}
                          onChange={(e) => handleFilterChange('coastal_zone', e.target.value)}
                          className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                        >
                          <option value="">All Zones</option>
                          {filterOptions.coastal_zones?.map(zone => (
                            <option key={zone} value={zone}>{zone}</option>
                          ))}
                        </select>
                      </div>

                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">Event Type</label>
                        <select
                          value={filters.event_type}
                          onChange={(e) => handleFilterChange('event_type', e.target.value)}
                          className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                        >
                          <option value="">All Types</option>
                          {filterOptions.event_types?.map(type => (
                            <option key={type.value} value={type.value}>{type.label}</option>
                          ))}
                        </select>
                      </div>

                      <div className="flex items-end">
                        <button
                          onClick={clearFilters}
                          className="px-4 py-2 text-gray-600 hover:text-gray-800 flex items-center gap-2"
                        >
                          <X className="h-4 w-4" />
                          Clear Filters
                        </button>
                      </div>
                    </div>
                  )}
                </div>
              )}

              {/* Events Grid */}
              {loading ? (
                <div className="flex items-center justify-center py-12">
                  <Loader2 className="h-8 w-8 animate-spin text-blue-600" />
                </div>
              ) : events.length === 0 ? (
                <div className="bg-white rounded-lg shadow-sm p-12 text-center">
                  <Calendar className="h-12 w-12 text-gray-400 mx-auto mb-4" />
                  <h3 className="text-lg font-medium text-gray-900">No events found</h3>
                  <p className="text-gray-500 mt-1">
                    {activeTab === 'my-events'
                      ? "You haven't registered for any events yet."
                      : activeTab === 'organized'
                      ? "You haven't organized any events yet."
                      : 'Try adjusting your filters or check back later.'}
                  </p>
                  {isOrganizer && activeTab === 'organized' && (
                    <button
                      onClick={() => router.push('/events/create')}
                      className="mt-4 inline-flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition"
                    >
                      <Plus className="h-4 w-4" />
                      Create Your First Event
                    </button>
                  )}
                </div>
              ) : (
                <>
                  <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                    {events.map(event => (
                      <EventCard
                        key={event.event_id}
                        event={event}
                        isAuthenticated={isAuthenticated}
                        onRegisterChange={() => loadEvents()}
                      />
                    ))}
                  </div>

                  {/* Pagination */}
                  {totalPages > 1 && (
                    <div className="flex items-center justify-center gap-4 mt-8">
                      <button
                        onClick={() => setPage(p => Math.max(0, p - 1))}
                        disabled={page === 0}
                        className="p-2 rounded-lg bg-white border border-gray-300 disabled:opacity-50 disabled:cursor-not-allowed hover:bg-gray-50"
                      >
                        <ChevronLeft className="h-5 w-5" />
                      </button>
                      <span className="text-sm text-gray-600">
                        Page {page + 1} of {totalPages}
                      </span>
                      <button
                        onClick={() => setPage(p => Math.min(totalPages - 1, p + 1))}
                        disabled={page >= totalPages - 1}
                        className="p-2 rounded-lg bg-white border border-gray-300 disabled:opacity-50 disabled:cursor-not-allowed hover:bg-gray-50"
                      >
                        <ChevronRight className="h-5 w-5" />
                      </button>
                    </div>
                  )}
                </>
              )}
            </div>

            {/* Sidebar - Leaderboard */}
            <div className="lg:w-80">
              <div className="bg-white rounded-xl shadow-sm p-6 sticky top-4">
                <h3 className="text-lg font-semibold text-gray-800 flex items-center gap-2 mb-4">
                  <Award className="h-5 w-5 text-amber-500" />
                  Leaderboard
                </h3>

                {leaderboard.length === 0 ? (
                  <p className="text-sm text-gray-500 text-center py-4">
                    No rankings yet. Be the first!
                  </p>
                ) : (
                  <div className="space-y-3">
                    {leaderboard.map((entry, index) => (
                      <div
                        key={entry.user_id}
                        className={`flex items-center gap-3 p-2 rounded-lg ${
                          index === 0 ? 'bg-amber-50' : index === 1 ? 'bg-gray-50' : index === 2 ? 'bg-orange-50' : ''
                        }`}
                      >
                        <div className={`w-8 h-8 rounded-full flex items-center justify-center font-bold text-sm ${
                          index === 0 ? 'bg-amber-500 text-white' :
                          index === 1 ? 'bg-gray-400 text-white' :
                          index === 2 ? 'bg-orange-400 text-white' :
                          'bg-gray-200 text-gray-600'
                        }`}>
                          {entry.rank}
                        </div>
                        <div className="flex-1 min-w-0">
                          <div className="font-medium text-gray-800 truncate">
                            {entry.user_name}
                          </div>
                          <div className="text-xs text-gray-500">
                            {entry.events_attended} events
                          </div>
                        </div>
                        <div className="text-right">
                          <div className="font-semibold text-amber-600">
                            {entry.total_points}
                          </div>
                          <div className="text-xs text-gray-500">pts</div>
                        </div>
                      </div>
                    ))}
                  </div>
                )}

                {/* My Badges */}
                {myPoints && myPoints.badges.length > 0 && (
                  <div className="mt-6 pt-6 border-t border-gray-200">
                    <h4 className="text-sm font-semibold text-gray-700 mb-3">Your Badges</h4>
                    <div className="flex flex-wrap gap-2">
                      {myPoints.badges.map(badge => {
                        const info = getBadgeInfo(badge.badge_id);
                        return (
                          <div
                            key={badge.badge_id}
                            className="px-3 py-1 bg-gradient-to-r from-amber-100 to-amber-50 rounded-full text-xs font-medium text-amber-700"
                            title={info.description}
                          >
                            {info.name}
                          </div>
                        );
                      })}
                    </div>
                  </div>
                )}

                <button
                  onClick={() => router.push('/leaderboard')}
                  className="w-full mt-4 py-2 text-blue-600 hover:text-blue-700 text-sm font-medium"
                >
                  View Full Leaderboard
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </DashboardLayout>
  );
}
