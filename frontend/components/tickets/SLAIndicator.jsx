'use client';

import { cn } from '@/lib/utils';
import { Clock, AlertTriangle, CheckCircle } from 'lucide-react';
import { useEffect, useState } from 'react';

/**
 * Calculate time remaining or overdue
 */
function calculateTimeStatus(dueDate) {
  if (!dueDate) return null;

  const now = new Date();
  const due = new Date(dueDate);
  const diffMs = due - now;
  const diffHours = diffMs / (1000 * 60 * 60);

  if (diffMs <= 0) {
    // Overdue
    const overdueHours = Math.abs(diffHours);
    return {
      status: 'breached',
      hours: overdueHours,
      text: formatTimeText(overdueHours, true)
    };
  } else if (diffHours <= 2) {
    // Warning - less than 2 hours
    return {
      status: 'warning',
      hours: diffHours,
      text: formatTimeText(diffHours, false)
    };
  } else {
    // On track
    return {
      status: 'ok',
      hours: diffHours,
      text: formatTimeText(diffHours, false)
    };
  }
}

/**
 * Format time text for display
 */
function formatTimeText(hours, isOverdue) {
  const absHours = Math.abs(hours);
  const prefix = isOverdue ? 'Overdue by ' : '';

  if (absHours < 1) {
    const minutes = Math.round(absHours * 60);
    return `${prefix}${minutes}m`;
  } else if (absHours < 24) {
    return `${prefix}${Math.round(absHours)}h`;
  } else {
    const days = Math.floor(absHours / 24);
    const remainingHours = Math.round(absHours % 24);
    return `${prefix}${days}d ${remainingHours}h`;
  }
}

/**
 * SLAIndicator - Shows SLA status with countdown/overdue
 * @param {string} responseDue - ISO datetime for response SLA
 * @param {string} resolutionDue - ISO datetime for resolution SLA
 * @param {boolean} responseMetAt - When response was met (null if not yet)
 * @param {boolean} resolvedAt - When ticket was resolved (null if not yet)
 * @param {string} size - Size variant: 'sm', 'md', 'lg'
 */
export function SLAIndicator({
  responseDue,
  resolutionDue,
  responseMetAt,
  resolvedAt,
  size = 'md',
  showBoth = false
}) {
  const [, forceUpdate] = useState(0);

  // Update every minute
  useEffect(() => {
    const interval = setInterval(() => forceUpdate(n => n + 1), 60000);
    return () => clearInterval(interval);
  }, []);

  const responseStatus = responseMetAt
    ? { status: 'met', text: 'Responded' }
    : calculateTimeStatus(responseDue);

  const resolutionStatus = resolvedAt
    ? { status: 'met', text: 'Resolved' }
    : calculateTimeStatus(resolutionDue);

  // Pick the most critical status to show
  const primaryStatus = !responseMetAt && responseStatus?.status === 'breached'
    ? { ...responseStatus, type: 'Response' }
    : !resolvedAt && resolutionStatus
      ? { ...resolutionStatus, type: 'Resolution' }
      : null;

  if (!primaryStatus) return null;

  const sizeClasses = {
    sm: 'text-xs px-2 py-0.5',
    md: 'text-sm px-2.5 py-1',
    lg: 'text-base px-3 py-1.5'
  };

  const statusClasses = {
    breached: 'bg-red-100 text-red-700 border-red-200',
    warning: 'bg-amber-100 text-amber-700 border-amber-200',
    ok: 'bg-green-100 text-green-700 border-green-200',
    met: 'bg-gray-100 text-gray-600 border-gray-200'
  };

  const Icon = primaryStatus.status === 'breached'
    ? AlertTriangle
    : primaryStatus.status === 'met'
      ? CheckCircle
      : Clock;

  return (
    <div className="flex items-center gap-2">
      <div
        className={cn(
          'inline-flex items-center gap-1.5 rounded-md border font-medium',
          sizeClasses[size],
          statusClasses[primaryStatus.status]
        )}
      >
        <Icon className={cn(
          size === 'sm' ? 'w-3 h-3' : size === 'lg' ? 'w-5 h-5' : 'w-4 h-4',
          primaryStatus.status === 'breached' && 'animate-pulse'
        )} />
        <span>{primaryStatus.type}: {primaryStatus.text}</span>
      </div>

      {showBoth && resolutionStatus && primaryStatus.type !== 'Resolution' && (
        <div
          className={cn(
            'inline-flex items-center gap-1.5 rounded-md border font-medium',
            sizeClasses[size],
            statusClasses[resolutionStatus.status]
          )}
        >
          <Clock className={size === 'sm' ? 'w-3 h-3' : 'w-4 h-4'} />
          <span>Resolution: {resolutionStatus.text}</span>
        </div>
      )}
    </div>
  );
}

export default SLAIndicator;
