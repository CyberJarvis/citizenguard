/**
 * API Client for CoastGuardian Backend
 * Axios-based HTTP client with authentication support
 */

import axios from 'axios';
import Cookies from 'js-cookie';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';

// Backend server base URL (without /api/v1) for static files like uploads
const SERVER_BASE_URL = process.env.NEXT_PUBLIC_SERVER_URL || 'http://localhost:8000';

/**
 * Get the proper image URL handling both S3 and local storage
 * @param {string} imageUrl - The image URL (can be S3 URL or local path)
 * @returns {string} The proper full URL
 */
export const getImageUrl = (imageUrl) => {
  if (!imageUrl) return '';
  // If it's already a full URL (S3 or other), use it directly
  if (imageUrl.startsWith('http://') || imageUrl.startsWith('https://')) {
    return imageUrl;
  }
  // Otherwise, prepend the server base URL for local files
  return `${SERVER_BASE_URL}${imageUrl.replace(/\\/g, '/')}`;
};

/**
 * Get the redirect path based on user role
 * Used for consistent navigation after login across the app
 * @param {string} role - The user's role
 * @returns {string} The path to redirect to
 */
export const getRoleBasedRedirectPath = (role) => {
  switch (role) {
    case 'authority_admin':
      return '/admin/dashboard';
    case 'authority':
      return '/authority';
    case 'analyst':
      return '/analyst';
    case 'citizen':
    default:
      return '/dashboard';
  }
};

/**
 * Get the full URL for an uploaded file
 * Handles relative paths like /uploads/hazards/image.jpg
 * @param {string} path - The file path (e.g., /uploads/hazards/uuid.jpg)
 * @returns {string} Full URL to the file
 */
export const getUploadUrl = (path) => {
  if (!path) return '';

  // If already a full URL, return as is
  if (path.startsWith('http://') || path.startsWith('https://')) {
    return path;
  }

  // Ensure path starts with /
  const normalizedPath = path.startsWith('/') ? path : `/${path}`;

  return `${SERVER_BASE_URL}${normalizedPath}`;
};

// Create axios instance
const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  withCredentials: true,
});

// Request interceptor - Add auth token to requests
apiClient.interceptors.request.use(
  (config) => {
    const token = Cookies.get('access_token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Response interceptor - Handle token refresh
apiClient.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;

    // If 401 and not already retried, try to refresh token
    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;

      try {
        const refreshToken = Cookies.get('refresh_token');
        if (!refreshToken) {
          throw new Error('No refresh token available');
        }

        const response = await axios.post(
          `${API_BASE_URL}/auth/refresh`,
          { refresh_token: refreshToken }
        );

        const { access_token, refresh_token: newRefreshToken } = response.data;

        // Update tokens
        Cookies.set('access_token', access_token, { expires: 1 / 12 }); // 2 hours
        Cookies.set('refresh_token', newRefreshToken, { expires: 7 });

        // Retry original request with new token
        originalRequest.headers.Authorization = `Bearer ${access_token}`;
        return apiClient(originalRequest);
      } catch (refreshError) {
        // Refresh failed - clear tokens and redirect to login
        Cookies.remove('access_token');
        Cookies.remove('refresh_token');

        if (typeof window !== 'undefined') {
          window.location.href = '/login';
        }

        return Promise.reject(refreshError);
      }
    }

    return Promise.reject(error);
  }
);

// ==================== AUTH API ====================

/**
 * Sign up with email and password
 */
export const signup = async (data) => {
  const response = await apiClient.post('/auth/signup', data);
  return response.data;
};

/**
 * Login with email/password
 */
export const loginWithPassword = async (email, password) => {
  const response = await apiClient.post('/auth/login', {
    email,
    password,
    login_type: 'password',
  });

  const { access_token, refresh_token } = response.data;

  // Store tokens in cookies
  Cookies.set('access_token', access_token, { expires: 1 / 12 }); // 2 hours
  Cookies.set('refresh_token', refresh_token, { expires: 7 });

  // Fetch user data after login to get complete user info including role
  const user = await getCurrentUser();

  return { user, access_token, refresh_token };
};

/**
 * Login with OTP (email or phone)
 */
export const loginWithOTP = async (identifier, otp, otpType = 'email') => {
  const payload = {
    login_type: 'otp',
    otp_type: otpType,
    otp,
  };

  if (otpType === 'email') {
    payload.email = identifier;
  } else {
    payload.phone = identifier;
  }

  const response = await apiClient.post('/auth/login', payload);

  const { access_token, refresh_token } = response.data;

  // Store tokens in cookies
  Cookies.set('access_token', access_token, { expires: 1 / 12 });
  Cookies.set('refresh_token', refresh_token, { expires: 7 });

  // Fetch user data after login to get complete user info including role
  const user = await getCurrentUser();

  return { user, access_token, refresh_token };
};

/**
 * Request OTP for login
 */
export const requestOTP = async (identifier, otpType = 'email') => {
  const payload = {
    otp_type: otpType,
  };

  if (otpType === 'email') {
    payload.email = identifier;
  } else {
    payload.phone = identifier;
  }

  const response = await apiClient.post('/auth/request-otp', payload);
  return response.data;
};

/**
 * Google OAuth login - Get authorization URL
 */
export const getGoogleAuthUrl = async () => {
  const response = await apiClient.get('/auth/google/login');
  return response.data.authorization_url;
};

/**
 * Google OAuth callback - Exchange code for tokens
 */
export const handleGoogleCallback = async (code, state) => {
  try {
    console.log('API: Calling Google callback with code and state...');
    console.log('API: Code length:', code?.length);
    console.log('API: State length:', state?.length);

    const response = await apiClient.get('/auth/google/callback', {
      params: { code, state },
    });

    console.log('API: Google callback response:', response.data);

    const { access_token, refresh_token, user } = response.data;

    if (!access_token || !refresh_token || !user) {
      console.error('API: Invalid response format:', response.data);
      throw new Error('Invalid response from server: missing tokens or user data');
    }

    // Store tokens in cookies
    Cookies.set('access_token', access_token, { expires: 1 / 12 });
    Cookies.set('refresh_token', refresh_token, { expires: 7 });

    console.log('API: Tokens stored successfully');

    return { user, access_token, refresh_token };
  } catch (error) {
    console.error('API: Google callback error:', error);
    console.error('API: Error response:', error.response);
    console.error('API: Error response status:', error.response?.status);

    // Log error data with proper serialization
    if (error.response?.data) {
      console.error('API: Error response data (raw):', JSON.stringify(error.response.data, null, 2));
      console.error('API: Error detail:', error.response.data.detail);
      console.error('API: Error message:', error.response.data.message);
    } else {
      console.error('API: No error response data');
    }

    throw error;
  }
};

/**
 * Logout - Revoke tokens
 */
export const logout = async () => {
  try {
    const refreshToken = Cookies.get('refresh_token');
    if (refreshToken) {
      await apiClient.post('/auth/logout', {
        refresh_token: refreshToken
      });
    }
  } catch (error) {
    console.error('Logout API error:', error);
  } finally {
    // Always clear tokens locally
    Cookies.remove('access_token');
    Cookies.remove('refresh_token');
  }
};

/**
 * Refresh access token
 */
export const refreshAccessToken = async () => {
  const refreshToken = Cookies.get('refresh_token');
  if (!refreshToken) {
    throw new Error('No refresh token available');
  }

  const response = await apiClient.post('/auth/refresh', {
    refresh_token: refreshToken,
  });

  const { access_token, refresh_token: newRefreshToken } = response.data;

  // Update tokens
  Cookies.set('access_token', access_token, { expires: 1 / 12 });
  Cookies.set('refresh_token', newRefreshToken, { expires: 7 });

  return { access_token, refresh_token: newRefreshToken };
};

/**
 * Get current user profile
 */
export const getCurrentUser = async () => {
  const response = await apiClient.get('/auth/me');
  return response.data;
};

/**
 * Change password
 */
export const changePassword = async (oldPassword, newPassword) => {
  const response = await apiClient.post('/auth/change-password', {
    old_password: oldPassword,
    new_password: newPassword,
  });
  return response.data;
};

/**
 * Forgot password - Request password reset OTP
 */
export const forgotPassword = async (email) => {
  const response = await apiClient.post('/auth/forgot-password', {
    email,
  });
  return response.data;
};

/**
 * Reset password with OTP
 */
export const resetPassword = async (email, otp, newPassword) => {
  const response = await apiClient.post('/auth/reset-password', {
    email,
    otp,
    new_password: newPassword,
  });
  return response.data;
};

/**
 * Verify OTP (for email verification after signup)
 */
export const verifyOTP = async (email, otp, otpType = 'email') => {
  const payload = {
    otp,
    otp_type: otpType,
  };

  if (otpType === 'email') {
    payload.email = email;
  } else {
    payload.phone = email; // Using 'email' parameter for both email/phone
  }

  const response = await apiClient.post('/auth/verify-otp', payload);
  return response.data;
};

// ==================== HAZARD REPORTS API ====================

/**
 * Submit a new hazard report with files (local upload)
 */
export const submitHazardReport = async (formData) => {
  const response = await apiClient.post('/hazards', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  });
  return response.data;
};

/**
 * Submit a new hazard report with S3 URLs (presigned upload)
 * Use this when images have been uploaded directly to S3
 *
 * @param {Object} reportData - Report data with S3 URLs
 * @param {string} reportData.hazard_type - Type of hazard
 * @param {string} reportData.category - 'natural' or 'humanMade'
 * @param {number} reportData.latitude - Latitude coordinate
 * @param {number} reportData.longitude - Longitude coordinate
 * @param {string} reportData.address - Address description
 * @param {string} reportData.description - Optional description
 * @param {Object} reportData.weather - Optional weather data
 * @param {string} reportData.image_url - S3 public URL of uploaded image
 * @param {string} reportData.voice_note_url - Optional S3 URL of voice note
 */
