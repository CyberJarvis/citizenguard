'use client';

import { useMemo } from 'react';
import { Circle, Popup, Tooltip } from 'react-leaflet';
import { TrendingUp, AlertTriangle, Waves } from 'lucide-react';

/**
 * ForecastConeLayer - Visualizes forecast hazard zones on the map
 *
 * Displays circular uncertainty zones around predicted high-risk areas
 * based on weather forecast data (wave height, wind, etc.)
 */
export function ForecastConeLayer({
  forecastData = [],
  forecastCone = null,
  visible = true,
  opacity = 0.6,
}) {
  // Process forecast data into renderable zones
  const forecastZones = useMemo(() => {
    if (!forecastData || forecastData.length === 0) return [];

    return forecastData.map((forecast) => {
      // Determine zone properties based on risk level
      let color, fillColor, radiusKm, strokeWeight;

      switch (forecast.risk_level) {
        case 'HIGH':
          color = '#ef4444';
          fillColor = '#ef4444';
          radiusKm = 50;
          strokeWeight = 3;
          break;
        case 'MODERATE':
          color = '#f97316';
          fillColor = '#f97316';
          radiusKm = 35;
          strokeWeight = 2;
          break;
        case 'LOW':
        default:
          color = '#22c55e';
          fillColor = '#22c55e';
          radiusKm = 25;
          strokeWeight = 1;
          break;
      }

      return {
        ...forecast,
        color,
        fillColor,
        radiusMeters: radiusKm * 1000,
        strokeWeight,
      };
    });
  }, [forecastData]);

  // Additional zones from forecast cone GeoJSON
  const coneFeatures = useMemo(() => {
    if (!forecastCone?.features) return [];

    return forecastCone.features.map((feature) => {
      const props = feature.properties || {};
      const coords = feature.geometry?.coordinates || [0, 0];
      const radiusKm = props.radius_km || 30;

      let color;
      switch (props.risk_level) {
        case 'HIGH':
          color = '#ef4444';
          break;
        case 'MODERATE':
          color = '#f97316';
          break;
        default:
          color = '#eab308';
      }

      return {
        lat: coords[1],
        lon: coords[0],
        location: props.location,
        risk_level: props.risk_level,
        max_wave: props.max_wave,
        color,
        radiusMeters: radiusKm * 1000,
      };
    });
  }, [forecastCone]);

  if (!visible) return null;

  return (
    <>
      {/* Forecast zones from API data */}
      {forecastZones.map((zone, index) => (
        <Circle
          key={`forecast-${zone.location}-${index}`}
          center={[zone.lat, zone.lon]}
          radius={zone.radiusMeters}
          pathOptions={{
            color: zone.color,
            fillColor: zone.fillColor,
            fillOpacity: opacity * 0.3,
            weight: zone.strokeWeight,
            dashArray: '10, 5',
            className: 'forecast-zone',
          }}
        >
          <Tooltip
            direction="top"
            offset={[0, -10]}
            opacity={0.95}
            className="forecast-tooltip"
          >
            <div className="p-2 min-w-[180px]">
              <div className="flex items-center gap-2 mb-2">
                <TrendingUp className="w-4 h-4 text-orange-400" />
                <span className="font-semibold text-sm">48h Forecast</span>
              </div>
              <div className="text-xs space-y-1">
                <div className="font-medium">{zone.location}</div>
                <div className="flex items-center gap-2">
                  <Waves className="w-3 h-3" />
                  <span>Max Wave: {zone.max_wave_height}m</span>
                </div>
                <div
                  className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium ${
                    zone.risk_level === 'HIGH'
                      ? 'bg-red-500/20 text-red-400'
                      : zone.risk_level === 'MODERATE'
                      ? 'bg-orange-500/20 text-orange-400'
                      : 'bg-green-500/20 text-green-400'
                  }`}
                >
                  {zone.risk_level === 'HIGH' && <AlertTriangle className="w-3 h-3" />}
                  {zone.risk_level} Risk
                </div>
              </div>
            </div>
          </Tooltip>

          <Popup className="forecast-popup">
            <div className="p-3 min-w-[220px]">
              <div className="flex items-center gap-2 mb-3 pb-2 border-b border-slate-600">
                <div
                  className={`w-3 h-3 rounded-full ${
                    zone.risk_level === 'HIGH'
                      ? 'bg-red-500'
                      : zone.risk_level === 'MODERATE'
                      ? 'bg-orange-500'
                      : 'bg-green-500'
                  }`}
                />
                <span className="font-semibold">{zone.location}</span>
              </div>

              <div className="space-y-2 text-sm">
                <div className="flex justify-between">
                  <span className="text-slate-400">Risk Level:</span>
                  <span
                    className={`font-medium ${
                      zone.risk_level === 'HIGH'
                        ? 'text-red-400'
                        : zone.risk_level === 'MODERATE'
                        ? 'text-orange-400'
                        : 'text-green-400'
                    }`}
                  >
                    {zone.risk_level}
                  </span>
                </div>

                <div className="flex justify-between">
                  <span className="text-slate-400">Max Wave Height:</span>
                  <span className="font-medium">{zone.max_wave_height}m</span>
                </div>

                <div className="flex justify-between">
                  <span className="text-slate-400">Forecast Hours:</span>
                  <span className="font-medium">{zone.forecast_hours}h</span>
                </div>

                {zone.max_wave_height >= 2.5 && (
                  <div className="mt-2 p-2 bg-red-500/10 border border-red-500/30 rounded text-xs text-red-300">
                    <AlertTriangle className="w-3 h-3 inline mr-1" />
                    IMD Warning: Unsafe for small boats
                  </div>
                )}
              </div>
            </div>
          </Popup>
        </Circle>
      ))}

      {/* Additional cone features from GeoJSON */}
      {coneFeatures.map((feature, index) => (
        <Circle
          key={`cone-${feature.location}-${index}`}
          center={[feature.lat, feature.lon]}
          radius={feature.radiusMeters}
          pathOptions={{
            color: feature.color,
            fillColor: feature.color,
            fillOpacity: opacity * 0.2,
            weight: 2,
            dashArray: '5, 10',
          }}
        >
          <Tooltip direction="top" offset={[0, -5]}>
            <div className="text-xs">
              <div className="font-medium">{feature.location}</div>
              <div>Predicted Risk Zone</div>
              {feature.max_wave && <div>Wave: {feature.max_wave}m</div>}
            </div>
          </Tooltip>
        </Circle>
      ))}

      {/* Legend indicator for forecast mode */}
      {(forecastZones.length > 0 || coneFeatures.length > 0) && (
        <div className="leaflet-bottom leaflet-left" style={{ marginBottom: '100px' }}>
          <div className="leaflet-control bg-slate-900/90 backdrop-blur-sm rounded-lg p-3 text-xs">
            <div className="flex items-center gap-2 mb-2 text-orange-400 font-medium">
              <TrendingUp className="w-4 h-4" />
              Forecast Mode Active
            </div>
            <div className="space-y-1 text-slate-300">
              <div className="flex items-center gap-2">
                <div className="w-3 h-3 rounded-full bg-red-500" />
                <span>High Risk Zone</span>
              </div>
              <div className="flex items-center gap-2">
                <div className="w-3 h-3 rounded-full bg-orange-500" />
                <span>Moderate Risk</span>
              </div>
              <div className="flex items-center gap-2">
                <div className="w-3 h-3 rounded-full bg-green-500" />
                <span>Low Risk</span>
              </div>
            </div>
          </div>
        </div>
      )}
    </>
  );
}

export default ForecastConeLayer;
