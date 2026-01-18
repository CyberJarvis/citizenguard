'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import {
  AlertCircle,
  AlertTriangle,
  Info,
  Megaphone,
  ChevronRight,
  MapPin,
  Clock,
  ExternalLink
} from 'lucide-react';
import { getAlerts } from '@/lib/api';
import { getRelativeTimeIST } from '@/lib/dateUtils';

export default function ActiveAlertsWidget() {
  const [alerts, setAlerts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Fetch active alerts
  useEffect(() => {
    const fetchAlerts = async () => {
      try {
        setLoading(true);
        setError(null);

        // Get active alerts, prioritize critical and high severity
        const response = await getAlerts({
          status_filter: 'active',
          limit: 5,
          skip: 0
        });

        // Sort by severity (critical > high > medium > low > info)
        const severityOrder = { critical: 0, high: 1, medium: 2, low: 3, info: 4 };
        const sortedAlerts = (response.alerts || []).sort(
          (a, b) => severityOrder[a.severity] - severityOrder[b.severity]
        );

        setAlerts(sortedAlerts);
      } catch (err) {
        console.error('Error fetching alerts:', err);
        setError('Failed to load alerts');
      } finally {
        setLoading(false);
      }
    };

    fetchAlerts();

    // Refresh alerts every 2 minutes
    const interval = setInterval(fetchAlerts, 120000);
    return () => clearInterval(interval);
  }, []);

  // Get severity configuration
  const getSeverityConfig = (severity) => {
    switch (severity) {
      case 'critical':
        return {
          icon: AlertCircle,
          color: 'text-red-600',
          bg: 'bg-red-50',
          border: 'border-red-300',
          badge: 'bg-red-600 text-white',
          label: 'CRITICAL',
          glow: 'ring-2 ring-red-200'
        };
      case 'high':
        return {
          icon: AlertTriangle,
          color: 'text-orange-600',
          bg: 'bg-orange-50',
          border: 'border-orange-300',
          badge: 'bg-orange-600 text-white',
          label: 'HIGH',
          glow: 'ring-1 ring-orange-200'
        };
      case 'medium':
        return {
          icon: Info,
          color: 'text-yellow-600',
          bg: 'bg-yellow-50',
          border: 'border-yellow-300',
          badge: 'bg-yellow-600 text-white',
          label: 'MEDIUM',
          glow: ''
        };
      case 'low':
        return {
          icon: Info,
          color: 'text-blue-600',
          bg: 'bg-blue-50',
          border: 'border-blue-300',
          badge: 'bg-blue-600 text-white',
          label: 'LOW',
          glow: ''
        };
      case 'info':
      default:
        return {
          icon: Megaphone,
          color: 'text-gray-600',
          bg: 'bg-gray-50',
          border: 'border-gray-300',
          badge: 'bg-gray-600 text-white',
          label: 'INFO',
          glow: ''
        };
    }
  };

  if (loading) {
    return (
      <div className="bg-white rounded-2xl shadow-lg border border-gray-200 p-6">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-bold text-gray-900 flex items-center gap-2">
            <Megaphone className="w-5 h-5 text-sky-600" />
            Active Alerts
          </h3>
        </div>
        <div className="flex items-center justify-center py-8">
          <div className="animate-spin rounded-full h-8 w-8 border-t-2 border-b-2 border-sky-500"></div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-white rounded-2xl shadow-lg border border-gray-200 p-6">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-bold text-gray-900 flex items-center gap-2">
            <Megaphone className="w-5 h-5 text-sky-600" />
            Active Alerts
          </h3>
        </div>
        <div className="text-center py-8">
          <AlertCircle className="w-12 h-12 text-red-500 mx-auto mb-3" />
          <p className="text-sm text-gray-600">{error}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-2xl shadow-lg border border-gray-200 overflow-hidden">
      {/* Header */}
      <div className="p-6 border-b border-gray-200 bg-gradient-to-r from-sky-50 to-blue-50">
        <div className="flex items-center justify-between">
          <h3 className="text-lg font-bold text-gray-900 flex items-center gap-2">
            <Megaphone className="w-5 h-5 text-sky-600" />
            Active Alerts
            {alerts.length > 0 && (
              <span className="ml-2 px-2 py-0.5 text-xs font-bold bg-sky-600 text-white rounded-full">
                {alerts.length}
              </span>
            )}
          </h3>

          <Link
            href="/notifications"
            className="text-sm font-medium text-sky-600 hover:text-sky-700 flex items-center gap-1"
          >
            View All
            <ChevronRight className="w-4 h-4" />
          </Link>
        </div>
      </div>

      {/* Alerts List */}
      <div className="divide-y divide-gray-100">
        {alerts.length === 0 ? (
          <div className="p-8 text-center">
            <Megaphone className="w-12 h-12 text-gray-300 mx-auto mb-3" />
            <p className="text-sm font-medium text-gray-600">No Active Alerts</p>
            <p className="text-xs text-gray-400 mt-1">You're safe! Check back later.</p>
          </div>
        ) : (
          alerts.map((alert) => {
            const config = getSeverityConfig(alert.severity);
            const Icon = config.icon;

            return (
              <div
                key={alert.alert_id}
                className={`p-5 hover:bg-gray-50 transition-all cursor-pointer ${config.glow}`}
              >
                <div className="flex items-start gap-4">
                  {/* Icon */}
                  <div
                    className={`flex-shrink-0 w-12 h-12 rounded-xl ${config.bg} ${config.border} border-2 flex items-center justify-center`}
                  >
                    <Icon className={`w-6 h-6 ${config.color}`} />
                  </div>

                  {/* Content */}
                  <div className="flex-1 min-w-0">
                    {/* Severity Badge */}
                    <div className="flex items-start justify-between gap-2 mb-2">
                      <span
                        className={`px-2 py-1 text-xs font-bold rounded ${config.badge} uppercase tracking-wide`}
                      >
                        {config.label}
                      </span>

                      {/* Time */}
                      <div className="flex items-center gap-1 text-xs text-gray-500">
                        <Clock className="w-3 h-3" />
                        {getRelativeTimeIST(alert.issued_at)}
                      </div>
                    </div>

                    {/* Title */}
                    <h4 className="text-base font-bold text-gray-900 mb-2 line-clamp-2">
                      {alert.title}
                    </h4>

                    {/* Description */}
                    <p className="text-sm text-gray-600 mb-3 line-clamp-2">
                      {alert.description}
                    </p>

                    {/* Regions */}
                    {alert.regions && alert.regions.length > 0 && (
                      <div className="flex items-center gap-2 mb-3">
                        <MapPin className="w-4 h-4 text-gray-400" />
                        <div className="flex flex-wrap gap-1">
                          {alert.regions.slice(0, 3).map((region, idx) => (
                            <span
                              key={idx}
                              className="px-2 py-0.5 text-xs bg-gray-100 text-gray-700 rounded"
                            >
                              {region}
                            </span>
                          ))}
                          {alert.regions.length > 3 && (
                            <span className="px-2 py-0.5 text-xs bg-gray-100 text-gray-700 rounded">
                              +{alert.regions.length - 3} more
                            </span>
                          )}
                        </div>
                      </div>
                    )}

                    {/* View Details Link */}
                    <Link
                      href={`/alerts/${alert.alert_id}`}
                      className={`inline-flex items-center gap-1 text-sm font-medium ${config.color} hover:underline`}
                    >
                      View Full Alert
                      <ExternalLink className="w-3 h-3" />
                    </Link>
                  </div>
                </div>
              </div>
            );
          })
        )}
      </div>

      {/* Footer - Show all alerts link if there are many */}
      {alerts.length >= 5 && (
        <div className="p-4 bg-gray-50 border-t border-gray-200">
          <Link
            href="/notifications"
            className="block w-full text-center py-2 text-sm font-medium text-sky-600 hover:text-sky-700 hover:bg-sky-50 rounded-lg transition-colors"
          >
            View All {alerts.length}+ Alerts
          </Link>
        </div>
      )}
    </div>
  );
}