export const submitHazardReportS3 = async (reportData) => {
  const response = await apiClient.post('/hazards/s3', reportData);
  return response.data;
};

/**
 * Check if S3 storage is enabled
 */
export const getStorageStatus = async () => {
  try {
    const response = await apiClient.get('/uploads/status');
    return response.data;
  } catch (error) {
    return { s3_enabled: false, storage_type: 'local' };
  }
};

/**
 * Get list of hazard reports with filters
 */
export const getHazardReports = async (params = {}) => {
  const response = await apiClient.get('/hazards', { params });
  return response.data;
};

/**
 * Get optimized map data with heatmap points
 * Returns reports, heatmap points, and statistics for map visualization
 */
export const getMapData = async (options = {}) => {
  const response = await apiClient.get('/hazards/map-data', {
    params: {
      hours: options.hours || 24,
      include_heatmap: options.includeHeatmap !== false,
      include_clusters: options.includeClusters !== false,
      min_severity: options.minSeverity || null,
    },
  });
  return response.data;
};

/**
 * Get timeline data for incident timeline visualization
 * Supports historical (6h, 24h) and forecast (48h_future) views
 * @param {Object} options - Timeline options
 * @param {string} options.timeRange - Time range: '6h', '24h', or '48h_future'
 * @param {boolean} options.includeForecast - Include forecast data for future range
 * @param {boolean} options.includeHeatmap - Include heatmap points
 */
export const getTimelineData = async (options = {}) => {
  const response = await apiClient.get('/hazards/timeline', {
    params: {
      time_range: options.timeRange || '24h',
      include_forecast: options.includeForecast !== false,
      include_heatmap: options.includeHeatmap !== false,
    },
  });
  return response.data;
};

/**
 * Get current user's hazard reports
 */
export const getMyHazardReports = async (params = {}) => {
  const response = await apiClient.get('/hazards/my-reports', { params });
  return response.data;
};

/**
 * Get a single hazard report by ID
 */
export const getHazardReportById = async (reportId) => {
  const response = await apiClient.get(`/hazards/${reportId}`);
  return response.data;
};

/**
 * Verify a hazard report (analyst/admin only)
 */
export const verifyHazardReport = async (reportId, verificationData) => {
  const response = await apiClient.patch(`/hazards/${reportId}/verify`, verificationData);
  return response.data;
};

/**
 * Like or unlike a hazard report
 */
export const toggleLikeHazardReport = async (reportId) => {
  const response = await apiClient.post(`/hazards/${reportId}/like`);
  return response.data;
};

/**
 * Record a view for a hazard report
 * Call this when a post becomes visible in the viewport
 */
export const recordHazardReportView = async (reportId) => {
  try {
    const response = await apiClient.post(`/hazards/${reportId}/view`);
    return response.data;
  } catch (error) {
    // Silently fail for view tracking - non-critical
    console.debug('View tracking failed:', error);
    return { success: false };
  }
};

/**
 * Get list of report IDs that the current user has liked
 */
export const getMyLikedReports = async () => {
  const response = await apiClient.get('/hazards/my-likes');
  return response.data;
};

/**
 * Delete a hazard report
 */
export const deleteHazardReport = async (reportId) => {
  const response = await apiClient.delete(`/hazards/${reportId}`);
  return response.data;
};

/**
 * Report a hazard report for inappropriate content
 */
export const reportHazardReport = async (reportId, reason) => {
  // Use URLSearchParams for proper form encoding that FastAPI expects
  const params = new URLSearchParams();
  params.append('reason', reason);
  const response = await apiClient.post(`/hazards/${reportId}/report`, params, {
    headers: {
      'Content-Type': 'application/x-www-form-urlencoded',
    },
  });
  return response.data;
};

// ==================== MONITORING API (ML-Powered) ====================

/**
 * Get list of all monitored locations
 */
export const getMonitoringLocations = async () => {
  const response = await apiClient.get('/monitoring/locations');
  return response.data;
};

/**
 * Get current monitoring data for all locations
 */
export const getCurrentMonitoringData = async (params = {}) => {
  const response = await apiClient.get('/monitoring/current', { params });
  return response.data;
};

/**
 * Get detailed monitoring data for a specific location
 */
export const getLocationDetails = async (locationId) => {
  const response = await apiClient.get(`/monitoring/location/${locationId}`);
  return response.data;
};

/**
 * Get recent earthquake data
 */
export const getRecentEarthquakes = async (params = {}) => {
  const response = await apiClient.get('/monitoring/earthquakes/recent', { params });
  return response.data;
};

/**
 * Get active alerts (warning or higher)
 */
export const getActiveAlerts = async (params = {}) => {
  const response = await apiClient.get('/monitoring/alerts/active', { params });
  return response.data;
};

/**
 * Get monitoring summary statistics
 */
export const getMonitoringSummary = async () => {
  const response = await apiClient.get('/monitoring/summary');
  return response.data;
};

/**
 * Trigger manual refresh of monitoring data (admin only)
 */
export const triggerMonitoringRefresh = async () => {
  const response = await apiClient.post('/monitoring/refresh');
  return response.data;
};

/**
 * Get monitoring system health status
 */
export const getMonitoringHealth = async () => {
  const response = await apiClient.get('/monitoring/health');
  return response.data;
};

// ==================== PROFILE API ====================

/**
 * Get current user's profile
 */
export const getMyProfile = async () => {
  const response = await apiClient.get('/profile/me');
  return response.data;
};

/**
 * Update current user's profile
 */
export const updateMyProfile = async (profileData) => {
  const response = await apiClient.put('/profile/me', profileData);
  return response.data;
};

/**
 * Upload profile picture
 */
export const uploadProfilePicture = async (file) => {
  const formData = new FormData();
  formData.append('file', file);

  const response = await apiClient.post('/profile/picture', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  });
  return response.data;
};

/**
 * Delete profile picture
 */
export const deleteProfilePicture = async () => {
  const response = await apiClient.delete('/profile/picture');
  return response.data;
};

/**
 * Get user statistics
 */
export const getUserStats = async () => {
  const response = await apiClient.get('/profile/stats');
  return response.data;
};

/**
 * Get public profile of another user
 */
export const getPublicProfile = async (userId) => {
  const response = await apiClient.get(`/profile/${userId}`);
  return response.data;
};

// ==================== CHAT API ====================

/**
 * Get chat messages from a room
 */
export const getChatMessages = async (roomId = 'general', page = 1, pageSize = 50) => {
  const response = await apiClient.get('/chat/messages', {
    params: {
      room_id: roomId,
      page,
      page_size: pageSize
    }
  });
  return response.data;
};

/**
 * Get online users in a chat room
 */
export const getOnlineUsers = async (roomId = 'general') => {
  const response = await apiClient.get('/chat/online-users', {
    params: { room_id: roomId }
  });
  return response.data;
};

/**
 * Get available chat rooms
 */
export const getChatRooms = async () => {
  const response = await apiClient.get('/chat/rooms');
  return response.data;
};

/**
 * Delete a chat message
 */
export const deleteChatMessage = async (messageId) => {
  const response = await apiClient.delete(`/chat/messages/${messageId}`);
  return response.data;
};

// ==================== NOTIFICATION API ====================

/**
 * Get user's notifications with filters
 */
export const getNotifications = async (params = {}) => {
  const response = await apiClient.get('/notifications', { params });
  return response.data;
};

/**
 * Get notification statistics
 */
export const getNotificationStats = async () => {
  const response = await apiClient.get('/notifications/stats');
  return response.data;
};

/**
 * Mark a notification as read
 */
export const markNotificationRead = async (notificationId) => {
  const response = await apiClient.put(`/notifications/${notificationId}/read`);
  return response.data;
};

/**
 * Mark all notifications as read
 */
export const markAllNotificationsRead = async () => {
  const response = await apiClient.put('/notifications/read-all');
  return response.data;
};

/**
 * Dismiss a notification
 */
export const dismissNotification = async (notificationId) => {
  const response = await apiClient.put(`/notifications/${notificationId}/dismiss`);
  return response.data;
};

/**
 * Clear all read notifications
 */
export const clearReadNotifications = async () => {
  const response = await apiClient.delete('/notifications/clear');
  return response.data;
};

/**
 * Delete a specific notification
 */
export const deleteNotification = async (notificationId) => {
  const response = await apiClient.delete(`/notifications/${notificationId}`);
  return response.data;
};

// ==================== ALERTS API ====================

/**
 * Get list of alerts with filters
 */
export const getAlerts = async (params = {}) => {
  const response = await apiClient.get('/alerts', { params });
  return response.data;
};

/**
 * Get a specific alert by ID
 */
export const getAlertById = async (alertId) => {
  const response = await apiClient.get(`/alerts/${alertId}`);
  return response.data;
};

/**
 * Get active alerts summary
 */
export const getActiveAlertsSummary = async () => {
  const response = await apiClient.get('/alerts/active/summary');
  return response.data;
};

// ==================== ANALYST API ====================

/**
 * Get analyst dashboard data
 */
export const getAnalystDashboard = async () => {
  const response = await apiClient.get('/analyst/dashboard');
  return response.data;
};

/**
 * Get real-time monitoring data
 */
export const getRealtimeMonitoring = async (minAlertLevel = null) => {
  const params = minAlertLevel ? { min_alert_level: minAlertLevel } : {};
  const response = await apiClient.get('/analyst/dashboard/realtime', { params });
  return response.data;
};

/**
 * Get report analytics
 */
export const getReportAnalytics = async (params = {}) => {
  const response = await apiClient.get('/analyst/analytics/reports', { params });
  return response.data;
};

/**
 * Get trend analytics
 */
export const getTrendAnalytics = async (params = {}) => {
  const response = await apiClient.get('/analyst/analytics/trends', { params });
  return response.data;
};

/**
 * Get geospatial analytics
 */
