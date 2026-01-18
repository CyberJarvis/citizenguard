'use client';

import { useEffect, useState, useRef, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import ProtectedRoute from '@/components/ProtectedRoute';
import DashboardLayout from '@/components/DashboardLayout';
import useAuthStore from '@/context/AuthContext';
import {
  User,
  MapPin,
  AlertTriangle,
  MessageCircle,
  Shield,
  Droplets,
  Wind,
  Waves,
  ThermometerSun,
  Heart,
  Flag,
  X,
  CheckCircle,
  Loader2,
  Map,
  Clock,
  Share2,
  MoreHorizontal,
  Eye,
  ChevronLeft,
  ChevronRight,
  Camera,
  Plus,
  Users,
  Trophy
} from 'lucide-react';
import { motion } from 'framer-motion';
import toast, { Toaster } from 'react-hot-toast';
import { getHazardReports, toggleLikeHazardReport, reportHazardReport, getMyLikedReports, recordHazardReportView } from '@/lib/api';
import SocialMediaAlerts from '@/components/SocialMediaAlerts';
import RealTimeHazardMonitor from '@/components/RealTimeHazardMonitor';
import PageHeader from '@/components/PageHeader';
import { getRelativeTimeIST, formatDateTimeIST, getSmartTimeIST } from '@/lib/dateUtils';
import SOSButton from '@/components/sos/SOSButton';

// Helper function to format relative time (using IST)
const formatRelativeTime = (dateString) => {
  return getRelativeTimeIST(dateString);
};

// View tracking wrapper component
function ViewTracker({ reportId, onView, children }) {
  const ref = useRef(null);
  const hasTracked = useRef(false);

  useEffect(() => {
    const element = ref.current;
    if (!element || hasTracked.current) return;

    const observer = new IntersectionObserver(
      (entries) => {
        if (entries[0].isIntersecting && !hasTracked.current) {
          hasTracked.current = true;
          onView(reportId);
        }
      },
      { threshold: 0.5 } // Trigger when 50% visible
    );

    observer.observe(element);
    return () => observer.disconnect();
  }, [reportId, onView]);

  return <div ref={ref}>{children}</div>;
}

// Helper function to get hazard type badge color
const getHazardBadgeColor = (hazardType) => {
  const colors = {
    'rip_current': 'bg-purple-100 text-purple-700 border-purple-200',
    'jellyfish': 'bg-pink-100 text-pink-700 border-pink-200',
    'oil_spill': 'bg-gray-800 text-white border-gray-700',
    'debris': 'bg-amber-100 text-amber-700 border-amber-200',
    'shark': 'bg-red-100 text-red-700 border-red-200',
    'algae_bloom': 'bg-green-100 text-green-700 border-green-200',
    'pollution': 'bg-orange-100 text-orange-700 border-orange-200',
    'erosion': 'bg-yellow-100 text-yellow-700 border-yellow-200',
    'flooding': 'bg-blue-100 text-blue-700 border-blue-200',
    'other': 'bg-slate-100 text-slate-700 border-slate-200'
  };
  return colors[hazardType?.toLowerCase()] || colors['other'];
};

// Helper function to format hazard type for display
const formatHazardType = (hazardType) => {
  if (!hazardType) return 'Unknown';
  return hazardType.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
};

// Animation variants
const fadeInUp = {
  hidden: { opacity: 0, y: 20 },
  visible: { opacity: 1, y: 0, transition: { duration: 0.4 } }
};

const staggerContainer = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: { staggerChildren: 0.1 }
  }
};

const scaleIn = {
  hidden: { opacity: 0, scale: 0.9 },
  visible: { opacity: 1, scale: 1, transition: { duration: 0.3 } }
};

// Get greeting based on time of day
const getGreeting = () => {
  const hour = new Date().getHours();
  if (hour < 12) return 'Good Morning';
  if (hour < 17) return 'Good Afternoon';
  return 'Good Evening';
};

