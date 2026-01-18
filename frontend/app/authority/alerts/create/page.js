'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import DashboardLayout from '@/components/DashboardLayout';
import PageHeader from '@/components/PageHeader';
import useAuthStore from '@/context/AuthContext';
import api from '@/lib/api';
import {
  AlertTriangle,
  Bell,
  ChevronLeft,
  MapPin,
  Calendar,
  FileText,
  Phone
} from 'lucide-react';

const ALERT_TYPES = [
  { value: 'tsunami', label: 'Tsunami' },
  { value: 'cyclone', label: 'Cyclone' },
  { value: 'high_waves', label: 'High Waves' },
  { value: 'storm_surge', label: 'Storm Surge' },
  { value: 'coastal_flooding', label: 'Coastal Flooding' },
  { value: 'coastal_erosion', label: 'Coastal Erosion' },
  { value: 'rip_current', label: 'Rip Current' },
  { value: 'oil_spill', label: 'Oil Spill' },
  { value: 'chemical_spill', label: 'Chemical Spill' },
  { value: 'algal_bloom', label: 'Algal Bloom' },
  { value: 'sea_level_rise', label: 'Sea Level Rise' },
  { value: 'marine_pollution', label: 'Marine Pollution' },
  { value: 'weather_warning', label: 'Weather Warning' },
  { value: 'general', label: 'General' },
  { value: 'other', label: 'Other' }
];

const SEVERITY_LEVELS = [
  { value: 'info', label: 'Info', description: 'General information', color: 'blue' },
  { value: 'low', label: 'Low', description: 'Minor concern', color: 'yellow' },
  { value: 'medium', label: 'Medium', description: 'Moderate risk', color: 'orange' },
  { value: 'high', label: 'High', description: 'Significant threat', color: 'red' },
  { value: 'critical', label: 'Critical', description: 'Extreme danger', color: 'red' }
];

const INDIAN_COASTAL_REGIONS = [
  'West Bengal',
  'Odisha',
  'Andhra Pradesh',
  'Tamil Nadu',
  'Puducherry',
  'Kerala',
  'Karnataka',
  'Goa',
  'Maharashtra',
  'Gujarat',
  'Daman and Diu',
  'Andaman and Nicobar Islands',
  'Lakshadweep'
];

