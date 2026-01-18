'use client';

import { create } from 'zustand';
import { persist } from 'zustand/middleware';

/**
 * Admin Preferences Store
 * Persisted to localStorage for remembering admin preferences
 */
export const useAdminPreferencesStore = create(
  persist(
    (set, get) => ({
      // Dashboard preferences
      dashboardLayout: 'default',
      defaultDateRange: '7days',

      // User list preferences
      usersPerPage: 20,
      defaultUserSort: 'created_at',
      defaultUserSortOrder: 'desc',

      // Audit log preferences
      logsPerPage: 50,

      // Auto refresh
      autoRefresh: true,
      refreshInterval: 60, // seconds

      // Actions
      setDashboardLayout: (layout) => set({ dashboardLayout: layout }),
      setDefaultDateRange: (range) => set({ defaultDateRange: range }),
      setUsersPerPage: (count) => set({ usersPerPage: count }),
      setDefaultUserSort: (field, order) => set({
        defaultUserSort: field,
        defaultUserSortOrder: order
      }),
      setLogsPerPage: (count) => set({ logsPerPage: count }),
      setAutoRefresh: (enabled) => set({ autoRefresh: enabled }),
      setRefreshInterval: (interval) => set({ refreshInterval: interval }),
    }),
    {
      name: 'admin-preferences',
      partialize: (state) => ({
        dashboardLayout: state.dashboardLayout,
        defaultDateRange: state.defaultDateRange,
        usersPerPage: state.usersPerPage,
        defaultUserSort: state.defaultUserSort,
        defaultUserSortOrder: state.defaultUserSortOrder,
        logsPerPage: state.logsPerPage,
        autoRefresh: state.autoRefresh,
        refreshInterval: state.refreshInterval,
      })
    }
  )
);

/**
 * Admin Dashboard Store
 * For dashboard data and statistics
 */
export const useAdminDashboardStore = create((set, get) => ({
  // Dashboard data
  dashboardData: null,
  isLoading: false,
  error: null,
  lastUpdated: null,

  // System health
  systemHealth: null,

  // Actions
  setDashboardData: (data) => set({
    dashboardData: data,
    isLoading: false,
    error: null,
    lastUpdated: new Date()
  }),
  setSystemHealth: (health) => set({ systemHealth: health }),
  setLoading: (loading) => set({ isLoading: loading }),
  setError: (error) => set({ error, isLoading: false }),
  clearDashboard: () => set({
    dashboardData: null,
    systemHealth: null,
    lastUpdated: null
  }),
}));

/**
 * Admin Users Store
 * For user management state
 */
export const useAdminUsersStore = create((set, get) => ({
  // Users list
  users: [],
  totalUsers: 0,
  totalPages: 0,
  currentPage: 1,
  isLoading: false,
  error: null,

  // Filters
  searchQuery: '',
  roleFilter: 'all',
  statusFilter: 'all',
  sortBy: 'created_at',
  sortOrder: 'desc',

  // Selected user for detail view
  selectedUser: null,
  selectedUserLoading: false,

  // Modals
  isBanModalOpen: false,
  isRoleModalOpen: false,
  isCreateModalOpen: false,
  isEditModalOpen: false,
  modalUser: null,

  // Actions
  setUsers: (users, total, pages) => set({
    users,
    totalUsers: total,
    totalPages: pages,
    isLoading: false
  }),
  setCurrentPage: (page) => set({ currentPage: page }),
  setLoading: (loading) => set({ isLoading: loading }),
  setError: (error) => set({ error, isLoading: false }),

  // Filter actions
  setSearchQuery: (query) => set({ searchQuery: query, currentPage: 1 }),
  setRoleFilter: (role) => set({ roleFilter: role, currentPage: 1 }),
  setStatusFilter: (status) => set({ statusFilter: status, currentPage: 1 }),
  setSort: (sortBy, sortOrder) => set({ sortBy, sortOrder }),
  clearFilters: () => set({
    searchQuery: '',
    roleFilter: 'all',
    statusFilter: 'all',
    currentPage: 1
  }),

  // Selected user actions
  setSelectedUser: (user) => set({ selectedUser: user }),
  setSelectedUserLoading: (loading) => set({ selectedUserLoading: loading }),
  clearSelectedUser: () => set({ selectedUser: null }),

  // Update user in list
  updateUserInList: (userId, updates) => set((state) => ({
    users: state.users.map(u =>
      u.user_id === userId ? { ...u, ...updates } : u
    ),
    selectedUser: state.selectedUser?.user_id === userId
      ? { ...state.selectedUser, ...updates }
      : state.selectedUser
  })),

  // Remove user from list
  removeUserFromList: (userId) => set((state) => ({
    users: state.users.filter(u => u.user_id !== userId),
    totalUsers: state.totalUsers - 1,
    selectedUser: state.selectedUser?.user_id === userId ? null : state.selectedUser
  })),

  // Modal actions
  openBanModal: (user) => set({ isBanModalOpen: true, modalUser: user }),
  closeBanModal: () => set({ isBanModalOpen: false, modalUser: null }),
  openRoleModal: (user) => set({ isRoleModalOpen: true, modalUser: user }),
  closeRoleModal: () => set({ isRoleModalOpen: false, modalUser: null }),
  openCreateModal: () => set({ isCreateModalOpen: true }),
  closeCreateModal: () => set({ isCreateModalOpen: false }),
  openEditModal: (user) => set({ isEditModalOpen: true, modalUser: user }),
  closeEditModal: () => set({ isEditModalOpen: false, modalUser: null }),
}));

