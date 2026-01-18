'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import DashboardLayout from '@/components/DashboardLayout';
import PageHeader from '@/components/PageHeader';
import useAuthStore from '@/context/AuthContext';
import api from '@/lib/api';
import toast from 'react-hot-toast';
import {
  Settings,
  Shield,
  RefreshCw,
  Save,
  X,
  Edit2,
  Plus,
  Trash2,
  Globe,
  Bell,
  Lock,
  Mail,
  Database,
  Zap,
  AlertCircle,
  Check
} from 'lucide-react';

export default function AdminSettingsPage() {
  const router = useRouter();
  const { user, isLoading: authLoading } = useAuthStore();

  // Settings state
  const [settings, setSettings] = useState({});
  const [loading, setLoading] = useState(true);
  const [selectedCategory, setSelectedCategory] = useState('general');

  // Edit state
  const [editingKey, setEditingKey] = useState(null);
  const [editValue, setEditValue] = useState('');

  // Create modal state
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [newSetting, setNewSetting] = useState({
    key: '',
    value: '',
    category: 'general',
    value_type: 'string',
    description: ''
  });

  // Delete confirmation
  const [deleteConfirm, setDeleteConfirm] = useState(null);

  const categories = [
    { id: 'general', label: 'General', icon: Globe },
    { id: 'notifications', label: 'Notifications', icon: Bell },
    { id: 'security', label: 'Security', icon: Lock },
    { id: 'email', label: 'Email', icon: Mail },
    { id: 'storage', label: 'Storage', icon: Database },
    { id: 'performance', label: 'Performance', icon: Zap }
  ];

  useEffect(() => {
    if (!authLoading && user) {
      if (user.role !== 'authority_admin') {
        toast.error('Access denied. Admin privileges required.');
        router.push('/dashboard');
      } else {
        fetchSettings();
      }
    }
  }, [user, authLoading, router]);

  const fetchSettings = async () => {
    try {
      setLoading(true);
      const response = await api.get('/admin/settings');
      // Handle different response formats
      const data = response.data?.data || response.data || {};
      setSettings(typeof data === 'object' && data !== null ? data : {});
    } catch (error) {
      console.error('Error fetching settings:', error);
      toast.error('Failed to load settings');
      setSettings({});
    } finally {
      setLoading(false);
    }
  };

  const handleEditStart = (setting) => {
    setEditingKey(setting.key);
    setEditValue(setting.value);
  };

  const handleEditCancel = () => {
    setEditingKey(null);
    setEditValue('');
  };

  const handleEditSave = async (key) => {
    try {
      await api.put(`/admin/settings/${key}`, { value: editValue });
      toast.success('Setting updated successfully');
      setEditingKey(null);
      setEditValue('');
      fetchSettings();
    } catch (error) {
      toast.error('Failed to update setting');
    }
  };

  const handleCreateSetting = async () => {
    if (!newSetting.key || !newSetting.value) {
      toast.error('Key and value are required');
      return;
    }

    try {
      await api.post('/admin/settings', newSetting);
      toast.success('Setting created successfully');
      setShowCreateModal(false);
      setNewSetting({
        key: '',
        value: '',
        category: 'general',
        value_type: 'string',
        description: ''
      });
      fetchSettings();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to create setting');
    }
  };

  const handleDeleteSetting = async (key) => {
    try {
      await api.delete(`/admin/settings/${key}`);
      toast.success('Setting deleted successfully');
      setDeleteConfirm(null);
      fetchSettings();
    } catch (error) {
      toast.error('Failed to delete setting');
    }
  };

  const renderSettingValue = (setting) => {
    if (editingKey === setting.key) {
      return (
        <div className="flex items-center gap-2">
          {setting.value_type === 'boolean' ? (
            <select
              value={editValue}
              onChange={(e) => setEditValue(e.target.value)}
              className="border border-gray-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-[#1a6b9a] focus:border-[#1a6b9a]"
            >
              <option value="true">True</option>
              <option value="false">False</option>
            </select>
          ) : setting.value_type === 'number' ? (
            <input
              type="number"
              value={editValue}
              onChange={(e) => setEditValue(e.target.value)}
              className="border border-gray-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-[#1a6b9a] focus:border-[#1a6b9a] w-32"
            />
          ) : (
            <input
              type="text"
              value={editValue}
              onChange={(e) => setEditValue(e.target.value)}
              className="border border-gray-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-[#1a6b9a] focus:border-[#1a6b9a] flex-1"
            />
          )}
          <button
            onClick={() => handleEditSave(setting.key)}
            className="p-2 text-green-600 hover:bg-green-50 rounded-lg transition-colors"
            title="Save"
          >
            <Check className="w-4 h-4" />
          </button>
          <button
            onClick={handleEditCancel}
            className="p-2 text-gray-500 hover:bg-gray-100 rounded-lg transition-colors"
            title="Cancel"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
      );
    }

    if (setting.value_type === 'boolean') {
      return (
        <span className={`px-2 py-1 text-xs font-medium rounded-full ${
          setting.value === 'true' || setting.value === true
            ? 'bg-green-100 text-green-700'
            : 'bg-gray-100 text-gray-700'
        }`}>
          {setting.value === 'true' || setting.value === true ? 'Enabled' : 'Disabled'}
        </span>
      );
    }

    return (
      <span className="text-gray-900 font-mono text-sm">{String(setting.value)}</span>
    );
  };

  const getCurrentCategorySettings = () => {
    const categorySettings = settings[selectedCategory];
    return Array.isArray(categorySettings) ? categorySettings : [];
  };

  if (authLoading || loading || !user) {
    return (
      <DashboardLayout>
        <div className="flex items-center justify-center min-h-screen">
          <div className="text-center">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-[#0d4a6f] mx-auto mb-4"></div>
            <p className="text-gray-600">Loading settings...</p>
          </div>
        </div>
      </DashboardLayout>
    );
  }

  return (
    <DashboardLayout>
      <div className="p-6 space-y-6">
        {/* Page Header */}
        <PageHeader />
        
        {/* Header */}
        <div className="bg-gradient-to-r from-[#0d4a6f] to-[#083a57] rounded-2xl shadow-lg p-6 text-white relative overflow-hidden">
          <div className="absolute bottom-0 left-0 right-0 opacity-10">
            <svg viewBox="0 0 1440 120" className="w-full h-12">
              <path fill="white" d="M0,32L48,37.3C96,43,192,53,288,58.7C384,64,480,64,576,58.7C672,53,768,43,864,42.7C960,43,1056,53,1152,58.7C1248,64,1344,64,1392,64L1440,64L1440,120L1392,120C1344,120,1248,120,1152,120C1056,120,960,120,864,120C768,120,672,120,576,120C480,120,384,120,288,120C192,120,96,120,48,120L0,120Z"></path>
            </svg>
          </div>
          <div className="relative z-10 flex items-center justify-between">
            <div>
              <h1 className="text-2xl font-bold flex items-center gap-3">
                <div className="p-2 bg-white/20 rounded-xl backdrop-blur-sm">
                  <Settings className="w-6 h-6" />
                </div>
                System Settings
              </h1>
              <p className="text-[#9ecbec] mt-1">
                Configure system-wide settings and preferences
              </p>
            </div>
            <div className="flex items-center gap-2">
              <button
                onClick={() => setShowCreateModal(true)}
                className="flex items-center gap-2 px-4 py-2 bg-white/10 border border-white/20 hover:bg-white/20 rounded-xl transition-colors"
              >
                <Plus className="w-4 h-4" />
                Add Setting
              </button>
              <button
                onClick={fetchSettings}
                className="flex items-center gap-2 px-4 py-2 bg-white/10 border border-white/20 hover:bg-white/20 rounded-xl transition-colors"
              >
                <RefreshCw className="w-4 h-4" />
                Refresh
              </button>
            </div>
          </div>
        </div>

        {/* Settings Layout */}
        <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
          {/* Category Sidebar */}
          <div className="lg:col-span-1">
            <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-4">
              <h3 className="text-sm font-semibold text-gray-500 uppercase mb-4">Categories</h3>
              <nav className="space-y-1">
                {categories.map((category) => {
                  const Icon = category.icon;
                  const count = (settings[category.id] || []).length;
                  return (
                    <button
                      key={category.id}
                      onClick={() => setSelectedCategory(category.id)}
                      className={`w-full flex items-center justify-between px-3 py-2 rounded-xl text-sm transition-colors ${
                        selectedCategory === category.id
                          ? 'bg-[#e8f4fc] text-[#0d4a6f]'
                          : 'text-gray-600 hover:bg-gray-50'
                      }`}
                    >
                      <div className="flex items-center gap-3">
                        <Icon className="w-4 h-4" />
                        <span>{category.label}</span>
                      </div>
                      {count > 0 && (
                        <span className={`px-2 py-0.5 text-xs rounded-full ${
                          selectedCategory === category.id
                            ? 'bg-[#c5e1f5]'
                            : 'bg-gray-100'
                        }`}>
                          {count}
                        </span>
                      )}
                    </button>
                  );
                })}
              </nav>
            </div>
          </div>

          {/* Settings List */}
          <div className="lg:col-span-3">
            <div className="bg-white rounded-xl shadow-sm border border-gray-200">
              <div className="p-4 border-b border-gray-200">
                <h2 className="text-lg font-semibold text-gray-900 capitalize">
                  {selectedCategory} Settings
                </h2>
              </div>
              <div className="divide-y divide-gray-100">
                {getCurrentCategorySettings().length === 0 ? (
                  <div className="p-8 text-center text-gray-500">
                    <Settings className="w-12 h-12 mx-auto mb-4 opacity-50" />
                    <p>No settings in this category</p>
                    <button
                      onClick={() => {
                        setNewSetting(prev => ({ ...prev, category: selectedCategory }));
                        setShowCreateModal(true);
                      }}
                      className="mt-4 text-sky-600 hover:text-sky-700 text-sm font-medium"
                    >
                      Add a setting
                    </button>
                  </div>
                ) : (
                  getCurrentCategorySettings().map((setting) => (
                    <div
                      key={setting.key}
                      className="p-4 hover:bg-gray-50 transition-colors"
                    >
                      <div className="flex items-start justify-between">
                        <div className="flex-1">
                          <div className="flex items-center gap-2 mb-1">
                            <span className="font-medium text-gray-900">{setting.key}</span>
                            <span className="px-2 py-0.5 text-xs bg-gray-100 text-gray-600 rounded">
                              {setting.value_type}
                            </span>
                          </div>
                          {setting.description && (
                            <p className="text-sm text-gray-500 mb-2">{setting.description}</p>
                          )}
                          <div className="mt-2">
                            {renderSettingValue(setting)}
                          </div>
                        </div>
                        {editingKey !== setting.key && (
                          <div className="flex items-center gap-1 ml-4">
                            <button
                              onClick={() => handleEditStart(setting)}
                              className="p-2 text-gray-400 hover:text-sky-600 hover:bg-sky-50 rounded-lg transition-colors"
                              title="Edit"
                            >
                              <Edit2 className="w-4 h-4" />
                            </button>
                            <button
                              onClick={() => setDeleteConfirm(setting.key)}
                              className="p-2 text-gray-400 hover:text-red-600 hover:bg-red-50 rounded-lg transition-colors"
                              title="Delete"
                            >
                              <Trash2 className="w-4 h-4" />
                            </button>
                          </div>
                        )}
                      </div>
                    </div>
                  ))
                )}
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Create Setting Modal */}
      {showCreateModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-xl max-w-md w-full">
            <div className="p-6 border-b border-gray-200 flex items-center justify-between">
              <h2 className="text-xl font-semibold text-gray-900">Add New Setting</h2>
              <button
                onClick={() => setShowCreateModal(false)}
                className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
              >
                <X className="w-5 h-5" />
              </button>
            </div>
            <div className="p-6 space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Key *</label>
                <input
                  type="text"
                  value={newSetting.key}
                  onChange={(e) => setNewSetting(prev => ({ ...prev, key: e.target.value }))}
                  className="w-full border border-gray-300 rounded-lg px-3 py-2 focus:ring-2 focus:ring-[#1a6b9a] focus:border-[#1a6b9a]"
                  placeholder="setting_key"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Value *</label>
                <input
                  type="text"
                  value={newSetting.value}
                  onChange={(e) => setNewSetting(prev => ({ ...prev, value: e.target.value }))}
                  className="w-full border border-gray-300 rounded-lg px-3 py-2 focus:ring-2 focus:ring-[#1a6b9a] focus:border-[#1a6b9a]"
                  placeholder="value"
                />
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Category</label>
                  <select
                    value={newSetting.category}
                    onChange={(e) => setNewSetting(prev => ({ ...prev, category: e.target.value }))}
                    className="w-full border border-gray-300 rounded-lg px-3 py-2 focus:ring-2 focus:ring-[#1a6b9a] focus:border-[#1a6b9a]"
                  >
                    {categories.map(cat => (
                      <option key={cat.id} value={cat.id}>{cat.label}</option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Value Type</label>
                  <select
                    value={newSetting.value_type}
                    onChange={(e) => setNewSetting(prev => ({ ...prev, value_type: e.target.value }))}
                    className="w-full border border-gray-300 rounded-lg px-3 py-2 focus:ring-2 focus:ring-[#1a6b9a] focus:border-[#1a6b9a]"
                  >
                    <option value="string">String</option>
                    <option value="number">Number</option>
                    <option value="boolean">Boolean</option>
                    <option value="json">JSON</option>
                  </select>
                </div>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Description</label>
                <textarea
                  value={newSetting.description}
                  onChange={(e) => setNewSetting(prev => ({ ...prev, description: e.target.value }))}
                  className="w-full border border-gray-300 rounded-lg px-3 py-2 focus:ring-2 focus:ring-[#1a6b9a] focus:border-[#1a6b9a]"
                  rows={2}
                  placeholder="Optional description"
                />
              </div>
            </div>
            <div className="p-6 border-t border-gray-200 flex justify-end gap-3">
              <button
                onClick={() => setShowCreateModal(false)}
                className="px-4 py-2 text-gray-700 border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={handleCreateSetting}
                className="px-4 py-2 bg-sky-500 text-white rounded-lg hover:bg-sky-600 transition-colors flex items-center gap-2"
              >
                <Save className="w-4 h-4" />
                Create Setting
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Delete Confirmation Modal */}
      {deleteConfirm && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-xl max-w-md w-full p-6">
            <div className="flex items-center gap-3 mb-4">
              <div className="p-3 bg-red-100 rounded-full">
                <AlertCircle className="w-6 h-6 text-red-600" />
              </div>
              <div>
                <h3 className="text-lg font-semibold text-gray-900">Delete Setting</h3>
                <p className="text-sm text-gray-500">
                  Are you sure you want to delete "{deleteConfirm}"?
                </p>
              </div>
            </div>
            <p className="text-sm text-gray-600 mb-6">
              This action cannot be undone. The setting will be permanently removed from the system.
            </p>
            <div className="flex justify-end gap-3">
              <button
                onClick={() => setDeleteConfirm(null)}
                className="px-4 py-2 text-gray-700 border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={() => handleDeleteSetting(deleteConfirm)}
                className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors"
              >
                Delete
              </button>
            </div>
          </div>
        </div>
      )}
    </DashboardLayout>
  );
}
