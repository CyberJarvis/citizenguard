'use client';

import Link from 'next/link';
import { MessageCircle } from 'lucide-react';

export default function FloatingChatButton() {
  return (
    <Link
      href="/community/chat"
      className="fixed bottom-6 right-6 z-40 w-14 h-14 bg-blue-600 text-white rounded-full shadow-lg hover:bg-blue-700 transition-all duration-300 flex items-center justify-center group hover:scale-105 active:scale-95"
      aria-label="Open Community Chat"
    >
      <MessageCircle className="w-6 h-6" />
      {/* Pulse animation */}
      <span className="absolute w-full h-full rounded-full bg-blue-600 animate-ping opacity-30" />
    </Link>
  );
}
