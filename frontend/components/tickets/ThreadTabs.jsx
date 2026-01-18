'use client';

import { cn } from '@/lib/utils';
import { Users, MessageCircle, Lock, FileText } from 'lucide-react';

/**
 * Thread configurations
 */
const THREAD_CONFIG = {
  all: {
    label: 'All Parties',
    icon: Users,
    description: 'Visible to everyone',
    color: 'text-blue-600 border-blue-500 bg-blue-50'
  },
  ra: {
    label: 'Reporter Chat',
    icon: MessageCircle,
    description: 'Private with reporter',
    color: 'text-green-600 border-green-500 bg-green-50'
  },
  aa: {
    label: 'Authority Chat',
    icon: Lock,
    description: 'Private with authority',
    color: 'text-purple-600 border-purple-500 bg-purple-50'
  },
  internal: {
    label: 'Internal Notes',
    icon: FileText,
    description: 'Staff only',
    color: 'text-gray-600 border-gray-500 bg-gray-50'
  }
};

/**
 * Get allowed threads based on user role
 */
export function getAllowedThreads(userRole, isReporter = false) {
  if (isReporter) {
    // Reporter can only see all-party and their private chat with analyst
    return ['all', 'ra'];
  }

  switch (userRole) {
    case 'citizen':
      return ['all', 'ra'];
    case 'analyst':
      return ['all', 'ra', 'aa', 'internal'];
    case 'authority':
    case 'authority_admin':
      return ['all', 'aa', 'internal'];
    default:
      return ['all'];
  }
}

/**
 * ThreadTabs - Tab navigation for message threads
 * @param {string} activeThread - Currently active thread
 * @param {function} onThreadChange - Callback when thread changes
 * @param {array} allowedThreads - List of allowed thread keys
 * @param {object} threadCounts - Message counts per thread
 */
export function ThreadTabs({
  activeThread = 'all',
  onThreadChange,
  allowedThreads = ['all', 'ra', 'aa', 'internal'],
  threadCounts = {}
}) {
  return (
    <div className="flex border-b border-gray-200 overflow-x-auto">
      {allowedThreads.map((threadKey) => {
        const config = THREAD_CONFIG[threadKey];
        if (!config) return null;

        const Icon = config.icon;
        const isActive = activeThread === threadKey;
        const count = threadCounts[threadKey] || 0;

        return (
          <button
            key={threadKey}
            onClick={() => onThreadChange(threadKey)}
            className={cn(
              'flex items-center gap-2 px-4 py-3 text-sm font-medium whitespace-nowrap',
              'border-b-2 transition-colors',
              isActive
                ? `${config.color} border-current`
                : 'text-gray-500 border-transparent hover:text-gray-700 hover:bg-gray-50'
            )}
            title={config.description}
          >
            <Icon className="w-4 h-4" />
            <span>{config.label}</span>
            {count > 0 && (
              <span className={cn(
                'ml-1 px-1.5 py-0.5 text-xs rounded-full',
                isActive ? 'bg-white/80' : 'bg-gray-200'
              )}>
                {count}
              </span>
            )}
          </button>
        );
      })}
    </div>
  );
}

/**
 * ThreadSelector - Dropdown for selecting thread when composing message
 */
export function ThreadSelector({
  selectedThread = 'all',
  onThreadChange,
  allowedThreads = ['all', 'ra', 'aa', 'internal']
}) {
  return (
    <div className="flex items-center gap-2">
      <span className="text-sm text-gray-500">Send to:</span>
      <select
        value={selectedThread}
        onChange={(e) => onThreadChange(e.target.value)}
        className="text-sm border border-gray-300 rounded-md px-2 py-1 bg-white"
      >
        {allowedThreads.map((threadKey) => {
          const config = THREAD_CONFIG[threadKey];
          if (!config) return null;
          return (
            <option key={threadKey} value={threadKey}>
              {config.label}
            </option>
          );
        })}
      </select>
    </div>
  );
}

export { THREAD_CONFIG };
export default ThreadTabs;