function DashboardContent() {
  const router = useRouter();
  const { user } = useAuthStore();
  const [feedPosts, setFeedPosts] = useState([]);
  const [isLoadingFeed, setIsLoadingFeed] = useState(true);
  const [expandedImage, setExpandedImage] = useState(null);
  const [weatherData, setWeatherData] = useState({
    temperature: '--',
    condition: 'Loading...',
    waveHeight: '--',
    wind: '--',
    precipitation: '--',
    location: 'Detecting...',
    humidity: '--',
    isLoading: true
  });

  // Report modal state
  const [reportModal, setReportModal] = useState({ isOpen: false, postId: null, postTitle: '' });
  const [reportReason, setReportReason] = useState('');
  const [isSubmittingReport, setIsSubmittingReport] = useState(false);

  // View tracking
  const viewedPostsRef = useRef(new Set());

  // Redirect authorities to their dashboard
  useEffect(() => {
    if (user && (user.role === 'authority' || user.role === 'authority_admin')) {
      router.push('/authority');
    }
  }, [user, router]);

  // Fetch real-time weather data based on user location
  useEffect(() => {
    const fetchWeather = async () => {
      try {
        if (!navigator.geolocation) {
          toast.error('Geolocation is not supported');
          setWeatherData(prev => ({ ...prev, isLoading: false, condition: 'Unavailable' }));
          return;
        }

        navigator.geolocation.getCurrentPosition(
          async (position) => {
            const { latitude, longitude } = position.coords;

            try {
              const weatherApiKey = process.env.NEXT_PUBLIC_WEATHER_API_KEY;

              // Check if API key is configured
              if (!weatherApiKey) {
                console.warn('Weather API key not configured');
                setWeatherData(prev => ({ ...prev, isLoading: false, condition: 'API not configured' }));
                return;
              }

              // Use current.json API which is more reliable
              const response = await fetch(
                `https://api.weatherapi.com/v1/current.json?key=${weatherApiKey}&q=${latitude},${longitude}&aqi=no`
              );

              if (!response.ok) {
                const errorText = await response.text();
                console.error('Weather API error:', errorText);
                throw new Error(`Weather API returned ${response.status}`);
              }

              const data = await response.json();
              console.log('Weather API response:', data);

              // Validate data structure
              if (!data || !data.current || !data.location) {
                console.error('Invalid data structure:', data);
                throw new Error('Invalid weather data received');
              }

              const current = data.current;

              // Determine condition severity based on wind speed and weather condition
              let conditionSeverity = 'Low';
              const windKph = current.wind_kph || 0;
              const isStormyCondition = current.condition?.text?.toLowerCase().includes('storm') ||
                                       current.condition?.text?.toLowerCase().includes('thunder');

              if (windKph > 40 || isStormyCondition) {
                conditionSeverity = 'High';
              } else if (windKph > 25 || current.precip_mm > 5) {
                conditionSeverity = 'Medium';
              }

              // Estimate wave height based on wind speed (simplified model)
              const estimatedWaveHeight = windKph < 10 ? 0.5 :
                                         windKph < 25 ? 1.2 :
                                         windKph < 40 ? 2.5 : 4.0;

              setWeatherData({
                temperature: Math.round(current.temp_c),
                condition: conditionSeverity,
                waveHeight: `${estimatedWaveHeight.toFixed(1)}m`,
                wind: `${Math.round(windKph)}kph`,
                precipitation: current.precip_mm > 5 ? 'High' : current.precip_mm > 1 ? 'Medium' : 'Low',
                location: `${data.location.name}, ${data.location.region}`,
                weatherCondition: current.condition?.text || 'Clear',
                humidity: current.humidity || 0,
                isLoading: false
              });

              console.log('Weather data set successfully');
            } catch (error) {
              console.error('Weather fetch error:', error);
              toast.error('Failed to load weather data');
              setWeatherData({
                temperature: '--',
                condition: 'Unavailable',
                waveHeight: '--',
                wind: '--',
                precipitation: '--',
                location: 'Location unavailable',
                humidity: '--',
                isLoading: false
              });
            }
          },
          (error) => {
            console.error('Geolocation error:', error);
            toast.error('Location access denied');
            setWeatherData(prev => ({ ...prev, isLoading: false, condition: 'Location unavailable' }));
          },
          { enableHighAccuracy: true, timeout: 10000, maximumAge: 300000 }
        );
      } catch (error) {
        console.error('Weather init error:', error);
      }
    };

    fetchWeather();
  }, []);

  // Fetch hazard reports and user's liked reports on component mount
  useEffect(() => {
    const fetchHazardReports = async () => {
      try {
        setIsLoadingFeed(true);

        // Fetch both reports and user's liked reports in parallel
        const [reportsResponse, likedResponse] = await Promise.all([
          getHazardReports({
            page: 1,
            page_size: 10,
            verification_status: 'verified'
          }),
          getMyLikedReports().catch(() => ({ liked_report_ids: [] })) // Gracefully handle if not logged in
        ]);

        const likedReportIds = new Set(likedResponse.liked_report_ids || []);

        const baseUrl = process.env.NEXT_PUBLIC_API_URL?.replace('/api/v1', '') || 'http://localhost:8000';

        // Helper to handle both local and S3 URLs
        const getImageUrl = (imageUrl) => {
          if (!imageUrl) return '';
          // If it's already a full URL (S3 or other), use it directly
          if (imageUrl.startsWith('http://') || imageUrl.startsWith('https://')) {
            return imageUrl;
          }
          // Otherwise, prepend the base URL for local files
          return `${baseUrl}${imageUrl.replace(/\\/g, '/')}`;
        };

        const transformedPosts = reportsResponse.reports.map(report => {
          // Build profile picture URL if available
          let profilePicture = null;
          if (report.user_profile_picture) {
            profilePicture = report.user_profile_picture.startsWith('http')
              ? report.user_profile_picture
              : `${baseUrl}${report.user_profile_picture}`;
          }

          return {
            id: report._id,
            report_id: report.report_id,
            user: {
              name: report.user_name || 'Anonymous',
              avatar: profilePicture
            },
            image: getImageUrl(report.image_url),
            description: report.description || `${report.hazard_type} reported`,
            location: report.location.address || 'Unknown Location',
            distance: 'Nearby',
            likes: Math.max(0, report.likes || 0),
            isLiked: likedReportIds.has(report.report_id),
            comments: report.comments,
            views: report.views || 0,
            verificationStatus: report.verification_status,
            hazardType: report.hazard_type,
            created_at: report.created_at
          };
        });

        setFeedPosts(transformedPosts);
      } catch (error) {
        console.error('Error fetching hazard reports:', error);
        toast.error('Failed to load hazard reports');
      } finally{
        setIsLoadingFeed(false);
      }
    };

    fetchHazardReports();
  }, []);

  // Handle like toggle for hazard reports
  const handleLikeToggle = async (reportId) => {
    // Optimistic update for better UX
    setFeedPosts(prevPosts =>
      prevPosts.map(post => {
        if (post.report_id === reportId) {
          const newIsLiked = !post.isLiked;
          const newLikes = newIsLiked ? post.likes + 1 : Math.max(0, post.likes - 1);
          return { ...post, isLiked: newIsLiked, likes: newLikes };
        }
        return post;
      })
    );

    try {
      const response = await toggleLikeHazardReport(reportId);
      if (response.success) {
        // Update with actual server values
        setFeedPosts(prevPosts =>
          prevPosts.map(post =>
            post.report_id === reportId
              ? { ...post, isLiked: response.is_liked, likes: Math.max(0, response.likes_count) }
              : post
          )
        );
      }
    } catch (error) {
      console.error('Error toggling like:', error);
      toast.error('Failed to update like');
      // Revert optimistic update on error
      setFeedPosts(prevPosts =>
        prevPosts.map(post => {
          if (post.report_id === reportId) {
            const revertedIsLiked = !post.isLiked;
            const revertedLikes = revertedIsLiked ? post.likes + 1 : Math.max(0, post.likes - 1);
            return { ...post, isLiked: revertedIsLiked, likes: revertedLikes };
          }
          return post;
        })
      );
    }
  };

  // Open report modal
  const openReportModal = (postId, postTitle) => {
    setReportModal({ isOpen: true, postId, postTitle });
    setReportReason('');
  };

  // Close report modal
  const closeReportModal = () => {
    setReportModal({ isOpen: false, postId: null, postTitle: '' });
    setReportReason('');
  };

  // Submit report
  const handleSubmitReport = async () => {
    if (!reportReason.trim() || reportReason.length < 10) {
      toast.error('Please provide a detailed reason (at least 10 characters)');
      return;
    }

    try {
      setIsSubmittingReport(true);
      const response = await reportHazardReport(reportModal.postId, reportReason);
      if (response.success) {
        toast.success(response.message || 'Report submitted successfully');
        closeReportModal();
      }
    } catch (error) {
      console.error('Error submitting report:', error);
      const errorMessage = error.response?.data?.detail || 'Failed to submit report';
      toast.error(errorMessage);
    } finally {
      setIsSubmittingReport(false);
    }
  };

  // Handle view tracking when a post comes into view
  const handlePostView = useCallback(async (reportId) => {
    // Skip if already viewed this session
    if (viewedPostsRef.current.has(reportId)) return;

    // Mark as viewed locally first
    viewedPostsRef.current.add(reportId);

    // Record view on server and update local state
    const result = await recordHazardReportView(reportId);
    if (result.success) {
      setFeedPosts(prevPosts =>
        prevPosts.map(post =>
          post.report_id === reportId
            ? { ...post, views: result.views_count }
            : post
        )
      );
    }
  }, []);

  const quickActions = [
    {
      id: 'map',
      icon: Map,
      title: 'Map View',
      color: 'from-[#1a6b9a] to-[#0d4a6f]',
      onClick: () => router.push('/map')
    },
    {
      id: 'myreports',
      icon: Clock,
      title: 'My Reports',
      color: 'from-[#0d4a6f] to-[#083a57]',
      onClick: () => router.push('/my-reports')
    },
    {
      id: 'chat',
      icon: Users,
      title: 'Community',
      color: 'from-[#4391c4] to-[#1a6b9a]',
      onClick: () => router.push('/community')
    },
    {
      id: 'safety',
      icon: Shield,
      title: 'Safety Tips',
      color: 'from-[#1a6b9a] to-emerald-600',
      onClick: () => router.push('/safety')
    }
  ];

  return (
    <div className="p-3 lg:p-6 w-full pb-24 lg:pb-6">
      <Toaster position="top-center" />

      {/* Mobile Greeting */}
      <div className="lg:hidden mb-4">
        <h1 className="text-2xl font-semibold text-slate-900">
          {getGreeting()}, <span className="text-[#0d4a6f]">{user?.full_name?.split(' ')[0] || 'Guardian'}</span>!
        </h1>
        <p className="text-slate-500 text-sm mt-1">Stay safe and help protect our coast</p>
      </div>

      {/* Page Header - Desktop Only */}
      <PageHeader />

      {/* Two Column Layout */}
      <motion.div
        className="grid grid-cols-1 lg:grid-cols-3 gap-4 lg:items-start"
        initial="hidden"
        animate="visible"
        variants={staggerContainer}
      >
        {/* Left Column - Main Content */}
        <div className="lg:col-span-2 space-y-4 lg:max-h-[calc(100vh-6rem)] lg:overflow-y-auto lg:pr-2 scrollbar-hide">

          {/* Weather Card - Teal Theme with Wave Elements */}
          <motion.div
            variants={fadeInUp}
            className="bg-white rounded-2xl shadow-sm border border-slate-100 overflow-hidden"
          >
            <div className="bg-gradient-to-r from-[#0d4a6f] to-[#083a57] p-5 text-white relative overflow-hidden">
              {/* Decorative Wave Elements */}
              <div className="absolute bottom-0 left-0 right-0 opacity-10">
                <svg viewBox="0 0 1440 120" className="w-full h-16">
                  <path fill="white" d="M0,32L48,37.3C96,43,192,53,288,58.7C384,64,480,64,576,58.7C672,53,768,43,864,48C960,53,1056,75,1152,80C1248,85,1344,75,1392,69.3L1440,64L1440,120L1392,120C1344,120,1248,120,1152,120C1056,120,960,120,864,120C768,120,672,120,576,120C480,120,384,120,288,120C192,120,96,120,48,120L0,120Z"></path>
                </svg>
              </div>
              <div className="absolute top-2 right-4 opacity-20">
                <svg width="80" height="50" viewBox="0 0 80 50" fill="none">
                  <path d="M60 25C60 20 56 15 50 15C48 10 43 7 37 7C30 7 24 12 23 18C18 19 15 23 15 28C15 34 19 38 25 38H60C66 38 70 34 70 28C70 22 66 18 60 18V25Z" fill="white"/>
                </svg>
              </div>

              <div className="flex items-center justify-between mb-3 relative z-10">
                <div className="flex items-center space-x-2">
                  <MapPin className="w-4 h-4" />
                  <span className="text-sm font-medium">{weatherData.location}</span>
                </div>
                {weatherData.isLoading && <Loader2 className="w-4 h-4 animate-spin" />}
              </div>

              <div className="flex items-end justify-between relative z-10">
                <div className="text-5xl font-semibold">{weatherData.temperature}°C</div>
                <div className={`px-3 py-1.5 rounded-full text-xs font-semibold ${
                  weatherData.condition === 'High' ? 'bg-red-500' :
                  weatherData.condition === 'Medium' ? 'bg-yellow-500' : 'bg-emerald-500'
                } text-white shadow-lg`}>
                  {weatherData.condition} Risk
                </div>
              </div>
            </div>

            <div className="grid grid-cols-4 divide-x divide-slate-100">
              <div className="p-4 text-center">
                <Waves className="w-5 h-5 text-[#0d4a6f] mx-auto mb-1" />
                <div className="text-lg font-semibold text-slate-900">{weatherData.waveHeight}</div>
                <div className="text-xs text-slate-500">Waves</div>
              </div>
              <div className="p-4 text-center">
                <Wind className="w-5 h-5 text-[#1a6b9a] mx-auto mb-1" />
                <div className="text-lg font-semibold text-slate-900">{weatherData.wind}</div>
                <div className="text-xs text-slate-500">Wind</div>
              </div>
              <div className="p-4 text-center">
                <Droplets className="w-5 h-5 text-[#0d4a6f] mx-auto mb-1" />
                <div className="text-lg font-semibold text-slate-900">{weatherData.precipitation}</div>
                <div className="text-xs text-slate-500">Rain</div>
              </div>
              <div className="p-4 text-center">
                <ThermometerSun className="w-5 h-5 text-orange-500 mx-auto mb-1" />
                <div className="text-lg font-semibold text-slate-900">{weatherData.humidity}%</div>
                <div className="text-xs text-slate-500">Humidity</div>
              </div>
            </div>
          </motion.div>

          {/* HERO Report Hazard Button - BIG and prominent */}
          <motion.button
            variants={scaleIn}
            whileHover={{ scale: 1.02 }}
            whileTap={{ scale: 0.98 }}
            onClick={() => router.push('/report-hazard')}
            className="w-full fab-hero rounded-2xl p-6 flex items-center justify-between text-white shadow-xl animate-pulse-glow"
          >
            <div className="flex items-center gap-4">
              <div className="w-14 h-14 bg-white/20 rounded-xl flex items-center justify-center backdrop-blur-sm">
                <Camera className="w-7 h-7 text-white" />
              </div>
              <div className="text-left">
                <h3 className="text-xl font-semibold">Report a Hazard</h3>
                <p className="text-white/80 text-sm">Help keep our coast safe</p>
              </div>
            </div>
            <div className="w-12 h-12 bg-white/20 rounded-full flex items-center justify-center">
              <Plus className="w-6 h-6 text-white" strokeWidth={3} />
            </div>
          </motion.button>

          {/* Quick Actions - Clean Grid */}
          <motion.div variants={fadeInUp} className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            {quickActions.map((action, index) => {
              const Icon = action.icon;
              return (
                <motion.button
                  key={action.id}
                  variants={scaleIn}
                  whileHover={{ scale: 1.03, y: -2 }}
                  whileTap={{ scale: 0.97 }}
                  onClick={action.onClick}
                  className="bg-white rounded-2xl shadow-sm border border-slate-100 hover:shadow-md hover:border-[#9ecbec] transition-all p-4 flex flex-col items-center justify-center text-center min-h-[100px]"
                >
                  <div className={`w-12 h-12 bg-gradient-to-br ${action.color} rounded-xl flex items-center justify-center mb-3 shadow-sm`}>
                    <Icon className="w-6 h-6 text-white" strokeWidth={2} />
                  </div>
                  <h3 className="font-semibold text-slate-800 text-sm">{action.title}</h3>
                </motion.button>
              );
            })}
          </motion.div>

          {/* Real-time Hazard Monitoring - Mobile Only */}
          <div className="lg:hidden">
            <RealTimeHazardMonitor
              compact={true}
              refreshInterval={60000}
            />
          </div>

          {/* Social Media Alerts - Mobile Only */}
          <div className="lg:hidden">
            <SocialMediaAlerts variant="compact" maxAlerts={3} refreshInterval={30000} />
          </div>

        {/* Community Feed - Enhanced */}
        <motion.div variants={fadeInUp} className="space-y-4">
          <div className="flex items-center justify-between px-1">
            <h2 className="text-lg font-semibold text-slate-900">Recent Reports</h2>
            <span className="text-xs text-slate-500 bg-[#e8f4fc] px-2 py-1 rounded-full">{feedPosts.length} verified</span>
          </div>

          {isLoadingFeed ? (
            <div className="bg-white rounded-2xl shadow-sm border border-slate-100 p-12 flex flex-col items-center justify-center">
              <div className="relative">
                <div className="w-16 h-16 rounded-full border-4 border-slate-100 border-t-[#0d4a6f] animate-spin"></div>
              </div>
              <p className="text-slate-500 text-sm mt-4">Loading reports...</p>
            </div>
          ) : feedPosts.length === 0 ? (
            <div className="bg-white rounded-2xl shadow-sm border border-slate-100 p-12 flex flex-col items-center justify-center">
              <div className="w-20 h-20 bg-[#e8f4fc] rounded-full flex items-center justify-center mb-4">
                <AlertTriangle className="w-10 h-10 text-[#6badd9]" />
              </div>
              <p className="text-slate-900 font-medium mb-1">No reports yet</p>
              <p className="text-slate-500 text-sm text-center">Be the first to report a coastal hazard!</p>
              <button
                onClick={() => router.push('/report-hazard')}
                className="mt-4 px-4 py-2 bg-[#0d4a6f] text-white text-sm font-medium rounded-xl hover:bg-[#083a57] transition"
              >
                Report Hazard
              </button>
            </div>
          ) : (
            feedPosts.map((post) => (
              <ViewTracker key={post.id} reportId={post.report_id} onView={handlePostView}>
                <motion.div
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  className="bg-white rounded-2xl shadow-sm border border-slate-100 overflow-hidden hover:shadow-lg hover:border-[#c5e1f5] transition-all duration-300"
                >
                  {/* Post Header - Enhanced */}
                <div className="flex items-center justify-between p-4">
                  <div className="flex items-center space-x-3">
                    {/* Profile Picture */}
                    <div className="relative">
                      {post.user.avatar ? (
                        <img
                          src={post.user.avatar}
                          alt={post.user.name}
                          className="w-11 h-11 rounded-full object-cover border-2 border-white shadow-sm"
                          onError={(e) => {
                            e.target.style.display = 'none';
                            e.target.nextSibling.style.display = 'flex';
                          }}
                        />
                      ) : null}
                      <div
                        className={`w-11 h-11 bg-gradient-to-br from-[#1a6b9a] to-[#0d4a6f] rounded-full flex items-center justify-center shadow-sm ${post.user.avatar ? 'hidden' : ''}`}
                      >
                        <span className="text-white font-semibold text-sm">
                          {post.user.name?.charAt(0)?.toUpperCase() || 'A'}
                        </span>
                      </div>
                      {/* Online indicator */}
                      <div className="absolute -bottom-0.5 -right-0.5 w-3.5 h-3.5 bg-green-500 rounded-full border-2 border-white"></div>
                    </div>

                    {/* User Info */}
                    <div className="flex flex-col">
                      <div className="flex items-center gap-2">
                        <span className="font-semibold text-gray-900 text-sm">{post.user.name}</span>
                        {post.verificationStatus === 'verified' && (
                          <CheckCircle className="w-4 h-4 text-[#1a6b9a] fill-[#1a6b9a]" />
                        )}
                      </div>
                      <div className="flex items-center gap-1.5 text-xs text-gray-500">
                        <Clock className="w-3 h-3" />
                        <span>{formatRelativeTime(post.created_at)}</span>
                        <span className="text-gray-300">•</span>
                        <MapPin className="w-3 h-3" />
                        <span className="truncate max-w-[120px] sm:max-w-[200px]">{post.location}</span>
                      </div>
                    </div>
                  </div>

                  {/* Hazard Type Badge */}
                  <div className={`px-2.5 py-1 rounded-full text-xs font-medium border ${getHazardBadgeColor(post.hazardType)}`}>
                    {formatHazardType(post.hazardType)}
                  </div>
                </div>

                {/* Post Description */}
                <div className="px-4 pb-3">
                  <p className="text-gray-800 text-sm leading-relaxed">{post.description}</p>
                </div>

                {/* Post Image - Full Display with Click to Expand */}
                <div
                  className="relative bg-gray-50 cursor-pointer group"
                  onClick={() => setExpandedImage(post.image)}
                >
                  {post.image ? (
                    <>
                      <img
                        src={post.image}
                        alt={post.description}
                        className="w-full max-h-[500px] object-contain"
                        onError={(e) => {
                          console.error('Image failed to load:', post.image);
                          e.target.style.display = 'none';
                          e.target.nextSibling.style.display = 'flex';
                        }}
                      />
                      {/* Hover overlay */}
                      <div className="absolute inset-0 bg-black/0 group-hover:bg-black/10 transition-all flex items-center justify-center">
                        <div className="opacity-0 group-hover:opacity-100 transition-opacity bg-black/50 text-white px-3 py-1.5 rounded-full text-xs font-medium flex items-center gap-1.5">
                          <Eye className="w-3.5 h-3.5" />
                          Click to expand
                        </div>
                      </div>
                    </>
                  ) : null}
                  <div className={`w-full h-48 flex items-center justify-center ${post.image ? 'hidden' : ''}`}>
                    <AlertTriangle className="w-12 h-12 text-gray-300" />
                  </div>
                </div>

                {/* Post Actions - Enhanced */}
                <div className="px-4 py-3 border-t border-gray-50">
                  <div className="flex items-center justify-between">
                    {/* Left side - Stats */}
                    <div className="flex items-center gap-4 text-xs text-gray-500">
                      <span className="flex items-center gap-1">
                        <Heart className={`w-3.5 h-3.5 ${post.likes > 0 ? 'text-red-500' : ''}`} />
                        {post.likes} {post.likes === 1 ? 'like' : 'likes'}
                      </span>
                      <span className="flex items-center gap-1">
                        <Eye className="w-3.5 h-3.5" />
                        {post.views} {post.views === 1 ? 'view' : 'views'}
                      </span>
                    </div>

                    {/* Verification Badge */}
                    {post.verificationStatus === 'verified' && (
                      <div className="hidden sm:flex items-center gap-1.5 px-2.5 py-1 bg-green-50 text-green-700 rounded-full text-xs font-medium">
                        <CheckCircle className="w-3.5 h-3.5" />
                        <span>Verified Report</span>
                      </div>
                    )}
                  </div>

                  {/* Action Buttons */}
                  <div className="flex items-center gap-2 mt-3 pt-3 border-t border-gray-50">
                    <button
                      onClick={() => handleLikeToggle(post.report_id)}
                      className={`flex-1 flex items-center justify-center gap-2 py-2.5 rounded-xl font-medium text-sm transition-all active:scale-95 ${
                        post.isLiked
                          ? 'bg-red-50 text-red-600 hover:bg-red-100'
                          : 'bg-gray-50 text-gray-600 hover:bg-gray-100'
                      }`}
                    >
                      <Heart className={`w-5 h-5 ${post.isLiked ? 'fill-current' : ''}`} />
                      <span>{post.isLiked ? 'Liked' : 'Like'}</span>
                    </button>

                    <button
                      onClick={() => {
                        navigator.share?.({
                          title: 'Coastal Hazard Report',
                          text: post.description,
                          url: window.location.href
                        }).catch(() => {
                          navigator.clipboard.writeText(window.location.href);
                          toast.success('Link copied to clipboard!');
                        });
                      }}
                      className="flex-1 flex items-center justify-center gap-2 py-2.5 rounded-xl font-medium text-sm bg-gray-50 text-gray-600 hover:bg-gray-100 transition-all active:scale-95"
                    >
                      <Share2 className="w-5 h-5" />
                      <span>Share</span>
                    </button>

                    <button
                      onClick={() => openReportModal(post.report_id, post.description)}
                      className="flex items-center justify-center p-2.5 rounded-xl bg-gray-50 text-gray-600 hover:bg-orange-50 hover:text-orange-600 transition-all active:scale-95"
                      title="Report this post"
                    >
                      <Flag className="w-5 h-5" />
                    </button>
                  </div>
                </div>
                </motion.div>
              </ViewTracker>
            ))
          )}
        </motion.div>
      </div>

        {/* Right Column - Sidebar */}
        <motion.div
          variants={fadeInUp}
          className="hidden lg:block lg:col-span-1 lg:sticky lg:top-6 space-y-4 lg:max-h-[calc(100vh-3rem)] lg:overflow-y-auto scrollbar-hide"
        >
          {/* Real-time Hazard Monitoring - Cyclone, Tsunami, Earthquake */}
          <RealTimeHazardMonitor
            compact={true}
            refreshInterval={60000}
            onHazardDetected={(alerts) => {
              if (alerts.length > 0) {
                toast.error(`${alerts.length} active hazard alert(s) detected!`, {
                  duration: 5000,
                  icon: '🚨'
                });
              }
            }}
          />

          {/* Social Media Alerts - Live hazard detection from SMI */}
          <SocialMediaAlerts variant="compact" maxAlerts={4} refreshInterval={30000} />

          {/* Emergency Contacts Card */}
          <div className="bg-white rounded-2xl shadow-sm border border-slate-100 p-5">
            <div className="flex items-center space-x-2 mb-4">
              <div className="w-10 h-10 bg-gradient-to-br from-red-500 to-red-600 rounded-xl flex items-center justify-center">
                <Shield className="w-5 h-5 text-white" />
              </div>
              <h3 className="text-lg font-semibold text-slate-900">Emergency Contacts</h3>
            </div>

            <div className="space-y-3">
              <div className="flex items-start space-x-3 p-3 bg-red-50 rounded-xl border border-red-100">
                <AlertTriangle className="w-5 h-5 text-red-600 flex-shrink-0 mt-0.5" />
                <div>
                  <p className="text-sm font-semibold text-slate-900">Coast Guard</p>
                  <a href="tel:911" className="text-lg font-semibold text-red-600 hover:text-red-700">
                    911
                  </a>
                </div>
              </div>

              <div className="flex items-start space-x-3 p-3 bg-[#e8f4fc] rounded-xl border border-[#c5e1f5]">
                <Waves className="w-5 h-5 text-[#0d4a6f] flex-shrink-0 mt-0.5" />
                <div>
                  <p className="text-sm font-semibold text-slate-900">Marine Rescue</p>
                  <a href="tel:1-800-123-4567" className="text-sm font-semibold text-[#0d4a6f] hover:text-[#083a57]">
                    1-800-123-4567
                  </a>
                </div>
              </div>

              <div className="flex items-start space-x-3 p-3 bg-orange-50 rounded-xl border border-orange-100">
                <Wind className="w-5 h-5 text-orange-600 flex-shrink-0 mt-0.5" />
                <div>
                  <p className="text-sm font-semibold text-slate-900">Weather Hotline</p>
                  <a href="tel:1-800-WEATHER" className="text-sm font-semibold text-orange-600 hover:text-orange-700">
                    1-800-WEATHER
                  </a>
                </div>
              </div>

              <div className="flex items-start space-x-3 p-3 bg-emerald-50 rounded-xl border border-emerald-100">
                <MessageCircle className="w-5 h-5 text-emerald-600 flex-shrink-0 mt-0.5" />
                <div>
                  <p className="text-sm font-semibold text-slate-900">Non-Emergency</p>
                  <a href="tel:311" className="text-sm font-semibold text-emerald-600 hover:text-emerald-700">
                    311
                  </a>
                </div>
              </div>
            </div>
          </div>

          {/* Quick Safety Tips Card */}
          <div className="bg-gradient-to-br from-[#e8f4fc] to-emerald-50 rounded-2xl shadow-sm border border-[#c5e1f5] p-5">
            <div className="flex items-center space-x-2 mb-4">
              <Shield className="w-5 h-5 text-[#0d4a6f]" />
              <h3 className="text-base font-semibold text-slate-900">Today's Safety Tip</h3>
            </div>

            <p className="text-sm text-slate-700 leading-relaxed mb-4">
              {weatherData.condition === 'High'
                ? 'High risk conditions detected. Avoid coastal areas and stay informed about weather updates.'
                : weatherData.condition === 'Medium'
                ? 'Moderate conditions. Exercise caution near the water and monitor weather changes.'
                : 'Conditions are favorable, but always check local forecasts before coastal activities.'}
            </p>

            <button
              onClick={() => router.push('/safety')}
              className="w-full bg-[#0d4a6f] hover:bg-[#083a57] text-white text-sm font-semibold py-2.5 px-4 rounded-xl transition-colors"
            >
              View All Safety Tips
            </button>
          </div>
        </motion.div>
      </motion.div>

      {/* Fullscreen Image Modal - Higher z-index to appear above PageHeader */}
      {expandedImage && (
        <div
          className="fixed inset-0 bg-black/95 z-[99999] flex items-center justify-center p-4"
          onClick={() => setExpandedImage(null)}
        >
          <button
            onClick={() => setExpandedImage(null)}
            className="absolute top-4 right-4 w-10 h-10 bg-white/10 hover:bg-white/20 rounded-full flex items-center justify-center transition-colors"
          >
            <X className="w-6 h-6 text-white" />
          </button>
          <img
            src={expandedImage}
            alt="Expanded view"
            className="max-w-full max-h-[90vh] object-contain rounded-lg"
            onClick={(e) => e.stopPropagation()}
          />
        </div>
      )}

      {/* Report Modal - Higher z-index to appear above PageHeader */}
      {reportModal.isOpen && (
        <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-[99999] p-4">
          <div className="bg-white rounded-2xl max-w-md w-full overflow-hidden">
            {/* Modal Header */}
            <div className="px-5 py-4 border-b border-gray-200 flex items-center justify-between">
              <h3 className="font-semibold text-lg text-gray-900">Report Post</h3>
              <button
                onClick={closeReportModal}
                className="w-8 h-8 rounded-full hover:bg-gray-100 flex items-center justify-center transition"
              >
                <X className="w-5 h-5 text-gray-500" />
              </button>
            </div>

            {/* Modal Body */}
            <div className="p-5">
              <p className="text-sm text-gray-600 mb-4">
                Please describe why you are reporting this post. Reports are reviewed by our moderation team.
              </p>

              <textarea
                value={reportReason}
                onChange={(e) => setReportReason(e.target.value)}
                placeholder="Describe the issue (e.g., misinformation, spam, inappropriate content)..."
                className="w-full px-4 py-3 border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-[#1a6b9a] focus:border-transparent resize-none"
                rows={4}
                maxLength={500}
              />
              <div className="flex justify-between items-center mt-1">
                <p className="text-xs text-gray-500">Minimum 10 characters required</p>
                <p className="text-xs text-gray-500">{reportReason.length}/500</p>
              </div>
            </div>

            {/* Modal Footer */}
            <div className="px-5 py-4 border-t border-gray-200 flex gap-3">
              <button
                onClick={closeReportModal}
                className="flex-1 px-4 py-3 bg-gray-100 text-gray-700 rounded-xl font-medium hover:bg-gray-200 transition"
              >
                Cancel
              </button>
              <button
                onClick={handleSubmitReport}
                disabled={isSubmittingReport || reportReason.length < 10}
                className="flex-1 px-4 py-3 bg-orange-500 text-white rounded-xl font-medium hover:bg-orange-600 transition disabled:opacity-50 flex items-center justify-center gap-2"
              >
                {isSubmittingReport ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    Submitting...
                  </>
                ) : (
                  <>
                    <Flag className="w-4 h-4" />
                    Submit Report
                  </>
                )}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Hide Scrollbar Styles */}
      <style jsx>{`
        .scrollbar-hide {
          -ms-overflow-style: none;  /* IE and Edge */
          scrollbar-width: none;  /* Firefox */
        }
        .scrollbar-hide::-webkit-scrollbar {
          display: none;  /* Chrome, Safari, Opera */
        }
      `}</style>

      {/* Floating SOS button for citizens/organizers */}
      <SOSButton />
    </div>
  );
}

export default function DashboardPage() {
  return (
    <ProtectedRoute>
      <DashboardLayout>
        <DashboardContent />
      </DashboardLayout>
    </ProtectedRoute>
  );
}