export const getGeoAnalytics = async (params = {}) => {
  const response = await apiClient.get('/analyst/analytics/geo', { params });
  return response.data;
};

/**
 * Get NLP insights
 */
export const getNlpInsights = async (params = {}) => {
  const response = await apiClient.get('/analyst/analytics/nlp', { params });
  return response.data;
};

/**
 * Get verification metrics
 */
export const getVerificationMetrics = async (params = {}) => {
  const response = await apiClient.get('/analyst/analytics/verification', { params });
  return response.data;
};

/**
 * Get hazard type analytics
 */
export const getHazardTypeAnalytics = async (params = {}) => {
  const response = await apiClient.get('/analyst/analytics/hazard-types', { params });
  return response.data;
};

/**
 * Get period comparison
 */
export const getPeriodComparison = async (params = {}) => {
  const response = await apiClient.get('/analyst/analytics/comparison', { params });
  return response.data;
};

/**
 * Get reports for analyst (PII filtered)
 */
export const getAnalystReports = async (params = {}) => {
  const response = await apiClient.get('/analyst/reports', { params });
  return response.data;
};

/**
 * Get single report detail for analyst
 */
export const getAnalystReportDetail = async (reportId) => {
  const response = await apiClient.get(`/analyst/reports/${reportId}`);
  return response.data;
};

// ==================== ANALYST NOTES API ====================

/**
 * Get analyst notes
 */
export const getAnalystNotes = async (params = {}) => {
  const response = await apiClient.get('/analyst/notes', { params });
  return response.data;
};

/**
 * Create a new note
 */
export const createAnalystNote = async (noteData) => {
  const response = await apiClient.post('/analyst/notes', noteData);
  return response.data;
};

/**
 * Get a specific note
 */
export const getAnalystNote = async (noteId) => {
  const response = await apiClient.get(`/analyst/notes/${noteId}`);
  return response.data;
};

/**
 * Update a note
 */
export const updateAnalystNote = async (noteId, updates) => {
  const response = await apiClient.put(`/analyst/notes/${noteId}`, updates);
  return response.data;
};

/**
 * Delete a note
 */
export const deleteAnalystNote = async (noteId) => {
  const response = await apiClient.delete(`/analyst/notes/${noteId}`);
  return response.data;
};

// ==================== ANALYST SAVED QUERIES API ====================

/**
 * Get saved queries
 */
export const getSavedQueries = async (params = {}) => {
  const response = await apiClient.get('/analyst/queries', { params });
  return response.data;
};

/**
 * Create a saved query
 */
export const createSavedQuery = async (queryData) => {
  const response = await apiClient.post('/analyst/queries', queryData);
  return response.data;
};

/**
 * Execute a saved query
 */
export const executeSavedQuery = async (queryId) => {
  const response = await apiClient.post(`/analyst/queries/${queryId}/execute`);
  return response.data;
};

/**
 * Delete a saved query
 */
export const deleteSavedQuery = async (queryId) => {
  const response = await apiClient.delete(`/analyst/queries/${queryId}`);
  return response.data;
};

// ==================== ANALYST EXPORT API ====================

/**
 * Create an export job
 */
export const createExportJob = async (exportConfig) => {
  const response = await apiClient.post('/analyst/export', exportConfig);
  return response.data;
};

/**
 * Get export jobs
 */
export const getExportJobs = async (params = {}) => {
  const response = await apiClient.get('/analyst/exports', { params });
  return response.data;
};

/**
 * Get export job status
 */
export const getExportJobStatus = async (jobId) => {
  const response = await apiClient.get(`/analyst/export/${jobId}`);
  return response.data;
};

/**
 * Download export file
 */
export const downloadExport = async (jobId) => {
  const response = await apiClient.get(`/analyst/export/${jobId}/download`, {
    responseType: 'blob'
  });
  return response.data;
};

/**
 * Delete export job
 */
export const deleteExportJob = async (jobId) => {
  const response = await apiClient.delete(`/analyst/export/${jobId}`);
  return response.data;
};

// ==================== ANALYST SCHEDULED REPORTS API ====================

/**
 * Get scheduled reports
 */
export const getScheduledReports = async () => {
  const response = await apiClient.get('/analyst/scheduled-reports');
  return response.data;
};

/**
 * Create a scheduled report
 */
export const createScheduledReport = async (config) => {
  const response = await apiClient.post('/analyst/scheduled-reports', config);
  return response.data;
};

/**
 * Update scheduled report
 */
export const updateScheduledReport = async (scheduleId, updates) => {
  const response = await apiClient.put(`/analyst/scheduled-reports/${scheduleId}`, null, { params: updates });
  return response.data;
};

/**
 * Delete scheduled report
 */
export const deleteScheduledReport = async (scheduleId) => {
  const response = await apiClient.delete(`/analyst/scheduled-reports/${scheduleId}`);
  return response.data;
};

/**
 * Run scheduled report manually
 */
export const runScheduledReport = async (scheduleId) => {
  const response = await apiClient.post(`/analyst/scheduled-reports/${scheduleId}/run`);
  return response.data;
};

// ==================== ANALYST API KEYS ====================

/**
 * Get API keys
 */
export const getApiKeys = async () => {
  const response = await apiClient.get('/analyst/api-keys');
  return response.data;
};

/**
 * Create API key
 */
export const createApiKey = async (keyConfig) => {
  const response = await apiClient.post('/analyst/api-keys', keyConfig);
  return response.data;
};

/**
 * Revoke API key
 */
export const revokeApiKey = async (keyId) => {
  const response = await apiClient.delete(`/analyst/api-keys/${keyId}`);
  return response.data;
};

// ==================== REPORT ENRICHMENT API ====================

/**
 * Get enrichment service health status
 */
export const getEnrichmentHealth = async () => {
  const response = await apiClient.get('/enrichment/health');
  return response.data;
};

/**
 * Fetch weather data for coordinates
 */
export const fetchWeatherData = async (latitude, longitude) => {
  const response = await apiClient.post('/enrichment/weather', { latitude, longitude });
  return response.data;
};

/**
 * Fetch marine/ocean data for coordinates
 */
export const fetchMarineData = async (latitude, longitude) => {
  const response = await apiClient.post('/enrichment/marine', { latitude, longitude });
  return response.data;
};

/**
 * Fetch astronomy data for coordinates
 */
export const fetchAstronomyData = async (latitude, longitude) => {
  const response = await apiClient.post('/enrichment/astronomy', { latitude, longitude });
  return response.data;
};

/**
 * Fetch seismic/earthquake data near coordinates
 */
export const fetchSeismicData = async (latitude, longitude, options = {}) => {
  const response = await apiClient.post('/enrichment/seismic', {
    latitude,
    longitude,
    radius_km: options.radiusKm || 500,
    lookback_days: options.lookbackDays || 7,
    min_magnitude: options.minMagnitude || 3.0
  });
  return response.data;
};

/**
 * Fetch complete environmental data snapshot for coordinates
 */
export const fetchEnvironmentalData = async (latitude, longitude) => {
  const response = await apiClient.post('/enrichment/environmental', { latitude, longitude });
  return response.data;
};

/**
 * Classify threat levels from environmental data
 */
export const classifyThreat = async (environmentalSnapshot, reportedHazardType = null) => {
  const response = await apiClient.post('/enrichment/classify', {
    environmental_snapshot: environmentalSnapshot,
    reported_hazard_type: reportedHazardType
  });
  return response.data;
};

/**
 * Execute full enrichment pipeline: fetch environmental data + classify threats
 * Main endpoint for report submission enrichment
 */
export const getFullEnrichment = async (latitude, longitude, reportedHazardType = null) => {
  const response = await apiClient.post('/enrichment/full', {
    latitude,
    longitude,
    reported_hazard_type: reportedHazardType
  });
  return response.data;
};

/**
 * Enrich an existing report with environmental data (Analyst+)
 */
export const enrichReport = async (reportId) => {
  const response = await apiClient.post(`/enrichment/report/${reportId}/enrich`);
  return response.data;
};

/**
 * Batch enrich multiple reports (Analyst+)
 */
export const batchEnrichReports = async (reportIds) => {
  const response = await apiClient.post('/enrichment/report/batch-enrich', null, {
    params: { report_ids: reportIds }
  });
  return response.data;
};

/**
 * Get classification thresholds (Analyst+)
 */
export const getClassificationThresholds = async () => {
  const response = await apiClient.get('/enrichment/thresholds');
  return response.data;
};

// ==================== VECTORDB API (Spam Detection) ====================

/**
 * Get VectorDB service health status
 */
export const getVectorDBHealth = async () => {
  const response = await apiClient.get('/vectordb/health');
  return response.data;
};

/**
 * Query VectorDB for similar reports
 */
export const queryVectorDB = async (text, options = {}) => {
  const response = await apiClient.post('/vectordb/query', {
    text,
    k: options.k || 5,
    filter_type: options.filterType || null
  });
  return response.data;
};

/**
 * Classify text for spam/hazard detection
 */
export const classifyText = async (text, hazardType = null) => {
  const response = await apiClient.post('/vectordb/classify', {
    text,
    hazard_type: hazardType
  });
  return response.data;
};

/**
 * Get VectorDB statistics
 */
export const getVectorDBStats = async () => {
  const response = await apiClient.get('/vectordb/stats');
  return response.data;
};

/**
 * Add sample to VectorDB index (Admin)
 */
export const addVectorDBSample = async (text, label, metadata = {}) => {
  const response = await apiClient.post('/vectordb/add', {
    text,
    label,
    metadata
  });
  return response.data;
};

/**
 * Rebuild VectorDB index (Admin)
 */
export const rebuildVectorDBIndex = async () => {
  const response = await apiClient.post('/vectordb/rebuild');
  return response.data;
};

// ==================== MULTI-HAZARD DETECTION API ====================

/**
 * Get MultiHazard service health status
 */