/**
 * Admin Content Store
 * For reports, alerts, and chat moderation
 */
export const useAdminContentStore = create((set, get) => ({
  // Reports
  reports: [],
  totalReports: 0,
  reportsLoading: false,
  reportsPage: 1,

  // Alerts
  alerts: [],
  totalAlerts: 0,
  alertsLoading: false,
  alertsPage: 1,

  // Chat messages
  chatMessages: [],
  totalMessages: 0,
  messagesLoading: false,
  messagesPage: 1,

  // Filters
  reportStatusFilter: 'all',
  reportTypeFilter: 'all',
  alertStatusFilter: 'all',
  alertSeverityFilter: 'all',

  // Actions - Reports
  setReports: (reports, total) => set({
    reports,
    totalReports: total,
    reportsLoading: false
  }),
  setReportsLoading: (loading) => set({ reportsLoading: loading }),
  setReportsPage: (page) => set({ reportsPage: page }),
  setReportFilters: (status, type) => set({
    reportStatusFilter: status,
    reportTypeFilter: type,
    reportsPage: 1
  }),
  removeReport: (reportId) => set((state) => ({
    reports: state.reports.filter(r => r.report_id !== reportId),
    totalReports: state.totalReports - 1
  })),

  // Actions - Alerts
  setAlerts: (alerts, total) => set({
    alerts,
    totalAlerts: total,
    alertsLoading: false
  }),
  setAlertsLoading: (loading) => set({ alertsLoading: loading }),
  setAlertsPage: (page) => set({ alertsPage: page }),
  setAlertFilters: (status, severity) => set({
    alertStatusFilter: status,
    alertSeverityFilter: severity,
    alertsPage: 1
  }),
  removeAlert: (alertId) => set((state) => ({
    alerts: state.alerts.filter(a => a.alert_id !== alertId),
    totalAlerts: state.totalAlerts - 1
  })),

  // Actions - Chat Messages
  setChatMessages: (messages, total) => set({
    chatMessages: messages,
    totalMessages: total,
    messagesLoading: false
  }),
  setMessagesLoading: (loading) => set({ messagesLoading: loading }),
  setMessagesPage: (page) => set({ messagesPage: page }),
  removeMessage: (messageId) => set((state) => ({
    chatMessages: state.chatMessages.filter(m => m.message_id !== messageId),
    totalMessages: state.totalMessages - 1
  })),
}));

/**
 * Admin Monitoring Store
 * For system monitoring data
 */
