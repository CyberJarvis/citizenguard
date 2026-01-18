'use client';

import { useState } from 'react';
import Link from 'next/link';
import {
  Heart,
  MessageCircle,
  Pin,
  MoreHorizontal,
  Trash2,
  Edit,
  EyeOff,
  Eye,
  Calendar,
  Image as ImageIcon,
  Megaphone,
  FileText
} from 'lucide-react';
import { togglePostLike, togglePostPin, togglePostVisibility, deletePost } from '@/lib/api';
import toast from 'react-hot-toast';

const postTypeConfig = {
  general: {
    label: 'Post',
    icon: FileText,
    bg: 'bg-gray-100',
    text: 'text-gray-600'
  },
  announcement: {
    label: 'Announcement',
    icon: Megaphone,
    bg: 'bg-blue-100',
    text: 'text-blue-600'
  },
  event_recap: {
    label: 'Event Recap',
    icon: Calendar,
    bg: 'bg-green-100',
    text: 'text-green-600'
  }
};

export default function CommunityPostCard({
  post,
  communityId,
  currentUserId,
  isOrganizer = false,
  onUpdate,
  onDelete
}) {
  const [isLiked, setIsLiked] = useState(post.is_liked || false);
  const [likesCount, setLikesCount] = useState(post.likes_count || 0);
  const [isPinned, setIsPinned] = useState(post.is_pinned || false);
  const [isHidden, setIsHidden] = useState(post.is_hidden || false);
  const [showMenu, setShowMenu] = useState(false);
  const [showFullContent, setShowFullContent] = useState(false);
  const [selectedImageIndex, setSelectedImageIndex] = useState(null);

  const typeConfig = postTypeConfig[post.post_type] || postTypeConfig.general;
  const TypeIcon = typeConfig.icon;

  const getBackendBaseUrl = () => {
    const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';
    return apiUrl.replace('/api/v1', '');
  };

  const getImageUrl = (path) => {
    if (!path) return null;
    if (path.startsWith('http')) return path;
    return `${getBackendBaseUrl()}${path}`;
  };

  const formatDate = (dateStr) => {
    if (!dateStr) return '';
    const date = new Date(dateStr);
    const now = new Date();
    const diffMs = now - date;
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);

    if (diffMins < 60) {
      return `${diffMins}m ago`;
    } else if (diffHours < 24) {
      return `${diffHours}h ago`;
    } else if (diffDays < 7) {
      return `${diffDays}d ago`;
    } else {
      return date.toLocaleDateString('en-IN', {
        day: 'numeric',
        month: 'short'
      });
    }
  };

  const handleLike = async () => {
    try {
      const response = await togglePostLike(communityId, post.post_id);
      if (response.success) {
        setIsLiked(response.is_liked);
        setLikesCount(response.likes_count);
      }
    } catch (error) {
      console.error('Error liking post:', error);
      toast.error('Failed to like post');
    }
  };

  const handlePin = async () => {
    try {
      const response = await togglePostPin(communityId, post.post_id, !isPinned);
      if (response.success) {
        setIsPinned(!isPinned);
        toast.success(isPinned ? 'Post unpinned' : 'Post pinned');
        if (onUpdate) onUpdate();
      }
    } catch (error) {
      console.error('Error pinning post:', error);
      toast.error('Failed to pin post');
    }
    setShowMenu(false);
  };

  const handleToggleVisibility = async () => {
    try {
      const response = await togglePostVisibility(communityId, post.post_id, !isHidden);
      if (response.success) {
        setIsHidden(!isHidden);
        toast.success(isHidden ? 'Post is now visible' : 'Post hidden');
        if (onUpdate) onUpdate();
      }
    } catch (error) {
      console.error('Error toggling visibility:', error);
      toast.error('Failed to update post');
    }
    setShowMenu(false);
  };

  const handleDelete = async () => {
    if (!confirm('Are you sure you want to delete this post?')) return;

    try {
      const response = await deletePost(communityId, post.post_id);
      if (response.success) {
        toast.success('Post deleted');
        if (onDelete) onDelete(post.post_id);
      }
    } catch (error) {
      console.error('Error deleting post:', error);
      toast.error('Failed to delete post');
    }
    setShowMenu(false);
  };

  const isAuthor = post.author_id === currentUserId;
  const canManage = isAuthor || isOrganizer;
  const contentTruncated = post.content.length > 300;

  return (
    <div className={`bg-white rounded-2xl shadow-sm border ${isHidden ? 'border-red-200 opacity-70' : isPinned ? 'border-amber-200' : 'border-gray-200'} overflow-hidden`}>
      {/* Pinned/Hidden Badge */}
      {(isPinned || isHidden) && (
        <div className={`px-4 py-2 ${isPinned ? 'bg-amber-50' : 'bg-red-50'} flex items-center gap-2`}>
          {isPinned && (
            <>
              <Pin className="w-4 h-4 text-amber-600" />
              <span className="text-sm font-medium text-amber-700">Pinned Post</span>
            </>
          )}
          {isHidden && (
            <>
              <EyeOff className="w-4 h-4 text-red-600" />
              <span className="text-sm font-medium text-red-700">Hidden</span>
            </>
          )}
        </div>
      )}

      <div className="p-4">
        {/* Header */}
        <div className="flex items-start justify-between mb-3">
          <div className="flex items-center gap-3">
            {/* Avatar */}
            {post.author_picture ? (
              <img
                src={getImageUrl(post.author_picture)}
                alt={post.author_name}
                className="w-10 h-10 rounded-full object-cover"
              />
            ) : (
              <div className="w-10 h-10 bg-gradient-to-br from-blue-500 to-cyan-500 rounded-full flex items-center justify-center">
                <span className="text-white font-bold text-sm">
                  {post.author_name?.charAt(0)?.toUpperCase() || '?'}
                </span>
              </div>
            )}

            <div>
              <p className="font-semibold text-gray-900">{post.author_name}</p>
              <div className="flex items-center gap-2 text-xs text-gray-500">
                <span>{formatDate(post.created_at)}</span>
                <span className={`px-2 py-0.5 rounded-full ${typeConfig.bg} ${typeConfig.text} flex items-center gap-1`}>
                  <TypeIcon className="w-3 h-3" />
                  {typeConfig.label}
                </span>
              </div>
            </div>
          </div>

          {/* Menu */}
          {canManage && (
            <div className="relative">
              <button
                onClick={() => setShowMenu(!showMenu)}
                className="w-8 h-8 rounded-full hover:bg-gray-100 flex items-center justify-center transition"
              >
                <MoreHorizontal className="w-5 h-5 text-gray-500" />
              </button>

              {showMenu && (
                <>
                  <div
                    className="fixed inset-0 z-10"
                    onClick={() => setShowMenu(false)}
                  />
                  <div className="absolute right-0 top-full mt-1 bg-white rounded-xl shadow-lg border border-gray-200 py-1 z-20 min-w-[160px]">
                    {isOrganizer && (
                      <>
                        <button
                          onClick={handlePin}
                          className="w-full px-4 py-2 text-left text-sm text-gray-700 hover:bg-gray-50 flex items-center gap-2"
                        >
                          <Pin className="w-4 h-4" />
                          {isPinned ? 'Unpin Post' : 'Pin Post'}
                        </button>
                        <button
                          onClick={handleToggleVisibility}
                          className="w-full px-4 py-2 text-left text-sm text-gray-700 hover:bg-gray-50 flex items-center gap-2"
                        >
                          {isHidden ? (
                            <>
                              <Eye className="w-4 h-4" />
                              Show Post
                            </>
                          ) : (
                            <>
                              <EyeOff className="w-4 h-4" />
                              Hide Post
                            </>
                          )}
                        </button>
                      </>
                    )}
                    <button
                      onClick={handleDelete}
                      className="w-full px-4 py-2 text-left text-sm text-red-600 hover:bg-red-50 flex items-center gap-2"
                    >
                      <Trash2 className="w-4 h-4" />
                      Delete Post
                    </button>
                  </div>
                </>
              )}
            </div>
          )}
        </div>

        {/* Related Event */}
        {post.related_event && (
          <Link
            href={`/events/${post.related_event.event_id}`}
            className="flex items-center gap-2 mb-3 px-3 py-2 bg-green-50 rounded-lg hover:bg-green-100 transition"
          >
            <Calendar className="w-4 h-4 text-green-600" />
            <span className="text-sm font-medium text-green-700">{post.related_event.title}</span>
          </Link>
        )}

        {/* Content */}
        <div className="mb-3">
          <p className="text-gray-800 whitespace-pre-wrap">
            {contentTruncated && !showFullContent
              ? `${post.content.slice(0, 300)}...`
              : post.content}
          </p>
          {contentTruncated && (
            <button
              onClick={() => setShowFullContent(!showFullContent)}
              className="text-blue-600 text-sm font-medium mt-1 hover:text-blue-700"
            >
              {showFullContent ? 'Show less' : 'Read more'}
            </button>
          )}
        </div>

        {/* Photos */}
        {post.photos && post.photos.length > 0 && (
          <div className={`mb-3 grid gap-2 ${
            post.photos.length === 1 ? 'grid-cols-1' :
            post.photos.length === 2 ? 'grid-cols-2' :
            'grid-cols-2'
          }`}>
            {post.photos.slice(0, 4).map((photo, index) => (
              <div
                key={index}
                className={`relative rounded-xl overflow-hidden cursor-pointer ${
                  post.photos.length === 3 && index === 0 ? 'row-span-2' : ''
                }`}
                onClick={() => setSelectedImageIndex(index)}
              >
                <img
                  src={getImageUrl(photo)}
                  alt={`Post photo ${index + 1}`}
                  className={`w-full object-cover ${
                    post.photos.length === 1 ? 'max-h-96' : 'aspect-square'
                  }`}
                />
                {index === 3 && post.photos.length > 4 && (
                  <div className="absolute inset-0 bg-black/50 flex items-center justify-center">
                    <span className="text-white text-2xl font-bold">+{post.photos.length - 4}</span>
                  </div>
                )}
              </div>
            ))}
          </div>
        )}

        {/* Actions */}
        <div className="flex items-center gap-4 pt-3 border-t border-gray-100">
          <button
            onClick={handleLike}
            className={`flex items-center gap-2 px-3 py-1.5 rounded-lg transition ${
              isLiked
                ? 'bg-red-50 text-red-600'
                : 'hover:bg-gray-100 text-gray-600'
            }`}
          >
            <Heart className={`w-5 h-5 ${isLiked ? 'fill-current' : ''}`} />
            <span className="text-sm font-medium">{likesCount}</span>
          </button>
        </div>
      </div>

      {/* Image Lightbox */}
      {selectedImageIndex !== null && (
        <div
          className="fixed inset-0 bg-black/90 flex items-center justify-center z-50 p-4"
          onClick={() => setSelectedImageIndex(null)}
        >
          <img
            src={getImageUrl(post.photos[selectedImageIndex])}
            alt="Full size"
            className="max-w-full max-h-full object-contain rounded-lg"
            onClick={(e) => e.stopPropagation()}
          />
        </div>
      )}
    </div>
  );
}
