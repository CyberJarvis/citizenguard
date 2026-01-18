'use client';

import { useState, useCallback } from 'react';
import { createExport, getExportStatus, downloadUnifiedExport } from '@/lib/api';
import toast from 'react-hot-toast';

/**
 * Custom hook for handling data exports
 * Provides export creation, status polling, and file download functionality
 */
export default function useExport() {
  const [isExporting, setIsExporting] = useState(false);
  const [progress, setProgress] = useState(0);
  const [currentJobId, setCurrentJobId] = useState(null);
  const [error, setError] = useState(null);

  /**
   * Poll for export job status until complete or failed
   */
  const pollStatus = useCallback(async (jobId) => {
    const maxAttempts = 60; // 2 minutes max
    let attempts = 0;

    while (attempts < maxAttempts) {
      try {
        const status = await getExportStatus(jobId);
        setProgress(status.progress || 0);

        if (status.status === 'completed') {
          return status;
        } else if (status.status === 'failed') {
          throw new Error(status.error_message || 'Export failed');
        }

        // Wait 2 seconds before next poll
        await new Promise(resolve => setTimeout(resolve, 2000));
        attempts++;
      } catch (err) {
        throw err;
      }
    }

    throw new Error('Export timed out');
  }, []);

  /**
   * Create and process an export
   * @param {Object} config - Export configuration
   * @param {string} config.dataType - Type of data to export (reports, tickets, alerts, users, audit_logs, smi)
   * @param {string} config.format - Export format (csv, excel, pdf)
   * @param {Object} config.filters - Current page filters
   * @param {Object} config.dateRange - Date range config { start, end } or { relative: '7days' }
   * @param {string[]} config.columns - Columns to include (optional)
   * @returns {Promise<boolean>} - Success status
   */
  const exportData = useCallback(async (config) => {
    setIsExporting(true);
    setProgress(0);
    setError(null);

    try {
      // Create export job
      const response = await createExport({
        data_type: config.dataType,
        export_format: config.format,
        filters: config.filters || {},
        date_range: config.dateRange || { relative: '30days' },
        columns: config.columns || null,
        format_settings: config.formatSettings || {}
      });

      if (!response.success) {
        throw new Error(response.error || 'Failed to create export');
      }

      const jobId = response.job_id;
      setCurrentJobId(jobId);

      // Poll for completion
      const finalStatus = await pollStatus(jobId);

      // Download the file
      await downloadUnifiedExport(jobId, finalStatus.file_name);

      toast.success(`Export downloaded: ${finalStatus.file_name}`);
      setIsExporting(false);
      setProgress(100);
      return true;

    } catch (err) {
      const errorMsg = err.response?.data?.detail || err.message || 'Export failed';
      setError(errorMsg);
      toast.error(errorMsg);
      setIsExporting(false);
      return false;
    }
  }, [pollStatus]);

  /**
   * Quick export with default settings
   * Uses 'all' for date range to export all available data
   */
  const quickExport = useCallback(async (dataType, format, currentFilters = {}) => {
    return exportData({
      dataType,
      format,
      filters: currentFilters,
      dateRange: { relative: 'all' }
    });
  }, [exportData]);

  /**
   * Cancel current export (if supported)
   */
  const cancelExport = useCallback(() => {
    setIsExporting(false);
    setProgress(0);
    setCurrentJobId(null);
    setError(null);
  }, []);

  return {
    exportData,
    quickExport,
    cancelExport,
    isExporting,
    progress,
    currentJobId,
    error
  };
}
