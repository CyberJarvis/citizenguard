/**
 * SMI (Social Media Intelligence) API Client - BlueRadar Integration
 *
 * This client connects to the CoastGuardian backend which integrates with
 * the BlueRadar real-time intelligence module.
 *
 * BlueRadar Features:
 * - Real-time social media scraping (Twitter, YouTube, Instagram, News)
 * - Fast rule-based NLP for hazard classification
 * - Indian coastal hazard detection
 * - Content validation and deduplication
 *
 * All requests are routed through the main backend on port 8000 with RBAC.
 */

import axios from 'axios';
import Cookies from 'js-cookie';
import { formatDateIST } from '@/lib/dateUtils';

// Configuration
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';
const SMI_BASE_URL = `${API_BASE_URL}/smi`;

// Create axios instance for SMI API
const smiClient = axios.create({
  baseURL: SMI_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 15000, // 15 second timeout
  withCredentials: true,
});

// Request interceptor - Add auth token
smiClient.interceptors.request.use(
  (config) => {
    const token = Cookies.get('access_token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// Response interceptor - Handle token refresh
smiClient.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;

    // If 401, try to refresh token
    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;

      try {
        const refreshToken = Cookies.get('refresh_token');
        if (refreshToken) {
          const response = await axios.post(
            `${API_BASE_URL}/auth/refresh`,
            { refresh_token: refreshToken }
          );

          const { access_token, refresh_token: newRefreshToken } = response.data;
          Cookies.set('access_token', access_token);
          if (newRefreshToken) {
            Cookies.set('refresh_token', newRefreshToken);
          }

          originalRequest.headers.Authorization = `Bearer ${access_token}`;
          return smiClient(originalRequest);
        }
      } catch (refreshError) {
        console.error('Token refresh failed:', refreshError);
      }
    }

    return Promise.reject(error);
  }
);

// ==================== HEALTH & SYSTEM ====================

/**
 * Check BlueRadar system health
 */
export const getSMIHealth = async () => {
  const response = await smiClient.get('/health');
  return response.data.data || response.data;
};

/**
 * Get BlueRadar system info
 */
export const getSMISystemInfo = async () => {
  const response = await smiClient.get('/system/info');
  return response.data.data || response.data;
};

/**
 * Get comprehensive dashboard data
 */
export const getSMIDashboard = async () => {
  const response = await smiClient.get('/dashboard');
  return response.data.data || response.data;
};

// ==================== FEED MANAGEMENT ====================

/**
 * Start the real-time scraping feed
 */
export const startEnhancedFeed = async (config = {}) => {
  const response = await smiClient.post('/feed/start', config);
  return response.data.data || response.data;
};

/**
 * Stop feed
 */
export const stopFeed = async () => {
  const response = await smiClient.post('/feed/stop');
  return response.data.data || response.data;
};

/**
 * Configure feed parameters
 * @param {Object} config - { post_interval, disaster_probability }
 */
export const configureFeed = async (config) => {
  const response = await smiClient.post('/feed/configure', config);
  return response.data.data || response.data;
};

/**
 * Get current feed status
 */
export const getFeedStatus = async () => {
  const response = await smiClient.get('/feed/status');
  return response.data.data || response.data;
};

/**
 * Get posts from the feed
 */
export const getEnhancedFeedPosts = async (limit = 50) => {
  const response = await smiClient.get('/feed/posts', {
    params: { limit }
  });
  const data = response.data.data || response.data;
  return data.posts || data;
};

/**
 * Get recent live posts (alias for getEnhancedFeedPosts)
 */
export const getLivePosts = async (limit = 50) => {
  return getEnhancedFeedPosts(limit);
};

// ==================== ANALYSIS ====================

/**
 * Analyze a single post using BlueRadar NLP
 */
export const analyzePost = async (post) => {
  const response = await smiClient.post('/analyze', post);
  return response.data.data || response.data;
};

/**
 * Batch analyze multiple posts
 */
export const batchAnalyze = async (posts, filterThreshold = 3.0) => {
  const response = await smiClient.post('/analyze/batch', {
    posts,
    filter_threshold: filterThreshold
  });
  return response.data.data || response.data;
};

/**
 * Check post for misinformation/spam
 */
export const checkMisinformation = async (post) => {
  const response = await smiClient.post('/analyze/misinformation', post);
  return response.data.data || response.data;
};

/**
 * Get priority scoring breakdown
 */
export const getPriorityBreakdown = async (post) => {
  const response = await smiClient.post('/analyze/priority', post);
  return response.data.data || response.data;
};

/**
 * Verify facts in a post
 */
export const verifyFacts = async (post) => {
  const response = await smiClient.post('/verify/facts', post);
  return response.data.data || response.data;
};

