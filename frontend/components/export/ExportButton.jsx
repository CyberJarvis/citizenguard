'use client';

import { useState, useRef, useEffect } from 'react';
import { Download, FileText, FileSpreadsheet, File, ChevronDown, Loader2, Settings2 } from 'lucide-react';
import useExport from '@/hooks/useExport';
import ExportOptionsModal from './ExportOptionsModal';

/**
 * Column definitions for each data type
 */
const DATA_TYPE_COLUMNS = {
  reports: [
    { key: 'report_id', label: 'Report ID', default: true },
    { key: 'hazard_type', label: 'Hazard Type', default: true },
    { key: 'category', label: 'Category', default: true },
    { key: 'severity', label: 'Severity', default: true },
    { key: 'verification_status', label: 'Status', default: true },
    { key: 'description', label: 'Description', default: false },
    { key: 'address', label: 'Address', default: true },
    { key: 'city', label: 'City', default: true },
    { key: 'state', label: 'State', default: true },
    { key: 'latitude', label: 'Latitude', default: false },
    { key: 'longitude', label: 'Longitude', default: false },
    { key: 'verification_score', label: 'AI Score', default: true },
    { key: 'created_at', label: 'Created At', default: true },
    { key: 'verified_at', label: 'Verified At', default: false },
  ],
  tickets: [
    { key: 'ticket_id', label: 'Ticket ID', default: true },
    { key: 'hazard_report_id', label: 'Report ID', default: true },
    { key: 'status', label: 'Status', default: true },
    { key: 'priority', label: 'Priority', default: true },
    { key: 'analyst_name', label: 'Assigned Analyst', default: true },
    { key: 'authority_name', label: 'Assigned Authority', default: true },
    { key: 'created_at', label: 'Created At', default: true },
    { key: 'updated_at', label: 'Updated At', default: true },
    { key: 'response_due', label: 'Response Due', default: false },
    { key: 'resolution_due', label: 'Resolution Due', default: false },
  ],
  alerts: [
    { key: 'alert_id', label: 'Alert ID', default: true },
    { key: 'title', label: 'Title', default: true },
    { key: 'alert_type', label: 'Type', default: true },
    { key: 'severity', label: 'Severity', default: true },
    { key: 'status', label: 'Status', default: true },
    { key: 'regions', label: 'Regions', default: true },
    { key: 'issued_at', label: 'Issued At', default: true },
    { key: 'expires_at', label: 'Expires At', default: true },
    { key: 'created_by', label: 'Created By', default: false },
  ],
  users: [
    { key: 'user_id', label: 'User ID', default: true },
    { key: 'name', label: 'Name', default: true },
    { key: 'email', label: 'Email', default: true },
    { key: 'phone', label: 'Phone', default: false },
    { key: 'role', label: 'Role', default: true },
    { key: 'is_active', label: 'Status', default: true },
    { key: 'credibility_score', label: 'Credibility Score', default: true },
    { key: 'created_at', label: 'Joined At', default: true },
    { key: 'last_login', label: 'Last Login', default: false },
  ],
  audit_logs: [
    { key: 'timestamp', label: 'Timestamp', default: true },
    { key: 'user_name', label: 'User', default: true },
    { key: 'user_email', label: 'Email', default: false },
    { key: 'action_type', label: 'Action', default: true },
    { key: 'resource', label: 'Resource', default: true },
    { key: 'details', label: 'Details', default: true },
    { key: 'ip_address', label: 'IP Address', default: false },
  ],
  smi: [
    { key: 'id', label: 'ID', default: true },
    { key: 'source', label: 'Source', default: true },
    { key: 'content', label: 'Content', default: true },
    { key: 'hazard_type', label: 'Hazard Type', default: true },
    { key: 'confidence', label: 'Confidence', default: true },
    { key: 'location', label: 'Location', default: true },
    { key: 'timestamp', label: 'Timestamp', default: true },
  ],
};

/**
 * Export format options
 */
const EXPORT_FORMATS = [
  { key: 'csv', label: 'CSV', icon: FileText, description: 'Comma-separated values' },
  { key: 'excel', label: 'Excel', icon: FileSpreadsheet, description: 'Microsoft Excel format' },
  { key: 'pdf', label: 'PDF', icon: File, description: 'PDF document' },
];

/**
 * Reusable Export Button with dropdown menu
 * @param {Object} props
 * @param {string} props.dataType - Type of data: 'reports', 'tickets', 'alerts', 'users', 'audit_logs', 'smi'
 * @param {Object} props.currentFilters - Current page filters to apply to export
 * @param {boolean} props.disabled - Disable the button
 * @param {string} props.className - Additional CSS classes
 * @param {string} props.size - Button size: 'sm', 'md', 'lg'
 */
/**
 * Clean filters by removing empty, null, undefined, and "all" values
 * These are UI placeholder values that shouldn't be sent to the API
 */
function cleanFilters(filters) {
  if (!filters || typeof filters !== 'object') return {};

  const cleaned = {};
  const excludeValues = ['all', 'All', '', null, undefined];

  for (const [key, value] of Object.entries(filters)) {
    // Skip internal/UI-only keys
    if (key.startsWith('_') || key === 'page' || key === 'limit' || key === 'sort') continue;

    // Skip empty/placeholder values
    if (excludeValues.includes(value)) continue;

    // Skip empty arrays
    if (Array.isArray(value) && value.length === 0) continue;

    // Include valid values
    cleaned[key] = value;
  }

  return cleaned;
}

