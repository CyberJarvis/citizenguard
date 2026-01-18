'use client';

import ProtectedRoute from '@/components/ProtectedRoute';
import DashboardLayout from '@/components/DashboardLayout';
import useAuthStore from '@/context/AuthContext';
import { Settings, User, Bell, Shield, Globe, Palette, Lock, Mail, Smartphone } from 'lucide-react';
import PageHeader from '@/components/PageHeader';

function SettingsContent() {
  const { user } = useAuthStore();

  const settingsSections = [
    {
      id: 'profile',
      title: 'Profile Settings',
      icon: User,
      color: 'from-[#0d4a6f] to-[#1a6b9a]',
      items: [
        { label: 'Full Name', value: user?.name || 'Not set', type: 'text' },
        { label: 'Email Address', value: user?.email || 'Not set', type: 'email' },
        { label: 'Phone Number', value: 'Not set', type: 'phone' },
        { label: 'Bio', value: 'Not set', type: 'textarea' },
      ]
    },
    {
      id: 'notifications',
      title: 'Notifications',
      icon: Bell,
      color: 'from-purple-500 to-pink-500',
      items: [
        { label: 'Email Notifications', value: true, type: 'toggle' },
        { label: 'Push Notifications', value: false, type: 'toggle' },
        { label: 'SMS Alerts', value: false, type: 'toggle' },
        { label: 'Report Updates', value: true, type: 'toggle' },
      ]
    },
    {
      id: 'privacy',
      title: 'Privacy & Security',
      icon: Shield,
      color: 'from-green-500 to-emerald-500',
      items: [
        { label: 'Profile Visibility', value: 'Public', type: 'select' },
        { label: 'Two-Factor Authentication', value: false, type: 'toggle' },
        { label: 'Share Location', value: true, type: 'toggle' },
        { label: 'Data Sharing', value: false, type: 'toggle' },
      ]
    },
  ];

  return (
    <div className="p-4 lg:p-8">
      <div className="max-w-4xl mx-auto">
        {/* Top Icons Bar */}
        <PageHeader />

        {/* Page Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-semibold text-gray-900 mb-2">Settings</h1>
          <p className="text-gray-600">Manage your account preferences and settings</p>
        </div>

        {/* Settings Sections */}
        <div className="space-y-6">
          {settingsSections.map((section) => {
            const Icon = section.icon;
            return (
              <div key={section.id} className="bg-white rounded-2xl shadow-sm border border-gray-200 overflow-hidden">
                {/* Section Header */}
                <div className={`bg-gradient-to-r ${section.color} p-6 text-white`}>
                  <div className="flex items-center space-x-3">
                    <div className="w-12 h-12 bg-white bg-opacity-20 rounded-xl flex items-center justify-center">
                      <Icon className="w-6 h-6 text-white" />
                    </div>
                    <h2 className="text-xl font-semibold">{section.title}</h2>
                  </div>
                </div>

                {/* Section Content */}
                <div className="p-6 space-y-4">
                  {section.items.map((item, index) => (
                    <div key={index} className="flex items-center justify-between py-3 border-b border-gray-100 last:border-0">
                      <div className="flex-1">
                        <label className="text-sm font-medium text-gray-900">{item.label}</label>
                        {item.type === 'text' || item.type === 'email' || item.type === 'phone' ? (
                          <p className="text-sm text-gray-600 mt-1">{item.value}</p>
                        ) : null}
                      </div>
                      <div>
                        {item.type === 'toggle' ? (
                          <button
                            className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
                              item.value ? 'bg-[#0d4a6f]' : 'bg-gray-200'
                            }`}
                          >
                            <span
                              className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                                item.value ? 'translate-x-6' : 'translate-x-1'
                              }`}
                            />
                          </button>
                        ) : item.type === 'select' ? (
                          <select className="px-4 py-2 bg-gray-50 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-[#1a6b9a]">
                            <option>{item.value}</option>
                            <option>Private</option>
                            <option>Friends Only</option>
                          </select>
                        ) : (
                          <button className="px-4 py-2 bg-gray-100 hover:bg-gray-200 text-gray-700 rounded-lg text-sm font-medium transition-colors">
                            Edit
                          </button>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            );
          })}

          {/* Additional Settings */}
          <div className="bg-white rounded-2xl shadow-sm border border-gray-200 p-6">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">Additional Settings</h3>
            <div className="space-y-3">
              <button className="w-full flex items-center justify-between p-4 bg-gray-50 rounded-xl hover:bg-gray-100 transition-colors">
                <div className="flex items-center space-x-3">
                  <Globe className="w-5 h-5 text-gray-600" />
                  <div className="text-left">
                    <p className="text-sm font-semibold text-gray-900">Language & Region</p>
                    <p className="text-xs text-gray-600">English (US)</p>
                  </div>
                </div>
              </button>

              <button className="w-full flex items-center justify-between p-4 bg-gray-50 rounded-xl hover:bg-gray-100 transition-colors">
                <div className="flex items-center space-x-3">
                  <Palette className="w-5 h-5 text-gray-600" />
                  <div className="text-left">
                    <p className="text-sm font-semibold text-gray-900">Appearance</p>
                    <p className="text-xs text-gray-600">System default</p>
                  </div>
                </div>
              </button>

              <button className="w-full flex items-center justify-between p-4 bg-gray-50 rounded-xl hover:bg-gray-100 transition-colors">
                <div className="flex items-center space-x-3">
                  <Lock className="w-5 h-5 text-gray-600" />
                  <div className="text-left">
                    <p className="text-sm font-semibold text-gray-900">Change Password</p>
                    <p className="text-xs text-gray-600">Update your password</p>
                  </div>
                </div>
              </button>
            </div>
          </div>

          {/* Danger Zone */}
          <div className="bg-white rounded-2xl shadow-sm border border-red-200 overflow-hidden">
            <div className="bg-red-50 border-b border-red-200 p-6">
              <h3 className="text-lg font-bold text-red-900">Danger Zone</h3>
              <p className="text-sm text-red-700 mt-1">Irreversible actions that affect your account</p>
            </div>
            <div className="p-6 space-y-3">
              <button className="w-full p-4 bg-red-50 hover:bg-red-100 text-red-700 rounded-xl text-sm font-semibold transition-colors">
                Deactivate Account
              </button>
              <button className="w-full p-4 bg-red-100 hover:bg-red-200 text-red-900 rounded-xl text-sm font-semibold transition-colors">
                Delete Account Permanently
              </button>
            </div>
          </div>

          {/* Save Button */}
          <div className="flex items-center justify-end space-x-3">
            <button className="px-6 py-3 bg-white border border-gray-300 rounded-xl text-gray-700 font-semibold hover:bg-gray-50 transition-colors">
              Cancel
            </button>
            <button className="px-6 py-3 bg-gradient-to-r from-blue-600 to-blue-700 text-white rounded-xl font-semibold hover:from-blue-700 hover:to-blue-800 transition-all shadow-lg shadow-blue-200">
              Save Changes
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

export default function SettingsPage() {
  return (
    <ProtectedRoute>
      <DashboardLayout>
        <SettingsContent />
      </DashboardLayout>
    </ProtectedRoute>
  );
}
