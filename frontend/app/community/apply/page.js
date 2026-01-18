'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import ProtectedRoute from '@/components/ProtectedRoute';
import DashboardLayout from '@/components/DashboardLayout';
import {
  Award,
  CheckCircle,
  AlertTriangle,
  Upload,
  FileText,
  Loader2,
  ArrowLeft,
  Users,
  MapPin,
  Clock,
  XCircle
} from 'lucide-react';
import {
  checkOrganizerEligibility,
  getCoastalZones,
  submitOrganizerApplication,
  getOrganizerApplicationStatus
} from '@/lib/api';
import toast from 'react-hot-toast';

function OrganizerApplicationContent() {
  const router = useRouter();

  // State
  const [eligibility, setEligibility] = useState(null);
  const [applicationStatus, setApplicationStatus] = useState(null);
  const [coastalZones, setCoastalZones] = useState([]);
  const [states, setStates] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Form state
  const [formData, setFormData] = useState({
    name: '',
    email: '',
    phone: '',
    coastal_zone: '',
    state: ''
  });
  const [aadhaarFile, setAadhaarFile] = useState(null);
  const [filePreview, setFilePreview] = useState(null);

  // Load initial data
  useEffect(() => {
    const loadData = async () => {
      try {
        setIsLoading(true);

        const [eligibilityRes, zonesRes, statusRes] = await Promise.all([
          checkOrganizerEligibility(),
          getCoastalZones(),
          getOrganizerApplicationStatus()
        ]);

        setEligibility(eligibilityRes);
        setCoastalZones(zonesRes.coastal_zones || []);
        setStates(zonesRes.states || []);
        setApplicationStatus(statusRes);

      } catch (error) {
        console.error('Error loading data:', error);
        toast.error('Failed to load application data');
      } finally {
        setIsLoading(false);
      }
    };

    loadData();
  }, []);

  // Handle file selection
  const handleFileChange = (e) => {
    const file = e.target.files?.[0];
    if (!file) return;

    // Validate file type
    const allowedTypes = ['application/pdf', 'image/jpeg', 'image/png', 'image/jpg'];
    if (!allowedTypes.includes(file.type)) {
      toast.error('Please upload a PDF or image file (JPEG, PNG)');
      return;
    }

    // Validate file size (5MB max)
    if (file.size > 5 * 1024 * 1024) {
      toast.error('File size must be less than 5MB');
      return;
    }

    setAadhaarFile(file);

    // Create preview for images
    if (file.type.startsWith('image/')) {
      const reader = new FileReader();
      reader.onload = (e) => setFilePreview(e.target.result);
      reader.readAsDataURL(file);
    } else {
      setFilePreview(null);
    }
  };

  // Handle form submission
  const handleSubmit = async (e) => {
    e.preventDefault();

    if (!aadhaarFile) {
      toast.error('Please upload your Aadhaar document');
      return;
    }

    try {
      setIsSubmitting(true);

      const formDataToSend = new FormData();
      formDataToSend.append('name', formData.name);
      formDataToSend.append('email', formData.email);
      formDataToSend.append('phone', formData.phone);
      formDataToSend.append('coastal_zone', formData.coastal_zone);
      formDataToSend.append('state', formData.state);
      formDataToSend.append('aadhaar_document', aadhaarFile);

      const response = await submitOrganizerApplication(formDataToSend);

      if (response.success) {
        toast.success('Application submitted successfully!');
        // Refresh status
        const statusRes = await getOrganizerApplicationStatus();
        setApplicationStatus(statusRes);
        // Clear form
        setFormData({ name: '', email: '', phone: '', coastal_zone: '', state: '' });
        setAadhaarFile(null);
        setFilePreview(null);
      }
    } catch (error) {
      console.error('Error submitting application:', error);
      toast.error(error.response?.data?.detail || 'Failed to submit application');
    } finally {
      setIsSubmitting(false);
    }
  };

  // Render loading state
  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <div className="text-center">
          <Loader2 className="h-12 w-12 animate-spin text-blue-500 mx-auto mb-4" />
          <p className="text-gray-600">Loading application data...</p>
        </div>
      </div>
    );
  }

  // Render existing application status
  if (applicationStatus?.has_application) {
    const app = applicationStatus.application;
    const statusConfig = {
      pending: { color: 'yellow', icon: Clock, text: 'Under Review' },
      approved: { color: 'green', icon: CheckCircle, text: 'Approved' },
      rejected: { color: 'red', icon: XCircle, text: 'Rejected' }
    };
    const config = statusConfig[app.status] || statusConfig.pending;
    const StatusIcon = config.icon;

    return (
      <div className="max-w-2xl mx-auto">
        <div className={`bg-${config.color}-50 border border-${config.color}-200 rounded-xl p-6`}>
          <div className="flex items-center gap-4 mb-4">
            <div className={`p-3 bg-${config.color}-100 rounded-full`}>
              <StatusIcon className={`h-8 w-8 text-${config.color}-600`} />
            </div>
            <div>
              <h2 className="text-xl font-semibold text-gray-800">Application Status: {config.text}</h2>
              <p className="text-gray-600">Application ID: {app.application_id}</p>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4 mt-6">
            <div>
              <p className="text-sm text-gray-500">Submitted</p>
              <p className="font-medium">{new Date(app.applied_at).toLocaleDateString()}</p>
            </div>
            <div>
              <p className="text-sm text-gray-500">Coastal Zone</p>
              <p className="font-medium">{app.coastal_zone}</p>
            </div>
            <div>
              <p className="text-sm text-gray-500">State</p>
              <p className="font-medium">{app.state}</p>
            </div>
            <div>
              <p className="text-sm text-gray-500">Credibility at Application</p>
              <p className="font-medium">{app.credibility_at_application}</p>
            </div>
          </div>

          {app.status === 'rejected' && app.rejection_reason && (
            <div className="mt-6 p-4 bg-red-100 rounded-lg">
              <p className="text-sm font-medium text-red-800">Rejection Reason:</p>
              <p className="text-red-700 mt-1">{app.rejection_reason}</p>
            </div>
          )}

          {app.status === 'approved' && (
            <div className="mt-6 p-4 bg-green-100 rounded-lg">
              <p className="text-green-800">
                Congratulations! You are now a Verified Organizer. You can create communities and organize events.
              </p>
              <button
                onClick={() => router.push('/community')}
                className="mt-4 px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition"
              >
                Go to Community Hub
              </button>
            </div>
          )}

          <button
            onClick={() => router.back()}
            className="mt-6 flex items-center gap-2 text-gray-600 hover:text-gray-800 transition"
          >
            <ArrowLeft className="h-4 w-4" />
            Back
          </button>
        </div>
      </div>
    );
  }

  // Render eligibility check (not eligible)
  if (!eligibility?.eligible) {
    return (
      <div className="max-w-2xl mx-auto">
        <div className="bg-white rounded-xl shadow-lg p-8">
          <div className="flex items-center gap-4 mb-6">
            <div className="p-3 bg-orange-100 rounded-full">
              <AlertTriangle className="h-8 w-8 text-orange-600" />
            </div>
            <div>
              <h2 className="text-xl font-semibold text-gray-800">Not Eligible Yet</h2>
              <p className="text-gray-600">{eligibility?.message}</p>
            </div>
          </div>

          <div className="bg-gray-50 rounded-lg p-6 mb-6">
            <h3 className="font-medium text-gray-800 mb-4">Eligibility Requirements</h3>
            <div className="space-y-3">
              <div className="flex items-center gap-3">
                <div className={`p-1 rounded-full ${eligibility?.credibility_score >= 80 ? 'bg-green-100' : 'bg-red-100'}`}>
                  {eligibility?.credibility_score >= 80 ?
                    <CheckCircle className="h-5 w-5 text-green-600" /> :
                    <XCircle className="h-5 w-5 text-red-600" />
                  }
                </div>
                <span className="text-gray-700">
                  Credibility Score: <strong>{eligibility?.credibility_score || 0}</strong> / {eligibility?.required_score || 80} required
                </span>
              </div>
              <div className="flex items-center gap-3">
                <div className={`p-1 rounded-full ${eligibility?.reason !== 'pending_application' ? 'bg-green-100' : 'bg-red-100'}`}>
                  {eligibility?.reason !== 'pending_application' ?
                    <CheckCircle className="h-5 w-5 text-green-600" /> :
                    <XCircle className="h-5 w-5 text-red-600" />
                  }
                </div>
                <span className="text-gray-700">No pending application</span>
              </div>
            </div>
          </div>

          <p className="text-gray-600 text-sm">
            Keep contributing quality hazard reports to improve your credibility score.
            Once you reach 80 points, you can apply to become a Verified Organizer.
          </p>

          <button
            onClick={() => router.back()}
            className="mt-6 flex items-center gap-2 text-gray-600 hover:text-gray-800 transition"
          >
            <ArrowLeft className="h-4 w-4" />
            Back
          </button>
        </div>
      </div>
    );
  }

  // Render application form (eligible)
  return (
    <div className="max-w-3xl mx-auto">
      {/* Header */}
      <div className="mb-8">
        <button
          onClick={() => router.back()}
          className="flex items-center gap-2 text-gray-600 hover:text-gray-800 transition mb-4"
        >
          <ArrowLeft className="h-4 w-4" />
          Back
        </button>
        <h1 className="text-2xl font-bold text-gray-800">Apply as Verified Organizer</h1>
        <p className="text-gray-600 mt-2">
          Create communities, organize cleanup events, and lead coastal conservation efforts.
        </p>
      </div>

      {/* Eligibility Badge */}
      <div className="bg-green-50 border border-green-200 rounded-xl p-4 mb-6">
        <div className="flex items-center gap-3">
          <CheckCircle className="h-6 w-6 text-green-600" />
          <div>
            <p className="font-medium text-green-800">You are eligible to apply!</p>
            <p className="text-sm text-green-700">Your credibility score: {eligibility?.credibility_score}</p>
          </div>
        </div>
      </div>

      {/* Application Form */}
      <form onSubmit={handleSubmit} className="bg-white rounded-xl shadow-lg p-8">
        <div className="space-y-6">
          {/* Personal Information */}
          <div>
            <h3 className="text-lg font-semibold text-gray-800 mb-4">Personal Information</h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Full Name *</label>
                <input
                  type="text"
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  placeholder="Enter your full name"
                  required
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Email *</label>
                <input
                  type="email"
                  value={formData.email}
                  onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  placeholder="your@email.com"
                  required
                />
              </div>
              <div className="md:col-span-2">
                <label className="block text-sm font-medium text-gray-700 mb-1">Phone Number *</label>
                <input
                  type="tel"
                  value={formData.phone}
                  onChange={(e) => setFormData({ ...formData, phone: e.target.value })}
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  placeholder="+91 9876543210"
                  required
                />
              </div>
            </div>
          </div>

          {/* Location */}
          <div>
            <h3 className="text-lg font-semibold text-gray-800 mb-4">Primary Location</h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Coastal Zone *</label>
                <select
                  value={formData.coastal_zone}
                  onChange={(e) => setFormData({ ...formData, coastal_zone: e.target.value })}
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  required
                >
                  <option value="">Select Coastal Zone</option>
                  {coastalZones.map((zone) => (
                    <option key={zone} value={zone}>{zone}</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">State *</label>
                <select
                  value={formData.state}
                  onChange={(e) => setFormData({ ...formData, state: e.target.value })}
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  required
                >
                  <option value="">Select State</option>
                  {states.map((state) => (
                    <option key={state} value={state}>{state}</option>
                  ))}
                </select>
              </div>
            </div>
          </div>

          {/* Document Upload */}
          <div>
            <h3 className="text-lg font-semibold text-gray-800 mb-4">Identity Verification</h3>
            <p className="text-sm text-gray-600 mb-4">
              Please upload a copy of your Aadhaar card for verification. This will only be viewed by administrators.
            </p>
            <div className="border-2 border-dashed border-gray-300 rounded-lg p-6 text-center hover:border-blue-400 transition">
              <input
                type="file"
                id="aadhaar-upload"
                accept=".pdf,.jpg,.jpeg,.png"
                onChange={handleFileChange}
                className="hidden"
              />
              <label htmlFor="aadhaar-upload" className="cursor-pointer">
                {aadhaarFile ? (
                  <div className="space-y-2">
                    {filePreview ? (
                      <img src={filePreview} alt="Preview" className="h-32 mx-auto rounded-lg object-contain" />
                    ) : (
                      <FileText className="h-12 w-12 text-blue-500 mx-auto" />
                    )}
                    <p className="text-gray-700 font-medium">{aadhaarFile.name}</p>
                    <p className="text-sm text-gray-500">Click to change file</p>
                  </div>
                ) : (
                  <div className="space-y-2">
                    <Upload className="h-12 w-12 text-gray-400 mx-auto" />
                    <p className="text-gray-600">Click to upload Aadhaar document</p>
                    <p className="text-sm text-gray-500">PDF, JPG, PNG (max 5MB)</p>
                  </div>
                )}
              </label>
            </div>
          </div>

          {/* Submit Button */}
          <div className="pt-4">
            <button
              type="submit"
              disabled={isSubmitting}
              className="w-full py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition font-medium flex items-center justify-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isSubmitting ? (
                <>
                  <Loader2 className="h-5 w-5 animate-spin" />
                  Submitting Application...
                </>
              ) : (
                <>
                  <Award className="h-5 w-5" />
                  Submit Application
                </>
              )}
            </button>
          </div>
        </div>
      </form>

      {/* Benefits Section */}
      <div className="mt-8 bg-blue-50 rounded-xl p-6">
        <h3 className="font-semibold text-gray-800 mb-4">Benefits of Being a Verified Organizer</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="flex items-start gap-3">
            <Users className="h-5 w-5 text-blue-600 mt-0.5" />
            <div>
              <p className="font-medium text-gray-800">Create Communities</p>
              <p className="text-sm text-gray-600">Build and manage coastal conservation communities</p>
            </div>
          </div>
          <div className="flex items-start gap-3">
            <MapPin className="h-5 w-5 text-blue-600 mt-0.5" />
            <div>
              <p className="font-medium text-gray-800">Organize Events</p>
              <p className="text-sm text-gray-600">Create beach cleanups and awareness drives</p>
            </div>
          </div>
          <div className="flex items-start gap-3">
            <AlertTriangle className="h-5 w-5 text-blue-600 mt-0.5" />
            <div>
              <p className="font-medium text-gray-800">Emergency Response</p>
              <p className="text-sm text-gray-600">Get notified of hazards to coordinate responses</p>
            </div>
          </div>
          <div className="flex items-start gap-3">
            <Award className="h-5 w-5 text-blue-600 mt-0.5" />
            <div>
              <p className="font-medium text-gray-800">Earn Recognition</p>
              <p className="text-sm text-gray-600">Earn points and badges for your contributions</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default function OrganizerApplicationPage() {
  return (
    <ProtectedRoute>
      <DashboardLayout>
        <div className="py-6 px-4">
          <OrganizerApplicationContent />
        </div>
      </DashboardLayout>
    </ProtectedRoute>
  );
}
