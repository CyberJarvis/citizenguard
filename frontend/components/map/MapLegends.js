'use client';

import { useState } from 'react';
import { ChevronDown, ChevronUp, Info } from 'lucide-react';

export function MapLegends({ activeHazards }) {
  const [isExpanded, setIsExpanded] = useState(true);

  const legends = {
    tideGauges: {
      title: 'Tide Gauge Stations',
      items: [
        { label: 'Operational', color: '#10b981', shape: 'triangle' },
        { label: 'Maintenance', color: '#f59e0b', shape: 'triangle' },
        { label: 'Offline', color: '#ef4444', shape: 'triangle' }
      ]
    },
    tsunamiBuoys: {
      title: 'Tsunami Buoys',
      items: [
        { label: 'Active', color: '#10b981', shape: 'circle' },
        { label: 'Warning', color: '#ef4444', shape: 'circle' }
      ]
    },
    highWaves: {
      title: 'High Wave/Swell Surge',
      items: [
        { label: 'Warning (>4m)', color: '#ef4444', shape: 'circle' },
        { label: 'Alert (3-4m)', color: '#fb923c', shape: 'circle' },
        { label: 'Watch (2-3m)', color: '#fbbf24', shape: 'circle' },
        { label: 'No Threat (<2m)', color: '#10b981', shape: 'circle' }
      ]
    },
    stormSurge: {
      title: 'Storm Surge',
      items: [
        { label: '0.7+ m', color: '#ff0000', shape: 'gradient' },
        { label: '0.5-0.7 m', color: '#ffff00', shape: 'gradient' },
        { label: '0.35-0.5 m', color: '#00ff00', shape: 'gradient' },
        { label: '0.2-0.35 m', color: '#00ffff', shape: 'gradient' },
        { label: '0-0.2 m', color: '#0000ff', shape: 'gradient' }
      ]
    },
    seismic: {
      title: 'Earthquake/Tsunami',
      items: [
        { label: 'Tsunami Threat', color: '#ef4444', shape: 'circle' },
        { label: 'No Tsunami Threat', color: '#3b82f6', shape: 'circle' }
      ]
    },
    ripCurrents: {
      title: 'Rip Currents',
      items: [
        { label: 'High Risk', color: '#ef4444', shape: 'circle' },
        { label: 'Moderate Risk', color: '#fbbf24', shape: 'circle' },
        { label: 'Low Risk', color: '#10b981', shape: 'circle' }
      ]
    },
    marinePollution: {
      title: 'Marine Pollution',
      items: [
        { label: 'High Severity', color: '#ef4444', shape: 'circle' },
        { label: 'Moderate Severity', color: '#f59e0b', shape: 'circle' },
        { label: 'Low Severity', color: '#10b981', shape: 'circle' }
      ]
    }
  };

  const activeLegends = Object.keys(legends).filter(key =>
    activeHazards.includes(key)
  );

  if (activeLegends.length === 0) return null;

  return (
    <div className="absolute top-4 right-4 bg-white rounded-lg shadow-lg border border-gray-200 z-[1000] max-w-xs">
      {/* Header */}
      <div
        className="flex items-center justify-between p-3 border-b border-gray-200 cursor-pointer hover:bg-gray-50"
        onClick={() => setIsExpanded(!isExpanded)}
      >
        <h3 className="font-semibold text-sm flex items-center gap-2">
          <Info className="w-4 h-4 text-blue-600" />
          Legend
        </h3>
        {isExpanded ? (
          <ChevronUp className="w-4 h-4 text-gray-500" />
        ) : (
          <ChevronDown className="w-4 h-4 text-gray-500" />
        )}
      </div>

      {/* Content */}
      {isExpanded && (
        <div className="p-3 max-h-96 overflow-y-auto">
          {activeLegends.map((hazardKey, index) => {
            const legend = legends[hazardKey];
            return (
              <div
                key={hazardKey}
                className={`${index > 0 ? 'mt-4' : ''} ${
                  index > 0 ? 'pt-4 border-t border-gray-100' : ''
                }`}
              >
                <h4 className="font-medium text-xs text-gray-700 mb-2">
                  {legend.title}
                </h4>
                <div className="space-y-1.5">
                  {legend.items.map((item, itemIndex) => (
                    <div key={itemIndex} className="flex items-center gap-2">
                      {item.shape === 'triangle' && (
                        <div style={{ color: item.color, fontSize: '16px', lineHeight: 1 }}>
                          ▲
                        </div>
                      )}
                      {item.shape === 'circle' && (
                        <div
                          style={{
                            background: item.color,
                            width: '12px',
                            height: '12px',
                            borderRadius: '50%',
                            border: '2px solid white',
                            boxShadow: '0 0 2px rgba(0,0,0,0.3)'
                          }}
                        />
                      )}
                      {item.shape === 'gradient' && (
                        <div
                          style={{
                            background: item.color,
                            width: '30px',
                            height: '12px',
                            border: '1px solid rgba(0,0,0,0.2)',
                            borderRadius: '2px'
                          }}
                        />
                      )}
                      <span className="text-xs text-gray-600">{item.label}</span>
                    </div>
                  ))}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

export function StormSurgeLegend() {
  return (
    <div className="absolute bottom-20 right-4 bg-white rounded-lg shadow-lg border border-gray-200 p-4 z-[1000]">
      <h3 className="font-semibold text-sm mb-3">Storm Surge (m)</h3>
      <div className="space-y-2">
        <div className="flex items-center gap-3">
          <div className="w-8 h-6" style={{ background: '#ff0000' }} />
          <span className="text-xs">0.7</span>
        </div>
        <div className="flex items-center gap-3">
          <div className="w-8 h-6" style={{ background: '#ffff00' }} />
          <span className="text-xs">0.525</span>
        </div>
        <div className="flex items-center gap-3">
          <div className="w-8 h-6" style={{ background: '#00ff00' }} />
          <span className="text-xs">0.35</span>
        </div>
        <div className="flex items-center gap-3">
          <div className="w-8 h-6" style={{ background: '#00ffff' }} />
          <span className="text-xs">0.175</span>
        </div>
        <div className="flex items-center gap-3">
          <div className="w-8 h-6" style={{ background: '#0000ff' }} />
          <span className="text-xs">0.0</span>
        </div>
      </div>
    </div>
  );
}
