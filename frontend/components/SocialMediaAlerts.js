'use client';

import { useState, useEffect, useCallback, useRef } from 'react';
import {
  AlertTriangle,
  MapPin,
  RefreshCw,
  CheckCircle,
  Globe,
  MessageSquare,
  Shield,
  ChevronRight,
  Waves
} from 'lucide-react';
import {
  getActiveAlerts,
  getEnhancedFeedPosts,
  getDisasterStats,
  startEnhancedFeed,
  getPublicAlerts,
  getPublicFeed,
  getDisasterTypeInfo,
  formatTimestamp,
  getPublicDemoStatus,
  getPublicDemoFeed,
  getPublicDemoAlerts
} from '@/lib/smiApi';

// ==================== SKELETON LOADERS ====================
function SkeletonAlert() {
  return (
    <div className="p-3 animate-pulse">
      <div className="flex items-start gap-3">
        <div className="w-16 h-5 bg-gray-200 rounded"></div>
        <div className="flex-1 space-y-2">
          <div className="h-4 bg-gray-200 rounded w-3/4"></div>
          <div className="h-3 bg-gray-100 rounded w-1/2"></div>
        </div>
      </div>
    </div>
  );
}


// Misinformation detection patterns (multilingual)
const MISINFO_PATTERNS = {
  sensational: [
    // English
    'breaking', 'urgent', 'emergency', 'critical', 'alert', 'warning',
    'disaster', 'catastrophe', 'unprecedented', 'massive', 'devastating',
    'apocalyptic', 'worst ever', 'historic', 'never seen before',
    // Hindi
    'आपातकालीन', 'खतरा', 'तबाही', 'विनाशकारी', 'भयंकर', 'आपदा',
    // Tamil
    'அவசரம்', 'ஆபத்து', 'பேரழிவு'
  ],
  emotional: [
    'share before deleted', 'must watch', 'shocking', 'you wont believe',
    'please share', 'spread the word', 'wake up', 'open your eyes',
    'they dont want you to know'
  ]
};

function detectMisinformation(text) {
  if (!text) return { risk_level: 'minimal', flags: [] };

  const textLower = text.toLowerCase();
  const flags = [];
  let score = 0;

  // Check sensational language
  const sensationalMatches = MISINFO_PATTERNS.sensational.filter(p => textLower.includes(p.toLowerCase()));
  if (sensationalMatches.length >= 3) {
    flags.push('excessive_sensational_language');
    score += 0.3;
  } else if (sensationalMatches.length >= 1) {
    flags.push('sensational_language');
    score += 0.15;
  }

  // Check emotional manipulation
  if (MISINFO_PATTERNS.emotional.some(p => textLower.includes(p))) {
    flags.push('emotional_manipulation');
    score += 0.2;
  }

  // Check excessive caps (>40% uppercase in text longer than 20 chars)
  if (text.length > 20) {
    const capsRatio = (text.match(/[A-Z]/g) || []).length / text.length;
    if (capsRatio > 0.4) {
      flags.push('excessive_caps');
      score += 0.15;
    }
  }

  // Check excessive exclamation
  const exclamationCount = (text.match(/!/g) || []).length;
  if (exclamationCount >= 3) {
    flags.push('excessive_exclamation');
    score += 0.1;
  }

  // Determine risk level
  let risk_level = 'minimal';
  if (score >= 0.4) risk_level = 'high';
  else if (score >= 0.25) risk_level = 'moderate';
  else if (score >= 0.1) risk_level = 'low';

  return { risk_level, flags, score };
}

/**
 * Social Media Alerts Component - BlueRadar Integration
 * Shows live social media alerts and hazard detection from BlueRadar Intelligence module
 *
 * Features:
 * - Real-time alerts from Twitter, YouTube, Instagram, News
 * - Fast rule-based NLP hazard classification
 * - Indian coastal hazard detection
 * - Misinformation/spam detection
 */