export const getMultiHazardHealth = async () => {
  const response = await apiClient.get('/multi-hazard/health');
  return response.data;
};

/**
 * Get full monitoring status (authenticated - includes all location details)
 */
export const getMultiHazardStatus = async () => {
  const response = await apiClient.get('/multi-hazard/status');
  return response.data;
};

/**
 * Get monitoring summary (lightweight)
 */
export const getMultiHazardSummary = async () => {
  const response = await apiClient.get('/multi-hazard/summary');
  return response.data;
};

/**
 * Get detailed status for a specific location
 */
export const getMultiHazardLocationStatus = async (locationId) => {
  const response = await apiClient.get(`/multi-hazard/locations/${locationId}`);
  return response.data;
};

/**
 * Get public locations list (no auth required)
 */
export const getMultiHazardPublicLocations = async () => {
  const response = await apiClient.get('/multi-hazard/public/locations');
  return response.data;
};

/**
 * Get public status summary (no auth required)
 */
export const getMultiHazardPublicStatus = async () => {
  const response = await apiClient.get('/multi-hazard/public/status');
  return response.data;
};

/**
 * Get public alerts (no auth required)
 */
export const getMultiHazardPublicAlerts = async (options = {}) => {
  const response = await apiClient.get('/multi-hazard/public/alerts', {
    params: {
      min_level: options.minLevel || 1,
      limit: options.limit || 20
    }
  });
  return response.data;
};

/**
 * Get recent earthquakes from multi-hazard service
 */
export const getMultiHazardEarthquakes = async () => {
  const response = await apiClient.get('/multi-hazard/earthquakes');
  return response.data;
};

/**
 * Force refresh detection cycle (admin)
 */
export const refreshMultiHazardDetection = async (locationIds = null) => {
  const response = await apiClient.post('/multi-hazard/refresh', {
    location_ids: locationIds
  });
  return response.data;
};

/**
 * Detect hazards for a specific location
 */
export const detectHazards = async (latitude, longitude, options = {}) => {
  const response = await apiClient.post('/multi-hazard/detect', {
    latitude,
    longitude,
    radius_km: options.radiusKm || 50,
    include_forecast: options.includeForecast !== false
  });
  return response.data;
};

/**
 * Get active hazard alerts (requires analyst role)
 */
export const getMultiHazardAlerts = async (options = {}) => {
  const response = await apiClient.get('/multi-hazard/alerts', {
    params: {
      min_severity: options.minSeverity || null,
      hazard_type: options.hazardType || null,
      limit: options.limit || 50
    }
  });
  return response.data;
};

/**
 * Get cyclone and storm surge data for map visualization
 * Returns INCOIS-style cyclone tracking data
 */
export const getCycloneData = async (options = {}) => {
  const response = await apiClient.get('/multi-hazard/public/cyclone-data', {
    params: {
      include_forecast: options.includeForecast !== false,
      include_surge: options.includeSurge !== false,
      include_demo: options.includeDemo !== false,
    }
  });
  return response.data;
};

/**
 * Get storm surge color legend configuration
 */
export const getSurgeLegend = async () => {
  const response = await apiClient.get('/multi-hazard/public/surge-legend');
  return response.data;
};

/**
 * Get public hazard alerts (no auth required - for citizen dashboard)
 */
export const getPublicHazardAlerts = async (options = {}) => {
  const response = await apiClient.get('/multi-hazard/public/alerts', {
    params: {
      min_level: options.minLevel || 2,
      limit: options.limit || 20
    }
  });
  return response.data;
};

/**
 * Get hazard summary for a region
 */
export const getHazardSummary = async (latitude, longitude, radiusKm = 100) => {
  const response = await apiClient.get('/multi-hazard/summary', {
    params: { latitude, longitude, radius_km: radiusKm }
  });
  return response.data;
};

/**
 * Get historical hazard data
 */
export const getHazardHistory = async (options = {}) => {
  const response = await apiClient.get('/multi-hazard/history', {
    params: {
      latitude: options.latitude,
      longitude: options.longitude,
      days: options.days || 30,
      hazard_type: options.hazardType || null
    }
  });
  return response.data;
};

/**
 * Subscribe to hazard alerts for a location
 */
export const subscribeHazardAlerts = async (latitude, longitude, options = {}) => {
  const response = await apiClient.post('/multi-hazard/subscribe', {
    latitude,
    longitude,
    radius_km: options.radiusKm || 50,
    hazard_types: options.hazardTypes || null,
    min_severity: options.minSeverity || 'watch'
  });
  return response.data;
};

/**
 * Unsubscribe from hazard alerts
 */
export const unsubscribeHazardAlerts = async (subscriptionId) => {
  const response = await apiClient.delete(`/multi-hazard/subscribe/${subscriptionId}`);
  return response.data;
};

// ==================== UTILITY FUNCTIONS ====================

/**
 * Get color class for threat level
 */
export const getThreatLevelColor = (threatLevel) => {
  const colors = {
    warning: { bg: 'bg-red-100', text: 'text-red-800', border: 'border-red-500', badge: 'bg-red-500' },
    alert: { bg: 'bg-orange-100', text: 'text-orange-800', border: 'border-orange-500', badge: 'bg-orange-500' },
    watch: { bg: 'bg-yellow-100', text: 'text-yellow-800', border: 'border-yellow-500', badge: 'bg-yellow-500' },
    no_threat: { bg: 'bg-green-100', text: 'text-green-800', border: 'border-green-500', badge: 'bg-green-500' }
  };
  return colors[threatLevel?.toLowerCase()] || colors.no_threat;
};

/**
 * Get threat level display info
 */
export const getThreatLevelInfo = (threatLevel) => {
  const info = {
    warning: {
      label: 'WARNING',
      icon: 'AlertTriangle',
      description: 'Hazard is currently occurring or imminent',
      priority: 1
    },
    alert: {
      label: 'ALERT',
      icon: 'AlertCircle',
      description: 'Hazard will likely occur soon',
      priority: 2
    },
    watch: {
      label: 'WATCH',
      icon: 'Eye',
      description: 'Conditions are favorable for hazard development',
      priority: 3
    },
    no_threat: {
      label: 'NO THREAT',
      icon: 'CheckCircle',
      description: 'No significant hazard detected',
      priority: 4
    }
  };
  return info[threatLevel?.toLowerCase()] || info.no_threat;
};

/**
 * Get hazard type display info
 */
export const getHazardTypeInfo = (hazardType) => {
  const info = {
    tsunami: { label: 'Tsunami', icon: 'Waves', color: 'blue' },
    cyclone: { label: 'Cyclone', icon: 'Wind', color: 'purple' },
    high_waves: { label: 'High Waves', icon: 'Waves', color: 'cyan' },
    coastal_flood: { label: 'Coastal Flood', icon: 'Droplets', color: 'teal' },
    rip_current: { label: 'Rip Current', icon: 'ArrowDownRight', color: 'indigo' },
    earthquake: { label: 'Earthquake', icon: 'Activity', color: 'orange' },
    storm_surge: { label: 'Storm Surge', icon: 'CloudRain', color: 'slate' }
  };
  return info[hazardType?.toLowerCase()] || { label: hazardType || 'Unknown', icon: 'HelpCircle', color: 'gray' };
};

/**
 * Format environmental data for display
 */
export const formatEnvironmentalData = (snapshot) => {
  if (!snapshot) return null;

  const formatted = {
    weather: null,
    marine: null,
    seismic: null,
    astronomy: null
  };

  if (snapshot.weather) {
    formatted.weather = {
      temperature: `${snapshot.weather.temp_c}°C`,
      feelsLike: `${snapshot.weather.feelslike_c}°C`,
      wind: `${snapshot.weather.wind_kph} km/h ${snapshot.weather.wind_dir}`,
      gusts: snapshot.weather.gust_kph ? `${snapshot.weather.gust_kph} km/h` : null,
      pressure: `${snapshot.weather.pressure_mb} mb`,
      humidity: `${snapshot.weather.humidity}%`,
      visibility: `${snapshot.weather.vis_km} km`,
      condition: snapshot.weather.condition,
      precipitation: `${snapshot.weather.precip_mm} mm`
    };
  }

  if (snapshot.marine) {
    formatted.marine = {
      waveHeight: snapshot.marine.sig_ht_mt ? `${snapshot.marine.sig_ht_mt} m` : null,
      swellHeight: snapshot.marine.swell_ht_mt ? `${snapshot.marine.swell_ht_mt} m` : null,
      swellPeriod: snapshot.marine.swell_period_secs ? `${snapshot.marine.swell_period_secs} sec` : null,
      swellDirection: snapshot.marine.swell_dir_16_point,
      waterTemp: snapshot.marine.water_temp_c ? `${snapshot.marine.water_temp_c}°C` : null,
      tideType: snapshot.marine.tide_type,
      tideHeight: snapshot.marine.tide_height_mt ? `${snapshot.marine.tide_height_mt} m` : null
    };
  }

  if (snapshot.seismic) {
    formatted.seismic = {
      magnitude: snapshot.seismic.magnitude ? `M${snapshot.seismic.magnitude}` : null,
      depth: snapshot.seismic.depth_km ? `${snapshot.seismic.depth_km} km` : null,
      distance: snapshot.seismic.distance_km ? `${snapshot.seismic.distance_km} km away` : null,
      location: snapshot.seismic.place,
      tsunamiWarning: snapshot.seismic.tsunami === 1
    };
  }

  if (snapshot.astronomy) {
    formatted.astronomy = {
      sunrise: snapshot.astronomy.sunrise,
      sunset: snapshot.astronomy.sunset,
      moonPhase: snapshot.astronomy.moon_phase,
      isDay: snapshot.astronomy.is_day
    };
  }

  return formatted;
};

// ==================== TICKET API FUNCTIONS ====================

/**
 * Get all tickets (filtered by user role on backend)
 */
