'use client';

import { useState, useEffect } from 'react';
import { X, Users, Loader2, WifiOff, MessageCircle } from 'lucide-react';
import { useChat } from '@/hooks/useChat';
import MessageList from './MessageList';
import MessageInput from './MessageInput';
import Cookies from 'js-cookie';
import { jwtDecode } from 'jwt-decode';

export default function ChatModal({ isOpen, onClose }) {
  const [currentUserId, setCurrentUserId] = useState(null);
  const [showOnlineUsers, setShowOnlineUsers] = useState(false);
  const [isAuthenticated, setIsAuthenticated] = useState(false);

  const {
    messages,
    onlineUsers,
    isConnected,
    isConnecting,
    error,
    sendMessage,
    connect
  } = useChat('general');

  // Check authentication
  useEffect(() => {
    const token = Cookies.get('access_token');
    if (token) {
      try {
        const decoded = jwtDecode(token);
        setCurrentUserId(decoded.sub || decoded.user_id);
        setIsAuthenticated(true);
      } catch (err) {
        console.error('Error decoding token:', err);
        setIsAuthenticated(false);
      }
    } else {
      setIsAuthenticated(false);
    }
  }, [isOpen]);

  // Prevent body scroll when modal is open
  useEffect(() => {
    if (isOpen) {
      document.body.style.overflow = 'hidden';
    } else {
      document.body.style.overflow = '';
    }
    return () => {
      document.body.style.overflow = '';
    };
  }, [isOpen]);

  if (!isOpen) return null;

  return (
    <>
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-black/50 z-50 transition-opacity"
        onClick={onClose}
      />

      {/* Modal */}
      <div className="fixed bottom-6 right-6 z-50 w-[400px] h-[600px] max-w-[calc(100vw-48px)] max-h-[calc(100vh-100px)] bg-white rounded-2xl shadow-2xl flex flex-col overflow-hidden animate-scale-up">
        {/* Header */}
        <div className="bg-gradient-to-r from-blue-600 to-blue-700 text-white px-4 py-3 flex items-center justify-between flex-shrink-0">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-white/20 rounded-full flex items-center justify-center">
              <MessageCircle className="w-5 h-5" />
            </div>
            <div>
              <h2 className="font-semibold text-lg">Community Chat</h2>
              <div className="flex items-center gap-2 text-xs text-blue-100">
                {isConnected ? (
                  <>
                    <span className="w-2 h-2 bg-green-400 rounded-full animate-pulse" />
                    <span>{onlineUsers.length} online</span>
                  </>
                ) : isConnecting ? (
                  <>
                    <Loader2 className="w-3 h-3 animate-spin" />
                    <span>Connecting...</span>
                  </>
                ) : (
                  <>
                    <WifiOff className="w-3 h-3" />
                    <span>Disconnected</span>
                  </>
                )}
              </div>
            </div>
          </div>

          <div className="flex items-center gap-2">
            {/* Online Users Button */}
            <button
              onClick={() => setShowOnlineUsers(!showOnlineUsers)}
              className="w-9 h-9 rounded-full bg-white/20 hover:bg-white/30 flex items-center justify-center transition-colors"
            >
              <Users className="w-5 h-5" />
            </button>

            {/* Close Button */}
            <button
              onClick={onClose}
              className="w-9 h-9 rounded-full bg-white/20 hover:bg-white/30 flex items-center justify-center transition-colors"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* Online Users Dropdown */}
        {showOnlineUsers && (
          <div className="absolute top-16 right-4 w-64 bg-white rounded-lg shadow-xl border border-gray-200 z-10 max-h-64 overflow-y-auto">
            <div className="p-3 border-b border-gray-100">
              <div className="flex items-center justify-between">
                <span className="text-sm font-semibold text-gray-700">Online Users</span>
                <span className="text-xs bg-green-100 text-green-700 px-2 py-0.5 rounded-full">
                  {onlineUsers.length}
                </span>
              </div>
            </div>
            <div className="p-2">
              {onlineUsers.length === 0 ? (
                <p className="text-sm text-gray-500 text-center py-4">No users online</p>
              ) : (
                onlineUsers.map((user) => (
                  <div
                    key={user.user_id}
                    className="flex items-center gap-2 p-2 rounded-lg hover:bg-gray-50"
                  >
                    <div className="relative">
                      <div className="w-8 h-8 bg-blue-500 rounded-full flex items-center justify-center text-white text-xs font-semibold">
                        {user.user_name?.charAt(0)?.toUpperCase() || '?'}
                      </div>
                      <div className="absolute -bottom-0.5 -right-0.5 w-3 h-3 bg-green-500 border-2 border-white rounded-full" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium text-gray-800 truncate">
                        {user.user_name}
                      </p>
                      {user.user_role && user.user_role !== 'CITIZEN' && (
                        <span className="text-xs text-blue-600">{user.user_role}</span>
                      )}
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>
        )}

        {/* Chat Content */}
        {!isAuthenticated ? (
          <div className="flex-1 flex flex-col items-center justify-center p-6 text-center bg-gray-50">
            <div className="w-16 h-16 bg-blue-100 rounded-full flex items-center justify-center mb-4">
              <MessageCircle className="w-8 h-8 text-blue-600" />
            </div>
            <h3 className="text-lg font-semibold text-gray-800 mb-2">Join the Conversation</h3>
            <p className="text-sm text-gray-600 mb-4">
              Sign in to chat with other CoastGuardians members
            </p>
            <a
              href="/auth/login"
              className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition"
            >
              Sign In
            </a>
          </div>
        ) : (
          <>
            {/* Error Banner */}
            {error && (
              <div className="px-4 py-2 bg-red-50 border-b border-red-100 flex items-center justify-between">
                <span className="text-sm text-red-600">{error}</span>
                {!isConnected && !isConnecting && (
                  <button
                    onClick={connect}
                    className="text-xs text-red-600 hover:text-red-800 underline"
                  >
                    Retry
                  </button>
                )}
              </div>
            )}

            {/* Messages */}
            <div className="flex-1 bg-gray-50 overflow-hidden">
              <MessageList messages={messages} currentUserId={currentUserId} />
            </div>

            {/* Message Input */}
            <MessageInput onSendMessage={sendMessage} disabled={!isConnected} />
          </>
        )}
      </div>

      <style jsx>{`
        @keyframes scale-up {
          from {
            opacity: 0;
            transform: scale(0.9) translateY(20px);
          }
          to {
            opacity: 1;
            transform: scale(1) translateY(0);
          }
        }
        .animate-scale-up {
          animation: scale-up 0.2s ease-out;
        }
      `}</style>
    </>
  );
}
