'use client';

import { useState, useEffect, Suspense } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import Link from 'next/link';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import toast, { Toaster } from 'react-hot-toast';
import { Eye, EyeOff, AlertCircle, CheckCircle, ChevronDown, User, Shield, BarChart3, Settings, Users } from 'lucide-react';
import Image from 'next/image';
import useAuthStore from '@/context/AuthContext';
import { getGoogleAuthUrl, getRoleBasedRedirectPath } from '@/lib/api';
import GoogleTranslate from '@/components/GoogleTranslate';

// Validation schema
const loginSchema = z.object({
  email: z.string().email('Please enter a valid email address'),
  password: z.string().min(1, 'Password is required'),
});

// Cookie helper functions
const setCookie = (name, value, days = 30) => {
  const expires = new Date(Date.now() + days * 864e5).toUTCString();
  document.cookie = `${name}=${encodeURIComponent(value)}; expires=${expires}; path=/; SameSite=Lax`;
};

const getCookie = (name) => {
  const value = `; ${document.cookie}`;
  const parts = value.split(`; ${name}=`);
  if (parts.length === 2) {
    return decodeURIComponent(parts.pop().split(';').shift());
  }
  return null;
};

const deleteCookie = (name) => {
  document.cookie = `${name}=; expires=Thu, 01 Jan 1970 00:00:00 GMT; path=/`;
};

// Test credentials for quick login (Demo/Development)
const TEST_CREDENTIALS = {
  citizen: {
    email: 'citizen@coastguardian.com',
    password: 'Citizen@123',
    label: 'Citizen',
    icon: User,
    color: 'bg-emerald-500',
    description: 'Report hazards & view alerts',
  },
  authority: {
    email: 'authority@coastguardian.com',
    password: 'Authority@123',
    label: 'Authority',
    icon: Shield,
    color: 'bg-blue-500',
    description: 'Verify reports & create alerts',
  },
  analyst: {
    email: 'analyst@coastguardian.com',
    password: 'Analyst@123',
    label: 'Analyst',
    icon: BarChart3,
    color: 'bg-purple-500',
    description: 'Review & analyze reports',
  },
  admin: {
    email: 'admin@coastguardian.com',
    password: 'Admin@123',
    label: 'Admin',
    icon: Settings,
    color: 'bg-red-500',
    description: 'Full system control',
  },
  organizer: {
    email: 'organizer@coastguardian.com',
    password: 'Organizer@123',
    label: 'Organizer',
    icon: Users,
    color: 'bg-orange-500',
    description: 'Create communities & events',
  },
};

// Loading fallback component
function LoadingFallback() {
  return (
    <div className="min-h-screen flex items-center justify-center bg-[#f0f4f8]">
      <div className="animate-spin rounded-full h-10 w-10 border-t-2 border-b-2 border-[#0d4a6f]"></div>
    </div>
  );
}

