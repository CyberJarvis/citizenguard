'use client';

import React, { useEffect, useState } from 'react';
import { useMap, Polyline, Circle, Tooltip } from 'react-leaflet';
import { getOceanData } from '@/lib/api';

/**
 * WaveTrackLayer - Ocean wave and current visualization
 * Fetches real-time data from Open-Meteo Marine API via backend
 */
export function WaveTrackLayer({
  showCurrents = true,
  showWaveHeight = true,
  opacity = 0.8,
  refreshInterval = 300000, // 5 minutes
}) {
  const map = useMap();
  const [waveZones, setWaveZones] = useState([]);
  const [currentPaths, setCurrentPaths] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [lastUpdate, setLastUpdate] = useState(null);
  const [error, setError] = useState(null);

  // Fetch ocean data from API
  useEffect(() => {
    const fetchOceanData = async () => {
      try {
        setIsLoading(true);
        const data = await getOceanData({
          includeWaves: showWaveHeight,
          includeCurrents: showCurrents,
        });

        if (data.success) {
          setWaveZones(data.waveZones || []);
          setCurrentPaths(data.currentPaths || []);
          setLastUpdate(data.timestamp);
          setError(null);
        }
      } catch (err) {
        console.error('Failed to fetch ocean data:', err);
        setError(err.message);
        // Use fallback data if API fails
        setWaveZones(getDefaultWaveZones());
        setCurrentPaths(getDefaultCurrentPaths());
      } finally {
        setIsLoading(false);
      }
    };

    fetchOceanData();

    // Refresh data periodically
    const interval = setInterval(fetchOceanData, refreshInterval);
    return () => clearInterval(interval);
  }, [showWaveHeight, showCurrents, refreshInterval]);

  // Fallback data if API fails
  const getDefaultWaveZones = () => [
    { center: [15, 88], radius: 150000, height: '1.5m', color: '#f97316', level: 'Moderate', name: 'Central Bay' },
    { center: [12, 85], radius: 120000, height: '1.2m', color: '#eab308', level: 'Moderate', name: 'South Bay' },
    { center: [18, 91], radius: 130000, height: '1.8m', color: '#f97316', level: 'Moderate-High', name: 'North Bay' },
  ];

  const getDefaultCurrentPaths = () => [
    {
      name: 'East India Coastal Current',
      path: [[8.5, 80], [10, 80.2], [12, 80.5], [14, 81], [16, 81.5], [18, 82.5], [20, 84], [21.5, 87]],
      color: '#22d3ee',
      speed: '0.5-0.8 m/s',
      direction: 'Northward'
    },
    {
      name: 'Bay of Bengal Gyre',
      path: [[18, 85], [16, 88], [13, 90], [10, 89], [9, 86], [10, 83], [13, 82], [16, 83], [18, 85]],
      color: '#3b82f6',
      speed: '0.3-0.5 m/s',
      direction: 'Clockwise'
    },
  ];

  // Add animated dashed lines CSS
  useEffect(() => {
    const style = document.createElement('style');
    style.id = 'wave-track-styles';
    style.textContent = `
      .ocean-current-path {
        stroke-dasharray: 12, 8;
        animation: current-flow 2s linear infinite;
      }
      @keyframes current-flow {
        from { stroke-dashoffset: 0; }
        to { stroke-dashoffset: -20; }
      }
      .wave-zone-circle {
        transition: all 0.3s ease;
      }
      .wave-zone-circle:hover {
        stroke-width: 3;
      }
    `;

    if (!document.getElementById('wave-track-styles')) {
      document.head.appendChild(style);
    }

    return () => {
      const existingStyle = document.getElementById('wave-track-styles');
      if (existingStyle) existingStyle.remove();
    };
  }, []);

  return (
    <>
      {/* Wave Height Zones - Circles showing wave intensity */}
      {showWaveHeight && waveZones.map((zone, idx) => (
        <Circle
          key={`wave-zone-${idx}`}
          center={zone.center}
          radius={zone.radius}
          pathOptions={{
            color: zone.color,
            fillColor: zone.color,
            fillOpacity: 0.2 * opacity,
            weight: 2,
            opacity: 0.6 * opacity,
            dashArray: '8, 4',
            className: 'wave-zone-circle',
          }}
        >
          <Tooltip direction="center" permanent={false}>
            <div className="p-2 min-w-[140px]">
              <div className="font-bold text-sm mb-1">{zone.name}</div>
              <div className="text-xs space-y-0.5">
                <div><span className="opacity-70">Wave Height:</span> <span className="font-semibold">{zone.height || `${zone.waveHeight}m`}</span></div>
                <div><span className="opacity-70">Level:</span> <span className="font-semibold" style={{color: zone.color}}>{zone.level}</span></div>
                {zone.waveDirection && (
                  <div><span className="opacity-70">Direction:</span> {zone.waveDirection}°</div>
                )}
                {zone.wavePeriod && (
                  <div><span className="opacity-70">Period:</span> {zone.wavePeriod}s</div>
                )}
              </div>
            </div>
          </Tooltip>
        </Circle>
      ))}

      {/* Ocean Current Paths - Animated dashed lines */}
      {showCurrents && currentPaths.map((current, idx) => (
        <Polyline
          key={`current-${idx}`}
          positions={current.path}
          pathOptions={{
            color: current.color,
            weight: 4,
            opacity: 0.75 * opacity,
            dashArray: '12, 8',
            lineCap: 'round',
            lineJoin: 'round',
            className: 'ocean-current-path',
          }}
        >
          <Tooltip sticky>
            <div className="p-2 min-w-[160px]">
              <div className="font-bold text-sm mb-1">{current.name}</div>
              <div className="text-xs space-y-0.5">
                <div><span className="opacity-70">Direction:</span> <span className="font-semibold">{current.direction}</span></div>
                <div><span className="opacity-70">Speed:</span> <span className="font-semibold">{current.speed}</span></div>
                {current.description && (
                  <div className="mt-1 opacity-70 italic">{current.description}</div>
                )}
              </div>
            </div>
          </Tooltip>
        </Polyline>
      ))}

      {/* Current direction indicator dots */}
      {showCurrents && currentPaths.map((current, pathIdx) => {
        const dots = [];
        for (let i = 1; i < current.path.length; i++) {
          const from = current.path[i - 1];
          const to = current.path[i];
          const mid = [(from[0] + to[0]) / 2, (from[1] + to[1]) / 2];

          dots.push(
            <Circle
              key={`dot-${pathIdx}-${i}`}
              center={mid}
              radius={6000}
              pathOptions={{
                color: current.color,
                fillColor: current.color,
                fillOpacity: 0.9,
                weight: 0,
              }}
            />
          );
        }
        return dots;
      })}
    </>
  );
}

