'use client';

import { useEffect, useState } from 'react';
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
  TrendingUp,
  ThermometerSun,
  Heart,
  MessageSquare,
  MoreVertical,
  CheckCircle,
  Clock,
  Loader2,
  Users,
  Eye,
  Waves
} from 'lucide-react';
import toast, { Toaster } from 'react-hot-toast';
import { getHazardReports } from '@/lib/api';

function DashboardContent() {
  const router = useRouter();
  const { user } = useAuthStore();
  const [feedPosts, setFeedPosts] = useState([]);
  const [isLoadingFeed, setIsLoadingFeed] = useState(true);
  const [weatherData, setWeatherData] = useState({
    temperature: '--',
    condition: 'Loading...',
    waveHeight: '--',
    wind: '--',
    precipitation: '--',
    location: 'Detecting...',
    isLoading: true
  });

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
              const weatherApiKey = process.env.NEXT_PUBLIC_WEATHER_API_KEY || '9eb5843c7dfd41f181e173939252001';

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

  // Fetch hazard reports on component mount
  useEffect(() => {
    const fetchHazardReports = async () => {
      try {
        setIsLoadingFeed(true);
        const response = await getHazardReports({
          page: 1,
          page_size: 10,
          verification_status: 'verified'
        });

        const transformedPosts = response.reports.map(report => ({
          id: report._id,
          report_id: report.report_id,
          user: {
            name: report.user_name || 'Anonymous',
            avatar: null
          },
          image: `${process.env.NEXT_PUBLIC_API_URL?.replace('/api/v1', '') || 'http://localhost:8000'}${report.image_url}`,
          description: report.description || `${report.hazard_type} reported`,
          location: report.location.address || 'Unknown Location',
          distance: 'Nearby',
          likes: report.likes,
          comments: report.comments,
          verificationStatus: report.verification_status,
          hazardType: report.hazard_type,
          created_at: report.created_at
        }));

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

  const quickActions = [
    {
      id: 'report',
      icon: AlertTriangle,
      title: 'Report Hazard',
      color: 'from-red-500 to-orange-600',
      onClick: () => router.push('/report-hazard')
    },
    {
      id: 'map',
      icon: MapPin,
      title: 'Map View',
      color: 'from-blue-500 to-cyan-600',
      onClick: () => router.push('/map')
    },
    {
      id: 'chat',
      icon: MessageCircle,
      title: 'Community',
      color: 'from-cyan-500 to-blue-600',
      onClick: () => router.push('/community')
    },
    {
      id: 'safety',
      icon: Shield,
      title: 'Safety Tips',
      color: 'from-green-500 to-emerald-600',
      onClick: () => router.push('/safety')
    }
  ];

  // Stats data
  const stats = [
    {
      name: 'Total Reports',
      value: user?.total_reports || 0,
      icon: AlertTriangle,
      color: 'from-red-500 to-orange-500',
      change: '+12%'
    },
    {
      name: 'Verified Reports',
      value: user?.verified_reports || 0,
      icon: CheckCircle,
      color: 'from-green-500 to-emerald-500',
      change: '+8%'
    },
    {
      name: 'Credibility Score',
      value: user?.credibility_score || 50,
      icon: TrendingUp,
      color: 'from-blue-500 to-cyan-500',
      change: '+5%'
    },
    {
      name: 'Community Impact',
      value: '2.4K',
      icon: Users,
      color: 'from-purple-500 to-pink-500',
      change: '+15%'
    }
  ];

  return (
    <div className="p-4 lg:p-8 max-w-7xl mx-auto">
      <Toaster position="top-center" />

      {/* Main Content - Single Column Clean Layout */}
      <div className="space-y-6">
          {/* Weather Nugget Card */}
          <div className="bg-gradient-to-br from-blue-500 via-blue-600 to-blue-700 rounded-2xl shadow-xl p-6 text-white">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-semibold flex items-center">
                <Waves className="w-5 h-5 mr-2" />
                Weather Nugget
              </h2>
              {weatherData.isLoading && (
                <Loader2 className="w-5 h-5 animate-spin" />
              )}
            </div>

            <div className="mb-2">
              <p className="text-sm text-blue-100 flex items-center">
                <MapPin className="w-4 h-4 mr-1" />
                {weatherData.location}
              </p>
            </div>

            <div className="flex items-start justify-between mb-6">
              <div className="flex items-center space-x-4">
                <div className="text-6xl font-bold">{weatherData.temperature}°</div>
                <div className={`px-4 py-2 rounded-full text-sm font-semibold ${
                  weatherData.condition === 'High'
                    ? 'bg-red-400 bg-opacity-90 text-red-900'
                    : weatherData.condition === 'Medium'
                    ? 'bg-yellow-400 bg-opacity-90 text-yellow-900'
                    : 'bg-green-400 bg-opacity-90 text-green-900'
                }`}>
                  {weatherData.condition}
                </div>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div className="bg-white bg-opacity-20 backdrop-blur-sm rounded-xl p-4 border border-white border-opacity-30">
                <div className="flex items-center space-x-2 mb-1">
                  <Waves className="w-5 h-5 text-white" />
                  <p className="text-xs text-blue-100 font-medium uppercase tracking-wide">Wave Height</p>
                </div>
                <p className="text-2xl font-bold text-white">{weatherData.waveHeight}</p>
              </div>

              <div className="bg-white bg-opacity-20 backdrop-blur-sm rounded-xl p-4 border border-white border-opacity-30">
                <div className="flex items-center space-x-2 mb-1">
                  <Wind className="w-5 h-5 text-white" />
                  <p className="text-xs text-blue-100 font-medium uppercase tracking-wide">Wind Speed</p>
                </div>
                <p className="text-2xl font-bold text-white">{weatherData.wind}</p>
              </div>

              <div className="bg-white bg-opacity-20 backdrop-blur-sm rounded-xl p-4 border border-white border-opacity-30">
                <div className="flex items-center space-x-2 mb-1">
                  <Droplets className="w-5 h-5 text-white" />
                  <p className="text-xs text-blue-100 font-medium uppercase tracking-wide">Precipitation</p>
                </div>
                <p className="text-lg font-bold text-white">{weatherData.precipitation}</p>
              </div>

              <div className="bg-white bg-opacity-20 backdrop-blur-sm rounded-xl p-4 border border-white border-opacity-30">
                <div className="flex items-center space-x-2 mb-1">
                  <ThermometerSun className="w-5 h-5 text-white" />
                  <p className="text-xs text-blue-100 font-medium uppercase tracking-wide">Humidity</p>
                </div>
                <p className="text-lg font-bold text-white">{weatherData.humidity || '--'}%</p>
              </div>
            </div>
          </div>

          {/* Quick Actions Grid */}
          <div className="grid grid-cols-2 gap-4">
            {quickActions.map((action) => {
              const Icon = action.icon;
              return (
                <button
                  key={action.id}
                  onClick={action.onClick}
                  className="bg-white rounded-2xl shadow-md hover:shadow-xl transition-all p-6 text-left group"
                >
                  <div className={`w-14 h-14 bg-gradient-to-br ${action.color} rounded-2xl flex items-center justify-center mb-4 group-hover:scale-110 transition-transform`}>
                    <Icon className="w-7 h-7 text-white" />
                  </div>
                  <h3 className="font-bold text-gray-900 text-base">{action.title}</h3>
                </button>
              );
            })}
          </div>

          {/* Community Feed */}
          <div className="space-y-4">
            <h2 className="text-xl font-bold text-gray-900 px-1">Community Feed</h2>

            {isLoadingFeed ? (
              <div className="bg-white rounded-2xl shadow-md p-12 flex flex-col items-center justify-center">
                <Loader2 className="w-12 h-12 text-blue-600 animate-spin mb-4" />
                <p className="text-gray-600">Loading hazard reports...</p>
              </div>
            ) : feedPosts.length === 0 ? (
              <div className="bg-white rounded-2xl shadow-md p-12 flex flex-col items-center justify-center">
                <AlertTriangle className="w-16 h-16 text-gray-300 mb-4" />
                <p className="text-gray-600 text-center">No verified hazard reports yet.<br />Be the first to report a hazard!</p>
              </div>
            ) : (
              feedPosts.map((post) => (
                <div key={post.id} className="bg-white rounded-2xl shadow-md overflow-hidden hover:shadow-lg transition-shadow">
                  {/* Post Header */}
                  <div className="flex items-center justify-between p-4">
                    <div className="flex items-center space-x-3">
                      <div className="w-10 h-10 bg-gradient-to-br from-blue-400 to-cyan-500 rounded-full flex items-center justify-center">
                        <User className="w-5 h-5 text-white" />
                      </div>
                      <span className="font-semibold text-gray-900">{post.user.name}</span>
                    </div>
                    <button className="text-gray-400 hover:text-gray-600">
                      <MoreVertical className="w-5 h-5" />
                    </button>
                  </div>

                  {/* Post Image */}
                  <div className="relative h-64 bg-gray-200">
                    <img
                      src={post.image}
                      alt={post.description}
                      className="w-full h-full object-cover"
                    />
                    {/* Verification Badge Overlay */}
                    {post.verificationStatus === 'verified' ? (
                      <div className="absolute top-3 right-3 bg-green-500 text-white px-3 py-1.5 rounded-full text-xs font-semibold flex items-center space-x-1 shadow-lg">
                        <CheckCircle className="w-3.5 h-3.5" />
                        <span>Verified</span>
                      </div>
                    ) : post.verificationStatus === 'pending' ? (
                      <div className="absolute top-3 right-3 bg-yellow-500 text-white px-3 py-1.5 rounded-full text-xs font-semibold flex items-center space-x-1 shadow-lg">
                        <Clock className="w-3.5 h-3.5" />
                        <span>Pending Verification</span>
                      </div>
                    ) : null}
                  </div>

                  {/* Post Content */}
                  <div className="p-4">
                    <p className="text-gray-800 mb-3">{post.description}</p>

                    <div className="flex items-center justify-between">
                      <div className="flex items-center space-x-2 text-sm text-gray-600">
                        <MapPin className="w-4 h-4 text-blue-600" />
                        <span className="font-medium">{post.location}</span>
                        <span>•</span>
                        <span>{post.distance}</span>
                      </div>

                      <div className="flex items-center space-x-4 text-sm text-gray-600">
                        <div className="flex items-center space-x-1">
                          <Heart className="w-4 h-4" />
                          <span>{post.likes}</span>
                        </div>
                        <div className="flex items-center space-x-1">
                          <MessageSquare className="w-4 h-4" />
                          <span>{post.comments}</span>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>

        {/* Right Column - Stats & Info (Desktop only) */}
        <div className="hidden lg:block space-y-6">
          {/* User Stats Card */}
          <div className="bg-white rounded-2xl shadow-md p-6">
            <h3 className="font-bold text-gray-900 mb-4 flex items-center">
              <Shield className="w-5 h-5 mr-2 text-blue-600" />
              Your Stats
            </h3>

            <div className="space-y-4">
              <div className="flex justify-between items-center">
                <span className="text-gray-600">Credibility Score</span>
                <span className="font-bold text-blue-600 text-xl">{user?.credibility_score || 50}</span>
              </div>
              <div className="w-full bg-gray-200 rounded-full h-2">
                <div
                  className="bg-gradient-to-r from-blue-500 to-cyan-500 h-2 rounded-full"
                  style={{ width: `${user?.credibility_score || 50}%` }}
                ></div>
              </div>

              <div className="pt-4 border-t border-gray-100 space-y-3">
                <div className="flex justify-between">
                  <span className="text-gray-600">Reports Submitted</span>
                  <span className="font-semibold text-gray-900">{user?.total_reports || 0}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600">Verified Reports</span>
                  <span className="font-semibold text-gray-900">{user?.verified_reports || 0}</span>
                </div>
              </div>
            </div>
          </div>

          {/* Recent Activity Card */}
          <div className="bg-white rounded-2xl shadow-md p-6">
            <h3 className="font-bold text-gray-900 mb-4">Recent Activity</h3>
            <div className="space-y-3">
              <div className="flex items-center space-x-3 text-sm">
                <div className="w-2 h-2 bg-blue-500 rounded-full"></div>
                <span className="text-gray-600">No recent activity</span>
              </div>
            </div>
          </div>

          {/* Quick Info Card */}
          <div className="bg-gradient-to-br from-cyan-500 to-blue-600 rounded-2xl shadow-md p-6 text-white">
            <h3 className="font-bold mb-2">Safety Tip</h3>
            <p className="text-sm text-blue-50">
              Always check weather conditions before heading to the beach. Stay safe and report any hazards you observe.
            </p>
          </div>
        </div>
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
