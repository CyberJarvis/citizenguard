'use client';

import { Card, CardContent } from '@/components/ui/card';
import { cn } from '@/lib/utils';
import { TicketStatusBadge } from './TicketStatusBadge';
import { TicketPriorityBadge } from './TicketPriorityBadge';
import { SLAIndicator } from './SLAIndicator';
import { MapPin, Calendar, User, MessageSquare, AlertTriangle } from 'lucide-react';
import Link from 'next/link';

/**
 * Format date for display
 */
function formatDate(dateString) {
  if (!dateString) return 'N/A';
  const date = new Date(dateString);
  const now = new Date();
  const diffMs = now - date;
  const diffHours = diffMs / (1000 * 60 * 60);

  if (diffHours < 1) {
    const minutes = Math.floor(diffMs / (1000 * 60));
    return `${minutes}m ago`;
  } else if (diffHours < 24) {
    return `${Math.floor(diffHours)}h ago`;
  } else if (diffHours < 48) {
    return 'Yesterday';
  } else {
    return date.toLocaleDateString('en-IN', {
      day: 'numeric',
      month: 'short'
    });
  }
}

/**
 * TicketCard - Card component for displaying ticket in a list
 * @param {object} ticket - Ticket data
 * @param {boolean} compact - Use compact layout
 * @param {function} onClick - Click handler
 */
export function TicketCard({ ticket, compact = false, onClick }) {
  const {
    ticket_id,
    title,
    hazard_type,
    status,
    priority,
    location,
    created_at,
    response_due,
    resolution_due,
    first_response_at,
    resolved_at,
    reporter_name,
    assigned_analyst_name,
    assigned_authority_name,
    message_count,
    is_escalated
  } = ticket;

  const locationText = location?.region
    ? `${location.district || ''}, ${location.region}`.replace(/^, /, '')
    : location?.address || 'Unknown Location';

  const CardWrapper = onClick ? 'button' : Link;
  const cardProps = onClick
    ? { onClick, className: 'w-full text-left' }
    : { href: `/tickets/${ticket_id}` };

  return (
    <CardWrapper {...cardProps}>
      <Card className={cn(
        'hover:shadow-md transition-shadow cursor-pointer border-l-4',
        priority === 'emergency' && 'border-l-red-600',
        priority === 'critical' && 'border-l-red-500',
        priority === 'high' && 'border-l-orange-500',
        priority === 'medium' && 'border-l-yellow-500',
        priority === 'low' && 'border-l-gray-400',
        is_escalated && 'ring-2 ring-red-200'
      )}>
        <CardContent className={cn('p-4', compact && 'p-3')}>
          {/* Header Row */}
          <div className="flex items-start justify-between gap-2 mb-2">
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2 flex-wrap">
                <span className="text-xs text-gray-500 font-mono">
                  #{ticket_id?.slice(-8)}
                </span>
                <TicketStatusBadge status={status} />
                <TicketPriorityBadge priority={priority} />
                {is_escalated && (
                  <span className="inline-flex items-center gap-1 text-xs text-red-600">
                    <AlertTriangle className="w-3 h-3" />
                    Escalated
                  </span>
                )}
              </div>
              <h3 className="font-semibold text-gray-900 mt-1 truncate">
                {title || `${hazard_type} Report`}
              </h3>
            </div>
          </div>

          {/* Meta Info Row */}
          <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-sm text-gray-600 mb-2">
            <span className="inline-flex items-center gap-1">
              <MapPin className="w-3.5 h-3.5" />
              <span className="truncate max-w-[150px]">{locationText}</span>
            </span>
            <span className="inline-flex items-center gap-1">
              <Calendar className="w-3.5 h-3.5" />
              {formatDate(created_at)}
            </span>
            {message_count > 0 && (
              <span className="inline-flex items-center gap-1">
                <MessageSquare className="w-3.5 h-3.5" />
                {message_count}
              </span>
            )}
          </div>

          {/* Assignment Row */}
          {!compact && (
            <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-sm text-gray-500 mb-2">
              {reporter_name && (
                <span className="inline-flex items-center gap-1">
                  <User className="w-3.5 h-3.5" />
                  Reporter: {reporter_name}
                </span>
              )}
              {assigned_analyst_name && (
                <span className="inline-flex items-center gap-1">
                  <User className="w-3.5 h-3.5 text-blue-500" />
                  Analyst: {assigned_analyst_name}
                </span>
              )}
              {assigned_authority_name && (
                <span className="inline-flex items-center gap-1">
                  <User className="w-3.5 h-3.5 text-purple-500" />
                  Authority: {assigned_authority_name}
                </span>
              )}
            </div>
          )}

          {/* SLA Indicator */}
          {status !== 'closed' && status !== 'resolved' && (
            <SLAIndicator
              responseDue={response_due}
              resolutionDue={resolution_due}
              responseMetAt={first_response_at}
              resolvedAt={resolved_at}
              size="sm"
            />
          )}
        </CardContent>
      </Card>
    </CardWrapper>
  );
}

export default TicketCard;
