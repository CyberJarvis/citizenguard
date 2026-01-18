'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import useAuthStore from '@/context/AuthContext';
import { getRoleBasedRedirectPath } from '@/lib/api';

export default function Home() {
  const router = useRouter();
  const { isAuthenticated, isLoading, user, initialize } = useAuthStore();

  useEffect(() => {
    initialize();
  }, [initialize]);

  useEffect(() => {
    if (!isLoading) {
      if (isAuthenticated && user) {
        // Redirect authenticated users to their role-based dashboard
        const redirectPath = getRoleBasedRedirectPath(user.role);
        router.replace(redirectPath);
      } else {
        // Redirect unauthenticated users to login page
        router.replace('/login');
      }
    }
  }, [isAuthenticated, isLoading, user, router]);

  // Show loading spinner while checking auth status
  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-[#e8f4fc] to-[#c5e1f5]">
      <div className="text-center">
        <div className="animate-spin rounded-full h-16 w-16 border-t-4 border-b-4 border-[#0d4a6f] mx-auto mb-4"></div>
        <p className="text-[#0d4a6f] font-medium">Loading CoastGuardian...</p>
      </div>
    </div>
  );
}
