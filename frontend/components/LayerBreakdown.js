'use client';

import { useState } from 'react';
import {
  MapPin,
  Cloud,
  FileText,
  Image,
  User,
  Target,
  CheckCircle,
  XCircle,
  MinusCircle,
  ChevronDown,
  ChevronRight,
  Info,
  Shield,
  Percent
} from 'lucide-react';

/**
 * Layer Breakdown Component
 * Displays detailed breakdown of each verification layer
 */
export default function LayerBreakdown({
  verificationResult,
  showWeights = true,
  expandable = true,
  initialExpanded = false
}) {
  const [expandedLayers, setExpandedLayers] = useState(
    initialExpanded ? { all: true } : {}
  );

  if (!verificationResult) return null;

  const { layer_results, weights_used, composite_score, decision } = verificationResult;

  if (!layer_results || layer_results.length === 0) return null;

  // Toggle layer expansion
  const toggleLayer = (layerName) => {
    if (!expandable) return;
    setExpandedLayers(prev => ({
      ...prev,
      [layerName]: !prev[layerName]
    }));
  };

  // Get layer icon component
  const getLayerIcon = (layerName) => {
    switch (layerName?.toLowerCase()) {
      case 'geofence':
        return MapPin;
      case 'weather':
        return Cloud;
      case 'text':
        return FileText;
      case 'image':
        return Image;
      case 'reporter':
        return User;
      default:
        return Target;
    }
  };

  // Get status icon and color
  const getStatusConfig = (status) => {
    switch (status?.toLowerCase()) {
      case 'pass':
      case 'passed':
        return {
          icon: CheckCircle,
          color: 'text-green-500',
          bg: 'bg-green-100',
          border: 'border-green-200',
          label: 'Passed'
        };
      case 'fail':
      case 'failed':
        return {
          icon: XCircle,
          color: 'text-red-500',
          bg: 'bg-red-100',
          border: 'border-red-200',
          label: 'Failed'
        };
      case 'skip':
      case 'skipped':
        return {
          icon: MinusCircle,
          color: 'text-gray-400',
          bg: 'bg-gray-100',
          border: 'border-gray-200',
          label: 'Skipped'
        };
      default:
        return {
          icon: Info,
          color: 'text-gray-500',
          bg: 'bg-gray-100',
          border: 'border-gray-200',
          label: status || 'Unknown'
        };
    }
  };

  // Get layer display info
  const getLayerInfo = (layerName) => {
    switch (layerName?.toLowerCase()) {
      case 'geofence':
        return {
          title: 'Geofencing',
          description: 'Validates location is within Indian coastal zone',
          emoji: '📍',
          defaultWeight: 20
        };
      case 'weather':
        return {
          title: 'Weather Validation',
          description: 'Cross-references with real-time environmental data',
          emoji: '🌤️',
          defaultWeight: 25
        };
      case 'text':
        return {
          title: 'Text Analysis',
          description: 'Analyzes description using AI and VectorDB',
          emoji: '📝',
          defaultWeight: 25
        };
      case 'image':
        return {
          title: 'Image Classification',
          description: 'Validates images using CNN-based vision AI',
          emoji: '🖼️',
          defaultWeight: 20
        };
      case 'reporter':
        return {
          title: 'Reporter Credibility',
          description: 'Evaluates reporter historical accuracy',
          emoji: '👤',
          defaultWeight: 10
        };
      default:
        return {
          title: layerName,
          description: 'Verification layer',
          emoji: '🎯',
          defaultWeight: 0
        };
    }
  };

  // Calculate score display
  const getScoreDisplay = (score) => {
    const pct = Math.round((score || 0) * 100);
    return pct;
  };

  // Get score bar color
  const getScoreBarColor = (score) => {
    const pct = score * 100;
    if (pct >= 70) return 'bg-green-500';
    if (pct >= 40) return 'bg-yellow-500';
    return 'bg-red-500';
  };

  return (
    <div className="bg-white rounded-xl shadow-md border border-gray-200 overflow-hidden">
      {/* Header with composite score */}
      <div className="p-4 bg-gradient-to-r from-sky-500 to-blue-600 text-white">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-12 h-12 rounded-xl bg-white/20 flex items-center justify-center">
              <Shield className="w-7 h-7" />
            </div>
            <div>
              <h3 className="text-lg font-bold">Verification Breakdown</h3>
              <p className="text-sm opacity-90">6-Layer Pipeline Analysis</p>
            </div>
          </div>
          <div className="text-right">
            <p className="text-3xl font-bold">{Math.round(composite_score || 0)}%</p>
            <p className="text-xs opacity-75 uppercase tracking-wide">
              {decision?.replace(/_/g, ' ')}
            </p>
          </div>
        </div>
      </div>

      {/* Layers */}
      <div className="divide-y divide-gray-100">
        {layer_results.map((layer, index) => {
          const LayerIcon = getLayerIcon(layer.layer_name);
          const statusConfig = getStatusConfig(layer.status);
          const StatusIcon = statusConfig.icon;
          const layerInfo = getLayerInfo(layer.layer_name);
          const isExpanded = expandedLayers[layer.layer_name] || expandedLayers.all;
          const weight = weights_used?.[layer.layer_name] || layer.weight || layerInfo.defaultWeight / 100;
          const scoreDisplay = getScoreDisplay(layer.score);

          return (
            <div key={index} className="overflow-hidden">
              {/* Layer Header */}
              <div
                className={`p-4 flex items-center gap-4 ${expandable ? 'cursor-pointer hover:bg-gray-50' : ''} transition-colors`}
                onClick={() => toggleLayer(layer.layer_name)}
              >
                {/* Layer Icon */}
                <div className={`w-10 h-10 rounded-lg ${statusConfig.bg} flex items-center justify-center flex-shrink-0`}>
                  <span className="text-xl">{layerInfo.emoji}</span>
                </div>

                {/* Layer Info */}
                <div className="flex-grow min-w-0">
                  <div className="flex items-center gap-2">
                    <h4 className="font-semibold text-gray-900">{layerInfo.title}</h4>
                    <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium ${statusConfig.bg} ${statusConfig.color}`}>
                      <StatusIcon className="w-3 h-3" />
                      {statusConfig.label}
                    </span>
                  </div>
                  {!isExpanded && (
                    <p className="text-sm text-gray-500 truncate">{layer.reasoning}</p>
                  )}
                </div>

                {/* Score */}
                <div className="flex items-center gap-4 flex-shrink-0">
                  {showWeights && (
                    <div className="text-right hidden sm:block">
                      <p className="text-xs text-gray-400">Weight</p>
                      <p className="text-sm font-medium text-gray-600">
                        {Math.round(weight * 100)}%
                      </p>
                    </div>
                  )}
                  <div className="text-right">
                    <p className="text-xs text-gray-400">Score</p>
                    <p className={`text-lg font-bold ${layer.status === 'skipped' ? 'text-gray-400' : statusConfig.color}`}>
                      {layer.status === 'skipped' ? 'N/A' : `${scoreDisplay}%`}
                    </p>
                  </div>
                  {expandable && (
                    <div className="text-gray-400">
                      {isExpanded ? (
                        <ChevronDown className="w-5 h-5" />
                      ) : (
                        <ChevronRight className="w-5 h-5" />
                      )}
                    </div>
                  )}
                </div>
              </div>

              {/* Expanded Details */}
              {isExpanded && (
                <div className={`px-4 pb-4 pt-0 ${statusConfig.bg} bg-opacity-30`}>
                  <div className="ml-14 space-y-3">
                    {/* Description */}
                    <p className="text-sm text-gray-600">{layerInfo.description}</p>

                    {/* Score bar */}
                    {layer.status !== 'skipped' && (
                      <div className="space-y-1">
                        <div className="flex items-center justify-between text-xs">
                          <span className="text-gray-500">Layer Score</span>
                          <span className="font-medium">{scoreDisplay}%</span>
                        </div>
                        <div className="w-full bg-gray-200 rounded-full h-2 overflow-hidden">
                          <div
                            className={`h-full rounded-full transition-all duration-500 ${getScoreBarColor(layer.score)}`}
                            style={{ width: `${Math.min(100, scoreDisplay)}%` }}
                          />
                        </div>
                      </div>
                    )}

                    {/* Confidence */}
                    {layer.confidence !== undefined && layer.status !== 'skipped' && (
                      <div className="flex items-center gap-2 text-xs text-gray-500">
                        <Percent className="w-3 h-3" />
                        <span>Confidence: {Math.round(layer.confidence * 100)}%</span>
                      </div>
                    )}

                    {/* Reasoning */}
                    {layer.reasoning && (
                      <div className="flex items-start gap-2 p-2 bg-white rounded-lg border border-gray-200">
                        <Info className="w-4 h-4 text-gray-400 flex-shrink-0 mt-0.5" />
                        <p className="text-sm text-gray-700">{layer.reasoning}</p>
                      </div>
                    )}

                    {/* Layer-specific metadata */}
                    {layer.data && (
                      <LayerMetadata layerName={layer.layer_name} data={layer.data} />
                    )}
                  </div>
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* Footer with thresholds */}
      <div className="p-3 bg-gray-50 border-t border-gray-200">
        <div className="flex items-center justify-center gap-6 text-xs text-gray-500">
          <div className="flex items-center gap-1">
            <span className="w-2 h-2 rounded-full bg-red-500"></span>
            <span>&lt;40% Reject</span>
          </div>
          <div className="flex items-center gap-1">
            <span className="w-2 h-2 rounded-full bg-yellow-500"></span>
            <span>40-75% Review</span>
          </div>
          <div className="flex items-center gap-1">
            <span className="w-2 h-2 rounded-full bg-green-500"></span>
            <span>&ge;75% Approve</span>
          </div>
        </div>
      </div>
    </div>
  );
}

/**
 * Layer-specific metadata display
 */
function LayerMetadata({ layerName, data }) {
  if (!data) return null;

  const renderMetadata = () => {
    switch (layerName?.toLowerCase()) {
      case 'geofence':
        return (
          <div className="grid grid-cols-2 gap-2 text-xs">
            {data.distance_to_coast_km !== undefined && (
              <div className="bg-white rounded p-2 border border-gray-200">
                <p className="text-gray-500">Distance to Coast</p>
                <p className="font-medium">{data.distance_to_coast_km?.toFixed(2)} km</p>
              </div>
            )}
            {data.nearest_coastline_point && (
              <div className="bg-white rounded p-2 border border-gray-200">
                <p className="text-gray-500">Nearest Point</p>
                <p className="font-medium truncate">{data.nearest_coastline_point}</p>
              </div>
            )}
            {data.is_inland !== undefined && (
              <div className="bg-white rounded p-2 border border-gray-200">
                <p className="text-gray-500">Location Type</p>
                <p className="font-medium">{data.is_inland ? 'Inland' : 'Offshore'}</p>
              </div>
            )}
          </div>
        );

      case 'weather':
        return (
          <div className="grid grid-cols-2 gap-2 text-xs">
            {data.threat_level && (
              <div className="bg-white rounded p-2 border border-gray-200">
                <p className="text-gray-500">Threat Level</p>
                <p className="font-medium capitalize">{data.threat_level}</p>
              </div>
            )}
            {data.matching_indicators?.length > 0 && (
              <div className="bg-white rounded p-2 border border-gray-200 col-span-2">
                <p className="text-gray-500">Matching Indicators</p>
                <p className="font-medium">{data.matching_indicators.join(', ')}</p>
              </div>
            )}
          </div>
        );

      case 'text':
        return (
          <div className="grid grid-cols-2 gap-2 text-xs">
            {data.predicted_hazard_type && (
              <div className="bg-white rounded p-2 border border-gray-200">
                <p className="text-gray-500">Predicted Type</p>
                <p className="font-medium capitalize">{data.predicted_hazard_type.replace(/_/g, ' ')}</p>
              </div>
            )}
            {data.similarity_score !== undefined && (
              <div className="bg-white rounded p-2 border border-gray-200">
                <p className="text-gray-500">Similarity</p>
                <p className="font-medium">{Math.round(data.similarity_score * 100)}%</p>
              </div>
            )}
            {data.panic_level !== undefined && (
              <div className="bg-white rounded p-2 border border-gray-200">
                <p className="text-gray-500">Panic Level</p>
                <p className="font-medium">{Math.round(data.panic_level * 100)}%</p>
              </div>
            )}
            {data.is_spam !== undefined && (
              <div className="bg-white rounded p-2 border border-gray-200">
                <p className="text-gray-500">Spam Detection</p>
                <p className={`font-medium ${data.is_spam ? 'text-red-600' : 'text-green-600'}`}>
                  {data.is_spam ? 'Spam Detected' : 'Clean'}
                </p>
              </div>
            )}
          </div>
        );

      case 'image':
        return (
          <div className="grid grid-cols-2 gap-2 text-xs">
            {data.predicted_class && (
              <div className="bg-white rounded p-2 border border-gray-200">
                <p className="text-gray-500">Predicted Class</p>
                <p className="font-medium capitalize">{data.predicted_class.replace(/_/g, ' ')}</p>
              </div>
            )}
            {data.prediction_confidence !== undefined && (
              <div className="bg-white rounded p-2 border border-gray-200">
                <p className="text-gray-500">Confidence</p>
                <p className="font-medium">{Math.round(data.prediction_confidence * 100)}%</p>
              </div>
            )}
            {data.is_match !== undefined && (
              <div className="bg-white rounded p-2 border border-gray-200">
                <p className="text-gray-500">Matches Report</p>
                <p className={`font-medium ${data.is_match ? 'text-green-600' : 'text-red-600'}`}>
                  {data.is_match ? 'Yes' : 'No'}
                </p>
              </div>
            )}
          </div>
        );

      case 'reporter':
        return (
          <div className="grid grid-cols-2 gap-2 text-xs">
            {data.total_reports !== undefined && (
              <div className="bg-white rounded p-2 border border-gray-200">
                <p className="text-gray-500">Total Reports</p>
                <p className="font-medium">{data.total_reports}</p>
              </div>
            )}
            {data.verified_reports !== undefined && (
              <div className="bg-white rounded p-2 border border-gray-200">
                <p className="text-gray-500">Verified Reports</p>
                <p className="font-medium">{data.verified_reports}</p>
              </div>
            )}
            {data.historical_accuracy !== undefined && (
              <div className="bg-white rounded p-2 border border-gray-200">
                <p className="text-gray-500">Historical Accuracy</p>
                <p className="font-medium">{Math.round(data.historical_accuracy * 100)}%</p>
              </div>
            )}
            {data.credibility_score !== undefined && (
              <div className="bg-white rounded p-2 border border-gray-200">
                <p className="text-gray-500">Credibility Score</p>
                <p className="font-medium">{data.credibility_score}/100</p>
              </div>
            )}
          </div>
        );

      default:
        return null;
    }
  };

  const metadata = renderMetadata();
  if (!metadata) return null;

  return (
    <div className="mt-2">
      {metadata}
    </div>
  );
}

/**
 * Compact layer summary for inline display
 */
export function LayerSummary({ layerResults }) {
  if (!layerResults || layerResults.length === 0) return null;

  const getStatusEmoji = (status) => {
    switch (status?.toLowerCase()) {
      case 'pass':
      case 'passed':
        return '✅';
      case 'fail':
      case 'failed':
        return '❌';
      case 'skip':
      case 'skipped':
        return '⏭️';
      default:
        return '❓';
    }
  };

  return (
    <div className="flex items-center gap-1">
      {layerResults.map((layer, index) => (
        <span
          key={index}
          className="text-sm"
          title={`${layer.layer_name}: ${layer.status} (${Math.round((layer.score || 0) * 100)}%)`}
        >
          {getStatusEmoji(layer.status)}
        </span>
      ))}
    </div>
  );
}
