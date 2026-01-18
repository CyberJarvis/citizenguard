'use client';

import { useState, useEffect, Suspense, useRef } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import Link from 'next/link';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import toast, { Toaster } from 'react-hot-toast';
import { Eye, EyeOff, ArrowLeft, AlertCircle } from 'lucide-react';
import Image from 'next/image';
import { resetPassword, forgotPassword } from '@/lib/api';

// Validation schema
const resetPasswordSchema = z.object({
  otp: z.string().min(6, 'Code must be 6 digits').max(6, 'Code must be 6 digits').regex(/^\d{6}$/, 'Code must be 6 digits'),
  newPassword: z
    .string()
    .min(8, 'Password must be at least 8 characters')
    .regex(/[A-Z]/, 'Must contain uppercase letter')
    .regex(/[a-z]/, 'Must contain lowercase letter')
    .regex(/\d/, 'Must contain digit')
    .regex(/[!@#$%^&*(),.?":{}|<>]/, 'Must contain special character'),
  confirmPassword: z.string().min(1, 'Please confirm your password'),
}).refine((data) => data.newPassword === data.confirmPassword, {
  message: "Passwords don't match",
  path: ['confirmPassword'],
});

// Loading fallback component
function LoadingFallback() {
  return (
    <div className="min-h-screen flex items-center justify-center bg-[#f0f4f8]">
      <div className="animate-spin rounded-full h-10 w-10 border-t-2 border-b-2 border-[#0d4a6f]"></div>
    </div>
  );
}

// Main reset password component
function ResetPasswordContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [email, setEmail] = useState('');
  const [canResendOTP, setCanResendOTP] = useState(false);
  const [resendCountdown, setResendCountdown] = useState(60);
  const [otp, setOtp] = useState(['', '', '', '', '', '']);
  const inputRefs = useRef([]);

  const {
    register,
    handleSubmit,
    watch,
    setValue,
    formState: { errors },
  } = useForm({
    resolver: zodResolver(resetPasswordSchema),
  });

  const newPassword = watch('newPassword', '');

  // Password strength indicator
  const getPasswordStrength = (pwd) => {
    if (!pwd) return { strength: 0, label: '', color: '' };
    let strength = 0;
    if (pwd.length >= 8) strength++;
    if (/[A-Z]/.test(pwd)) strength++;
    if (/[a-z]/.test(pwd)) strength++;
    if (/[0-9]/.test(pwd)) strength++;
    if (/[!@#$%^&*(),.?":{}|<>]/.test(pwd)) strength++;

    if (strength <= 2) return { strength: 1, label: 'Weak', color: 'bg-red-500' };
    if (strength <= 3) return { strength: 2, label: 'Fair', color: 'bg-yellow-500' };
    if (strength <= 4) return { strength: 3, label: 'Good', color: 'bg-[#1a6b9a]' };
    return { strength: 4, label: 'Strong', color: 'bg-green-500' };
  };

  const passwordStrength = getPasswordStrength(newPassword);

  // Get email from URL parameters
  useEffect(() => {
    const emailParam = searchParams.get('email');
    if (emailParam) {
      setEmail(emailParam);
    } else {
      toast.error('Email is required. Please start the password reset process again.');
      router.push('/forgot-password');
    }
  }, [searchParams, router]);

  // Resend OTP countdown
  useEffect(() => {
    if (resendCountdown > 0) {
      const timer = setTimeout(() => setResendCountdown(resendCountdown - 1), 1000);
      return () => clearTimeout(timer);
    } else {
      setCanResendOTP(true);
    }
  }, [resendCountdown]);

  // Handle OTP input change
  const handleOtpChange = (index, value) => {
    if (!/^\d*$/.test(value)) return;

    const newOtp = [...otp];
    newOtp[index] = value;
    setOtp(newOtp);
    setValue('otp', newOtp.join(''));

    if (value && index < 5) {
      inputRefs.current[index + 1]?.focus();
    }
  };

  const handleOtpKeyDown = (index, e) => {
    if (e.key === 'Backspace' && !otp[index] && index > 0) {
      inputRefs.current[index - 1]?.focus();
    }
  };

  const handleOtpPaste = (e) => {
    e.preventDefault();
    const pastedData = e.clipboardData.getData('text').slice(0, 6);

    if (!/^\d+$/.test(pastedData)) return;

    const newOtp = [...otp];
    pastedData.split('').forEach((char, i) => {
      if (i < 6) newOtp[i] = char;
    });
    setOtp(newOtp);
    setValue('otp', newOtp.join(''));

    const lastIndex = Math.min(pastedData.length, 5);
    inputRefs.current[lastIndex]?.focus();
  };

  const handleResendOTP = async () => {
    if (!canResendOTP || !email) return;

    try {
      await forgotPassword(email);
      toast.success('New code sent to your email!');
      setCanResendOTP(false);
      setResendCountdown(60);
      setOtp(['', '', '', '', '', '']);
      setValue('otp', '');
    } catch (error) {
      toast.error('Failed to resend code. Please try again.');
    }
  };

  const onSubmit = async (data) => {
    if (!email) {
      toast.error('Email is required. Please start the password reset process again.');
      router.push('/forgot-password');
      return;
    }

    setIsLoading(true);

    try {
      const response = await resetPassword(email, data.otp, data.newPassword);

      const successMessage = response?.message || 'Password reset successfully!';
      toast.success(successMessage, { duration: 4000 });

      setTimeout(() => {
        router.push('/login?reset=success');
      }, 2000);
    } catch (error) {
      console.error('Password reset error:', error);

      const errorMessage = error.response?.data?.detail || 'Failed to reset password. Please try again.';

      if (errorMessage.toLowerCase().includes('invalid otp') || errorMessage.toLowerCase().includes('invalid code')) {
        toast.error('Invalid code. Please check and try again.');
      } else if (errorMessage.toLowerCase().includes('expired')) {
        toast.error('Code has expired. Please request a new one.');
      } else if (errorMessage.toLowerCase().includes('attempts')) {
        toast.error('Too many failed attempts. Please request a new code.');
      } else if (errorMessage.toLowerCase().includes('not found')) {
        toast.error('No password reset request found. Please start again.');
        setTimeout(() => router.push('/forgot-password'), 2000);
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
              <h1 className="text-xl font-semibold text-gray-900">Reset password</h1>
              <p className="text-sm text-gray-600">
                Enter the code sent to
              </p>
              {email && (
                <p className="text-sm font-semibold text-gray-900 mt-1">{email}</p>
              )}
            </div>

            <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
              {/* OTP Input */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2 text-center">
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
                      onChange={(e) => handleOtpChange(index, e.target.value)}
                      onKeyDown={(e) => handleOtpKeyDown(index, e)}
                      onPaste={handleOtpPaste}
                      className={`w-10 h-12 sm:w-12 sm:h-14 text-center text-xl font-semibold border-2 rounded-lg focus:outline-none focus:ring-2 transition-all ${
                        errors.otp
                          ? 'border-red-300 focus:border-red-500 focus:ring-red-500'
                          : 'border-gray-300 focus:border-[#1a6b9a] focus:ring-[#1a6b9a]'
                      }`}
                    />
                  ))}
                </div>
                <input type="hidden" {...register('otp')} />
                {errors.otp && (
                  <p className="mt-2 text-xs text-red-600 text-center">{errors.otp.message}</p>
                )}
              </div>

              {/* Resend OTP */}
              <div className="text-center">
                {canResendOTP ? (
                  <button
                    type="button"
                    onClick={handleResendOTP}
                    className="text-sm font-medium text-[#0d4a6f] hover:text-[#1a6b9a] transition-colors"
                  >
                    Resend code
                  </button>
                ) : (
                  <span className="text-sm text-gray-500">
                    Resend in <span className="font-semibold text-[#0d4a6f]">{resendCountdown}s</span>
                  </span>
                )}
              </div>

              {/* New Password Input */}
              <div>
                <label htmlFor="newPassword" className="block text-sm font-medium text-gray-700 mb-1.5">
                  New password
                </label>
                <div className="relative">
                  <input
                    id="newPassword"
                    type={showPassword ? 'text' : 'password'}
                    autoComplete="new-password"
                    {...register('newPassword')}
                    className={`w-full px-3 py-2.5 pr-10 bg-white border rounded-lg text-sm focus:outline-none focus:ring-2 transition-colors ${
                      errors.newPassword
                        ? 'border-red-300 focus:ring-red-500 focus:border-red-500'
                        : 'border-gray-300 focus:ring-[#1a6b9a] focus:border-[#1a6b9a]'
                    }`}
                    placeholder="Create new password"
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
                {/* Password Strength Indicator */}
                {newPassword && (
                  <div className="mt-2">
                    <div className="flex items-center gap-2">
                      <div className="flex-1 h-1 bg-gray-200 rounded-full overflow-hidden">
                        <div
                          className={`h-full ${passwordStrength.color} transition-all duration-300`}
                          style={{ width: `${(passwordStrength.strength / 4) * 100}%` }}
                        />
                      </div>
                      <span className={`text-xs font-medium ${
                        passwordStrength.strength <= 1 ? 'text-red-600' :
                        passwordStrength.strength <= 2 ? 'text-yellow-600' :
                        passwordStrength.strength <= 3 ? 'text-[#0d4a6f]' : 'text-green-600'
                      }`}>
                        {passwordStrength.label}
                      </span>
                    </div>
                  </div>
                )}
                {errors.newPassword && (
                  <p className="mt-1 text-xs text-red-600">{errors.newPassword.message}</p>
                )}
                <p className="mt-1 text-xs text-gray-500">
                  8+ characters with uppercase, lowercase, number & special character
                </p>
              </div>

              {/* Confirm Password Input */}
              <div>
                <label htmlFor="confirmPassword" className="block text-sm font-medium text-gray-700 mb-1.5">
                  Confirm new password
                </label>
                <div className="relative">
                  <input
                    id="confirmPassword"
                    type={showConfirmPassword ? 'text' : 'password'}
                    autoComplete="new-password"
                    {...register('confirmPassword')}
                    className={`w-full px-3 py-2.5 pr-10 bg-white border rounded-lg text-sm focus:outline-none focus:ring-2 transition-colors ${
                      errors.confirmPassword
                        ? 'border-red-300 focus:ring-red-500 focus:border-red-500'
                        : 'border-gray-300 focus:ring-[#1a6b9a] focus:border-[#1a6b9a]'
                    }`}
                    placeholder="Confirm your password"
                  />
                  <button
                    type="button"
                    onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                    className="absolute inset-y-0 right-0 pr-3 flex items-center"
                    tabIndex={-1}
                  >
                    {showConfirmPassword ? (
                      <EyeOff className="h-4 w-4 text-gray-400 hover:text-gray-600" />
                    ) : (
                      <Eye className="h-4 w-4 text-gray-400 hover:text-gray-600" />
                    )}
                  </button>
                </div>
                {errors.confirmPassword && (
                  <p className="mt-1 text-xs text-red-600">{errors.confirmPassword.message}</p>
                )}
              </div>

              {/* Submit Button */}
              <button
                type="submit"
                disabled={isLoading}
                className="w-full py-2.5 px-4 bg-[#0d4a6f] hover:bg-[#083a57] text-white text-sm font-medium rounded-lg focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-[#1a6b9a] disabled:opacity-50 disabled:cursor-not-allowed transition-colors mt-2"
              >
                {isLoading ? (
                  <span className="flex items-center justify-center">
                    <svg className="animate-spin -ml-1 mr-2 h-4 w-4 text-white" fill="none" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                    </svg>
                    Resetting...
                  </span>
                ) : (
                  'Reset password'
                )}
              </button>
            </form>

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

// Default export with Suspense boundary
export default function ResetPasswordPage() {
  return (
    <Suspense fallback={<LoadingFallback />}>
      <ResetPasswordContent />
    </Suspense>
  );
}
