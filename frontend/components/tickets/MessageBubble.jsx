'use client';

import { cn } from '@/lib/utils';
import { User, Shield, UserCheck } from 'lucide-react';
import { THREAD_CONFIG } from './ThreadTabs';

/**
 * Format timestamp for message display
 */
function formatMessageTime(dateString) {
  if (!dateString) return '';
  const date = new Date(dateString);
  const now = new Date();
  const isToday = date.toDateString() === now.toDateString();

  if (isToday) {
    return date.toLocaleTimeString('en-IN', {
      hour: '2-digit',
      minute: '2-digit'
    });
  } else {
    return date.toLocaleDateString('en-IN', {
      day: 'numeric',
      month: 'short',
      hour: '2-digit',
      minute: '2-digit'
    });
  }
}

/**
 * Get role icon
 */
function getRoleIcon(role) {
  switch (role) {
    case 'authority':
    case 'authority_admin':
      return Shield;
    case 'analyst':
      return UserCheck;
    default:
      return User;
  }
}

/**
 * MessageBubble - Individual message display
 * @param {object} message - Message data
 * @param {boolean} isOwnMessage - Whether this is the current user's message
 * @param {boolean} showThreadIndicator - Show which thread the message is in
 */
export function MessageBubble({
  message,
  isOwnMessage = false,
  showThreadIndicator = false
}) {
  const {
    content,
    sender_name,
    sender_role,
    created_at,
    thread,
    attachments
  } = message;

  const RoleIcon = getRoleIcon(sender_role);
  const threadConfig = thread ? THREAD_CONFIG[thread] : null;

  return (
    <div className={cn(
      'flex gap-2 mb-4',
      isOwnMessage ? 'flex-row-reverse' : 'flex-row'
    )}>
      {/* Avatar */}
      <div className={cn(
        'flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center',
        sender_role === 'authority' || sender_role === 'authority_admin'
          ? 'bg-purple-100 text-purple-600'
          : sender_role === 'analyst'
            ? 'bg-blue-100 text-blue-600'
            : 'bg-gray-100 text-gray-600'
      )}>
        <RoleIcon className="w-4 h-4" />
      </div>

      {/* Message Content */}
      <div className={cn(
        'flex flex-col max-w-[70%]',
        isOwnMessage ? 'items-end' : 'items-start'
      )}>
        {/* Sender Info */}
        <div className={cn(
          'flex items-center gap-2 mb-1 text-xs',
          isOwnMessage ? 'flex-row-reverse' : 'flex-row'
        )}>
          <span className="font-medium text-gray-700">
            {sender_name || 'Unknown'}
          </span>
          <span className="text-gray-400">
            {formatMessageTime(created_at)}
          </span>
          {showThreadIndicator && threadConfig && (
            <span className={cn(
              'px-1.5 py-0.5 rounded text-xs',
              threadConfig.color
            )}>
              {threadConfig.label}
            </span>
          )}
        </div>

        {/* Bubble */}
        <div className={cn(
          'px-4 py-2 rounded-2xl',
          isOwnMessage
            ? 'bg-teal-600 text-white rounded-tr-sm'
            : 'bg-gray-100 text-gray-800 rounded-tl-sm'
        )}>
          <p className="text-sm whitespace-pre-wrap break-words">
            {content}
          </p>
        </div>

        {/* Attachments */}
        {attachments && attachments.length > 0 && (
          <div className="flex flex-wrap gap-2 mt-2">
            {attachments.map((attachment, idx) => (
              <a
                key={idx}
                href={attachment}
                target="_blank"
                rel="noopener noreferrer"
                className="text-xs text-teal-600 hover:underline"
              >
                Attachment {idx + 1}
              </a>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

export default MessageBubble;
