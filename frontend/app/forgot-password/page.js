'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import toast, { Toaster } from 'react-hot-toast';
import { AlertCircle, ArrowLeft, Mail, CheckCircle } from 'lucide-react';
import Image from 'next/image';
import { forgotPassword } from '@/lib/api';
import GoogleTranslate from '@/components/GoogleTranslate';

// Validation schema
const forgotPasswordSchema = z.object({
  email: z.string().email('Please enter a valid email address'),
});

export default function ForgotPasswordPage() {
  const router = useRouter();
  const [isLoading, setIsLoading] = useState(false);
  const [emailSent, setEmailSent] = useState(false);
  const [sentEmail, setSentEmail] = useState('');

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm({
    resolver: zodResolver(forgotPasswordSchema),
  });

  const onSubmit = async (data) => {
    setIsLoading(true);

    try {
      const response = await forgotPassword(data.email);

      setSentEmail(response.sent_to || data.email);
      setEmailSent(true);

      toast.success('Password reset OTP sent to your email!', {
        duration: 4000,
      });

      // Redirect to reset password page after 2 seconds
      setTimeout(() => {
        router.push(`/reset-password?email=${encodeURIComponent(data.email)}`);
      }, 2000);
    } catch (error) {
      console.error('Forgot password error:', error);

      const errorMessage = error.response?.data?.detail || 'Failed to send password reset email. Please try again.';

      if (errorMessage.toLowerCase().includes('not found')) {
        toast.error('No account found with this email.');
      } else if (errorMessage.toLowerCase().includes('inactive')) {
        toast.error('This account is inactive. Please contact support.');
      } else if (errorMessage.toLowerCase().includes('rate limit') || errorMessage.toLowerCase().includes('too many')) {
        toast.error('Too many requests. Please try again later.');
      } else {
        toast.error(errorMessage);
      }
    } finally {
      setIsLoading(false);
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
      <div className="flex-1 flex items-center justify-center px-4 py-4 sm:py-6">
        <div className="w-full max-w-[400px]">
          {/* Card */}
          <div className="bg-white rounded-2xl shadow-sm border border-gray-200 px-5 sm:px-8 py-6">
            {/* Logo */}
            <div className="flex justify-center mb-3">
              <Image
                src="/logo.png"
                alt="CoastGuardian Logo"
                width={200}
                height={200}
                className="w-16 h-16 object-contain"
                priority
              />
            </div>

            {/* Title */}
            <div className="text-center mb-4">
              <h1 className="text-xl font-semibold text-gray-900">
                {emailSent ? 'Check your email' : 'Forgot password?'}
              </h1>
              <p className="text-sm text-gray-600">
                {emailSent
                  ? "We've sent you a password reset code"
                  : "Enter your email to reset your password"
                }
              </p>
            </div>

            {emailSent ? (
              // Success State
              <div className="text-center">
                <div className="mx-auto flex items-center justify-center h-16 w-16 rounded-full bg-green-100 mb-4">
                  <CheckCircle className="h-8 w-8 text-green-600" />
                </div>
                <p className="text-sm text-gray-600 mb-2">
                  We've sent a 6-digit code to
                </p>
                <p className="text-sm font-semibold text-gray-900 mb-4">{sentEmail}</p>
                <p className="text-xs text-gray-500 mb-6">
                  The code expires in 5 minutes. Check your spam folder if you don't see it.
                </p>
                <button
                  onClick={() => router.push(`/reset-password?email=${encodeURIComponent(sentEmail)}`)}
                  className="w-full py-2.5 px-4 bg-[#0d4a6f] hover:bg-[#083a57] text-white text-sm font-medium rounded-lg focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-[#1a6b9a] transition-colors"
                >
                  Continue to reset password
                </button>
              </div>
            ) : (
              // Email Input Form
              <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
                {/* Email Input */}
                <div>
                  <label htmlFor="email" className="block text-sm font-medium text-gray-700 mb-1.5">
                    Email
                  </label>
                  <input
                    id="email"
                    type="email"
                    autoComplete="email"
                    autoFocus
                    {...register('email')}
                    className={`w-full px-3 py-2.5 bg-white border rounded-lg text-sm focus:outline-none focus:ring-2 transition-colors ${
                      errors.email
                        ? 'border-red-300 focus:ring-red-500 focus:border-red-500'
                        : 'border-gray-300 focus:ring-[#1a6b9a] focus:border-[#1a6b9a]'
                    }`}
                    placeholder="Enter your email"
                  />
                  {errors.email && (
                    <p className="mt-1 text-xs text-red-600">{errors.email.message}</p>
                  )}
                </div>

                {/* Send OTP Button */}
                <button
                  type="submit"
                  disabled={isLoading}
                  className="w-full py-2.5 px-4 bg-[#0d4a6f] hover:bg-[#083a57] text-white text-sm font-medium rounded-lg focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-[#1a6b9a] disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                >
                  {isLoading ? (
                    <span className="flex items-center justify-center">
                      <svg className="animate-spin -ml-1 mr-2 h-4 w-4 text-white" fill="none" viewBox="0 0 24 24">
                        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                      </svg>
                      Sending...
                    </span>
                  ) : (
                    'Send reset code'
                  )}
                </button>
              </form>
            )}

            {/* Back to Login Link */}
            <div className="mt-6 text-center">
              <Link
                href="/login"
                className="inline-flex items-center text-sm font-medium text-[#0d4a6f] hover:text-[#1a6b9a] transition-colors"
              >
                <ArrowLeft className="h-4 w-4 mr-1" />
                Back to sign in
              </Link>
            </div>
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
