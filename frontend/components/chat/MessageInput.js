'use client';

import { useState, useRef, useEffect } from 'react';
import { Send, Loader2 } from 'lucide-react';

export default function MessageInput({ onSendMessage, disabled }) {
  const [message, setMessage] = useState('');
  const [isSending, setIsSending] = useState(false);
  const [rows, setRows] = useState(1);
  const inputRef = useRef(null);
  const maxRows = 5;

  useEffect(() => {
    // Auto-focus on desktop, not on mobile to avoid keyboard popup
    if (window.innerWidth >= 768) {
      inputRef.current?.focus();
    }
  }, []);

  const handleSubmit = async (e) => {
    e.preventDefault();

    if (!message.trim() || disabled || isSending) {
      return;
    }

    setIsSending(true);

    try {
      const success = onSendMessage(message);
      if (success) {
        setMessage('');
        setRows(1);
        // Re-focus after sending (better UX)
        setTimeout(() => inputRef.current?.focus(), 50);
      }
    } finally {
      setIsSending(false);
    }
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  const handleChange = (e) => {
    const value = e.target.value;
    setMessage(value);

    // Auto-resize textarea
    const lineCount = value.split('\n').length;
    setRows(Math.min(lineCount, maxRows));
  };

  const charCount = message.length;
  const maxChars = 2000;
  const isNearLimit = charCount > maxChars * 0.8;
  const isOverLimit = charCount > maxChars;

  return (
    <div className="border-t border-gray-200 bg-white">
      <div className="px-3 py-3 sm:px-4 sm:py-4">
        <form onSubmit={handleSubmit} className="flex items-end gap-2">
          {/* Message Input */}
          <div className="flex-1 relative">
            <textarea
              ref={inputRef}
              value={message}
              onChange={handleChange}
              onKeyPress={handleKeyPress}
              placeholder={disabled ? 'Connecting...' : 'Message'}
              disabled={disabled || isSending}
              rows={rows}
              className={`w-full px-4 py-3 pr-12 bg-gray-50 border rounded-3xl resize-none focus:outline-none focus:ring-2 transition-all text-[15px] ${
                disabled || isSending
                  ? 'border-gray-200 bg-gray-100 cursor-not-allowed text-gray-400'
                  : isOverLimit
                  ? 'border-red-300 focus:border-red-500 focus:ring-red-500/20'
                  : 'border-gray-300 focus:border-blue-500 focus:ring-blue-500/20'
              }`}
              style={{
                minHeight: '48px',
                maxHeight: `${maxRows * 24 + 24}px`
              }}
            />

            {/* Character Counter (shown when typing) */}
            {charCount > 0 && (
              <div
                className={`absolute bottom-2 right-3 text-xs font-medium transition-colors ${
                  isOverLimit
                    ? 'text-red-500'
                    : isNearLimit
                    ? 'text-orange-500'
                    : 'text-gray-400'
                }`}
              >
                {isNearLimit && `${charCount}/${maxChars}`}
              </div>
            )}
          </div>

          {/* Send Button */}
          <button
            type="submit"
            disabled={disabled || !message.trim() || isOverLimit || isSending}
            className={`flex-shrink-0 w-12 h-12 rounded-full flex items-center justify-center transition-all duration-200 ${
              disabled || !message.trim() || isOverLimit || isSending
                ? 'bg-gray-200 text-gray-400 cursor-not-allowed'
                : 'bg-blue-500 text-white hover:bg-blue-600 active:scale-95 shadow-lg shadow-blue-500/30'
            }`}
          >
            {isSending ? (
              <Loader2 className="w-5 h-5 animate-spin" />
            ) : (
              <Send className="w-5 h-5" />
            )}
          </button>
        </form>

        {/* Helper Text */}
        {!disabled && (
          <div className="mt-2 px-1">
            <p className="text-xs text-gray-500 hidden sm:block">
              Press <kbd className="px-1.5 py-0.5 bg-gray-100 border border-gray-300 rounded text-xs font-mono">Enter</kbd> to send, <kbd className="px-1.5 py-0.5 bg-gray-100 border border-gray-300 rounded text-xs font-mono">Shift+Enter</kbd> for new line
            </p>
            {isOverLimit && (
              <p className="text-xs text-red-500 sm:hidden">
                Message is too long ({charCount - maxChars} over limit)
              </p>
            )}
          </div>
        )}
      </div>

      {/* Safe area padding for mobile devices with notches */}
      <div className="h-[env(safe-area-inset-bottom)] bg-white" />
    </div>
  );
}
