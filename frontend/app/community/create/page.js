'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import ProtectedRoute from '@/components/ProtectedRoute';
import DashboardLayout from '@/components/DashboardLayout';
import {
  ArrowLeft,
  Building2,
  MapPin,
  FileText,
  Image as ImageIcon,
  Loader2,
  Upload,
  X,
  Check
} from 'lucide-react';
import { createCommunity, getCommunityFilterOptions, uploadCommunityImage } from '@/lib/api';
import toast from 'react-hot-toast';
import Cookies from 'js-cookie';
import { jwtDecode } from 'jwt-decode';

const CATEGORIES = [
  { value: 'cleanup', label: 'Beach Cleanup', description: 'Organize coastal and beach cleanup drives' },
  { value: 'animal_rescue', label: 'Animal Rescue', description: 'Marine life protection and rescue operations' },
  { value: 'awareness', label: 'Awareness', description: 'Educational programs and awareness campaigns' },
  { value: 'general', label: 'General', description: 'General coastal conservation activities' }
];

function CreateCommunityContent() {
  const router = useRouter();
  const [currentUser, setCurrentUser] = useState(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [filterOptions, setFilterOptions] = useState(null);

  // Form state
  const [formData, setFormData] = useState({
    name: '',
    description: '',
    category: 'cleanup',
    coastal_zone: '',
    state: '',
    is_public: true
  });

  // Image preview
  const [coverPreview, setCoverPreview] = useState(null);
  const [logoPreview, setLogoPreview] = useState(null);
  const [coverFile, setCoverFile] = useState(null);
  const [logoFile, setLogoFile] = useState(null);

  // Get current user
  useEffect(() => {
    const token = Cookies.get('access_token');
    if (token) {
      try {
        const decoded = jwtDecode(token);
        const role = (decoded.role || 'CITIZEN').toUpperCase();
        setCurrentUser({
          user_id: decoded.sub || decoded.user_id,
          name: decoded.name || decoded.user_name || 'User',
          role
        });

        // Check if user is organizer
        if (!['VERIFIED_ORGANIZER', 'AUTHORITY', 'AUTHORITY_ADMIN'].includes(role)) {
          toast.error('Only verified organizers can create communities');
          router.push('/community');
        }
      } catch (err) {
        console.error('Error decoding token:', err);
        router.push('/login');
      }
    }
  }, [router]);

  // Load filter options
  useEffect(() => {
    const loadFilters = async () => {
      try {
        const response = await getCommunityFilterOptions();
        if (response.success) {
          setFilterOptions({
            coastal_zones: response.coastal_zones,
            states: response.states
          });
        }
      } catch (error) {
        console.error('Error loading filters:', error);
      }
    };
    loadFilters();
  }, []);

  const handleInputChange = (e) => {
    const { name, value, type, checked } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: type === 'checkbox' ? checked : value
    }));
  };

  const handleImageChange = (e, type) => {
    const file = e.target.files[0];
    if (!file) return;

    // Validate file type
    if (!file.type.startsWith('image/')) {
      toast.error('Please select an image file');
      return;
    }

    // Validate file size (2MB max)
    if (file.size > 2 * 1024 * 1024) {
      toast.error('Image size must be less than 2MB');
      return;
    }

    // Create preview
    const reader = new FileReader();
    reader.onloadend = () => {
      if (type === 'cover') {
        setCoverPreview(reader.result);
        setCoverFile(file);
      } else {
        setLogoPreview(reader.result);
        setLogoFile(file);
      }
    };
    reader.readAsDataURL(file);
  };

  const removeImage = (type) => {
    if (type === 'cover') {
      setCoverPreview(null);
      setCoverFile(null);
    } else {
      setLogoPreview(null);
      setLogoFile(null);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();

    // Validation
    if (!formData.name.trim()) {
      toast.error('Please enter a community name');
      return;
    }
    if (!formData.description.trim()) {
      toast.error('Please enter a description');
      return;
    }
    if (!formData.coastal_zone) {
      toast.error('Please select a coastal zone');
      return;
    }
    if (!formData.state) {
      toast.error('Please select a state');
      return;
    }

    setIsSubmitting(true);

    try {
      // Create community
      const response = await createCommunity({
        name: formData.name.trim(),
        description: formData.description.trim(),
        category: formData.category,
        coastal_zone: formData.coastal_zone,
        state: formData.state,
        is_public: formData.is_public
      });

      if (response.success) {
        const communityId = response.community.community_id;

        // Upload images if provided
        if (coverFile) {
          try {
            await uploadCommunityImage(communityId, coverFile, 'cover');
          } catch (imgError) {
            console.error('Error uploading cover image:', imgError);
            toast.error('Community created but cover image upload failed');
          }
        }

        if (logoFile) {
          try {
            await uploadCommunityImage(communityId, logoFile, 'logo');
          } catch (imgError) {
            console.error('Error uploading logo:', imgError);
            toast.error('Community created but logo upload failed');
          }
        }

        toast.success('Community created successfully!');
        router.push(`/community/${communityId}`);
      }
    } catch (error) {
      console.error('Error creating community:', error);
      toast.error(error.response?.data?.detail || 'Failed to create community');
    } finally {
      setIsSubmitting(false);
    }
  };

  if (!currentUser) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <Loader2 className="w-8 h-8 text-blue-600 animate-spin" />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 py-8">
      <div className="max-w-3xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Header */}
        <div className="mb-8">
          <Link
            href="/community"
            className="inline-flex items-center gap-2 text-gray-600 hover:text-gray-800 mb-4"
          >
            <ArrowLeft className="w-4 h-4" />
            Back to Community Hub
          </Link>
          <h1 className="text-2xl sm:text-3xl font-bold text-gray-900">Create Community</h1>
          <p className="text-gray-600 mt-1">
            Start a new coastal conservation community in your area
          </p>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} className="space-y-6">
          {/* Basic Info */}
          <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-6">
            <h2 className="text-lg font-semibold text-gray-800 mb-4 flex items-center gap-2">
              <Building2 className="w-5 h-5 text-blue-600" />
              Basic Information
            </h2>

            <div className="space-y-4">
              {/* Name */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Community Name <span className="text-red-500">*</span>
                </label>
                <input
                  type="text"
                  name="name"
                  value={formData.name}
                  onChange={handleInputChange}
                  placeholder="e.g., Mumbai Coastal Cleanup Crew"
                  className="w-full px-4 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  maxLength={100}
                />
                <p className="text-xs text-gray-500 mt-1">{formData.name.length}/100 characters</p>
              </div>

              {/* Description */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Description <span className="text-red-500">*</span>
                </label>
                <textarea
                  name="description"
                  value={formData.description}
                  onChange={handleInputChange}
                  placeholder="Describe your community's mission and activities..."
                  rows={4}
                  className="w-full px-4 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 resize-none"
                  maxLength={500}
                />
                <p className="text-xs text-gray-500 mt-1">{formData.description.length}/500 characters</p>
              </div>

              {/* Category */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Category <span className="text-red-500">*</span>
                </label>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  {CATEGORIES.map(cat => (
                    <label
                      key={cat.value}
                      className={`relative flex items-start p-4 border rounded-lg cursor-pointer transition ${
                        formData.category === cat.value
                          ? 'border-blue-500 bg-blue-50 ring-2 ring-blue-500'
                          : 'border-gray-200 hover:border-gray-300'
                      }`}
                    >
                      <input
                        type="radio"
                        name="category"
                        value={cat.value}
                        checked={formData.category === cat.value}
                        onChange={handleInputChange}
                        className="sr-only"
                      />
                      <div className="flex-1">
                        <span className="block font-medium text-gray-800">{cat.label}</span>
                        <span className="text-xs text-gray-500">{cat.description}</span>
                      </div>
                      {formData.category === cat.value && (
                        <Check className="w-5 h-5 text-blue-600 flex-shrink-0" />
                      )}
                    </label>
                  ))}
                </div>
              </div>
            </div>
          </div>

          {/* Location */}
          <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-6">
            <h2 className="text-lg font-semibold text-gray-800 mb-4 flex items-center gap-2">
              <MapPin className="w-5 h-5 text-blue-600" />
              Location
            </h2>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              {/* Coastal Zone */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Coastal Zone <span className="text-red-500">*</span>
                </label>
                <select
                  name="coastal_zone"
                  value={formData.coastal_zone}
                  onChange={handleInputChange}
                  className="w-full px-4 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                >
                  <option value="">Select a zone</option>
                  {filterOptions?.coastal_zones?.map(zone => (
                    <option key={zone} value={zone}>{zone}</option>
                  ))}
                </select>
              </div>

              {/* State */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  State <span className="text-red-500">*</span>
                </label>
                <select
                  name="state"
                  value={formData.state}
                  onChange={handleInputChange}
                  className="w-full px-4 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                >
                  <option value="">Select a state</option>
                  {filterOptions?.states?.map(state => (
                    <option key={state} value={state}>{state}</option>
                  ))}
                </select>
              </div>
            </div>
          </div>

          {/* Images */}
          <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-6">
            <h2 className="text-lg font-semibold text-gray-800 mb-4 flex items-center gap-2">
              <ImageIcon className="w-5 h-5 text-blue-600" />
              Images
            </h2>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-6">
              {/* Cover Image */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Cover Image
                </label>
                {coverPreview ? (
                  <div className="relative">
                    <img
                      src={coverPreview}
                      alt="Cover preview"
                      className="w-full h-32 object-cover rounded-lg"
                    />
                    <button
                      type="button"
                      onClick={() => removeImage('cover')}
                      className="absolute top-2 right-2 p-1 bg-red-500 text-white rounded-full hover:bg-red-600"
                    >
                      <X className="w-4 h-4" />
                    </button>
                  </div>
                ) : (
                  <label className="flex flex-col items-center justify-center h-32 border-2 border-dashed border-gray-300 rounded-lg cursor-pointer hover:border-gray-400 transition">
                    <Upload className="w-8 h-8 text-gray-400 mb-2" />
                    <span className="text-sm text-gray-500">Upload cover image</span>
                    <span className="text-xs text-gray-400">Max 2MB</span>
                    <input
                      type="file"
                      accept="image/*"
                      onChange={(e) => handleImageChange(e, 'cover')}
                      className="hidden"
                    />
                  </label>
                )}
              </div>

              {/* Logo */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Logo
                </label>
                {logoPreview ? (
                  <div className="relative w-32">
                    <img
                      src={logoPreview}
                      alt="Logo preview"
                      className="w-32 h-32 object-cover rounded-lg"
                    />
                    <button
                      type="button"
                      onClick={() => removeImage('logo')}
                      className="absolute top-2 right-2 p-1 bg-red-500 text-white rounded-full hover:bg-red-600"
                    >
                      <X className="w-4 h-4" />
                    </button>
                  </div>
                ) : (
                  <label className="flex flex-col items-center justify-center w-32 h-32 border-2 border-dashed border-gray-300 rounded-lg cursor-pointer hover:border-gray-400 transition">
                    <Upload className="w-6 h-6 text-gray-400 mb-1" />
                    <span className="text-xs text-gray-500 text-center">Upload logo</span>
                    <input
                      type="file"
                      accept="image/*"
                      onChange={(e) => handleImageChange(e, 'logo')}
                      className="hidden"
                    />
                  </label>
                )}
              </div>
            </div>
          </div>

          {/* Visibility */}
          <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-6">
            <h2 className="text-lg font-semibold text-gray-800 mb-4 flex items-center gap-2">
              <FileText className="w-5 h-5 text-blue-600" />
              Settings
            </h2>

            <label className="flex items-start gap-3 cursor-pointer">
              <input
                type="checkbox"
                name="is_public"
                checked={formData.is_public}
                onChange={handleInputChange}
                className="mt-1 w-4 h-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500"
              />
              <div>
                <span className="block font-medium text-gray-800">Public Community</span>
                <span className="text-sm text-gray-500">
                  Anyone can view and join this community. Uncheck to make it private.
                </span>
              </div>
            </label>
          </div>

          {/* Submit */}
          <div className="flex items-center justify-end gap-4">
            <Link
              href="/community"
              className="px-6 py-2.5 border border-gray-300 rounded-lg font-medium text-gray-700 hover:bg-gray-50 transition"
            >
              Cancel
            </Link>
            <button
              type="submit"
              disabled={isSubmitting}
              className="px-6 py-2.5 bg-blue-600 text-white rounded-lg font-medium hover:bg-blue-700 transition disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
            >
              {isSubmitting ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  Creating...
                </>
              ) : (
                <>
                  <Building2 className="w-4 h-4" />
                  Create Community
                </>
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

export default function CreateCommunityPage() {
  return (
    <ProtectedRoute>
      <DashboardLayout>
        <CreateCommunityContent />
      </DashboardLayout>
    </ProtectedRoute>
  );
}
