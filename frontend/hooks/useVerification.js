'use client';

import { useState, useCallback, useEffect } from 'react';
import {
  getVerificationQueue,
  getVerificationDetails,
  makeVerificationDecision,
  rerunVerification,
  getVerificationStats,
  getVerificationThresholds,
  getVerificationHealth
} from '@/lib/api';

/**
 * Hook for managing verification queue and actions
 */
export function useVerificationQueue(options = {}) {
  const { limit = 50, offset = 0, autoRefresh = false, refreshInterval = 30000 } = options;

  const [queue, setQueue] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [pagination, setPagination] = useState({ total: 0, offset: 0, limit });

  const fetchQueue = useCallback(async (customOffset = offset) => {
    try {
      setLoading(true);
      setError(null);
      const data = await getVerificationQueue({ limit, offset: customOffset });
      setQueue(data.items || data);
      setPagination({
        total: data.total || (data.items?.length || data.length),
        offset: customOffset,
        limit
      });
    } catch (err) {
      console.error('Error fetching verification queue:', err);
      setError(err.message || 'Failed to load verification queue');
    } finally {
      setLoading(false);
    }
  }, [limit, offset]);

  const refresh = useCallback(() => {
    fetchQueue(pagination.offset);
  }, [fetchQueue, pagination.offset]);

  const nextPage = useCallback(() => {
    const newOffset = pagination.offset + limit;
    if (newOffset < pagination.total) {
      fetchQueue(newOffset);
    }
  }, [fetchQueue, pagination, limit]);

  const prevPage = useCallback(() => {
    const newOffset = Math.max(0, pagination.offset - limit);
    fetchQueue(newOffset);
  }, [fetchQueue, pagination.offset, limit]);

  useEffect(() => {
    fetchQueue();
  }, [fetchQueue]);

  useEffect(() => {
    if (autoRefresh) {
      const interval = setInterval(refresh, refreshInterval);
      return () => clearInterval(interval);
    }
  }, [autoRefresh, refreshInterval, refresh]);

  return {
    queue,
    loading,
    error,
    pagination,
    refresh,
    nextPage,
    prevPage,
    hasNextPage: pagination.offset + limit < pagination.total,
    hasPrevPage: pagination.offset > 0
  };
}

/**
 * Hook for managing a single report's verification details
 */
export function useVerificationDetails(reportId) {
  const [details, setDetails] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchDetails = useCallback(async () => {
    if (!reportId) return;

    try {
      setLoading(true);
      setError(null);
      const data = await getVerificationDetails(reportId);
      setDetails(data);
    } catch (err) {
      console.error('Error fetching verification details:', err);
      setError(err.message || 'Failed to load verification details');
    } finally {
      setLoading(false);
    }
  }, [reportId]);

  useEffect(() => {
    fetchDetails();
  }, [fetchDetails]);

  return {
    details,
    loading,
    error,
    refresh: fetchDetails
  };
}

/**
 * Hook for verification actions (approve, reject, rerun)
 */
export function useVerificationActions() {
  const [processing, setProcessing] = useState(false);
  const [error, setError] = useState(null);
  const [lastResult, setLastResult] = useState(null);

  const approve = useCallback(async (reportId, reason, credibilityImpact = 5) => {
    try {
      setProcessing(true);
      setError(null);
      const result = await makeVerificationDecision(reportId, {
        decision: 'auto_approved',
        reason: reason || 'Approved by analyst',
        credibility_impact: credibilityImpact
      });
      setLastResult(result);
      return result;
    } catch (err) {
      console.error('Error approving report:', err);
      setError(err.message || 'Failed to approve report');
      throw err;
    } finally {
      setProcessing(false);
    }
  }, []);

  const reject = useCallback(async (reportId, reason, credibilityImpact = -5) => {
    try {
      setProcessing(true);
      setError(null);
      const result = await makeVerificationDecision(reportId, {
        decision: 'rejected',
        reason: reason || 'Rejected by analyst',
        credibility_impact: credibilityImpact
      });
      setLastResult(result);
      return result;
    } catch (err) {
      console.error('Error rejecting report:', err);
      setError(err.message || 'Failed to reject report');
      throw err;
    } finally {
      setProcessing(false);
    }
  }, []);

  const rerun = useCallback(async (reportId) => {
    try {
      setProcessing(true);
      setError(null);
      const result = await rerunVerification(reportId);
      setLastResult(result);
      return result;
    } catch (err) {
      console.error('Error re-running verification:', err);
      setError(err.message || 'Failed to re-run verification');
      throw err;
    } finally {
      setProcessing(false);
    }
  }, []);

  const clearError = useCallback(() => {
    setError(null);
  }, []);

  return {
    processing,
    error,
    lastResult,
    approve,
    reject,
    rerun,
    clearError
  };
}

