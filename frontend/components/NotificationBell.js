'use client';

import { useState, useEffect, useRef } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { Bell, X, AlertCircle, CheckCircle, Info, AlertTriangle, Megaphone, ChevronRight } from 'lucide-react';
import { getNotificationStats, getNotifications, markNotificationRead, markAllNotificationsRead } from '@/lib/api';
import { getRelativeTimeIST } from '@/lib/dateUtils';

export default function NotificationBell({ variant = 'default' }) {
  const router = useRouter();
  const [isOpen, setIsOpen] = useState(false);
  const [unreadCount, setUnreadCount] = useState(0);
  const [notifications, setNotifications] = useState([]);
  const [loading, setLoading] = useState(false);
  const [isMobile, setIsMobile] = useState(false);
  const dropdownRef = useRef(null);

  // Header variant uses white icon styling
  const isHeaderVariant = variant === 'header';

  // Fetch notification stats
  const fetchStats = async () => {
    try {
      const stats = await getNotificationStats();
      setUnreadCount(stats.unread || 0);
    } catch (error) {
      console.error('Error fetching notification stats:', error);
    }
  };

  // Fetch recent notifications
  const fetchNotifications = async () => {
    setLoading(true);
    try {
      const data = await getNotifications({ limit: 5, skip: 0 });
      setNotifications(data || []);
    } catch (error) {
      console.error('Error fetching notifications:', error);
      setNotifications([]);
    } finally {
      setLoading(false);
    }
  };

  // Detect mobile screen size
  useEffect(() => {
    const checkMobile = () => {
      setIsMobile(window.innerWidth < 768);
    };

    checkMobile();
    window.addEventListener('resize', checkMobile);
    return () => window.removeEventListener('resize', checkMobile);
  }, []);

  // Initial load
  useEffect(() => {
    fetchStats();

    // Poll for new notifications every 10 seconds for real-time feel
    const interval = setInterval(fetchStats, 10000);
    return () => clearInterval(interval);
  }, []);

  // Prevent body scroll when mobile panel is open
  useEffect(() => {
    if (isMobile && isOpen) {
      document.body.style.overflow = 'hidden';
    } else {
      document.body.style.overflow = 'unset';
    }
    return () => {
      document.body.style.overflow = 'unset';
    };
  }, [isMobile, isOpen]);

  // Fetch notifications when dropdown opens
  useEffect(() => {
    if (isOpen) {
      fetchNotifications();
    }
  }, [isOpen]);

  // Handle notification click - Navigate to notifications page
  const handleNotificationClick = async (notification) => {
    try {
      // Mark as read
      if (!notification.is_read) {
        await markNotificationRead(notification.notification_id);
        setUnreadCount((prev) => Math.max(0, prev - 1));
      }

      // Close dropdown
      setIsOpen(false);

      // Navigate to full notifications page to see complete details
      router.push('/notifications');
    } catch (error) {
      console.error('Error marking notification as read:', error);
    }
  };

  // Handle mark all as read
  const handleMarkAllRead = async () => {
    try {
      await markAllNotificationsRead();
      setUnreadCount(0);
      setNotifications((prev) =>
        prev.map((n) => ({ ...n, is_read: true }))
      );
    } catch (error) {
      console.error('Error marking all as read:', error);
    }
  };

  // Get severity icon and color
  const getSeverityConfig = (severity) => {
    switch (severity) {
      case 'critical':
        return {
          icon: AlertCircle,
          color: 'text-red-600',
          bg: 'bg-red-50',
          border: 'border-red-200'
        };
      case 'high':
        return {
          icon: AlertTriangle,
          color: 'text-orange-600',
          bg: 'bg-orange-50',
          border: 'border-orange-200'
        };
      case 'medium':
        return {
          icon: Info,
          color: 'text-yellow-600',
          bg: 'bg-yellow-50',
          border: 'border-yellow-200'
        };
      case 'low':
        return {
          icon: CheckCircle,
          color: 'text-blue-600',
          bg: 'bg-blue-50',
          border: 'border-blue-200'
        };
      case 'info':
      default:
        return {
          icon: Megaphone,
          color: 'text-gray-600',
          bg: 'bg-gray-50',
          border: 'border-gray-200'
        };
    }
  };

  return (
    <>
      {/* Bell Button */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        className={`relative transition-colors active:scale-95 ${
          isHeaderVariant
            ? 'w-8 h-8 flex items-center justify-center hover:bg-white/20 rounded-lg'
            : 'w-8 h-8 flex items-center justify-center text-gray-600 hover:text-gray-900 hover:bg-gray-100 rounded-lg'
        }`}
        aria-label="Notifications"
      >
        <Bell className={`${isHeaderVariant ? 'w-[26px] h-[26px] text-white' : 'w-[26px] h-[26px]'}`} />

        {/* Unread Badge */}
        {unreadCount > 0 && (
          <span className={`absolute inline-flex items-center justify-center font-bold leading-none text-white bg-gradient-to-r from-red-500 to-red-600 rounded-full shadow-lg ${
            isHeaderVariant ? '-top-0.5 -right-0.5 px-1 py-0.5 text-[9px] min-w-[16px]' : 'top-0 right-0 w-4 h-4 text-[9px]'
          }`}>
            {unreadCount > 99 ? '99+' : unreadCount}
          </span>
        )}
      </button>

      {/* Mobile Full-Screen Modal */}
      {isOpen && isMobile && (
        <div className="fixed inset-0 z-50 bg-white animate-slide-up">
          {/* Mobile Header */}
          <div className="sticky top-0 bg-gradient-to-br from-sky-600 via-blue-600 to-indigo-600 text-white shadow-xl z-10">
            <div className="flex items-center justify-between px-5 pt-6 pb-4">
              <div className="flex items-center gap-3">
                <div className="p-2.5 bg-white/20 rounded-xl backdrop-blur-sm">
                  <Bell className="w-6 h-6" />
                </div>
                <div>
                  <h2 className="text-xl font-bold tracking-tight">Notifications</h2>
                  {unreadCount > 0 && (
                    <p className="text-sm text-white/80 font-medium">{unreadCount} new</p>
                  )}
                </div>
              </div>
              <button
                onClick={() => setIsOpen(false)}
                className="p-2.5 hover:bg-white/20 rounded-xl transition-all active:scale-90 backdrop-blur-sm"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Mobile Actions Bar */}
            {unreadCount > 0 && (
              <div className="px-5 pb-4">
                <button
                  onClick={handleMarkAllRead}
                  className="w-full py-3 px-4 bg-white/25 hover:bg-white/35 rounded-xl text-sm font-semibold transition-all active:scale-95 backdrop-blur-sm shadow-lg"
                >
                  ✓ Mark all as read
                </button>
              </div>
            )}
          </div>

          {/* Mobile Notifications List */}
          <div className="flex-1 overflow-y-auto bg-gray-50 px-4 py-4">
            {loading ? (
              <div className="flex items-center justify-center py-20">
                <div className="relative">
                  <div className="animate-spin rounded-full h-14 w-14 border-4 border-sky-200"></div>
                  <div className="animate-spin rounded-full h-14 w-14 border-t-4 border-sky-600 absolute top-0"></div>
                </div>
              </div>
            ) : notifications.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-20 text-center">
                <div className="bg-gradient-to-br from-sky-100 via-blue-100 to-indigo-100 rounded-3xl p-8 mb-5 shadow-lg">
                  <Bell className="w-16 h-16 text-sky-600" />
                </div>
                <h3 className="text-xl font-bold text-gray-900 mb-2">All caught up!</h3>
                <p className="text-sm text-gray-500 leading-relaxed">No new notifications right now</p>
              </div>
            ) : (
              <div className="space-y-3">
                {notifications.map((notification) => {
                  const config = getSeverityConfig(notification.severity);
                  const Icon = config.icon;

                  return (
                    <button
                      key={notification.notification_id}
                      onClick={() => handleNotificationClick(notification)}
                      className={`w-full rounded-2xl shadow-sm border-2 transition-all active:scale-98 hover:shadow-md ${
                        !notification.is_read
                          ? 'bg-white border-sky-200 shadow-sky-100/50'
                          : 'bg-white border-gray-100'
                      }`}
                    >
                      <div className="p-5">
                        <div className="flex items-start gap-4">
                          {/* Icon with Badge */}
                          <div className="relative flex-shrink-0">
                            <div className={`p-3.5 rounded-2xl ${config.bg} shadow-sm`}>
                              <Icon className={`w-6 h-6 ${config.color}`} />
                            </div>
                            {!notification.is_read && (
                              <div className="absolute -top-1 -right-1 w-3.5 h-3.5 bg-sky-500 rounded-full border-2 border-white animate-pulse shadow-lg"></div>
                            )}
                          </div>

                          {/* Content */}
                          <div className="flex-1 min-w-0">
                            {/* Title */}
                            <h4 className={`text-base font-bold mb-2 leading-snug ${
                              !notification.is_read ? 'text-gray-900' : 'text-gray-700'
                            }`}>
                              {notification.title}
                            </h4>

                            {/* Description */}
                            <p className="text-sm text-gray-600 mb-3 leading-relaxed line-clamp-2">
                              {notification.message}
                            </p>

                            {/* Meta Info */}
                            <div className="flex flex-wrap items-center gap-2 mb-3">
                              <span className={`inline-flex items-center px-2.5 py-1 rounded-lg text-xs font-bold ${config.bg} ${config.color} shadow-sm`}>
                                {notification.severity?.toUpperCase()}
                              </span>
                              <span className="text-xs text-gray-400 font-medium">
                                {getRelativeTimeIST(notification.created_at)}
                              </span>
                            </div>

                            {/* Location */}
                            {notification.region && (
                              <div className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-gray-50 rounded-lg">
                                <span className="text-sm">📍</span>
                                <span className="text-xs font-semibold text-gray-700">{notification.region}</span>
                              </div>
                            )}
                          </div>

                          {/* Arrow */}
                          <div className="flex-shrink-0 self-center">
                            <div className="p-1.5 bg-gray-50 rounded-lg">
                              <ChevronRight className="w-5 h-5 text-gray-400" />
                            </div>
                          </div>
                        </div>
                      </div>
                    </button>
                  );
                })}
              </div>
            )}
          </div>

          {/* Mobile Footer */}
          {notifications.length > 0 && (
            <div className="sticky bottom-0 bg-white border-t border-gray-200 shadow-2xl px-5 py-4">
              <Link
                href="/notifications"
                onClick={() => setIsOpen(false)}
                className="flex items-center justify-center gap-2 w-full py-4 bg-gradient-to-r from-sky-600 to-blue-600 text-white rounded-xl font-bold text-sm shadow-lg hover:shadow-xl transition-all active:scale-95"
              >
                View All Notifications
                <ChevronRight className="w-4 h-4" />
              </Link>
            </div>
          )}
        </div>
      )}

      {/* Desktop Dropdown */}
      {isOpen && !isMobile && (
        <div className="fixed inset-0" style={{ zIndex: 10000 }} onClick={() => setIsOpen(false)}>
          <div
            ref={dropdownRef}
            onClick={(e) => e.stopPropagation()}
            className="absolute right-4 top-16 w-[400px] bg-white rounded-2xl shadow-2xl border border-gray-200 max-h-[calc(100vh-5rem)] flex flex-col animate-fade-in overflow-hidden"
            style={{ zIndex: 10001 }}
          >
          {/* Header */}
          <div className="bg-gradient-to-br from-sky-600 via-blue-600 to-indigo-600 text-white px-5 py-5">
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-white/20 rounded-xl backdrop-blur-sm">
                  <Bell className="w-5 h-5" />
                </div>
                <div>
                  <h3 className="text-lg font-bold tracking-tight">Notifications</h3>
                  {unreadCount > 0 && (
                    <p className="text-xs text-white/80 font-medium">{unreadCount} new</p>
                  )}
                </div>
              </div>

              <button
                onClick={() => setIsOpen(false)}
                className="p-2 hover:bg-white/20 rounded-xl transition-all backdrop-blur-sm"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            {unreadCount > 0 && (
              <button
                onClick={handleMarkAllRead}
                className="w-full py-2.5 px-4 bg-white/25 hover:bg-white/35 rounded-xl text-sm font-semibold transition-all backdrop-blur-sm"
              >
                ✓ Mark all as read
              </button>
            )}
          </div>

          {/* Notifications List */}
          <div className="flex-1 overflow-y-auto bg-gray-50 p-4">
            {loading ? (
              <div className="flex items-center justify-center py-12">
                <div className="relative">
                  <div className="animate-spin rounded-full h-10 w-10 border-4 border-sky-200"></div>
                  <div className="animate-spin rounded-full h-10 w-10 border-t-4 border-sky-600 absolute top-0"></div>
                </div>
              </div>
            ) : notifications.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-12 text-center">
                <div className="bg-gradient-to-br from-sky-100 via-blue-100 to-indigo-100 rounded-3xl p-6 mb-4 shadow-lg">
                  <Bell className="w-12 h-12 text-sky-600" />
                </div>
                <p className="text-base font-bold text-gray-800 mb-1">All caught up!</p>
                <p className="text-xs text-gray-500">No new notifications</p>
              </div>
            ) : (
              <div className="space-y-2.5">
                {notifications.map((notification) => {
                  const config = getSeverityConfig(notification.severity);
                  const Icon = config.icon;

                  return (
                    <button
                      key={notification.notification_id}
                      onClick={() => handleNotificationClick(notification)}
                      className={`w-full rounded-xl shadow-sm border-2 transition-all hover:shadow-md ${
                        !notification.is_read
                          ? 'bg-white border-sky-200 shadow-sky-100/50'
                          : 'bg-white border-gray-100'
                      }`}
                    >
                      <div className="p-4">
                        <div className="flex items-start gap-3.5">
                          {/* Icon */}
                          <div className="relative flex-shrink-0">
                            <div className={`p-3 rounded-xl ${config.bg} shadow-sm`}>
                              <Icon className={`w-5 h-5 ${config.color}`} />
                            </div>
                            {!notification.is_read && (
                              <div className="absolute -top-1 -right-1 w-3 h-3 bg-sky-500 rounded-full border-2 border-white animate-pulse"></div>
                            )}
                          </div>

                          {/* Content */}
                          <div className="flex-1 min-w-0">
                            <h4 className={`text-sm font-bold mb-1.5 leading-snug ${
                              !notification.is_read ? 'text-gray-900' : 'text-gray-700'
                            }`}>
                              {notification.title}
                            </h4>

                            <p className="text-xs text-gray-600 mb-2.5 leading-relaxed line-clamp-2">
                              {notification.message}
                            </p>

                            <div className="flex flex-wrap items-center gap-2">
                              <span className={`px-2 py-0.5 rounded-md text-xs font-bold ${config.bg} ${config.color}`}>
                                {notification.severity?.toUpperCase()}
                              </span>
                              <span className="text-xs text-gray-400 font-medium">
                                {getRelativeTimeIST(notification.created_at)}
                              </span>
                            </div>

                            {notification.region && (
                              <div className="inline-flex items-center gap-1.5 px-2.5 py-1 bg-gray-50 rounded-lg mt-2">
                                <span className="text-xs">📍</span>
                                <span className="text-xs font-semibold text-gray-700">{notification.region}</span>
                              </div>
                            )}
                          </div>
                        </div>
                      </div>
                    </button>
                  );
                })}
              </div>
            )}
          </div>

          {/* Footer */}
          {notifications.length > 0 && (
            <div className="border-t border-gray-200 bg-white px-4 py-3">
              <Link
                href="/notifications"
                onClick={() => setIsOpen(false)}
                className="flex items-center justify-center gap-2 w-full py-3 bg-gradient-to-r from-sky-600 to-blue-600 text-white rounded-xl font-bold text-sm shadow-lg hover:shadow-xl transition-all"
              >
                View All Notifications
                <ChevronRight className="w-4 h-4" />
              </Link>
            </div>
          )}
          </div>
        </div>
      )}
    </>
  );
}
