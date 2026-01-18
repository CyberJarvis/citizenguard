'use client';

import { useEffect, useRef, useState } from 'react';
import { format, isToday, isYesterday } from 'date-fns';
import { Check, CheckCheck } from 'lucide-react';

// Backend URL for images (static files are served from root, not /api/v1)
const getBackendBaseUrl = () => {
  const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';
  // Remove /api/v1 suffix to get the backend root URL
  return apiUrl.replace('/api/v1', '');
};

// Helper to get full image URL
const getImageUrl = (path) => {
  if (!path) return null;
  if (path.startsWith('http')) return path;
  return `${getBackendBaseUrl()}${path}`;
};

// Avatar component with error handling
function Avatar({ src, name, role, size = 'sm' }) {
  const [imageError, setImageError] = useState(false);

  const sizeClasses = size === 'sm' ? 'w-8 h-8 text-xs' : 'w-11 h-11 text-sm';

  const getRoleBadgeStyle = (role) => {
    switch (role) {
      case 'ADMIN':
        return 'bg-red-500 text-white';
      case 'ANALYST':
        return 'bg-blue-500 text-white';
      default:
        return 'bg-gray-400 text-white';
    }
  };

  const getInitials = (name) => {
    return name
      ?.split(' ')
      .map(n => n[0])
      .join('')
      .toUpperCase()
      .slice(0, 2) || '??';
  };

  if (!src || imageError) {
    return (
      <div className={`${sizeClasses} rounded-full flex items-center justify-center font-semibold ${getRoleBadgeStyle(role)}`}>
        {getInitials(name)}
      </div>
    );
  }

  return (
    <img
      src={getImageUrl(src)}
      alt={name}
      className={`${sizeClasses} rounded-full object-cover`}
      onError={() => setImageError(true)}
    />
  );
}