export const getTickets = async (options = {}) => {
  const params = new URLSearchParams();
  if (options.status) params.append('status', options.status);
  if (options.priority) params.append('priority', options.priority);
  if (options.page) params.append('page', options.page);
  if (options.pageSize) params.append('page_size', options.pageSize);

  const response = await apiClient.get(`/tickets?${params.toString()}`);
  return response.data;
};

/**
 * Get ticket queue for analysts/authorities
 */
export const getTicketQueue = async (options = {}) => {
  const params = new URLSearchParams();
  if (options.status) params.append('status', options.status);
  if (options.priority) params.append('priority', options.priority);
  if (options.limit) params.append('limit', options.limit);

  const response = await apiClient.get(`/tickets/queue?${params.toString()}`);
  return response.data;
};

/**
 * Get my tickets (for reporters/citizens)
 */
export const getMyTickets = async (options = {}) => {
  const params = new URLSearchParams();
  if (options.status) params.append('status', options.status);
  if (options.page) params.append('page', options.page);
  if (options.pageSize) params.append('page_size', options.pageSize);

  const response = await apiClient.get(`/tickets/my/tickets?${params.toString()}`);
  return response.data;
};

/**
 * Get ticket detail by ID
 */
export const getTicketDetail = async (ticketId) => {
  const response = await apiClient.get(`/tickets/${ticketId}`);
  return response.data;
};

/**
 * Create a new ticket from a verified report
 */
export const createTicket = async (data) => {
  const response = await apiClient.post('/tickets', data);
  return response.data;
};

/**
 * Assign ticket to an analyst
 */
export const assignTicket = async (ticketId, data) => {
  const response = await apiClient.post(`/tickets/${ticketId}/assign`, data);
  return response.data;
};

/**
 * Update ticket status
 */
export const updateTicketStatus = async (ticketId, data) => {
  const response = await apiClient.patch(`/tickets/${ticketId}/status`, data);
  return response.data;
};

/**
 * Update ticket priority
 */
export const updateTicketPriority = async (ticketId, data) => {
  const response = await apiClient.put(`/tickets/${ticketId}/priority`, data);
  return response.data;
};

/**
 * Escalate a ticket
 */
export const escalateTicket = async (ticketId, data) => {
  const response = await apiClient.post(`/tickets/${ticketId}/escalate`, data);
  return response.data;
};

/**
 * Resolve a ticket
 */
export const resolveTicket = async (ticketId, data) => {
  const response = await apiClient.post(`/tickets/${ticketId}/resolve`, data);
  return response.data;
};

/**
 * Close a ticket
 */
export const closeTicket = async (ticketId, reason = null) => {
  const response = await apiClient.post(`/tickets/${ticketId}/close`, null, {
    params: reason ? { reason } : {}
  });
  return response.data;
};

/**
 * Reopen a ticket
 */
export const reopenTicket = async (ticketId, reason) => {
  const response = await apiClient.post(`/tickets/${ticketId}/reopen`, null, {
    params: { reason }
  });
  return response.data;
};

/**
 * Send a message in a ticket
 */
export const sendTicketMessage = async (ticketId, data) => {
  const response = await apiClient.post(`/tickets/${ticketId}/messages`, data);
  return response.data;
};

/**
 * Get messages for a ticket
 */
export const getTicketMessages = async (ticketId, options = {}) => {
  const params = new URLSearchParams();
  if (options.limit) params.append('limit', options.limit);
  if (options.beforeMessageId) params.append('before_message_id', options.beforeMessageId);

  const response = await apiClient.get(`/tickets/${ticketId}/messages?${params.toString()}`);
  return response.data;
};

/**
 * Submit feedback for a ticket
 */
export const submitTicketFeedback = async (ticketId, data) => {
  const response = await apiClient.post(`/tickets/${ticketId}/feedback`, data);
  return response.data;
};

/**
 * Get ticket statistics
 */
export const getTicketStats = async (days = 7) => {
  const response = await apiClient.get(`/tickets/stats/summary?days=${days}`);
  return response.data;
};

/**
 * Get ticket health check
 */
export const getTicketHealth = async () => {
  const response = await apiClient.get('/tickets/health');
  return response.data;
};

// ==================== VERIFICATION API FUNCTIONS ====================

/**
 * Get verification queue (reports needing manual review)
 */
export const getVerificationQueue = async (options = {}) => {
  const params = new URLSearchParams();
  if (options.limit) params.append('limit', options.limit);
  if (options.offset) params.append('offset', options.offset);

  const response = await apiClient.get(`/verification/queue?${params.toString()}`);
  return response.data;
};

/**
 * Get verification details for a report
 */
export const getVerificationDetails = async (reportId) => {
  const response = await apiClient.get(`/verification/${reportId}`);
  return response.data;
};

/**
 * Make analyst decision on a report
 */
export const makeVerificationDecision = async (reportId, data) => {
  const response = await apiClient.post(`/verification/${reportId}/decide`, data);
  return response.data;
};

/**
 * Re-run verification pipeline on a report
 */
export const rerunVerification = async (reportId) => {
  const response = await apiClient.post(`/verification/${reportId}/rerun`);
  return response.data;
};

/**
 * Get verification statistics
 */
export const getVerificationStats = async (days = 7) => {
  const response = await apiClient.get(`/verification/stats?days=${days}`);
  return response.data;
};

/**
 * Get verification thresholds
 */
export const getVerificationThresholds = async () => {
  const response = await apiClient.get('/verification/thresholds');
  return response.data;
};

/**
 * Get verification health check
 */
export const getVerificationHealth = async () => {
  const response = await apiClient.get('/verification/health');
  return response.data;
};

/**
 * Backfill tickets for verified reports that don't have tickets
 * @param {boolean} dryRun - If true, only count reports without creating tickets
 * @param {number} limit - Maximum number of reports to process
 */
export const backfillTickets = async (dryRun = true, limit = 100) => {
  const response = await apiClient.post(`/verification/backfill-tickets?dry_run=${dryRun}&limit=${limit}`);
  return response.data;
};

/**
 * Manually create a ticket for a verified report
 * @param {string} reportId - The report ID to create a ticket for
 */
export const createTicketForReport = async (reportId) => {
  const response = await apiClient.post(`/verification/${reportId}/create-ticket`);
  return response.data;
};

// ============================================================
// Ocean Data API
// ============================================================

/**
 * Get real-time ocean wave and current data
 * Uses Open-Meteo Marine API for wave heights
 * @param {Object} options - Options for fetching ocean data
 * @param {boolean} options.includeWaves - Include wave height data (default: true)
 * @param {boolean} options.includeCurrents - Include ocean current data (default: true)
 */
export const getOceanData = async (options = {}) => {
  const { includeWaves = true, includeCurrents = true } = options;
  const response = await apiClient.get('/hazards/ocean-data', {
    params: {
      include_waves: includeWaves,
      include_currents: includeCurrents,
    },
  });
  return response.data;
};

// ============================================================
// Organizer API - Application & Verification
// ============================================================

/**
 * Check if current user is eligible to apply as organizer
 * Requires credibility >= 80, no pending application
 */
export const checkOrganizerEligibility = async () => {
  const response = await apiClient.get('/organizer/eligibility');
  return response.data;
};

/**
 * Get list of Indian coastal zones and states for application form
 */
export const getCoastalZones = async () => {
  const response = await apiClient.get('/organizer/zones');
  return response.data;
};

/**
 * Submit organizer application with Aadhaar document
 * @param {FormData} formData - Form data with name, email, phone, coastal_zone, state, aadhaar_document
 */
export const submitOrganizerApplication = async (formData) => {
  const response = await apiClient.post('/organizer/apply', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  });
  return response.data;
};

/**
 * Get current user's organizer application status
 */
export const getOrganizerApplicationStatus = async () => {
  const response = await apiClient.get('/organizer/application-status');
  return response.data;
};

// ============================================================
// Organizer Admin API - Application Review
// ============================================================

/**
 * Admin: Get list of organizer applications
 * @param {Object} params - Query parameters
 * @param {string} params.status - Filter by status: pending, approved, rejected
 * @param {number} params.skip - Pagination offset
 * @param {number} params.limit - Number of results
 */
export const getOrganizerApplications = async (params = {}) => {
  const response = await apiClient.get('/organizer/admin/applications', { params });
  return response.data;
};

/**
 * Admin: Get detailed organizer application by ID
 * @param {string} applicationId - Application ID
 */
export const getOrganizerApplicationDetail = async (applicationId) => {
  const response = await apiClient.get(`/organizer/admin/applications/${applicationId}`);
  return response.data;
};

/**
 * Admin: Get Aadhaar document URL for an application
 * @param {string} applicationId - Application ID
 */
export const getAadhaarDocumentUrl = (applicationId) => {
  const token = Cookies.get('access_token');
  return `${API_BASE_URL}/organizer/admin/applications/${applicationId}/aadhaar?token=${token}`;
};

/**
 * Admin: Approve an organizer application
 * @param {string} applicationId - Application ID to approve
 */
export const approveOrganizerApplication = async (applicationId) => {
  const response = await apiClient.post(`/organizer/admin/applications/${applicationId}/approve`);
  return response.data;
};

/**
 * Admin: Reject an organizer application
 * @param {string} applicationId - Application ID to reject
 * @param {string} rejectionReason - Reason for rejection
 */
export const rejectOrganizerApplication = async (applicationId, rejectionReason) => {
  const response = await apiClient.post(`/organizer/admin/applications/${applicationId}/reject`, {
    rejection_reason: rejectionReason,
  });
  return response.data;
};

/**
 * Admin: Get organizer statistics for dashboard
 */
export const getOrganizerStatistics = async () => {
  const response = await apiClient.get('/organizer/admin/statistics');
  return response.data;
};

// ============================================================
// Community API - Browse, Join, Leave
// ============================================================

