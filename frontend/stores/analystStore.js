'use client';

import { create } from 'zustand';
import { persist } from 'zustand/middleware';

/**
 * Analyst Preferences Store
 * Persisted to localStorage for remembering user preferences
 */
export const useAnalystStore = create(
  persist(
    (set, get) => ({
      // Dashboard preferences
      dashboardLayout: 'default', // 'default', 'compact', 'expanded'
      defaultDateRange: '7days',

      // Real-time monitoring preferences
      autoRefresh: true,
      refreshInterval: 60, // seconds
      alertSoundEnabled: false,

      // Saved filters
      lastUsedFilters: {},
      favoriteQueries: [],

      // Recent items (for quick access)
      recentNotes: [],
      recentExports: [],

      // Actions
      setDashboardLayout: (layout) => set({ dashboardLayout: layout }),
      setDefaultDateRange: (range) => set({ defaultDateRange: range }),
      setAutoRefresh: (enabled) => set({ autoRefresh: enabled }),
      setRefreshInterval: (interval) => set({ refreshInterval: interval }),
      setAlertSoundEnabled: (enabled) => set({ alertSoundEnabled: enabled }),

      saveLastUsedFilters: (filters) => set({ lastUsedFilters: filters }),

      addRecentNote: (note) => set((state) => ({
        recentNotes: [note, ...state.recentNotes.filter(n => n.note_id !== note.note_id)].slice(0, 10)
      })),

      addRecentExport: (exportJob) => set((state) => ({
        recentExports: [exportJob, ...state.recentExports.filter(e => e.job_id !== exportJob.job_id)].slice(0, 10)
      })),

      clearRecentItems: () => set({ recentNotes: [], recentExports: [] }),
    }),
    {
      name: 'analyst-preferences',
      partialize: (state) => ({
        dashboardLayout: state.dashboardLayout,
        defaultDateRange: state.defaultDateRange,
        autoRefresh: state.autoRefresh,
        refreshInterval: state.refreshInterval,
        alertSoundEnabled: state.alertSoundEnabled,
        lastUsedFilters: state.lastUsedFilters,
      })
    }
  )
);

/**
 * Real-time Monitoring Store
 * Non-persisted store for live monitoring data
 */
export const useRealtimeStore = create((set, get) => ({
  // Monitoring data
  monitoringData: null,
  lastUpdate: null,
  isLoading: false,
  error: null,

  // Selected location for detail view
  selectedLocation: null,

  // Connection status
  isConnected: false,

  // Actions
  setMonitoringData: (data) => set({
    monitoringData: data,
    lastUpdate: new Date(),
    isLoading: false,
    error: null
  }),

  setSelectedLocation: (locationId) => set({ selectedLocation: locationId }),
  setLoading: (loading) => set({ isLoading: loading }),
  setError: (error) => set({ error, isLoading: false }),
  setConnected: (connected) => set({ isConnected: connected }),

  clearMonitoringData: () => set({
    monitoringData: null,
    lastUpdate: null,
    selectedLocation: null
  }),
}));

/**
 * Notes Store
 * For managing analyst notes state
 */
export const useNotesStore = create((set, get) => ({
  // Notes state
  notes: [],
  totalNotes: 0,
  selectedNote: null,
  isEditing: false,
  isLoading: false,

  // Filters
  tagFilter: [],
  searchQuery: '',
  availableTags: [],

  // Actions
  setNotes: (notes, total) => set({ notes, totalNotes: total }),
  addNote: (note) => set((state) => ({
    notes: [note, ...state.notes],
    totalNotes: state.totalNotes + 1
  })),
  updateNote: (noteId, updates) => set((state) => ({
    notes: state.notes.map(n => n.note_id === noteId ? {...n, ...updates} : n),
    selectedNote: state.selectedNote?.note_id === noteId
      ? {...state.selectedNote, ...updates}
      : state.selectedNote
  })),
  deleteNote: (noteId) => set((state) => ({
    notes: state.notes.filter(n => n.note_id !== noteId),
    totalNotes: state.totalNotes - 1,
    selectedNote: state.selectedNote?.note_id === noteId ? null : state.selectedNote
  })),

  setSelectedNote: (note) => set({ selectedNote: note }),
  setEditing: (editing) => set({ isEditing: editing }),
  setLoading: (loading) => set({ isLoading: loading }),

  setTagFilter: (tags) => set({ tagFilter: tags }),
  setSearchQuery: (query) => set({ searchQuery: query }),
  setAvailableTags: (tags) => set({ availableTags: tags }),

  clearFilters: () => set({ tagFilter: [], searchQuery: '' }),
}));

/**
 * Export Store
 * For managing export jobs state
 */
export const useExportStore = create((set, get) => ({
  // Export jobs
  exportJobs: [],
  activeJob: null,
  isExporting: false,

  // Modal state
  isExportModalOpen: false,
  exportConfig: null,

  // Actions
  setExportJobs: (jobs) => set({ exportJobs: jobs }),
  addExportJob: (job) => set((state) => ({
    exportJobs: [job, ...state.exportJobs],
    activeJob: job
  })),
  updateExportJob: (jobId, updates) => set((state) => ({
    exportJobs: state.exportJobs.map(j => j.job_id === jobId ? {...j, ...updates} : j),
    activeJob: state.activeJob?.job_id === jobId
      ? {...state.activeJob, ...updates}
      : state.activeJob
  })),

  setActiveJob: (job) => set({ activeJob: job }),
  setExporting: (exporting) => set({ isExporting: exporting }),

  openExportModal: (config = null) => set({ isExportModalOpen: true, exportConfig: config }),
  closeExportModal: () => set({ isExportModalOpen: false, exportConfig: null }),
}));

/**
 * Analytics Data Store
 * For caching analytics data
 */
export const useAnalyticsDataStore = create((set, get) => ({
  // Dashboard data
  dashboardData: null,
  dashboardLoading: false,

  // Analytics data
  reportAnalytics: null,
  trendData: null,
  geoData: null,
  nlpInsights: null,

  // Loading states
  isLoading: {
    reports: false,
    trends: false,
    geo: false,
    nlp: false,
  },

  // Current filters
  currentDateRange: '7days',
  currentFilters: {},

  // Actions
  setDashboardData: (data) => set({ dashboardData: data, dashboardLoading: false }),
  setDashboardLoading: (loading) => set({ dashboardLoading: loading }),

  setReportAnalytics: (data) => set({ reportAnalytics: data }),
  setTrendData: (data) => set({ trendData: data }),
  setGeoData: (data) => set({ geoData: data }),
  setNlpInsights: (data) => set({ nlpInsights: data }),

  setLoading: (type, loading) => set((state) => ({
    isLoading: { ...state.isLoading, [type]: loading }
  })),

  setDateRange: (range) => set({ currentDateRange: range }),
  setFilters: (filters) => set({ currentFilters: filters }),

  clearAllData: () => set({
    dashboardData: null,
    reportAnalytics: null,
    trendData: null,
    geoData: null,
    nlpInsights: null,
  }),
}));

export default useAnalystStore;
