'use client';

import { useState } from 'react';
import Link from 'next/link';
import {
  Users,
  MapPin,
  Calendar,
  CheckCircle,
  UserPlus,
  UserMinus,
  Loader2
} from 'lucide-react';
import { joinCommunity, leaveCommunity } from '@/lib/api';
import toast from 'react-hot-toast';

const categoryColors = {
  cleanup: { bg: 'bg-[#e8f4fc]', text: 'text-[#0d4a6f]', label: 'Beach Cleanup' },
  animal_rescue: { bg: 'bg-green-100', text: 'text-green-700', label: 'Animal Rescue' },
  awareness: { bg: 'bg-purple-100', text: 'text-purple-700', label: 'Awareness' },
  general: { bg: 'bg-gray-100', text: 'text-gray-700', label: 'General' }
};

export default function CommunityCard({
  community,
  isAuthenticated = false,
  onJoinLeave,
  compact = false
}) {
  const [isLoading, setIsLoading] = useState(false);
  const [isMember, setIsMember] = useState(community.is_member);

  const categoryConfig = categoryColors[community.category] || categoryColors.general;

  // Backend base URL for images
  const getImageUrl = (path) => {
    if (!path) return null;
    if (path.startsWith('http')) return path;
    const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';
    return `${apiUrl.replace('/api/v1', '')}${path}`;
  };

  const handleJoinLeave = async (e) => {
    e.preventDefault();
    e.stopPropagation();

    if (!isAuthenticated) {
      toast.error('Please login to join communities');
      return;
    }

    if (community.is_organizer) {
      toast.error('Organizers cannot leave their own community');
      return;
    }

    try {
      setIsLoading(true);

      if (isMember) {
        await leaveCommunity(community.community_id);
        toast.success('Left the community');
        setIsMember(false);
      } else {
        await joinCommunity(community.community_id);
        toast.success('Joined the community!');
        setIsMember(true);
      }

      if (onJoinLeave) {
        onJoinLeave(community.community_id, !isMember);
      }
    } catch (error) {
      console.error('Error:', error);
      toast.error(error.response?.data?.detail || 'Failed to update membership');
    } finally {
      setIsLoading(false);
    }
  };

  if (compact) {
    return (
      <Link href={`/community/${community.community_id}`}>
        <div className="bg-white rounded-lg border border-gray-200 p-4 hover:shadow-md transition cursor-pointer">
          <div className="flex items-center gap-3">
            <div className="w-12 h-12 rounded-lg bg-gradient-to-br from-[#1a6b9a] to-[#0d4a6f] flex items-center justify-center text-white font-semibold text-lg">
              {community.name.charAt(0)}
            </div>
            <div className="flex-1 min-w-0">
              <h3 className="font-medium text-gray-800 truncate">{community.name}</h3>
              <div className="flex items-center gap-2 text-sm text-gray-500">
                <Users className="h-3.5 w-3.5" />
                <span>{community.member_count} members</span>
              </div>
            </div>
            {isMember && (
              <CheckCircle className="h-5 w-5 text-green-500 flex-shrink-0" />
            )}
          </div>
        </div>
      </Link>
    );
  }

  return (
    <Link href={`/community/${community.community_id}`}>
      <div className="bg-white rounded-xl shadow-md overflow-hidden hover:shadow-lg transition cursor-pointer group">
        {/* Cover Image */}
        <div className="h-32 bg-gradient-to-br from-[#1a6b9a] to-[#0d4a6f] relative">
          {community.cover_image_url && (
            <img
              src={getImageUrl(community.cover_image_url)}
              alt={community.name}
              className="w-full h-full object-cover"
            />
          )}
          {/* Category Badge */}
          <div className={`absolute top-3 left-3 px-2 py-1 rounded-full text-xs font-medium ${categoryConfig.bg} ${categoryConfig.text}`}>
            {categoryConfig.label}
          </div>
          {/* Member Badge */}
          {isMember && (
            <div className="absolute top-3 right-3 px-2 py-1 rounded-full text-xs font-medium bg-green-500 text-white flex items-center gap-1">
              <CheckCircle className="h-3 w-3" />
              Member
            </div>
          )}
        </div>

        {/* Content */}
        <div className="p-4">
          {/* Logo & Name */}
          <div className="flex items-start gap-3">
            <div className="w-12 h-12 rounded-lg bg-white border border-gray-200 flex items-center justify-center -mt-8 relative shadow-sm">
              {community.logo_url ? (
                <img
                  src={getImageUrl(community.logo_url)}
                  alt={community.name}
                  className="w-full h-full object-cover rounded-lg"
                />
              ) : (
                <span className="text-xl font-semibold text-[#0d4a6f]">
                  {community.name.charAt(0)}
                </span>
              )}
            </div>
            <div className="flex-1 min-w-0 pt-1">
              <h3 className="font-semibold text-gray-800 truncate group-hover:text-[#0d4a6f] transition">
                {community.name}
              </h3>
              <p className="text-sm text-gray-500">by {community.organizer_name}</p>
            </div>
          </div>

          {/* Description */}
          <p className="text-sm text-gray-600 mt-3 line-clamp-2">
            {community.description}
          </p>

          {/* Stats */}
          <div className="flex items-center gap-4 mt-4 text-sm text-gray-500">
            <div className="flex items-center gap-1">
              <Users className="h-4 w-4" />
              <span>{community.member_count}</span>
            </div>
            <div className="flex items-center gap-1">
              <MapPin className="h-4 w-4" />
              <span>{community.coastal_zone}</span>
            </div>
            <div className="flex items-center gap-1">
              <Calendar className="h-4 w-4" />
              <span>{community.total_events} events</span>
            </div>
          </div>

          {/* Join/Leave Button */}
          {isAuthenticated && !community.is_organizer && (
            <button
              onClick={handleJoinLeave}
              disabled={isLoading}
              className={`w-full mt-4 py-2 rounded-lg font-medium flex items-center justify-center gap-2 transition ${
                isMember
                  ? 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                  : 'bg-[#0d4a6f] text-white hover:bg-[#083a57]'
              } disabled:opacity-50`}
            >
              {isLoading ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : isMember ? (
                <>
                  <UserMinus className="h-4 w-4" />
                  Leave
                </>
              ) : (
                <>
                  <UserPlus className="h-4 w-4" />
                  Join
                </>
              )}
            </button>
          )}
        </div>
      </div>
    </Link>
  );
}