export default function SocialMediaAlerts({
  variant = 'compact',
  refreshInterval = 15000,
  maxAlerts = 5,
  usePublicApi = true
}) {
  const [alerts, setAlerts] = useState([]);
  const [recentPosts, setRecentPosts] = useState([]);
  const [stats, setStats] = useState({});
  const [isLoading, setIsLoading] = useState(true);
  const [showAllAlerts, setShowAllAlerts] = useState(false);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [isDemoMode, setIsDemoMode] = useState(false);

  // Cache ref to persist data across renders
  const dataCache = useRef({ alerts: [], posts: [] });

  // Fetch data with caching and fallback
  const fetchData = useCallback(async (showRefreshIndicator = false) => {
    if (showRefreshIndicator) setIsRefreshing(true);

    try {
      const shouldUsePublic = usePublicApi || variant === 'compact';

      // Check if demo mode is active
      let demoActive = false;
      try {
        const demoStatus = await getPublicDemoStatus();
        demoActive = demoStatus?.is_running || false;
        setIsDemoMode(demoActive);
      } catch (e) {
        console.log('Demo status check failed:', e.message);
      }

      if (shouldUsePublic) {
        // Fetch all data in parallel with generous limits
        let alertsRes, postsRes;
        try {
          if (demoActive) {
            // Use demo APIs when demo is running
            [alertsRes, postsRes] = await Promise.all([
              getPublicDemoAlerts(50),
              getPublicDemoFeed(50)
            ]);
          } else {
            [alertsRes, postsRes] = await Promise.all([
              getPublicAlerts(50),
              getPublicFeed(50)
            ]);
          }
        } catch (fetchErr) {
          console.log('Parallel fetch failed, trying sequential:', fetchErr.message);
          if (demoActive) {
            alertsRes = await getPublicDemoAlerts(50).catch(() => ({ alerts: [], count: 0 }));
            postsRes = await getPublicDemoFeed(50).catch(() => ({ posts: [], count: 0 }));
          } else {
            alertsRes = await getPublicAlerts(50).catch(() => ({ alerts: [], count: 0 }));
            postsRes = await getPublicFeed(50).catch(() => ({ posts: [], count: 0 }));
          }
        }

        // Safely extract arrays from API responses
        const alertsArray = Array.isArray(alertsRes?.alerts) ? alertsRes.alerts : [];
        const postsArray = Array.isArray(postsRes?.posts) ? postsRes.posts : [];

        console.log('SMI Public API Response:', {
          alertsCount: alertsArray.length,
          postsCount: postsArray.length,
          sampleAlert: alertsArray[0],
          samplePost: postsArray[0]
        });

        // Apply misinformation detection to posts
        const postsWithMisinfo = postsArray.map(p => ({
          ...p,
          misinformation_analysis: detectMisinformation(p.text || p.original_post?.text || '')
        }));

        // For public API, all returned posts are already disaster-related
        // Just include all posts that have alert_level or disaster_type
        const disasterPosts = postsWithMisinfo.filter(p => {
          const type = p.analysis?.disaster_type || p.disaster_type;
          const level = p.alert_level;
          return (type && type !== 'none') || level;
        });

        console.log('Filtered disaster posts:', disasterPosts.length);

        // Always update state - use all fetched data
        const finalAlerts = alertsArray.length > 0 ? alertsArray : dataCache.current.alerts;
        const finalPosts = disasterPosts.length > 0 ? disasterPosts :
                          postsWithMisinfo.length > 0 ? postsWithMisinfo :
                          dataCache.current.posts;

        setAlerts(finalAlerts);
        setRecentPosts(finalPosts);

        // Update cache
        if (alertsArray.length > 0 || postsWithMisinfo.length > 0) {
          dataCache.current = { alerts: alertsArray, posts: disasterPosts.length > 0 ? disasterPosts : postsWithMisinfo.slice(0, 20) };
        }
      } else {
        // Authenticated endpoints
        await startEnhancedFeed().catch(() => {});

        const [alertsRes, postsRes, statsRes] = await Promise.all([
          getActiveAlerts().catch(() => ({ alerts: { alerts: [] } })),
          getEnhancedFeedPosts(100).catch(() => ({ posts: [] })),
          getDisasterStats().catch(() => ({ statistics: {} }))
        ]);

        const alertsArray = alertsRes?.alerts?.alerts || alertsRes?.alerts || [];
        const postsArray = Array.isArray(postsRes) ? postsRes : (postsRes.posts || []);

        // Apply misinformation detection
        const postsWithMisinfo = postsArray.map(p => ({
          ...p,
          misinformation_analysis: detectMisinformation(p.text || p.original_post?.text || '')
        }));

        const disasterPosts = postsWithMisinfo.filter(p => {
          const type = p.analysis?.disaster_type || p.disaster_type;
          return type && type !== 'none';
        });

        if (alertsArray.length > 0 || disasterPosts.length > 0) {
          setAlerts(alertsArray);
          setRecentPosts(disasterPosts);
          dataCache.current = { alerts: alertsArray, posts: disasterPosts };
        } else if (dataCache.current.alerts.length > 0) {
          setAlerts(dataCache.current.alerts);
          setRecentPosts(dataCache.current.posts);
        }

        setStats(statsRes.statistics || statsRes || {});
      }
    } catch (error) {
      console.log('SMI fetch error:', error.message);
      // Use cached data on error
      if (dataCache.current.alerts.length > 0 || dataCache.current.posts.length > 0) {
        setAlerts(dataCache.current.alerts);
        setRecentPosts(dataCache.current.posts);
      }
    } finally {
      setIsLoading(false);
      setIsRefreshing(false);
    }
  }, [usePublicApi, variant]);

  // Manual refresh handler
  const handleRefresh = () => {
    fetchData(true);
  };

  useEffect(() => {
    fetchData();
    const interval = setInterval(() => fetchData(false), refreshInterval);
    return () => clearInterval(interval);
  }, [fetchData, refreshInterval]);

  // Combine alerts and disaster posts - prioritize alerts, then posts
  // For public API, alerts and posts are separate - combine them all
  const displayItems = [...alerts, ...recentPosts.filter(p =>
    !alerts.some(a => a.post_id === p.id || a.post_id === p.post_id)
  )];

  // Log state for debugging (dev only)
  if (process.env.NODE_ENV === 'development') {
    console.log('SocialMediaAlerts state:', {
      alertsCount: alerts.length,
      recentPostsCount: recentPosts.length,
      displayItemsCount: displayItems.length,
      isLoading
    });
  }

  // Count critical alerts
  const criticalCount = displayItems.filter(item =>
    item.alert_level === 'HIGH' || item.alert_level === 'CRITICAL'
  ).length;

  // Skeleton loading state
  if (isLoading) {
    return (
      <div className="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
        {/* Header Skeleton */}
        <div className="bg-gradient-to-r from-[#0d4a6f] to-[#1a6b9a] p-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <div className="w-5 h-5 bg-white/30 rounded animate-pulse"></div>
              <div className="w-32 h-5 bg-white/30 rounded animate-pulse"></div>
            </div>
            <div className="w-16 h-5 bg-white/20 rounded animate-pulse"></div>
          </div>
        </div>
        {/* Content Skeleton */}
        <div className="divide-y divide-gray-100">
          {[1, 2, 3].map(i => <SkeletonAlert key={i} />)}
        </div>
      </div>
    );
  }

  // Compact variant for citizen dashboard - Clean Modern Design
  if (variant === 'compact') {
    return (
      <div className="bg-white rounded-2xl shadow-sm border border-gray-100 overflow-hidden">
        {/* Clean Header */}
        <div className="px-4 py-3 border-b border-gray-100">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <div className="w-8 h-8 bg-[#0d4a6f] rounded-lg flex items-center justify-center">
                <Globe className="w-4 h-4 text-white" />
              </div>
              <div>
                <h3 className="text-base font-semibold text-gray-900">Social Media Intel</h3>
                <div className="flex items-center gap-1.5">
                  <span className="w-1.5 h-1.5 bg-green-500 rounded-full animate-pulse" />
                  <span className="text-[10px] text-gray-500">Live monitoring</span>
                  {isDemoMode && (
                    <span className="px-1.5 py-0.5 bg-purple-100 text-purple-600 rounded text-[9px] font-medium">
                      DEMO
                    </span>
                  )}
                </div>
              </div>
            </div>
            <div className="flex items-center gap-2">
              {criticalCount > 0 && (
                <span className="px-2 py-1 bg-red-50 text-red-600 rounded-lg text-[10px] font-semibold">
                  {criticalCount} Critical
                </span>
              )}
              <button
                onClick={handleRefresh}
                disabled={isRefreshing}
                className="p-1.5 text-gray-400 hover:text-[#0d4a6f] hover:bg-gray-50 rounded-lg transition-colors disabled:opacity-50"
              >
                <RefreshCw className={`w-4 h-4 ${isRefreshing ? 'animate-spin' : ''}`} />
              </button>
            </div>
          </div>
        </div>

        {/* Alert List - Clean Cards */}
        <div className={`overflow-y-auto ${showAllAlerts ? 'max-h-[350px]' : 'max-h-[220px]'}`}>
          {displayItems.length === 0 ? (
            <div className="p-6 text-center">
              <div className="w-12 h-12 mx-auto mb-3 bg-emerald-50 rounded-xl flex items-center justify-center">
                <Shield className="w-6 h-6 text-emerald-500" />
              </div>
              <p className="text-gray-800 font-medium text-sm">All Clear</p>
              <p className="text-gray-400 text-xs mt-0.5">No hazard alerts detected</p>
            </div>
          ) : (
            <div className="p-2 space-y-2">
              {displayItems.slice(0, showAllAlerts ? displayItems.length : maxAlerts).map((item, idx) => {
                const alertLevel = item.alert_level || 'MEDIUM';
                const disasterType = item.disaster_type || item.analysis?.disaster_type || 'unknown';
                const disasterInfo = getDisasterTypeInfo(disasterType);
                const text = item.post_excerpt || item.text || item.original_post?.text || '';
                const location = item.location || item.original_post?.location || '';
                const timestamp = item.timestamp || item.original_post?.timestamp;

                // Clean color scheme based on alert level
                const levelStyles = {
                  'HIGH': { bg: 'bg-red-50', border: 'border-red-200', badge: 'bg-red-500 text-white', dot: 'bg-red-500' },
                  'CRITICAL': { bg: 'bg-red-50', border: 'border-red-200', badge: 'bg-red-500 text-white', dot: 'bg-red-500' },
                  'MEDIUM': { bg: 'bg-amber-50', border: 'border-amber-200', badge: 'bg-amber-500 text-white', dot: 'bg-amber-500' },
                  'LOW': { bg: 'bg-emerald-50', border: 'border-emerald-200', badge: 'bg-emerald-500 text-white', dot: 'bg-emerald-500' },
                };
                const style = levelStyles[alertLevel] || levelStyles['MEDIUM'];

                return (
                  <div key={idx} className={`${style.bg} ${style.border} border rounded-xl p-3 transition-all hover:shadow-sm`}>
                    <div className="flex items-start gap-3">
                      {/* Alert Indicator */}
                      <div className={`w-2 h-2 ${style.dot} rounded-full mt-1.5 flex-shrink-0`} />

                      <div className="flex-1 min-w-0">
                        {/* Header Row */}
                        <div className="flex items-center justify-between gap-2 mb-1">
                          <div className="flex items-center gap-1.5">
                            <span className={`px-1.5 py-0.5 ${style.badge} text-[9px] font-semibold rounded`}>
                              {alertLevel}
                            </span>
                            <span className="text-[10px] text-gray-600 font-medium capitalize">
                              {disasterInfo.label}
                            </span>
                          </div>
                          {timestamp && (
                            <span className="text-[9px] text-gray-400">
                              {formatTimestamp(timestamp)}
                            </span>
                          )}
                        </div>

                        {/* Content */}
                        <p className="text-xs text-gray-700 line-clamp-2 leading-relaxed">{text}</p>

                        {/* Location */}
                        {location && (
                          <div className="flex items-center gap-1 mt-1.5">
                            <MapPin className="w-3 h-3 text-gray-400" />
                            <span className="text-[10px] text-gray-500 truncate">{location}</span>
                          </div>
                        )}
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* Clean Footer */}
        {displayItems.length > 0 && (
          <div className="px-4 py-2.5 border-t border-gray-100 bg-gray-50/50">
            <div className="flex items-center justify-between">
              <span className="text-[10px] text-gray-500">
                {displayItems.length} alert{displayItems.length !== 1 ? 's' : ''} detected
              </span>
              {displayItems.length > maxAlerts && (
                <button
                  onClick={() => setShowAllAlerts(!showAllAlerts)}
                  className="text-[10px] text-[#0d4a6f] hover:text-[#083a57] font-medium flex items-center gap-0.5"
                >
                  {showAllAlerts ? 'Show less' : `View ${displayItems.length - maxAlerts} more`}
                  <ChevronRight className={`w-3 h-3 transition-transform ${showAllAlerts ? 'rotate-90' : ''}`} />
                </button>
              )}
            </div>
          </div>
        )}
      </div>
    );
  }

  // Full variant for analyst page
  return (
    <div className="space-y-4">
      {/* Stats Row */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <StatCard title="Total Detections" value={recentPosts.length} icon={MessageSquare} color="ocean" />
        <StatCard title="Critical Alerts" value={criticalCount} icon={AlertTriangle} color="red" highlight={criticalCount > 0} />
        <StatCard title="Monitoring" value={Object.keys(stats).length || 5} icon={Globe} color="green" />
        <StatCard
          title="Flagged"
          value={recentPosts.filter(p =>
            p.misinformation_analysis?.risk_level &&
            p.misinformation_analysis.risk_level !== 'minimal'
          ).length}
          icon={Shield}
          color="amber"
        />
      </div>

      {/* Posts List */}
      <div className="bg-white rounded-2xl border border-gray-100 overflow-hidden">
        <div className="px-4 py-3 border-b border-gray-100 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 bg-[#0d4a6f] rounded-lg flex items-center justify-center">
              <Waves className="w-4 h-4 text-white" />
            </div>
            <div>
              <h3 className="text-sm font-semibold text-gray-900">Live Feed</h3>
              <div className="flex items-center gap-1.5">
                <span className="w-1.5 h-1.5 bg-green-500 rounded-full animate-pulse" />
                <span className="text-[10px] text-gray-500">Real-time</span>
                {isDemoMode && (
                  <span className="px-1.5 py-0.5 bg-purple-100 text-purple-600 rounded text-[9px] font-medium">
                    DEMO
                  </span>
                )}
              </div>
            </div>
          </div>
          <button onClick={handleRefresh} disabled={isRefreshing} className="p-2 text-gray-400 hover:text-[#0d4a6f] hover:bg-gray-50 rounded-lg disabled:opacity-50 transition-colors">
            <RefreshCw className={`w-4 h-4 ${isRefreshing ? 'animate-spin' : ''}`} />
          </button>
        </div>

        <div className="max-h-[350px] overflow-y-auto">
          {recentPosts.length === 0 ? (
            <div className="p-8 text-center">
              <div className="w-14 h-14 mx-auto mb-3 bg-emerald-50 rounded-xl flex items-center justify-center">
                <CheckCircle className="w-7 h-7 text-emerald-500" />
              </div>
              <p className="text-gray-800 font-medium text-sm">No Hazard Posts Detected</p>
              <p className="text-gray-400 text-xs mt-1">System actively monitoring social media</p>
            </div>
          ) : (
            <div className="p-2 space-y-2">
              {recentPosts.map((post, idx) => <PostRow key={idx} post={post} />)}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

// Helper Components
function StatCard({ title, value, icon: Icon, color, highlight }) {
  const colors = {
    ocean: 'bg-[#e8f4fc] text-[#0d4a6f]',
    blue: 'bg-blue-100 text-blue-600',
    red: 'bg-red-100 text-red-600',
    green: 'bg-green-100 text-green-600',
    amber: 'bg-amber-100 text-amber-600',
  };

  return (
    <div className={`bg-white rounded-xl border p-3 md:p-4 ${highlight ? 'border-red-300 bg-red-50' : 'border-gray-200'}`}>
      <div className="flex items-center justify-between mb-2">
        <div className={`p-2 rounded-lg ${colors[color]}`}>
          <Icon className="w-4 h-4" />
        </div>
        {highlight && <span className="w-2 h-2 bg-red-500 rounded-full animate-pulse" />}
      </div>
      <p className="text-xl md:text-2xl font-bold text-gray-900">{value}</p>
      <p className="text-xs text-gray-600 truncate">{title}</p>
    </div>
  );
}

function PostRow({ post }) {
  const alertLevel = post.alert_level || 'LOW';
  const disasterType = post.analysis?.disaster_type || post.disaster_type || 'unknown';
  const disasterInfo = getDisasterTypeInfo(disasterType);
  const originalPost = post.original_post || post;
  const user = originalPost.user || {};

  // Clean color scheme based on alert level
  const levelStyles = {
    'HIGH': { bg: 'bg-red-50', border: 'border-red-200', badge: 'bg-red-500 text-white', dot: 'bg-red-500' },
    'CRITICAL': { bg: 'bg-red-50', border: 'border-red-200', badge: 'bg-red-500 text-white', dot: 'bg-red-500' },
    'MEDIUM': { bg: 'bg-amber-50', border: 'border-amber-200', badge: 'bg-amber-500 text-white', dot: 'bg-amber-500' },
    'LOW': { bg: 'bg-emerald-50', border: 'border-emerald-200', badge: 'bg-emerald-500 text-white', dot: 'bg-emerald-500' },
  };
  const style = levelStyles[alertLevel] || levelStyles['LOW'];

  return (
    <div className={`${style.bg} ${style.border} border rounded-xl p-3 transition-all hover:shadow-sm`}>
      <div className="flex items-start gap-3">
        {/* User Avatar */}
        <div className="w-8 h-8 bg-[#0d4a6f] rounded-lg flex items-center justify-center text-white font-semibold flex-shrink-0 text-xs">
          {user.username?.[0]?.toUpperCase() || 'U'}
        </div>

        <div className="flex-1 min-w-0">
          {/* Header */}
          <div className="flex items-center justify-between gap-2 mb-1">
            <div className="flex items-center gap-1.5">
              <span className="font-medium text-gray-900 text-xs truncate">
                {user.username || 'Anonymous'}
              </span>
              <span className="text-[10px] text-gray-400">{originalPost.platform || 'social'}</span>
            </div>
            <div className="flex items-center gap-1.5">
              <span className={`px-1.5 py-0.5 ${style.badge} text-[9px] font-semibold rounded`}>
                {alertLevel}
              </span>
              <span className="text-[10px] text-gray-600 font-medium capitalize">
                {disasterInfo.label}
              </span>
            </div>
          </div>

          {/* Content */}
          <p className="text-xs text-gray-700 line-clamp-2 leading-relaxed mb-1.5">{originalPost.text || post.text}</p>

          {/* Footer */}
          <div className="flex items-center justify-between">
            {originalPost.location && (
              <span className="flex items-center gap-1 text-[10px] text-gray-500">
                <MapPin className="w-3 h-3" />
                <span className="truncate max-w-[150px]">{originalPost.location}</span>
              </span>
            )}
            <span className="text-[9px] text-gray-400">{formatTimestamp(originalPost.timestamp)}</span>
          </div>
        </div>
      </div>
    </div>
  );
}
