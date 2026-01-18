'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import DashboardLayout from '@/components/DashboardLayout';
import PageHeader from '@/components/PageHeader';
import useAuthStore from '@/context/AuthContext';
import {
  getAdminReports,
  deleteAdminReport,
  getAdminAlerts,
  deleteAdminAlert,
  getAdminChatMessages,
  deleteAdminChatMessage,
  getAdminCommunities,
  deleteAdminCommunity,
  getAdminCommunityPosts,
  deleteAdminCommunityPost,
} from '@/lib/api';
import { formatDateTimeIST } from '@/lib/dateUtils';
import toast from 'react-hot-toast';
import {
  FileText,
  AlertTriangle,
  MessageSquare,
  Users,
  Trash2,
  Search,
  Filter,
  ChevronLeft,
  ChevronRight,
  Eye,
  X,
  CheckCircle,
  XCircle,
  Clock,
  Shield,
  RefreshCw,
  MoreVertical,
  Globe,
  Hash,
  Calendar,
  MapPin,
  User,
  AlertCircle,
  Loader2
} from 'lucide-react';

const CONTENT_TYPES = [
  { id: 'reports', label: 'Hazard Reports', icon: FileText, color: 'text-blue-600' },
  { id: 'alerts', label: 'Alerts', icon: AlertTriangle, color: 'text-red-600' },
  { id: 'messages', label: 'Chat Messages', icon: MessageSquare, color: 'text-green-600' },
  { id: 'communities', label: 'Communities', icon: Users, color: 'text-purple-600' },
  { id: 'community_posts', label: 'Community Posts', icon: Hash, color: 'text-orange-600' },
];