// ==================== POSTS & DATA ====================

/**
 * Get recent analyzed posts
 * @param {Object} params - { limit, disaster_type, urgency, min_relevance }
 */
export const getRecentPosts = async (params = {}) => {
  const response = await smiClient.get('/posts/recent', { params });
  const data = response.data.data || response.data;
  return data.posts || data;
};

/**
 * Search posts
 * @param {Object} params - { query, disaster_type, language, platform, limit }
 */
export const searchPosts = async (params = {}) => {
  const response = await smiClient.get('/posts/search', { params });
  const data = response.data.data || response.data;
  return data.posts || data;
};

// ==================== ALERTS ====================

/**
 * Get active alerts
 */
export const getActiveAlerts = async () => {
  const response = await smiClient.get('/alerts/active');
  const data = response.data.data || response.data;

  let alertsArray = [];
  let count = 0;
  let alertThreshold = null;

  if (data.alerts) {
    if (Array.isArray(data.alerts)) {
      alertsArray = data.alerts;
      count = data.count || alertsArray.length;
      alertThreshold = data.alert_threshold;
    }
  }

  return {
    alerts: alertsArray,
    count: count,
    alert_threshold: alertThreshold
  };
};

/**
 * Get critical alerts only
 */
export const getCriticalAlerts = async () => {
  const response = await smiClient.get('/alerts/critical');
  const data = response.data.data || response.data;

  let alertsArray = [];
  let count = 0;

  if (data.alerts) {
    if (Array.isArray(data.alerts)) {
      alertsArray = data.alerts;
      count = data.count || alertsArray.length;
    }
  }

  return {
    alerts: alertsArray,
    count: count,
    threshold: data.threshold
  };
};

/**
 * Get recent alerts from cache
 */
export const getRecentAlerts = async (limit = 50) => {
  const response = await smiClient.get('/alerts/recent', {
    params: { limit }
  });
  const data = response.data.data || response.data;
  return data.alerts || data;
};

/**
 * Sync alerts to notification system (admin only)
 */
export const syncAlertsToNotifications = async () => {
  const response = await smiClient.post('/alerts/sync');
  return response.data.data || response.data;
};

// ==================== STATISTICS ====================

/**
 * Get disaster type statistics
 */
export const getDisasterStats = async (days = 7) => {
  const response = await smiClient.get('/statistics/disaster', {
    params: { days }
  });
  const data = response.data.data || response.data;
  return { statistics: data.statistics || data };
};

/**
 * Get platform breakdown statistics
 */
export const getPlatformStats = async () => {
  const response = await smiClient.get('/statistics/platform');
  const data = response.data.data || response.data;
  return { statistics: data.statistics || data };
};

// ==================== LANGUAGES ====================

/**
 * Get supported languages
 */
export const getSupportedLanguages = async () => {
  const response = await smiClient.get('/languages');
  const data = response.data.data || response.data;
  return data;
};

// ==================== DATABASE ====================

/**
 * Cleanup cache (clear all data) - Admin only
 */
export const cleanupDatabase = async () => {
  const response = await smiClient.post('/database/cleanup');
  return response.data.data || response.data;
};

// ==================== CONFIGURATION ====================

/**
 * Get SMI configuration
 */
export const getSMIConfig = async () => {
  const response = await smiClient.get('/config');
  return response.data.data || response.data;
};

/**
 * Get the current base URL
 */
export const getBaseUrl = () => SMI_BASE_URL;

// ==================== PUBLIC ENDPOINTS (No Auth Required) ====================
// These endpoints are for citizen dashboard - no authentication needed

/**
 * Create a separate client for public endpoints (no auth)
 */
const publicClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 10000,
});

/**
 * Get public health status (no auth required)
 */
export const getPublicHealth = async () => {
  try {
    const response = await publicClient.get('/smi/public/health');
    const data = response.data?.data || response.data || {};
    return {
      status: data.status || 'healthy',
      is_connected: data.is_connected !== false
    };
  } catch (error) {
    console.log('Public health check error (non-fatal):', error.message);
    return { status: 'unknown', is_connected: true };
  }
};

/**
 * Get public alerts for citizen dashboard (no auth required)
 */
export const getPublicAlerts = async (limit = 20) => {
  try {
    const response = await publicClient.get('/smi/public/alerts', {
      params: { limit }
    });
    const data = response.data?.data || response.data || {};
    return {
      alerts: data.alerts || [],
      count: data.count || 0
    };
  } catch (error) {
    console.log('Public alerts fetch error (non-fatal):', error.message);
    return { alerts: [], count: 0 };
  }
};

/**
 * Get public feed posts for citizen dashboard (no auth required)
 */