export default function CreateAlert() {
  const router = useRouter();
  const { user, isLoading: authLoading } = useAuthStore();

  const [formData, setFormData] = useState({
    title: '',
    description: '',
    alert_type: '',
    severity: '',
    regions: [],
    expires_at: '',
    instructions: '',
    contact_info: '',
    tags: '',
    priority: 1
  });

  const [submitting, setSubmitting] = useState(false);

  // Check if user is authority or admin
  if (!authLoading && user && user.role !== 'authority' && user.role !== 'authority_admin') {
    router.push('/dashboard');
    return null;
  }

  const handleChange = (field, value) => {
    setFormData(prev => ({ ...prev, [field]: value }));
  };

  const handleRegionToggle = (region) => {
    setFormData(prev => ({
      ...prev,
      regions: prev.regions.includes(region)
        ? prev.regions.filter(r => r !== region)
        : [...prev.regions, region]
    }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();

    // Validation
    if (!formData.title || !formData.description || !formData.alert_type || !formData.severity) {
      alert('Please fill in all required fields');
      return;
    }

    if (formData.regions.length === 0) {
      alert('Please select at least one affected region');
      return;
    }

    // Validate title length (min 5, max 200)
    const title = formData.title.trim();
    if (title.length < 5) {
      alert('Title must be at least 5 characters long');
      return;
    }
    if (title.length > 200) {
      alert('Title must not exceed 200 characters');
      return;
    }

    // Validate description length (min 10, max 2000)
    const description = formData.description.trim();
    if (description.length < 10) {
      alert('Description must be at least 10 characters long');
      return;
    }
    if (description.length > 2000) {
      alert('Description must not exceed 2000 characters');
      return;
    }

    // Prepare payload outside try block for error logging
    let payload = null;

    try {
      setSubmitting(true);

      // Prepare payload matching AlertCreate model exactly
      payload = {
        title: title,
        description: description,
        alert_type: formData.alert_type,
        severity: formData.severity,
        regions: formData.regions,
        priority: parseInt(formData.priority) || 3,
        tags: formData.tags ? formData.tags.split(',').map(t => t.trim()).filter(t => t) : [],
        coordinates: null,
        expires_at: null,
        instructions: null,
        contact_info: null
      };

      // Add optional fields with proper values
      if (formData.expires_at) {
        payload.expires_at = new Date(formData.expires_at).toISOString();
      }
      if (formData.instructions?.trim()) {
        payload.instructions = formData.instructions.trim();
      }
      if (formData.contact_info?.trim()) {
        payload.contact_info = formData.contact_info.trim();
      }

      console.log('Sending payload:', JSON.stringify(payload, null, 2));
      const response = await api.post('/alerts', payload);

      alert('Alert created successfully!');
      router.push('/authority/alerts');

    } catch (error) {
      console.error('Error creating alert:', error);
      console.error('Error response:', error.response?.data);
      console.error('Payload sent:', JSON.stringify(payload, null, 2));

      // Display detailed validation errors
      const errorDetail = error.response?.data?.detail;
      if (Array.isArray(errorDetail)) {
        // Pydantic validation errors
        const errors = errorDetail.map(err => {
          const location = err.loc.join(' -> ');
          return `${location}: ${err.msg}`;
        }).join('\n');
        alert(`Validation errors:\n\n${errors}`);
      } else if (errorDetail) {
        alert(`Error: ${errorDetail}`);
      } else {
        alert('Failed to create alert. Please check the console for details.');
      }
    } finally {
      setSubmitting(false);
    }
  };

  const getSeverityColor = (severity) => {
    const colors = {
      info: 'bg-blue-100 border-blue-300 text-blue-900',
      low: 'bg-yellow-100 border-yellow-300 text-yellow-900',
      medium: 'bg-orange-100 border-orange-300 text-orange-900',
      high: 'bg-red-100 border-red-300 text-red-900',
      critical: 'bg-red-200 border-red-400 text-red-900'
    };
    return colors[severity] || 'bg-gray-100 border-gray-300 text-gray-900';
  };

  if (authLoading || !user) {
    return (
      <DashboardLayout>
        <div className="flex items-center justify-center min-h-screen">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-[#0d4a6f]"></div>
        </div>
      </DashboardLayout>
    );
  }

  return (
    <DashboardLayout>
      <div className="p-6 space-y-6">
        {/* Page Header - Desktop Only */}
        <PageHeader />

        {/* Header */}
        <div className="flex items-center gap-4">
          <button
            onClick={() => router.push('/authority/alerts')}
            className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
          >
            <ChevronLeft className="w-6 h-6" />
          </button>
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Create New Alert</h1>
            <p className="text-gray-600">Publish a hazard alert to notify affected regions</p>
          </div>
        </div>

        <form onSubmit={handleSubmit} className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Left Column - Form Fields */}
          <div className="lg:col-span-2 space-y-6">
            {/* Basic Information */}
            <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
              <h2 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
                <FileText className="w-5 h-5 text-[#0d4a6f]" />
                Alert Details
              </h2>

              <div className="space-y-4">
                {/* Title */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Alert Title *
                  </label>
                  <input
                    type="text"
                    value={formData.title}
                    onChange={(e) => handleChange('title', e.target.value)}
                    className="w-full px-4 py-2 border border-gray-300 rounded-xl focus:ring-2 focus:ring-[#1a6b9a]"
                    placeholder="e.g., Cyclone Warning for Odisha Coast"
                    required
                  />
                </div>

                {/* Description */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Description *
                  </label>
                  <textarea
                    value={formData.description}
                    onChange={(e) => handleChange('description', e.target.value)}
                    className="w-full px-4 py-2 border border-gray-300 rounded-xl focus:ring-2 focus:ring-[#1a6b9a]"
                    rows="4"
                    placeholder="Detailed description of the hazard and its expected impact..."
                    required
                  />
                </div>

                {/* Alert Type */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Alert Type *
                  </label>
                  <select
                    value={formData.alert_type}
                    onChange={(e) => handleChange('alert_type', e.target.value)}
                    className="w-full px-4 py-2 border border-gray-300 rounded-xl focus:ring-2 focus:ring-[#1a6b9a]"
                    required
                  >
                    <option value="">Select alert type</option>
                    {ALERT_TYPES.map(type => (
                      <option key={type.value} value={type.value}>
                        {type.label}
                      </option>
                    ))}
                  </select>
                </div>

                {/* Severity */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Severity Level *
                  </label>
                  <div className="grid grid-cols-5 gap-2">
                    {SEVERITY_LEVELS.map(level => (
                      <button
                        key={level.value}
                        type="button"
                        onClick={() => handleChange('severity', level.value)}
                        className={`p-3 border-2 rounded-lg transition-all ${
                          formData.severity === level.value
                            ? getSeverityColor(level.value)
                            : 'border-gray-300 bg-white text-gray-700 hover:bg-gray-50'
                        }`}
                      >
                        <div className="text-sm font-semibold">{level.label}</div>
                        <div className="text-xs mt-1 opacity-75">{level.description}</div>
                      </button>
                    ))}
                  </div>
                </div>

                {/* Priority */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Priority Level (1-5)
                  </label>
                  <input
                    type="number"
                    min="1"
                    max="5"
                    value={formData.priority}
                    onChange={(e) => handleChange('priority', e.target.value)}
                    className="w-full px-4 py-2 border border-gray-300 rounded-xl focus:ring-2 focus:ring-[#1a6b9a]"
                  />
                  <p className="text-xs text-gray-600 mt-1">1 = Lowest, 5 = Highest priority</p>
                </div>
              </div>
            </div>

            {/* Affected Regions */}
            <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
              <h2 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
                <MapPin className="w-5 h-5 text-[#0d4a6f]" />
                Affected Regions *
              </h2>

              <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
                {INDIAN_COASTAL_REGIONS.map(region => (
                  <button
                    key={region}
                    type="button"
                    onClick={() => handleRegionToggle(region)}
                    className={`p-3 border-2 rounded-xl text-sm font-medium transition-colors ${
                      formData.regions.includes(region)
                        ? 'border-[#1a6b9a] bg-[#e8f4fc] text-[#0d4a6f]'
                        : 'border-gray-300 bg-white text-gray-700 hover:bg-gray-50'
                    }`}
                  >
                    {region}
                  </button>
                ))}
              </div>

              {formData.regions.length > 0 && (
                <div className="mt-4 p-3 bg-[#e8f4fc] border border-[#c5e1f5] rounded-xl">
                  <p className="text-sm font-medium text-[#083a57]">
                    Selected: {formData.regions.join(', ')}
                  </p>
                </div>
              )}
            </div>

            {/* Additional Information */}
            <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
              <h2 className="text-lg font-semibold text-gray-900 mb-4">
                Additional Information
              </h2>

              <div className="space-y-4">
                {/* Instructions */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Safety Instructions
                  </label>
                  <textarea
                    value={formData.instructions}
                    onChange={(e) => handleChange('instructions', e.target.value)}
                    className="w-full px-4 py-2 border border-gray-300 rounded-xl focus:ring-2 focus:ring-[#1a6b9a]"
                    rows="3"
                    placeholder="What actions should people take? Safety measures to follow..."
                  />
                </div>

                {/* Contact Info */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2 flex items-center gap-1">
                    <Phone className="w-4 h-4" />
                    Emergency Contact Information
                  </label>
                  <input
                    type="text"
                    value={formData.contact_info}
                    onChange={(e) => handleChange('contact_info', e.target.value)}
                    className="w-full px-4 py-2 border border-gray-300 rounded-xl focus:ring-2 focus:ring-[#1a6b9a]"
                    placeholder="e.g., Emergency Hotline: 1800-XXX-XXXX"
                  />
                </div>

                {/* Expiry Date */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2 flex items-center gap-1">
                    <Calendar className="w-4 h-4" />
                    Expiry Date (Optional)
                  </label>
                  <input
                    type="datetime-local"
                    value={formData.expires_at}
                    onChange={(e) => handleChange('expires_at', e.target.value)}
                    className="w-full px-4 py-2 border border-gray-300 rounded-xl focus:ring-2 focus:ring-[#1a6b9a]"
                  />
                  <p className="text-xs text-gray-600 mt-1">Leave empty if alert has no expiry</p>
                </div>

                {/* Tags */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Tags (comma-separated)
                  </label>
                  <input
                    type="text"
                    value={formData.tags}
                    onChange={(e) => handleChange('tags', e.target.value)}
                    className="w-full px-4 py-2 border border-gray-300 rounded-xl focus:ring-2 focus:ring-[#1a6b9a]"
                    placeholder="e.g., urgent, evacuation, fishermen"
                  />
                </div>
              </div>
            </div>
          </div>

          {/* Right Column - Preview & Submit */}
          <div className="lg:col-span-1">
            <div className="bg-white rounded-xl shadow-lg border border-gray-200 p-6 sticky top-6">
              <h2 className="text-lg font-semibold text-gray-900 mb-4">Preview</h2>

              {/* Preview Card */}
              <div className={`p-4 border-2 rounded-xl mb-6 ${
                formData.severity ? getSeverityColor(formData.severity) : 'border-gray-300 bg-gray-50'
              }`}>
                <div className="flex items-center gap-2 mb-2">
                  <AlertTriangle className="w-5 h-5" />
                  {formData.severity && (
                    <span className="text-xs font-bold uppercase">{formData.severity}</span>
                  )}
                </div>
                <h3 className="font-bold text-lg mb-2">
                  {formData.title || 'Alert Title'}
                </h3>
                <p className="text-sm mb-3">
                  {formData.description || 'Alert description will appear here...'}
                </p>
                {formData.regions.length > 0 && (
                  <div className="text-sm">
                    <span className="font-medium">Regions:</span> {formData.regions.join(', ')}
                  </div>
                )}
              </div>

              {/* Submit Button */}
              <button
                type="submit"
                disabled={submitting}
                className="w-full py-3 px-4 bg-[#0d4a6f] text-white rounded-xl font-medium hover:bg-[#083a57] transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
              >
                {submitting ? (
                  <>
                    <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-white"></div>
                    Creating...
                  </>
                ) : (
                  <>
                    <Bell className="w-5 h-5" />
                    Publish Alert
                  </>
                )}
              </button>

              {/* Info */}
              <div className="mt-4 p-3 bg-[#e8f4fc] border border-[#c5e1f5] rounded-xl">
                <p className="text-xs text-[#083a57]">
                  <strong>Note:</strong> This alert will be immediately visible to all users in the selected regions.
                </p>
              </div>
            </div>
          </div>
        </form>
      </div>
    </DashboardLayout>
  );
}