/**
 * List communities with optional filters
 * @param {Object} params - Query parameters
 * @param {string} params.coastal_zone - Filter by coastal zone
 * @param {string} params.state - Filter by state
 * @param {string} params.category - Filter by category
 * @param {string} params.search - Search by name/description
 * @param {number} params.skip - Pagination offset
 * @param {number} params.limit - Number of results
 */
export const listCommunities = async (params = {}) => {
  const response = await apiClient.get('/communities', { params });
  return response.data;
};

/**
 * Get filter options for communities (zones, states, categories)
 */
export const getCommunityFilterOptions = async () => {
  const response = await apiClient.get('/communities/filters');
  return response.data;
};

/**
 * Get community details by ID
 * @param {string} communityId - Community ID
 */
export const getCommunityById = async (communityId) => {
  const response = await apiClient.get(`/communities/${communityId}`);
  return response.data;
};

/**
 * Get members of a community
 * @param {string} communityId - Community ID
 * @param {number} skip - Pagination offset
 * @param {number} limit - Number of results
 */
export const getCommunityMembers = async (communityId, skip = 0, limit = 50) => {
  const response = await apiClient.get(`/communities/${communityId}/members`, {
    params: { skip, limit }
  });
  return response.data;
};

/**
 * Get communities the current user is a member of
 */
export const getMyCommunities = async (skip = 0, limit = 20) => {
  const response = await apiClient.get('/communities/my/communities', {
    params: { skip, limit }
  });
  return response.data;
};

/**
 * Get communities organized by the current user
 */
export const getMyOrganizedCommunities = async (skip = 0, limit = 20) => {
  const response = await apiClient.get('/communities/my/organized', {
    params: { skip, limit }
  });
  return response.data;
};

/**
 * Join a community
 * @param {string} communityId - Community ID to join
 */
export const joinCommunity = async (communityId) => {
  const response = await apiClient.post(`/communities/${communityId}/join`);
  return response.data;
};

/**
 * Leave a community
 * @param {string} communityId - Community ID to leave
 */
export const leaveCommunity = async (communityId) => {
  const response = await apiClient.post(`/communities/${communityId}/leave`);
  return response.data;
};

/**
 * Create a new community (requires organizer role)
 * @param {Object} communityData - Community data
 */
export const createCommunity = async (communityData) => {
  const response = await apiClient.post('/communities', communityData);
  return response.data;
};

/**
 * Update a community
 * @param {string} communityId - Community ID
 * @param {Object} updateData - Update data
 */
export const updateCommunity = async (communityId, updateData) => {
  const response = await apiClient.put(`/communities/${communityId}`, updateData);
  return response.data;
};

/**
 * Delete a community
 * @param {string} communityId - Community ID
 */
export const deleteCommunity = async (communityId) => {
  const response = await apiClient.delete(`/communities/${communityId}`);
  return response.data;
};

/**
 * Upload community image (cover or logo)
 * @param {string} communityId - Community ID
 * @param {File} file - Image file
 * @param {string} imageType - 'cover' or 'logo'
 */
export const uploadCommunityImage = async (communityId, file, imageType = 'cover') => {
  const formData = new FormData();
  formData.append('file', file);
  // Don't set Content-Type header - axios will set it automatically with proper boundary
  const response = await apiClient.post(
    `/communities/${communityId}/upload-image?image_type=${imageType}`,
    formData
  );
  return response.data;
};

// ============================================================
// Events API - Event Management & Registration
// ============================================================

/**
 * Get filter options for events (zones, event types, statuses)
 */
export const getEventFilterOptions = async () => {
  const response = await apiClient.get('/events/filters');
  return response.data;
};

/**
 * List events with optional filters
 * @param {Object} params - Query parameters
 * @param {string} params.community_id - Filter by community
 * @param {string} params.coastal_zone - Filter by coastal zone
 * @param {string} params.event_type - Filter by event type
 * @param {string} params.status - Filter by status
 * @param {boolean} params.is_emergency - Filter emergency events
 * @param {boolean} params.upcoming_only - Show only upcoming events
 * @param {number} params.skip - Pagination offset
 * @param {number} params.limit - Number of results
 */
export const listEvents = async (params = {}) => {
  const response = await apiClient.get('/events', { params });
  return response.data;
};

/**
 * Get events for a specific community
 * @param {string} communityId - Community ID
 * @param {number} skip - Pagination offset
 * @param {number} limit - Number of results
 * @param {string} status - Filter by status (e.g., 'completed')
 */
export const getCommunityEvents = async (communityId, skip = 0, limit = 20, status = null) => {
  const params = { community_id: communityId, skip, limit };
  if (status) {
    params.status = status;
  }
  const response = await apiClient.get('/events', { params });
  return response.data;
};

/**
 * Get event details by ID
 * @param {string} eventId - Event ID
 */
export const getEventById = async (eventId) => {
  const response = await apiClient.get(`/events/${eventId}`);
  return response.data;
};

/**
 * Get events the current user is registered for
 */
export const getMyEvents = async (skip = 0, limit = 20) => {
  const response = await apiClient.get('/events/my/events', {
    params: { skip, limit }
  });
  return response.data;
};

/**
 * Get events organized by the current user
 */
export const getMyOrganizedEvents = async (skip = 0, limit = 20) => {
  const response = await apiClient.get('/events/my/organized', {
    params: { skip, limit }
  });
  return response.data;
};

/**
 * Create a new event (requires organizer role)
 * @param {Object} eventData - Event data
 */
export const createEvent = async (eventData) => {
  const response = await apiClient.post('/events', eventData);
  return response.data;
};

/**
 * Update an event
 * @param {string} eventId - Event ID
 * @param {Object} updateData - Update data
 */
export const updateEvent = async (eventId, updateData) => {
  const response = await apiClient.put(`/events/${eventId}`, updateData);
  return response.data;
};

/**
 * Cancel an event
 * @param {string} eventId - Event ID
 */
export const cancelEvent = async (eventId) => {
  const response = await apiClient.post(`/events/${eventId}/cancel`);
  return response.data;
};

/**
 * Register for an event
 * @param {string} eventId - Event ID to register for
 */
export const registerForEvent = async (eventId) => {
  const response = await apiClient.post(`/events/${eventId}/register`);
  return response.data;
};

/**
 * Unregister from an event
 * @param {string} eventId - Event ID to unregister from
 */
export const unregisterFromEvent = async (eventId) => {
  const response = await apiClient.delete(`/events/${eventId}/register`);
  return response.data;
};

/**
 * Check registration status for an event
 * @param {string} eventId - Event ID
 */
export const checkEventRegistration = async (eventId) => {
  const response = await apiClient.get(`/events/${eventId}/registration-status`);
  return response.data;
};

/**
 * Get all registrations for an event (organizer only)
 * @param {string} eventId - Event ID
 * @param {number} skip - Pagination offset
 * @param {number} limit - Number of results
 */
export const getEventRegistrations = async (eventId, skip = 0, limit = 100) => {
  const response = await apiClient.get(`/events/${eventId}/registrations`, {
    params: { skip, limit }
  });
  return response.data;
};

/**
 * Mark attendance for event participants (organizer only)
 * @param {string} eventId - Event ID
 * @param {string[]} userIds - Array of user IDs to mark as attended
 */
export const markEventAttendance = async (eventId, userIds) => {
  const response = await apiClient.post(`/events/${eventId}/mark-attendance`, {
    user_ids: userIds
  });
  return response.data;
};

/**
 * Mark an event as completed (organizer only)
 * @param {string} eventId - Event ID
 */
export const completeEvent = async (eventId) => {
  const response = await apiClient.post(`/events/${eventId}/complete`);
  return response.data;
};

// ============================================================
// Points & Gamification API
// ============================================================

/**
 * Get current user's points and badges
 */
export const getMyPoints = async () => {
  const response = await apiClient.get('/events/points/my');
  return response.data;
};

/**
 * Get points leaderboard
 * @param {number} skip - Pagination offset
 * @param {number} limit - Number of results (default: 10)
 */
export const getLeaderboard = async (skip = 0, limit = 10) => {
  const response = await apiClient.get('/events/points/leaderboard', {
    params: { skip, limit }
  });
  return response.data;
};

/**
 * Get current user's rank on the leaderboard
 */
export const getMyRank = async () => {
  const response = await apiClient.get('/events/points/my-rank');
  return response.data;
};

/**
 * Get all available badges
 */
export const getAllBadges = async () => {
  const response = await apiClient.get('/events/points/badges');
  return response.data;
};

// ============================================================
// Event Type & Status Helpers
// ============================================================

/**
 * Get event type display info
 */
export const getEventTypeInfo = (eventType) => {
  const info = {
    beach_cleanup: { label: 'Beach Cleanup', icon: 'Trash2', color: 'blue' },
    mangrove_plantation: { label: 'Mangrove Plantation', icon: 'Trees', color: 'green' },
    awareness_drive: { label: 'Awareness Drive', icon: 'Megaphone', color: 'purple' },
    rescue_operation: { label: 'Rescue Operation', icon: 'LifeBuoy', color: 'red' },
    training_workshop: { label: 'Training Workshop', icon: 'GraduationCap', color: 'amber' },
    emergency_response: { label: 'Emergency Response', icon: 'AlertTriangle', color: 'rose' },
  };
  return info[eventType?.toLowerCase()] || { label: eventType || 'Unknown', icon: 'Calendar', color: 'gray' };
};

/**
 * Get event status display info
 */
export const getEventStatusInfo = (status) => {
  const info = {
    draft: { label: 'Draft', color: 'gray', bgColor: 'bg-gray-100', textColor: 'text-gray-700' },
    published: { label: 'Published', color: 'blue', bgColor: 'bg-blue-100', textColor: 'text-blue-700' },
    ongoing: { label: 'Ongoing', color: 'green', bgColor: 'bg-green-100', textColor: 'text-green-700' },
    completed: { label: 'Completed', color: 'emerald', bgColor: 'bg-emerald-100', textColor: 'text-emerald-700' },
    cancelled: { label: 'Cancelled', color: 'red', bgColor: 'bg-red-100', textColor: 'text-red-700' },
  };
  return info[status?.toLowerCase()] || { label: status || 'Unknown', color: 'gray', bgColor: 'bg-gray-100', textColor: 'text-gray-700' };
};