export const getPublicFeed = async (limit = 20) => {
  try {
    const response = await publicClient.get('/smi/public/feed', {
      params: { limit }
    });
    const data = response.data?.data || response.data || {};
    return {
      posts: data.posts || [],
      count: data.count || 0
    };
  } catch (error) {
    console.log('Public feed fetch error (non-fatal):', error.message);
    return { posts: [], count: 0 };
  }
};

/**
 * Get public statistics (no auth required)
 */
export const getPublicStats = async () => {
  try {
    const response = await publicClient.get('/smi/public/stats');
    const data = response.data?.data || response.data || {};
    return { statistics: data.statistics || data };
  } catch (error) {
    console.log('Public stats fetch error (non-fatal):', error.message);
    return { statistics: {} };
  }
};

// ==================== DEMO MODE ENDPOINTS ====================

/**
 * Get demo mode status
 */
export const getDemoStatus = async () => {
  const response = await smiClient.get('/demo/status');
  return response.data.data || response.data;
};

/**
 * Start demo simulation mode
 */
export const startDemoMode = async (config = {}) => {
  const response = await smiClient.post('/demo/start', config);
  return response.data.data || response.data;
};

/**
 * Stop demo simulation mode
 */
export const stopDemoMode = async () => {
  const response = await smiClient.post('/demo/stop');
  return response.data.data || response.data;
};

/**
 * Configure demo mode
 */
export const configureDemoMode = async (config) => {
  const response = await smiClient.post('/demo/configure', config);
  return response.data.data || response.data;
};

/**
 * Get demo posts
 */
export const getDemoPosts = async (limit = 50) => {
  const response = await smiClient.get('/demo/posts', {
    params: { limit }
  });
  const data = response.data.data || response.data;
  return data.posts || data;
};

/**
 * Get demo alerts
 */
export const getDemoAlerts = async () => {
  const response = await smiClient.get('/demo/alerts');
  const data = response.data.data || response.data;
  return {
    alerts: data.alerts || [],
    count: data.count || 0
  };
};

// Public demo endpoints (no auth)

/**
 * Get public demo status (no auth required)
 */
export const getPublicDemoStatus = async () => {
  try {
    const response = await publicClient.get('/smi/public/demo/status');
    return response.data?.data || response.data || { is_running: false, available: false };
  } catch (error) {
    console.log('Public demo status error (non-fatal):', error.message);
    return { is_running: false, available: false };
  }
};

/**
 * Get public demo feed (no auth required)
 */
export const getPublicDemoFeed = async (limit = 20) => {
  try {
    const response = await publicClient.get('/smi/public/demo/feed', {
      params: { limit }
    });
    const data = response.data?.data || response.data || {};
    return {
      posts: data.posts || [],
      count: data.count || 0,
      mode: 'demo'
    };
  } catch (error) {
    console.log('Public demo feed error (non-fatal):', error.message);
    return { posts: [], count: 0, mode: 'demo' };
  }
};

/**
 * Get public demo alerts (no auth required)
 */
export const getPublicDemoAlerts = async (limit = 20) => {
  try {
    const response = await publicClient.get('/smi/public/demo/alerts', {
      params: { limit }
    });
    const data = response.data?.data || response.data || {};
    return {
      alerts: data.alerts || [],
      count: data.count || 0,
      mode: 'demo'
    };
  } catch (error) {
    console.log('Public demo alerts error (non-fatal):', error.message);
    return { alerts: [], count: 0, mode: 'demo' };
  }
};

/**
 * Start demo mode (public endpoint - no auth required)
 */
export const startPublicDemoMode = async (config = {}) => {
  try {
    const response = await publicClient.post('/smi/public/demo/start', config);
    return response.data?.data || response.data || { is_running: false };
  } catch (error) {
    console.log('Start demo error:', error.message);
    return { is_running: false, error: error.message };
  }
};

/**
 * Stop demo mode (public endpoint - no auth required)
 */
export const stopPublicDemoMode = async () => {
  try {
    const response = await publicClient.post('/smi/public/demo/stop');
    return response.data?.data || response.data || { is_running: false };
  } catch (error) {
    console.log('Stop demo error:', error.message);
    return { is_running: false, error: error.message };
  }
};

/**
 * Configure demo mode (public endpoint - no auth required)
 */
export const configurePublicDemoMode = async (config) => {
  try {
    const response = await publicClient.post('/smi/public/demo/configure', config);
    return response.data?.data || response.data || {};
  } catch (error) {
    console.log('Configure demo error:', error.message);
    return { error: error.message };
  }
};

// ==================== UTILITY FUNCTIONS ====================

/**
 * Get priority color based on level
 */
