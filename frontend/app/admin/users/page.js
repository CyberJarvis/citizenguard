'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import DashboardLayout from '@/components/DashboardLayout';
import PageHeader from '@/components/PageHeader';
import useAuthStore from '@/context/AuthContext';
import api from '@/lib/api';
import { formatDateIST, formatDateTimeIST } from '@/lib/dateUtils';
import toast from 'react-hot-toast';
import { ExportButton } from '@/components/export';
import {
  Users,
  Search,
  Filter,
  ChevronLeft,
  ChevronRight,
  Ban,
  UserCheck,
  Shield,
  Mail,
  Phone,
  Calendar,
  MoreVertical,
  Eye,
  Edit,
  UserPlus,
  X,
  Check,
  AlertTriangle
} from 'lucide-react';

export default function AdminUsersPage() {
  const router = useRouter();
  const { user, isLoading: authLoading } = useAuthStore();
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [pagination, setPagination] = useState({ page: 1, limit: 20, total_count: 0, total_pages: 0 });

  // Filters
  const [searchQuery, setSearchQuery] = useState('');
  const [roleFilter, setRoleFilter] = useState('all');
  const [statusFilter, setStatusFilter] = useState('all');

  // Modals
  const [selectedUser, setSelectedUser] = useState(null);
  const [showBanModal, setShowBanModal] = useState(false);
  const [showRoleModal, setShowRoleModal] = useState(false);
  const [showDetailModal, setShowDetailModal] = useState(false);
  const [banReason, setBanReason] = useState('');
  const [newRole, setNewRole] = useState('');
  const [roleReason, setRoleReason] = useState('');
  const [actionLoading, setActionLoading] = useState(false);

  useEffect(() => {
    if (!authLoading && user) {
      if (user.role !== 'authority_admin') {
        toast.error('Access denied. Admin privileges required.');
        router.push('/dashboard');
      } else {
        fetchUsers();
      }
    }
  }, [user, authLoading, router, pagination.page, roleFilter, statusFilter]);

  const fetchUsers = async () => {
    try {
      setLoading(true);
      const params = {
        page: pagination.page,
        limit: pagination.limit,
      };
      if (searchQuery) params.search = searchQuery;
      if (roleFilter !== 'all') params.role = roleFilter;
      if (statusFilter !== 'all') params.status = statusFilter;

      const response = await api.get('/admin/users', { params });
      // Handle different response formats
      const data = response.data?.data || response.data || {};
      const usersData = data.users || data || [];
      setUsers(Array.isArray(usersData) ? usersData : []);
      setPagination(prev => ({
        ...prev,
        ...(data.pagination || response.data?.pagination || {})
      }));
    } catch (error) {
      console.error('Error fetching users:', error);
      toast.error('Failed to load users');
      setUsers([]);
    } finally {
      setLoading(false);
    }
  };

  const handleSearch = (e) => {
    e.preventDefault();
    setPagination(prev => ({ ...prev, page: 1 }));
    fetchUsers();
  };

  const handleBanUser = async () => {
    if (!banReason.trim() || banReason.length < 10) {
      toast.error('Ban reason must be at least 10 characters');
      return;
    }

    try {
      setActionLoading(true);
      await api.post(`/admin/users/${selectedUser.user_id}/ban`, { reason: banReason });
      toast.success(`User ${selectedUser.name || selectedUser.email} has been banned`);
      setShowBanModal(false);
      setBanReason('');
      setSelectedUser(null);
      fetchUsers();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to ban user');
    } finally {
      setActionLoading(false);
    }
  };

  const handleUnbanUser = async (userToBan) => {
    try {
      await api.post(`/admin/users/${userToBan.user_id}/unban`);
      toast.success(`User ${userToBan.name || userToBan.email} has been unbanned`);
      fetchUsers();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to unban user');
    }
  };

  const handleAssignRole = async () => {
    if (!newRole) {
      toast.error('Please select a role');
      return;
    }

    try {
      setActionLoading(true);
      await api.post(`/admin/users/${selectedUser.user_id}/role`, {
        role: newRole,
        reason: roleReason || null
      });
      toast.success(`Role changed to ${newRole}`);
      setShowRoleModal(false);
      setNewRole('');
      setRoleReason('');
      setSelectedUser(null);
      fetchUsers();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to change role');
    } finally {
      setActionLoading(false);
    }
  };

  const getRoleBadgeColor = (role) => {
    switch (role) {
      case 'authority_admin': return 'bg-sky-100 text-sky-700';
      case 'authority': return 'bg-blue-100 text-blue-700';
      case 'analyst': return 'bg-green-100 text-green-700';
      default: return 'bg-gray-100 text-gray-700';
    }
  };

  const getStatusBadge = (user) => {
    if (user.is_banned) {
      return <span className="px-2 py-1 bg-red-100 text-red-700 text-xs rounded-full">Banned</span>;
    }
    if (!user.is_active) {
      return <span className="px-2 py-1 bg-gray-100 text-gray-700 text-xs rounded-full">Inactive</span>;
    }
    return <span className="px-2 py-1 bg-green-100 text-green-700 text-xs rounded-full">Active</span>;
  };

  if (authLoading || loading || !user) {
    return (
      <DashboardLayout>
        <div className="flex items-center justify-center min-h-screen">
          <div className="text-center">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-[#0d4a6f] mx-auto mb-4"></div>
            <p className="text-gray-600">Loading users...</p>
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
          <div className="relative z-10">
            <h1 className="text-2xl font-bold flex items-center gap-3">
              <div className="p-2 bg-white/20 rounded-xl backdrop-blur-sm">
                <Users className="w-6 h-6" />
              </div>
              User Management
            </h1>
            <p className="text-[#9ecbec] mt-1">
              Manage all users, roles, and permissions
            </p>
          </div>
        </div>

        {/* Filters */}
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-4">
          <form onSubmit={handleSearch} className="grid grid-cols-1 md:grid-cols-5 gap-4">
            {/* Search */}
            <div className="md:col-span-2">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-gray-400" />
                <input
                  type="text"
                  placeholder="Search by name, email, or phone..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-xl focus:ring-2 focus:ring-[#1a6b9a] focus:border-transparent"
                />
              </div>
            </div>

            {/* Role Filter */}
            <select
              value={roleFilter}
              onChange={(e) => { setRoleFilter(e.target.value); setPagination(p => ({ ...p, page: 1 })); }}
              className="px-4 py-2 border border-gray-300 rounded-xl focus:ring-2 focus:ring-[#1a6b9a]"
            >
              <option value="all">All Roles</option>
              <option value="citizen">Citizen</option>
              <option value="analyst">Analyst</option>
              <option value="authority">Authority</option>
              <option value="authority_admin">Authority Admin</option>
            </select>

            {/* Status Filter */}
            <select
              value={statusFilter}
              onChange={(e) => { setStatusFilter(e.target.value); setPagination(p => ({ ...p, page: 1 })); }}
              className="px-4 py-2 border border-gray-300 rounded-xl focus:ring-2 focus:ring-[#1a6b9a]"
            >
              <option value="all">All Status</option>
              <option value="active">Active</option>
              <option value="inactive">Inactive</option>
              <option value="banned">Banned</option>
            </select>

            <button
              type="submit"
              className="px-4 py-2 bg-[#0d4a6f] text-white rounded-xl hover:bg-[#083a57] transition-colors flex items-center justify-center gap-2"
            >
              <Filter className="w-4 h-4" />
              Apply
            </button>

            {/* Export Button */}
            <ExportButton
              dataType="users"
              currentFilters={{ role: roleFilter, status: statusFilter }}
              size="md"
            />
          </form>
        </div>

        {/* Users Table */}
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-gray-50 border-b border-gray-200">
                <tr>
                  <th className="px-6 py-4 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider">User</th>
                  <th className="px-6 py-4 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider">Role</th>
                  <th className="px-6 py-4 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider">Status</th>
                  <th className="px-6 py-4 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider">Credibility</th>
                  <th className="px-6 py-4 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider">Joined</th>
                  <th className="px-6 py-4 text-right text-xs font-semibold text-gray-600 uppercase tracking-wider">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200">
                {users.map((u) => (
                  <tr key={u.user_id} className="hover:bg-gray-50">
                    <td className="px-6 py-4">
                      <div className="flex items-center gap-3">
                        <div className="w-10 h-10 bg-[#e8f4fc] rounded-full flex items-center justify-center">
                          <span className="text-[#0d4a6f] font-semibold">
                            {(u.name || u.email || 'U')[0].toUpperCase()}
                          </span>
                        </div>
                        <div>
                          <p className="font-medium text-gray-900">{u.name || 'No name'}</p>
                          <p className="text-sm text-gray-500">{u.email || u.phone || 'No contact'}</p>
                        </div>
                      </div>
                    </td>
                    <td className="px-6 py-4">
                      <span className={`px-3 py-1 rounded-full text-xs font-medium ${getRoleBadgeColor(u.role)}`}>
                        {u.role?.replace('_', ' ').toUpperCase()}
                      </span>
                    </td>
                    <td className="px-6 py-4">
                      {getStatusBadge(u)}
                    </td>
                    <td className="px-6 py-4">
                      <div className="flex items-center gap-2">
                        <div className="w-16 bg-gray-200 rounded-full h-2">
                          <div
                            className="bg-[#0d4a6f] h-2 rounded-full"
                            style={{ width: `${u.credibility_score}%` }}
                          ></div>
                        </div>
                        <span className="text-sm text-gray-600">{u.credibility_score}</span>
                      </div>
                    </td>
                    <td className="px-6 py-4 text-sm text-gray-500">
                      {u.created_at ? formatDateIST(u.created_at) : 'N/A'}
                    </td>
                    <td className="px-6 py-4 text-right">
                      <div className="flex items-center justify-end gap-2">
                        <button
                          onClick={() => { setSelectedUser(u); setShowDetailModal(true); }}
                          className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
                          title="View Details"
                        >
                          <Eye className="w-4 h-4 text-gray-600" />
                        </button>
                        <button
                          onClick={() => { setSelectedUser(u); setNewRole(u.role); setShowRoleModal(true); }}
                          className="p-2 hover:bg-blue-100 rounded-lg transition-colors"
                          title="Change Role"
                        >
                          <Shield className="w-4 h-4 text-blue-600" />
                        </button>
                        {u.is_banned ? (
                          <button
                            onClick={() => handleUnbanUser(u)}
                            className="p-2 hover:bg-green-100 rounded-lg transition-colors"
                            title="Unban User"
                          >
                            <UserCheck className="w-4 h-4 text-green-600" />
                          </button>
                        ) : (
                          <button
                            onClick={() => { setSelectedUser(u); setShowBanModal(true); }}
                            className="p-2 hover:bg-red-100 rounded-lg transition-colors"
                            title="Ban User"
                            disabled={u.user_id === user.user_id}
                          >
                            <Ban className="w-4 h-4 text-red-600" />
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {users.length === 0 && (
            <div className="text-center py-12">
              <Users className="w-12 h-12 text-gray-300 mx-auto mb-4" />
              <p className="text-gray-500">No users found</p>
            </div>
          )}

          {/* Pagination */}
          {pagination.total_pages > 1 && (
            <div className="flex items-center justify-between px-6 py-4 border-t border-gray-200">
              <p className="text-sm text-gray-600">
                Showing {((pagination.page - 1) * pagination.limit) + 1} to {Math.min(pagination.page * pagination.limit, pagination.total_count)} of {pagination.total_count} users
              </p>
              <div className="flex items-center gap-2">
                <button
                  onClick={() => setPagination(p => ({ ...p, page: p.page - 1 }))}
                  disabled={pagination.page === 1}
                  className="p-2 border border-gray-300 rounded-lg hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  <ChevronLeft className="w-4 h-4" />
                </button>
                <span className="px-4 py-2 text-sm">
                  Page {pagination.page} of {pagination.total_pages}
                </span>
                <button
                  onClick={() => setPagination(p => ({ ...p, page: p.page + 1 }))}
                  disabled={pagination.page >= pagination.total_pages}
                  className="p-2 border border-gray-300 rounded-lg hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  <ChevronRight className="w-4 h-4" />
                </button>
              </div>
            </div>
          )}
        </div>

        {/* Ban Modal */}
        {showBanModal && selectedUser && (
          <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
            <div className="bg-white rounded-xl shadow-xl max-w-md w-full p-6">
              <div className="flex items-center gap-3 mb-4">
                <div className="p-3 bg-red-100 rounded-full">
                  <Ban className="w-6 h-6 text-red-600" />
                </div>
                <div>
                  <h3 className="text-lg font-semibold text-gray-900">Ban User</h3>
                  <p className="text-sm text-gray-500">{selectedUser.name || selectedUser.email}</p>
                </div>
              </div>
              <div className="mb-4">
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Reason for ban (min 10 characters)
                </label>
                <textarea
                  value={banReason}
                  onChange={(e) => setBanReason(e.target.value)}
                  placeholder="Enter the reason for banning this user..."
                  className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-500 resize-none"
                  rows={3}
                />
              </div>
              <div className="flex gap-3">
                <button
                  onClick={() => { setShowBanModal(false); setBanReason(''); setSelectedUser(null); }}
                  className="flex-1 px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-50"
                >
                  Cancel
                </button>
                <button
                  onClick={handleBanUser}
                  disabled={actionLoading || banReason.length < 10}
                  className="flex-1 px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 disabled:opacity-50"
                >
                  {actionLoading ? 'Banning...' : 'Ban User'}
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Role Modal */}
        {showRoleModal && selectedUser && (
          <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
            <div className="bg-white rounded-xl shadow-xl max-w-md w-full p-6">
              <div className="flex items-center gap-3 mb-4">
                <div className="p-3 bg-blue-100 rounded-full">
                  <Shield className="w-6 h-6 text-blue-600" />
                </div>
                <div>
                  <h3 className="text-lg font-semibold text-gray-900">Change Role</h3>
                  <p className="text-sm text-gray-500">{selectedUser.name || selectedUser.email}</p>
                </div>
              </div>
              <div className="mb-4">
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  New Role
                </label>
                <select
                  value={newRole}
                  onChange={(e) => setNewRole(e.target.value)}
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                >
                  <option value="citizen">Citizen</option>
                  <option value="analyst">Analyst</option>
                  <option value="authority">Authority</option>
                  <option value="authority_admin">Authority Admin</option>
                </select>
              </div>
              <div className="mb-4">
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Reason (optional)
                </label>
                <input
                  type="text"
                  value={roleReason}
                  onChange={(e) => setRoleReason(e.target.value)}
                  placeholder="Why are you changing this role?"
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                />
              </div>
              <div className="flex gap-3">
                <button
                  onClick={() => { setShowRoleModal(false); setNewRole(''); setRoleReason(''); setSelectedUser(null); }}
                  className="flex-1 px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-50"
                >
                  Cancel
                </button>
                <button
                  onClick={handleAssignRole}
                  disabled={actionLoading || newRole === selectedUser.role}
                  className="flex-1 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
                >
                  {actionLoading ? 'Saving...' : 'Change Role'}
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Detail Modal */}
        {showDetailModal && selectedUser && (
          <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
            <div className="bg-white rounded-xl shadow-xl max-w-2xl w-full max-h-[90vh] overflow-hidden">
              <div className="flex items-center justify-between p-6 border-b border-gray-200">
                <h3 className="text-lg font-semibold text-gray-900">User Details</h3>
                <button
                  onClick={() => { setShowDetailModal(false); setSelectedUser(null); }}
                  className="p-2 hover:bg-gray-100 rounded-lg"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>
              <div className="p-6 overflow-y-auto max-h-[calc(90vh-140px)]">
                <div className="flex items-center gap-4 mb-6">
                  <div className="w-16 h-16 bg-indigo-100 rounded-full flex items-center justify-center">
                    <span className="text-2xl font-bold text-indigo-600">
                      {(selectedUser.name || selectedUser.email || 'U')[0].toUpperCase()}
                    </span>
                  </div>
                  <div>
                    <h2 className="text-xl font-bold text-gray-900">{selectedUser.name || 'No name'}</h2>
                    <p className="text-gray-500">{selectedUser.user_id}</p>
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div className="p-4 bg-gray-50 rounded-lg">
                    <p className="text-sm text-gray-500 mb-1">Email</p>
                    <p className="font-medium">{selectedUser.email || 'Not provided'}</p>
                  </div>
                  <div className="p-4 bg-gray-50 rounded-lg">
                    <p className="text-sm text-gray-500 mb-1">Phone</p>
                    <p className="font-medium">{selectedUser.phone || 'Not provided'}</p>
                  </div>
                  <div className="p-4 bg-gray-50 rounded-lg">
                    <p className="text-sm text-gray-500 mb-1">Role</p>
                    <span className={`px-3 py-1 rounded-full text-xs font-medium ${getRoleBadgeColor(selectedUser.role)}`}>
                      {selectedUser.role?.replace('_', ' ').toUpperCase()}
                    </span>
                  </div>
                  <div className="p-4 bg-gray-50 rounded-lg">
                    <p className="text-sm text-gray-500 mb-1">Status</p>
                    {getStatusBadge(selectedUser)}
                  </div>
                  <div className="p-4 bg-gray-50 rounded-lg">
                    <p className="text-sm text-gray-500 mb-1">Credibility Score</p>
                    <p className="font-medium">{selectedUser.credibility_score}/100</p>
                  </div>
                  <div className="p-4 bg-gray-50 rounded-lg">
                    <p className="text-sm text-gray-500 mb-1">Total Reports</p>
                    <p className="font-medium">{selectedUser.total_reports || 0}</p>
                  </div>
                  <div className="p-4 bg-gray-50 rounded-lg">
                    <p className="text-sm text-gray-500 mb-1">Joined</p>
                    <p className="font-medium">
                      {selectedUser.created_at ? formatDateIST(selectedUser.created_at) : 'N/A'}
                    </p>
                  </div>
                  <div className="p-4 bg-gray-50 rounded-lg">
                    <p className="text-sm text-gray-500 mb-1">Last Login</p>
                    <p className="font-medium">
                      {selectedUser.last_login ? formatDateTimeIST(selectedUser.last_login) : 'Never'}
                    </p>
                  </div>
                </div>

                {selectedUser.is_banned && (
                  <div className="mt-4 p-4 bg-red-50 border border-red-200 rounded-lg">
                    <div className="flex items-center gap-2 mb-2">
                      <AlertTriangle className="w-5 h-5 text-red-600" />
                      <span className="font-medium text-red-700">User is Banned</span>
                    </div>
                    <p className="text-sm text-red-600">{selectedUser.ban_reason || 'No reason provided'}</p>
                  </div>
                )}
              </div>
            </div>
          </div>
        )}
      </div>
    </DashboardLayout>
  );
}