// Main login component
function LoginContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { user, loginWithPassword, isAuthenticated, initialize } = useAuthStore();
  const [showPassword, setShowPassword] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [apiError, setApiError] = useState('');
  const [showVerifiedMessage, setShowVerifiedMessage] = useState(false);
  const [selectedRole, setSelectedRole] = useState('citizen');
  const [showRoleDropdown, setShowRoleDropdown] = useState(false);
  const [rememberMe, setRememberMe] = useState(false);

  const {
    register,
    handleSubmit,
    setValue,
    formState: { errors },
  } = useForm({
    resolver: zodResolver(loginSchema),
  });

  // Load saved credentials from cookies on mount, or default to citizen
  useEffect(() => {
    const savedEmail = getCookie('cg_remembered_email');
    const savedPassword = getCookie('cg_remembered_password');
    const savedRemember = getCookie('cg_remember_me');

    if (savedEmail && savedPassword && savedRemember === 'true') {
      setValue('email', savedEmail);
      setValue('password', savedPassword);
      setRememberMe(true);
    } else {
      // Default to citizen credentials for demo
      const citizenCreds = TEST_CREDENTIALS.citizen;
      setValue('email', citizenCreds.email);
      setValue('password', citizenCreds.password);
    }
  }, [setValue]);

  // Handle role selection and auto-fill credentials
  const handleRoleSelect = (roleKey) => {
    const creds = TEST_CREDENTIALS[roleKey];
    if (creds) {
      setValue('email', creds.email);
      setValue('password', creds.password);
      setSelectedRole(roleKey);
      setShowRoleDropdown(false);
      toast.success(`${creds.label} credentials filled!`, { duration: 2000 });
    }
  };

  // Check for verified parameter and show success message
  useEffect(() => {
    const verified = searchParams.get('verified');
    const reset = searchParams.get('reset');

    if (verified === 'true') {
      setShowVerifiedMessage(true);
      toast.success('Email verified successfully! You can now sign in.');
      setTimeout(() => setShowVerifiedMessage(false), 5000);
    }

    if (reset === 'success') {
      toast.success('Password reset successfully! Please login with your new password.', {
        duration: 6000,
      });
    }
  }, [searchParams]);

  // Initialize auth and redirect if already logged in
  useEffect(() => {
    initialize();
  }, [initialize]);

  // Handle password login
  const onSubmit = async (data) => {
    setIsLoading(true);
    setApiError('');

    const { success, error, user: loggedInUser } = await loginWithPassword(data.email, data.password);
    setIsLoading(false);

    if (success) {
      if (rememberMe) {
        setCookie('cg_remembered_email', data.email, 30);
        setCookie('cg_remembered_password', data.password, 30);
        setCookie('cg_remember_me', 'true', 30);
      } else {
        deleteCookie('cg_remembered_email');
        deleteCookie('cg_remembered_password');
        deleteCookie('cg_remember_me');
      }

      toast.success('Login successful!');
      setTimeout(() => {
        const redirectPath = getRoleBasedRedirectPath(loggedInUser?.role);
        router.push(redirectPath);
      }, 100);
    } else {
      let errorMessage = error || 'Login failed. Please try again.';

      if (errorMessage.toLowerCase().includes('invalid') || errorMessage.toLowerCase().includes('incorrect')) {
        errorMessage = 'Invalid email or password. Please try again.';
      } else if (errorMessage.toLowerCase().includes('not found')) {
        errorMessage = 'No account found with this email. Please sign up first.';
      } else if (errorMessage.toLowerCase().includes('not verified')) {
        errorMessage = 'Please verify your email before logging in.';
      } else if (errorMessage.toLowerCase().includes('disabled') || errorMessage.toLowerCase().includes('suspended')) {
        errorMessage = 'Your account has been disabled. Please contact support.';
      }

      setApiError(errorMessage);
      toast.error(errorMessage);
    }
  };

  // Handle Google OAuth login
  const handleGoogleLogin = async () => {
    try {
      const url = await getGoogleAuthUrl();
      window.location.href = url;
    } catch (error) {
      toast.error('Failed to initiate Google login');
    }
  };

  return (
    <div className="min-h-screen flex flex-col bg-[#f0f4f8]">
      <Toaster position="top-center" toastOptions={{ duration: 3000 }} />

      {/* Top Bar with Translation */}
      <div className="absolute top-4 right-4 z-10">
        <GoogleTranslate variant="sidebar" />
      </div>

      {/* Main Content */}
      <div className="flex-1 flex items-center justify-center px-4 py-3">
        <div className="w-full max-w-[400px]">
          {/* Card */}
          <div className="bg-white rounded-2xl shadow-sm border border-gray-200 px-5 sm:px-6 py-5">
            {/* Logo */}
            <div className="flex justify-center mb-2">
              <Image
                src="/logo.png"
                alt="CoastGuardian Logo"
                width={200}
                height={200}
                className="w-28 h-28 object-cover scale-150"
                priority
              />
            </div>

            {/* Title */}
            <div className="text-center mb-4">
              <h1 className="text-xl font-semibold text-gray-900">Sign in</h1>
              <p className="text-sm text-gray-500">to continue to CoastGuardian</p>
            </div>

            {/* Success Message */}
            {showVerifiedMessage && (
              <div className="mb-3 p-2.5 bg-green-50 border border-green-200 rounded-lg flex items-start">
                <CheckCircle className="h-4 w-4 text-green-600 mt-0.5 mr-2 flex-shrink-0" />
                <p className="text-sm text-green-800">Email verified! You can now sign in.</p>
              </div>
            )}

            {/* Error Message */}
            {apiError && (
              <div className="mb-3 p-2.5 bg-red-50 border border-red-200 rounded-lg flex items-start">
                <AlertCircle className="h-4 w-4 text-red-600 mt-0.5 mr-2 flex-shrink-0" />
                <p className="text-sm text-red-800">{apiError}</p>
              </div>
            )}

            <form onSubmit={handleSubmit(onSubmit)} className="space-y-2.5">
              {/* Quick Demo Login */}
              <div className="relative">
                <label className="block text-xs font-medium text-gray-700 mb-1">
                  Quick Demo Login
                </label>
                <button
                  type="button"
                  onClick={() => setShowRoleDropdown(!showRoleDropdown)}
                  className="w-full flex items-center justify-between px-3 py-2 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-[#1a6b9a] focus:border-[#1a6b9a] transition-colors"
                >
                  {selectedRole ? (
                    <div className="flex items-center gap-2">
                      {(() => {
                        const RoleIcon = TEST_CREDENTIALS[selectedRole].icon;
                        return (
                          <>
                            <span className={`w-5 h-5 rounded-full ${TEST_CREDENTIALS[selectedRole].color} flex items-center justify-center`}>
                              <RoleIcon className="w-3 h-3 text-white" />
                            </span>
                            <span className="text-sm text-gray-700">{TEST_CREDENTIALS[selectedRole].label}</span>
                          </>
                        );
                      })()}
                    </div>
                  ) : (
                    <span className="text-sm text-gray-500">Select role</span>
                  )}
                  <ChevronDown className={`w-4 h-4 text-gray-400 transition-transform ${showRoleDropdown ? 'rotate-180' : ''}`} />
                </button>

                {showRoleDropdown && (
                  <div className="absolute z-20 mt-1 w-full bg-white border border-gray-200 rounded-lg shadow-lg overflow-hidden">
                    {Object.entries(TEST_CREDENTIALS).map(([key, creds]) => {
                      const RoleIcon = creds.icon;
                      return (
                        <button
                          key={key}
                          type="button"
                          onClick={() => handleRoleSelect(key)}
                          className={`w-full flex items-center gap-2.5 px-3 py-2 hover:bg-gray-50 transition-colors ${selectedRole === key ? 'bg-[#e8f4fc]' : ''}`}
                        >
                          <span className={`w-6 h-6 rounded-full ${creds.color} flex items-center justify-center`}>
                            <RoleIcon className="w-3 h-3 text-white" />
                          </span>
                          <div className="text-left">
                            <p className="text-sm font-medium text-gray-800">{creds.label}</p>
                            <p className="text-xs text-gray-500">{creds.description}</p>
                          </div>
                        </button>
                      );
                    })}
                  </div>
                )}
              </div>

              {/* Divider */}
              <div className="relative py-1">
                <div className="absolute inset-0 flex items-center">
                  <div className="w-full border-t border-gray-200"></div>
                </div>
                <div className="relative flex justify-center">
                  <span className="px-2 bg-white text-xs text-gray-400">or</span>
                </div>
              </div>

              {/* Email Input */}
              <div>
                <label htmlFor="email" className="block text-xs font-medium text-gray-700 mb-1">
                  Email
                </label>
                <input
                  id="email"
                  type="email"
                  autoComplete="email"
                  {...register('email')}
                  className={`w-full px-3 py-2 bg-white border rounded-lg text-sm focus:outline-none focus:ring-2 transition-colors ${errors.email
                    ? 'border-red-300 focus:ring-red-500 focus:border-red-500'
                    : 'border-gray-300 focus:ring-[#1a6b9a] focus:border-[#1a6b9a]'
                    }`}
                  placeholder="Enter your email"
                />
                {errors.email && (
                  <p className="mt-1 text-xs text-red-600">{errors.email.message}</p>
                )}
              </div>

              {/* Password Input */}
              <div>
                <div className="flex items-center justify-between mb-1">
                  <label htmlFor="password" className="block text-xs font-medium text-gray-700">
                    Password
                  </label>
                  <Link href="/forgot-password" className="text-xs font-medium text-[#0d4a6f] hover:text-[#1a6b9a]">
                    Forgot?
                  </Link>
                </div>
                <div className="relative">
                  <input
                    id="password"
                    type={showPassword ? 'text' : 'password'}
                    autoComplete="current-password"
                    {...register('password')}
                    className={`w-full px-3 py-2 pr-10 bg-white border rounded-lg text-sm focus:outline-none focus:ring-2 transition-colors ${errors.password
                      ? 'border-red-300 focus:ring-red-500 focus:border-red-500'
                      : 'border-gray-300 focus:ring-[#1a6b9a] focus:border-[#1a6b9a]'
                      }`}
                    placeholder="Enter your password"
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    className="absolute inset-y-0 right-0 pr-3 flex items-center"
                    tabIndex={-1}
                  >
                    {showPassword ? (
                      <EyeOff className="h-4 w-4 text-gray-400 hover:text-gray-600" />
                    ) : (
                      <Eye className="h-4 w-4 text-gray-400 hover:text-gray-600" />
                    )}
                  </button>
                </div>
                {errors.password && (
                  <p className="mt-1 text-xs text-red-600">{errors.password.message}</p>
                )}
              </div>

              {/* Remember Me */}
              <label className="flex items-center cursor-pointer">
                <input
                  type="checkbox"
                  checked={rememberMe}
                  onChange={(e) => setRememberMe(e.target.checked)}
                  className="w-3.5 h-3.5 text-[#0d4a6f] bg-white border-gray-300 rounded focus:ring-[#1a6b9a] focus:ring-2"
                />
                <span className="ml-2 text-xs text-gray-600">Remember me</span>
              </label>

              {/* Sign In Button */}
              <button
                type="submit"
                disabled={isLoading}
                className="w-full py-2 px-4 bg-[#0d4a6f] hover:bg-[#083a57] text-white text-sm font-medium rounded-lg focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-[#1a6b9a] disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                {isLoading ? (
                  <span className="flex items-center justify-center">
                    <svg className="animate-spin -ml-1 mr-2 h-4 w-4 text-white" fill="none" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                    </svg>
                    Signing in...
                  </span>
                ) : (
                  'Sign in'
                )}
              </button>

              {/* Divider */}
              <div className="relative py-1">
                <div className="absolute inset-0 flex items-center">
                  <div className="w-full border-t border-gray-200"></div>
                </div>
                <div className="relative flex justify-center">
                  <span className="px-2 bg-white text-xs text-gray-400">or</span>
                </div>
              </div>

              {/* Google Sign In */}
              <button
                type="button"
                onClick={handleGoogleLogin}
                className="w-full flex items-center justify-center gap-2 py-2 px-4 bg-white border border-gray-300 rounded-lg text-sm font-medium text-gray-700 hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-gray-500 transition-colors"
              >
                <svg className="w-4 h-4" viewBox="0 0 24 24">
                  <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" />
                  <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" />
                  <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" />
                  <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" />
                </svg>
                Continue with Google
              </button>
            </form>

            {/* Sign Up Link */}
            <p className="mt-3 text-center text-xs text-gray-600">
              Don't have an account?{' '}
              <Link href="/signup" className="font-medium text-[#0d4a6f] hover:text-[#1a6b9a]">
                Create account
              </Link>
            </p>
          </div>
        </div>
      </div>

      {/* Footer */}
      <footer className="py-2 px-4">
        <div className="max-w-[400px] mx-auto flex flex-col sm:flex-row items-center justify-between gap-2 text-xs text-gray-500">
          <span>English (United States)</span>
          <div className="flex items-center gap-4">
            <Link href="/help" className="hover:text-gray-700">Help</Link>
            <Link href="/privacy" className="hover:text-gray-700">Privacy</Link>
            <Link href="/terms" className="hover:text-gray-700">Terms</Link>
          </div>
        </div>
      </footer>
    </div>
  );
}

// Default export with Suspense boundary
export default function LoginPage() {
  return (
    <Suspense fallback={<LoadingFallback />}>
      <LoginContent />
    </Suspense>
  );
}
