'use client';

import { useState, useCallback } from 'react';
import { Clock, History, ArrowRight, Loader2 } from 'lucide-react';

/**
 * TimelineFilter - Toggle buttons for time-based hazard filtering
 *
 * Allows users to switch between:
 * - Last 6 hours
 * - Last 24 hours
 * - Next 48 hours (forecast)
 */
export function TimelineFilter({
  selectedRange = '24h',
  onRangeChange,
  isLoading = false,
  disabled = false,
  className = '',
}) {
  const timeRanges = [
    {
      id: '6h',
      label: 'Last 6h',
      icon: Clock,
      description: 'Recent incidents',
      isPast: true,
    },
    {
      id: '24h',
      label: 'Last 24h',
      icon: History,
      description: 'Past day',
      isPast: true,
    },
    {
      id: '48h_future',
      label: 'Next 48h',
      icon: ArrowRight,
      description: 'Forecast',
      isPast: false,
    },
  ];

  const handleRangeSelect = useCallback((rangeId) => {
    if (!disabled && !isLoading && rangeId !== selectedRange) {
      onRangeChange?.(rangeId);
    }
  }, [disabled, isLoading, selectedRange, onRangeChange]);

  return (
    <div className={`flex flex-col gap-2 ${className}`}>
      <div className="flex items-center gap-2 text-xs text-slate-400 px-1">
        <Clock className="w-3 h-3" />
        <span>Incident Timeline</span>
      </div>

      <div className="flex gap-1 p-1 bg-slate-800/50 rounded-lg">
        {timeRanges.map((range) => {
          const isSelected = selectedRange === range.id;
          const Icon = range.icon;

          return (
            <button
              key={range.id}
              onClick={() => handleRangeSelect(range.id)}
              disabled={disabled || isLoading}
              className={`
                relative flex-1 flex items-center justify-center gap-1.5
                px-3 py-2 rounded-md text-xs font-medium
                transition-all duration-200 ease-out
                ${isSelected
                  ? range.isPast
                    ? 'bg-cyan-600 text-white shadow-lg shadow-cyan-500/25'
                    : 'bg-orange-500 text-white shadow-lg shadow-orange-500/25'
                  : 'text-slate-400 hover:text-white hover:bg-slate-700/50'
                }
                ${disabled || isLoading ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}
              `}
              title={range.description}
            >
              {isLoading && isSelected ? (
                <Loader2 className="w-3.5 h-3.5 animate-spin" />
              ) : (
                <Icon className="w-3.5 h-3.5" />
              )}
              <span>{range.label}</span>

              {/* Indicator dot for forecast */}
              {!range.isPast && isSelected && (
                <span className="absolute -top-1 -right-1 w-2 h-2 bg-orange-400 rounded-full animate-pulse" />
              )}
            </button>
          );
        })}
      </div>

      {/* Info text based on selection */}
      <div className="text-[10px] text-slate-500 px-1">
        {selectedRange === '6h' && 'Showing recent hazard reports from the last 6 hours'}
        {selectedRange === '24h' && 'Showing hazard reports from the past 24 hours'}
        {selectedRange === '48h_future' && (
          <span className="text-orange-400/80">
            Showing predicted hazard zones for the next 48 hours
          </span>
        )}
      </div>
    </div>
  );
}

/**
 * Compact version for mobile or space-constrained layouts
 */
export function TimelineFilterCompact({
  selectedRange = '24h',
  onRangeChange,
  isLoading = false,
  disabled = false,
  className = '',
}) {
  const options = [
    { id: '6h', label: '6h' },
    { id: '24h', label: '24h' },
    { id: '48h_future', label: '48h+' },
  ];

  return (
    <div className={`flex gap-0.5 p-0.5 bg-slate-800/80 rounded-lg backdrop-blur-sm ${className}`}>
      {options.map((opt) => {
        const isSelected = selectedRange === opt.id;
        const isFuture = opt.id === '48h_future';

        return (
          <button
            key={opt.id}
            onClick={() => !disabled && !isLoading && onRangeChange?.(opt.id)}
            disabled={disabled || isLoading}
            className={`
              px-2.5 py-1 rounded text-[10px] font-semibold
              transition-all duration-150
              ${isSelected
                ? isFuture
                  ? 'bg-orange-500 text-white'
                  : 'bg-cyan-600 text-white'
                : 'text-slate-400 hover:text-white'
              }
              ${disabled || isLoading ? 'opacity-50' : ''}
            `}
          >
            {isLoading && isSelected ? '...' : opt.label}
          </button>
        );
      })}
    </div>
  );
}

export default TimelineFilter;
