'use client';

import { useState, useEffect, useRef } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import toast, { Toaster } from 'react-hot-toast';
import { ArrowLeft, AlertCircle } from 'lucide-react';
import Image from 'next/image';
import apiClient from '@/lib/api';

export default function VerifyOTPPage() {
  const router = useRouter();
  const [otp, setOtp] = useState(['', '', '', '', '', '']);
  const [email, setEmail] = useState('');
  const [isVerifying, setIsVerifying] = useState(false);
  const [isResending, setIsResending] = useState(false);
  const [countdown, setCountdown] = useState(0);
  const [error, setError] = useState('');
  const inputRefs = useRef([]);

  useEffect(() => {
    // Get email from session storage
    const pendingEmail = sessionStorage.getItem('pendingVerificationEmail');
    if (!pendingEmail) {
      toast.error('No pending verification found');
      router.push('/signup');
      return;
    }
    setEmail(pendingEmail);
  }, [router]);

  useEffect(() => {
    // Countdown timer for resend
    if (countdown > 0) {
      const timer = setTimeout(() => setCountdown(countdown - 1), 1000);
      return () => clearTimeout(timer);
    }
  }, [countdown]);

  const handleChange = (index, value) => {
    // Only allow numbers
    if (!/^\d*$/.test(value)) return;

    const newOtp = [...otp];
    newOtp[index] = value;
    setOtp(newOtp);
    setError('');

    // Auto-focus next input
    if (value && index < 5) {
      inputRefs.current[index + 1]?.focus();
    }
  };

  const handleKeyDown = (index, e) => {
    // Handle backspace
    if (e.key === 'Backspace' && !otp[index] && index > 0) {
      inputRefs.current[index - 1]?.focus();
    }
  };

  const handlePaste = (e) => {
    e.preventDefault();
    const pastedData = e.clipboardData.getData('text').slice(0, 6);

    if (!/^\d+$/.test(pastedData)) return;

    const newOtp = [...otp];
    pastedData.split('').forEach((char, i) => {
      if (i < 6) newOtp[i] = char;
    });
    setOtp(newOtp);

    // Focus last filled input or last input
    const lastIndex = Math.min(pastedData.length, 5);
    inputRefs.current[lastIndex]?.focus();
  };

  const handleVerify = async (e) => {
    e.preventDefault();

    const otpString = otp.join('');
    if (otpString.length !== 6) {
      setError('Please enter the complete 6-digit code');
      return;
    }

    setIsVerifying(true);
    setError('');

    try {
      const response = await apiClient.post('/auth/verify-otp', {
        email,
        otp: otpString,
        otp_type: 'email'
      });

      toast.success('Email verified successfully!');
      sessionStorage.removeItem('pendingVerificationEmail');

      setTimeout(() => {
        router.push('/login?verified=true');
      }, 1000);

    } catch (error) {
      console.error('OTP verification error:', error);

      let errorMessage = 'Verification failed. Please try again.';

      if (error.response?.data) {
        const errorData = error.response.data;
        if (errorData.detail) {
          errorMessage = typeof errorData.detail === 'string'
            ? errorData.detail
            : errorData.detail.message || errorMessage;
        } else if (errorData.error?.message) {
          errorMessage = errorData.error.message;
        }

        if (errorMessage.toLowerCase().includes('invalid') || errorMessage.toLowerCase().includes('incorrect')) {
          errorMessage = 'Invalid code. Please check and try again.';
        } else if (errorMessage.toLowerCase().includes('expired')) {
          errorMessage = 'Code has expired. Please request a new one.';
        } else if (errorMessage.toLowerCase().includes('attempts')) {
          errorMessage = 'Too many attempts. Please request a new code.';
        }
      }

      setError(errorMessage);
      toast.error(errorMessage);
    } finally {
      setIsVerifying(false);
    }
  };

  const handleResend = async () => {
    if (countdown > 0) return;

    setIsResending(true);
    setError('');

    try {
      await apiClient.post('/auth/request-otp', {
        email,
        otp_type: 'email'
      });

      toast.success('New code sent to your email!');
      setCountdown(60);
      setOtp(['', '', '', '', '', '']);
      inputRefs.current[0]?.focus();

    } catch (error) {
      console.error('Resend OTP error:', error);
      toast.error('Failed to resend code. Please try again.');
    } finally {
      setIsResending(false);
    }
  };

  return (
    <div className="min-h-screen flex flex-col bg-[#f0f4f8]">
      <Toaster position="top-center" toastOptions={{ duration: 3000 }} />

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
              <h1 className="text-xl font-semibold text-gray-900">Verify your email</h1>
              <p className="text-sm text-gray-600">
                Enter the 6-digit code sent to
              </p>
              <p className="text-sm font-semibold text-gray-900 mt-1">{email}</p>
            </div>

            {/* Error Message */}
            {error && (
              <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg flex items-start">
                <AlertCircle className="h-5 w-5 text-red-600 mt-0.5 mr-2 flex-shrink-0" />
                <p className="text-sm text-red-800">{error}</p>
              </div>
            )}

            <form onSubmit={handleVerify}>
              {/* OTP Input */}
              <div className="mb-6">
                <label className="block text-sm font-medium text-gray-700 mb-3 text-center">
                  Verification code
                </label>
                <div className="flex justify-center gap-2 sm:gap-3">
                  {otp.map((digit, index) => (
                    <input
                      key={index}
                      ref={(el) => (inputRefs.current[index] = el)}
                      type="text"
                      inputMode="numeric"
                      maxLength={1}
                      value={digit}
                      onChange={(e) => handleChange(index, e.target.value)}
                      onKeyDown={(e) => handleKeyDown(index, e)}
                      onPaste={handlePaste}
                      className={`w-10 h-12 sm:w-12 sm:h-14 text-center text-xl font-semibold border-2 rounded-lg focus:outline-none focus:ring-2 transition-all ${
                        error
                          ? 'border-red-300 focus:border-red-500 focus:ring-red-500'
                          : 'border-gray-300 focus:border-[#1a6b9a] focus:ring-[#1a6b9a]'
                      }`}
                    />
                  ))}
                </div>
              </div>

              {/* Verify Button */}
              <button
                type="submit"
                disabled={isVerifying || otp.join('').length !== 6}
                className="w-full py-2.5 px-4 bg-[#0d4a6f] hover:bg-[#083a57] text-white text-sm font-medium rounded-lg focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-[#1a6b9a] disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                {isVerifying ? (
                  <span className="flex items-center justify-center">
                    <svg className="animate-spin -ml-1 mr-2 h-4 w-4 text-white" fill="none" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                    </svg>
                    Verifying...
                  </span>
                ) : (
                  'Verify email'
                )}
              </button>
            </form>

            {/* Resend OTP */}
            <div className="mt-6 text-center">
              <p className="text-sm text-gray-600 mb-2">
                Didn't receive the code?
              </p>
              {countdown > 0 ? (
                <p className="text-sm text-gray-500">
                  Resend in <span className="font-semibold text-[#0d4a6f]">{countdown}s</span>
                </p>
              ) : (
                <button
                  type="button"
                  onClick={handleResend}
                  disabled={isResending}
                  className="text-sm font-medium text-[#0d4a6f] hover:text-[#1a6b9a] disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                >
                  {isResending ? 'Sending...' : 'Resend code'}
                </button>
              )}
            </div>

            {/* Help text */}
            <div className="mt-6 p-3 bg-gray-50 border border-gray-200 rounded-lg">
              <p className="text-xs text-gray-600 text-center">
                Check your spam folder if you don't see the email
              </p>
            </div>

            {/* Back to Signup Link */}
            <div className="mt-6 text-center">
              <Link
                href="/signup"
                className="inline-flex items-center text-sm font-medium text-[#0d4a6f] hover:text-[#1a6b9a] transition-colors"
              >
                <ArrowLeft className="h-4 w-4 mr-1" />
                Back to sign up
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
