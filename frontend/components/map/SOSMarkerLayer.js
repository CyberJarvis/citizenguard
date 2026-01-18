'use client';

import { useEffect, useState, useCallback } from 'react';
import { Marker, Popup, useMap } from 'react-leaflet';
import L from 'leaflet';
import { getActiveSOSAlerts, acknowledgesSOS, dispatchSOSRescue } from '@/lib/api';
import useAuthStore from '@/context/AuthContext';

// Create pulsing SOS icon
const createSOSIcon = (status) => {
  if (typeof window === 'undefined') return null;

  const color = status === 'active' ? '#ef4444' : status === 'acknowledged' ? '#f97316' : '#3b82f6';
  const pulseClass = status === 'active' ? 'sos-pulse' : '';

  return L.divIcon({
    className: `sos-marker ${pulseClass}`,
    html: `
      <div class="sos-marker-container" style="--sos-color: ${color}">
        <div class="sos-marker-outer"></div>
        <div class="sos-marker-inner">
          <span>SOS</span>
        </div>
      </div>
    `,
    iconSize: [50, 50],
    iconAnchor: [25, 25],
    popupAnchor: [0, -30],
  });
};

// Inject SOS marker styles
const injectSOSStyles = () => {
  if (typeof document === 'undefined') return;
  if (document.getElementById('sos-marker-styles')) return;

  const style = document.createElement('style');
  style.id = 'sos-marker-styles';
  style.textContent = `
    .sos-marker-container {
      position: relative;
      width: 50px;
      height: 50px;
    }

    .sos-marker-outer {
      position: absolute;
      inset: 0;
      border-radius: 50%;
      background: var(--sos-color);
      opacity: 0.3;
    }

    .sos-pulse .sos-marker-outer {
      animation: sos-pulse-animation 1.5s ease-out infinite;
    }

    .sos-marker-inner {
      position: absolute;
      inset: 10px;
      border-radius: 50%;
      background: var(--sos-color);
      display: flex;
      align-items: center;
      justify-content: center;
      box-shadow: 0 0 10px var(--sos-color);
    }

    .sos-marker-inner span {
      color: white;
      font-size: 10px;
      font-weight: bold;
    }

    @keyframes sos-pulse-animation {
      0% {
        transform: scale(1);
        opacity: 0.3;
      }
      50% {
        transform: scale(1.5);
        opacity: 0.1;
      }
      100% {
        transform: scale(2);
        opacity: 0;
      }
    }

    .sos-popup {
      min-width: 250px;
    }

    .sos-popup h3 {
      color: #ef4444;
      font-weight: bold;
      margin-bottom: 8px;
    }

    .sos-popup-info {
      font-size: 12px;
      color: #374151;
    }

    .sos-popup-info p {
      margin: 4px 0;
    }

    .sos-popup-actions {
      margin-top: 12px;
      display: flex;
      gap: 8px;
    }

    .sos-popup-btn {
      flex: 1;
      padding: 8px 12px;
      border: none;
      border-radius: 6px;
      font-size: 12px;
      font-weight: 600;
      cursor: pointer;
      transition: all 0.2s;
    }

    .sos-popup-btn-acknowledge {
      background: #f97316;
      color: white;
    }

    .sos-popup-btn-acknowledge:hover {
      background: #ea580c;
    }

    .sos-popup-btn-dispatch {
      background: #3b82f6;
      color: white;
    }

    .sos-popup-btn-dispatch:hover {
      background: #2563eb;
    }

    .sos-popup-btn-call {
      background: #22c55e;
      color: white;
    }

    .sos-popup-btn-call:hover {
      background: #16a34a;
    }
  `;
  document.head.appendChild(style);
};

