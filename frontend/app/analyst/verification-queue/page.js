'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';

/**
 * Verification Queue Redirect Page
 * Redirects to the unified Reports page with queue tab active
 */
export default function VerificationQueueRedirect() {
  const router = useRouter();

  useEffect(() => {
    // Redirect to the unified reports page
    // The reports page now has a "Verification Queue" tab built-in
    router.replace('/analyst/reports?tab=queue');
  }, [router]);

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50">
      <div className="text-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
        <p className="text-gray-600">Redirecting to Reports...</p>
      </div>
    </div>
  );
}
