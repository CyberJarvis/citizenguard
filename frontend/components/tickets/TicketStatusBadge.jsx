'use client';

import { Badge } from '@/components/ui/badge';
import { cn } from '@/lib/utils';

/**
 * Status configurations for tickets
 */
const STATUS_CONFIG = {
  open: {
    label: 'Open',
    variant: 'outline',
    className: 'border-blue-500 text-blue-600 bg-blue-50'
  },
  assigned: {
    label: 'Assigned',
    variant: 'outline',
    className: 'border-indigo-500 text-indigo-600 bg-indigo-50'
  },
  in_progress: {
    label: 'In Progress',
    variant: 'default',
    className: 'bg-amber-500 text-white border-amber-500'
  },
  escalated: {
    label: 'Escalated',
    variant: 'destructive',
    className: 'bg-red-500 text-white border-red-500'
  },
  resolved: {
    label: 'Resolved',
    variant: 'outline',
    className: 'border-green-500 text-green-600 bg-green-50'
  },
  closed: {
    label: 'Closed',
    variant: 'secondary',
    className: 'bg-gray-200 text-gray-600 border-gray-300'
  }
};

/**
 * TicketStatusBadge - Displays ticket status with appropriate styling
 * @param {string} status - The ticket status
 * @param {string} className - Additional CSS classes
 */
export function TicketStatusBadge({ status, className }) {
  const config = STATUS_CONFIG[status] || STATUS_CONFIG.open;

  return (
    <Badge
      variant={config.variant}
      className={cn(config.className, className)}
    >
      {config.label}
    </Badge>
  );
}

export default TicketStatusBadge;
