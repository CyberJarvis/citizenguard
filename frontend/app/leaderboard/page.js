'use client';

import { useState, useEffect, useCallback } from 'react';
import Link from 'next/link';
import DashboardLayout from '@/components/DashboardLayout';
import LeaderboardPodium from '@/components/leaderboard/LeaderboardPodium';
import LeaderboardCard from '@/components/leaderboard/LeaderboardCard';
import {
  Trophy,
  Medal,
  Loader2,
  RefreshCw,
  TrendingUp,
  Award,
  Users,
  Calendar,
  ChevronLeft,
  ChevronRight,
  Star,
  Shield,
  Crown,
  Target
} from 'lucide-react';
import { getLeaderboard, getMyRank, getMyPoints, getAllBadges, getBadgeInfo } from '@/lib/api';
import Cookies from 'js-cookie';
import PageHeader from '@/components/PageHeader';
import { jwtDecode } from 'jwt-decode';

const badgeIcons = {
  first_timer: Star,
  active_volunteer: Award,
  ocean_defender: Shield,
  beach_warrior: Trophy,
  super_volunteer: Crown,
  emergency_responder: Shield,
  community_builder: Users,
};

const badgeColors = {
  first_timer: { bg: 'bg-amber-100', text: 'text-amber-600' },
  active_volunteer: { bg: 'bg-[#e8f4fc]', text: 'text-[#0d4a6f]' },
  ocean_defender: { bg: 'bg-cyan-100', text: 'text-cyan-600' },
  beach_warrior: { bg: 'bg-yellow-100', text: 'text-yellow-600' },
  super_volunteer: { bg: 'bg-purple-100', text: 'text-purple-600' },
  emergency_responder: { bg: 'bg-red-100', text: 'text-red-600' },
  community_builder: { bg: 'bg-green-100', text: 'text-green-600' },
};

