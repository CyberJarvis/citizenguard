'use client';

import { Trophy, Award, Medal, Star, Shield, Crown } from 'lucide-react';
import { getBadgeInfo } from '@/lib/api';

const rankColors = {
  1: { bg: 'bg-gradient-to-br from-yellow-400 to-amber-500', border: 'border-yellow-300', text: 'text-yellow-600', shadow: 'shadow-yellow-200' },
  2: { bg: 'bg-gradient-to-br from-gray-300 to-gray-400', border: 'border-gray-200', text: 'text-gray-600', shadow: 'shadow-gray-200' },
  3: { bg: 'bg-gradient-to-br from-amber-600 to-amber-700', border: 'border-amber-400', text: 'text-amber-700', shadow: 'shadow-amber-200' },
};

const rankIcons = {
  1: Crown,
  2: Award,
  3: Medal,
};

const badgeIcons = {
  first_timer: Star,
  active_volunteer: Award,
  ocean_defender: Shield,
  beach_warrior: Trophy,
  super_volunteer: Crown,
  emergency_responder: Shield,
  community_builder: Award,
};

const badgeColors = {
  first_timer: 'text-amber-500',
  active_volunteer: 'text-blue-500',
  ocean_defender: 'text-cyan-500',
  beach_warrior: 'text-yellow-500',
  super_volunteer: 'text-purple-500',
  emergency_responder: 'text-red-500',
  community_builder: 'text-green-500',
};

export default function LeaderboardPodium({ topThree, currentUserId }) {
  if (!topThree || topThree.length === 0) return null;

  // Reorder for podium display: [2nd, 1st, 3rd]
  const podiumOrder = [topThree[1], topThree[0], topThree[2]].filter(Boolean);
  const podiumHeights = ['h-28', 'h-36', 'h-24'];
  const positions = [2, 1, 3];

  return (
    <div className="bg-gradient-to-br from-blue-600 via-blue-700 to-indigo-800 rounded-2xl p-6 mb-8 shadow-xl">
      <h2 className="text-center text-white text-lg font-bold mb-8">Top Volunteers</h2>

      <div className="flex items-end justify-center gap-4 mb-4">
        {podiumOrder.map((user, index) => {
          if (!user) return <div key={index} className="w-24 md:w-32" />;

          const rank = positions[index];
          const colors = rankColors[rank];
          const RankIcon = rankIcons[rank];
          const isCurrentUser = user.user_id === currentUserId;

          return (
            <div key={user.user_id} className="flex flex-col items-center">
              {/* Avatar and Rank Badge */}
              <div className="relative mb-2">
                {/* Crown for 1st place */}
                {rank === 1 && (
                  <div className="absolute -top-6 left-1/2 -translate-x-1/2 animate-bounce">
                    <Crown className="w-8 h-8 text-yellow-400 drop-shadow-lg" />
                  </div>
                )}

                {/* Avatar */}
                <div className={`relative w-16 h-16 md:w-20 md:h-20 rounded-full border-4 ${colors.border} shadow-lg ${colors.shadow} ${isCurrentUser ? 'ring-4 ring-white ring-opacity-50' : ''}`}>
                  {user.profile_picture ? (
                    <img
                      src={user.profile_picture.startsWith('http') ? user.profile_picture : `${process.env.NEXT_PUBLIC_API_URL?.replace('/api/v1', '') || 'http://localhost:8000'}${user.profile_picture}`}
                      alt={user.user_name}
                      className="w-full h-full rounded-full object-cover"
                    />
                  ) : (
                    <div className={`w-full h-full rounded-full ${colors.bg} flex items-center justify-center`}>
                      <span className="text-white text-lg md:text-xl font-bold">
                        {user.user_name?.charAt(0)?.toUpperCase() || '?'}
                      </span>
                    </div>
                  )}

                  {/* Rank Badge */}
                  <div className={`absolute -bottom-2 -right-2 w-7 h-7 md:w-8 md:h-8 ${colors.bg} rounded-full flex items-center justify-center border-2 border-white shadow-md`}>
                    <span className="text-white text-xs md:text-sm font-bold">{rank}</span>
                  </div>
                </div>
              </div>

              {/* User Name */}
              <p className={`text-white text-xs md:text-sm font-semibold text-center truncate w-20 md:w-28 ${isCurrentUser ? 'text-yellow-300' : ''}`}>
                {isCurrentUser ? 'You' : user.user_name?.split(' ')[0] || 'Anonymous'}
              </p>

              {/* Points */}
              <p className="text-blue-200 text-xs font-medium">
                {user.total_points?.toLocaleString()} pts
              </p>

              {/* Badges (show first 3) */}
              <div className="flex gap-1 mt-1">
                {user.badges?.slice(0, 3).map((badge, idx) => {
                  const BadgeIcon = badgeIcons[badge] || Star;
                  const badgeColor = badgeColors[badge] || 'text-gray-400';
                  return (
                    <BadgeIcon
                      key={idx}
                      className={`w-3 h-3 md:w-4 md:h-4 ${badgeColor}`}
                      title={getBadgeInfo(badge)?.name}
                    />
                  );
                })}
              </div>

              {/* Podium Base */}
              <div className={`${podiumHeights[index]} w-20 md:w-28 ${colors.bg} rounded-t-lg mt-3 flex items-start justify-center pt-2 shadow-lg`}>
                <RankIcon className="w-6 h-6 md:w-8 md:h-8 text-white opacity-50" />
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
