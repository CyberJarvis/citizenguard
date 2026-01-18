'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import ProtectedRoute from '@/components/ProtectedRoute';
import DashboardLayout from '@/components/DashboardLayout';
import MessageList from '@/components/chat/MessageList';
import MessageInput from '@/components/chat/MessageInput';
import OnlineUsers from '@/components/chat/OnlineUsers';
import { useChat } from '@/hooks/useChat';
import { getChatMessages } from '@/lib/api';
import { Users, Wifi, WifiOff, Loader2, ArrowLeft } from 'lucide-react';
import toast from 'react-hot-toast';
import Cookies from 'js-cookie';
import { jwtDecode } from 'jwt-decode';

function CommunityContent() {
  const [currentUser, setCurrentUser] = useState(null);
  const [isLoadingHistory, setIsLoadingHistory] = useState(true);
  const [showOnlineUsers, setShowOnlineUsers] = useState(false);
  const roomId = 'general';

  const {
    messages,
    onlineUsers,
    isConnected,
    isConnecting,
    error,
    sendMessage,
    setMessages
  } = useChat(roomId);

  // Get current user from token
  useEffect(() => {
    const token = Cookies.get('access_token');
    if (token) {
      try {
        const decoded = jwtDecode(token);
        setCurrentUser({
          user_id: decoded.sub || decoded.user_id,
          name: decoded.name || decoded.user_name || 'User',
          role: (decoded.role || 'CITIZEN').toUpperCase()
        });
      } catch (err) {
        console.error('Error decoding token:', err);
      }
    }
  }, []);

  // Load message history
  useEffect(() => {
    const loadHistory = async () => {
      try {
        setIsLoadingHistory(true);
        const response = await getChatMessages(roomId, 1, 50);
        if (response.messages) {
          setMessages(prev => {
            if (prev.length === 0) {
              return response.messages;
            }
            const existingIds = new Set(prev.map(msg => msg.message_id));
            const newHistoryMessages = response.messages.filter(msg => !existingIds.has(msg.message_id));
            return [...newHistoryMessages, ...prev].sort((a, b) => new Date(a.timestamp) - new Date(b.timestamp));
          });
        }
      } catch (err) {
        console.error('Error loading message history:', err);
        toast.error('Failed to load message history');
      } finally {
        setIsLoadingHistory(false);
      }
    };

    loadHistory();
  }, [roomId, setMessages]);

  // Show error toast when connection error occurs
  useEffect(() => {
    if (error) {
      toast.error(error);
    }
  }, [error]);

  // Show success toast when connected
  useEffect(() => {
    if (isConnected && !isConnecting && currentUser) {
      toast.success(`Welcome, ${currentUser.name}!`, { duration: 2000 });
    }
  }, [isConnected, isConnecting, currentUser]);

  const handleSendMessage = (content) => {
    const success = sendMessage(content);
    if (!success) {
      toast.error('Failed to send message');
    }
    return success;
  };

  const ConnectionStatus = () => {
    if (isConnecting) {
      return (
        <div className="flex items-center gap-2 px-3 py-1.5 bg-yellow-50 text-yellow-700 rounded-full text-xs font-medium">
          <Loader2 className="w-3.5 h-3.5 animate-spin" />
          <span>Connecting...</span>
        </div>
      );
    }

    if (isConnected) {
      return (
        <div className="flex items-center gap-2 px-3 py-1.5 bg-green-50 text-green-700 rounded-full text-xs font-medium">
          <Wifi className="w-3.5 h-3.5" />
          <span className="hidden sm:inline">Connected</span>
        </div>
      );
    }

    return (
      <div className="flex items-center gap-2 px-3 py-1.5 bg-red-50 text-red-700 rounded-full text-xs font-medium">
        <WifiOff className="w-3.5 h-3.5" />
        <span className="hidden sm:inline">Disconnected</span>
      </div>
    );
  };

  return (
    <div className="h-[calc(100vh-4rem)] sm:h-[calc(100vh-5rem)] flex flex-col bg-gray-50">
      {/* Mobile-optimized Header */}
      <div className="flex-shrink-0 bg-white border-b border-gray-200 safe-area-top">
        <div className="px-3 py-3 sm:px-4 sm:py-4">
          <div className="flex items-center justify-between">
            {/* Back Button & Title */}
            <div className="flex items-center gap-3 flex-1 min-w-0">
              <Link
                href="/community"
                className="flex items-center justify-center w-8 h-8 rounded-full hover:bg-gray-100 transition-colors"
              >
                <ArrowLeft className="w-5 h-5 text-gray-600" />
              </Link>
              <div>
                <h1 className="text-base sm:text-lg font-bold text-gray-900 truncate">
                  Community Chat
                </h1>
                <p className="text-xs sm:text-sm text-gray-600 truncate">
                  Ocean safety discussions
                </p>
              </div>
            </div>

            {/* Action Buttons */}
            <div className="flex items-center gap-2 sm:gap-3 ml-3">
              <ConnectionStatus />

              {/* Online Users Button (Mobile) */}
              <button
                onClick={() => setShowOnlineUsers(true)}
                className="lg:hidden relative flex items-center gap-2 px-3 py-1.5 bg-blue-50 text-blue-700 rounded-full text-xs font-medium hover:bg-blue-100 transition-colors active:scale-95"
              >
                <Users className="w-3.5 h-3.5" />
                <span className="font-semibold">{onlineUsers.length}</span>
                {onlineUsers.length > 0 && (
                  <div className="absolute -top-1 -right-1 w-2.5 h-2.5 bg-green-500 border-2 border-white rounded-full" />
                )}
              </button>
            </div>
          </div>
        </div>

        {/* Connection Banner (when disconnected) */}
        {!isConnected && !isConnecting && (
          <div className="px-3 pb-2 sm:px-4">
            <div className="bg-red-50 border border-red-200 rounded-lg px-3 py-2 flex items-center gap-2">
              <WifiOff className="w-4 h-4 text-red-600 flex-shrink-0" />
              <p className="text-xs text-red-700 flex-1">
                Connection lost. Attempting to reconnect...
              </p>
            </div>
          </div>
        )}
      </div>

      {/* Messages Container */}
      <div className="flex-1 flex overflow-hidden">
        <div className="flex-1 flex flex-col bg-gray-50">
          {/* Loading State */}
          {isLoadingHistory ? (
            <div className="flex-1 flex items-center justify-center">
              <div className="text-center">
                <Loader2 className="w-10 h-10 text-blue-600 animate-spin mx-auto mb-3" />
                <p className="text-sm text-gray-600 font-medium">Loading messages...</p>
              </div>
            </div>
          ) : (
            <MessageList messages={messages} currentUserId={currentUser?.user_id} />
          )}

          {/* Message Input (Sticky at bottom) */}
          <div className="flex-shrink-0">
            <MessageInput
              onSendMessage={handleSendMessage}
              disabled={!isConnected || isConnecting}
            />
          </div>
        </div>

        {/* Online Users - Desktop Sidebar / Mobile Modal */}
        <OnlineUsers
          users={onlineUsers}
          isConnected={isConnected}
          isOpen={showOnlineUsers}
          onClose={() => setShowOnlineUsers(false)}
        />
      </div>

      {/* PWA-style safe area padding */}
      <style jsx global>{`
        .safe-area-top {
          padding-top: env(safe-area-inset-top);
        }
      `}</style>
    </div>
  );
}

export default function CommunityPage() {
  return (
    <ProtectedRoute>
      <DashboardLayout>
        <CommunityContent />
      </DashboardLayout>
    </ProtectedRoute>
  );
}