export default function MessageList({ messages, currentUserId }) {
  const messagesEndRef = useRef(null);
  const messagesContainerRef = useRef(null);

  const scrollToBottom = (behavior = 'smooth') => {
    messagesEndRef.current?.scrollIntoView({ behavior });
  };

  useEffect(() => {
    scrollToBottom('auto');
  }, []);

  useEffect(() => {
    // Only auto-scroll if user is near bottom
    const container = messagesContainerRef.current;
    if (container) {
      const isNearBottom = container.scrollHeight - container.scrollTop - container.clientHeight < 100;
      if (isNearBottom) {
        scrollToBottom();
      }
    }
  }, [messages]);

  const formatTime = (timestamp) => {
    try {
      // Ensure timestamp is a proper ISO string with timezone
      let isoString = timestamp;
      if (typeof timestamp === 'string') {
        // If timestamp doesn't end with 'Z' or timezone offset, assume UTC
        if (!timestamp.match(/[Z\+\-]\d{2}:\d{2}?$/) && !timestamp.endsWith('Z')) {
          isoString = timestamp + 'Z';
        }
      }

      // Parse the timestamp and convert to local time
      const date = new Date(isoString);

      // Check if date is valid
      if (isNaN(date.getTime())) {
        console.error('Invalid timestamp:', timestamp, 'converted to:', isoString);
        return '';
      }

      // Format in local timezone (HH:mm format shows 24-hour time)
      return format(date, 'HH:mm');
    } catch (error) {
      console.error('Error formatting time:', error, 'for timestamp:', timestamp);
      return '';
    }
  };

  const formatDate = (timestamp) => {
    try {
      // Ensure timestamp is a proper ISO string with timezone
      let isoString = timestamp;
      if (typeof timestamp === 'string') {
        // If timestamp doesn't end with 'Z' or timezone offset, assume UTC
        if (!timestamp.match(/[Z\+\-]\d{2}:\d{2}?$/) && !timestamp.endsWith('Z')) {
          isoString = timestamp + 'Z';
        }
      }

      // Parse the timestamp and convert to local time
      const date = new Date(isoString);

      // Check if date is valid
      if (isNaN(date.getTime())) {
        console.error('Invalid timestamp for date:', timestamp, 'converted to:', isoString);
        return '';
      }

      // Format date in local timezone
      if (isToday(date)) return 'Today';
      if (isYesterday(date)) return 'Yesterday';
      return format(date, 'MMM dd, yyyy');
    } catch (error) {
      console.error('Error formatting date:', error, 'for timestamp:', timestamp);
      return '';
    }
  };

  const shouldShowDateDivider = (currentMsg, previousMsg) => {
    if (!previousMsg) return true;
    const currentDate = new Date(currentMsg.timestamp).toDateString();
    const previousDate = new Date(previousMsg.timestamp).toDateString();
    return currentDate !== previousDate;
  };

  return (
    <div
      ref={messagesContainerRef}
      className="flex-1 overflow-y-auto overscroll-contain scrollbar-hide"
      style={{
        WebkitOverflowScrolling: 'touch',
        scrollBehavior: 'smooth'
      }}
    >
      <div className="px-3 py-4 space-y-1">
        {messages.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full min-h-[300px] text-center px-4">
            <div className="w-16 h-16 bg-blue-50 rounded-full flex items-center justify-center mb-3">
              <svg className="w-8 h-8 text-blue-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
              </svg>
            </div>
            <h3 className="text-base font-semibold text-gray-900 mb-1">No messages yet</h3>
            <p className="text-sm text-gray-500 max-w-xs">
              Be the first to start the conversation!
            </p>
          </div>
        ) : (
          messages.map((message, index) => {
            const isOwnMessage = message.user_id === currentUserId;
            const isSystemMessage = message.type === 'system';
            const showDateDivider = shouldShowDateDivider(message, messages[index - 1]);

            return (
              <div key={`${message.message_id}-${index}`}>
                {/* Date Divider */}
                {showDateDivider && (
                  <div className="flex items-center justify-center my-4">
                    <div className="bg-gray-100 text-gray-600 text-xs font-medium px-3 py-1 rounded-full">
                      {formatDate(message.timestamp)}
                    </div>
                  </div>
                )}

                {/* System Message */}
                {isSystemMessage ? (
                  <div className="flex justify-center my-2">
                    <div className="bg-blue-50 text-blue-700 text-xs px-3 py-1.5 rounded-full max-w-xs text-center">
                      {message.content}
                    </div>
                  </div>
                ) : (
                  /* Regular Message */
                  <div className={`flex gap-2 mb-3 ${isOwnMessage ? 'flex-row-reverse' : 'flex-row'}`}>
                    {/* Avatar - Hide for own messages on mobile */}
                    {!isOwnMessage && (
                      <div className="flex-shrink-0 mt-auto">
                        <Avatar
                          src={message.profile_picture}
                          name={message.user_name}
                          role={message.user_role}
                          size="sm"
                        />
                      </div>
                    )}

                    {/* Message Content */}
                    <div className={`flex flex-col ${isOwnMessage ? 'items-end' : 'items-start'} max-w-[75%] sm:max-w-[70%]`}>
                      {/* Sender Name - Only for others' messages */}
                      {!isOwnMessage && (
                        <div className="flex items-center gap-2 mb-0.5 px-1">
                          <span className="text-xs font-semibold text-gray-700">
                            {message.user_name}
                          </span>
                          {message.user_role && message.user_role !== 'CITIZEN' && (
                            <span className={`text-[10px] px-1.5 py-0.5 rounded font-medium ${
                              message.user_role === 'ADMIN'
                                ? 'bg-red-100 text-red-700'
                                : 'bg-blue-100 text-blue-700'
                            }`}>
                              {message.user_role}
                            </span>
                          )}
                        </div>
                      )}

                      {/* Message Bubble */}
                      <div className={`group relative rounded-2xl px-3 py-2 shadow-sm ${
                        isOwnMessage
                          ? 'bg-blue-500 text-white rounded-tr-sm'
                          : 'bg-white text-gray-900 border border-gray-200 rounded-tl-sm'
                      }`}>
                        {/* Message Text */}
                        <p className="text-[15px] leading-relaxed whitespace-pre-wrap break-words">
                          {message.content}
                        </p>

                        {/* Timestamp & Status */}
                        <div className={`flex items-center gap-1 mt-1 ${
                          isOwnMessage ? 'justify-end' : 'justify-start'
                        }`}>
                          <span className={`text-[11px] ${
                            isOwnMessage ? 'text-blue-100' : 'text-gray-500'
                          }`}>
                            {formatTime(message.timestamp)}
                          </span>

                          {/* Read Receipt (for own messages) */}
                          {isOwnMessage && (
                            <CheckCheck className="w-3 h-3 text-blue-100" />
                          )}

                          {/* Edited Indicator */}
                          {message.edited && (
                            <span className={`text-[10px] italic ${
                              isOwnMessage ? 'text-blue-100' : 'text-gray-400'
                            }`}>
                              edited
                            </span>
                          )}
                        </div>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            );
          })
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Hide scrollbar styles */}
      <style jsx>{`
        .scrollbar-hide {
          -ms-overflow-style: none;  /* IE and Edge */
          scrollbar-width: none;  /* Firefox */
        }
        .scrollbar-hide::-webkit-scrollbar {
          display: none;  /* Chrome, Safari, Opera */
        }
      `}</style>
    </div>
  );
}
