'use client';

import { Badge } from '@/components/ui/badge';
import { cn } from '@/lib/utils';
import { AlertTriangle, AlertCircle, ArrowUp, Minus, ArrowDown } from 'lucide-react';

/**
 * Priority configurations for tickets with SLA indication
 */
const PRIORITY_CONFIG = {
  emergency: {
    label: 'Emergency',
    icon: AlertTriangle,
    className: 'bg-red-600 text-white border-red-600 animate-pulse',
    slaHours: { response: 1, resolution: 4 }
  },
  critical: {
    label: 'Critical',
    icon: AlertCircle,
    className: 'bg-red-500 text-white border-red-500',
    slaHours: { response: 2, resolution: 8 }
  },
  high: {
    label: 'High',
    icon: ArrowUp,
    className: 'bg-orange-500 text-white border-orange-500',
    slaHours: { response: 4, resolution: 24 }
  },
  medium: {
    label: 'Medium',
    icon: Minus,
    className: 'bg-yellow-500 text-white border-yellow-500',
    slaHours: { response: 8, resolution: 48 }
  },
  low: {
    label: 'Low',
    icon: ArrowDown,
    className: 'bg-gray-400 text-white border-gray-400',
    slaHours: { response: 24, resolution: 72 }
  }
};

/**
 * TicketPriorityBadge - Displays ticket priority with icon
 * @param {string} priority - The ticket priority
 * @param {boolean} showIcon - Whether to show the priority icon
 * @param {string} className - Additional CSS classes
 */
export function TicketPriorityBadge({ priority, showIcon = true, className }) {
  const config = PRIORITY_CONFIG[priority] || PRIORITY_CONFIG.medium;
  const Icon = config.icon;

  return (
    <Badge className={cn(config.className, className)}>
      {showIcon && <Icon className="w-3 h-3 mr-1" />}
      {config.label}
    </Badge>
  );
}

/**
 * Get SLA hours for a priority
 */
export function getSLAHours(priority) {
  return PRIORITY_CONFIG[priority]?.slaHours || PRIORITY_CONFIG.medium.slaHours;
}

export default TicketPriorityBadge;
