'use client';

import { useState, useEffect } from 'react';
import { useRouter, usePathname } from 'next/navigation';
import useAuthStore from '@/context/AuthContext';
import {
  Home,
  AlertTriangle,
  Map,
  MessageCircle,
  Shield,
  BarChart3,
  Settings,
  LogOut,
  Menu,
  X,
  Bell,
  FileText,
  Users,
  Activity,
  Plus,
  ShieldCheck,
  Server,
  ClipboardList,
  Database,
  Radio,
  Ticket,
  Trophy,
  ChevronLeft,
  ChevronRight,
  PanelLeftClose,
  PanelLeft,
  Trash2
} from 'lucide-react';
import toast from 'react-hot-toast';
import { getMyProfile } from '@/lib/api';
import NotificationBell from './NotificationBell';
import GoogleTranslate from './GoogleTranslate';
import BottomNav from './ui/BottomNav';
import OfflineIndicator from './OfflineIndicator';
import { startBackgroundSync, stopBackgroundSync } from '@/lib/backgroundSync';

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

export default function DashboardLayout({ children }) {
  const router = useRouter();
  const pathname = usePathname();
  const { user, logout, updateUser } = useAuthStore();
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [profilePicture, setProfilePicture] = useState(null);
  const [imageError, setImageError] = useState(false);

  // Fetch profile and update user data if role is missing
  useEffect(() => {
    const fetchProfileAndUpdateUser = async () => {
      try {
        const profile = await getMyProfile();
        setProfilePicture(profile.profile_picture);
        setImageError(false);

        // If user exists but role is missing, update the user with fresh data
        if (user && !user.role && profile.role) {
          console.log('Updating user with role from profile:', profile.role);
          updateUser({ role: profile.role });
        }
      } catch (error) {
        console.error('Error fetching profile:', error);
      }
    };
    // Only fetch profile if user is authenticated
    if (user) {
      fetchProfileAndUpdateUser();
    }
  }, [pathname, user, updateUser]); // Refetch when navigating to different pages or user changes

  // Normalize user role to lowercase for comparison
  // Default to 'citizen' if user exists but role is missing
  const userRole = user?.role?.toLowerCase() || (user ? 'citizen' : null);

  // Start background sync for citizen and organizer users (PWA feature)
  useEffect(() => {
    const isCitizenOrOrganizer = userRole === 'citizen' || userRole === 'verified_organizer';
    if (isCitizenOrOrganizer) {
      startBackgroundSync();
      return () => stopBackgroundSync();
    }
  }, [userRole]);

  const handleLogout = async () => {
    await logout();
    toast.success('Logged out successfully');
    router.push('/login');
  };

  // Navigation items organized by sections
  const navigationSections = [
    // ============ CITIZEN SECTION ============
    {
      title: null, // No title for citizen (main section)
      roles: ['citizen'],
      items: [
        {
          name: 'Dashboard',
          href: '/dashboard',
          icon: Home,
          description: 'Overview & Stats'
        },
        {
          name: 'Report Hazard',
          href: '/report-hazard',
          icon: AlertTriangle,
          description: 'Submit new report',
          highlight: true
        },
        {
          name: 'My Reports',
          href: '/my-reports',
          icon: FileText,
          description: 'View your reports'
        },
        {
          name: 'My Tickets',
          href: '/my-tickets',
          icon: Ticket,
          description: 'Track your tickets'
        },
        {
          name: 'Map View',
          href: '/map',
          icon: Map,
          description: 'Interactive map'
        },
        {
          name: 'Community',
          href: '/community',
          icon: MessageCircle,
          description: 'Chat & discuss'
        },
        {
          name: 'Leaderboard',
          href: '/leaderboard',
          icon: Trophy,
          description: 'Top volunteers'
        },
        {
          name: 'Safety Tips',
          href: '/safety',
          icon: Shield,
          description: 'Guidelines & tips'
        }
      ]
    },
    // ============ AUTHORITY SECTION ============
    {
      title: null,
      roles: ['authority'],
      items: [
        {
          name: 'Authority Dashboard',
          href: '/authority',
          icon: Shield,
          description: 'Authority overview'
        },
        {
          name: 'Reports & Verification',
          href: '/authority/reports',
          icon: FileText,
          description: 'Verify hazard reports',
          highlight: true
        },
        {
          name: 'Tickets',
          href: '/authority/tickets',
          icon: Ticket,
          description: 'Manage active tickets',
          highlight: true
        },
        {
          name: 'Alert Management',
          href: '/authority/alerts',
          icon: Bell,
          description: 'Manage alerts'
        },
        {
          name: 'Community Chat',
          href: '/community',
          icon: MessageCircle,
          description: 'Chat with citizens'
        },
        {
          name: 'Hazard Map',
          href: '/authority/map',
          icon: Map,
          description: 'Live ocean monitoring'
        },
        {
          name: 'Analytics',
          href: '/authority/analytics',
          icon: BarChart3,
          description: 'View insights'
        }
      ]
    },
    // ============ ANALYST SECTION ============
    {
      title: null,
      roles: ['analyst'],
      items: [
        {
          name: 'Analyst Dashboard',
          href: '/analyst',
          icon: Activity,
          description: 'Analytics overview'
        },
        {
          name: 'Social Intelligence',
          href: '/analyst/social-intelligence',
          icon: Radio,
          description: 'Social media monitoring',
          highlight: true
        },
        {
          name: 'Hazard Map',
          href: '/analyst/map',
          icon: Map,
          description: 'Live ocean monitoring'
        },
        {
          name: 'All Reports',
          href: '/analyst/reports',
          icon: FileText,
          description: 'View & filter reports'
        },
        {
          name: 'Tickets',
          href: '/analyst/tickets',
          icon: Ticket,
          description: 'Manage active tickets',
          highlight: true
        },
        {
          name: 'My Notes',
          href: '/analyst/notes',
          icon: FileText,
          description: 'Personal annotations'
        },
        {
          name: 'Export Center',
          href: '/analyst/exports',
          icon: FileText,
          description: 'Export & reports'
        }
      ]
    },
    // ============ VERIFIED ORGANIZER SECTION ============
    {
      title: null,
      roles: ['verified_organizer'],
      items: [
        {
          name: 'Dashboard',
          href: '/dashboard',
          icon: Home,
          description: 'Overview & Stats'
        },
        {
          name: 'My Communities',
          href: '/community',
          icon: Users,
          description: 'Manage communities',
          highlight: true
        },
        {
          name: 'Create Event',
          href: '/events/create',
          icon: Plus,
          description: 'Organize events',
          highlight: true
        },
        {
          name: 'My Events',
          href: '/events',
          icon: Activity,
          description: 'View your events'
        },
        {
          name: 'Report Hazard',
          href: '/report-hazard',
          icon: AlertTriangle,
          description: 'Submit new report'
        },
        {
          name: 'Map View',
          href: '/map',
          icon: Map,
          description: 'Interactive map'
        },
        {
          name: 'Leaderboard',
          href: '/leaderboard',
          icon: Trophy,
          description: 'Top volunteers'
        },
        {
          name: 'Safety Tips',
          href: '/safety',
          icon: Shield,
          description: 'Guidelines & tips'
        }
      ]
    },
    // ============ ADMIN SECTION (authority_admin only) ============
    {
      title: 'Administration',
      roles: ['authority_admin'],
      items: [
        {
          name: 'Admin Dashboard',
          href: '/admin',
          icon: ShieldCheck,
          description: 'System overview',
          highlight: true
        },
        {
          name: 'User Management',
          href: '/admin/users',
          icon: Users,
          description: 'Manage all users'
        },
        {
          name: 'Content Management',
          href: '/admin/content',
          icon: Trash2,
          description: 'Manage all content',
          highlight: true
        },
        {
          name: 'Content Moderation',
          href: '/admin/reports',
          icon: ClipboardList,
          description: 'Moderate content'
        },
        {
          name: 'System Monitor',
          href: '/admin/monitoring',
          icon: Server,
          description: 'Health & performance'
        },
        {
          name: 'System Settings',
          href: '/admin/settings',
          icon: Settings,
          description: 'Configure system'
        },
        {
          name: 'Audit Logs',
          href: '/admin/audit-logs',
          icon: Database,
          description: 'Activity history'
        }
      ]
    }
  ];

  const isActive = (href) => pathname === href;

  return (
    <div className="min-h-screen bg-slate-50">
      {/* Mobile Sidebar Overlay */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 bg-black/50 backdrop-blur-sm z-40 lg:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      {/* Sidebar */}
      <aside
        className={`fixed top-0 left-0 z-50 h-full bg-white border-r border-gray-200 transform transition-all duration-300 ease-in-out ${sidebarCollapsed ? 'lg:w-20 lg:overflow-visible' : 'lg:w-72'
          } w-72 ${sidebarOpen ? 'translate-x-0' : '-translate-x-full'
          } lg:translate-x-0`}
      >
        {/* Logo Header */}
        {/* <div className={`h-22 flex items-center ${sidebarCollapsed ? 'justify-center px-2' : 'justify-between px-6'} border-b border-gray-200`}>
          <div className={`flex items-center ${sidebarCollapsed ? 'justify-center' : 'gap-2'}`}>
            <img
              src="/logo.png"
              alt="CoastGuardian Logo"
              className={`${sidebarCollapsed ? 'w-15 h-18' : 'w-12 h-12'} object-contain`}
            />
            {!sidebarCollapsed && (
              <div>
                <h1 className="text-xl font-bold text-[#0d4a6f]">CoastGuardian</h1>
                <p className="text-xs text-gray-500">Ocean Safety Platform</p>
              </div>
            )}
          </div>
          <button
            onClick={() => setSidebarOpen(false)}
            className="lg:hidden w-8 h-8 flex items-center justify-center hover:bg-gray-100 rounded-lg"
          >
            <X className="w-5 h-5 text-gray-600" />
          </button>
        </div> */}

        <div className={`flex items-center gap-3 ${sidebarCollapsed ? "justify-center" : "justify-between px-6"} border-b border-gray-200`}>
          <div className="w-22 h-22 flex items-center justify-center overflow-hidden">
            <img
              src="/logo.png"
              alt="CoastGuardian Logo"
              className="w-full h-full object-cover"
            />
          </div>

          {!sidebarCollapsed && (
            <div className="leading-tight">
              <h1 className="text-2xl font-bold text-[#0d4a6f]">CoastGuardian</h1>
              <p className="text-xs text-gray-500">Ocean Safety Platform</p>
            </div>
          )}
        </div>



        {/* Floating Collapse/Expand Button - Desktop Only */}
        <button
          onClick={() => setSidebarCollapsed(!sidebarCollapsed)}
          className="hidden lg:flex absolute top-1/2 -translate-y-1/2 -right-3 w-6 h-6 bg-white border border-gray-200 rounded-full items-center justify-center shadow-sm hover:shadow-md hover:bg-gray-50 transition-all z-10"
          title={sidebarCollapsed ? 'Expand sidebar' : 'Collapse sidebar'}
        >
          {sidebarCollapsed ? (
            <ChevronRight className="w-3.5 h-3.5 text-gray-500" />
          ) : (
            <ChevronLeft className="w-3.5 h-3.5 text-gray-500" />
          )}
        </button>


        {/* User Info */}
        {/* <div className="px-4 py-4 border-b border-gray-200">
          <div className="flex items-center space-x-3 p-3 bg-gradient-to-r from-[#e8f4fc] to-cyan-50 rounded-xl">
            <div className="w-12 h-12 bg-gradient-to-br from-[#1a6b9a] to-[#0d4a6f] rounded-xl flex items-center justify-center flex-shrink-0">
              <User className="w-6 h-6 text-white" />
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-semibold text-gray-900 truncate">
                {user?.name || 'User'}
              </p>
              <p className="text-xs text-gray-600 capitalize">{user?.role || 'Citizen'}</p>
            </div>
            <Activity className="w-4 h-4 text-green-500 flex-shrink-0" />
          </div>
        </div> */}

        {/* Navigation */}
        <nav className={`flex-1 ${sidebarCollapsed ? 'overflow-visible px-2' : 'overflow-y-auto px-4'} py-4 space-y-1`}>
          {navigationSections
            .filter(section => section.roles.includes(userRole) || (!userRole && section.roles.includes('analyst')))
            .map((section, sectionIndex) => (
              <div key={section.title || sectionIndex}>
                {/* Section Header */}
                {section.title && !sidebarCollapsed && (
                  <div className="pt-4 pb-2 px-2 first:pt-0">
                    <div className="flex items-center gap-2">
                      <div className="h-px flex-1 bg-gray-200"></div>
                      <span className="text-xs font-semibold text-gray-400 uppercase tracking-wider">
                        {section.title}
                      </span>
                      <div className="h-px flex-1 bg-gray-200"></div>
                    </div>
                  </div>
                )}

                {/* Section Items */}
                {section.items.map((item) => {
                  const Icon = item.icon;
                  const active = isActive(item.href);
                  const isAdminItem = section.title === 'Administration';

                  return (
                    <div key={item.name} className="relative group/tooltip">
                      <button
                        onClick={() => {
                          router.push(item.href);
                          setSidebarOpen(false);
                        }}
                        className={`w-full flex items-center ${sidebarCollapsed ? 'justify-center px-2' : 'space-x-3 px-4'} py-3 rounded-xl transition-all group mb-1 ${active
                            ? isAdminItem
                              ? 'bg-gradient-to-r from-[#1a6b9a] to-[#0d4a6f] text-white shadow-lg shadow-[#1a6b9a]/30'
                              : 'bg-gradient-to-r from-[#0d4a6f] to-[#083a57] text-white shadow-lg shadow-[#0d4a6f]/20'
                            : item.highlight
                              ? isAdminItem
                                ? 'bg-gradient-to-r from-[#e8f4fc] to-cyan-50 text-[#0d4a6f] hover:from-[#d0e8f5] hover:to-cyan-100'
                                : 'bg-gradient-to-r from-orange-50 to-red-50 text-orange-700 hover:from-orange-100 hover:to-red-100'
                              : isAdminItem
                                ? 'text-gray-700 hover:bg-sky-50'
                                : 'text-slate-700 hover:bg-[#e8f4fc]'
                          }`}
                      >
                        <Icon className={`w-5 h-5 flex-shrink-0 ${active ? 'text-white' : ''}`} />
                        {!sidebarCollapsed && (
                          <div className="flex-1 text-left">
                            <p className={`text-sm font-semibold ${active ? 'text-white' : ''}`}>
                              {item.name}
                            </p>
                            <p
                              className={`text-xs ${active ? 'text-[#c5e1f5]' : 'text-slate-500 group-hover:text-slate-600'
                                }`}
                            >
                              {item.description}
                            </p>
                          </div>
                        )}
                      </button>
                      {/* Tooltip for collapsed sidebar */}
                      {sidebarCollapsed && (
                        <div className="absolute left-full top-1/2 -translate-y-1/2 ml-3 px-3 py-1.5 bg-gray-800 text-white text-sm font-medium rounded-lg whitespace-nowrap opacity-0 invisible group-hover/tooltip:opacity-100 group-hover/tooltip:visible transition-all duration-200 z-[100] shadow-lg pointer-events-none">
                          {item.name}
                          <div className="absolute right-full top-1/2 -translate-y-1/2 border-4 border-transparent border-r-gray-800"></div>
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            ))}
        </nav>

        {/* Bottom Actions - Logout only */}
        <div className={`${sidebarCollapsed ? 'px-2' : 'px-4'} py-4 border-t border-gray-200`}>
          <div className="relative group/logout">
            <button
              onClick={handleLogout}
              className={`w-full flex items-center ${sidebarCollapsed ? 'justify-center px-2' : 'space-x-3 px-4'} py-3 text-red-600 hover:bg-red-50 rounded-xl transition-all`}
            >
              <LogOut className="w-5 h-5" />
              {!sidebarCollapsed && <span className="text-sm font-medium">Logout</span>}
            </button>
            {/* Tooltip for collapsed sidebar */}
            {sidebarCollapsed && (
              <div className="absolute left-full top-1/2 -translate-y-1/2 ml-3 px-3 py-1.5 bg-gray-800 text-white text-sm font-medium rounded-lg whitespace-nowrap opacity-0 invisible group-hover/logout:opacity-100 group-hover/logout:visible transition-all duration-200 z-[100] shadow-lg pointer-events-none">
                Logout
                <div className="absolute right-full top-1/2 -translate-y-1/2 border-4 border-transparent border-r-gray-800"></div>
              </div>
            )}
          </div>
        </div>
      </aside>


      {/* Main Content */}
      <div className={`transition-all duration-300 ${sidebarCollapsed ? 'lg:pl-20' : 'lg:pl-72'}`}>
        {/* Mobile Top Bar Only - Hidden on Desktop */}
        <header className="lg:hidden sticky top-0 z-30 h-14 bg-gradient-to-r from-[#0d4a6f] to-[#1a6b9a] shadow-md">
          <div className="h-full px-4 flex items-center justify-between">
            {/* Left: Mobile Menu + App Name */}
            <div className="flex items-center space-x-3">
              <button
                onClick={() => setSidebarOpen(true)}
                className="w-9 h-9 flex items-center justify-center hover:bg-white/10 rounded-lg transition-colors"
              >
                <Menu className="w-5 h-5 text-white" />
              </button>
              <div className="flex items-center space-x-2">
                {/* <img src="/logo.png" alt="Logo" className="w-7 h-7" /> */}
                <span className="text-white font-semibold text-2xl">CoastGuardian</span>
              </div>
            </div>

            {/* Right: Icons Only - Globe, Bell, Profile */}
            <div className="flex items-center space-x-1">
              <GoogleTranslate variant="header" />
              <NotificationBell variant="header" />
              <button
                onClick={() => setSidebarOpen(true)}
                className="w-9 h-9 flex items-center justify-center hover:bg-white/10 rounded-lg transition-colors"
              >
                {profilePicture && !imageError ? (
                  <img
                    src={getImageUrl(profilePicture)}
                    alt={user?.name}
                    className="w-7 h-7 rounded-lg object-cover ring-2 ring-white/30"
                    onError={() => setImageError(true)}
                  />
                ) : (
                  <div className="w-7 h-7 bg-white/20 rounded-lg flex items-center justify-center ring-2 ring-white/30">
                    <span className="text-white text-xs font-bold">
                      {user?.name?.split(' ').map(n => n[0]).join('').toUpperCase().slice(0, 2) || 'U'}
                    </span>
                  </div>
                )}
              </button>
            </div>
          </div>
        </header>

        {/* Page Content */}
        <main className="min-h-screen lg:min-h-screen pb-24 lg:pb-0 bg-slate-50">
          {children}
        </main>

        {/* Footer - Desktop Only */}
        <footer className="hidden lg:block bg-white border-t border-gray-200 py-6">
          <div className="px-4 lg:px-8">
            <div className="flex flex-col md:flex-row items-center justify-between space-y-2 md:space-y-0">
              <p className="text-sm text-gray-500">
                © 2025 CoastGuardian. All rights reserved.
              </p>
              <div className="flex items-center space-x-6">
                <button className="text-sm text-gray-500 hover:text-gray-700">Privacy</button>
                <button className="text-sm text-gray-500 hover:text-gray-700">Terms</button>
                <button className="text-sm text-gray-500 hover:text-gray-700">Help</button>
              </div>
            </div>
          </div>
        </footer>

        {/* Mobile Bottom Navigation - New FAB Design */}
        <BottomNav />

        {/* Offline Indicator - Only for Citizen and Organizer users (PWA feature) */}
        {(userRole === 'citizen' || userRole === 'verified_organizer') && (
          <OfflineIndicator />
        )}
      </div>
    </div>
  );
}
