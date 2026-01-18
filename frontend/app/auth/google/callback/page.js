'use client';

import { useEffect, useState, Suspense } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import useAuthStore from '@/context/AuthContext';
import { getRoleBasedRedirectPath } from '@/lib/api';
import { Waves, AlertCircle } from 'lucide-react';

// Loading fallback component
function LoadingFallback() {
  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-sky-50 via-blue-50 to-cyan-100 px-4">
      <div className="max-w-md w-full">
        <div className="bg-white rounded-2xl shadow-xl p-8">
          <div className="text-center">
            <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl shadow-lg mb-4 bg-gradient-to-br from-sky-500 to-blue-600">
              <Waves className="w-8 h-8 text-white" />
            </div>
            <h2 className="text-2xl font-bold text-gray-900 mb-3">Loading...</h2>
            <p className="text-gray-600 mb-6">Please wait while we process your request...</p>
            <div className="animate-spin rounded-full h-12 w-12 border-t-4 border-b-4 border-sky-500 mx-auto"></div>
          </div>
        </div>
      </div>
    </div>
  );
}

// Main callback handler component
function GoogleCallbackHandler() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { handleGoogleCallback } = useAuthStore();
  const [error, setError] = useState(null);
  const [isProcessing, setIsProcessing] = useState(true);

  useEffect(() => {
    const handleCallback = async () => {
      try {
        const code = searchParams.get('code');
        const state = searchParams.get('state');
        const errorParam = searchParams.get('error');

        // Handle OAuth errors from Google
        if (errorParam) {
          const errorDescription = searchParams.get('error_description') || 'Google login cancelled or failed';
          console.error('Google OAuth error:', errorParam, errorDescription);
          setError(errorDescription);
          setIsProcessing(false);
          setTimeout(() => router.push('/login'), 5000);
          return;
        }

        // Validate required parameters
        if (!code) {
          console.error('Missing authorization code from Google');
          setError('Invalid callback: missing authorization code');
          setIsProcessing(false);
          setTimeout(() => router.push('/login'), 5000);
          return;
        }

        console.log('Processing Google OAuth callback...');
        console.log('Code received:', code.substring(0, 10) + '...');
        console.log('State received:', state);

        // Call backend to complete authentication
        const { success, error: authError, user: loggedInUser } = await handleGoogleCallback(code, state);

        if (success) {
          console.log('Google authentication successful, redirecting...');
          setIsProcessing(false);
          // Redirect based on user role using utility function
          const redirectPath = getRoleBasedRedirectPath(loggedInUser?.role);
          router.push(redirectPath);
        } else {
          console.error('Google authentication failed:', authError);

          // Ensure authError is a string
          let errorMsg = 'Google login failed. Please try again.';
          if (authError) {
            if (typeof authError === 'string') {
              errorMsg = authError;
            } else if (typeof authError === 'object') {
              errorMsg = authError.message || authError.error || JSON.stringify(authError);
            }
          }

          console.error('Setting error message:', errorMsg);
          setError(errorMsg);
          setIsProcessing(false);
          setTimeout(() => router.push('/login'), 5000);
        }
      } catch (err) {
        console.error('Unexpected error during Google callback:', err);

        // Ensure error is a string
        let errorMsg = 'An unexpected error occurred during authentication';
        if (err) {
          if (typeof err === 'string') {
            errorMsg = err;
          } else if (err.message) {
            errorMsg = err.message;
          } else if (typeof err === 'object') {
            errorMsg = JSON.stringify(err);
          }
        }

        setError(errorMsg);
        setIsProcessing(false);
        setTimeout(() => router.push('/login'), 5000);
      }
    };

    handleCallback();
  }, [searchParams, handleGoogleCallback, router]);

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-sky-50 via-blue-50 to-cyan-100 px-4">
      <div className="max-w-md w-full">
        <div className="bg-white rounded-2xl shadow-xl p-8">
          <div className="text-center">
            <div className={`inline-flex items-center justify-center w-16 h-16 rounded-2xl shadow-lg mb-4 ${
              error ? 'bg-gradient-to-br from-red-500 to-red-600' : 'bg-gradient-to-br from-sky-500 to-blue-600'
            }`}>
              {error ? (
                <AlertCircle className="w-8 h-8 text-white" />
              ) : (
                <Waves className="w-8 h-8 text-white" />
              )}
            </div>

            {error ? (
              <div>
                <h2 className="text-2xl font-bold text-red-600 mb-3">Authentication Failed</h2>
                <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-4">
                  <p className="text-sm text-red-800 break-words">
                    {typeof error === 'string' ? error : 'An error occurred during authentication'}
                  </p>
                </div>

                {/* Show helpful hint about redirect URI */}
                {error && typeof error === 'string' && (error.includes('redirect') || error.includes('400')) && (
                  <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4 mb-4">
                    <p className="text-xs text-yellow-800">
                      <strong>Possible fix:</strong> Ensure Google Cloud Console has the redirect URI:
                      <code className="ml-1 px-1 bg-yellow-100 rounded">http://localhost:3000/auth/google/callback</code>
                    </p>
                  </div>
                )}

                <p className="text-sm text-gray-500 mb-4">Redirecting to login page in 5 seconds...</p>
                <button
                  onClick={() => router.push('/login')}
                  className="text-sm font-medium text-sky-600 hover:text-sky-500 underline"
                >
                  Return to login now
                </button>
              </div>
            ) : (
              <div>
                <h2 className="text-2xl font-bold text-gray-900 mb-3">
                  {isProcessing ? 'Completing Sign In' : 'Redirecting...'}
                </h2>
                <p className="text-gray-600 mb-6">
                  {isProcessing
                    ? 'Please wait while we authenticate you with Google...'
                    : 'Authentication successful! Redirecting to dashboard...'
                  }
                </p>
                <div className="animate-spin rounded-full h-12 w-12 border-t-4 border-b-4 border-sky-500 mx-auto"></div>
                <p className="text-xs text-gray-400 mt-4">This may take a few seconds</p>
              </div>
            )}
          </div>
        </div>

        {/* Debug info in development */}
        {process.env.NODE_ENV === 'development' && (
          <div className="mt-4 p-3 bg-gray-800 text-white text-xs rounded-lg font-mono overflow-auto max-h-32">
            <div>Code: {searchParams.get('code')?.substring(0, 20)}...</div>
            <div>State: {searchParams.get('state')?.substring(0, 20) || 'none'}</div>
            <div>Error param: {searchParams.get('error') || 'none'}</div>
          </div>
        )}
      </div>
    </div>
  );
}

// Default export with Suspense boundary
export default function GoogleCallbackPage() {
  return (
    <Suspense fallback={<LoadingFallback />}>
      <GoogleCallbackHandler />
    </Suspense>
  );
}
