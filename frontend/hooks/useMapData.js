'use client';

import { useState, useEffect, useCallback, useRef } from 'react';
import {
  getMultiHazardHealth,
  getMultiHazardPublicLocations,
  getMultiHazardPublicAlerts,
  getMapData,
  getTimelineData,
} from '@/lib/api';

/**
 * Custom hook for fetching and managing map data
 * Provides real-time monitoring locations, alerts, and user reports with heatmap
 * Supports timeline filtering for historical and forecast views
 */
export function useMapData(options = {}) {
  const {
    refreshInterval = 60000, // 1 minute default
    hoursFilter = 24, // 24 hours default
    autoRefresh = true,
    timelineRange = null, // '6h', '24h', or '48h_future' - if set, uses timeline API
  } = options;

  const [data, setData] = useState({
    locations: [],
    alerts: [],
    reports: [],
    heatmapPoints: [],
    statistics: {
      totalLocations: 0,
      totalAlerts: 0,
      totalReports: 0,
      criticalAlerts: 0,
      warningAlerts: 0,
      watchAlerts: 0,
    },
    // Timeline/Forecast specific data
    forecastData: null,
    forecastCone: null,
    isForecastMode: false,
  });

  const [isLoading, setIsLoading] = useState(true);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [isConnected, setIsConnected] = useState(false);
  const [lastUpdate, setLastUpdate] = useState(null);
  const [error, setError] = useState(null);

  const refreshTimerRef = useRef(null);
  const mountedRef = useRef(true);

  // Calculate cutoff time for filter
  const getCutoffTime = useCallback(() => {
    return new Date(Date.now() - hoursFilter * 60 * 60 * 1000);
  }, [hoursFilter]);

  // Generate enhanced heatmap points from multiple sources
  const generateEnhancedHeatmapPoints = useCallback((mapDataPoints, alerts, locations) => {
    const points = [];

    // Add heatmap points from map-data API (real reports)
    if (mapDataPoints && mapDataPoints.length > 0) {
      mapDataPoints.forEach((point) => {
        if (Array.isArray(point) && point.length >= 2) {
          points.push([point[0], point[1], point[2] || 0.6]);
        }
      });
    }

    // Add alert-based heatmap points with higher intensity
    if (alerts && alerts.length > 0) {
      alerts.forEach((alert) => {
        const location = locations.find((l) => l.location_id === alert.location_id);
        if (location) {
          const lat = location.coordinates?.lat || location.lat;
          const lon = location.coordinates?.lon || location.lon;
          if (lat && lon) {
            // Higher weight for higher alert levels
            const weight = Math.min(1.0, (alert.alert_level || 1) / 4);
            points.push([lat, lon, weight]);
          }
        }
      });
    }

    // Add location-based baseline points (lower intensity for monitoring stations)
    if (locations && locations.length > 0) {
      locations.forEach((location) => {
        const lat = location.coordinates?.lat || location.lat;
        const lon = location.coordinates?.lon || location.lon;
        if (lat && lon) {
          // Base intensity based on risk profile and alert level
          let baseIntensity = 0.15;
          if (location.risk_profile === 'high') baseIntensity = 0.25;
          if (location.risk_profile === 'critical') baseIntensity = 0.35;

          // Add alert level bonus
          const alertBonus = ((location.alert_level || 1) - 1) * 0.15;
          const weight = Math.min(0.5, baseIntensity + alertBonus);

          points.push([lat, lon, weight]);
        }
      });
    }

    return points;
  }, []);

  // Calculate statistics
  const calculateStatistics = useCallback((locations, alerts, reports, mapStats) => {
    return {
      totalLocations: locations.length,
      totalAlerts: alerts.length,
      totalReports: mapStats?.total_reports || reports.length,
      criticalAlerts: (mapStats?.critical_count || 0) + alerts.filter((a) => a.alert_level >= 5).length,
      warningAlerts: (mapStats?.high_count || 0) + alerts.filter((a) => a.alert_level === 4).length,
      watchAlerts: alerts.filter((a) => a.alert_level === 3).length,
      mediumCount: mapStats?.medium_count || 0,
      lowCount: mapStats?.low_count || 0,
    };
  }, []);

  // Fetch all data
  const fetchData = useCallback(
    async (isManualRefresh = false) => {
      if (!mountedRef.current) return;

      try {
        if (isManualRefresh) {
          setIsRefreshing(true);
        }

        // Check health first
        const health = await getMultiHazardHealth().catch(() => ({ status: 'unknown' }));
        const connected = health.status === 'healthy' || health.status === 'degraded';
        setIsConnected(connected);

        // Fetch base data (locations and alerts)
        const [locationsData, alertsData] = await Promise.all([
          getMultiHazardPublicLocations().catch(() => ({ locations: [] })),
          getMultiHazardPublicAlerts({ limit: 100 }).catch(() => ({ alerts: [] })),
        ]);

        const locations = locationsData.locations || [];
        const alerts = alertsData.alerts || [];

        // Fetch either timeline data or regular map data based on mode
        let reports = [];
        let apiHeatmapPoints = [];
        let mapStats = {};
        let forecastData = null;
        let forecastCone = null;
        let isForecastMode = false;

        if (timelineRange) {
          // Timeline mode - use timeline API
          const timelineResponse = await getTimelineData({
            timeRange: timelineRange,
            includeForecast: true,
            includeHeatmap: true,
          }).catch(() => ({
            success: false,
            data: { reports: [], heatmap_points: [], statistics: {} },
          }));

          const timelineData = timelineResponse.data || {};
          reports = timelineData.reports || [];
          apiHeatmapPoints = timelineData.heatmap_points || [];
          mapStats = timelineData.statistics || {};
          forecastData = timelineData.forecast_data || null;
          forecastCone = timelineData.forecast_cone || null;
          isForecastMode = timelineData.is_future || false;
        } else {
          // Regular mode - use map-data API
          const mapDataResponse = await getMapData({
            hours: hoursFilter,
            includeHeatmap: true,
            includeClusters: true,
          }).catch(() => ({
            success: false,
            data: { reports: [], heatmap_points: [], statistics: {} },
          }));

          const mapData = mapDataResponse.data || {};
          reports = mapData.reports || [];
          apiHeatmapPoints = mapData.heatmap_points || [];
          mapStats = mapData.statistics || {};
        }

        if (!mountedRef.current) return;

        // Generate enhanced heatmap points from all sources
        const heatmapPoints = generateEnhancedHeatmapPoints(apiHeatmapPoints, alerts, locations);

        // Calculate statistics
        const statistics = calculateStatistics(locations, alerts, reports, mapStats);

        setData({
          locations,
          alerts,
          reports,
          heatmapPoints,
          statistics,
          forecastData,
          forecastCone,
          isForecastMode,
        });

        setLastUpdate(new Date());
        setError(null);
      } catch (err) {
        console.error('Error fetching map data:', err);
        setError(err.message || 'Failed to fetch data');
        setIsConnected(false);
      } finally {
        if (mountedRef.current) {
          setIsLoading(false);
          setIsRefreshing(false);
        }
      }
    },
    [hoursFilter, timelineRange, generateEnhancedHeatmapPoints, calculateStatistics]
  );

  // Manual refresh
  const refresh = useCallback(() => {
    fetchData(true);
  }, [fetchData]);

  // Initial load and auto-refresh setup
  useEffect(() => {
    mountedRef.current = true;

    // Initial fetch
    fetchData();

    // Setup auto-refresh
    if (autoRefresh && refreshInterval > 0) {
      refreshTimerRef.current = setInterval(() => {
        fetchData();
      }, refreshInterval);
    }

    return () => {
      mountedRef.current = false;
      if (refreshTimerRef.current) {
        clearInterval(refreshTimerRef.current);
      }
    };
  }, [fetchData, autoRefresh, refreshInterval]);

  // Get location by ID
  const getLocationById = useCallback(
    (locationId) => {
      return data.locations.find((l) => l.location_id === locationId);
    },
    [data.locations]
  );

  // Get alerts for a specific location
  const getAlertsForLocation = useCallback(
    (locationId) => {
      return data.alerts.filter((a) => a.location_id === locationId);
    },
    [data.alerts]
  );

  // Get reports near a coordinate
  const getReportsNearLocation = useCallback(
    (lat, lon, radiusKm = 50) => {
      return data.reports.filter((report) => {
        const reportLat = report.latitude;
        const reportLon = report.longitude;
        if (!reportLat || !reportLon) return false;

        // Simple distance calculation
        const R = 6371; // Earth's radius in km
        const dLat = ((reportLat - lat) * Math.PI) / 180;
        const dLon = ((reportLon - lon) * Math.PI) / 180;
        const a =
          Math.sin(dLat / 2) * Math.sin(dLat / 2) +
          Math.cos((lat * Math.PI) / 180) *
            Math.cos((reportLat * Math.PI) / 180) *
            Math.sin(dLon / 2) *
            Math.sin(dLon / 2);
        const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
        const distance = R * c;

        return distance <= radiusKm;
      });
    },
    [data.reports]
  );

  return {
    // Data
    locations: data.locations,
    alerts: data.alerts,
    reports: data.reports,
    heatmapPoints: data.heatmapPoints,
    statistics: data.statistics,

    // Timeline/Forecast data
    forecastData: data.forecastData,
    forecastCone: data.forecastCone,
    isForecastMode: data.isForecastMode,

    // State
    isLoading,
    isRefreshing,
    isConnected,
    lastUpdate,
    error,

    // Actions
    refresh,

    // Utilities
    getLocationById,
    getAlertsForLocation,
    getReportsNearLocation,
    getCutoffTime,
  };
}

export default useMapData;
