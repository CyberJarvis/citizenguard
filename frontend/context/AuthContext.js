/**
 * Authentication Context using Zustand
 * Global state management for user authentication
 */

import { create } from 'zustand';
import { persist, createJSONStorage } from 'zustand/middleware';
import Cookies from 'js-cookie';
import {
  getCurrentUser,
  logout as apiLogout,
  loginWithPassword as apiLoginWithPassword,
  loginWithOTP as apiLoginWithOTP,
  signup as apiSignup,
  handleGoogleCallback as apiHandleGoogleCallback,
} from '@/lib/api';

const useAuthStore = create(
  persist(
    (set, get) => ({
      // State
      user: null,
      isAuthenticated: false,
      isLoading: false, // Start as false - ProtectedRoute manages loading state
      error: null,

      // Actions

      /**
       * Set user and authentication status
       */
      setUser: (user) => {
        set({
          user,
          isAuthenticated: !!user,
          error: null,
        });
      },

      /**
       * Set loading state
       */
      setLoading: (isLoading) => {
        set({ isLoading });
      },

      /**
       * Set error
       */
      setError: (error) => {
        set({ error });
      },

      /**
       * Clear error
       */
      clearError: () => {
        set({ error: null });
      },

      /**
       * Initialize auth - Check if user is logged in
       * IMPORTANT: Does not overwrite existing authenticated state
       */
      initialize: async () => {
        const currentState = get();

        // If user is already authenticated, just mark as loaded and return
        // This prevents race condition with Google OAuth callback
        if (currentState.user && currentState.isAuthenticated) {
          console.log('Auth already initialized with user:', currentState.user.email);
          set({ isLoading: false });
          return;
        }

        const accessToken = Cookies.get('access_token');

        if (!accessToken) {
          set({
            user: null,
            isAuthenticated: false,
            isLoading: false
          });
          return;
        }

        try {
          set({ isLoading: true });
          const user = await getCurrentUser();
          set({
            user,
            isAuthenticated: true,
            isLoading: false,
            error: null,
          });
        } catch (error) {
          console.error('Failed to initialize auth:', error);

          // If network error or 401, clear stale tokens
          if (error.message === 'Network Error' || error.response?.status === 401) {
            Cookies.remove('access_token');
            Cookies.remove('refresh_token');
          }

          set({
            user: null,
            isAuthenticated: false,
            isLoading: false,
            error: null, // Don't set error on init failure, just redirect to login
          });
        }
      },

      /**
       * Sign up with email and password
       */
      signup: async (data) => {
        try {
          set({ isLoading: true, error: null });

          const response = await apiSignup(data);
          const user = response.user;

          set({
            user,
            isAuthenticated: true,
            isLoading: false,
            error: null,
          });

          return { success: true, user };
        } catch (error) {
          const errorMessage = error.response?.data?.detail || 'Signup failed';
          set({
            error: errorMessage,
            isLoading: false
          });
          return { success: false, error: errorMessage };
        }
      },

      /**
       * Login with email and password
       */
      loginWithPassword: async (email, password) => {
        try {
          set({ isLoading: true, error: null });

          const { user } = await apiLoginWithPassword(email, password);

          set({
            user,
            isAuthenticated: true,
            isLoading: false,
            error: null,
          });

          return { success: true, user };
        } catch (error) {
          const errorMessage = error.response?.data?.detail || 'Login failed';
          set({
            error: errorMessage,
            isLoading: false
          });
          return { success: false, error: errorMessage };
        }
      },

      /**
       * Login with OTP
       */
      loginWithOTP: async (identifier, otp, otpType = 'email') => {
        try {
          set({ isLoading: true, error: null });

          const { user } = await apiLoginWithOTP(identifier, otp, otpType);

          set({
            user,
            isAuthenticated: true,
            isLoading: false,
            error: null,
          });

          return { success: true, user };
        } catch (error) {
          const errorMessage = error.response?.data?.detail || 'OTP login failed';
          set({
            error: errorMessage,
            isLoading: false
          });
          return { success: false, error: errorMessage };
        }
      },

      /**
       * Handle Google OAuth callback
       */
      handleGoogleCallback: async (code, state) => {
        try {
          set({ isLoading: true, error: null });

          console.log('AuthContext: Calling backend Google callback...');
          const { user } = await apiHandleGoogleCallback(code, state);
          console.log('AuthContext: Google callback successful, user:', user);

          set({
            user,
            isAuthenticated: true,
            isLoading: false,
            error: null,
          });

          return { success: true, user };
        } catch (error) {
          console.error('AuthContext: Google callback error:', error);
          console.error('AuthContext: Error response:', error.response);

          // Extract detailed error message - handle both string and object formats
          let errorMessage = 'Google login failed. Please try again.';

          try {
            if (error.response?.data) {
              const data = error.response.data;
              console.log('AuthContext: Error data (raw):', JSON.stringify(data, null, 2));
              console.log('AuthContext: Error data.detail:', data.detail);
              console.log('AuthContext: Error data.error:', data.error);
              console.log('AuthContext: Error data.message:', data.message);

              // Handle main.py error format: { success: false, error: { code, message } }
              if (data.error && typeof data.error === 'object' && data.error.message) {
                errorMessage = data.error.message;
              }
              // Handle FastAPI error format: { detail: "message" } or { detail: { code, message } }
              else if (data.detail) {
                if (typeof data.detail === 'string') {
                  errorMessage = data.detail;
                } else if (typeof data.detail === 'object') {
                  errorMessage = data.detail.message || data.detail.code || JSON.stringify(data.detail);
                }
              }
              // Handle simple error format: { error: "message" }
              else if (data.error && typeof data.error === 'string') {
                errorMessage = data.error;
              }
              // Handle { message: "..." } format
              else if (data.message) {
                errorMessage = data.message;
              }
              // Fallback
              else {
                errorMessage = JSON.stringify(data);
              }
            } else if (error.message) {
              errorMessage = error.message;
            }
          } catch (parseError) {
            console.error('Error parsing error message:', parseError);
            errorMessage = 'An unexpected error occurred. Please check the console for details.';
          }

          console.error('AuthContext: Final error message:', errorMessage);

          set({
            error: errorMessage,
            isLoading: false,
            user: null,
            isAuthenticated: false
          });

          return { success: false, error: errorMessage };
        }
      },

      /**
       * Logout
       */
      logout: async () => {
        try {
          await apiLogout();
        } catch (error) {
          console.error('Logout error:', error);
        } finally {
          set({
            user: null,
            isAuthenticated: false,
            error: null,
          });
        }
      },

      /**
       * Update user profile
       */
      updateUser: (updates) => {
        const currentUser = get().user;
        if (currentUser) {
          set({
            user: { ...currentUser, ...updates }
          });
        }
      },
    }),
    {
      name: 'auth-storage',
      storage: createJSONStorage(() => {
        // Use sessionStorage for security
        if (typeof window !== 'undefined') {
          return window.sessionStorage;
        }
        return {
          getItem: () => null,
          setItem: () => {},
          removeItem: () => {},
        };
      }),
      partialize: (state) => ({
        user: state.user,
        isAuthenticated: state.isAuthenticated,
      }),
    }
  )
);

export default useAuthStore;