export const useAdminMonitoringStore = create((set, get) => ({
  // System health
  health: null,
  healthLoading: false,

  // API stats
  apiStats: null,
  apiStatsLoading: false,

  // Error logs
  errorLogs: [],
  totalErrors: 0,
  errorsLoading: false,
  errorsPage: 1,

  // Database stats
  dbStats: null,
  dbStatsLoading: false,

  // Last update timestamps
  lastHealthUpdate: null,
  lastApiStatsUpdate: null,

  // Actions
  setHealth: (health) => set({
    health,
    healthLoading: false,
    lastHealthUpdate: new Date()
  }),
  setHealthLoading: (loading) => set({ healthLoading: loading }),

  setApiStats: (stats) => set({
    apiStats: stats,
    apiStatsLoading: false,
    lastApiStatsUpdate: new Date()
  }),
  setApiStatsLoading: (loading) => set({ apiStatsLoading: loading }),

  setErrorLogs: (logs, total) => set({
    errorLogs: logs,
    totalErrors: total,
    errorsLoading: false
  }),
  setErrorsLoading: (loading) => set({ errorsLoading: loading }),
  setErrorsPage: (page) => set({ errorsPage: page }),

  setDbStats: (stats) => set({ dbStats: stats, dbStatsLoading: false }),
  setDbStatsLoading: (loading) => set({ dbStatsLoading: loading }),

  clearMonitoring: () => set({
    health: null,
    apiStats: null,
    errorLogs: [],
    dbStats: null,
    lastHealthUpdate: null,
    lastApiStatsUpdate: null
  }),
}));

/**
 * Admin Settings Store
 * For system settings management
 */
export const useAdminSettingsStore = create((set, get) => ({
  // Settings
  settings: {},
  settingsLoading: false,
  error: null,

  // Selected category
  selectedCategory: 'general',

  // Edit mode
  editingKey: null,
  editValue: null,

  // Actions
  setSettings: (settings) => set({ settings, settingsLoading: false }),
  setSettingsLoading: (loading) => set({ settingsLoading: loading }),
  setError: (error) => set({ error }),
  setSelectedCategory: (category) => set({ selectedCategory: category }),

  startEditing: (key, value) => set({ editingKey: key, editValue: value }),
  cancelEditing: () => set({ editingKey: null, editValue: null }),
  setEditValue: (value) => set({ editValue: value }),

  updateSetting: (key, value) => set((state) => {
    const newSettings = { ...state.settings };
    // Find and update the setting in the correct category
    Object.keys(newSettings).forEach(category => {
      if (newSettings[category]) {
        newSettings[category] = newSettings[category].map(s =>
          s.key === key ? { ...s, value } : s
        );
      }
    });
    return { settings: newSettings, editingKey: null, editValue: null };
  }),
}));

/**
 * Admin Audit Logs Store
 * For audit log viewing and filtering
 */
export const useAdminAuditStore = create((set, get) => ({
  // Audit logs
  logs: [],
  totalLogs: 0,
  logsLoading: false,
  currentPage: 1,

  // Admin activity logs
  adminLogs: [],
  totalAdminLogs: 0,
  adminLogsLoading: false,
  adminLogsPage: 1,

  // Stats
  auditStats: null,
  statsLoading: false,

  // Filters
  actionFilter: 'all',
  userIdFilter: '',
  dateRangeFilter: '7days',
  searchQuery: '',

  // Actions
  setLogs: (logs, total) => set({
    logs,
    totalLogs: total,
    logsLoading: false
  }),
  setLogsLoading: (loading) => set({ logsLoading: loading }),
  setCurrentPage: (page) => set({ currentPage: page }),

  setAdminLogs: (logs, total) => set({
    adminLogs: logs,
    totalAdminLogs: total,
    adminLogsLoading: false
  }),
  setAdminLogsLoading: (loading) => set({ adminLogsLoading: loading }),
  setAdminLogsPage: (page) => set({ adminLogsPage: page }),

  setAuditStats: (stats) => set({ auditStats: stats, statsLoading: false }),
  setStatsLoading: (loading) => set({ statsLoading: loading }),

  // Filter actions
  setActionFilter: (action) => set({ actionFilter: action, currentPage: 1 }),
  setUserIdFilter: (userId) => set({ userIdFilter: userId, currentPage: 1 }),
  setDateRangeFilter: (range) => set({ dateRangeFilter: range, currentPage: 1 }),
  setSearchQuery: (query) => set({ searchQuery: query, currentPage: 1 }),
  clearFilters: () => set({
    actionFilter: 'all',
    userIdFilter: '',
    dateRangeFilter: '7days',
    searchQuery: '',
    currentPage: 1
  }),
}));

// Default export
export default useAdminPreferencesStore;
