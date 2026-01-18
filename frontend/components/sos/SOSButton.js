'use client';

import React, { useState, useCallback, useEffect, useRef } from 'react';
import { Phone, X, AlertTriangle, Loader2, MapPin, Check, Ship } from 'lucide-react';
import { triggerSOS, cancelSOS } from '@/lib/api';
import useAuthStore from '@/context/AuthContext';
import toast from 'react-hot-toast';

const COUNTDOWN_SECONDS = 3;

const SOSButton = ({
  className = '',
  onSOSTriggered = null,
  showFloating = true
}) => {
  const user = useAuthStore((state) => state.user);
  const isAuthenticated = useAuthStore((state) => state.isAuthenticated);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [isCountingDown, setIsCountingDown] = useState(false);
  const [countdown, setCountdown] = useState(COUNTDOWN_SECONDS);
  const [isTriggering, setIsTriggering] = useState(false);
  const [location, setLocation] = useState(null);
  const [locationError, setLocationError] = useState(null);
  const [isGettingLocation, setIsGettingLocation] = useState(false);
  const [activeSOS, setActiveSOS] = useState(null);
  const [vesselInfo, setVesselInfo] = useState({ id: '', name: '', crewCount: 1 });
  const [message, setMessage] = useState('');

  const countdownRef = useRef(null);

  // Get user's current location
  const getCurrentLocation = useCallback(() => {
    if (!navigator.geolocation) {
      setLocationError('Geolocation is not supported by your browser');
      return;
    }

    setIsGettingLocation(true);
    setLocationError(null);

    navigator.geolocation.getCurrentPosition(
      (position) => {
        setLocation({
          latitude: position.coords.latitude,
          longitude: position.coords.longitude,
          accuracy: position.coords.accuracy,
        });
        setIsGettingLocation(false);
      },
      (error) => {
        let errorMessage = 'Unable to get your location';
        switch (error.code) {
          case error.PERMISSION_DENIED:
            errorMessage = 'Location permission denied. Please enable GPS.';
            break;
          case error.POSITION_UNAVAILABLE:
            errorMessage = 'Location unavailable. Please check GPS settings.';
            break;
          case error.TIMEOUT:
            errorMessage = 'Location request timed out. Please try again.';
            break;
        }
        setLocationError(errorMessage);
        setIsGettingLocation(false);
      },
      {
        enableHighAccuracy: true,
        timeout: 10000,
        maximumAge: 0,
      }
    );
  }, []);

  // Get location when modal opens
  useEffect(() => {
    if (isModalOpen && !location) {
      getCurrentLocation();
    }
  }, [isModalOpen, location, getCurrentLocation]);

  // Countdown logic
  useEffect(() => {
    if (isCountingDown && countdown > 0) {
      countdownRef.current = setTimeout(() => {
        setCountdown(countdown - 1);
      }, 1000);
    } else if (isCountingDown && countdown === 0) {
      // Trigger SOS when countdown reaches 0
      handleTriggerSOS();
    }

    return () => {
      if (countdownRef.current) {
        clearTimeout(countdownRef.current);
      }
    };
  }, [isCountingDown, countdown]);

  const handleOpenModal = () => {
    if (!isAuthenticated) {
      toast.error('Please login to use SOS feature');
      return;
    }
    setIsModalOpen(true);
    setCountdown(COUNTDOWN_SECONDS);
    setIsCountingDown(false);
  };

  const handleStartCountdown = () => {
    if (!location) {
      toast.error('Location is required for SOS');
      getCurrentLocation();
      return;
    }
    setIsCountingDown(true);
    setCountdown(COUNTDOWN_SECONDS);
  };

  const handleCancelCountdown = () => {
    setIsCountingDown(false);
    setCountdown(COUNTDOWN_SECONDS);
    if (countdownRef.current) {
      clearTimeout(countdownRef.current);
    }
  };

  const handleCloseModal = () => {
    handleCancelCountdown();
    setIsModalOpen(false);
    setActiveSOS(null);
    setMessage('');
  };

  const handleTriggerSOS = async () => {
    setIsCountingDown(false);
    setIsTriggering(true);

    try {
      const response = await triggerSOS({
        latitude: location.latitude,
        longitude: location.longitude,
        vessel_id: vesselInfo.id || undefined,
        vessel_name: vesselInfo.name || undefined,
        crew_count: vesselInfo.crewCount || 1,
        message: message || undefined,
        priority: 'critical',
      });

      if (response.success) {
        setActiveSOS(response);
        toast.success('SOS Alert Sent! Help is on the way.', {
          duration: 5000,
          icon: '🆘',
        });

        if (onSOSTriggered) {
          onSOSTriggered(response);
        }
      } else {
        throw new Error(response.message || 'Failed to send SOS');
      }
    } catch (error) {
      console.error('SOS trigger error:', error);
      toast.error(error.message || 'Failed to send SOS. Please try again.');
    } finally {
      setIsTriggering(false);
    }
  };

  const handleCancelSOS = async () => {
    if (!activeSOS?.sos_id) return;

    try {
      const response = await cancelSOS(activeSOS.sos_id, {
        reason: 'User cancelled - situation resolved',
      });

      if (response.success) {
        toast.success('SOS cancelled successfully');
        setActiveSOS(null);
        handleCloseModal();
      }
    } catch (error) {
      console.error('Cancel SOS error:', error);
      toast.error('Failed to cancel SOS');
    }
  };

  // Don't render for non-citizen users (authorities don't need SOS)
  if (!isAuthenticated || !['citizen', 'organizer'].includes(user?.role)) {
    return null;
  }

  return (
    <>
      {/* Floating SOS Button */}
      {showFloating && (
        <button
          onClick={handleOpenModal}
          className={`fixed z-[1000] bottom-20 right-4 lg:bottom-8 lg:right-8
            w-16 h-16 rounded-full bg-red-600 hover:bg-red-700
            text-white shadow-lg shadow-red-600/30
            flex items-center justify-center
            transition-all duration-300 hover:scale-110
            animate-pulse hover:animate-none
            ${activeSOS ? 'ring-4 ring-red-400 ring-offset-2' : ''}
            ${className}`}
          title="Emergency SOS"
        >
          <span className="text-xl font-bold">SOS</span>
        </button>
      )}

      {/* SOS Modal */}
      {isModalOpen && (
        <div className="fixed inset-0 z-[2000] flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm">
          <div className="bg-slate-900 rounded-2xl w-full max-w-md shadow-2xl border border-slate-700 overflow-hidden">
            {/* Header */}
            <div className="bg-red-600 p-4 flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-full bg-white/20 flex items-center justify-center">
                  <Phone className="w-5 h-5 text-white" />
                </div>
                <div>
                  <h2 className="text-lg font-bold text-white">Emergency SOS</h2>
                  <p className="text-red-100 text-xs">Coast Guard Emergency Alert</p>
                </div>
              </div>
              <button
                onClick={handleCloseModal}
                className="p-2 hover:bg-white/10 rounded-lg transition-colors"
              >
                <X className="w-5 h-5 text-white" />
              </button>
            </div>

            <div className="p-6">
              {/* Success State */}
              {activeSOS && (
                <div className="text-center">
                  <div className="w-20 h-20 rounded-full bg-green-500/20 mx-auto mb-4 flex items-center justify-center">
                    <Check className="w-10 h-10 text-green-400" />
                  </div>
                  <h3 className="text-xl font-bold text-white mb-2">SOS Sent Successfully!</h3>
                  <p className="text-slate-400 text-sm mb-4">
                    Alert ID: <span className="text-cyan-400 font-mono">{activeSOS.sos_id}</span>
                  </p>
                  <p className="text-slate-300 text-sm mb-6">
                    Emergency contacts and nearby Coast Guard stations have been notified.
                    Stay calm and wait for rescue.
                  </p>
                  <div className="flex gap-3">
                    <button
                      onClick={handleCancelSOS}
                      className="flex-1 px-4 py-3 rounded-xl bg-slate-700 hover:bg-slate-600 text-white font-medium transition-colors"
                    >
                      Cancel SOS (False Alarm)
                    </button>
                    <button
                      onClick={handleCloseModal}
                      className="flex-1 px-4 py-3 rounded-xl bg-cyan-600 hover:bg-cyan-500 text-white font-medium transition-colors"
                    >
                      Close
                    </button>
                  </div>
                </div>
              )}

              {/* Countdown State */}
              {!activeSOS && isCountingDown && (
                <div className="text-center">
                  <div className="w-32 h-32 rounded-full border-4 border-red-500 mx-auto mb-4 flex items-center justify-center animate-pulse">
                    <span className="text-5xl font-bold text-red-500">{countdown}</span>
                  </div>
                  <p className="text-slate-300 text-lg mb-2">Sending SOS in {countdown} seconds...</p>
                  <p className="text-slate-400 text-sm mb-6">Tap Cancel to stop</p>
                  <button
                    onClick={handleCancelCountdown}
                    className="w-full px-4 py-4 rounded-xl bg-slate-700 hover:bg-slate-600 text-white font-bold text-lg transition-colors"
                  >
                    CANCEL
                  </button>
                </div>
              )}

              {/* Loading State */}
              {!activeSOS && isTriggering && (
                <div className="text-center py-8">
                  <Loader2 className="w-16 h-16 text-red-500 mx-auto mb-4 animate-spin" />
                  <p className="text-white text-lg">Sending SOS Alert...</p>
                  <p className="text-slate-400 text-sm">Please wait</p>
                </div>
              )}

              {/* Initial State */}
              {!activeSOS && !isCountingDown && !isTriggering && (
                <>
                  {/* Location Status */}
                  <div className="mb-4 p-3 rounded-xl bg-slate-800 border border-slate-700">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <MapPin className={`w-4 h-4 ${location ? 'text-green-400' : 'text-slate-400'}`} />
                        <span className="text-sm text-slate-300">GPS Location</span>
                      </div>
                      {isGettingLocation ? (
                        <Loader2 className="w-4 h-4 text-cyan-400 animate-spin" />
                      ) : location ? (
                        <span className="text-xs text-green-400 font-mono">
                          {location.latitude.toFixed(4)}, {location.longitude.toFixed(4)}
                        </span>
                      ) : (
                        <button
                          onClick={getCurrentLocation}
                          className="text-xs text-cyan-400 hover:text-cyan-300"
                        >
                          Get Location
                        </button>
                      )}
                    </div>
                    {locationError && (
                      <p className="text-red-400 text-xs mt-2">{locationError}</p>
                    )}
                  </div>

                  {/* Vessel Info (Optional) */}
                  <div className="mb-4 p-3 rounded-xl bg-slate-800 border border-slate-700">
                    <div className="flex items-center gap-2 mb-3">
                      <Ship className="w-4 h-4 text-slate-400" />
                      <span className="text-sm text-slate-300">Vessel Info (Optional)</span>
                    </div>
                    <div className="grid grid-cols-2 gap-2">
                      <input
                        type="text"
                        placeholder="Vessel ID"
                        value={vesselInfo.id}
                        onChange={(e) => setVesselInfo({ ...vesselInfo, id: e.target.value })}
                        className="px-3 py-2 rounded-lg bg-slate-700 border border-slate-600 text-white text-sm placeholder-slate-400 focus:outline-none focus:border-cyan-500"
                      />
                      <input
                        type="text"
                        placeholder="Vessel Name"
                        value={vesselInfo.name}
                        onChange={(e) => setVesselInfo({ ...vesselInfo, name: e.target.value })}
                        className="px-3 py-2 rounded-lg bg-slate-700 border border-slate-600 text-white text-sm placeholder-slate-400 focus:outline-none focus:border-cyan-500"
                      />
                    </div>
                    <div className="mt-2">
                      <label className="text-xs text-slate-400">People on board</label>
                      <input
                        type="number"
                        min="1"
                        max="100"
                        value={vesselInfo.crewCount}
                        onChange={(e) => setVesselInfo({ ...vesselInfo, crewCount: parseInt(e.target.value) || 1 })}
                        className="w-full mt-1 px-3 py-2 rounded-lg bg-slate-700 border border-slate-600 text-white text-sm focus:outline-none focus:border-cyan-500"
                      />
                    </div>
                  </div>

                  {/* Message (Optional) */}
                  <div className="mb-6">
                    <textarea
                      placeholder="Brief distress message (optional)"
                      value={message}
                      onChange={(e) => setMessage(e.target.value)}
                      maxLength={500}
                      rows={2}
                      className="w-full px-3 py-2 rounded-xl bg-slate-800 border border-slate-700 text-white text-sm placeholder-slate-400 focus:outline-none focus:border-cyan-500 resize-none"
                    />
                  </div>

                  {/* Warning */}
                  <div className="mb-6 p-3 rounded-xl bg-amber-500/10 border border-amber-500/30">
                    <div className="flex items-start gap-2">
                      <AlertTriangle className="w-5 h-5 text-amber-400 flex-shrink-0 mt-0.5" />
                      <p className="text-amber-200 text-xs">
                        SOS alerts will notify emergency contacts and nearby Coast Guard stations.
                        False alarms may result in legal action. Use only in genuine emergencies.
                      </p>
                    </div>
                  </div>

                  {/* Action Buttons */}
                  <button
                    onClick={handleStartCountdown}
                    disabled={!location || isGettingLocation}
                    className="w-full px-4 py-4 rounded-xl bg-red-600 hover:bg-red-500 disabled:bg-slate-700 disabled:cursor-not-allowed text-white font-bold text-lg transition-colors flex items-center justify-center gap-2"
                  >
                    <Phone className="w-5 h-5" />
                    SEND SOS ALERT
                  </button>

                  <button
                    onClick={handleCloseModal}
                    className="w-full mt-3 px-4 py-3 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 font-medium transition-colors"
                  >
                    Cancel
                  </button>
                </>
              )}
            </div>
          </div>
        </div>
      )}
    </>
  );
};

export default SOSButton;