export default function AdminContentPage() {
  const router = useRouter();
  const { user, isLoading: authLoading } = useAuthStore();
  const [activeTab, setActiveTab] = useState('reports');
  const [loading, setLoading] = useState(false);
  const [items, setItems] = useState([]);
  const [pagination, setPagination] = useState({ page: 1, limit: 20, total_count: 0, total_pages: 0 });
  
  // Filters
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState('all');
  const [selectedItems, setSelectedItems] = useState(new Set());
  
  // Modals
  const [showDeleteModal, setShowDeleteModal] = useState(false);
  const [itemToDelete, setItemToDelete] = useState(null);
  const [deleteReason, setDeleteReason] = useState('');
  const [showDetailModal, setShowDetailModal] = useState(false);
  const [selectedItem, setSelectedItem] = useState(null);

  useEffect(() => {
    if (!authLoading && user) {
      if (user.role !== 'authority_admin') {
        toast.error('Access denied. Admin privileges required.');
        router.push('/dashboard');
      } else {
        fetchContent();
      }
    }
  }, [user, authLoading, activeTab, pagination.page, statusFilter, searchQuery]);

  const fetchContent = async () => {
    setLoading(true);
    try {
      const params = {
        page: pagination.page,
        limit: pagination.limit,
      };

      if (statusFilter !== 'all') {
        params.status = statusFilter;
      }

      if (searchQuery) {
        params.search = searchQuery;
      }

      let response;
      switch (activeTab) {
        case 'reports':
          response = await getAdminReports(params);
          break;
        case 'alerts':
          response = await getAdminAlerts(params);
          break;
        case 'messages':
          response = await getAdminChatMessages(params);
          break;
        case 'communities':
          response = await getAdminCommunities(params);
          break;
        case 'community_posts':
          // For community posts, we need to fetch all communities first, then their posts
          // This is a simplified version - you might want to create a dedicated admin endpoint
          response = { data: { items: [], pagination: { total_count: 0, total_pages: 0 } } };
          break;
        default:
          response = { data: { items: [], pagination: { total_count: 0, total_pages: 0 } } };
      }

      const data = response.data || response;
      setItems(Array.isArray(data.items || data.reports || data.alerts || data.messages || data.communities) 
        ? (data.items || data.reports || data.alerts || data.messages || data.communities) 
        : []);
      setPagination(data.pagination || { page: 1, limit: 20, total_count: 0, total_pages: 0 });
    } catch (error) {
      console.error('Error fetching content:', error);
      toast.error('Failed to load content');
      setItems([]);
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async () => {
    if (!itemToDelete) return;

    try {
      setLoading(true);
      let response;
      
      switch (activeTab) {
        case 'reports':
          response = await deleteAdminReport(itemToDelete.report_id || itemToDelete.id, deleteReason);
          break;
        case 'alerts':
          response = await deleteAdminAlert(itemToDelete.alert_id || itemToDelete.id);
          break;
        case 'messages':
          response = await deleteAdminChatMessage(itemToDelete.message_id || itemToDelete.id);
          break;
        case 'communities':
          response = await deleteAdminCommunity(itemToDelete.community_id || itemToDelete.id);
          break;
        case 'community_posts':
          response = await deleteAdminCommunityPost(
            itemToDelete.community_id,
            itemToDelete.post_id || itemToDelete.id
          );
          break;
        default:
          return;
      }

      toast.success('Content deleted successfully');
      setShowDeleteModal(false);
      setItemToDelete(null);
      setDeleteReason('');
      fetchContent();
    } catch (error) {
      console.error('Error deleting content:', error);
      toast.error(error.response?.data?.detail || 'Failed to delete content');
    } finally {
      setLoading(false);
    }
  };

  const handleViewDetail = (item) => {
    setSelectedItem(item);
    setShowDetailModal(true);
  };

  const renderContentItem = (item, index) => {
    const Icon = CONTENT_TYPES.find(t => t.id === activeTab)?.icon || FileText;
    
    switch (activeTab) {
      case 'reports':
        return (
          <div key={item.report_id || item.id || index} className="bg-white rounded-xl border border-slate-200 p-4 hover:shadow-md transition-shadow">
            <div className="flex items-start justify-between">
              <div className="flex-1">
                <div className="flex items-center gap-2 mb-2">
                  <Icon className="w-5 h-5 text-blue-600" />
                  <h3 className="font-semibold text-slate-900">{item.hazard_type || 'Hazard Report'}</h3>
                  <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${
                    item.verification_status === 'verified' ? 'bg-green-100 text-green-700' :
                    item.verification_status === 'pending' ? 'bg-yellow-100 text-yellow-700' :
                    'bg-gray-100 text-gray-700'
                  }`}>
                    {item.verification_status || 'pending'}
                  </span>
                </div>
                <p className="text-sm text-slate-600 mb-2 line-clamp-2">{item.description || 'No description'}</p>
                <div className="flex items-center gap-4 text-xs text-slate-500">
                  <span className="flex items-center gap-1">
                    <User className="w-3 h-3" />
                    {item.user_name || item.user_id || 'Unknown'}
                  </span>
                  <span className="flex items-center gap-1">
                    <MapPin className="w-3 h-3" />
                    {item.location?.address || 'Location not specified'}
                  </span>
                  <span className="flex items-center gap-1">
                    <Clock className="w-3 h-3" />
                    {item.created_at ? formatDateTimeIST(item.created_at) : 'Unknown date'}
                  </span>
                </div>
              </div>
              <div className="flex items-center gap-2 ml-4">
                <button
                  onClick={() => handleViewDetail(item)}
                  className="p-2 hover:bg-slate-100 rounded-lg transition-colors"
                  title="View details"
                >
                  <Eye className="w-4 h-4 text-slate-600" />
                </button>
                <button
                  onClick={() => {
                    setItemToDelete(item);
                    setShowDeleteModal(true);
                  }}
                  className="p-2 hover:bg-red-50 rounded-lg transition-colors"
                  title="Delete"
                >
                  <Trash2 className="w-4 h-4 text-red-600" />
                </button>
              </div>
            </div>
          </div>
        );

      case 'alerts':
        return (
          <div key={item.alert_id || item.id || index} className="bg-white rounded-xl border border-slate-200 p-4 hover:shadow-md transition-shadow">
            <div className="flex items-start justify-between">
              <div className="flex-1">
                <div className="flex items-center gap-2 mb-2">
                  <Icon className="w-5 h-5 text-red-600" />
                  <h3 className="font-semibold text-slate-900">{item.title || 'Alert'}</h3>
                  <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${
                    item.severity === 'critical' ? 'bg-red-100 text-red-700' :
                    item.severity === 'high' ? 'bg-orange-100 text-orange-700' :
                    item.severity === 'medium' ? 'bg-yellow-100 text-yellow-700' :
                    'bg-blue-100 text-blue-700'
                  }`}>
                    {item.severity || 'info'}
                  </span>
                  <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${
                    item.status === 'active' ? 'bg-green-100 text-green-700' :
                    item.status === 'cancelled' ? 'bg-gray-100 text-gray-700' :
                    'bg-slate-100 text-slate-700'
                  }`}>
                    {item.status || 'draft'}
                  </span>
                </div>
                <p className="text-sm text-slate-600 mb-2">{item.message || item.description || 'No message'}</p>
                <div className="flex items-center gap-4 text-xs text-slate-500">
                  <span className="flex items-center gap-1">
                    <AlertCircle className="w-3 h-3" />
                    {item.alert_type || 'General'}
                  </span>
                  <span className="flex items-center gap-1">
                    <MapPin className="w-3 h-3" />
                    {item.regions?.join(', ') || 'All regions'}
                  </span>
                  <span className="flex items-center gap-1">
                    <Clock className="w-3 h-3" />
                    {item.created_at ? formatDateTimeIST(item.created_at) : 'Unknown date'}
                  </span>
                </div>
              </div>
              <div className="flex items-center gap-2 ml-4">
                <button
                  onClick={() => handleViewDetail(item)}
                  className="p-2 hover:bg-slate-100 rounded-lg transition-colors"
                  title="View details"
                >
                  <Eye className="w-4 h-4 text-slate-600" />
                </button>
                <button
                  onClick={() => {
                    setItemToDelete(item);
                    setShowDeleteModal(true);
                  }}
                  className="p-2 hover:bg-red-50 rounded-lg transition-colors"
                  title="Delete"
                >
                  <Trash2 className="w-4 h-4 text-red-600" />
                </button>
              </div>
            </div>
          </div>
        );

      case 'messages':
        return (
          <div key={item.message_id || item.id || index} className="bg-white rounded-xl border border-slate-200 p-4 hover:shadow-md transition-shadow">
            <div className="flex items-start justify-between">
              <div className="flex-1">
                <div className="flex items-center gap-2 mb-2">
                  <Icon className="w-5 h-5 text-green-600" />
                  <h3 className="font-semibold text-slate-900">{item.user_name || 'Anonymous'}</h3>
                  <span className="px-2 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-700">
                    {item.room_id || 'general'}
                  </span>
                </div>
                <p className="text-sm text-slate-600 mb-2">{item.content || 'No content'}</p>
                <div className="flex items-center gap-4 text-xs text-slate-500">
                  <span className="flex items-center gap-1">
                    <User className="w-3 h-3" />
                    {item.user_id || 'Unknown user'}
                  </span>
                  <span className="flex items-center gap-1">
                    <Hash className="w-3 h-3" />
                    {item.message_type || 'text'}
                  </span>
                  <span className="flex items-center gap-1">
                    <Clock className="w-3 h-3" />
                    {item.timestamp ? formatDateTimeIST(item.timestamp) : 'Unknown date'}
                  </span>
                </div>
              </div>
              <div className="flex items-center gap-2 ml-4">
                <button
                  onClick={() => handleViewDetail(item)}
                  className="p-2 hover:bg-slate-100 rounded-lg transition-colors"
                  title="View details"
                >
                  <Eye className="w-4 h-4 text-slate-600" />
                </button>
                <button
                  onClick={() => {
                    setItemToDelete(item);
                    setShowDeleteModal(true);
                  }}
                  className="p-2 hover:bg-red-50 rounded-lg transition-colors"
                  title="Delete"
                >
                  <Trash2 className="w-4 h-4 text-red-600" />
                </button>
              </div>
            </div>
          </div>
        );

      case 'communities':
        return (
          <div key={item.community_id || item.id || index} className="bg-white rounded-xl border border-slate-200 p-4 hover:shadow-md transition-shadow">
            <div className="flex items-start justify-between">
              <div className="flex-1">
                <div className="flex items-center gap-2 mb-2">
                  <Icon className="w-5 h-5 text-purple-600" />
                  <h3 className="font-semibold text-slate-900">{item.name || 'Community'}</h3>
                  {!item.is_active && (
                    <span className="px-2 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-700">
                      Inactive
                    </span>
                  )}
                </div>
                <p className="text-sm text-slate-600 mb-2">{item.description || 'No description'}</p>
                <div className="flex items-center gap-4 text-xs text-slate-500">
                  <span className="flex items-center gap-1">
                    <Users className="w-3 h-3" />
                    {item.member_count || 0} members
                  </span>
                  <span className="flex items-center gap-1">
                    <MapPin className="w-3 h-3" />
                    {item.location?.state || item.state || 'Unknown'}
                  </span>
                  <span className="flex items-center gap-1">
                    <Clock className="w-3 h-3" />
                    {item.created_at ? formatDateTimeIST(item.created_at) : 'Unknown date'}
                  </span>
                </div>
              </div>
              <div className="flex items-center gap-2 ml-4">
                <button
                  onClick={() => handleViewDetail(item)}
                  className="p-2 hover:bg-slate-100 rounded-lg transition-colors"
                  title="View details"
                >
                  <Eye className="w-4 h-4 text-slate-600" />
                </button>
                <button
                  onClick={() => {
                    setItemToDelete(item);
                    setShowDeleteModal(true);
                  }}
                  className="p-2 hover:bg-red-50 rounded-lg transition-colors"
                  title="Delete"
                >
                  <Trash2 className="w-4 h-4 text-red-600" />
                </button>
              </div>
            </div>
          </div>
        );

      default:
        return null;
    }
  };

  if (authLoading || !user) {
    return (
      <DashboardLayout>
        <div className="flex items-center justify-center min-h-screen">
          <Loader2 className="w-8 h-8 animate-spin text-[#0d4a6f]" />
        </div>
      </DashboardLayout>
    );
  }

  return (
    <DashboardLayout>
      <div className="p-3 lg:p-6 w-full pb-24 lg:pb-6">
        <PageHeader />

        {/* Header */}
        <div className="bg-gradient-to-r from-[#0d4a6f] to-[#083a57] rounded-2xl shadow-lg p-6 text-white relative overflow-hidden mb-6">
          <div className="absolute bottom-0 left-0 right-0 opacity-10">
            <svg viewBox="0 0 1440 120" className="w-full h-12">
              <path fill="white" d="M0,32L48,37.3C96,43,192,53,288,58.7C384,64,480,64,576,58.7C672,53,768,43,864,42.7C960,43,1056,53,1152,58.7C1248,64,1344,64,1392,64L1440,64L1440,120L1392,120C1344,120,1248,120,1152,120C1056,120,960,120,864,120C768,120,672,120,576,120C480,120,384,120,288,120C192,120,96,120,48,120L0,120Z"></path>
            </svg>
          </div>
          <div className="relative z-10">
            <div className="flex items-center justify-between">
              <div>
                <h1 className="text-2xl font-bold mb-2">Content Management</h1>
                <p className="text-blue-100">Manage and moderate all platform content</p>
              </div>
              <button
                onClick={fetchContent}
                disabled={loading}
                className="p-3 bg-white/20 hover:bg-white/30 rounded-xl transition-colors"
                title="Refresh"
              >
                <RefreshCw className={`w-5 h-5 ${loading ? 'animate-spin' : ''}`} />
              </button>
            </div>
          </div>
        </div>

        {/* Tabs */}
        <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-2 mb-6">
          <div className="flex gap-2 overflow-x-auto scrollbar-hide">
            {CONTENT_TYPES.map((type) => {
              const TypeIcon = type.icon;
              return (
                <button
                  key={type.id}
                  onClick={() => {
                    setActiveTab(type.id);
                    setPagination({ ...pagination, page: 1 });
                    setSearchQuery('');
                    setStatusFilter('all');
                  }}
                  className={`flex items-center gap-2 px-4 py-2 rounded-lg font-medium transition-colors whitespace-nowrap ${
                    activeTab === type.id
                      ? 'bg-[#0d4a6f] text-white'
                      : 'text-slate-600 hover:bg-slate-100'
                  }`}
                >
                  <TypeIcon className="w-4 h-4" />
                  {type.label}
                </button>
              );
            })}
          </div>
        </div>

        {/* Filters */}
        <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-4 mb-6">
          <div className="flex flex-col md:flex-row gap-4">
            <div className="flex-1">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-400" />
                <input
                  type="text"
                  placeholder="Search content..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="w-full pl-10 pr-4 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#0d4a6f]"
                />
              </div>
            </div>
            <div className="flex items-center gap-2">
              <Filter className="w-5 h-5 text-slate-400" />
              <select
                value={statusFilter}
                onChange={(e) => {
                  setStatusFilter(e.target.value);
                  setPagination({ ...pagination, page: 1 });
                }}
                className="px-4 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#0d4a6f]"
              >
                <option value="all">All Status</option>
                {activeTab === 'reports' && (
                  <>
                    <option value="pending">Pending</option>
                    <option value="verified">Verified</option>
                    <option value="rejected">Rejected</option>
                  </>
                )}
                {activeTab === 'alerts' && (
                  <>
                    <option value="active">Active</option>
                    <option value="draft">Draft</option>
                    <option value="cancelled">Cancelled</option>
                    <option value="expired">Expired</option>
                  </>
                )}
                {activeTab === 'communities' && (
                  <>
                    <option value="active">Active</option>
                    <option value="inactive">Inactive</option>
                  </>
                )}
              </select>
            </div>
          </div>
        </div>

        {/* Content List */}
        <div className="space-y-4">
          {loading ? (
            <div className="flex items-center justify-center py-12">
              <Loader2 className="w-8 h-8 animate-spin text-[#0d4a6f]" />
            </div>
          ) : items.length === 0 ? (
            <div className="bg-white rounded-xl border border-slate-200 p-12 text-center">
              <FileText className="w-12 h-12 text-slate-400 mx-auto mb-4" />
              <p className="text-slate-600">No content found</p>
            </div>
          ) : (
            items.map((item, index) => renderContentItem(item, index))
          )}
        </div>

        {/* Pagination */}
        {pagination.total_pages > 1 && (
          <div className="flex items-center justify-between mt-6 bg-white rounded-xl shadow-sm border border-slate-200 p-4">
            <div className="text-sm text-slate-600">
              Showing {((pagination.page - 1) * pagination.limit) + 1} to {Math.min(pagination.page * pagination.limit, pagination.total_count)} of {pagination.total_count} items
            </div>
            <div className="flex items-center gap-2">
              <button
                onClick={() => setPagination({ ...pagination, page: pagination.page - 1 })}
                disabled={pagination.page === 1}
                className="p-2 border border-slate-300 rounded-lg disabled:opacity-50 disabled:cursor-not-allowed hover:bg-slate-50"
              >
                <ChevronLeft className="w-4 h-4" />
              </button>
              <span className="px-4 py-2 text-sm font-medium">
                Page {pagination.page} of {pagination.total_pages}
              </span>
              <button
                onClick={() => setPagination({ ...pagination, page: pagination.page + 1 })}
                disabled={pagination.page >= pagination.total_pages}
                className="p-2 border border-slate-300 rounded-lg disabled:opacity-50 disabled:cursor-not-allowed hover:bg-slate-50"
              >
                <ChevronRight className="w-4 h-4" />
              </button>
            </div>
          </div>
        )}

        {/* Delete Modal */}
        {showDeleteModal && (
          <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-[99999] p-4">
            <div className="bg-white rounded-2xl shadow-xl max-w-md w-full p-6">
              <div className="flex items-center gap-3 mb-4">
                <div className="p-2 bg-red-100 rounded-lg">
                  <Trash2 className="w-6 h-6 text-red-600" />
                </div>
                <h3 className="text-xl font-semibold text-slate-900">Delete Content</h3>
              </div>
              <p className="text-slate-600 mb-4">
                Are you sure you want to delete this {activeTab === 'reports' ? 'report' : activeTab === 'alerts' ? 'alert' : activeTab === 'messages' ? 'message' : activeTab === 'communities' ? 'community' : 'post'}? This action cannot be undone.
              </p>
              {activeTab === 'reports' && (
                <div className="mb-4">
                  <label className="block text-sm font-medium text-slate-700 mb-2">
                    Reason for deletion (optional)
                  </label>
                  <textarea
                    value={deleteReason}
                    onChange={(e) => setDeleteReason(e.target.value)}
                    placeholder="Enter reason for deletion..."
                    className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#0d4a6f]"
                    rows="3"
                  />
                </div>
              )}
              <div className="flex items-center gap-3">
                <button
                  onClick={() => {
                    setShowDeleteModal(false);
                    setItemToDelete(null);
                    setDeleteReason('');
                  }}
                  className="flex-1 px-4 py-2 border border-slate-300 rounded-lg text-slate-700 hover:bg-slate-50 transition-colors"
                >
                  Cancel
                </button>
                <button
                  onClick={handleDelete}
                  disabled={loading}
                  className="flex-1 px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors disabled:opacity-50"
                >
                  {loading ? 'Deleting...' : 'Delete'}
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Detail Modal */}
        {showDetailModal && selectedItem && (
          <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-[99999] p-4">
            <div className="bg-white rounded-2xl shadow-xl max-w-2xl w-full max-h-[90vh] overflow-y-auto p-6">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-xl font-semibold text-slate-900">Content Details</h3>
                <button
                  onClick={() => {
                    setShowDetailModal(false);
                    setSelectedItem(null);
                  }}
                  className="p-2 hover:bg-slate-100 rounded-lg transition-colors"
                >
                  <X className="w-5 h-5 text-slate-600" />
                </button>
              </div>
              <div className="space-y-4">
                <pre className="bg-slate-50 rounded-lg p-4 text-xs overflow-x-auto">
                  {JSON.stringify(selectedItem, null, 2)}
                </pre>
              </div>
            </div>
          </div>
        )}
      </div>
    </DashboardLayout>
  );
}