/**
 * Hook for verification statistics
 */
export function useVerificationStats(days = 7) {
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchStats = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await getVerificationStats(days);
      setStats(data);
    } catch (err) {
      console.error('Error fetching verification stats:', err);
      setError(err.message || 'Failed to load verification stats');
    } finally {
      setLoading(false);
    }
  }, [days]);

  useEffect(() => {
    fetchStats();
  }, [fetchStats]);

  return {
    stats,
    loading,
    error,
    refresh: fetchStats
  };
}

/**
 * Hook for verification thresholds
 * Uses health endpoint which is public and includes thresholds
 */
export function useVerificationThresholds() {
  const [thresholds, setThresholds] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchThresholds = async () => {
      try {
        setLoading(true);
        // Use health endpoint which includes thresholds and is public
        const data = await getVerificationHealth();
        setThresholds(data.thresholds || { auto_approve: 75, manual_review: 40 });
      } catch (err) {
        console.error('Error fetching thresholds:', err);
        // Use default thresholds on error
        setThresholds({ auto_approve: 75, manual_review: 40 });
        setError(err.message || 'Failed to load thresholds');
      } finally {
        setLoading(false);
      }
    };

    fetchThresholds();
  }, []);

  return { thresholds, loading, error };
}

/**
 * Hook for verification health status
 */
export function useVerificationHealth() {
  const [health, setHealth] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchHealth = async () => {
      try {
        setLoading(true);
        const data = await getVerificationHealth();
        setHealth(data);
      } catch (err) {
        console.error('Error fetching verification health:', err);
        setError(err.message || 'Failed to load health status');
      } finally {
        setLoading(false);
      }
    };

    fetchHealth();
  }, []);

  return { health, loading, error };
}

/**
 * Combined hook for full verification management
 * Provides queue, actions, and stats in one hook
 */
export default function useVerification(options = {}) {
  const queue = useVerificationQueue(options);
  const actions = useVerificationActions();
  const stats = useVerificationStats(options.statsDays || 7);
  const thresholds = useVerificationThresholds();

  // Refresh queue after an action
  const handleApprove = useCallback(async (reportId, reason, credibilityImpact) => {
    const result = await actions.approve(reportId, reason, credibilityImpact);
    queue.refresh();
    stats.refresh();
    return result;
  }, [actions, queue, stats]);

  const handleReject = useCallback(async (reportId, reason, credibilityImpact) => {
    const result = await actions.reject(reportId, reason, credibilityImpact);
    queue.refresh();
    stats.refresh();
    return result;
  }, [actions, queue, stats]);

  const handleRerun = useCallback(async (reportId) => {
    const result = await actions.rerun(reportId);
    queue.refresh();
    return result;
  }, [actions, queue]);

  return {
    // Queue
    queue: queue.queue,
    queueLoading: queue.loading,
    queueError: queue.error,
    queuePagination: queue.pagination,
    refreshQueue: queue.refresh,
    nextPage: queue.nextPage,
    prevPage: queue.prevPage,
    hasNextPage: queue.hasNextPage,
    hasPrevPage: queue.hasPrevPage,

    // Actions
    processing: actions.processing,
    actionError: actions.error,
    lastResult: actions.lastResult,
    approve: handleApprove,
    reject: handleReject,
    rerun: handleRerun,
    clearActionError: actions.clearError,

    // Stats
    stats: stats.stats,
    statsLoading: stats.loading,
    statsError: stats.error,
    refreshStats: stats.refresh,

    // Thresholds
    thresholds: thresholds.thresholds,
    thresholdsLoading: thresholds.loading
  };
}
