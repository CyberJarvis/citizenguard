'use client';

import { Users, X } from 'lucide-react';
import { useEffect, useState } from 'react';

// Backend URL for images (static files are served from root, not /api/v1)
const getBackendBaseUrl = () => {
  const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';
  // Remove /api/v1 suffix to get the backend root URL
  return apiUrl.replace('/api/v1', '');
};

// Helper to get full image URL
const getImageUrl = (path) => {
  if (!path) return null;
  if (path.startsWith('http')) return path;
  return `${getBackendBaseUrl()}${path}`;
};

// Avatar component with error handling
function Avatar({ src, name, role }) {
  const [imageError, setImageError] = useState(false);

  const getRoleBadgeStyle = (role) => {
    switch (role) {
      case 'ADMIN':
        return 'bg-red-500 text-white';
      case 'ANALYST':
        return 'bg-blue-500 text-white';
      default:
        return 'bg-gray-400 text-white';
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

  if (!src || imageError) {
    return (
      <div className={`w-11 h-11 rounded-full flex items-center justify-center text-white text-sm font-semibold shadow-sm ${getRoleBadgeStyle(role)}`}>
        {getInitials(name)}
      </div>
    );
  }

  return (
    <img
      src={getImageUrl(src)}
      alt={name}
      className="w-11 h-11 rounded-full object-cover shadow-sm"
      onError={() => setImageError(true)}
    />
  );
}

export default function OnlineUsers({ users, isConnected, isOpen, onClose }) {
  // Prevent body scroll when modal is open on mobile
  useEffect(() => {
    if (isOpen) {
      document.body.style.overflow = 'hidden';
    } else {
      document.body.style.overflow = '';
    }
    return () => {
      document.body.style.overflow = '';
    };
  }, [isOpen]);

  const UsersList = () => (
    <>
      {/* Header */}
      <div className="sticky top-0 bg-white border-b border-gray-200 p-4 z-10">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Users className="w-5 h-5 text-gray-600" />
            <div>
              <h3 className="font-semibold text-gray-800">Online Now</h3>
              {!isConnected && (
                <p className="text-xs text-gray-500">Connecting...</p>
              )}
            </div>
          </div>
          <div className="flex items-center gap-3">
            <div className="bg-green-100 text-green-800 text-sm font-semibold px-3 py-1 rounded-full">
              {users.length}
            </div>
            {/* Close button (mobile only) */}
            <button
              onClick={onClose}
              className="lg:hidden w-8 h-8 flex items-center justify-center rounded-full hover:bg-gray-100 transition-colors"
            >
              <X className="w-5 h-5 text-gray-600" />
            </button>
          </div>
        </div>
      </div>

      {/* Users List */}
      <div className="flex-1 overflow-y-auto p-4">
        {users.length === 0 ? (
          <div className="text-center py-12">
            <div className="w-16 h-16 bg-gray-100 rounded-full flex items-center justify-center mx-auto mb-3">
              <Users className="w-8 h-8 text-gray-400" />
            </div>
            <p className="text-sm text-gray-500">No users online</p>
          </div>
        ) : (
          <div className="space-y-1">
            {users.map((user) => (
              <div
                key={user.user_id}
                className="flex items-center gap-3 p-3 rounded-xl hover:bg-gray-50 transition-colors"
              >
                {/* Avatar with online indicator */}
                <div className="relative flex-shrink-0">
                  <Avatar
                    src={user.profile_picture}
                    name={user.user_name}
                    role={user.user_role}
                  />
                  {/* Online indicator */}
                  <div className="absolute bottom-0 right-0 w-3.5 h-3.5 bg-green-500 border-2 border-white rounded-full" />
                </div>

                {/* User info */}
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-gray-900 truncate">
                    {user.user_name}
                  </p>
                  {user.user_role && user.user_role !== 'CITIZEN' && (
                    <span className={`inline-block text-xs px-2 py-0.5 rounded-full mt-1 ${
                      user.user_role === 'ADMIN'
                        ? 'bg-red-100 text-red-700'
                        : 'bg-blue-100 text-blue-700'
                    }`}>
                      {user.user_role}
                    </span>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </>
  );

  return (
    <>
      {/* Mobile: Slide-up modal */}
      {isOpen && (
        <>
          {/* Backdrop */}
          <div
            className="lg:hidden fixed inset-0 bg-black/50 z-40 transition-opacity"
            onClick={onClose}
          />

          {/* Modal */}
          <div className="lg:hidden fixed inset-x-0 bottom-0 bg-white rounded-t-2xl shadow-2xl z-50 flex flex-col max-h-[80vh] animate-slide-up">
            <UsersList />
          </div>
        </>
      )}

      {/* Desktop: Sidebar */}
      <div className="hidden lg:flex lg:w-72 bg-white border-l border-gray-200 flex-col">
        <UsersList />
      </div>

      <style jsx>{`
        @keyframes slide-up {
          from {
            transform: translateY(100%);
          }
          to {
            transform: translateY(0);
          }
        }
        .animate-slide-up {
          animation: slide-up 0.3s ease-out;
        }
      `}</style>
    </>
  );
}
