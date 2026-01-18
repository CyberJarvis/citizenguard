'use client';

import { useState, useEffect } from 'react';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from '@/components/ui/dialog';
import {
  Download,
  FileText,
  FileSpreadsheet,
  File,
  Loader2,
  Calendar,
  CheckSquare,
  Square,
  AlertCircle
} from 'lucide-react';
import useExport from '@/hooks/useExport';

/**
 * Date range presets
 */
const DATE_PRESETS = [
  { key: '7days', label: 'Last 7 Days' },
  { key: '30days', label: 'Last 30 Days' },
  { key: '90days', label: 'Last 90 Days' },
  { key: 'year', label: 'Last Year' },
  { key: 'all', label: 'All Time' },
  { key: 'custom', label: 'Custom Range' },
];

/**
 * Export format options with icons
 */
const FORMAT_OPTIONS = [
  { key: 'csv', label: 'CSV', icon: FileText, color: 'text-green-600', bg: 'bg-green-50', border: 'border-green-200' },
  { key: 'excel', label: 'Excel', icon: FileSpreadsheet, color: 'text-emerald-600', bg: 'bg-emerald-50', border: 'border-emerald-200' },
  { key: 'pdf', label: 'PDF', icon: File, color: 'text-red-600', bg: 'bg-red-50', border: 'border-red-200' },
];

/**
 * Advanced Export Options Modal
 */