export default function ExportButton({
  dataType = 'reports',
  currentFilters = {},
  disabled = false,
  className = '',
  size = 'md'
}) {
  const [isOpen, setIsOpen] = useState(false);
  const [showAdvancedModal, setShowAdvancedModal] = useState(false);
  const dropdownRef = useRef(null);
  const { quickExport, isExporting, progress } = useExport();

  // Get available columns for this data type
  const availableColumns = DATA_TYPE_COLUMNS[dataType] || DATA_TYPE_COLUMNS.reports;

  // Clean filters to remove UI-only values like "all"
  const cleanedFilters = cleanFilters(currentFilters);

  // Close dropdown on outside click
  useEffect(() => {
    const handleClickOutside = (event) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target)) {
        setIsOpen(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  // Handle quick export
  const handleQuickExport = async (format) => {
    setIsOpen(false);
    await quickExport(dataType, format, cleanedFilters);
  };

  // Handle advanced export
  const handleAdvancedExport = () => {
    setIsOpen(false);
    setShowAdvancedModal(true);
  };

  // Size classes
  const sizeClasses = {
    sm: 'px-2.5 py-1.5 text-xs gap-1',
    md: 'px-3 py-2 text-sm gap-1.5',
    lg: 'px-4 py-2.5 text-base gap-2'
  };

  const iconSizes = {
    sm: 'w-3.5 h-3.5',
    md: 'w-4 h-4',
    lg: 'w-5 h-5'
  };

  return (
    <>
      <div className={`relative inline-block ${className}`} ref={dropdownRef}>
        {/* Main Export Button */}
        <button
          type="button"
          onClick={() => setIsOpen(!isOpen)}
          disabled={disabled || isExporting}
          className={`
            inline-flex items-center justify-center font-medium rounded-lg
            bg-[#0d4a6f] hover:bg-[#083a57] text-white
            transition-all duration-200 ease-in-out
            disabled:opacity-50 disabled:cursor-not-allowed
            focus:outline-none focus:ring-2 focus:ring-[#0d4a6f]/50 focus:ring-offset-2
            ${sizeClasses[size]}
          `}
        >
          {isExporting ? (
            <>
              <Loader2 className={`${iconSizes[size]} animate-spin`} />
              <span>Exporting... {progress > 0 && `${progress}%`}</span>
            </>
          ) : (
            <>
              <Download className={iconSizes[size]} />
              <span>Export</span>
              <ChevronDown className={`${iconSizes[size]} ml-0.5 transition-transform ${isOpen ? 'rotate-180' : ''}`} />
            </>
          )}
        </button>

        {/* Dropdown Menu - using fixed positioning to avoid overflow issues */}
        {isOpen && !isExporting && (
          <div
            className="fixed w-56 bg-white rounded-xl shadow-xl border border-gray-200 py-2 animate-in fade-in slide-in-from-top-2 duration-200"
            style={{
              zIndex: 9999,
              top: dropdownRef.current ? dropdownRef.current.getBoundingClientRect().bottom + 8 : 0,
              right: dropdownRef.current ? window.innerWidth - dropdownRef.current.getBoundingClientRect().right : 0,
            }}
          >
            {/* Quick Export Options */}
            <div className="px-3 py-1.5">
              <p className="text-xs font-semibold text-gray-500 uppercase tracking-wider">Quick Export</p>
            </div>

            {EXPORT_FORMATS.map((format) => {
              const Icon = format.icon;
              return (
                <button
                  key={format.key}
                  onClick={() => handleQuickExport(format.key)}
                  className="w-full px-3 py-2 text-left hover:bg-gray-50 flex items-center gap-3 transition-colors"
                >
                  <Icon className="w-4 h-4 text-gray-500" />
                  <div>
                    <p className="text-sm font-medium text-gray-900">{format.label}</p>
                    <p className="text-xs text-gray-500">{format.description}</p>
                  </div>
                </button>
              );
            })}

            {/* Divider */}
            <div className="my-2 border-t border-gray-100" />

            {/* Advanced Export */}
            <button
              onClick={handleAdvancedExport}
              className="w-full px-3 py-2 text-left hover:bg-gray-50 flex items-center gap-3 transition-colors"
            >
              <Settings2 className="w-4 h-4 text-[#0d4a6f]" />
              <div>
                <p className="text-sm font-medium text-[#0d4a6f]">Advanced Export...</p>
                <p className="text-xs text-gray-500">Custom date range & columns</p>
              </div>
            </button>
          </div>
        )}
      </div>

      {/* Advanced Export Modal - Only render when needed */}
      {showAdvancedModal && (
        <ExportOptionsModal
          isOpen={showAdvancedModal}
          onClose={() => setShowAdvancedModal(false)}
          dataType={dataType}
          currentFilters={cleanedFilters}
          availableColumns={availableColumns}
        />
      )}
    </>
  );
}

// Export column definitions for external use
export { DATA_TYPE_COLUMNS, EXPORT_FORMATS };
