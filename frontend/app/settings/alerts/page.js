'use client';

import { useState, useEffect, useCallback } from 'react';
import {
  Bell,
  BellOff,
  MapPin,
  Loader2,
  Save,
  Trash2,
  Check,
  AlertTriangle,
  Waves,
  Wind,
  CloudLightning,
  Droplets,
  Navigation,
  ChevronRight,
  Info,
  Smartphone,
  Settings,
} from 'lucide-react';
import DashboardLayout from '@/components/DashboardLayout';
import ProtectedRoute from '@/components/ProtectedRoute';
import {
  getAlertSubscription,
  subscribeToPredictiveAlerts,
  unsubscribeFromPredictiveAlerts,
  toggleAlertSubscription,
  getVapidPublicKey,
  registerPushSubscription,
  unregisterPushSubscription,
  getAlertThresholds,
} from '@/lib/api';
import toast from 'react-hot-toast';

const ALERT_TYPES = [
  { id: 'high_wave', label: 'High Waves', icon: Waves, color: 'text-cyan-400' },
  { id: 'high_wind', label: 'High Wind', icon: Wind, color: 'text-blue-400' },
  { id: 'cyclone_watch', label: 'Cyclone', icon: CloudLightning, color: 'text-purple-400' },
  { id: 'storm_surge', label: 'Storm Surge', icon: Droplets, color: 'text-orange-400' },
];

const SEVERITY_LEVELS = [
  { id: 'info', label: 'All (Info+)', color: 'bg-slate-500' },
  { id: 'advisory', label: 'Advisory+', color: 'bg-blue-500' },
  { id: 'watch', label: 'Watch+', color: 'bg-yellow-500' },
  { id: 'warning', label: 'Warning+', color: 'bg-orange-500' },
  { id: 'critical', label: 'Critical Only', color: 'bg-red-500' },
];

const RADIUS_OPTIONS = [
  { value: 50, label: '50 km' },
  { value: 100, label: '100 km' },
  { value: 200, label: '200 km' },
  { value: 300, label: '300 km' },
  { value: 500, label: '500 km' },
];

