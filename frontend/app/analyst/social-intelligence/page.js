'use client';

import { useState, useEffect, useRef } from 'react';
import { useRouter } from 'next/navigation';
import dynamic from 'next/dynamic';
import useAuthStore from '@/context/AuthContext';
import DashboardLayout from '@/components/DashboardLayout';
import PageHeader from '@/components/PageHeader';
import { motion } from 'framer-motion';
import {
  Activity,
  AlertTriangle,
  RefreshCw,
  Globe,
  MessageSquare,
  Shield,
  AlertCircle,
  CheckCircle,
  XCircle,
  MapPin,
  BarChart3,
  Zap,
  Radio,
  Loader2,
  Wifi,
  WifiOff,
  ThumbsUp,
  Share2,
  MessageCircle,
  Filter,
  TrendingUp,
  Beaker,
  ExternalLink,
  Play,
  Square,
  Waves,
  Eye,
  Clock
} from 'lucide-react';
import toast from 'react-hot-toast';
import {
  getPublicHealth,
  getPublicFeed,
  getPublicAlerts,
  getEnhancedFeedPosts,
  getActiveAlerts,
  getDisasterStats,
  getPlatformStats,
  startEnhancedFeed,
  getUrgencyColor,
  getDisasterTypeInfo,
  getMisinfoRiskColor,
  formatTimestamp,
  getLanguageDisplay,
  // Demo mode APIs
  getPublicDemoStatus,
  startPublicDemoMode,
  stopPublicDemoMode,
  getPublicDemoFeed,
  getPublicDemoAlerts
} from '@/lib/smiApi';

// Animation variants
const fadeInUp = {
  hidden: { opacity: 0, y: 20 },
  visible: { opacity: 1, y: 0, transition: { duration: 0.4 } }
};

const staggerContainer = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: { staggerChildren: 0.08 }
  }
};

const scaleIn = {
  hidden: { opacity: 0, scale: 0.95 },
  visible: { opacity: 1, scale: 1, transition: { duration: 0.3 } }
};

// ==================== MISINFORMATION DETECTION ====================
const MISINFO_PATTERNS = {
  sensational: [
    'breaking', 'urgent', 'emergency', 'critical', 'alert', 'warning',
    'disaster', 'catastrophe', 'unprecedented', 'massive', 'devastating',
    'apocalyptic', 'end of world', 'biblical', 'never seen before',
    'category 3', 'category 4', 'category 5', 'extreme danger',
    'आपातकालीन', 'खतरा', 'तबाही', 'विनाशकारी', 'भयंकर', 'आपदा', 'चेतावनी',
    'அவசரம்', 'ஆபத்து', 'பேரழிவு', 'எச்சரிக்கை',
    'आपातकाल', 'संकट'
  ],
  exaggeration: [
    'hundreds dead', 'thousands missing', 'total destruction',
    'completely wiped out', 'nothing left', 'everything destroyed',
    'worst ever', 'historic disaster', 'never happened before',
    'total evacuation', 'complete chaos'
  ],
  conspiracy: [
    'cover up', 'government hiding', 'media blackout', 'conspiracy',
    'they dont want you to know', 'secret', 'hidden truth',
    'wake up people', 'open your eyes', 'mainstream media lies'
  ],
  emotional: [
    'share before deleted', 'must watch', 'shocking truth',
    'you wont believe', 'real truth', 'please share',
    'spread the word', 'before its too late', 'save lives'
  ]
};

function detectMisinformation(text) {
  if (!text) return { risk_level: 'minimal', confidence_score: 0, flags: [] };

  const textLower = text.toLowerCase();
  const flags = [];
  let score = 0;

  const sensationalMatches = MISINFO_PATTERNS.sensational.filter(p =>
    textLower.includes(p.toLowerCase())
  );
  if (sensationalMatches.length >= 3) {
    flags.push('excessive_sensational_language');
    score += 0.3;
  } else if (sensationalMatches.length >= 2) {
    flags.push('multiple_sensational_terms');
    score += 0.2;
  } else if (sensationalMatches.length >= 1) {
    flags.push('sensational_language');
    score += 0.1;
  }

  if (MISINFO_PATTERNS.exaggeration.some(p => textLower.includes(p))) {
    flags.push('exaggerated_claims');
    score += 0.15;
  }

  if (MISINFO_PATTERNS.conspiracy.some(p => textLower.includes(p))) {
    flags.push('conspiracy_language');
    score += 0.25;
  }

  if (MISINFO_PATTERNS.emotional.some(p => textLower.includes(p))) {
    flags.push('emotional_manipulation');
    score += 0.15;
  }

  if (text.length > 15) {
    const capsRatio = (text.match(/[A-Z]/g) || []).length / text.length;
    if (capsRatio > 0.35) {
      flags.push('excessive_caps');
      score += 0.15;
    }
  }

  const exclamationCount = (text.match(/!/g) || []).length;
  if (exclamationCount >= 3) {
    flags.push('excessive_exclamation');
    score += 0.1;
  }

  let risk_level = 'minimal';
  if (score >= 0.35) risk_level = 'high';
  else if (score >= 0.2) risk_level = 'moderate';
  else if (score >= 0.1) risk_level = 'low';

  return {
    risk_level,
    confidence_score: Math.min(score, 1),
    flags
  };
}

// ==================== SKELETON LOADERS ====================
function SkeletonStatCard() {
  return (
    <div className="bg-white rounded-2xl border border-slate-100 p-4 animate-pulse shadow-sm">
      <div className="flex items-center gap-3 mb-3">
        <div className="w-12 h-12 bg-slate-200 rounded-xl"></div>
        <div className="flex-1">
          <div className="h-3 bg-slate-200 rounded w-20 mb-2"></div>
          <div className="h-6 bg-slate-100 rounded w-12"></div>
        </div>
      </div>
    </div>
  );
}

function SkeletonPostCard() {
  return (
    <div className="bg-white rounded-2xl border border-slate-100 p-4 animate-pulse shadow-sm">
      <div className="flex items-start gap-3">
        <div className="w-11 h-11 bg-slate-200 rounded-full flex-shrink-0"></div>
        <div className="flex-1 space-y-3">
          <div className="flex items-center gap-2">
            <div className="h-4 bg-slate-200 rounded w-28"></div>
            <div className="h-3 bg-slate-100 rounded w-20"></div>
          </div>
          <div className="h-4 bg-slate-200 rounded w-full"></div>
          <div className="h-4 bg-slate-200 rounded w-4/5"></div>
          <div className="flex gap-2">
            <div className="h-6 bg-slate-200 rounded-full w-20"></div>
            <div className="h-6 bg-slate-100 rounded-full w-16"></div>
          </div>
        </div>
      </div>
    </div>
  );
}