/**
 * Get badge display info
 */
export const getBadgeInfo = (badgeId) => {
  const badges = {
    first_timer: { name: 'First Timer', icon: 'Star', color: 'amber', description: 'Attended your first volunteer event' },
    active_volunteer: { name: 'Active Volunteer', icon: 'Award', color: 'blue', description: 'Attended 3 volunteer events' },
    ocean_defender: { name: 'Ocean Defender', icon: 'Shield', color: 'cyan', description: 'Attended 5 volunteer events' },
    beach_warrior: { name: 'Beach Warrior', icon: 'Trophy', color: 'yellow', description: 'Attended 10 volunteer events' },
    super_volunteer: { name: 'Super Volunteer', icon: 'Crown', color: 'purple', description: 'Attended 25 volunteer events' },
    emergency_responder: { name: 'Emergency Responder', icon: 'AlertTriangle', color: 'red', description: 'Responded to an emergency event' },
    community_builder: { name: 'Community Builder', icon: 'Users', color: 'green', description: 'Organized 5 events' },
  };
  return badges[badgeId] || { name: badgeId, icon: 'Award', color: 'gray', description: 'Achievement unlocked' };
};

// ============================================================
// Certificate API
// ============================================================

/**
 * Generate certificate for an event
 * @param {string} eventId - Event ID
 */
export const generateCertificate = async (eventId) => {
  const response = await apiClient.post(`/certificates/events/${eventId}/generate`);
  return response.data;
};

/**
 * Download certificate for an event
 * @param {string} eventId - Event ID
 */
export const downloadEventCertificate = async (eventId) => {
  const response = await apiClient.get(`/certificates/events/${eventId}/download`, {
    responseType: 'blob'
  });
  return response.data;
};

/**
 * Email certificate to user
 * @param {string} eventId - Event ID
 */
export const emailCertificate = async (eventId) => {
  const response = await apiClient.post(`/certificates/events/${eventId}/email`);
  return response.data;
};

/**
 * Get all certificates for current user
 * @param {number} skip - Pagination offset
 * @param {number} limit - Number of results
 */
export const getMyCertificates = async (skip = 0, limit = 20) => {
  const response = await apiClient.get('/certificates/my', {
    params: { skip, limit }
  });
  return response.data;
};

/**
 * Verify a certificate (public)
 * @param {string} certificateId - Certificate ID
 */
export const verifyCertificate = async (certificateId) => {
  const response = await apiClient.get(`/certificates/${certificateId}/verify`);
  return response.data;
};

/**
 * Download certificate by ID
 * @param {string} certificateId - Certificate ID
 */
export const downloadCertificateById = async (certificateId) => {
  const response = await apiClient.get(`/certificates/${certificateId}/download`, {
    responseType: 'blob'
  });
  return response.data;
};

// ============================================================
// Event Photos API
// ============================================================

/**
 * Upload a photo to an event
 * @param {string} eventId - Event ID
 * @param {File} file - Image file
 * @param {string} caption - Optional caption
 */
export const uploadEventPhoto = async (eventId, file, caption = '') => {
  const formData = new FormData();
  formData.append('file', file);
  if (caption) {
    formData.append('caption', caption);
  }

  const response = await apiClient.post(`/events/${eventId}/photos`, formData, {
    headers: {
      'Content-Type': 'multipart/form-data'
    }
  });
  return response.data;
};

/**
 * Get photos for an event
 * @param {string} eventId - Event ID
 * @param {number} skip - Pagination offset
 * @param {number} limit - Max items
 * @param {boolean} includeHidden - Include hidden photos (organizers only)
 */
export const getEventPhotos = async (eventId, skip = 0, limit = 20, includeHidden = false) => {
  const response = await apiClient.get(`/events/${eventId}/photos`, {
    params: { skip, limit, include_hidden: includeHidden }
  });
  return response.data;
};

/**
 * Delete an event photo
 * @param {string} eventId - Event ID
 * @param {string} photoId - Photo ID
 */
export const deleteEventPhoto = async (eventId, photoId) => {
  const response = await apiClient.delete(`/events/${eventId}/photos/${photoId}`);
  return response.data;
};

/**
 * Toggle photo visibility (organizer moderation)
 * @param {string} eventId - Event ID
 * @param {string} photoId - Photo ID
 * @param {boolean} hide - True to hide, false to show
 */
export const togglePhotoVisibility = async (eventId, photoId, hide = true) => {
  const response = await apiClient.post(`/events/${eventId}/photos/${photoId}/visibility`, { hide });
  return response.data;
};

/**
 * Get all photos uploaded by current user
 * @param {number} skip - Pagination offset
 * @param {number} limit - Max items
 */
export const getMyPhotos = async (skip = 0, limit = 20) => {
  const response = await apiClient.get('/events/photos/my', {
    params: { skip, limit }
  });
  return response.data;
};

// ============================================================
// Community Posts API
// ============================================================

/**
 * Create a new community post
 * @param {string} communityId - Community ID
 * @param {string} content - Post content
 * @param {string} postType - "general", "announcement", or "event_recap"
 * @param {string} relatedEventId - Event ID for event recaps
 * @param {File[]} photos - Array of photos
 */
export const createCommunityPost = async (communityId, content, postType = 'general', relatedEventId = null, photos = []) => {
  const formData = new FormData();
  formData.append('content', content);
  formData.append('post_type', postType);
  if (relatedEventId) {
    formData.append('related_event_id', relatedEventId);
  }
  photos.forEach(photo => {
    formData.append('photos', photo);
  });

  const response = await apiClient.post(`/communities/${communityId}/posts`, formData, {
    headers: {
      'Content-Type': 'multipart/form-data'
    }
  });
  return response.data;
};

/**
 * Get posts for a community
 * @param {string} communityId - Community ID
 * @param {number} skip - Pagination offset
 * @param {number} limit - Max items
 * @param {boolean} includeHidden - Include hidden posts (organizers only)
 */
export const getCommunityPosts = async (communityId, skip = 0, limit = 20, includeHidden = false) => {
  const response = await apiClient.get(`/communities/${communityId}/posts`, {
    params: { skip, limit, include_hidden: includeHidden }
  });
  return response.data;
};

/**
 * Update a community post
 * @param {string} communityId - Community ID
 * @param {string} postId - Post ID
 * @param {string} content - New content
 */
export const updatePost = async (communityId, postId, content) => {
  const response = await apiClient.put(`/communities/${communityId}/posts/${postId}`, { content });
  return response.data;
};

/**
 * Delete a community post
 * @param {string} communityId - Community ID
 * @param {string} postId - Post ID
 */
export const deletePost = async (communityId, postId) => {
  const response = await apiClient.delete(`/communities/${communityId}/posts/${postId}`);
  return response.data;
};

/**
 * Toggle like on a post
 * @param {string} communityId - Community ID
 * @param {string} postId - Post ID
 */
export const togglePostLike = async (communityId, postId) => {
  const response = await apiClient.post(`/communities/${communityId}/posts/${postId}/like`);
  return response.data;
};

/**
 * Toggle pin on a post (organizer only)
 * @param {string} communityId - Community ID
 * @param {string} postId - Post ID
 * @param {boolean} pin - True to pin, false to unpin
 */
export const togglePostPin = async (communityId, postId, pin = true) => {
  const response = await apiClient.post(`/communities/${communityId}/posts/${postId}/pin`, { pin });
  return response.data;
};

/**
 * Toggle visibility of a post (organizer moderation)
 * @param {string} communityId - Community ID
 * @param {string} postId - Post ID
 * @param {boolean} hide - True to hide, false to show
 */
export const togglePostVisibility = async (communityId, postId, hide = true) => {
  const response = await apiClient.post(`/communities/${communityId}/posts/${postId}/visibility`, { hide });
  return response.data;
};

/**
 * Transcribe audio file to text using backend Whisper service
 * @param {Blob|File} audioBlob - Audio file to transcribe
 * @param {string} language - Language code (default: 'en' for English)
 * @returns {Promise<{transcription: string, language: string, language_code: string}>}
 */
export const transcribeAudio = async (audioBlob, language = 'en') => {
  const formData = new FormData();

  // Determine the correct file extension and ensure proper MIME type
  let mimeType = audioBlob.type || 'audio/webm';
  let extension = 'webm';

  // Map MIME types to extensions
  const mimeToExt = {
    'audio/webm': 'webm',
    'audio/webm;codecs=opus': 'webm',
    'audio/mp4': 'm4a',
    'audio/mpeg': 'mp3',
    'audio/ogg': 'ogg',
    'audio/wav': 'wav',
    'audio/x-wav': 'wav',
    'audio/flac': 'flac',
  };

  // Find extension from MIME type
  for (const [mime, ext] of Object.entries(mimeToExt)) {
    if (mimeType.includes(mime.split(';')[0])) {
      extension = ext;
      break;
    }
  }

  // Create a new blob with explicit MIME type if needed
  const audioFile = new File([audioBlob], `recording.${extension}`, {
    type: mimeType.split(';')[0] // Remove codec info
  });

  formData.append('audio', audioFile);
  formData.append('language', language);
  formData.append('decode_strategy', 'ctc'); // Faster decoding

  const response = await apiClient.post('/transcribe', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
    timeout: 120000, // 120 seconds timeout for transcription (model loading can take time)
  });

  return response.data;
};

// ============================================================================
// Admin Content Management APIs
// ============================================================================

/**
 * Get all reports for admin moderation
 */
export const getAdminReports = async (params = {}) => {
  const response = await apiClient.get('/admin/reports', { params });
  return response.data;
};

/**
 * Delete a report (admin only)
 */