/**
 * WaveTrackLegend - Legend component for wave/current visualization
 */
export function WaveTrackLegend({ className = '' }) {
  return (
    <div className={`glass-panel-dark p-3 ${className}`}>
      <h4 className="text-xs font-semibold text-white mb-2 uppercase tracking-wider">
        Ocean Currents
      </h4>
      <div className="space-y-1.5 text-[11px]">
        <div className="flex items-center gap-2">
          <div className="w-6 h-0.5 rounded" style={{background: 'repeating-linear-gradient(90deg, #f97316 0, #f97316 8px, transparent 8px, transparent 12px)'}} />
          <span className="text-slate-300">Fast ({'>'}0.6 m/s)</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-6 h-0.5 rounded" style={{background: 'repeating-linear-gradient(90deg, #22d3ee 0, #22d3ee 8px, transparent 8px, transparent 12px)'}} />
          <span className="text-slate-300">Medium (0.4-0.6 m/s)</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-6 h-0.5 rounded" style={{background: 'repeating-linear-gradient(90deg, #3b82f6 0, #3b82f6 8px, transparent 8px, transparent 12px)'}} />
          <span className="text-slate-300">Slow ({'<'}0.4 m/s)</span>
        </div>
      </div>

      <h4 className="text-xs font-semibold text-white mt-3 mb-2 uppercase tracking-wider">
        Wave Height
      </h4>
      <div className="space-y-1.5 text-[11px]">
        <div className="flex items-center gap-2">
          <div className="w-3 h-3 rounded-full border-2 border-red-500 bg-red-500/20" />
          <span className="text-slate-300">High ({'>'}2.0m)</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-3 h-3 rounded-full border-2 border-orange-500 bg-orange-500/20" />
          <span className="text-slate-300">Moderate (1.5-2.0m)</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-3 h-3 rounded-full border-2 border-yellow-500 bg-yellow-500/20" />
          <span className="text-slate-300">Low-Mod (1.0-1.5m)</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-3 h-3 rounded-full border-2 border-green-500 bg-green-500/20" />
          <span className="text-slate-300">Low ({'<'}1.0m)</span>
        </div>
      </div>

      <p className="mt-3 text-[10px] text-slate-500 italic">
        Data: Open-Meteo Marine API
      </p>
    </div>
  );
}

export default WaveTrackLayer;