export default function ExportOptionsModal({
  isOpen,
  onClose,
  dataType,
  currentFilters = {},
  availableColumns = []
}) {
  const { exportData, isExporting, progress } = useExport();

  // Form state
  const [selectedFormat, setSelectedFormat] = useState('csv');
  const [datePreset, setDatePreset] = useState('30days');
  const [customStartDate, setCustomStartDate] = useState('');
  const [customEndDate, setCustomEndDate] = useState('');
  const [selectedColumns, setSelectedColumns] = useState([]);

  // Initialize selected columns with defaults
  useEffect(() => {
    if (availableColumns.length > 0 && selectedColumns.length === 0) {
      const defaultCols = availableColumns
        .filter(col => col.default)
        .map(col => col.key);
      setSelectedColumns(defaultCols);
    }
  }, [availableColumns]);

  // Reset form when modal opens
  useEffect(() => {
    if (isOpen) {
      setSelectedFormat('csv');
      setDatePreset('30days');
      setCustomStartDate('');
      setCustomEndDate('');
      const defaultCols = availableColumns
        .filter(col => col.default)
        .map(col => col.key);
      setSelectedColumns(defaultCols);
    }
  }, [isOpen, availableColumns]);

  // Handle column toggle
  const toggleColumn = (columnKey) => {
    setSelectedColumns(prev =>
      prev.includes(columnKey)
        ? prev.filter(k => k !== columnKey)
        : [...prev, columnKey]
    );
  };

  // Select/deselect all columns
  const toggleAllColumns = () => {
    if (selectedColumns.length === availableColumns.length) {
      setSelectedColumns([]);
    } else {
      setSelectedColumns(availableColumns.map(col => col.key));
    }
  };

  // Build date range config
  const getDateRange = () => {
    if (datePreset === 'custom') {
      return {
        start: customStartDate || null,
        end: customEndDate || null
      };
    }
    if (datePreset === 'all') {
      return {};
    }
    return { relative: datePreset };
  };

  // Handle export
  const handleExport = async () => {
    if (selectedColumns.length === 0) {
      return;
    }

    const success = await exportData({
      dataType,
      format: selectedFormat,
      filters: currentFilters,
      dateRange: getDateRange(),
      columns: selectedColumns
    });

    if (success) {
      onClose();
    }
  };

  // Get data type label
  const getDataTypeLabel = () => {
    const labels = {
      reports: 'Hazard Reports',
      tickets: 'Support Tickets',
      alerts: 'Alerts',
      users: 'Users',
      audit_logs: 'Audit Logs',
      smi: 'Social Intelligence'
    };
    return labels[dataType] || 'Data';
  };

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="sm:max-w-xl bg-white">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2 text-gray-900">
            <Download className="w-5 h-5 text-[#0d4a6f]" />
            Export {getDataTypeLabel()}
          </DialogTitle>
          <DialogDescription className="text-gray-500">
            Configure your export settings below. Select format, date range, and columns to include.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-5 py-2">
          {/* Format Selection */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Export Format
            </label>
            <div className="grid grid-cols-3 gap-3">
              {FORMAT_OPTIONS.map((format) => {
                const Icon = format.icon;
                const isSelected = selectedFormat === format.key;
                return (
                  <button
                    key={format.key}
                    type="button"
                    onClick={() => setSelectedFormat(format.key)}
                    className={`
                      flex flex-col items-center justify-center p-3 rounded-xl border-2 transition-all
                      ${isSelected
                        ? `${format.bg} ${format.border} ${format.color}`
                        : 'bg-gray-50 border-gray-200 text-gray-500 hover:border-gray-300'
                      }
                    `}
                  >
                    <Icon className={`w-6 h-6 mb-1 ${isSelected ? format.color : ''}`} />
                    <span className="text-sm font-medium">{format.label}</span>
                  </button>
                );
              })}
            </div>
          </div>

          {/* Date Range */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              <Calendar className="w-4 h-4 inline mr-1.5" />
              Date Range
            </label>
            <div className="flex flex-wrap gap-2">
              {DATE_PRESETS.map((preset) => (
                <button
                  key={preset.key}
                  type="button"
                  onClick={() => setDatePreset(preset.key)}
                  className={`
                    px-3 py-1.5 text-sm font-medium rounded-lg transition-all
                    ${datePreset === preset.key
                      ? 'bg-[#0d4a6f] text-white'
                      : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                    }
                  `}
                >
                  {preset.label}
                </button>
              ))}
            </div>

            {/* Custom Date Inputs */}
            {datePreset === 'custom' && (
              <div className="mt-3 grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs text-gray-500 mb-1">Start Date</label>
                  <input
                    type="date"
                    value={customStartDate}
                    onChange={(e) => setCustomStartDate(e.target.value)}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-[#0d4a6f]/50 focus:border-[#0d4a6f]"
                  />
                </div>
                <div>
                  <label className="block text-xs text-gray-500 mb-1">End Date</label>
                  <input
                    type="date"
                    value={customEndDate}
                    onChange={(e) => setCustomEndDate(e.target.value)}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-[#0d4a6f]/50 focus:border-[#0d4a6f]"
                  />
                </div>
              </div>
            )}
          </div>

          {/* Column Selection */}
          <div>
            <div className="flex items-center justify-between mb-2">
              <label className="block text-sm font-medium text-gray-700">
                Columns to Include
              </label>
              <button
                type="button"
                onClick={toggleAllColumns}
                className="text-xs text-[#0d4a6f] hover:underline"
              >
                {selectedColumns.length === availableColumns.length ? 'Deselect All' : 'Select All'}
              </button>
            </div>
            <div className="max-h-40 overflow-y-auto border border-gray-200 rounded-lg p-2 bg-gray-50">
              <div className="grid grid-cols-2 gap-1">
                {availableColumns.map((column) => {
                  const isSelected = selectedColumns.includes(column.key);
                  return (
                    <button
                      key={column.key}
                      type="button"
                      onClick={() => toggleColumn(column.key)}
                      className={`
                        flex items-center gap-2 px-2 py-1.5 rounded-md text-left text-sm transition-colors
                        ${isSelected
                          ? 'bg-[#e8f4fc] text-[#0d4a6f]'
                          : 'hover:bg-gray-100 text-gray-600'
                        }
                      `}
                    >
                      {isSelected ? (
                        <CheckSquare className="w-4 h-4 text-[#0d4a6f]" />
                      ) : (
                        <Square className="w-4 h-4 text-gray-400" />
                      )}
                      <span className="truncate">{column.label}</span>
                    </button>
                  );
                })}
              </div>
            </div>
            {selectedColumns.length === 0 && (
              <p className="mt-1.5 text-xs text-red-500 flex items-center gap-1">
                <AlertCircle className="w-3 h-3" />
                Please select at least one column
              </p>
            )}
          </div>
        </div>

        <DialogFooter className="gap-2 sm:gap-2">
          <button
            type="button"
            onClick={onClose}
            disabled={isExporting}
            className="px-4 py-2 text-sm font-medium text-gray-700 bg-gray-100 hover:bg-gray-200 rounded-lg transition-colors disabled:opacity-50"
          >
            Cancel
          </button>
          <button
            type="button"
            onClick={handleExport}
            disabled={isExporting || selectedColumns.length === 0}
            className="px-4 py-2 text-sm font-medium text-white bg-[#0d4a6f] hover:bg-[#083a57] rounded-lg transition-colors disabled:opacity-50 flex items-center gap-2"
          >
            {isExporting ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                Exporting... {progress > 0 && `${progress}%`}
              </>
            ) : (
              <>
                <Download className="w-4 h-4" />
                Export {selectedFormat.toUpperCase()}
              </>
            )}
          </button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
