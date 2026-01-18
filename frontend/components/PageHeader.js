'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { User, Settings, LogOut, ChevronDown, Waves, Sun, Moon, Sunrise } from 'lucide-react';
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

// Get greeting based on time of day
const getGreeting = () => {
  const hour = new Date().getHours();

  if (hour >= 5 && hour < 12) return "Good Morning";
  if (hour >= 12 && hour < 17) return "Good Afternoon";
  if (hour >= 17 && hour < 21) return "Good Evening";
  return "Good Night"; // covers 21–4
};

// Get icon based on time of day
const getTimeIcon = () => {
  const hour = new Date().getHours();
  if (hour >= 6 && hour < 12) return Sunrise;
  if (hour >= 12 && hour < 18) return Sun;
  return Moon;
};

export default function PageHeader({
  title, // Optional custom title instead of greeting
  subtitle = 'Stay safe and help protect our coast',
  showGreeting = true // Whether to show greeting or custom title
}) {
  const router = useRouter();
  const { user, logout } = useAuthStore();
  const [profileDropdownOpen, setProfileDropdownOpen] = useState(false);
  const [profilePicture, setProfilePicture] = useState(null);
  const [imageError, setImageError] = useState(false);
  const [greeting] = useState(getGreeting());
  const TimeIcon = getTimeIcon();

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

  const displayName = user?.full_name?.split(' ')[0] || user?.name?.split(' ')[0] || 'Guardian';

  return (
    <div className="hidden lg:block relative -mx-3 lg:-mx-6 -mt-3 lg:-mt-6 mb-4 " style={{ zIndex: 9999 }}>
      {/* Main Header Container - Full width, no rounded corners, fixed height */}
      <div className="bg-gradient-to-r from-[#0d4a6f] via-[#1a6b9a] to-[#0d4a6f] px-4 lg:px-6 h-[85px] shadow-md relative sticky fixed">
        {/* Subtle Wave Pattern */}
        <div className="absolute inset-0 opacity-[0.08] pointer-events-none overflow-hidden">
          <svg className="absolute bottom-0 left-0 w-full h-8" viewBox="0 0 1440 120" preserveAspectRatio="none">
            <path fill="white" d="M0,64L48,58.7C96,53,192,43,288,48C384,53,480,75,576,80C672,85,768,75,864,64C960,53,1056,43,1152,48C1248,53,1344,75,1392,85.3L1440,96L1440,120L0,120Z"></path>
          </svg>
        </div>

        <div className="flex items-center justify-between h-full relative" style={{ zIndex: 10000 }}>
          {/* Left: Greeting/Title with Icon */}
          <div className="flex items-center gap-2.5">
            <div className="w-9 h-9 bg-white/15 backdrop-blur-sm rounded-lg flex items-center justify-center flex-shrink-0">
              <TimeIcon className="w-5 h-5 text-white" />
            </div>
            <div>
              {showGreeting ? (
                <>
                  <h1 className="text-2xl font-semibold text-white leading-tight">
                    {greeting}, <span className="text-cyan-200">{displayName}</span>!
                  </h1>
                  <p className="text-white/60 text-[11px] flex items-center gap-1">
                    <Waves className="w-3 h-3" />
                    {subtitle}
                  </p>
                </>
              ) : (
                <>
                  <h1 className="text-xl font-semibold text-white leading-tight">{title}</h1>
                  {subtitle && <p className="text-white/60 text-[11px]">{subtitle}</p>}
                </>
              )}
            </div>
          </div>

          {/* Right: Actions Container */}
          <div className="flex items-center gap-4">
            <GoogleTranslate variant="header" />
            <NotificationBell variant="header" />

            {/* Profile Dropdown */}
            <div className="relative profile-dropdown-container">
              <button
                onClick={() => setProfileDropdownOpen(!profileDropdownOpen)}
                className="flex items-center gap-1.5 px-1.5 py-1 hover:bg-white/10 rounded-md transition-all duration-200"
              >
                {profilePicture && !imageError ? (
                  <img
                    src={getImageUrl(profilePicture)}
                    alt={user?.name}
                    className="w-10 h-10 rounded-lg object-cover ring-2 ring-white/30"
                    onError={() => setImageError(true)}
                  />
                ) : (
                  <div className="w-10 h-10 bg-gradient-to-br from-cyan-400 to-blue-500 rounded-lg flex items-center justify-center ring-2 ring-white/30">
                    <span className="text-white text-xs font-bold">
                      {user?.name?.split(' ').map(n => n[0]).join('').toUpperCase().slice(0, 2) || 'U'}
                    </span>
                  </div>
                )}
                <ChevronDown className={`w-3.5 h-3.5 text-white/60 transition-transform duration-200 ${profileDropdownOpen ? 'rotate-180' : ''}`} />
              </button>

              {profileDropdownOpen && (
                <div className="absolute top-full right-0 mt-2 w-52 bg-white rounded-xl shadow-2xl border border-gray-100 py-1.5" style={{ zIndex: 10001 }}>
                    {/* Profile Info Header */}
                    <div className="px-3 py-2.5 border-b border-gray-100">
                      <div className="flex items-center gap-2.5">
                        {profilePicture && !imageError ? (
                          <img
                            src={getImageUrl(profilePicture)}
                            alt={user?.name}
                            className="w-9 h-9 rounded-lg object-cover"
                          />
                        ) : (
                          <div className="w-9 h-9 bg-gradient-to-br from-[#1a6b9a] to-[#0d4a6f] rounded-lg flex items-center justify-center">
                            <span className="text-white text-sm font-bold">
                              {user?.name?.split(' ').map(n => n[0]).join('').toUpperCase().slice(0, 2) || 'U'}
                            </span>
                          </div>
                        )}
                        <div className="flex-1 min-w-0">
                          <p className="text-sm font-semibold text-gray-900 truncate">{user?.name || user?.full_name}</p>
                          <p className="text-xs text-gray-500 truncate">{user?.email}</p>
                        </div>
                      </div>
                      <span className="inline-flex items-center mt-2 px-2 py-0.5 rounded-full text-[10px] font-medium bg-[#0d4a6f]/10 text-[#0d4a6f] capitalize">
                        {user?.role || 'Citizen'}
                      </span>
                    </div>

                    {/* Menu Items */}
                    <div className="py-1">
                      <button
                        onClick={() => {
                          router.push('/profile');
                          setProfileDropdownOpen(false);
                        }}
                        className="w-full text-left px-3 py-2 text-sm text-gray-700 hover:bg-gray-50 flex items-center gap-2.5 transition-colors"
                      >
                        <div className="w-7 h-7 bg-blue-50 rounded-md flex items-center justify-center">
                          <User className="w-3.5 h-3.5 text-[#0d4a6f]" />
                        </div>
                        <span className="font-medium">Your Profile</span>
                      </button>
                      <button
                        onClick={() => {
                          router.push('/settings');
                          setProfileDropdownOpen(false);
                        }}
                        className="w-full text-left px-3 py-2 text-sm text-gray-700 hover:bg-gray-50 flex items-center gap-2.5 transition-colors"
                      >
                        <div className="w-7 h-7 bg-gray-100 rounded-md flex items-center justify-center">
                          <Settings className="w-3.5 h-3.5 text-gray-600" />
                        </div>
                        <span className="font-medium">Settings</span>
                      </button>
                    </div>

                    {/* Logout */}
                    <div className="border-t border-gray-100 pt-1">
                      <button
                        onClick={handleLogout}
                        className="w-full text-left px-3 py-2 text-sm text-red-600 hover:bg-red-50 flex items-center gap-2.5 transition-colors"
                      >
                        <div className="w-7 h-7 bg-red-50 rounded-md flex items-center justify-center">
                          <LogOut className="w-3.5 h-3.5 text-red-500" />
                        </div>
                        <span className="font-medium">Logout</span>
                      </button>
                    </div>
                  </div>
                )}
              </div>
          </div>
        </div>
      </div>
    </div>
  );
}
