'use client';

import { useState, useEffect } from 'react';
import {
  AlertTriangle,
  AlertCircle,
  Eye,
  CheckCircle,
  Shield,
  Waves,
  Wind,
  Droplets,
  Activity,
  ArrowDownRight,
  Info,
  ChevronDown,
  ChevronUp,
  Clock,
  RefreshCw
} from 'lucide-react';
import { getFullEnrichment, getThreatLevelColor, getThreatLevelInfo, getHazardTypeInfo } from '@/lib/api';

/**
 * Threat Classification Card Component
 * Displays threat levels and recommendations based on environmental analysis
 */
export default function ThreatClassificationCard({
  latitude,
  longitude,
  reportedHazardType = null,
  initialClassification = null,
  onClassificationLoaded = null,
  showRecommendations = true,
  compact = false
}) {
  const [classification, setClassification] = useState(initialClassification);
  const [environmentalData, setEnvironmentalData] = useState(null);
  const [loading, setLoading] = useState(!initialClassification);
  const [error, setError] = useState(null);
  const [expanded, setExpanded] = useState(!compact);
  const [processingTime, setProcessingTime] = useState(null);

  // Fetch classification data
  const fetchClassification = async () => {
    if (!latitude || !longitude) return;

    try {
      setLoading(true);
      setError(null);

      const response = await getFullEnrichment(latitude, longitude, reportedHazardType);

      if (response.success) {
        setClassification(response.hazard_classification);
        setEnvironmentalData(response.environmental_snapshot);
        setProcessingTime(response.processing_time_ms);
        if (onClassificationLoaded) {
          onClassificationLoaded(response);
        }
      } else {
        setError('Failed to analyze threat levels');
      }
    } catch (err) {
      console.error('Classification fetch error:', err);
      setError(err.message || 'Failed to analyze threat levels');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (!initialClassification && latitude && longitude) {
      fetchClassification();
    }
  }, [latitude, longitude, initialClassification]);

  // Get threat level configuration
  const getThreatConfig = (level) => {
    switch (level?.toLowerCase()) {
      case 'warning':
        return {
          icon: AlertTriangle,
          bg: 'bg-gradient-to-br from-red-500 to-red-600',
          text: 'text-white',
          border: 'border-red-500',
          lightBg: 'bg-red-50',
          lightText: 'text-red-800',
          pulse: true
        };
      case 'alert':
        return {
          icon: AlertCircle,
          bg: 'bg-gradient-to-br from-orange-500 to-orange-600',
          text: 'text-white',
          border: 'border-orange-500',
          lightBg: 'bg-orange-50',
          lightText: 'text-orange-800',
          pulse: false
        };
      case 'watch':
        return {
          icon: Eye,
          bg: 'bg-gradient-to-br from-yellow-500 to-yellow-600',
          text: 'text-white',
          border: 'border-yellow-500',
          lightBg: 'bg-yellow-50',
          lightText: 'text-yellow-800',
          pulse: false
        };
      case 'no_threat':
      default:
        return {
          icon: CheckCircle,
          bg: 'bg-gradient-to-br from-green-500 to-green-600',
          text: 'text-white',
          border: 'border-green-500',
          lightBg: 'bg-green-50',
          lightText: 'text-green-800',
          pulse: false
        };
    }
  };

  // Get hazard icon
  const getHazardIcon = (hazardType) => {
    switch (hazardType?.toLowerCase()) {
      case 'tsunami':
        return Waves;
      case 'cyclone':
        return Wind;
      case 'high_waves':
        return Waves;
      case 'coastal_flood':
        return Droplets;
      case 'rip_current':
        return ArrowDownRight;
      default:
        return Activity;
    }
  };

  if (loading) {
    return (
      <div className="bg-white rounded-2xl shadow-lg border border-gray-200 p-6">
        <div className="flex items-center justify-center py-8">
          <div className="flex flex-col items-center gap-3">
            <div className="relative">
              <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-sky-500"></div>
              <Shield className="absolute inset-0 m-auto w-6 h-6 text-sky-500" />
            </div>
            <p className="text-sm text-gray-500">Analyzing threat levels...</p>
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-white rounded-2xl shadow-lg border border-gray-200 p-6">
        <div className="text-center py-6">
          <AlertTriangle className="w-12 h-12 text-orange-500 mx-auto mb-3" />
          <p className="text-sm font-medium text-gray-900 mb-1">Analysis Failed</p>
          <p className="text-xs text-gray-500 mb-4">{error}</p>
          <button
            onClick={fetchClassification}
            className="px-4 py-2 text-sm font-medium text-sky-600 bg-sky-50 rounded-lg hover:bg-sky-100 transition-colors"
          >
            Retry Analysis
          </button>
        </div>
      </div>
    );
  }

  if (!classification) {
    return null;
  }

  const threatLevel = classification.threat_level || 'no_threat';
  const config = getThreatConfig(threatLevel);
  const ThreatIcon = config.icon;
  const threatInfo = getThreatLevelInfo(threatLevel);
  const HazardIcon = classification.hazard_type ? getHazardIcon(classification.hazard_type) : Shield;

  return (
    <div className="bg-white rounded-2xl shadow-lg border border-gray-200 overflow-hidden">
      {/* Main Threat Level Display */}
      <div
        className={`p-6 ${config.bg} ${config.text} ${config.pulse ? 'animate-pulse' : ''} cursor-pointer`}
        onClick={() => setExpanded(!expanded)}
      >
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <div className="w-14 h-14 rounded-2xl bg-white/20 flex items-center justify-center">
              <ThreatIcon className="w-8 h-8" />
            </div>
            <div>
              <p className="text-sm opacity-90 mb-1">Threat Assessment</p>
              <h3 className="text-2xl font-bold tracking-wide">
                {threatInfo.label}
              </h3>
              {classification.hazard_type && (
                <div className="flex items-center gap-1 mt-1 opacity-90">
                  <HazardIcon className="w-4 h-4" />
                  <span className="text-sm capitalize">
                    {classification.hazard_type.replace('_', ' ')}
                  </span>
                </div>
              )}
            </div>
          </div>
          <div className="flex flex-col items-end gap-2">
            <div className="flex items-center gap-2 text-sm opacity-90">
              <Shield className="w-4 h-4" />
              <span>{Math.round((classification.confidence || 0.5) * 100)}% Confidence</span>
            </div>
            {compact && (
              expanded ? <ChevronUp className="w-5 h-5 opacity-70" /> : <ChevronDown className="w-5 h-5 opacity-70" />
            )}
          </div>
        </div>
      </div>

      {/* Expanded Content */}
      {expanded && (
        <div className="p-4 space-y-4">
          {/* Individual Threat Levels */}
          <div className="grid grid-cols-2 sm:grid-cols-5 gap-2">
            <ThreatIndicator
              label="Tsunami"
              level={classification.tsunami_threat}
              icon={Waves}
            />
            <ThreatIndicator
              label="Cyclone"
              level={classification.cyclone_threat}
              icon={Wind}
            />
            <ThreatIndicator
              label="High Waves"
              level={classification.high_waves_threat}
              icon={Waves}
            />
            <ThreatIndicator
              label="Flood"
              level={classification.coastal_flood_threat}
              icon={Droplets}
            />
            <ThreatIndicator
              label="Rip Current"
              level={classification.rip_current_threat}
              icon={ArrowDownRight}
            />
          </div>

          {/* Reasoning */}
          {classification.reasoning && (
            <div className={`rounded-xl p-4 ${config.lightBg}`}>
              <h4 className={`text-sm font-bold ${config.lightText} mb-2 flex items-center gap-2`}>
                <Info className="w-4 h-4" />
                Analysis
              </h4>
              <p className="text-sm text-gray-700">{classification.reasoning}</p>
            </div>
          )}

          {/* Recommendations */}
          {showRecommendations && classification.recommendations && classification.recommendations.length > 0 && (
            <div className="bg-gray-50 rounded-xl p-4">
              <h4 className="text-sm font-bold text-gray-900 mb-3 flex items-center gap-2">
                <Shield className="w-4 h-4 text-sky-600" />
                Safety Recommendations
              </h4>
              <ul className="space-y-2">
                {classification.recommendations.map((rec, index) => (
                  <li key={index} className="flex items-start gap-2 text-sm text-gray-700">
                    <span className={`flex-shrink-0 w-5 h-5 rounded-full ${config.bg} ${config.text} text-xs flex items-center justify-center font-bold`}>
                      {index + 1}
                    </span>
                    <span>{rec}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Footer Info */}
          <div className="flex items-center justify-between text-xs text-gray-400 pt-2 border-t border-gray-100">
            <div className="flex items-center gap-1">
              <Clock className="w-3 h-3" />
              <span>
                {classification.classified_at
                  ? new Date(classification.classified_at).toLocaleString()
                  : 'Just now'}
              </span>
            </div>
            {processingTime && (
              <span>Processed in {processingTime.toFixed(0)}ms</span>
            )}
            <button
              onClick={(e) => {
                e.stopPropagation();
                fetchClassification();
              }}
              className="flex items-center gap-1 text-sky-500 hover:text-sky-600"
            >
              <RefreshCw className="w-3 h-3" />
              Refresh
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

// Individual threat indicator component
function ThreatIndicator({ label, level, icon: Icon }) {
  const getIndicatorColor = (level) => {
    switch (level?.toLowerCase()) {
      case 'warning':
        return { bg: 'bg-red-100', text: 'text-red-700', dot: 'bg-red-500' };
      case 'alert':
        return { bg: 'bg-orange-100', text: 'text-orange-700', dot: 'bg-orange-500' };
      case 'watch':
        return { bg: 'bg-yellow-100', text: 'text-yellow-700', dot: 'bg-yellow-500' };
      case 'no_threat':
      default:
        return { bg: 'bg-green-100', text: 'text-green-700', dot: 'bg-green-500' };
    }
  };

  const color = getIndicatorColor(level);

  return (
    <div className={`${color.bg} rounded-lg p-2 text-center`}>
      <Icon className={`w-4 h-4 ${color.text} mx-auto mb-1`} />
      <p className="text-xs font-medium text-gray-600">{label}</p>
      <div className="flex items-center justify-center gap-1 mt-1">
        <span className={`w-2 h-2 rounded-full ${color.dot}`}></span>
        <span className={`text-xs font-semibold ${color.text} uppercase`}>
          {level?.replace('_', ' ') || 'OK'}
        </span>
      </div>
    </div>
  );
}

/**
 * Compact Threat Badge Component
 * For inline display of threat level
 */
export function ThreatBadge({ level, showLabel = true, size = 'md' }) {
  const config = {
    warning: { bg: 'bg-red-500', text: 'text-white', icon: AlertTriangle },
    alert: { bg: 'bg-orange-500', text: 'text-white', icon: AlertCircle },
    watch: { bg: 'bg-yellow-500', text: 'text-white', icon: Eye },
    no_threat: { bg: 'bg-green-500', text: 'text-white', icon: CheckCircle }
  };

  const sizeClasses = {
    sm: 'px-2 py-0.5 text-xs',
    md: 'px-3 py-1 text-sm',
    lg: 'px-4 py-2 text-base'
  };

  const threatConfig = config[level?.toLowerCase()] || config.no_threat;
  const Icon = threatConfig.icon;

  return (
    <span className={`inline-flex items-center gap-1 ${threatConfig.bg} ${threatConfig.text} ${sizeClasses[size]} rounded-full font-semibold`}>
      <Icon className={size === 'sm' ? 'w-3 h-3' : size === 'lg' ? 'w-5 h-5' : 'w-4 h-4'} />
      {showLabel && (
        <span className="uppercase tracking-wide">
          {level?.replace('_', ' ') || 'Safe'}
        </span>
      )}
    </span>
  );
}
