'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';

export default function OfflinePage() {
  const router = useRouter();
  const [isOnline, setIsOnline] = useState(false);

  useEffect(() => {
    setIsOnline(navigator.onLine);

    const handleOnline = () => {
      setIsOnline(true);
      // Auto-redirect when back online
      setTimeout(() => {
        router.back();
      }, 1500);
    };

    const handleOffline = () => {
      setIsOnline(false);
    };

    window.addEventListener('online', handleOnline);
    window.addEventListener('offline', handleOffline);

    return () => {
      window.removeEventListener('online', handleOnline);
      window.removeEventListener('offline', handleOffline);
    };
  }, [router]);

  const handleRetry = () => {
    if (navigator.onLine) {
      router.back();
    } else {
      window.location.reload();
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-[#e8f4fc] to-[#c5e1f5] flex items-center justify-center p-4">
      <div className="max-w-md w-full bg-white rounded-2xl shadow-xl p-8 text-center">
        {/* Logo */}
        <div className="mb-6">
          <div className="w-24 h-24 mx-auto bg-[#e8f4fc] rounded-full flex items-center justify-center">
            <svg
              className="w-14 h-14 text-[#0d4a6f]"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={1.5}
                d="M18.364 5.636a9 9 0 010 12.728m0 0l-2.829-2.829m2.829 2.829L21 21M15.536 8.464a5 5 0 010 7.072m0 0l-2.829-2.829m-4.243 2.829a5 5 0 01-7.072-7.072m7.072 7.072L9 12m0 0L6.172 9.172m0 0a5 5 0 017.071-7.071M9 12l2.829 2.829"
              />
            </svg>
          </div>
        </div>

        {/* Status */}
        {isOnline ? (
          <>
            <div className="mb-4">
              <span className="inline-flex items-center px-3 py-1 rounded-full text-sm font-medium bg-green-100 text-green-800">
                <span className="w-2 h-2 bg-green-500 rounded-full mr-2 animate-pulse"></span>
                Back Online
              </span>
            </div>
            <h1 className="text-2xl font-bold text-[#0d4a6f] mb-2">
              Connection Restored!
            </h1>
            <p className="text-gray-600 mb-6">
              Redirecting you back...
            </p>
            <div className="flex justify-center">
              <div className="animate-spin rounded-full h-8 w-8 border-t-2 border-b-2 border-[#0d4a6f]"></div>
            </div>
          </>
        ) : (
          <>
            <div className="mb-4">
              <span className="inline-flex items-center px-3 py-1 rounded-full text-sm font-medium bg-amber-100 text-amber-800">
                <span className="w-2 h-2 bg-amber-500 rounded-full mr-2"></span>
                Offline Mode
              </span>
            </div>
            <h1 className="text-2xl font-bold text-[#0d4a6f] mb-2">
              You're Offline
            </h1>
            <p className="text-gray-600 mb-6">
              Don't worry! Your data is safe. You can still view cached content and any reports you submit will be saved and synced when you're back online.
            </p>

            {/* Features available offline */}
            <div className="bg-[#f0f9ff] rounded-lg p-4 mb-6 text-left">
              <h3 className="font-semibold text-[#0d4a6f] mb-3 text-sm">Available Offline:</h3>
              <ul className="space-y-2 text-sm text-gray-700">
                <li className="flex items-center">
                  <svg className="w-4 h-4 mr-2 text-green-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                  </svg>
                  View cached hazard reports
                </li>
                <li className="flex items-center">
                  <svg className="w-4 h-4 mr-2 text-green-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                  </svg>
                  Submit new reports (queued)
                </li>
                <li className="flex items-center">
                  <svg className="w-4 h-4 mr-2 text-green-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                  </svg>
                  View your profile
                </li>
                <li className="flex items-center">
                  <svg className="w-4 h-4 mr-2 text-green-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                  </svg>
                  Browse cached map tiles
                </li>
              </ul>
            </div>

            {/* Retry button */}
            <button
              onClick={handleRetry}
              className="w-full bg-[#0d4a6f] hover:bg-[#083a57] text-white font-semibold py-3 px-6 rounded-lg transition-colors duration-200 flex items-center justify-center"
            >
              <svg className="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
              </svg>
              Try Again
            </button>

            <p className="text-xs text-gray-500 mt-4">
              We'll automatically reconnect when your internet is back.
            </p>
          </>
        )}

        {/* Branding */}
        <div className="mt-8 pt-6 border-t border-gray-100">
          <p className="text-sm text-[#0d4a6f] font-medium">CoastGuardian</p>
          <p className="text-xs text-gray-500">Protecting Coastal Communities</p>
        </div>
      </div>
    </div>
  );
}