const SOSMarkerLayer = ({
  refreshInterval = 10000,
  onSOSClick = null,
  visible = true
}) => {
  const map = useMap();
  const user = useAuthStore((state) => state.user);
  const [sosAlerts, setSOSAlerts] = useState([]);
  const [loading, setLoading] = useState(false);

  const isAuthority = user?.role && ['authority', 'authority_admin'].includes(user.role);

  // Fetch active SOS alerts
  const fetchSOSAlerts = useCallback(async () => {
    if (!visible) return;

    try {
      setLoading(true);
      const response = await getActiveSOSAlerts({ limit: 50 });
      if (response.success) {
        setSOSAlerts(response.data || []);
      }
    } catch (error) {
      console.error('Error fetching SOS alerts:', error);
    } finally {
      setLoading(false);
    }
  }, [visible]);

  // Initial fetch and polling
  useEffect(() => {
    injectSOSStyles();
    fetchSOSAlerts();

    const interval = setInterval(fetchSOSAlerts, refreshInterval);
    return () => clearInterval(interval);
  }, [fetchSOSAlerts, refreshInterval]);

  // Handle acknowledge
  const handleAcknowledge = async (sosId) => {
    try {
      await acknowledgesSOS(sosId, { notes: 'Acknowledged from map' });
      fetchSOSAlerts(); // Refresh list
    } catch (error) {
      console.error('Error acknowledging SOS:', error);
    }
  };

  // Handle dispatch
  const handleDispatch = async (sosId) => {
    try {
      await dispatchSOSRescue(sosId, {
        dispatch_notes: 'Rescue dispatched from map interface'
      });
      fetchSOSAlerts();
    } catch (error) {
      console.error('Error dispatching rescue:', error);
    }
  };

  // Format time
  const formatTime = (isoString) => {
    if (!isoString) return 'Unknown';
    const date = new Date(isoString);
    return date.toLocaleTimeString('en-IN', {
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  if (!visible || sosAlerts.length === 0) {
    return null;
  }

  return (
    <>
      {sosAlerts.map((sos) => (
        <Marker
          key={sos.sos_id}
          position={[sos.latitude, sos.longitude]}
          icon={createSOSIcon(sos.status)}
          eventHandlers={{
            click: () => {
              if (onSOSClick) onSOSClick(sos);
            },
          }}
        >
          <Popup className="sos-popup">
            <div>
              <h3>SOS ALERT - {sos.sos_id}</h3>
              <div className="sos-popup-info">
                <p><strong>Name:</strong> {sos.user_name}</p>
                <p><strong>Phone:</strong> <a href={`tel:${sos.user_phone}`}>{sos.user_phone}</a></p>
                {sos.vessel_name && <p><strong>Vessel:</strong> {sos.vessel_name}</p>}
                {sos.crew_count > 1 && <p><strong>People:</strong> {sos.crew_count}</p>}
                <p><strong>Time:</strong> {formatTime(sos.created_at)}</p>
                <p><strong>Status:</strong> <span style={{
                  color: sos.status === 'active' ? '#ef4444' :
                         sos.status === 'acknowledged' ? '#f97316' : '#3b82f6',
                  fontWeight: 'bold',
                  textTransform: 'uppercase'
                }}>{sos.status}</span></p>
                {sos.message && <p><strong>Message:</strong> {sos.message}</p>}
                {sos.acknowledged_by_name && (
                  <p><strong>Acknowledged by:</strong> {sos.acknowledged_by_name}</p>
                )}
              </div>

              {isAuthority && (
                <div className="sos-popup-actions">
                  {sos.status === 'active' && (
                    <button
                      className="sos-popup-btn sos-popup-btn-acknowledge"
                      onClick={() => handleAcknowledge(sos.sos_id)}
                    >
                      Acknowledge
                    </button>
                  )}
                  {(sos.status === 'active' || sos.status === 'acknowledged') && (
                    <button
                      className="sos-popup-btn sos-popup-btn-dispatch"
                      onClick={() => handleDispatch(sos.sos_id)}
                    >
                      Dispatch
                    </button>
                  )}
                  <a
                    href={`tel:${sos.user_phone}`}
                    className="sos-popup-btn sos-popup-btn-call"
                    style={{ textAlign: 'center', textDecoration: 'none' }}
                  >
                    Call
                  </a>
                </div>
              )}
            </div>
          </Popup>
        </Marker>
      ))}
    </>
  );
};

export default SOSMarkerLayer;