export const getPriorityColor = (priority) => {
  const colors = {
    'P0': { bg: 'bg-red-100', text: 'text-red-800', border: 'border-red-500', dot: 'bg-red-500' },
    'P1': { bg: 'bg-orange-100', text: 'text-orange-800', border: 'border-orange-500', dot: 'bg-orange-500' },
    'P2': { bg: 'bg-yellow-100', text: 'text-yellow-800', border: 'border-yellow-500', dot: 'bg-yellow-500' },
    'P3': { bg: 'bg-blue-100', text: 'text-blue-800', border: 'border-blue-500', dot: 'bg-blue-500' },
    'P4': { bg: 'bg-gray-100', text: 'text-gray-800', border: 'border-gray-500', dot: 'bg-gray-500' },
  };
  return colors[priority] || colors['P4'];
};

/**
 * Get urgency color
 */
export const getUrgencyColor = (urgency) => {
  const colors = {
    'critical': { bg: 'bg-red-100', text: 'text-red-800' },
    'high': { bg: 'bg-orange-100', text: 'text-orange-800' },
    'medium': { bg: 'bg-yellow-100', text: 'text-yellow-800' },
    'low': { bg: 'bg-green-100', text: 'text-green-800' },
  };
  return colors[urgency?.toLowerCase()] || colors['low'];
};

/**
 * Get disaster type icon and color
 * Supports BlueRadar hazard types
 */
export const getDisasterTypeInfo = (type) => {
  const info = {
    'tsunami': { color: 'blue', label: 'Tsunami' },
    'cyclone': { color: 'purple', label: 'Cyclone' },
    'flood': { color: 'cyan', label: 'Flood' },
    'flooding': { color: 'cyan', label: 'Flooding' },
    'storm_surge': { color: 'indigo', label: 'Storm Surge' },
    'rough_sea': { color: 'teal', label: 'Rough Sea' },
    'oil_spill': { color: 'amber', label: 'Oil Spill' },
    'earthquake': { color: 'orange', label: 'Earthquake' },
    'hazard': { color: 'red', label: 'Hazard' },
    'none': { color: 'gray', label: 'Normal' },
  };
  return info[type?.toLowerCase()] || { color: 'gray', label: type || 'Unknown' };
};

/**
 * Get alert level color
 */
export const getAlertLevelColor = (level) => {
  const colors = {
    'CRITICAL': { bg: 'bg-red-100', text: 'text-red-800', border: 'border-red-500' },
    'HIGH': { bg: 'bg-orange-100', text: 'text-orange-800', border: 'border-orange-500' },
    'MEDIUM': { bg: 'bg-yellow-100', text: 'text-yellow-800', border: 'border-yellow-500' },
    'LOW': { bg: 'bg-green-100', text: 'text-green-800', border: 'border-green-500' },
  };
  return colors[level?.toUpperCase()] || colors['LOW'];
};

/**
 * Get misinformation risk color
 */
export const getMisinfoRiskColor = (risk) => {
  const colors = {
    'high': { bg: 'bg-red-100', text: 'text-red-800' },
    'moderate': { bg: 'bg-orange-100', text: 'text-orange-800' },
    'low': { bg: 'bg-yellow-100', text: 'text-yellow-800' },
    'minimal': { bg: 'bg-green-100', text: 'text-green-800' },
  };
  return colors[risk] || colors['minimal'];
};

/**
 * Format timestamp
 */
export const formatTimestamp = (timestamp) => {
  if (!timestamp) return '';
  const date = new Date(timestamp);
  const now = new Date();
  const diff = (now - date) / 1000; // seconds

  if (diff < 60) return 'Just now';
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
  if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
  return formatDateIST(timestamp);
};

/**
 * Get language display name
 */
export const getLanguageDisplay = (code) => {
  const languages = {
    'en': 'English',
    'hi': 'Hindi',
    'ta': 'Tamil',
    'te': 'Telugu',
    'kn': 'Kannada',
    'ml': 'Malayalam',
    'bn': 'Bengali',
    'gu': 'Gujarati',
    'mr': 'Marathi',
  };
  return languages[code] || code;
};

/**
 * Get platform display info
 */
export const getPlatformInfo = (platform) => {
  const info = {
    'twitter': { label: 'Twitter/X', color: 'blue', icon: '𝕏' },
    'youtube': { label: 'YouTube', color: 'red', icon: '▶' },
    'instagram': { label: 'Instagram', color: 'pink', icon: '📷' },
    'news': { label: 'News', color: 'gray', icon: '📰' },
    'facebook': { label: 'Facebook', color: 'blue', icon: 'f' },
  };
  return info[platform?.toLowerCase()] || { label: platform || 'Unknown', color: 'gray', icon: '?' };
};

export default smiClient;
