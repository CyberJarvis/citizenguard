'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import DashboardLayout from '@/components/DashboardLayout';
import {
  Bell,
  Filter,
  CheckCircle2,
  Trash2,
  AlertCircle,
  AlertTriangle,
  Info,
  Megaphone,
  X,
  Check
} from 'lucide-react';
import {
  getNotifications,
  getNotificationStats,
  markNotificationRead,
  markAllNotificationsRead,
  dismissNotification,
  clearReadNotifications
} from '@/lib/api';
import { getRelativeTimeIST } from '@/lib/dateUtils';
import toast, { Toaster } from 'react-hot-toast';

export default function NotificationsPage() {
  const router = useRouter();
  const [notifications, setNotifications] = useState([]);
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [activeFilter, setActiveFilter] = useState('all'); // all, unread, alert, system
  const [activeSeverity, setActiveSeverity] = useState('all'); // all, critical, high, medium, low, info

  // Fetch notifications
  const fetchNotifications = async () => {
    setLoading(true);
    try {
      const params = {};

      // Apply filters
      if (activeFilter !== 'all') {
        if (activeFilter === 'unread') {
          params.unread_only = true;
        } else {
          params.type_filter = activeFilter;
        }
      }

      if (activeSeverity !== 'all') {
        params.severity_filter = activeSeverity;
      }

      params.limit = 50;

      const data = await getNotifications(params);
      setNotifications(data || []);
    } catch (error) {
      console.error('Error fetching notifications:', error);
      setNotifications([]);
      toast.error('Failed to load notifications');
    } finally {
      setLoading(false);
    }
  };

  // Fetch stats
  const fetchStats = async () => {
    try {
      const statsData = await getNotificationStats();
      setStats(statsData);
    } catch (error) {
      console.error('Error fetching stats:', error);
    }
  };

  // Initial load
  useEffect(() => {
    fetchNotifications();
    fetchStats();
  }, [activeFilter, activeSeverity]);

  // Handle mark as read (removed navigation)
  const handleMarkAsRead = async (notification) => {
    try {
      // Mark as read
      if (!notification.is_read) {
        await markNotificationRead(notification.notification_id);

        // Update local state
        setNotifications((prev) =>
          prev.map((n) =>
            n.notification_id === notification.notification_id
              ? { ...n, is_read: true }
              : n
          )
        );

        setStats((prev) => ({
          ...prev,
          unread: Math.max(0, prev.unread - 1)
        }));

        toast.success('Marked as read');
      }
    } catch (error) {
      console.error('Error marking notification as read:', error);
      toast.error('Failed to update notification');
    }
  };

  // Handle mark all as read
  const handleMarkAllRead = async () => {
    try {
      await markAllNotificationsRead();

      // Update local state
      setNotifications((prev) => prev.map((n) => ({ ...n, is_read: true })));
      setStats((prev) => ({ ...prev, unread: 0 }));

      toast.success('All notifications marked as read');
    } catch (error) {
      console.error('Error marking all as read:', error);
      toast.error('Failed to mark all as read');
    }
  };

  // Handle dismiss notification
  const handleDismiss = async (notificationId, event) => {
    event.stopPropagation();

    try {
      await dismissNotification(notificationId);

      // Remove from local state
      setNotifications((prev) =>
        prev.filter((n) => n.notification_id !== notificationId)
      );

      toast.success('Notification dismissed');
    } catch (error) {
      console.error('Error dismissing notification:', error);
      toast.error('Failed to dismiss notification');
    }
  };

  // Handle clear read
  const handleClearRead = async () => {
    try {
      const result = await clearReadNotifications();

      // Remove read notifications from state
      setNotifications((prev) => prev.filter((n) => !n.is_read));

      toast.success(`Cleared ${result.count} read notifications`);
    } catch (error) {
      console.error('Error clearing notifications:', error);
      toast.error('Failed to clear notifications');
    }
  };

  // Get severity config
  const getSeverityConfig = (severity) => {
    switch (severity) {
      case 'critical':
        return {
          icon: AlertCircle,
          color: 'text-red-600',
          bg: 'bg-red-50',
          border: 'border-red-200',
          label: 'Critical'
        };
      case 'high':
        return {
          icon: AlertTriangle,
          color: 'text-orange-600',
          bg: 'bg-orange-50',
          border: 'border-orange-200',
          label: 'High'
        };
      case 'medium':
        return {
          icon: Info,
          color: 'text-yellow-600',
          bg: 'bg-yellow-50',
          border: 'border-yellow-200',
          label: 'Medium'
        };
      case 'low':
        return {
          icon: CheckCircle2,
          color: 'text-blue-600',
          bg: 'bg-blue-50',
          border: 'border-blue-200',
          label: 'Low'
        };
      case 'info':
      default:
        return {
          icon: Megaphone,
          color: 'text-gray-600',
          bg: 'bg-gray-50',
          border: 'border-gray-200',
          label: 'Info'
        };
    }
  };

  const filterOptions = [
    { value: 'all', label: 'All' },
    { value: 'unread', label: 'Unread' },
    { value: 'alert', label: 'Alerts' },
    { value: 'report_update', label: 'Report Updates' },
    { value: 'system', label: 'System' }
  ];

  const severityOptions = [
    { value: 'all', label: 'All Severity' },
    { value: 'critical', label: 'Critical' },
    { value: 'high', label: 'High' },
    { value: 'medium', label: 'Medium' },
    { value: 'low', label: 'Low' },
    { value: 'info', label: 'Info' }
  ];

  return (
    <DashboardLayout>
      <Toaster position="top-center" />

      <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
        {/* Header */}
        <div className="mb-8">
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-6">
            <div>
              <h1 className="text-2xl sm:text-3xl font-bold text-gray-900 flex items-center gap-3 mb-2">
                <div className="p-2 bg-gradient-to-br from-sky-500 to-blue-600 rounded-xl">
                  <Bell className="w-6 h-6 sm:w-7 sm:h-7 text-white" />
                </div>
                Notifications
              </h1>
              {stats && (
                <p className="text-sm text-gray-600 ml-1">
                  <span className="font-semibold text-gray-900">{stats.total}</span> total
                  {stats.unread > 0 && (
                    <>
                      {' • '}
                      <span className="font-semibold text-sky-600">{stats.unread}</span> unread
                    </>
                  )}
                </p>
              )}
            </div>

            <div className="flex items-center gap-2">
              {stats && stats.unread > 0 && (
                <button
                  onClick={handleMarkAllRead}
                  className="flex items-center gap-2 px-3 sm:px-4 py-2 text-sm font-medium text-white bg-gradient-to-r from-sky-600 to-blue-600 hover:from-sky-700 hover:to-blue-700 rounded-xl transition-all shadow-sm hover:shadow-md"
                >
                  <CheckCircle2 className="w-4 h-4" />
                  <span className="hidden sm:inline">Mark All Read</span>
                  <span className="sm:hidden">Mark All</span>
                </button>
              )}

              <button
                onClick={handleClearRead}
                className="flex items-center gap-2 px-3 sm:px-4 py-2 text-sm font-medium text-red-600 hover:text-red-700 bg-white hover:bg-red-50 border border-red-200 hover:border-red-300 rounded-xl transition-all shadow-sm"
              >
                <Trash2 className="w-4 h-4" />
                <span className="hidden sm:inline">Clear Read</span>
                <span className="sm:hidden">Clear</span>
              </button>
            </div>
          </div>

          {/* Filters */}
          <div className="bg-white rounded-2xl shadow-sm border border-gray-200 p-4">
            {/* Type Filter */}
            <div className="mb-3 sm:mb-4">
              <div className="flex items-center gap-2 mb-3">
                <Filter className="w-4 h-4 text-gray-400" />
                <span className="text-xs font-semibold text-gray-500 uppercase tracking-wide">Filter by Type</span>
              </div>
              <div className="flex items-center gap-2 flex-wrap">
                {filterOptions.map((option) => (
                  <button
                    key={option.value}
                    onClick={() => setActiveFilter(option.value)}
                    className={`px-3 sm:px-4 py-1.5 sm:py-2 text-xs sm:text-sm font-medium rounded-xl transition-all ${
                      activeFilter === option.value
                        ? 'bg-gradient-to-r from-sky-600 to-blue-600 text-white shadow-md scale-105'
                        : 'bg-gray-100 text-gray-700 hover:bg-gray-200 hover:scale-105'
                    }`}
                  >
                    {option.label}
                  </button>
                ))}
              </div>
            </div>

            {/* Severity Filter */}
            <div className="pt-3 sm:pt-4 border-t border-gray-100">
              <div className="flex items-center gap-2 mb-3">
                <AlertCircle className="w-4 h-4 text-gray-400" />
                <span className="text-xs font-semibold text-gray-500 uppercase tracking-wide">Filter by Severity</span>
              </div>
              <div className="flex items-center gap-2 flex-wrap">
                {severityOptions.map((option) => (
                  <button
                    key={option.value}
                    onClick={() => setActiveSeverity(option.value)}
                    className={`px-3 sm:px-4 py-1.5 sm:py-2 text-xs sm:text-sm font-medium rounded-xl transition-all ${
                      activeSeverity === option.value
                        ? 'bg-gradient-to-r from-purple-600 to-indigo-600 text-white shadow-md scale-105'
                        : 'bg-gray-100 text-gray-600 hover:bg-gray-200 hover:scale-105'
                    }`}
                  >
                    {option.label}
                  </button>
                ))}
              </div>
            </div>
          </div>
        </div>

        {/* Notifications List */}
        <div className="space-y-4">
          {loading ? (
            <div className="bg-white rounded-2xl shadow-sm border border-gray-200 p-12">
              <div className="flex flex-col items-center justify-center">
                <div className="relative">
                  <div className="animate-spin rounded-full h-12 w-12 border-4 border-sky-200"></div>
                  <div className="animate-spin rounded-full h-12 w-12 border-t-4 border-sky-600 absolute top-0"></div>
                </div>
                <p className="text-sm text-gray-500 mt-4 font-medium">Loading notifications...</p>
              </div>
            </div>
          ) : notifications.length === 0 ? (
            <div className="bg-gradient-to-br from-gray-50 to-gray-100 rounded-2xl shadow-sm border border-gray-200 p-12 sm:p-16">
              <div className="flex flex-col items-center justify-center text-center">
                <div className="bg-gradient-to-br from-sky-100 to-blue-100 rounded-3xl p-6 mb-6 shadow-lg">
                  <Bell className="w-16 h-16 text-sky-600" />
                </div>
                <h3 className="text-xl font-bold text-gray-900 mb-2">
                  {activeFilter !== 'all' || activeSeverity !== 'all' ? 'No matching notifications' : 'All caught up!'}
                </h3>
                <p className="text-sm text-gray-500 max-w-sm">
                  {activeFilter !== 'all' || activeSeverity !== 'all'
                    ? 'Try adjusting your filters to see more notifications'
                    : "You have no new notifications right now. We'll notify you when something important happens."}
                </p>
              </div>
            </div>
          ) : (
            <>
              {notifications.map((notification) => {
                const config = getSeverityConfig(notification.severity);
                const Icon = config.icon;

                return (
                  <div
                    key={notification.notification_id}
                    className={`bg-white rounded-2xl shadow-sm border-2 transition-all hover:shadow-md ${
                      !notification.is_read
                        ? 'border-sky-300 bg-sky-50/30'
                        : 'border-gray-200 hover:border-gray-300'
                    }`}
                  >
                    <div className="p-5 sm:p-6">
                      {/* Header Section */}
                      <div className="flex items-start gap-4 mb-4">
                        {/* Icon */}
                        <div className={`flex-shrink-0 p-3.5 rounded-2xl ${config.bg} shadow-sm`}>
                          <Icon className={`w-6 h-6 ${config.color}`} />
                        </div>

                        {/* Title & Actions */}
                        <div className="flex-1 min-w-0">
                          <div className="flex items-start justify-between gap-3">
                            <div className="flex-1 min-w-0">
                              <div className="flex items-center gap-2 mb-1">
                                <h3 className={`text-base sm:text-lg font-bold leading-tight ${
                                  !notification.is_read ? 'text-gray-900' : 'text-gray-700'
                                }`}>
                                  {notification.title}
                                </h3>
                                {!notification.is_read && (
                                  <span className="flex-shrink-0 w-2.5 h-2.5 bg-sky-500 rounded-full animate-pulse shadow-lg"></span>
                                )}
                              </div>

                              {/* Badges Row */}
                              <div className="flex items-center gap-2 flex-wrap mt-2">
                                <span className={`inline-flex items-center px-2.5 py-1 rounded-lg text-xs font-bold ${config.bg} ${config.color}`}>
                                  {config.label}
                                </span>
                                <span className="text-xs text-gray-400 font-medium">
                                  {getRelativeTimeIST(notification.created_at)}
                                </span>
                                {notification.region && (
                                  <span className="inline-flex items-center gap-1 px-2 py-1 bg-gray-100 text-gray-700 rounded-lg text-xs font-medium">
                                    <span>📍</span>
                                    {notification.region}
                                  </span>
                                )}
                              </div>
                            </div>

                            {/* Action Buttons */}
                            <div className="flex items-center gap-1.5">
                              {!notification.is_read && (
                                <button
                                  onClick={() => handleMarkAsRead(notification)}
                                  className="p-2 text-sky-600 hover:text-sky-700 hover:bg-sky-50 rounded-xl transition-all"
                                  title="Mark as Read"
                                >
                                  <CheckCircle2 className="w-5 h-5" />
                                </button>
                              )}
                              <button
                                onClick={(e) => handleDismiss(notification.notification_id, e)}
                                className="p-2 text-gray-400 hover:text-red-600 hover:bg-red-50 rounded-xl transition-all"
                                title="Dismiss"
                              >
                                <X className="w-5 h-5" />
                              </button>
                            </div>
                          </div>
                        </div>
                      </div>

                      {/* Message */}
                      <p className="text-sm text-gray-700 mb-4 leading-relaxed whitespace-pre-wrap pl-16">
                        {notification.message}
                      </p>

                      {/* Metadata Details */}
                      {notification.metadata && Object.keys(notification.metadata).length > 0 && (
                        <div className="pl-16 space-y-3 mb-4">
                          {/* Alert Type & Priority */}
                          {(notification.metadata.alert_type || notification.metadata.priority) && (
                            <div className="flex flex-wrap items-center gap-2">
                              {notification.metadata.alert_type && (
                                <div className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-gradient-to-r from-gray-50 to-gray-100 rounded-xl border border-gray-200">
                                  <span className="text-xs font-semibold text-gray-500">Type:</span>
                                  <span className="text-xs font-bold text-gray-900 capitalize">
                                    {notification.metadata.alert_type.replace(/_/g, ' ')}
                                  </span>
                                </div>
                              )}
                              {notification.metadata.priority && (
                                <div className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-gradient-to-r from-gray-50 to-gray-100 rounded-xl border border-gray-200">
                                  <span className="text-xs font-semibold text-gray-500">Priority:</span>
                                  <span className="text-xs font-bold text-gray-900 capitalize">
                                    {notification.metadata.priority}
                                  </span>
                                </div>
                              )}
                            </div>
                          )}

                          {/* Instructions */}
                          {notification.metadata.instructions && (
                            <div className="p-4 bg-gradient-to-r from-amber-50 to-orange-50 border-l-4 border-amber-500 rounded-xl shadow-sm">
                              <div className="flex items-start gap-3">
                                <div className="p-2 bg-amber-100 rounded-lg">
                                  <AlertTriangle className="w-5 h-5 text-amber-600" />
                                </div>
                                <div className="flex-1">
                                  <p className="text-xs font-bold text-amber-900 mb-1.5 uppercase tracking-wide">Safety Instructions</p>
                                  <p className="text-sm text-amber-900 leading-relaxed">
                                    {notification.metadata.instructions}
                                  </p>
                                </div>
                              </div>
                            </div>
                          )}

                          {/* Contact Info */}
                          {notification.metadata.contact_info && (
                            <div className="p-4 bg-gradient-to-r from-blue-50 to-sky-50 border-l-4 border-blue-500 rounded-xl shadow-sm">
                              <div className="flex items-start gap-3">
                                <div className="p-2 bg-blue-100 rounded-lg">
                                  <Info className="w-5 h-5 text-blue-600" />
                                </div>
                                <div className="flex-1">
                                  <p className="text-xs font-bold text-blue-900 mb-1.5 uppercase tracking-wide">Contact Information</p>
                                  <p className="text-sm text-blue-900 leading-relaxed">
                                    {notification.metadata.contact_info}
                                  </p>
                                </div>
                              </div>
                            </div>
                          )}

                          {/* Creator Info & Tags */}
                          <div className="flex flex-col sm:flex-row sm:items-center gap-3 pt-2">
                            {/* Creator */}
                            {(notification.metadata.creator_name || notification.metadata.creator_org) && (
                              <div className="flex items-center gap-2 text-xs">
                                <span className="font-semibold text-gray-500">Issued by:</span>
                                <span className="font-medium text-gray-900">
                                  {notification.metadata.creator_name}
                                  {notification.metadata.creator_org && (
                                    <span className="text-gray-600"> ({notification.metadata.creator_org})</span>
                                  )}
                                </span>
                              </div>
                            )}

                            {/* Tags */}
                            {notification.metadata.tags && notification.metadata.tags.length > 0 && (
                              <div className="flex flex-wrap items-center gap-2">
                                {notification.metadata.tags.map((tag, idx) => (
                                  <span
                                    key={idx}
                                    className="inline-flex items-center px-2.5 py-1 bg-gray-100 text-gray-700 rounded-lg text-xs font-medium"
                                  >
                                    #{tag}
                                  </span>
                                ))}
                              </div>
                            )}
                          </div>

                          {/* Alert ID */}
                          {notification.alert_id && (
                            <div className="pt-2 border-t border-gray-200">
                              <span className="text-xs text-gray-400 font-mono">ID: {notification.alert_id}</span>
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                  </div>
                );
              })}
            </>
          )}
        </div>
      </div>
    </DashboardLayout>
  );
}
