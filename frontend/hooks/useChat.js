import { useState, useEffect, useRef, useCallback } from 'react';
import Cookies from 'js-cookie';

const WS_URL = process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:8000';

export function useChat(roomId = 'general') {
  const [messages, setMessages] = useState([]);
  const [onlineUsers, setOnlineUsers] = useState([]);
  const [isConnected, setIsConnected] = useState(false);
  const [isConnecting, setIsConnecting] = useState(false);
  const [error, setError] = useState(null);

  const wsRef = useRef(null);
  const reconnectTimeoutRef = useRef(null);
  const reconnectAttemptsRef = useRef(0);
  const isMountedRef = useRef(true);
  const isConnectingRef = useRef(false);
  const maxReconnectAttempts = 5;

  // Cleanup function to properly close WebSocket
  const cleanup = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }

    if (wsRef.current) {
      // Remove all event handlers before closing to prevent callbacks
      wsRef.current.onopen = null;
      wsRef.current.onmessage = null;
      wsRef.current.onerror = null;
      wsRef.current.onclose = null;

      if (wsRef.current.readyState === WebSocket.OPEN ||
          wsRef.current.readyState === WebSocket.CONNECTING) {
        wsRef.current.close(1000, 'User disconnected');
      }
      wsRef.current = null;
    }

    isConnectingRef.current = false;
  }, []);

  const handleWebSocketMessage = useCallback((data) => {
    if (!isMountedRef.current) return;

    const { type, data: payload } = data;

    switch (type) {
      case 'message':
        // New message received
        setMessages((prev) => {
          // Avoid duplicates
          if (prev.some(msg => msg.message_id === payload.message_id)) {
            return prev;
          }
          return [...prev, payload];
        });
        break;

      case 'join':
        // User joined - only received by OTHER users (not the joiner)
        console.log(`${payload.user_name} joined the chat`);
        break;

      case 'leave':
        // User left - only received by OTHER users (not the leaver)
        console.log(`${payload.user_name} left the chat`);
        break;

      case 'online_users':
        // Update online users list
        setOnlineUsers(payload.users || []);
        break;

      case 'typing':
        // Handle typing indicator (can be implemented later)
        break;

      case 'message_deleted':
        // Remove deleted message
        setMessages((prev) => prev.filter(msg => msg.message_id !== payload.message_id));
        break;

      case 'error':
        console.error('Server error:', payload.message);
        setError(payload.message);
        break;

      default:
        console.log('Unknown message type:', type);
    }
  }, []);

  const connect = useCallback(() => {
    // Prevent multiple simultaneous connections
    if (isConnectingRef.current) {
      console.log('Connection already in progress, skipping');
      return;
    }

    if (wsRef.current?.readyState === WebSocket.OPEN) {
      console.log('Already connected, skipping');
      return;
    }

    if (!isMountedRef.current) {
      console.log('Component unmounted, skipping connection');
      return;
    }

    const token = Cookies.get('access_token');
    if (!token) {
      setError('No authentication token found');
      return;
    }

    // Clean up any existing connection first
    cleanup();

    isConnectingRef.current = true;
    setIsConnecting(true);
    setError(null);

    try {
      console.log('Creating WebSocket connection...');
      const ws = new WebSocket(`${WS_URL}/api/v1/chat/ws?token=${token}&room_id=${roomId}`);

      ws.onopen = () => {
        if (!isMountedRef.current) {
          ws.close(1000, 'Component unmounted');
          return;
        }
        console.log('WebSocket connected');
        setIsConnected(true);
        setIsConnecting(false);
        setError(null);
        isConnectingRef.current = false;
        reconnectAttemptsRef.current = 0;
      };

      ws.onmessage = (event) => {
        if (!isMountedRef.current) return;
        try {
          const data = JSON.parse(event.data);
          handleWebSocketMessage(data);
        } catch (err) {
          console.error('Error parsing WebSocket message:', err);
        }
      };

      ws.onerror = (error) => {
        console.error('WebSocket error:', error);
        if (isMountedRef.current) {
          setError('Connection error occurred');
        }
      };

      ws.onclose = (event) => {
        console.log('WebSocket disconnected', event.code, event.reason);

        if (!isMountedRef.current) {
          return;
        }

        setIsConnected(false);
        setIsConnecting(false);
        isConnectingRef.current = false;
        wsRef.current = null;

        // Only attempt to reconnect if:
        // 1. Not a normal closure (code 1000)
        // 2. Component is still mounted
        // 3. Haven't exceeded max attempts
        if (event.code !== 1000 &&
            isMountedRef.current &&
            reconnectAttemptsRef.current < maxReconnectAttempts) {
          const delay = Math.min(1000 * Math.pow(2, reconnectAttemptsRef.current), 10000);
          console.log(`Reconnecting in ${delay}ms... (attempt ${reconnectAttemptsRef.current + 1})`);

          setError('Connection lost. Reconnecting...');

          reconnectTimeoutRef.current = setTimeout(() => {
            if (isMountedRef.current) {
              reconnectAttemptsRef.current++;
              connect();
            }
          }, delay);
        } else if (reconnectAttemptsRef.current >= maxReconnectAttempts) {
          setError('Failed to connect after multiple attempts. Please refresh the page.');
        }
      };

      wsRef.current = ws;
    } catch (err) {
      console.error('Error creating WebSocket:', err);
      setError('Failed to create connection');
      setIsConnecting(false);
      isConnectingRef.current = false;
    }
  }, [roomId, cleanup, handleWebSocketMessage]);

  const sendMessage = useCallback((content) => {
    if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) {
      console.error('WebSocket is not connected');
      return false;
    }

    if (!content || !content.trim()) {
      return false;
    }

    try {
      wsRef.current.send(JSON.stringify({
        type: 'message',
        content: content.trim()
      }));
      return true;
    } catch (err) {
      console.error('Error sending message:', err);
      return false;
    }
  }, []);

  
  const sendTyping = useCallback((isTyping) => {
    if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) {
      return;
    }

    try {
      wsRef.current.send(JSON.stringify({
        type: 'typing',
        is_typing: isTyping
      }));
    } catch (err) {
      console.error('Error sending typing indicator:', err);
    }
  }, []);

  const disconnect = useCallback(() => {
    cleanup();
    setIsConnected(false);
    setMessages([]);
    setOnlineUsers([]);
  }, [cleanup]);

  // Auto-connect on mount with proper cleanup
  useEffect(() => {
    isMountedRef.current = true;
    reconnectAttemptsRef.current = 0;

    // Small delay to handle React Strict Mode double-mount
    const connectTimeout = setTimeout(() => {
      if (isMountedRef.current) {
        connect();
      }
    }, 100);

    return () => {
      isMountedRef.current = false;
      clearTimeout(connectTimeout);
      cleanup();
    };
  }, [roomId]); // Only depend on roomId, not connect/cleanup to avoid loops

  return {
    messages,
    onlineUsers,
    isConnected,
    isConnecting,
    error,
    sendMessage,
    sendTyping,
    connect,
    disconnect,
    setMessages // Allow setting messages from API
  };
}