export const deleteAdminReport = async (reportId, reason = null) => {
  const params = reason ? { reason } : {};
  const response = await apiClient.delete(`/admin/reports/${reportId}`, { params });
  return response.data;
};

/**
 * Get all alerts for admin moderation
 */
export const getAdminAlerts = async (params = {}) => {
  const response = await apiClient.get('/admin/alerts', { params });
  return response.data;
};

/**
 * Delete an alert (admin only)
 */
export const deleteAdminAlert = async (alertId) => {
  const response = await apiClient.delete(`/admin/alerts/${alertId}`);
  return response.data;
};

/**
 * Get all chat messages for admin moderation
 */
export const getAdminChatMessages = async (params = {}) => {
  const response = await apiClient.get('/admin/chat/messages', { params });
  return response.data;
};

/**
 * Delete a chat message (admin only)
 */
export const deleteAdminChatMessage = async (messageId) => {
  const response = await apiClient.delete(`/admin/chat/messages/${messageId}`);
  return response.data;
};

/**
 * Get all communities (admin can see all including inactive)
 */
export const getAdminCommunities = async (params = {}) => {
  const response = await apiClient.get('/communities', { params: { ...params, include_inactive: true } });
  return response.data;
};

/**
 * Delete a community (admin only - hard delete)
 */
export const deleteAdminCommunity = async (communityId) => {
  const response = await apiClient.delete(`/communities/${communityId}`);
  return response.data;
};

/**
 * Get all community posts (admin view)
 */
export const getAdminCommunityPosts = async (communityId, params = {}) => {
  const response = await apiClient.get(`/communities/${communityId}/posts`, { params });
  return response.data;
};

/**
 * Delete a community post (admin only)
 */
export const deleteAdminCommunityPost = async (communityId, postId) => {
  const response = await apiClient.delete(`/communities/${communityId}/posts/${postId}`);
  return response.data;
};

/**
 * Get all tickets for admin
 */
export const getAdminTickets = async (params = {}) => {
  const response = await apiClient.get('/tickets', { params });
  return response.data;
};

/**
 * Delete a ticket (admin only)
 */
export const deleteAdminTicket = async (ticketId) => {
  const response = await apiClient.delete(`/tickets/${ticketId}`);
  return response.data;
};

// ==================== SOS EMERGENCY API ====================

/**
 * Trigger an SOS emergency alert
 * @param {Object} data - SOS data
 * @param {number} data.latitude - GPS latitude
 * @param {number} data.longitude - GPS longitude
 * @param {string} data.vessel_id - Optional vessel registration ID
 * @param {string} data.vessel_name - Optional vessel name
 * @param {number} data.crew_count - Number of people on board (default: 1)
 * @param {string} data.message - Optional distress message
 * @param {string} data.priority - Priority level: critical, high, medium, low
 */
export const triggerSOS = async (data) => {
  const response = await apiClient.post('/sos/trigger', data);
  return response.data;
};

/**
 * Get active SOS alerts (authorities see all, citizens see their own)
 * @param {Object} options - Query options
 * @param {string} options.status - Filter by status: active, acknowledged, dispatched
 * @param {number} options.limit - Max results
 * @param {number} options.skip - Pagination offset
 */
export const getActiveSOSAlerts = async (options = {}) => {
  const response = await apiClient.get('/sos/active', { params: options });
  return response.data;
};

/**
 * Get detailed information about a specific SOS alert
 * @param {string} sosId - SOS alert ID
 */
export const getSOSDetail = async (sosId) => {
  const response = await apiClient.get(`/sos/${sosId}`);
  return response.data;
};

/**
 * Acknowledge an SOS alert (authority only)
 * @param {string} sosId - SOS alert ID
 * @param {Object} data - Acknowledgement data
 * @param {string} data.notes - Optional acknowledgement notes
 */
export const acknowledgesSOS = async (sosId, data = {}) => {
  const response = await apiClient.patch(`/sos/${sosId}/acknowledge`, data);
  return response.data;
};

/**
 * Dispatch rescue for an SOS alert (authority only)
 * @param {string} sosId - SOS alert ID
 * @param {Object} data - Dispatch data
 * @param {string} data.dispatch_notes - Dispatch instructions
 * @param {string} data.rescue_unit - Optional rescue unit name/ID
 * @param {number} data.eta_minutes - Optional ETA in minutes
 */
export const dispatchSOSRescue = async (sosId, data) => {
  const response = await apiClient.patch(`/sos/${sosId}/dispatch`, data);
  return response.data;
};

/**
 * Resolve an SOS alert (authority only)
 * @param {string} sosId - SOS alert ID
 * @param {Object} data - Resolution data
 * @param {string} data.resolution_notes - Resolution details
 * @param {string} data.outcome - Outcome: rescued, false_alarm, self_resolved, other
 */
export const resolvesSOS = async (sosId, data) => {
  const response = await apiClient.patch(`/sos/${sosId}/resolve`, data);
  return response.data;
};

/**
 * Cancel an SOS alert (by the user who triggered it)
 * @param {string} sosId - SOS alert ID
 * @param {Object} data - Cancellation data
 * @param {string} data.reason - Reason for cancellation
 */
export const cancelSOS = async (sosId, data) => {
  const response = await apiClient.patch(`/sos/${sosId}/cancel`, data);
  return response.data;
};

/**
 * Get current user's SOS alert history
 * @param {Object} options - Query options
 * @param {number} options.limit - Max results (default: 20)
 * @param {number} options.skip - Pagination offset
 */
export const getMySOSHistory = async (options = {}) => {
  const response = await apiClient.get('/sos/my/history', { params: options });
  return response.data;
};

// ==================== UNIFIED EXPORT API ====================

/**
 * Create a unified export job (for all roles: analyst, authority, admin)
 * @param {Object} config - Export configuration
 * @param {string} config.data_type - Type of data: reports, tickets, alerts, users, audit_logs, smi
 * @param {string} config.export_format - Format: csv, excel, pdf
 * @param {Object} config.filters - Query filters
 * @param {Object} config.date_range - Date range config { start, end } or { relative: '7days' }
 * @param {string[]} config.columns - Columns to include (optional)
 */
export const createExport = async (config) => {
  const response = await apiClient.post('/export', config);
  return response.data;
};

/**
 * Get export job status
 * @param {string} jobId - Export job ID
 */
export const getExportStatus = async (jobId) => {
  const response = await apiClient.get(`/export/${jobId}`);
  return response.data;
};

/**
 * Download unified export file
 * @param {string} jobId - Export job ID
 * @param {string} fileName - Expected file name for download
 */
export const downloadUnifiedExport = async (jobId, fileName) => {
  const response = await apiClient.get(`/export/${jobId}/download`, {
    responseType: 'blob'
  });

  // Create download link
  const url = window.URL.createObjectURL(new Blob([response.data]));
  const link = document.createElement('a');
  link.href = url;
  link.setAttribute('download', fileName || `export-${jobId}.csv`);
  document.body.appendChild(link);
  link.click();
  link.remove();
  window.URL.revokeObjectURL(url);

  return true;
};

/**
 * Delete an export job
 * @param {string} jobId - Export job ID
 */
export const deleteExport = async (jobId) => {
  const response = await apiClient.delete(`/export/${jobId}`);
  return response.data;
};

// ==================== PREDICTIVE ALERTS API ====================

/**
 * Subscribe to predictive alerts for a location
 */
export const subscribeToPredictiveAlerts = async (data) => {
  const response = await apiClient.post('/predictive-alerts/subscribe', data);
  return response.data;
};

/**
 * Get current user's alert subscription
 */
export const getAlertSubscription = async () => {
  const response = await apiClient.get('/predictive-alerts/subscriptions');
  return response.data;
};

/**
 * Unsubscribe from predictive alerts
 */
export const unsubscribeFromPredictiveAlerts = async () => {
  const response = await apiClient.delete('/predictive-alerts/subscribe');
  return response.data;
};

/**
 * Toggle alert subscription on/off
 */
export const toggleAlertSubscription = async (enabled) => {
  const response = await apiClient.patch('/predictive-alerts/subscribe/toggle', null, {
    params: { enabled }
  });
  return response.data;
};

/**
 * Register browser push subscription
 */
export const registerPushSubscription = async (subscriptionInfo, deviceInfo = null) => {
  const response = await apiClient.post('/predictive-alerts/push-subscription', {
    endpoint: subscriptionInfo.endpoint,
    keys: {
      p256dh: subscriptionInfo.keys?.p256dh || '',
      auth: subscriptionInfo.keys?.auth || ''
    },
    expiration_time: subscriptionInfo.expirationTime,
    device_info: deviceInfo
  });
  return response.data;
};

/**
 * Unregister push subscription
 */
export const unregisterPushSubscription = async (endpoint = null) => {
  const response = await apiClient.delete('/predictive-alerts/push-subscription', {
    params: endpoint ? { endpoint } : {}
  });
  return response.data;
};

/**
 * Get VAPID public key for push subscription
 */
export const getVapidPublicKey = async () => {
  const response = await apiClient.get('/predictive-alerts/push-vapid-key');
  return response.data;
};

/**
 * Get active predictive alerts
 */
export const getActivePredictiveAlerts = async (options = {}) => {
  const response = await apiClient.get('/predictive-alerts/active', {
    params: {
      latitude: options.latitude,
      longitude: options.longitude,
      radius_km: options.radiusKm,
      alert_type: options.alertType,
      min_severity: options.minSeverity
    }
  });
  return response.data;
};

/**
 * Get alerts for current user based on subscription
 */
export const getMyPredictiveAlerts = async () => {
  const response = await apiClient.get('/predictive-alerts/my-alerts');
  return response.data;
};

/**
 * Get IMD alert thresholds
 */
export const getAlertThresholds = async () => {
  const response = await apiClient.get('/predictive-alerts/thresholds');
  return response.data;
};

export default apiClient;
