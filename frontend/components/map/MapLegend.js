'use client';

import React from 'react';
import { Clock, Radio } from 'lucide-react';
import { ALERT_CONFIG } from './OceanMap';

/**
 * MapLegend - Bottom legend with alert levels
 */
export function MapLegend({
  lastUpdate = null,
  isConnected = false,
  hoursFilter = 24,
}) {
  // Format time
  const formatTime = (date) => {
    if (!date) return 'N/A';
    return date.toLocaleTimeString('en-US', {
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  return (
    <div className="glass-panel p-4">
      {/* Alert Levels */}
      <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-3">
        Alert Levels
      </p>
      <div className="flex flex-wrap gap-3 mb-4">
        {Object.entries(ALERT_CONFIG)
          .reverse()
          .map(([level, config]) => (
            <div key={level} className="flex items-center gap-2">
              <div
                className="w-3 h-3 rounded-full"
                style={{ background: config.gradient }}
              />
              <span className="text-xs text-slate-300 font-medium">
                {config.name}
              </span>
            </div>
          ))}
      </div>

      {/* Time Indicator & Status */}
      <div className="flex items-center justify-between pt-3 border-t border-slate-700/50">
        {/* 24-Hour Indicator */}
        <div className="flex items-center gap-2">
          <Clock className="w-3 h-3 text-cyan-400" />
          <span className="text-xs text-slate-400">
            Last {hoursFilter} hours
          </span>
        </div>

        {/* Live Status */}
        <div className="flex items-center gap-2">
          {isConnected ? (
            <>
              <div className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
              <span className="text-xs text-slate-400">
                Live • {formatTime(lastUpdate)}
              </span>
            </>
          ) : (
            <>
              <Radio className="w-3 h-3 text-red-400" />
              <span className="text-xs text-red-400">Disconnected</span>
            </>
          )}
        </div>
      </div>
    </div>
  );
}

export default MapLegend;