function AlertSettingsPage() {
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [subscription, setSubscription] = useState(null);

  // Form state
  const [enabled, setEnabled] = useState(false);
  const [latitude, setLatitude] = useState('');
  const [longitude, setLongitude] = useState('');
  const [radiusKm, setRadiusKm] = useState(100);
  const [selectedAlertTypes, setSelectedAlertTypes] = useState([]);
  const [minSeverity, setMinSeverity] = useState('advisory');
  const [channels, setChannels] = useState(['push']);

  // Push notification state
  const [pushSupported, setPushSupported] = useState(false);
  const [pushPermission, setPushPermission] = useState('default');
  const [pushEnabled, setPushEnabled] = useState(false);
  const [enablingPush, setEnablingPush] = useState(false);

  // Thresholds
  const [thresholds, setThresholds] = useState(null);

  // Location state
  const [gettingLocation, setGettingLocation] = useState(false);

  // Load subscription and thresholds
  useEffect(() => {
    loadData();
    checkPushSupport();
  }, []);

  const loadData = async () => {
    try {
      setLoading(true);

      // Load subscription
      const subResponse = await getAlertSubscription();
      if (subResponse.success && subResponse.data) {
        const sub = subResponse.data;
        setSubscription(sub);
        setEnabled(sub.enabled !== false);
        setLatitude(sub.latitude?.toString() || '');
        setLongitude(sub.longitude?.toString() || '');
        setRadiusKm(sub.radius_km || 100);
        setSelectedAlertTypes(sub.alert_types || []);
        setMinSeverity(sub.min_severity || 'advisory');
        setChannels(sub.channels || ['push']);
      }

      // Load thresholds
      const thresholdResponse = await getAlertThresholds();
      if (thresholdResponse.success) {
        setThresholds(thresholdResponse.thresholds);
      }
    } catch (error) {
      console.error('Failed to load alert settings:', error);
    } finally {
      setLoading(false);
    }
  };

  const checkPushSupport = async () => {
    if (typeof window === 'undefined') return;

    const supported = 'serviceWorker' in navigator && 'PushManager' in window;
    setPushSupported(supported);

    if (supported) {
      const permission = Notification.permission;
      setPushPermission(permission);
      setPushEnabled(permission === 'granted');
    }
  };

  const getCurrentLocation = useCallback(() => {
    if (!navigator.geolocation) {
      toast.error('Geolocation is not supported by your browser');
      return;
    }

    setGettingLocation(true);

    navigator.geolocation.getCurrentPosition(
      (position) => {
        setLatitude(position.coords.latitude.toFixed(6));
        setLongitude(position.coords.longitude.toFixed(6));
        setGettingLocation(false);
        toast.success('Location captured');
      },
      (error) => {
        setGettingLocation(false);
        toast.error('Failed to get location: ' + error.message);
      },
      { enableHighAccuracy: true, timeout: 10000 }
    );
  }, []);

  const handleEnablePush = async () => {
    if (!pushSupported) {
      toast.error('Push notifications are not supported in your browser');
      return;
    }

    setEnablingPush(true);

    try {
      // Request notification permission
      const permission = await Notification.requestPermission();
      setPushPermission(permission);

      if (permission !== 'granted') {
        toast.error('Notification permission denied');
        setEnablingPush(false);
        return;
      }

      // Get VAPID key
      const vapidResponse = await getVapidPublicKey();
      if (!vapidResponse.success || !vapidResponse.vapid_public_key) {
        toast.error('Push notifications are not configured on the server');
        setEnablingPush(false);
        return;
      }

      // Subscribe to push
      const registration = await navigator.serviceWorker.ready;
      const pushSubscription = await registration.pushManager.subscribe({
        userVisibleOnly: true,
        applicationServerKey: urlBase64ToUint8Array(vapidResponse.vapid_public_key),
      });

      // Send subscription to server
      const subscriptionJson = pushSubscription.toJSON();
      await registerPushSubscription({
        endpoint: subscriptionJson.endpoint,
        keys: subscriptionJson.keys,
        expirationTime: subscriptionJson.expirationTime,
      });

      setPushEnabled(true);
      toast.success('Push notifications enabled');

      // Add push to channels if not already there
      if (!channels.includes('push')) {
        setChannels([...channels, 'push']);
      }
    } catch (error) {
      console.error('Failed to enable push:', error);
      toast.error('Failed to enable push notifications');
    } finally {
      setEnablingPush(false);
    }
  };

  const handleDisablePush = async () => {
    try {
      const registration = await navigator.serviceWorker.ready;
      const subscription = await registration.pushManager.getSubscription();

      if (subscription) {
        await subscription.unsubscribe();
        await unregisterPushSubscription(subscription.endpoint);
      }

      setPushEnabled(false);
      toast.success('Push notifications disabled');

      // Remove push from channels
      setChannels(channels.filter((c) => c !== 'push'));
    } catch (error) {
      console.error('Failed to disable push:', error);
      toast.error('Failed to disable push notifications');
    }
  };

  const handleSave = async () => {
    if (!latitude || !longitude) {
      toast.error('Please set your location');
      return;
    }

    setSaving(true);

    try {
      const response = await subscribeToPredictiveAlerts({
        latitude: parseFloat(latitude),
        longitude: parseFloat(longitude),
        radius_km: radiusKm,
        alert_types: selectedAlertTypes.length > 0 ? selectedAlertTypes : null,
        min_severity: minSeverity,
        channels,
        enabled,
      });

      if (response.success) {
        toast.success('Alert settings saved');
        setSubscription(response.data);
      } else {
        toast.error(response.message || 'Failed to save settings');
      }
    } catch (error) {
      console.error('Failed to save settings:', error);
      toast.error('Failed to save alert settings');
    } finally {
      setSaving(false);
    }
  };

  const handleUnsubscribe = async () => {
    if (!confirm('Are you sure you want to unsubscribe from all alerts?')) {
      return;
    }

    try {
      await unsubscribeFromPredictiveAlerts();
      setSubscription(null);
      setEnabled(false);
      setLatitude('');
      setLongitude('');
      toast.success('Unsubscribed from alerts');
    } catch (error) {
      console.error('Failed to unsubscribe:', error);
      toast.error('Failed to unsubscribe');
    }
  };

  const toggleAlertType = (typeId) => {
    if (selectedAlertTypes.includes(typeId)) {
      setSelectedAlertTypes(selectedAlertTypes.filter((t) => t !== typeId));
    } else {
      setSelectedAlertTypes([...selectedAlertTypes, typeId]);
    }
  };

  // Convert VAPID key to Uint8Array
  function urlBase64ToUint8Array(base64String) {
    const padding = '='.repeat((4 - (base64String.length % 4)) % 4);
    const base64 = (base64String + padding).replace(/-/g, '+').replace(/_/g, '/');
    const rawData = window.atob(base64);
    const outputArray = new Uint8Array(rawData.length);
    for (let i = 0; i < rawData.length; ++i) {
      outputArray[i] = rawData.charCodeAt(i);
    }
    return outputArray;
  }

  if (loading) {
    return (
      <DashboardLayout>
        <div className="flex items-center justify-center h-64">
          <Loader2 className="w-8 h-8 animate-spin text-cyan-500" />
        </div>
      </DashboardLayout>
    );
  }

  return (
    <DashboardLayout>
      <div className="max-w-3xl mx-auto p-4 lg:p-8">
        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="text-2xl font-bold text-white">Alert Settings</h1>
            <p className="text-slate-400 mt-1">Configure predictive weather alerts for your location</p>
          </div>
          <div className="flex items-center gap-2">
            <span className={`px-3 py-1 rounded-full text-sm font-medium ${enabled ? 'bg-green-500/20 text-green-400' : 'bg-slate-700 text-slate-400'}`}>
              {enabled ? 'Active' : 'Inactive'}
            </span>
          </div>
        </div>

        {/* Main Settings Card */}
        <div className="bg-slate-800 rounded-xl border border-slate-700 overflow-hidden">
          {/* Enable/Disable Toggle */}
          <div className="p-6 border-b border-slate-700">
            <label className="flex items-center justify-between cursor-pointer">
              <div className="flex items-center gap-3">
                {enabled ? (
                  <Bell className="w-6 h-6 text-cyan-400" />
                ) : (
                  <BellOff className="w-6 h-6 text-slate-400" />
                )}
                <div>
                  <p className="font-medium text-white">Alert Notifications</p>
                  <p className="text-sm text-slate-400">Receive alerts when conditions exceed IMD thresholds</p>
                </div>
              </div>
              <div className="relative">
                <input
                  type="checkbox"
                  checked={enabled}
                  onChange={(e) => setEnabled(e.target.checked)}
                  className="sr-only"
                />
                <div className={`w-14 h-7 rounded-full transition-colors ${enabled ? 'bg-cyan-600' : 'bg-slate-600'}`}>
                  <div className={`absolute top-0.5 left-0.5 w-6 h-6 rounded-full bg-white transition-transform ${enabled ? 'translate-x-7' : ''}`} />
                </div>
              </div>
            </label>
          </div>

          {/* Location Section */}
          <div className="p-6 border-b border-slate-700">
            <div className="flex items-center gap-2 mb-4">
              <MapPin className="w-5 h-5 text-cyan-400" />
              <h3 className="font-medium text-white">Monitoring Location</h3>
            </div>

            <div className="grid grid-cols-2 gap-4 mb-4">
              <div>
                <label className="block text-sm text-slate-400 mb-1">Latitude</label>
                <input
                  type="number"
                  step="0.000001"
                  value={latitude}
                  onChange={(e) => setLatitude(e.target.value)}
                  placeholder="e.g., 13.0827"
                  className="w-full px-3 py-2 bg-slate-700 border border-slate-600 rounded-lg text-white placeholder-slate-400 focus:outline-none focus:border-cyan-500"
                />
              </div>
              <div>
                <label className="block text-sm text-slate-400 mb-1">Longitude</label>
                <input
                  type="number"
                  step="0.000001"
                  value={longitude}
                  onChange={(e) => setLongitude(e.target.value)}
                  placeholder="e.g., 80.2707"
                  className="w-full px-3 py-2 bg-slate-700 border border-slate-600 rounded-lg text-white placeholder-slate-400 focus:outline-none focus:border-cyan-500"
                />
              </div>
            </div>

            <div className="flex items-center gap-4">
              <button
                onClick={getCurrentLocation}
                disabled={gettingLocation}
                className="flex items-center gap-2 px-4 py-2 bg-slate-700 hover:bg-slate-600 text-white rounded-lg transition-colors"
              >
                {gettingLocation ? (
                  <Loader2 className="w-4 h-4 animate-spin" />
                ) : (
                  <Navigation className="w-4 h-4" />
                )}
                Use Current Location
              </button>

              <div>
                <label className="block text-sm text-slate-400 mb-1">Alert Radius</label>
                <select
                  value={radiusKm}
                  onChange={(e) => setRadiusKm(Number(e.target.value))}
                  className="px-3 py-2 bg-slate-700 border border-slate-600 rounded-lg text-white focus:outline-none focus:border-cyan-500"
                >
                  {RADIUS_OPTIONS.map((opt) => (
                    <option key={opt.value} value={opt.value}>
                      {opt.label}
                    </option>
                  ))}
                </select>
              </div>
            </div>
          </div>

          {/* Alert Types Section */}
          <div className="p-6 border-b border-slate-700">
            <div className="flex items-center gap-2 mb-4">
              <AlertTriangle className="w-5 h-5 text-cyan-400" />
              <h3 className="font-medium text-white">Alert Types</h3>
              <span className="text-sm text-slate-400 ml-auto">
                {selectedAlertTypes.length === 0 ? 'All types' : `${selectedAlertTypes.length} selected`}
              </span>
            </div>

            <div className="grid grid-cols-2 gap-3">
              {ALERT_TYPES.map((type) => {
                const Icon = type.icon;
                const isSelected = selectedAlertTypes.length === 0 || selectedAlertTypes.includes(type.id);

                return (
                  <button
                    key={type.id}
                    onClick={() => toggleAlertType(type.id)}
                    className={`flex items-center gap-3 p-3 rounded-lg border transition-colors ${
                      isSelected
                        ? 'bg-slate-700 border-cyan-500'
                        : 'bg-slate-800 border-slate-600 opacity-50'
                    }`}
                  >
                    <Icon className={`w-5 h-5 ${type.color}`} />
                    <span className="text-white text-sm">{type.label}</span>
                    {isSelected && <Check className="w-4 h-4 text-cyan-400 ml-auto" />}
                  </button>
                );
              })}
            </div>

            <p className="text-xs text-slate-500 mt-3">
              Leave all unselected to receive all alert types
            </p>
          </div>

          {/* Severity Section */}
          <div className="p-6 border-b border-slate-700">
            <div className="flex items-center gap-2 mb-4">
              <Settings className="w-5 h-5 text-cyan-400" />
              <h3 className="font-medium text-white">Minimum Severity</h3>
            </div>

            <div className="flex flex-wrap gap-2">
              {SEVERITY_LEVELS.map((level) => (
                <button
                  key={level.id}
                  onClick={() => setMinSeverity(level.id)}
                  className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                    minSeverity === level.id
                      ? `${level.color} text-white`
                      : 'bg-slate-700 text-slate-300 hover:bg-slate-600'
                  }`}
                >
                  {level.label}
                </button>
              ))}
            </div>
          </div>

          {/* Push Notifications Section */}
          <div className="p-6 border-b border-slate-700">
            <div className="flex items-center gap-2 mb-4">
              <Smartphone className="w-5 h-5 text-cyan-400" />
              <h3 className="font-medium text-white">Push Notifications</h3>
            </div>

            {!pushSupported ? (
              <div className="flex items-center gap-2 p-3 bg-amber-500/10 border border-amber-500/30 rounded-lg">
                <Info className="w-5 h-5 text-amber-400" />
                <p className="text-sm text-amber-200">Push notifications are not supported in your browser</p>
              </div>
            ) : pushEnabled ? (
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <div className="w-3 h-3 rounded-full bg-green-500 animate-pulse" />
                  <span className="text-green-400">Push notifications enabled</span>
                </div>
                <button
                  onClick={handleDisablePush}
                  className="px-4 py-2 bg-slate-700 hover:bg-slate-600 text-slate-300 rounded-lg transition-colors"
                >
                  Disable
                </button>
              </div>
            ) : (
              <button
                onClick={handleEnablePush}
                disabled={enablingPush}
                className="flex items-center gap-2 px-4 py-2 bg-cyan-600 hover:bg-cyan-500 text-white rounded-lg transition-colors"
              >
                {enablingPush ? (
                  <Loader2 className="w-4 h-4 animate-spin" />
                ) : (
                  <Bell className="w-4 h-4" />
                )}
                Enable Push Notifications
              </button>
            )}
          </div>

          {/* IMD Thresholds Info */}
          {thresholds && (
            <div className="p-6 bg-slate-800/50">
              <div className="flex items-center gap-2 mb-3">
                <Info className="w-5 h-5 text-slate-400" />
                <h3 className="font-medium text-slate-300">IMD Standard Thresholds</h3>
              </div>
              <div className="grid grid-cols-2 gap-4 text-sm">
                <div>
                  <p className="text-slate-400 mb-1">Wave Height Warnings:</p>
                  <p className="text-slate-300">Advisory: {thresholds.wave_height_meters?.small_craft_advisory}m</p>
                  <p className="text-slate-300">Warning: {thresholds.wave_height_meters?.fishing_warning}m</p>
                </div>
                <div>
                  <p className="text-slate-400 mb-1">Wind Speed Warnings:</p>
                  <p className="text-slate-300">Gale: {thresholds.wind_speed_knots?.gale_warning} knots</p>
                  <p className="text-slate-300">Storm: {thresholds.wind_speed_knots?.storm_warning} knots</p>
                </div>
                <div>
                  <p className="text-slate-400 mb-1">Cyclone Watch Distance:</p>
                  <p className="text-slate-300">Watch: {thresholds.cyclone_distance_km?.cyclone_watch} km</p>
                  <p className="text-slate-300">Alert: {thresholds.cyclone_distance_km?.cyclone_alert} km</p>
                </div>
                <div>
                  <p className="text-slate-400 mb-1">Storm Surge:</p>
                  <p className="text-slate-300">Warning: {thresholds.storm_surge_meters?.warning}m</p>
                  <p className="text-slate-300">Danger: {thresholds.storm_surge_meters?.danger}m</p>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Action Buttons */}
        <div className="flex items-center justify-between mt-6">
          {subscription && (
            <button
              onClick={handleUnsubscribe}
              className="flex items-center gap-2 px-4 py-2 bg-red-500/20 hover:bg-red-500/30 text-red-400 rounded-lg transition-colors"
            >
              <Trash2 className="w-4 h-4" />
              Unsubscribe
            </button>
          )}

          <button
            onClick={handleSave}
            disabled={saving || !latitude || !longitude}
            className="flex items-center gap-2 px-6 py-3 bg-cyan-600 hover:bg-cyan-500 disabled:bg-slate-700 disabled:cursor-not-allowed text-white font-medium rounded-lg transition-colors ml-auto"
          >
            {saving ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <Save className="w-4 h-4" />
            )}
            Save Settings
          </button>
        </div>
      </div>
    </DashboardLayout>
  );
}

export default function AlertSettingsPageWrapper() {
  return (
    <ProtectedRoute>
      <AlertSettingsPage />
    </ProtectedRoute>
  );
}
