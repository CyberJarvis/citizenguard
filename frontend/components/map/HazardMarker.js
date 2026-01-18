'use client';

import { Marker, Popup, Circle } from 'react-leaflet';
import { AlertTriangle, Waves, Droplets, Anchor, Zap, Wind } from 'lucide-react';

// Custom marker icons
const createCustomIcon = (color, icon = 'circle') => {
  // Check if running in browser
  if (typeof window === 'undefined') return null;

  const L = require('leaflet');

  const iconHtml = icon === 'triangle'
    ? `<div style="color: ${color}; font-size: 24px;">▲</div>`
    : icon === 'buoy'
    ? `<div style="background: ${color}; width: 16px; height: 16px; border-radius: 50%; border: 3px solid white; box-shadow: 0 0 5px rgba(0,0,0,0.3);"></div>`
    : `<div style="background: ${color}; width: 14px; height: 14px; border-radius: 50%; border: 2px solid white;"></div>`;

  return L.divIcon({
    html: iconHtml,
    className: 'custom-marker',
    iconSize: [20, 20],
    iconAnchor: [10, 10],
    popupAnchor: [0, -10]
  });
};

// Severity colors
const SEVERITY_COLORS = {
  operational: '#10b981',
  maintenance: '#f59e0b',
  offline: '#ef4444',
  active: '#10b981',
  warning: '#ef4444',
  no_threat: '#10b981',
  watch: '#fbbf24',
  alert: '#fb923c',
  high: '#ef4444',
  moderate: '#fbbf24',
  low: '#10b981',
};

export function TideGaugeMarker({ station }) {
  return (
    <>
      <Marker
        position={[station.lat, station.lon]}
        icon={createCustomIcon(SEVERITY_COLORS[station.status], 'triangle')}
      >
        <Popup>
          <div className="p-2">
            <h3 className="font-bold text-sm mb-2">{station.name}</h3>
            <div className="text-xs space-y-1">
              <p><strong>ID:</strong> {station.id}</p>
              <p><strong>Region:</strong> {station.region}</p>
              <p><strong>Sea Level:</strong> {station.seaLevel} m</p>
              <p><strong>Status:</strong> <span className={`font-medium ${
                station.status === 'operational' ? 'text-green-600' : 'text-orange-600'
              }`}>{station.status.toUpperCase()}</span></p>
            </div>
          </div>
        </Popup>
      </Marker>
    </>
  );
}

export function TsunamiBuoyMarker({ buoy }) {
  return (
    <>
      <Marker
        position={[buoy.lat, buoy.lon]}
        icon={createCustomIcon(SEVERITY_COLORS[buoy.status], 'buoy')}
      >
        <Popup>
          <div className="p-2">
            <h3 className="font-bold text-sm mb-2">{buoy.name}</h3>
            <div className="text-xs space-y-1">
              <p><strong>ID:</strong> {buoy.id}</p>
              <p><strong>Status:</strong> <span className={`font-medium ${
                buoy.status === 'active' ? 'text-green-600' : 'text-red-600'
              }`}>{buoy.status.toUpperCase()}</span></p>
              <p><strong>Depth:</strong> {buoy.depth} m</p>
              <p><strong>Last Update:</strong> {buoy.lastUpdate}</p>
            </div>
          </div>
        </Popup>
      </Marker>
    </>
  );
}

export function HighWaveMarker({ data }) {
  return (
    <>
      <Marker
        position={[data.lat, data.lon]}
        icon={createCustomIcon(SEVERITY_COLORS[data.severity])}
      >
        <Popup>
          <div className="p-2">
            <h3 className="font-bold text-sm mb-2 flex items-center gap-2">
              <Waves className="w-4 h-4" />
              {data.location}
            </h3>
            <div className="text-xs space-y-1">
              <p><strong>Severity:</strong> <span className={`font-medium uppercase ${
                data.severity === 'warning' ? 'text-red-600' :
                data.severity === 'alert' ? 'text-orange-600' :
                data.severity === 'watch' ? 'text-yellow-600' :
                'text-green-600'
              }`}>{data.severity.replace('_', ' ')}</span></p>
              <p><strong>Wave Height:</strong> {data.waveHeight} m</p>
              <p><strong>Swell Period:</strong> {data.swellPeriod.toFixed(1)} s</p>
              <p><strong>Wind Speed:</strong> {data.windSpeed.toFixed(0)} knots</p>
              <p><strong>Direction:</strong> {data.direction}</p>
              <p className="text-gray-500 text-[10px] mt-2">
                Valid until: {new Date(data.validUntil).toLocaleString()}
              </p>
            </div>
          </div>
        </Popup>
      </Marker>
      {/* Add a circle for visual impact */}
      <Circle
        center={[data.lat, data.lon]}
        radius={data.severity === 'warning' ? 50000 : data.severity === 'alert' ? 35000 : 20000}
        pathOptions={{
          color: SEVERITY_COLORS[data.severity],
          fillColor: SEVERITY_COLORS[data.severity],
          fillOpacity: 0.1,
          weight: 2
        }}
      />
    </>
  );
}

