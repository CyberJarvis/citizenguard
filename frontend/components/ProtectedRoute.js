/**
 * Protected Route Component
 * Redirects to login if user is not authenticated
 */

'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import useAuthStore from '@/context/AuthContext';
import Cookies from 'js-cookie';

// Global flag to prevent multiple initializations across component re-renders
let isInitializing = false;
let hasInitialized = false;

export default function ProtectedRoute({ children, requiredRole = null }) {
  const router = useRouter();
  const { isAuthenticated, isLoading, user, initialize } = useAuthStore();
  const [isReady, setIsReady] = useState(hasInitialized);

  useEffect(() => {
    // If already initialized globally, just mark as ready
    if (hasInitialized) {
      setIsReady(true);
      return;
    }

    // Prevent concurrent initializations
    if (isInitializing) {
      // Wait for the ongoing initialization
      const checkReady = setInterval(() => {
        if (hasInitialized) {
          clearInterval(checkReady);
          setIsReady(true);
        }
      }, 50);
      return () => clearInterval(checkReady);
    }

    const doInit = async () => {
      isInitializing = true;

      // Check if already authenticated from persisted state
      const currentState = useAuthStore.getState();
      if (currentState.user && currentState.isAuthenticated) {
        hasInitialized = true;
        isInitializing = false;
        setIsReady(true);
        return;
      }

      // Check for token and initialize
      const hasToken = !!Cookies.get('access_token');
      if (hasToken) {
        await initialize();
      } else {
        // No token, mark loading as false
        useAuthStore.setState({ isLoading: false });
      }

      hasInitialized = true;
      isInitializing = false;
      setIsReady(true);
    };

    doInit();
  }, [initialize]);

  useEffect(() => {
    // Only check auth after initialization is complete
    if (!isReady || isLoading) return;

    // Check if we have a token
    const hasToken = !!Cookies.get('access_token');

    // If no token and not authenticated, redirect to login
    if (!isAuthenticated && !hasToken) {
      router.push('/login');
      return;
    }

    // Check role if required
    if (isAuthenticated && requiredRole && user?.role !== requiredRole) {
      router.push('/unauthorized');
    }
  }, [isAuthenticated, isLoading, user, requiredRole, router, isReady]);

  // Show loading spinner while checking auth
  if (!isReady || isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-sky-50 to-blue-100">
        <div className="text-center">
          <div className="animate-spin rounded-full h-16 w-16 border-t-4 border-b-4 border-sky-500 mx-auto mb-4"></div>
          <p className="text-gray-600 font-medium">Loading...</p>
        </div>
      </div>
    );
  }

  // Don't render children if not authenticated
  if (!isAuthenticated) {
    return null;
  }

  return <>{children}</>;
}
