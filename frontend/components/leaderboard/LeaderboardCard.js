'use client';

import { Star, Award, Shield, Trophy, Crown, AlertTriangle, Users, Calendar } from 'lucide-react';
import { getBadgeInfo } from '@/lib/api';

const badgeIcons = {
  first_timer: Star,
  active_volunteer: Award,
  ocean_defender: Shield,
  beach_warrior: Trophy,
  super_volunteer: Crown,
  emergency_responder: AlertTriangle,
  community_builder: Users,
};

const badgeColors = {
  first_timer: { bg: 'bg-amber-100', text: 'text-amber-600', border: 'border-amber-200' },
  active_volunteer: { bg: 'bg-blue-100', text: 'text-blue-600', border: 'border-blue-200' },
  ocean_defender: { bg: 'bg-cyan-100', text: 'text-cyan-600', border: 'border-cyan-200' },
  beach_warrior: { bg: 'bg-yellow-100', text: 'text-yellow-600', border: 'border-yellow-200' },
  super_volunteer: { bg: 'bg-purple-100', text: 'text-purple-600', border: 'border-purple-200' },
  emergency_responder: { bg: 'bg-red-100', text: 'text-red-600', border: 'border-red-200' },
  community_builder: { bg: 'bg-green-100', text: 'text-green-600', border: 'border-green-200' },
};

const rankStyles = {
  1: { bg: 'bg-gradient-to-r from-yellow-50 to-amber-50', border: 'border-yellow-200', text: 'text-yellow-600' },
  2: { bg: 'bg-gradient-to-r from-gray-50 to-slate-50', border: 'border-gray-200', text: 'text-gray-600' },
  3: { bg: 'bg-gradient-to-r from-amber-50 to-orange-50', border: 'border-amber-200', text: 'text-amber-700' },
};

export default function LeaderboardCard({ user, rank, isCurrentUser = false }) {
  const rankStyle = rankStyles[rank] || { bg: 'bg-white', border: 'border-gray-100', text: 'text-gray-700' };

  return (
    <div
      className={`flex items-center gap-4 p-4 rounded-xl border transition-all hover:shadow-md ${
        isCurrentUser
          ? 'bg-gradient-to-r from-blue-50 to-indigo-50 border-blue-200 ring-2 ring-blue-100'
          : `${rankStyle.bg} ${rankStyle.border}`
      }`}
    >
      {/* Rank */}
      <div className={`w-10 h-10 rounded-full flex items-center justify-center font-bold text-lg ${
        rank <= 3
          ? `${rankStyle.bg} ${rankStyle.text} border-2 ${rankStyle.border}`
          : 'bg-gray-100 text-gray-600'
      }`}>
        {rank}
      </div>

      {/* Avatar */}
      <div className="relative">
        {user.profile_picture ? (
          <img
            src={user.profile_picture.startsWith('http') ? user.profile_picture : `${process.env.NEXT_PUBLIC_API_URL?.replace('/api/v1', '') || 'http://localhost:8000'}${user.profile_picture}`}
            alt={user.user_name}
            className="w-12 h-12 rounded-full object-cover border-2 border-white shadow"
          />
        ) : (
          <div className="w-12 h-12 rounded-full bg-gradient-to-br from-blue-500 to-indigo-600 flex items-center justify-center border-2 border-white shadow">
            <span className="text-white text-lg font-bold">
              {user.user_name?.charAt(0)?.toUpperCase() || '?'}
            </span>
          </div>
        )}
        {isCurrentUser && (
          <div className="absolute -bottom-1 -right-1 w-5 h-5 bg-blue-500 rounded-full flex items-center justify-center border-2 border-white">
            <span className="text-white text-[8px] font-bold">YOU</span>
          </div>
        )}
      </div>

      {/* User Info */}
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <p className={`font-semibold truncate ${isCurrentUser ? 'text-blue-700' : 'text-gray-800'}`}>
            {isCurrentUser ? 'You' : user.user_name || 'Anonymous'}
          </p>
          {rank <= 3 && (
            <span className={`text-xs px-2 py-0.5 rounded-full ${rankStyle.bg} ${rankStyle.text} font-medium`}>
              {rank === 1 ? 'Champion' : rank === 2 ? 'Runner-up' : 'Bronze'}
            </span>
          )}
        </div>

        {/* Badges */}
        <div className="flex flex-wrap gap-1 mt-1">
          {user.badges?.slice(0, 5).map((badge, idx) => {
            const BadgeIcon = badgeIcons[badge] || Star;
            const colors = badgeColors[badge] || { bg: 'bg-gray-100', text: 'text-gray-500', border: 'border-gray-200' };
            const badgeInfo = getBadgeInfo(badge);

            return (
              <div
                key={idx}
                className={`flex items-center gap-1 px-1.5 py-0.5 rounded-full ${colors.bg} ${colors.text} border ${colors.border}`}
                title={badgeInfo?.description}
              >
                <BadgeIcon className="w-3 h-3" />
                <span className="text-[10px] font-medium hidden sm:inline">{badgeInfo?.name}</span>
              </div>
            );
          })}
          {user.badges?.length > 5 && (
            <span className="text-xs text-gray-500 px-1">+{user.badges.length - 5}</span>
          )}
        </div>
      </div>

      {/* Stats */}
      <div className="flex items-center gap-4 text-right">
        {/* Events Attended */}
        <div className="hidden sm:block">
          <div className="flex items-center gap-1 text-gray-500">
            <Calendar className="w-4 h-4" />
            <span className="text-sm font-medium">{user.events_attended || 0}</span>
          </div>
          <p className="text-xs text-gray-400">events</p>
        </div>

        {/* Points */}
        <div>
          <p className={`text-xl font-bold ${isCurrentUser ? 'text-blue-600' : rank <= 3 ? rankStyle.text : 'text-gray-800'}`}>
            {user.total_points?.toLocaleString() || 0}
          </p>
          <p className="text-xs text-gray-400">points</p>
        </div>
      </div>
    </div>
  );
}