export function SeismicMarker({ data }) {
  const size = Math.pow(10, data.magnitude) / 100; // Scale for circle radius

  return (
    <>
      <Circle
        center={[data.lat, data.lon]}
        radius={size * 1000}
        pathOptions={{
          color: data.tsunamiThreat === 'no' ? '#3b82f6' : '#ef4444',
          fillColor: data.tsunamiThreat === 'no' ? '#3b82f6' : '#ef4444',
          fillOpacity: 0.3,
          weight: 2
        }}
      />
      <Marker
        position={[data.lat, data.lon]}
        icon={createCustomIcon(data.tsunamiThreat === 'no' ? '#3b82f6' : '#ef4444')}
      >
        <Popup>
          <div className="p-2">
            <h3 className="font-bold text-sm mb-2 flex items-center gap-2">
              <Zap className="w-4 h-4" />
              Earthquake
            </h3>
            <div className="text-xs space-y-1">
              <p><strong>Magnitude:</strong> M {data.magnitude}</p>
              <p><strong>Depth:</strong> {data.depth} km</p>
              <p><strong>Location:</strong> {data.location}</p>
              <p><strong>Tsunami Threat:</strong> <span className={`font-medium ${
                data.tsunamiThreat === 'no' ? 'text-green-600' : 'text-red-600'
              }`}>{data.tsunamiThreat.toUpperCase()}</span></p>
              <p className="text-gray-500 text-[10px] mt-2">
                {new Date(data.time).toLocaleString()}
              </p>
            </div>
          </div>
        </Popup>
      </Marker>
    </>
  );
}

export function RipCurrentMarker({ data }) {
  return (
    <>
      <Marker
        position={[data.lat, data.lon]}
        icon={createCustomIcon(SEVERITY_COLORS[data.severity])}
      >
        <Popup>
          <div className="p-2">
            <h3 className="font-bold text-sm mb-2 flex items-center gap-2">
              <Wind className="w-4 h-4" />
              {data.beach}
            </h3>
            <div className="text-xs space-y-1">
              <p><strong>Location:</strong> {data.location}</p>
              <p><strong>Severity:</strong> <span className={`font-medium uppercase ${
                data.severity === 'high' ? 'text-red-600' :
                data.severity === 'moderate' ? 'text-yellow-600' :
                'text-green-600'
              }`}>{data.severity}</span></p>
              <p><strong>Current Speed:</strong> {data.currentSpeed.toFixed(1)} m/s</p>
              <p><strong>Advisory:</strong> {data.advisory}</p>
              <p className="text-gray-500 text-[10px] mt-2">
                Valid until: {new Date(data.validUntil).toLocaleString()}
              </p>
            </div>
          </div>
        </Popup>
      </Marker>
    </>
  );
}

export function PollutionMarker({ data }) {
  const icon = data.type === 'algal_bloom' ? '🦠' : data.type === 'oil_spill' ? '🛢️' : '🗑️';

  // Create emoji icon
  const createEmojiIcon = () => {
    if (typeof window === 'undefined') return null;
    const L = require('leaflet');

    return L.divIcon({
      html: `<div style="font-size: 24px;">${icon}</div>`,
      className: 'custom-marker',
      iconSize: [24, 24],
      iconAnchor: [12, 12]
    });
  };

  return (
    <>
      <Circle
        center={[data.lat, data.lon]}
        radius={data.area * 1000}
        pathOptions={{
          color: data.severity === 'high' ? '#ef4444' : data.severity === 'moderate' ? '#f59e0b' : '#10b981',
          fillColor: data.severity === 'high' ? '#ef4444' : data.severity === 'moderate' ? '#f59e0b' : '#10b981',
          fillOpacity: 0.2,
          weight: 2
        }}
      />
      <Marker
        position={[data.lat, data.lon]}
        icon={createEmojiIcon()}
      >
        <Popup>
          <div className="p-2">
            <h3 className="font-bold text-sm mb-2 flex items-center gap-2">
              <Droplets className="w-4 h-4" />
              {data.type.replace('_', ' ').toUpperCase()}
            </h3>
            <div className="text-xs space-y-1">
              <p><strong>Location:</strong> {data.location}</p>
              <p><strong>Severity:</strong> <span className={`font-medium uppercase ${
                data.severity === 'high' ? 'text-red-600' :
                data.severity === 'moderate' ? 'text-yellow-600' :
                'text-green-600'
              }`}>{data.severity}</span></p>
              <p><strong>Affected Area:</strong> {data.area} sq km</p>
              {data.species && <p><strong>Species:</strong> {data.species}</p>}
              {data.source && <p><strong>Source:</strong> {data.source}</p>}
              <p className="text-gray-500 text-[10px] mt-2">
                Detected: {new Date(data.detectedAt || data.reportedAt).toLocaleString()}
              </p>
            </div>
          </div>
        </Popup>
      </Marker>
    </>
  );
}
