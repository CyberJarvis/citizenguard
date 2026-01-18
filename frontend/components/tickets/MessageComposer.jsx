'use client';

import { useState } from 'react';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import { ThreadSelector } from './ThreadTabs';
import { Send, Paperclip, X } from 'lucide-react';

/**
 * MessageComposer - Input component for sending messages
 * @param {function} onSend - Callback when message is sent (content, thread, attachments)
 * @param {array} allowedThreads - Allowed thread options
 * @param {string} defaultThread - Default thread selection
 * @param {boolean} disabled - Disable the composer
 * @param {string} placeholder - Placeholder text
 */
export function MessageComposer({
  onSend,
  allowedThreads = ['all'],
  defaultThread = 'all',
  disabled = false,
  placeholder = 'Type your message...'
}) {
  const [content, setContent] = useState('');
  const [selectedThread, setSelectedThread] = useState(defaultThread);
  const [attachments, setAttachments] = useState([]);
  const [isSending, setIsSending] = useState(false);

  const handleSend = async () => {
    if (!content.trim() || isSending) return;

    setIsSending(true);
    try {
      await onSend(content.trim(), selectedThread, attachments);
      setContent('');
      setAttachments([]);
    } catch (error) {
      console.error('Failed to send message:', error);
    } finally {
      setIsSending(false);
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleFileSelect = (e) => {
    const files = Array.from(e.target.files || []);
    // In a real app, you'd upload these and get URLs
    setAttachments(prev => [...prev, ...files.map(f => f.name)]);
  };

  const removeAttachment = (index) => {
    setAttachments(prev => prev.filter((_, i) => i !== index));
  };

  return (
    <div className="border-t border-gray-200 bg-white p-4">
      {/* Thread Selector */}
      {allowedThreads.length > 1 && (
        <div className="mb-3">
          <ThreadSelector
            selectedThread={selectedThread}
            onThreadChange={setSelectedThread}
            allowedThreads={allowedThreads}
          />
        </div>
      )}

      {/* Attachments Preview */}
      {attachments.length > 0 && (
        <div className="flex flex-wrap gap-2 mb-3">
          {attachments.map((attachment, idx) => (
            <div
              key={idx}
              className="flex items-center gap-1 px-2 py-1 bg-gray-100 rounded text-sm"
            >
              <span className="truncate max-w-[150px]">{attachment}</span>
              <button
                onClick={() => removeAttachment(idx)}
                className="text-gray-500 hover:text-red-500"
              >
                <X className="w-3 h-3" />
              </button>
            </div>
          ))}
        </div>
      )}

      {/* Input Area */}
      <div className="flex items-end gap-2">
        <div className="flex-1 relative">
          <textarea
            value={content}
            onChange={(e) => setContent(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={placeholder}
            disabled={disabled || isSending}
            rows={1}
            className={cn(
              'w-full px-4 py-3 pr-10 border border-gray-300 rounded-xl',
              'resize-none focus:outline-none focus:ring-2 focus:ring-teal-500 focus:border-transparent',
              'disabled:bg-gray-100 disabled:cursor-not-allowed',
              'min-h-[48px] max-h-[120px]'
            )}
            style={{
              height: 'auto',
              minHeight: '48px'
            }}
            onInput={(e) => {
              e.target.style.height = 'auto';
              e.target.style.height = Math.min(e.target.scrollHeight, 120) + 'px';
            }}
          />

          {/* Attachment Button */}
          <label className="absolute right-3 bottom-3 cursor-pointer text-gray-400 hover:text-gray-600">
            <Paperclip className="w-5 h-5" />
            <input
              type="file"
              multiple
              onChange={handleFileSelect}
              className="hidden"
              disabled={disabled || isSending}
            />
          </label>
        </div>

        {/* Send Button */}
        <Button
          onClick={handleSend}
          disabled={!content.trim() || disabled || isSending}
          className="h-12 w-12 rounded-xl bg-teal-600 hover:bg-teal-700"
        >
          <Send className={cn('w-5 h-5', isSending && 'animate-pulse')} />
        </Button>
      </div>

      {/* Helper Text */}
      <p className="text-xs text-gray-400 mt-2">
        Press Enter to send, Shift+Enter for new line
      </p>
    </div>
  );
}

export default MessageComposer;