function SkeletonAlertCard() {
  return (
    <div className="p-3 rounded-xl bg-slate-50 animate-pulse">
      <div className="flex items-center gap-2 mb-2">
        <div className="w-5 h-5 bg-slate-200 rounded"></div>
        <div className="h-4 bg-slate-200 rounded w-24"></div>
      </div>
      <div className="h-3 bg-slate-100 rounded w-32"></div>
    </div>
  );
}

// Dynamic import for ApexCharts
const Chart = dynamic(() => import('react-apexcharts'), { ssr: false });

export default function SocialIntelligenceDashboard() {
  const router = useRouter();
  const { user } = useAuthStore();

  // System state
  const [isConnected, setIsConnected] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [lastRefresh, setLastRefresh] = useState(null);

  // Data state
  const [posts, setPosts] = useState([]);
  const [alerts, setAlerts] = useState([]);
  const [disasterStats, setDisasterStats] = useState({});
  const [platformStats, setPlatformStats] = useState({});

  // UI state
  const [selectedPost, setSelectedPost] = useState(null);
  const [filterAlertLevel, setFilterAlertLevel] = useState('all');
  const [filterDisaster, setFilterDisaster] = useState('all');

  // Demo mode state
  const [isDemoMode, setIsDemoMode] = useState(false);
  const [demoLoading, setDemoLoading] = useState(false);

  // Refs
  const refreshInterval = useRef(null);

  // Check authorization
  useEffect(() => {
    if (user && !['analyst', 'authority_admin'].includes(user.role)) {
      router.push('/dashboard');
    }
  }, [user, router]);

  // Check SMI system health on mount
  useEffect(() => {
    checkSystemHealth();
  }, []);

  const checkSystemHealth = async () => {
    try {
      const publicHealth = await getPublicHealth();
      const isOnline = publicHealth.status === 'healthy' || publicHealth.is_connected === true;

      if (!isOnline) {
        console.log('SMI service offline based on public health check');
        setIsConnected(false);
        toast.error('Social Media Intelligence system is offline');
        setIsLoading(false);
        return;
      }

      setIsConnected(true);
      await fetchAllData();
    } catch (error) {
      console.error('SMI system not available:', error);
      setIsConnected(false);
      toast.error('Social Media Intelligence system is offline');
    } finally {
      setIsLoading(false);
    }
  };

  const fetchAllData = async () => {
    try {
      startEnhancedFeed().catch(() => {});

      const [postsRes, alertsRes, disasterRes, platformRes] = await Promise.all([
        getEnhancedFeedPosts(100).catch(() => null),
        getActiveAlerts().catch(() => null),
        getDisasterStats().catch(() => null),
        getPlatformStats().catch(() => null)
      ]);

      let finalPostsRes = postsRes;
      let finalAlertsRes = alertsRes;

      if (!postsRes || !alertsRes) {
        const [publicPosts, publicAlerts] = await Promise.all([
          !postsRes ? getPublicFeed(50).catch(() => ({ posts: [] })) : Promise.resolve(null),
          !alertsRes ? getPublicAlerts(50).catch(() => ({ alerts: [] })) : Promise.resolve(null)
        ]);
        if (publicPosts) finalPostsRes = publicPosts;
        if (publicAlerts) finalAlertsRes = publicAlerts;
      }

      const postsArray = Array.isArray(finalPostsRes) ? finalPostsRes : (finalPostsRes?.posts || []);
      const postsWithMisinfo = postsArray.map(post => {
        const text = post.original_post?.text || post.text || '';
        const misinfoAnalysis = post.misinformation_analysis || detectMisinformation(text);
        return {
          ...post,
          misinformation_analysis: misinfoAnalysis
        };
      });
      setPosts(postsWithMisinfo);

      const alertsArray = finalAlertsRes?.alerts || [];
      setAlerts(Array.isArray(alertsArray) ? alertsArray : []);

      setDisasterStats(disasterRes?.statistics || disasterRes || {});
      setPlatformStats(platformRes?.statistics || platformRes || {});

      setLastRefresh(new Date());
    } catch (error) {
      console.error('Error fetching data:', error);
    }
  };

  const fetchLatestData = async () => {
    if (!isConnected) return;

    try {
      let [postsRes, alertsRes] = await Promise.all([
        getEnhancedFeedPosts(100).catch(() => null),
        getActiveAlerts().catch(() => null)
      ]);

      if (!postsRes || !alertsRes) {
        const [publicPosts, publicAlerts] = await Promise.all([
          !postsRes ? getPublicFeed(50).catch(() => ({ posts: [] })) : Promise.resolve(null),
          !alertsRes ? getPublicAlerts(50).catch(() => ({ alerts: [] })) : Promise.resolve(null)
        ]);
        if (publicPosts) postsRes = publicPosts;
        if (publicAlerts) alertsRes = publicAlerts;
      }

      const newPosts = Array.isArray(postsRes) ? postsRes : (postsRes?.posts || []);
      const postsWithMisinfo = newPosts.map(post => {
        const text = post.original_post?.text || post.text || '';
        const misinfoAnalysis = post.misinformation_analysis || detectMisinformation(text);
        return { ...post, misinformation_analysis: misinfoAnalysis };
      });

      if (postsWithMisinfo.length > 0) {
        setPosts(prev => {
          const existingIds = new Set(prev.map(p => p.post_id || p.id));
          const uniqueNew = postsWithMisinfo.filter(p => !existingIds.has(p.post_id || p.id));
          return [...uniqueNew, ...prev].slice(0, 100);
        });
      }

      const alertsArray = alertsRes?.alerts || [];
      setAlerts(Array.isArray(alertsArray) ? alertsArray : []);

      setLastRefresh(new Date());
    } catch (error) {
      console.error('Error fetching latest data:', error);
    }
  };

  // Demo mode functions
  const checkDemoStatus = async () => {
    try {
      const status = await getPublicDemoStatus();
      setIsDemoMode(status.is_running === true);
    } catch (error) {
      console.error('Error checking demo status:', error);
    }
  };

  const toggleDemoMode = async () => {
    setDemoLoading(true);
    try {
      if (isDemoMode) {
        await stopPublicDemoMode();
        setIsDemoMode(false);
        toast.success('Demo mode stopped - Switching to live BlueRadar feed');
        await fetchAllData();
      } else {
        const result = await startPublicDemoMode({ post_interval: 5, disaster_probability: 0.7 });
        if (result.success || result.mode === 'demo') {
          setIsDemoMode(true);
          toast.success('Demo mode started - LLM-simulated posts active');
          await fetchDemoData();
        } else {
          toast.error(result.error || 'Failed to start demo mode');
        }
      }
    } catch (error) {
      console.error('Error toggling demo mode:', error);
      toast.error('Failed to toggle demo mode');
    } finally {
      setDemoLoading(false);
    }
  };

  const fetchDemoData = async () => {
    try {
      const [demoPostsRes, demoAlertsRes] = await Promise.all([
        getPublicDemoFeed(50).catch(() => ({ posts: [] })),
        getPublicDemoAlerts(50).catch(() => ({ alerts: [] }))
      ]);

      const postsArray = demoPostsRes.posts || [];

      const postsWithMisinfo = postsArray.map((post) => {
        const text = post.original_post?.text || post.text || '';
        const misinfoAnalysis = post.misinformation_analysis || detectMisinformation(text);

        return {
          ...post,
          misinformation_analysis: misinfoAnalysis,
          author: post.author || 'Demo Simulation'
        };
      });
      setPosts(postsWithMisinfo);
      setAlerts(demoAlertsRes.alerts || []);
      setLastRefresh(new Date());
    } catch (error) {
      console.error('Error fetching demo data:', error);
    }
  };

  // Check demo status on mount
  useEffect(() => {
    checkDemoStatus();
  }, []);

  // Auto-refresh effect
  useEffect(() => {
    if (refreshInterval.current) {
      clearInterval(refreshInterval.current);
    }

    if (isDemoMode) {
      fetchDemoData();
    }

    const interval = isDemoMode ? 8000 : 10000;
    refreshInterval.current = setInterval(() => {
      if (isDemoMode) {
        fetchDemoData();
      } else {
        fetchLatestData();
      }
    }, interval);

    return () => {
      if (refreshInterval.current) {
        clearInterval(refreshInterval.current);
      }
    };
  }, [isDemoMode]);

  // Filter posts
  const filteredPosts = posts.filter(post => {
    if (filterAlertLevel !== 'all' && post.alert_level !== filterAlertLevel) return false;
    if (filterDisaster !== 'all') {
      const disasterType = post.analysis?.disaster_type || post.disaster_type;
      if (disasterType !== filterDisaster) return false;
    }
    return true;
  });

  // Stats calculations
  const disasterPosts = posts.filter(p => {
    const type = p.disaster_type || p.analysis?.disaster_type;
    return type && type !== 'none';
  });
  const criticalPosts = posts.filter(p => p.alert_level === 'HIGH' || p.alert_level === 'CRITICAL').length;
  const misinfoFlagged = posts.filter(p => {
    const risk = p.misinformation_analysis?.risk_level;
    return risk && risk !== 'minimal';
  }).length;

  // Debug logging
  if (posts.length > 0 && typeof window !== 'undefined') {
    console.log('📊 Stats:', {
      total: posts.length,
      disaster: disasterPosts.length,
      critical: criticalPosts,
      misinfo: misinfoFlagged,
      alerts: alerts.length
    });
  }

  // Chart data
  const getDisasterChartData = () => {
    const labels = [];
    const values = [];

    Object.entries(disasterStats).forEach(([key, value]) => {
      if (key === 'none' || key === 'period_days') return;

      const label = getDisasterTypeInfo(key).label;
      const count = typeof value === 'object' ? (value.count || 0) : (typeof value === 'number' ? value : 0);

      if (count > 0) {
        labels.push(label);
        values.push(count);
      }
    });

    return { labels, values };
  };

  const chartData = getDisasterChartData();

  const disasterChartOptions = {
    chart: { type: 'donut', fontFamily: 'inherit' },
    labels: chartData.labels,
    colors: ['#0d4a6f', '#1a6b9a', '#4391c4', '#F59E0B', '#EF4444', '#8B5CF6'],
    legend: { position: 'bottom', fontSize: '11px' },
    dataLabels: { enabled: true, formatter: (val) => `${val.toFixed(0)}%` },
    plotOptions: {
      pie: {
        donut: {
          size: '65%',
          labels: { show: true, total: { show: true, label: 'Total', fontSize: '14px' } }
        }
      }
    }
  };
  const disasterChartSeries = chartData.values;

  // Alert level distribution
  const alertLevelCounts = {
    HIGH: posts.filter(p => p.alert_level === 'HIGH' || p.alert_level === 'CRITICAL').length,
    MEDIUM: posts.filter(p => p.alert_level === 'MEDIUM').length,
    LOW: posts.filter(p => p.alert_level === 'LOW').length,
  };

  const priorityChartOptions = {
    chart: { type: 'bar', fontFamily: 'inherit', toolbar: { show: false } },
    colors: ['#EF4444', '#F97316', '#10B981'],
    plotOptions: {
      bar: {
        horizontal: true,
        distributed: true,
        borderRadius: 6,
        barHeight: '60%'
      }
    },
    xaxis: {
      categories: ['High/Critical', 'Medium', 'Low']
    },
    legend: { show: false },
    dataLabels: { enabled: true, style: { fontSize: '12px', fontWeight: 600 } },
    grid: { borderColor: '#f1f5f9' }
  };
  const priorityChartSeries = [{ data: Object.values(alertLevelCounts) }];

  // Loading state
  if (isLoading) {
    return (
      <DashboardLayout>
        <div className="p-4 lg:p-6 space-y-6">
          {/* Header Skeleton */}
          <div className="bg-white rounded-2xl border border-slate-100 p-6 animate-pulse shadow-sm">
            <div className="flex flex-col lg:flex-row justify-between items-start lg:items-center gap-4">
              <div className="flex items-center gap-4">
                <div className="w-14 h-14 bg-slate-200 rounded-xl"></div>
                <div className="space-y-2">
                  <div className="h-7 w-56 bg-slate-200 rounded"></div>
                  <div className="h-4 w-72 bg-slate-100 rounded"></div>
                </div>
              </div>
              <div className="flex items-center gap-3">
                <div className="h-9 w-28 bg-slate-200 rounded-full"></div>
                <div className="h-9 w-32 bg-slate-200 rounded-full"></div>
              </div>
            </div>
          </div>

          {/* Stats Grid Skeleton */}
          <div className="grid grid-cols-2 lg:grid-cols-5 gap-4">
            {[1, 2, 3, 4, 5].map(i => <SkeletonStatCard key={i} />)}
          </div>

          {/* Main Content Skeleton */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            <div className="lg:col-span-2 space-y-4">
              {[1, 2, 3].map(i => <SkeletonPostCard key={i} />)}
            </div>
            <div className="space-y-4">
              {[1, 2, 3].map(i => <SkeletonAlertCard key={i} />)}
            </div>
          </div>
        </div>
      </DashboardLayout>
    );
  }

  // Offline state
  if (!isConnected) {
    return (
      <DashboardLayout>
        <div className="flex items-center justify-center min-h-[70vh] p-6">
          <motion.div
            initial={{ opacity: 0, scale: 0.9 }}
            animate={{ opacity: 1, scale: 1 }}
            className="text-center max-w-md bg-white rounded-3xl shadow-xl border border-slate-100 p-10"
          >
            <div className="w-20 h-20 bg-red-100 rounded-full flex items-center justify-center mx-auto mb-6">
              <WifiOff className="w-10 h-10 text-red-500" />
            </div>
            <h2 className="text-2xl font-bold text-slate-900 mb-3">SMI System Offline</h2>
            <p className="text-slate-600 mb-8 leading-relaxed">
              The Social Media Intelligence system is not available. Please ensure the BlueRadar service is running on port 8001.
            </p>
            <button
              onClick={checkSystemHealth}
              className="inline-flex items-center gap-2 px-8 py-4 bg-gradient-to-r from-[#0d4a6f] to-[#1a6b9a] text-white rounded-xl hover:shadow-lg hover:shadow-[#0d4a6f]/20 transition-all font-medium"
            >
              <RefreshCw className="w-5 h-5" />
              Retry Connection
            </button>
          </motion.div>
        </div>
      </DashboardLayout>
    );
  }

  return (
    <DashboardLayout>
      <div className="p-4 lg:p-6 pb-24 lg:pb-6">
        {/* Page Header - Desktop Only */}
        <PageHeader />

        <motion.div
          className="space-y-6"
          initial="hidden"
          animate="visible"
          variants={staggerContainer}
        >
        {/* Hero Header Card */}
        <motion.div
          variants={fadeInUp}
          className="bg-white rounded-2xl shadow-sm border border-slate-100 overflow-hidden"
        >
          {/* Gradient Header */}
          <div className="bg-gradient-to-r from-[#0d4a6f] via-[#1a6b9a] to-[#0d4a6f] p-6 text-white relative overflow-hidden">
            {/* Decorative Wave */}
            <div className="absolute bottom-0 left-0 right-0 opacity-10">
              <svg viewBox="0 0 1440 120" className="w-full h-12">
                <path fill="white" d="M0,32L48,37.3C96,43,192,53,288,58.7C384,64,480,64,576,58.7C672,53,768,43,864,48C960,53,1056,75,1152,80C1248,85,1344,75,1392,69.3L1440,64L1440,120L1392,120C1344,120,1248,120,1152,120C1056,120,960,120,864,120C768,120,672,120,576,120C480,120,384,120,288,120C192,120,96,120,48,120L0,120Z"></path>
              </svg>
            </div>
            <div className="absolute top-4 right-6 opacity-15">
              <Radio className="w-24 h-24" />
            </div>

            <div className="flex flex-col lg:flex-row justify-between items-start lg:items-center gap-4 relative z-10">
              <div className="flex items-center gap-4">
                <div className="w-14 h-14 bg-white/20 backdrop-blur-sm rounded-xl flex items-center justify-center">
                  <Radio className="w-7 h-7 text-white" />
                </div>
                <div>
                  <h1 className="text-2xl lg:text-3xl font-bold">Social Media Intelligence</h1>
                  <p className="text-white/80 mt-1">Real-time multilingual disaster monitoring & analysis</p>
                </div>
              </div>

              <div className="flex items-center gap-3 flex-wrap">
                {/* Connection Status */}
                <div className="flex items-center gap-2 px-4 py-2 rounded-full text-sm bg-white/20 backdrop-blur-sm">
                  <Wifi className="w-4 h-4" />
                  <span className="font-medium">Connected</span>
                  <span className="w-2 h-2 bg-emerald-400 rounded-full animate-pulse" />
                </div>

                {/* Live Indicator */}
                <div className={`flex items-center gap-2 px-4 py-2 rounded-full text-sm font-medium ${isDemoMode ? 'bg-purple-500/30' : 'bg-emerald-500/30'}`}>
                  <Activity className="w-4 h-4 animate-pulse" />
                  {isDemoMode ? 'Demo Mode' : 'Live Monitoring'}
                </div>
              </div>
            </div>
          </div>

          {/* Action Bar */}
          <div className="p-4 bg-slate-50/50 border-t border-slate-100 flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
            <div className="flex items-center gap-4 text-sm text-slate-600">
              {lastRefresh && (
                <div className="flex items-center gap-2">
                  <Clock className="w-4 h-4" />
                  <span>Updated: {lastRefresh.toLocaleTimeString()}</span>
                </div>
              )}
            </div>

            <div className="flex items-center gap-3">
              {/* Demo Mode Toggle */}
              <button
                onClick={toggleDemoMode}
                disabled={demoLoading}
                className={`flex items-center gap-2 px-5 py-2.5 rounded-xl transition-all font-medium ${
                  isDemoMode
                    ? 'bg-purple-600 text-white hover:bg-purple-700 shadow-lg shadow-purple-600/20'
                    : 'bg-slate-100 text-slate-700 hover:bg-slate-200 border border-slate-200'
                } ${demoLoading ? 'opacity-50 cursor-not-allowed' : ''}`}
              >
                {demoLoading ? (
                  <Loader2 className="w-4 h-4 animate-spin" />
                ) : isDemoMode ? (
                  <Square className="w-4 h-4" />
                ) : (
                  <Play className="w-4 h-4" />
                )}
                {isDemoMode ? 'Stop Demo' : 'Start Demo'}
              </button>

              {/* Refresh Button */}
              <button
                onClick={isDemoMode ? fetchDemoData : fetchAllData}
                className="flex items-center gap-2 px-5 py-2.5 bg-gradient-to-r from-[#0d4a6f] to-[#1a6b9a] text-white rounded-xl hover:shadow-lg hover:shadow-[#0d4a6f]/20 transition-all font-medium"
              >
                <RefreshCw className="w-4 h-4" />
                Refresh
              </button>
            </div>
          </div>
        </motion.div>

        {/* Stats Grid */}
        <motion.div
          variants={fadeInUp}
          className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-4"
        >
          <StatCard
            title="Total Analyzed"
            value={posts.length}
            icon={MessageSquare}
            gradient="from-[#0d4a6f] to-[#1a6b9a]"
            bgLight="bg-[#e8f4fc]"
          />
          <StatCard
            title="Disaster Related"
            value={disasterPosts.length}
            icon={AlertTriangle}
            gradient="from-amber-500 to-orange-500"
            bgLight="bg-amber-50"
          />
          <StatCard
            title="Critical Alerts"
            value={criticalPosts}
            icon={Zap}
            gradient="from-red-500 to-red-600"
            bgLight="bg-red-50"
            highlight={criticalPosts > 0}
          />
          <StatCard
            title="Misinfo Flagged"
            value={misinfoFlagged}
            icon={Shield}
            gradient="from-purple-500 to-purple-600"
            bgLight="bg-purple-50"
            highlight={misinfoFlagged > 0}
          />
          <StatCard
            title="Active Alerts"
            value={alerts.length}
            icon={AlertCircle}
            gradient="from-emerald-500 to-emerald-600"
            bgLight="bg-emerald-50"
          />
        </motion.div>

        {/* Main Content Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Live Feed - Takes 2 columns */}
          <motion.div variants={fadeInUp} className="lg:col-span-2 space-y-4">
            {/* Feed Header with Filters */}
            <div className="bg-white rounded-2xl border border-slate-100 shadow-sm p-4">
              <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 bg-gradient-to-br from-emerald-500 to-emerald-600 rounded-xl flex items-center justify-center">
                    <Activity className="w-5 h-5 text-white" />
                  </div>
                  <div>
                    <h3 className="text-lg font-semibold text-slate-900">Live Social Feed</h3>
                    <div className="flex items-center gap-2 text-sm text-slate-500">
                      <span className="w-2 h-2 bg-emerald-500 rounded-full animate-pulse"></span>
                      <span>Real-time updates</span>
                    </div>
                  </div>
                </div>
                <div className="flex items-center gap-3">
                  <div className="flex items-center gap-2 text-slate-500">
                    <Filter className="w-4 h-4" />
                  </div>
                  <select
                    value={filterAlertLevel}
                    onChange={(e) => setFilterAlertLevel(e.target.value)}
                    className="px-4 py-2 border border-slate-200 rounded-xl text-sm focus:ring-2 focus:ring-[#0d4a6f]/20 focus:border-[#0d4a6f] transition-all bg-white"
                  >
                    <option value="all">All Alerts</option>
                    <option value="HIGH">High Priority</option>
                    <option value="MEDIUM">Medium Priority</option>
                    <option value="LOW">Low Priority</option>
                  </select>
                  <select
                    value={filterDisaster}
                    onChange={(e) => setFilterDisaster(e.target.value)}
                    className="px-4 py-2 border border-slate-200 rounded-xl text-sm focus:ring-2 focus:ring-[#0d4a6f]/20 focus:border-[#0d4a6f] transition-all bg-white"
                  >
                    <option value="all">All Types</option>
                    <option value="tsunami">Tsunami</option>
                    <option value="cyclone">Cyclone</option>
                    <option value="flooding">Flooding</option>
                    <option value="oil_spill">Oil Spill</option>
                    <option value="earthquake">Earthquake</option>
                    <option value="none">Normal</option>
                  </select>
                </div>
              </div>
            </div>

            {/* Posts List */}
            <div className="space-y-4 overflow-y-auto pr-1 scrollbar-thin">
              {filteredPosts.length === 0 ? (
                <motion.div
                  variants={scaleIn}
                  className="bg-white rounded-2xl border border-slate-100 shadow-sm p-12 text-center"
                >
                  <div className="w-16 h-16 bg-slate-100 rounded-full flex items-center justify-center mx-auto mb-4">
                    <MessageSquare className="w-8 h-8 text-slate-400" />
                  </div>
                  <h3 className="text-lg font-semibold text-slate-900 mb-2">No posts detected yet</h3>
                  <p className="text-slate-500">Data will appear as it's analyzed by our AI system.</p>
                </motion.div>
              ) : (
                filteredPosts.map((post, index) => (
                  <motion.div
                    key={post.post_id || post.id || index}
                    variants={scaleIn}
                    whileHover={{ scale: 1.01 }}
                  >
                    <PostCard
                      post={post}
                      onClick={() => setSelectedPost(post)}
                    />
                  </motion.div>
                ))
              )}
            </div>
          </motion.div>

          {/* Right Sidebar - Analytics */}
          <motion.div variants={fadeInUp} className="space-y-6 lg:sticky lg:top-6 lg:self-start">
            {/* Active Alerts Panel */}
            <div className="bg-white rounded-2xl border border-slate-100 shadow-sm overflow-hidden">
              <div className="p-5 border-b border-slate-100 bg-gradient-to-r from-red-50 to-orange-50">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 bg-gradient-to-br from-red-500 to-orange-500 rounded-xl flex items-center justify-center">
                      <AlertTriangle className="w-5 h-5 text-white" />
                    </div>
                    <div>
                      <h3 className="text-lg font-semibold text-slate-900">Active Alerts</h3>
                      <p className="text-sm text-slate-500">Real-time notifications</p>
                    </div>
                  </div>
                  <span className="px-3 py-1 bg-red-100 text-red-700 text-sm font-bold rounded-full">
                    {alerts.length}
                  </span>
                </div>
              </div>
              <div className="p-4 space-y-3 max-h-[320px] overflow-y-auto">
                {alerts.length === 0 ? (
                  <div className="text-center py-8">
                    <div className="w-14 h-14 bg-emerald-100 rounded-full flex items-center justify-center mx-auto mb-3">
                      <CheckCircle className="w-7 h-7 text-emerald-500" />
                    </div>
                    <p className="text-slate-600 font-medium">All Clear</p>
                    <p className="text-slate-400 text-sm">No active alerts</p>
                  </div>
                ) : (
                  alerts.map((alert, idx) => {
                    const alertLevel = alert.alert_level || 'MEDIUM';
                    const isHigh = alertLevel === 'HIGH' || alertLevel === 'CRITICAL';

                    return (
                      <div
                        key={alert.post_id || idx}
                        className={`p-4 rounded-xl border transition-all hover:shadow-md cursor-pointer ${
                          isHigh
                            ? 'bg-red-50 border-red-200 hover:border-red-300'
                            : 'bg-orange-50 border-orange-200 hover:border-orange-300'
                        }`}
                      >
                        <div className="flex items-start gap-3">
                          <div className={`w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0 ${
                            isHigh ? 'bg-red-100' : 'bg-orange-100'
                          }`}>
                            <AlertCircle className={`w-4 h-4 ${isHigh ? 'text-red-600' : 'text-orange-600'}`} />
                          </div>
                          <div className="flex-1 min-w-0">
                            <div className="flex items-center justify-between gap-2 mb-1">
                              <p className={`text-sm font-semibold capitalize truncate ${
                                isHigh ? 'text-red-800' : 'text-orange-800'
                              }`}>
                                {alert.disaster_type || 'Alert'}
                              </p>
                              <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${
                                isHigh ? 'bg-red-200 text-red-700' : 'bg-orange-200 text-orange-700'
                              }`}>
                                {alertLevel}
                              </span>
                            </div>
                            <p className={`text-xs truncate ${isHigh ? 'text-red-600' : 'text-orange-600'}`}>
                              <MapPin className="w-3 h-3 inline mr-1" />
                              {alert.location || 'Unknown location'}
                            </p>
                            {alert.post_excerpt && (
                              <p className="text-xs text-slate-500 mt-2 line-clamp-2">{alert.post_excerpt.substring(0, 80)}...</p>
                            )}
                            <div className="flex items-center gap-3 mt-2">
                              {alert.timestamp && (
                                <p className="text-xs text-slate-400">{formatTimestamp(alert.timestamp)}</p>
                              )}
                              {alert.source_url && (
                                <a
                                  href={alert.source_url}
                                  target="_blank"
                                  rel="noopener noreferrer"
                                  onClick={(e) => e.stopPropagation()}
                                  className="text-xs text-[#0d4a6f] hover:text-[#1a6b9a] flex items-center gap-1 font-medium"
                                >
                                  <ExternalLink className="w-3 h-3" />
                                  Source
                                </a>
                              )}
                            </div>
                          </div>
                        </div>
                      </div>
                    );
                  })
                )}
              </div>
            </div>

            {/* Priority Distribution */}
            <div className="bg-white rounded-2xl border border-slate-100 shadow-sm p-5">
              <div className="flex items-center gap-3 mb-4">
                <div className="w-10 h-10 bg-gradient-to-br from-[#0d4a6f] to-[#1a6b9a] rounded-xl flex items-center justify-center">
                  <TrendingUp className="w-5 h-5 text-white" />
                </div>
                <h3 className="text-lg font-semibold text-slate-900">Priority Distribution</h3>
              </div>
              {posts.length > 0 ? (
                <Chart
                  options={priorityChartOptions}
                  series={priorityChartSeries}
                  type="bar"
                  height={160}
                />
              ) : (
                <div className="h-[160px] flex items-center justify-center text-slate-400">
                  <p className="text-sm">No data available</p>
                </div>
              )}
            </div>

            {/* Disaster Types Chart */}
            <div className="bg-white rounded-2xl border border-slate-100 shadow-sm p-5">
              <div className="flex items-center gap-3 mb-4">
                <div className="w-10 h-10 bg-gradient-to-br from-purple-500 to-purple-600 rounded-xl flex items-center justify-center">
                  <BarChart3 className="w-5 h-5 text-white" />
                </div>
                <h3 className="text-lg font-semibold text-slate-900">Disaster Types</h3>
              </div>
              {Object.keys(disasterStats).length > 0 && chartData.values.length > 0 ? (
                <Chart
                  options={disasterChartOptions}
                  series={disasterChartSeries}
                  type="donut"
                  height={200}
                />
              ) : (
                <div className="h-[200px] flex items-center justify-center text-slate-400">
                  <p className="text-sm">No disaster data</p>
                </div>
              )}
            </div>

          </motion.div>
        </div>

        {/* Post Detail Modal */}
        {selectedPost && (
          <PostDetailModal
            post={selectedPost}
            onClose={() => setSelectedPost(null)}
          />
        )}

        {/* Hide Scrollbar Styles */}
        <style jsx>{`
          .scrollbar-thin {
            scrollbar-width: thin;
            scrollbar-color: #e2e8f0 transparent;
          }
          .scrollbar-thin::-webkit-scrollbar {
            width: 6px;
          }
          .scrollbar-thin::-webkit-scrollbar-track {
            background: transparent;
          }
          .scrollbar-thin::-webkit-scrollbar-thumb {
            background-color: #e2e8f0;
            border-radius: 3px;
          }
          .scrollbar-thin::-webkit-scrollbar-thumb:hover {
            background-color: #cbd5e1;
          }
        `}</style>
        </motion.div>
      </div>
    </DashboardLayout>
  );
}

// ==================== STAT CARD COMPONENT ====================
function StatCard({ title, value, icon: Icon, gradient, bgLight, highlight }) {
  return (
    <motion.div
      whileHover={{ scale: 1.02, y: -2 }}
      className={`bg-white rounded-2xl border p-4 transition-all shadow-sm hover:shadow-md ${
        highlight ? 'border-red-200 ring-2 ring-red-100' : 'border-slate-100'
      }`}
    >
      <div className="flex items-center gap-3">
        <div className={`w-12 h-12 bg-gradient-to-br ${gradient} rounded-xl flex items-center justify-center shadow-sm`}>
          <Icon className="w-6 h-6 text-white" />
        </div>
        <div className="flex-1">
          <p className="text-xs font-medium text-slate-500 uppercase tracking-wide">{title}</p>
          <div className="flex items-center gap-2">
            <p className="text-2xl font-bold text-slate-900">{value}</p>
            {highlight && <span className="w-2 h-2 bg-red-500 rounded-full animate-pulse" />}
          </div>
        </div>
      </div>
    </motion.div>
  );
}

// ==================== ALERT LEVEL COLORS ====================
function getAlertLevelColor(level) {
  const colors = {
    'HIGH': { bg: 'bg-red-100', text: 'text-red-800', border: 'border-l-red-500', dot: 'bg-red-500' },
    'CRITICAL': { bg: 'bg-red-100', text: 'text-red-800', border: 'border-l-red-500', dot: 'bg-red-500' },
    'MEDIUM': { bg: 'bg-orange-100', text: 'text-orange-800', border: 'border-l-orange-500', dot: 'bg-orange-500' },
    'LOW': { bg: 'bg-emerald-100', text: 'text-emerald-800', border: 'border-l-emerald-500', dot: 'bg-emerald-500' },
  };
  return colors[level] || colors['LOW'];
}

// ==================== POST CARD COMPONENT ====================
function PostCard({ post, onClick }) {
  const alertLevel = post.alert_level || 'LOW';
  const alertColors = getAlertLevelColor(alertLevel);
  const disasterType = post.analysis?.disaster_type || post.disaster_type || 'none';
  const disasterInfo = getDisasterTypeInfo(disasterType);
  const urgency = post.analysis?.urgency || post.urgency || 'low';
  const urgencyColors = getUrgencyColor(urgency);
  const misinfoRisk = post.misinformation_analysis?.risk_level || 'minimal';
  const misinfoColors = getMisinfoRiskColor(misinfoRisk);

  const originalPost = post.original_post || post;
  const user = originalPost.user || {};
  const authorName = user.username || originalPost.author || post.author || '';
  const engagement = originalPost.engagement || post.engagement || {};
  const sourceUrl = post.source_url || originalPost.source_url || originalPost.url || '';

  return (
    <div
      onClick={onClick}
      className={`bg-white rounded-2xl border-l-4 ${alertColors.border} border border-slate-100 p-5 hover:shadow-lg transition-all cursor-pointer shadow-sm`}
    >
      {/* Header */}
      <div className="flex items-start justify-between mb-4">
        <div className="flex items-center gap-3">
          <div className="w-11 h-11 bg-gradient-to-br from-[#0d4a6f] to-[#1a6b9a] rounded-full flex items-center justify-center text-white font-bold shadow-sm">
            {authorName?.[0]?.toUpperCase() || 'U'}
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="font-semibold text-slate-900">{authorName || 'Unknown'}</span>
              {user.is_verified && (
                <CheckCircle className="w-4 h-4 text-[#0d4a6f]" />
              )}
            </div>
            <div className="flex items-center gap-2 text-xs text-slate-500">
              <span className="capitalize">{originalPost.platform || 'Social'}</span>
              <span>•</span>
              <span>{formatTimestamp(originalPost.timestamp)}</span>
              {originalPost.language && (
                <>
                  <span>•</span>
                  <span className="px-1.5 py-0.5 bg-slate-100 rounded text-slate-600">{getLanguageDisplay(originalPost.language)}</span>
                </>
              )}
            </div>
          </div>
        </div>
        <span className={`px-3 py-1 text-xs font-bold rounded-full ${alertColors.bg} ${alertColors.text}`}>
          {alertLevel}
        </span>
      </div>

      {/* Content */}
      <p className="text-slate-700 mb-4 line-clamp-3 leading-relaxed">{originalPost.text || post.text}</p>

      {/* Location */}
      {originalPost.location && (
        <div className="flex items-center gap-2 text-sm text-slate-600 mb-4 bg-slate-50 px-3 py-2 rounded-lg w-fit">
          <MapPin className="w-4 h-4 text-[#0d4a6f]" />
          <span>{originalPost.location}</span>
        </div>
      )}

      {/* Tags */}
      <div className="flex flex-wrap gap-2 mb-4">
        {disasterType !== 'none' && (
          <span className="px-3 py-1 text-xs font-medium rounded-full bg-amber-100 text-amber-700 capitalize">
            {disasterInfo.label}
          </span>
        )}
        <span className={`px-3 py-1 text-xs font-medium rounded-full ${urgencyColors.bg} ${urgencyColors.text} capitalize`}>
          {urgency}
        </span>
        {misinfoRisk !== 'minimal' && (
          <span className={`px-3 py-1 text-xs font-medium rounded-full ${misinfoColors.bg} ${misinfoColors.text}`}>
            ⚠ Misinfo: {misinfoRisk}
          </span>
        )}
      </div>

      {/* Engagement & Source Link */}
      <div className="flex items-center justify-between pt-3 border-t border-slate-100">
        <div className="flex items-center gap-5 text-sm text-slate-500">
          <span className="flex items-center gap-1.5 hover:text-[#0d4a6f] transition-colors">
            <ThumbsUp className="w-4 h-4" />
            <span className="font-medium">{engagement.likes || 0}</span>
          </span>
          <span className="flex items-center gap-1.5 hover:text-[#0d4a6f] transition-colors">
            <Share2 className="w-4 h-4" />
            <span className="font-medium">{engagement.shares || engagement.retweets || 0}</span>
          </span>
          <span className="flex items-center gap-1.5 hover:text-[#0d4a6f] transition-colors">
            <MessageCircle className="w-4 h-4" />
            <span className="font-medium">{engagement.comments || 0}</span>
          </span>
          <span className="flex items-center gap-1.5 hover:text-[#0d4a6f] transition-colors">
            <Eye className="w-4 h-4" />
            <span className="font-medium">{engagement.views || originalPost.views || post.views || 0}</span>
          </span>
        </div>
        {sourceUrl && (
          <a
            href={sourceUrl}
            target="_blank"
            rel="noopener noreferrer"
            onClick={(e) => e.stopPropagation()}
            className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-[#0d4a6f] hover:text-[#083a57] hover:bg-[#e8f4fc] rounded-lg transition-all"
          >
            <ExternalLink className="w-3.5 h-3.5" />
            View Source
          </a>
        )}
      </div>
    </div>
  );
}

// ==================== POST DETAIL MODAL ====================
function PostDetailModal({ post, onClose }) {
  const alertLevel = post.alert_level || 'LOW';
  const alertColors = getAlertLevelColor(alertLevel);
  const analysis = post.analysis || {};
  const misinfoAnalysis = post.misinformation_analysis || {};
  const originalPost = post.original_post || post;
  const engagement = originalPost.engagement || post.engagement || {};
  const sourceUrl = post.source_url || originalPost.source_url || originalPost.url || '';

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4"
      onClick={onClose}
    >
      <motion.div
        initial={{ opacity: 0, scale: 0.9, y: 20 }}
        animate={{ opacity: 1, scale: 1, y: 0 }}
        exit={{ opacity: 0, scale: 0.9, y: 20 }}
        className="bg-white rounded-3xl max-w-2xl w-full max-h-[90vh] overflow-y-auto shadow-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="sticky top-0 bg-gradient-to-r from-[#0d4a6f] to-[#1a6b9a] p-5 flex items-center justify-between rounded-t-3xl">
          <div className="flex items-center gap-3">
            <span className={`px-4 py-1.5 text-sm font-bold rounded-full bg-white/20 text-white`}>
              {alertLevel} Alert
            </span>
            <span className="text-sm text-white/80">
              {formatTimestamp(post.processed_at || originalPost.timestamp)}
            </span>
          </div>
          <button
            onClick={onClose}
            className="w-10 h-10 bg-white/20 hover:bg-white/30 rounded-full flex items-center justify-center transition-colors"
          >
            <XCircle className="w-5 h-5 text-white" />
          </button>
        </div>

        {/* Content */}
        <div className="p-6 space-y-6">
          {/* Original Post */}
          <div className="bg-slate-50 rounded-2xl p-5">
            <h4 className="text-sm font-semibold text-slate-500 uppercase tracking-wide mb-3">Original Post</h4>
            <p className="text-slate-800 leading-relaxed">{originalPost.text || post.text}</p>
          </div>

          {/* Analysis Grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="bg-[#e8f4fc] rounded-2xl p-5 border border-[#c5e1f5]">
              <h4 className="text-sm font-semibold text-[#0d4a6f] uppercase tracking-wide mb-4 flex items-center gap-2">
                <Activity className="w-4 h-4" />
                Disaster Analysis
              </h4>
              <div className="space-y-3">
                <div className="flex justify-between items-center">
                  <span className="text-sm text-slate-600">Type</span>
                  <span className="text-sm font-semibold capitalize px-2 py-0.5 bg-white rounded">{analysis.disaster_type || 'None'}</span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-sm text-slate-600">Urgency</span>
                  <span className="text-sm font-semibold capitalize px-2 py-0.5 bg-white rounded">{analysis.urgency || 'Low'}</span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-sm text-slate-600">Relevance</span>
                  <span className="text-sm font-semibold px-2 py-0.5 bg-white rounded">{analysis.relevance_score || 0}/10</span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-sm text-slate-600">Confidence</span>
                  <span className="text-sm font-semibold px-2 py-0.5 bg-white rounded">{((analysis.confidence_score || 0) * 100).toFixed(0)}%</span>
                </div>
              </div>
            </div>

            <div className="bg-purple-50 rounded-2xl p-5 border border-purple-200">
              <h4 className="text-sm font-semibold text-purple-700 uppercase tracking-wide mb-4 flex items-center gap-2">
                <Shield className="w-4 h-4" />
                Misinformation Check
              </h4>
              <div className="space-y-3">
                <div className="flex justify-between items-center">
                  <span className="text-sm text-slate-600">Risk Level</span>
                  <span className={`text-sm font-semibold capitalize px-2 py-0.5 rounded ${
                    misinfoAnalysis.risk_level === 'high' ? 'bg-red-100 text-red-700' :
                    misinfoAnalysis.risk_level === 'moderate' ? 'bg-amber-100 text-amber-700' :
                    'bg-emerald-100 text-emerald-700'
                  }`}>
                    {misinfoAnalysis.risk_level || 'Minimal'}
                  </span>
                </div>
                {misinfoAnalysis.credibility_concerns?.length > 0 && (
                  <div>
                    <span className="text-sm text-slate-600">Concerns:</span>
                    <ul className="mt-2 space-y-1">
                      {misinfoAnalysis.credibility_concerns.slice(0, 3).map((c, i) => (
                        <li key={i} className="text-xs text-purple-700 bg-white px-2 py-1 rounded">• {c}</li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* Keywords */}
          {analysis.keywords?.length > 0 && (
            <div>
              <h4 className="text-sm font-semibold text-slate-500 uppercase tracking-wide mb-3">Extracted Keywords</h4>
              <div className="flex flex-wrap gap-2">
                {analysis.keywords.map((keyword, idx) => (
                  <span key={idx} className="px-3 py-1.5 bg-[#e8f4fc] text-[#0d4a6f] text-sm font-medium rounded-full border border-[#c5e1f5]">
                    {keyword}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* Engagement Metrics */}
          <div className="bg-gradient-to-r from-slate-50 to-slate-100 rounded-2xl p-5 border border-slate-200">
            <h4 className="text-sm font-semibold text-slate-700 uppercase tracking-wide mb-4 flex items-center gap-2">
              <Activity className="w-4 h-4" />
              Engagement Metrics
            </h4>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div className="text-center">
                <ThumbsUp className="w-5 h-5 text-[#0d4a6f] mx-auto mb-2" />
                <div className="text-2xl font-bold text-slate-900">{engagement.likes || 0}</div>
                <div className="text-xs text-slate-500">Likes</div>
              </div>
              <div className="text-center">
                <Share2 className="w-5 h-5 text-[#0d4a6f] mx-auto mb-2" />
                <div className="text-2xl font-bold text-slate-900">{engagement.shares || engagement.retweets || 0}</div>
                <div className="text-xs text-slate-500">Shares</div>
              </div>
              <div className="text-center">
                <MessageCircle className="w-5 h-5 text-[#0d4a6f] mx-auto mb-2" />
                <div className="text-2xl font-bold text-slate-900">{engagement.comments || 0}</div>
                <div className="text-xs text-slate-500">Comments</div>
              </div>
              <div className="text-center">
                <Eye className="w-5 h-5 text-[#0d4a6f] mx-auto mb-2" />
                <div className="text-2xl font-bold text-slate-900">{engagement.views || originalPost.views || post.views || 0}</div>
                <div className="text-xs text-slate-500">Views</div>
              </div>
            </div>
          </div>

          {/* Source Link */}
          {sourceUrl && (
            <div className="bg-gradient-to-r from-[#e8f4fc] to-cyan-50 rounded-2xl p-5 border border-[#c5e1f5]">
              <h4 className="text-sm font-semibold text-[#0d4a6f] mb-3 flex items-center gap-2">
                <Globe className="w-4 h-4" />
                Original Source
              </h4>
              <a
                href={sourceUrl}
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-center gap-2 text-[#0d4a6f] hover:text-[#083a57] text-sm break-all font-medium"
              >
                <ExternalLink className="w-4 h-4 flex-shrink-0" />
                {sourceUrl}
              </a>
            </div>
          )}

          {/* Processing Info */}
          <div className="text-xs text-slate-400 border-t border-slate-100 pt-4 flex justify-between">
            <span>Post ID: {post.id || post.post_id || 'N/A'}</span>
            <span>Processing Time: {post.processing_time_ms || 0}ms</span>
          </div>
        </div>
      </motion.div>
    </motion.div>
  );
}
