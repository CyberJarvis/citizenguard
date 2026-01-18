'use client';

import React, { useMemo } from 'react';
import dynamic from 'next/dynamic';
import { Marker, Popup } from 'react-leaflet';
import { MapPin, Clock, AlertTriangle, Eye } from 'lucide-react';

// Dynamic import for MarkerClusterGroup
const MarkerClusterGroup = dynamic(
  () => import('react-leaflet-cluster').then((mod) => mod.default),
  { ssr: false }
);

// Severity color mapping
const SEVERITY_CONFIG = {
  critical: {
    color: '#ef4444',
    gradient: 'linear-gradient(135deg, #ef4444 0%, #dc2626 100%)',
    bg: 'bg-red-500',
  },
  high: {
    color: '#f97316',
    gradient: 'linear-gradient(135deg, #f97316 0%, #ea580c 100%)',
    bg: 'bg-orange-500',
  },
  medium: {
    color: '#eab308',
    gradient: 'linear-gradient(135deg, #eab308 0%, #ca8a04 100%)',
    bg: 'bg-yellow-500',
  },
  low: {
    color: '#22c55e',
    gradient: 'linear-gradient(135deg, #22c55e 0%, #16a34a 100%)',
    bg: 'bg-emerald-500',
  },
};

// Create cluster icon
const createClusterCustomIcon = (cluster) => {
  if (typeof window === 'undefined') return null;
  const L = require('leaflet');
  const count = cluster.getChildCount();

  let size, className, color;
  if (count >= 50) {
    size = 60;
    className = 'cluster-xlarge';
    color = '#ef4444';
  } else if (count >= 20) {
    size = 52;
    className = 'cluster-large';
    color = '#f97316';
  } else if (count >= 10) {
    size = 44;
    className = 'cluster-medium';
    color = '#eab308';
  } else {
    size = 36;
    className = 'cluster-small';
    color = '#22c55e';
  }

  return L.divIcon({
    html: `<div class="cluster-marker ${className}">${count}</div>`,
    className: 'custom-cluster-marker',
    iconSize: [size, size],
    iconAnchor: [size / 2, size / 2],
  });
};

// Create report marker icon
const createReportIcon = (report) => {
  if (typeof window === 'undefined') return null;
  const L = require('leaflet');
  const severity = report.severity?.toLowerCase() || 'medium';
  const config = SEVERITY_CONFIG[severity] || SEVERITY_CONFIG.medium;

  const html = `
    <div style="
      width: 32px;
      height: 32px;
      background: ${config.gradient};
      border: 2px solid rgba(255,255,255,0.9);
      border-radius: 50%;
      display: flex;
      align-items: center;
      justify-content: center;
      box-shadow: 0 4px 12px rgba(0,0,0,0.3);
    ">
      <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"></path>
        <circle cx="12" cy="10" r="3"></circle>
      </svg>
    </div>
  `;

  return L.divIcon({
    html,
    className: 'custom-report-marker',
    iconSize: [32, 32],
    iconAnchor: [16, 32],
    popupAnchor: [0, -32],
  });
};

/**
 * ClusterLayer - Marker clustering for user reports
 * Groups nearby reports and shows count
 */
export function ClusterLayer({
  reports = [],
  onReportClick = () => {},
}) {
  // Memoize report markers
  const reportMarkers = useMemo(() => {
    return reports
      .filter((report) => {
        const lat = report.location?.latitude || report.latitude;
        const lon = report.location?.longitude || report.longitude;
        return lat && lon;
      })
      .map((report) => {
        const lat = report.location?.latitude || report.latitude;
        const lon = report.location?.longitude || report.longitude;
        const severity = report.severity?.toLowerCase() || 'medium';
        const config = SEVERITY_CONFIG[severity] || SEVERITY_CONFIG.medium;

        return {
          ...report,
          lat,
          lon,
          severityConfig: config,
        };
      });
  }, [reports]);

  // Format date
  const formatDate = (dateStr) => {
    if (!dateStr) return 'Unknown';
    const date = new Date(dateStr);
    const now = new Date();
    const diffHours = Math.floor((now - date) / (1000 * 60 * 60));

    if (diffHours < 1) return 'Just now';
    if (diffHours < 24) return `${diffHours}h ago`;
    return date.toLocaleDateString();
  };

  if (reportMarkers.length === 0) return null;

  return (
    <MarkerClusterGroup
      chunkedLoading
      iconCreateFunction={createClusterCustomIcon}
      maxClusterRadius={60}
      spiderfyOnMaxZoom
      showCoverageOnHover={false}
      zoomToBoundsOnClick
      disableClusteringAtZoom={15}
    >
      {reportMarkers.map((report) => (
        <Marker
          key={report.id || report._id}
          position={[report.lat, report.lon]}
          icon={createReportIcon(report)}
          eventHandlers={{
            click: () => onReportClick(report),
          }}
        >
          <Popup className="ocean-popup" maxWidth={320}>
            <div className="p-4">
              {/* Header */}
              <div className="flex items-start justify-between mb-3">
                <div className="flex items-center gap-2">
                  <MapPin className="w-4 h-4 text-cyan-400" />
                  <h3 className="font-bold text-white text-sm">
                    {report.hazard_type?.replace(/_/g, ' ') || 'Hazard Report'}
                  </h3>
                </div>
                <span
                  className="px-2 py-1 rounded-lg text-xs font-bold text-white capitalize"
                  style={{ background: report.severityConfig.gradient }}
                >
                  {report.severity || 'Medium'}
                </span>
              </div>

              {/* Description */}
              {report.description && (
                <p className="text-sm text-slate-300 mb-3 line-clamp-3">
                  {report.description}
                </p>
              )}

              {/* Meta Info */}
              <div className="flex items-center gap-4 text-xs text-slate-400">
                <div className="flex items-center gap-1">
                  <Clock className="w-3 h-3" />
                  <span>{formatDate(report.created_at || report.timestamp)}</span>
                </div>
                {report.verification_status && (
                  <div className="flex items-center gap-1">
                    {report.verification_status === 'verified' ? (
                      <>
                        <Eye className="w-3 h-3 text-emerald-400" />
                        <span className="text-emerald-400">Verified</span>
                      </>
                    ) : (
                      <>
                        <AlertTriangle className="w-3 h-3 text-yellow-400" />
                        <span className="text-yellow-400">Pending</span>
                      </>
                    )}
                  </div>
                )}
              </div>

              {/* Coordinates */}
              <div className="mt-3 pt-2 border-t border-slate-700/50 text-xs text-slate-500">
                {report.lat?.toFixed(4)}°N, {report.lon?.toFixed(4)}°E
              </div>
            </div>
          </Popup>
        </Marker>
      ))}
    </MarkerClusterGroup>
  );
}

export default ClusterLayer;
