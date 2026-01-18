'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { User, Settings, LogOut } from 'lucide-react';
import useAuthStore from '@/context/AuthContext';
import { getMyProfile } from '@/lib/api';
import GoogleTranslate from './GoogleTranslate';
import NotificationBell from './NotificationBell';
import toast from 'react-hot-toast';

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

export default function TopIconsBar() {
  const router = useRouter();
  const { user, logout } = useAuthStore();
  const [profileDropdownOpen, setProfileDropdownOpen] = useState(false);
  const [profilePicture, setProfilePicture] = useState(null);
  const [imageError, setImageError] = useState(false);

  useEffect(() => {
    const fetchProfile = async () => {
      try {
        const profile = await getMyProfile();
        setProfilePicture(profile.profile_picture);
        setImageError(false);
      } catch (error) {
        console.error('Error fetching profile:', error);
      }
    };
    if (user) {
      fetchProfile();
    }
  }, [user]);

  const handleLogout = async () => {
    await logout();
    toast.success('Logged out successfully');
    router.push('/login');
  };

  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (e) => {
      if (profileDropdownOpen && !e.target.closest('.profile-dropdown-container')) {
        setProfileDropdownOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, [profileDropdownOpen]);

  return (
    <div className="hidden lg:flex items-center justify-end mb-4">
      <div className="flex items-center gap-1 bg-white rounded-xl px-2 py-1.5 shadow-sm border border-gray-100">
        <GoogleTranslate variant="sidebar" />
        <NotificationBell />
        <div className="relative profile-dropdown-container">
          <button
            onClick={() => setProfileDropdownOpen(!profileDropdownOpen)}
            className="w-9 h-9 flex items-center justify-center hover:bg-gray-100 rounded-lg transition-colors"
          >
            {profilePicture && !imageError ? (
              <img
                src={getImageUrl(profilePicture)}
                alt={user?.name}
                className="w-8 h-8 rounded-lg object-cover ring-2 ring-gray-200"
                onError={() => setImageError(true)}
              />
            ) : (
              <div className="w-8 h-8 bg-gradient-to-br from-[#1a6b9a] to-[#0d4a6f] rounded-lg flex items-center justify-center">
                <span className="text-white text-xs font-bold">
                  {user?.name?.split(' ').map(n => n[0]).join('').toUpperCase().slice(0, 2) || 'U'}
                </span>
              </div>
            )}
          </button>

          {profileDropdownOpen && (
            <div className="absolute top-full right-0 mt-2 w-56 bg-white rounded-xl shadow-xl border border-gray-200 py-2 z-50">
              <div className="px-4 py-3 border-b border-gray-100">
                <p className="text-sm font-semibold text-gray-900">{user?.name}</p>
                <p className="text-xs text-gray-500">{user?.email}</p>
                <p className="text-xs text-[#0d4a6f] font-medium capitalize mt-1">{user?.role || 'Citizen'}</p>
              </div>
              <button
                onClick={() => {
                  router.push('/profile');
                  setProfileDropdownOpen(false);
                }}
                className="w-full text-left px-4 py-2 text-sm text-gray-700 hover:bg-gray-50 flex items-center gap-2"
              >
                <User className="w-4 h-4" />
                Your Profile
              </button>
              <button
                onClick={() => {
                  router.push('/settings');
                  setProfileDropdownOpen(false);
                }}
                className="w-full text-left px-4 py-2 text-sm text-gray-700 hover:bg-gray-50 flex items-center gap-2"
              >
                <Settings className="w-4 h-4" />
                Settings
              </button>
              <div className="border-t border-gray-100 mt-2"></div>
              <button
                onClick={handleLogout}
                className="w-full text-left px-4 py-2 text-sm text-red-600 hover:bg-red-50 flex items-center gap-2"
              >
                <LogOut className="w-4 h-4" />
                Logout
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