export default function LeaderboardPage() {
  const [currentUser, setCurrentUser] = useState(null);
  const [leaderboard, setLeaderboard] = useState([]);
  const [myRank, setMyRank] = useState(null);
  const [myPoints, setMyPoints] = useState(null);
  const [allBadges, setAllBadges] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [page, setPage] = useState(0);
  const [total, setTotal] = useState(0);
  const limit = 20;

  // Get current user from token
  useEffect(() => {
    const token = Cookies.get('access_token');
    if (token) {
      try {
        const decoded = jwtDecode(token);
        setCurrentUser({
          user_id: decoded.sub || decoded.user_id,
          name: decoded.name || decoded.user_name || 'User',
        });
      } catch (err) {
        console.error('Error decoding token:', err);
      }
    }
  }, []);

  // Load leaderboard data
  const loadData = useCallback(async (isRefresh = false) => {
    if (isRefresh) {
      setIsRefreshing(true);
    } else {
      setIsLoading(true);
    }

    try {
      const [leaderboardRes, badgesRes] = await Promise.all([
        getLeaderboard(page * limit, limit),
        getAllBadges()
      ]);

      if (leaderboardRes.success) {
        setLeaderboard(leaderboardRes.leaderboard || []);
        setTotal(leaderboardRes.total || 0);
      }

      if (badgesRes.success) {
        setAllBadges(badgesRes.badges || []);
      }

      // Load user-specific data if logged in
      if (currentUser) {
        const [rankRes, pointsRes] = await Promise.all([
          getMyRank().catch(() => null),
          getMyPoints().catch(() => null)
        ]);

        if (rankRes?.success) {
          setMyRank(rankRes);
        }
        if (pointsRes?.success) {
          setMyPoints(pointsRes);
        }
      }
    } catch (error) {
      console.error('Error loading leaderboard:', error);
    } finally {
      setIsLoading(false);
      setIsRefreshing(false);
    }
  }, [page, currentUser]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const handleRefresh = () => {
    loadData(true);
  };

  const topThree = leaderboard.slice(0, 3);
  const restOfLeaderboard = page === 0 ? leaderboard.slice(3) : leaderboard;
  const totalPages = Math.ceil(total / limit);

  // Check if current user is in the displayed list
  const currentUserInList = leaderboard.find(u => u.user_id === currentUser?.user_id);

  return (
    <DashboardLayout>
      <div className="p-4 lg:p-6 pb-24 lg:pb-8">
        {/* Top Icons Bar */}
        <PageHeader />

        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-8 mt-4">
          <div>
            <h1 className="text-2xl sm:text-3xl font-semibold text-gray-900 flex items-center gap-3">
              <Trophy className="w-8 h-8 text-yellow-500" />
              Leaderboard
            </h1>
            <p className="text-gray-600 mt-1">
              Top volunteers making a difference in coastal conservation
            </p>
          </div>

          <button
            onClick={handleRefresh}
            disabled={isRefreshing}
            className="flex items-center gap-2 px-4 py-2 bg-white border border-gray-200 rounded-lg hover:bg-gray-50 transition disabled:opacity-50"
          >
            <RefreshCw className={`w-4 h-4 ${isRefreshing ? 'animate-spin' : ''}`} />
            Refresh
          </button>
        </div>

        {isLoading ? (
          <div className="flex items-center justify-center py-20">
            <Loader2 className="w-8 h-8 text-[#0d4a6f] animate-spin" />
          </div>
        ) : (
          <>
            {/* Current User Stats (if logged in and not in top 3) */}
            {currentUser && myPoints && !currentUserInList && (
              <div className="bg-gradient-to-r from-[#e8f4fc] to-cyan-50 border border-[#9ecbec] rounded-xl p-4 mb-6">
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                  <div className="flex items-center gap-4">
                    <div className="w-12 h-12 rounded-full bg-gradient-to-br from-[#1a6b9a] to-[#0d4a6f] flex items-center justify-center">
                      <span className="text-white text-lg font-semibold">
                        {currentUser.name?.charAt(0)?.toUpperCase() || '?'}
                      </span>
                    </div>
                    <div>
                      <p className="font-semibold text-gray-800">Your Ranking</p>
                      <p className="text-sm text-gray-600">
                        {myRank?.rank ? `#${myRank.rank} of ${total} volunteers` : 'Keep volunteering to get ranked!'}
                      </p>
                    </div>
                  </div>

                  <div className="flex items-center gap-6">
                    <div className="text-center">
                      <p className="text-2xl font-semibold text-[#0d4a6f]">{myPoints.total_points?.toLocaleString() || 0}</p>
                      <p className="text-xs text-gray-500">Points</p>
                    </div>
                    <div className="text-center">
                      <p className="text-2xl font-semibold text-green-600">{myPoints.events_attended || 0}</p>
                      <p className="text-xs text-gray-500">Events</p>
                    </div>
                    <div className="text-center">
                      <p className="text-2xl font-semibold text-purple-600">{myPoints.badges?.length || 0}</p>
                      <p className="text-xs text-gray-500">Badges</p>
                    </div>
                    {myRank?.points_to_next_rank > 0 && (
                      <div className="text-center hidden sm:block">
                        <p className="text-lg font-semibold text-amber-600">+{myRank.points_to_next_rank}</p>
                        <p className="text-xs text-gray-500">to next rank</p>
                      </div>
                    )}
                  </div>
                </div>

                {/* User's badges */}
                {myPoints.badges?.length > 0 && (
                  <div className="mt-4 pt-4 border-t border-[#c5e1f5]">
                    <p className="text-xs font-medium text-gray-500 mb-2">Your Badges</p>
                    <div className="flex flex-wrap gap-2">
                      {myPoints.badges.map((badge, idx) => {
                        const BadgeIcon = badgeIcons[badge] || Award;
                        const colors = badgeColors[badge] || { bg: 'bg-gray-100', text: 'text-gray-600' };
                        const info = getBadgeInfo(badge);
                        return (
                          <div
                            key={idx}
                            className={`flex items-center gap-1.5 px-2 py-1 rounded-full ${colors.bg} ${colors.text}`}
                            title={info?.description}
                          >
                            <BadgeIcon className="w-4 h-4" />
                            <span className="text-xs font-medium">{info?.name}</span>
                          </div>
                        );
                      })}
                    </div>
                  </div>
                )}
              </div>
            )}

            {/* Top 3 Podium */}
            {page === 0 && topThree.length > 0 && (
              <LeaderboardPodium topThree={topThree} currentUserId={currentUser?.user_id} />
            )}

            {/* Stats Overview */}
            {page === 0 && (
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
                <div className="bg-white rounded-xl p-4 border border-gray-100 shadow-sm">
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded-lg bg-[#e8f4fc] flex items-center justify-center">
                      <Users className="w-5 h-5 text-[#0d4a6f]" />
                    </div>
                    <div>
                      <p className="text-2xl font-semibold text-gray-800">{total}</p>
                      <p className="text-xs text-gray-500">Total Volunteers</p>
                    </div>
                  </div>
                </div>

                <div className="bg-white rounded-xl p-4 border border-gray-100 shadow-sm">
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded-lg bg-amber-100 flex items-center justify-center">
                      <Trophy className="w-5 h-5 text-amber-600" />
                    </div>
                    <div>
                      <p className="text-2xl font-semibold text-gray-800">
                        {topThree[0]?.total_points?.toLocaleString() || 0}
                      </p>
                      <p className="text-xs text-gray-500">Top Points</p>
                    </div>
                  </div>
                </div>

                <div className="bg-white rounded-xl p-4 border border-gray-100 shadow-sm">
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded-lg bg-green-100 flex items-center justify-center">
                      <Calendar className="w-5 h-5 text-green-600" />
                    </div>
                    <div>
                      <p className="text-2xl font-semibold text-gray-800">
                        {topThree[0]?.events_attended || 0}
                      </p>
                      <p className="text-xs text-gray-500">Most Events</p>
                    </div>
                  </div>
                </div>

                <div className="bg-white rounded-xl p-4 border border-gray-100 shadow-sm">
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded-lg bg-purple-100 flex items-center justify-center">
                      <Award className="w-5 h-5 text-purple-600" />
                    </div>
                    <div>
                      <p className="text-2xl font-semibold text-gray-800">{allBadges.length}</p>
                      <p className="text-xs text-gray-500">Badge Types</p>
                    </div>
                  </div>
                </div>
              </div>
            )}

            {/* Leaderboard List */}
            <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
              <div className="px-6 py-4 border-b border-gray-100 flex items-center justify-between">
                <h2 className="font-semibold text-gray-800 flex items-center gap-2">
                  <Medal className="w-5 h-5 text-gray-400" />
                  {page === 0 ? 'Rankings' : `Rankings (${page * limit + 1} - ${Math.min((page + 1) * limit, total)})`}
                </h2>
                <span className="text-sm text-gray-500">{total} volunteers</span>
              </div>

              <div className="divide-y divide-gray-50">
                {(page === 0 ? restOfLeaderboard : leaderboard).length === 0 ? (
                  <div className="text-center py-12">
                    <Target className="w-12 h-12 text-gray-300 mx-auto mb-3" />
                    <p className="text-gray-500">No volunteers yet</p>
                    <p className="text-sm text-gray-400">Be the first to earn points!</p>
                  </div>
                ) : (
                  (page === 0 ? restOfLeaderboard : leaderboard).map((user, index) => {
                    const rank = page === 0 ? index + 4 : page * limit + index + 1;
                    return (
                      <div key={user.user_id} className="px-4 py-2">
                        <LeaderboardCard
                          user={user}
                          rank={rank}
                          isCurrentUser={user.user_id === currentUser?.user_id}
                        />
                      </div>
                    );
                  })
                )}
              </div>

              {/* Pagination */}
              {totalPages > 1 && (
                <div className="px-6 py-4 border-t border-gray-100 flex items-center justify-between">
                  <button
                    onClick={() => setPage(p => Math.max(0, p - 1))}
                    disabled={page === 0}
                    className="flex items-center gap-1 px-3 py-2 text-sm font-medium text-gray-600 hover:text-gray-800 disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    <ChevronLeft className="w-4 h-4" />
                    Previous
                  </button>

                  <span className="text-sm text-gray-500">
                    Page {page + 1} of {totalPages}
                  </span>

                  <button
                    onClick={() => setPage(p => Math.min(totalPages - 1, p + 1))}
                    disabled={page >= totalPages - 1}
                    className="flex items-center gap-1 px-3 py-2 text-sm font-medium text-gray-600 hover:text-gray-800 disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    Next
                    <ChevronRight className="w-4 h-4" />
                  </button>
                </div>
              )}
            </div>

            {/* Badges Info Section */}
            {page === 0 && allBadges.length > 0 && (
              <div className="mt-8 bg-white rounded-xl border border-gray-200 shadow-sm p-6">
                <h3 className="font-semibold text-gray-800 mb-4 flex items-center gap-2">
                  <Award className="w-5 h-5 text-purple-500" />
                  Available Badges
                </h3>

                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
                  {allBadges.map((badge) => {
                    const BadgeIcon = badgeIcons[badge.badge_id] || Award;
                    const colors = badgeColors[badge.badge_id] || { bg: 'bg-gray-100', text: 'text-gray-600' };
                    const userHasBadge = myPoints?.badges?.includes(badge.badge_id);

                    return (
                      <div
                        key={badge.badge_id}
                        className={`p-4 rounded-xl border transition ${
                          userHasBadge
                            ? `${colors.bg} border-current`
                            : 'bg-gray-50 border-gray-100 opacity-60'
                        }`}
                      >
                        <div className="flex items-start gap-3">
                          <div className={`w-10 h-10 rounded-lg ${colors.bg} flex items-center justify-center`}>
                            <BadgeIcon className={`w-5 h-5 ${colors.text}`} />
                          </div>
                          <div className="flex-1">
                            <p className={`font-medium ${userHasBadge ? colors.text : 'text-gray-600'}`}>
                              {badge.name}
                            </p>
                            <p className="text-xs text-gray-500 mt-0.5">
                              {badge.description}
                            </p>
                            {userHasBadge && (
                              <span className="inline-flex items-center gap-1 text-xs text-green-600 mt-1">
                                <Star className="w-3 h-3" fill="currentColor" />
                                Earned
                              </span>
                            )}
                          </div>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            )}

            {/* Call to Action */}
            {page === 0 && !currentUser && (
              <div className="mt-8 bg-gradient-to-r from-[#0d4a6f] to-[#083a57] rounded-xl p-6 text-center text-white">
                <Trophy className="w-12 h-12 mx-auto mb-3 text-yellow-300" />
                <h3 className="text-xl font-semibold mb-2">Join the Movement</h3>
                <p className="text-cyan-100 mb-4">
                  Sign up to track your volunteer activities, earn badges, and climb the leaderboard!
                </p>
                <Link
                  href="/login"
                  className="inline-flex items-center gap-2 px-6 py-3 bg-white text-[#0d4a6f] font-semibold rounded-lg hover:bg-cyan-50 transition"
                >
                  Get Started
                  <TrendingUp className="w-4 h-4" />
                </Link>
              </div>
            )}
          </>
        )}
      </div>
    </DashboardLayout>
  );
}
