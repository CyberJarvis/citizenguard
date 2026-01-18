'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import DashboardLayout from '@/components/DashboardLayout';
import PageHeader from '@/components/PageHeader';
import useAuthStore from '@/context/AuthContext';
import api from '@/lib/api';
import {
  TicketCard,
  TicketStatusBadge,
  TicketPriorityBadge,
  SLAIndicator
} from '@/components/tickets';
import {
  Ticket,
  Search,
  Filter,
  Clock,
  AlertTriangle,
  CheckCircle,
  XCircle,
  MapPin,
  Calendar,
  User,
  MessageSquare,
  ChevronRight,
  Gauge,
  Zap,
  RefreshCw,
  ArrowUpRight,
  Timer,
  AlertCircle,
  UserCheck,
  Users
} from 'lucide-react';
import { ExportButton } from '@/components/export';

const priorityConfig = {
  emergency: { bg: 'bg-red-100', text: 'text-red-700', border: 'border-red-300', dot: 'bg-red-500', label: 'Emergency' },
  critical: { bg: 'bg-orange-100', text: 'text-orange-700', border: 'border-orange-300', dot: 'bg-orange-500', label: 'Critical' },
  high: { bg: 'bg-yellow-100', text: 'text-yellow-700', border: 'border-yellow-300', dot: 'bg-yellow-500', label: 'High' },
  medium: { bg: 'bg-blue-100', text: 'text-blue-700', border: 'border-blue-300', dot: 'bg-blue-500', label: 'Medium' },
  low: { bg: 'bg-gray-100', text: 'text-gray-700', border: 'border-gray-300', dot: 'bg-gray-400', label: 'Low' }
};

const statusConfig = {
  open: { bg: 'bg-green-100', text: 'text-green-700', icon: AlertCircle, label: 'Open' },
  assigned: { bg: 'bg-blue-100', text: 'text-blue-700', icon: User, label: 'Assigned' },
  in_progress: { bg: 'bg-purple-100', text: 'text-purple-700', icon: Clock, label: 'In Progress' },
  escalated: { bg: 'bg-red-100', text: 'text-red-700', icon: AlertTriangle, label: 'Escalated' },
  resolved: { bg: 'bg-[#c5e1f5]', text: 'text-[#0d4a6f]', icon: CheckCircle, label: 'Resolved' },
  closed: { bg: 'bg-gray-100', text: 'text-gray-600', icon: XCircle, label: 'Closed' }
};

export default function TicketsPage() {
  const router = useRouter();
  const { user, isLoading: authLoading, initialize } = useAuthStore();

  const [tickets, setTickets] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState('all');
  const [priorityFilter, setPriorityFilter] = useState('all');
  const [assignedToMe, setAssignedToMe] = useState(false);
  const [useV2Queue, setUseV2Queue] = useState(true); // Use V2 role-based queue
  const [stats, setStats] = useState({
    total: 0,
    open: 0,
    in_progress: 0,
    resolved: 0,
    overdue: 0,
    escalated: 0,
    myTickets: 0
  });

  // Initialize auth on mount to validate token
  useEffect(() => {
    initialize();
  }, [initialize]);

  useEffect(() => {
    if (!authLoading && user) {
      if (!['analyst', 'authority', 'authority_admin', 'admin'].includes(user.role)) {
        router.push('/dashboard');
      } else {
        fetchTickets();
      }
    }
  }, [user, authLoading, statusFilter, priorityFilter, assignedToMe]);

  const fetchTickets = async () => {
    try {
      setLoading(true);

      let response;
      if (useV2Queue) {
        // Use V2 role-based queue endpoint
        const params = new URLSearchParams();
        params.append('role', 'analyst');
        if (statusFilter !== 'all') params.append('status', statusFilter);
        if (priorityFilter !== 'all') params.append('priority', priorityFilter);
        if (assignedToMe) params.append('assigned_to_me', 'true');

        try {
          response = await api.get(`/tickets/v2/queue?${params.toString()}`);
        } catch (e) {
          // Fallback to V1 if V2 not available
          console.log('V2 queue not available, falling back to V1');
          setUseV2Queue(false);
          const v1Params = new URLSearchParams();
          if (statusFilter !== 'all') v1Params.append('status', statusFilter);
          if (priorityFilter !== 'all') v1Params.append('priority', priorityFilter);
          response = await api.get(`/tickets?${v1Params.toString()}`);
        }
      } else {
        // V1 endpoint
        const params = new URLSearchParams();
        if (statusFilter !== 'all') params.append('status', statusFilter);
        if (priorityFilter !== 'all') params.append('priority', priorityFilter);
        response = await api.get(`/tickets?${params.toString()}`);
      }

      setTickets(response.data.tickets || response.data || []);

      // Calculate stats
      const allTickets = response.data.tickets || response.data || [];
      const now = new Date();
      setStats({
        total: allTickets.length,
        open: allTickets.filter(t => t.status === 'open').length,
        in_progress: allTickets.filter(t => t.status === 'in_progress' || t.status === 'assigned').length,
        resolved: allTickets.filter(t => t.status === 'resolved' || t.status === 'closed').length,
        overdue: allTickets.filter(t => new Date(t.resolution_due) < now && !['resolved', 'closed'].includes(t.status)).length,
        escalated: allTickets.filter(t => t.status === 'escalated' || t.is_escalated).length,
        myTickets: allTickets.filter(t =>
          t.assigned_analyst_id === user?.user_id ||
          t.assignment?.analyst_id === user?.user_id
        ).length
      });
    } catch (error) {
      console.error('Error fetching tickets:', error);
    } finally {
      setLoading(false);
    }
  };

  const filteredTickets = tickets.filter(ticket => {
    if (!searchQuery) return true;
    const query = searchQuery.toLowerCase();
    return (
      ticket.ticket_id?.toLowerCase().includes(query) ||
      ticket.title?.toLowerCase().includes(query) ||
      ticket.hazard_type?.toLowerCase().includes(query) ||
      ticket.location_address?.toLowerCase().includes(query)
    );
  });

  const formatDate = (dateStr) => {
    if (!dateStr) return 'N/A';
    return new Date(dateStr).toLocaleDateString('en-IN', {
      day: 'numeric',
      month: 'short',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  const isOverdue = (ticket) => {
    if (['resolved', 'closed'].includes(ticket.status)) return false;
    return new Date(ticket.resolution_due) < new Date();
  };

  const getTimeRemaining = (dueDate) => {
    if (!dueDate) return null;
    const now = new Date();
    const due = new Date(dueDate);
    const diff = due - now;

    if (diff < 0) {
      const hours = Math.abs(Math.floor(diff / (1000 * 60 * 60)));
      return { overdue: true, text: `${hours}h overdue` };
    }

    const hours = Math.floor(diff / (1000 * 60 * 60));
    if (hours < 24) {
      return { overdue: false, text: `${hours}h remaining`, urgent: hours < 4 };
    }
    const days = Math.floor(hours / 24);
    return { overdue: false, text: `${days}d remaining`, urgent: false };
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
        <div className="bg-gradient-to-r from-[#0d4a6f] to-[#083a57] rounded-2xl shadow-lg p-6 text-white relative overflow-hidden">
          <div className="absolute bottom-0 left-0 right-0 opacity-10">
            <svg viewBox="0 0 1440 120" className="w-full h-12">
              <path fill="white" d="M0,32L48,37.3C96,43,192,53,288,58.7C384,64,480,64,576,58.7C672,53,768,43,864,42.7C960,43,1056,53,1152,58.7C1248,64,1344,64,1392,64L1440,64L1440,120L1392,120C1344,120,1248,120,1152,120C1056,120,960,120,864,120C768,120,672,120,576,120C480,120,384,120,288,120C192,120,96,120,48,120L0,120Z"></path>
            </svg>
          </div>
          <div className="relative z-10 flex items-center justify-between">
            <div>
              <h1 className="text-2xl font-semibold flex items-center gap-3">
                <div className="p-2 bg-white/20 rounded-xl backdrop-blur-sm">
                  <Ticket className="w-6 h-6 text-white" />
                </div>
                Support Tickets
              </h1>
              <p className="text-[#9ecbec] mt-1">Manage and respond to hazard report tickets</p>
            </div>
            <button
              onClick={fetchTickets}
              className="flex items-center gap-2 px-4 py-2 bg-white/10 border border-white/20 rounded-xl hover:bg-white/20 transition-colors text-white"
            >
              <RefreshCw className="w-4 h-4" />
              Refresh
            </button>
          </div>
        </div>

        {/* Stats Cards */}
        <div className="grid grid-cols-2 md:grid-cols-6 gap-4">
          <div className="bg-white rounded-xl p-4 border border-gray-200 shadow-sm">
            <div className="flex items-center justify-between">
              <span className="text-sm text-gray-600">Total</span>
              <Ticket className="w-5 h-5 text-gray-400" />
            </div>
            <div className="text-2xl font-semibold text-gray-900 mt-1">{stats.total}</div>
          </div>
          <div
            className={`bg-white rounded-xl p-4 border shadow-sm cursor-pointer transition-all ${
              assignedToMe ? 'border-[#1a6b9a] ring-2 ring-[#c5e1f5]' : 'border-[#c5e1f5] hover:border-[#1a6b9a]'
            }`}
            onClick={() => setAssignedToMe(!assignedToMe)}
          >
            <div className="flex items-center justify-between">
              <span className="text-sm text-[#0d4a6f]">My Tickets</span>
              <UserCheck className="w-5 h-5 text-[#1a6b9a]" />
            </div>
            <div className="text-2xl font-semibold text-[#0d4a6f] mt-1">{stats.myTickets}</div>
          </div>
          <div className="bg-white rounded-xl p-4 border border-green-200 shadow-sm">
            <div className="flex items-center justify-between">
              <span className="text-sm text-green-600">Open</span>
              <AlertCircle className="w-5 h-5 text-green-500" />
            </div>
            <div className="text-2xl font-semibold text-green-700 mt-1">{stats.open}</div>
          </div>
          <div className="bg-white rounded-xl p-4 border border-[#c5e1f5] shadow-sm">
            <div className="flex items-center justify-between">
              <span className="text-sm text-[#0d4a6f]">In Progress</span>
              <Clock className="w-5 h-5 text-[#1a6b9a]" />
            </div>
            <div className="text-2xl font-semibold text-[#0d4a6f] mt-1">{stats.in_progress}</div>
          </div>
          <div className="bg-white rounded-xl p-4 border border-red-200 shadow-sm">
            <div className="flex items-center justify-between">
              <span className="text-sm text-red-600">Escalated</span>
              <AlertTriangle className="w-5 h-5 text-red-500" />
            </div>
            <div className="text-2xl font-semibold text-red-700 mt-1">{stats.escalated}</div>
          </div>
          <div className="bg-white rounded-xl p-4 border border-orange-200 shadow-sm">
            <div className="flex items-center justify-between">
              <span className="text-sm text-orange-600">SLA Breach</span>
              <Timer className="w-5 h-5 text-orange-500" />
            </div>
            <div className="text-2xl font-semibold text-orange-700 mt-1">{stats.overdue}</div>
          </div>
        </div>

        {/* Filters */}
        <div className="bg-white rounded-xl p-4 border border-gray-200 shadow-sm">
          <div className="flex flex-col md:flex-row gap-4">
            {/* Search */}
            <div className="flex-1 relative">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-5 h-5 text-gray-400" />
              <input
                type="text"
                placeholder="Search tickets by ID, title, hazard type, location..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full pl-10 pr-4 py-2 border border-gray-200 rounded-xl focus:ring-2 focus:ring-[#1a6b9a] focus:border-transparent"
              />
            </div>

            {/* Status Filter */}
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="px-4 py-2 border border-gray-200 rounded-xl focus:ring-2 focus:ring-[#1a6b9a]"
            >
              <option value="all">All Status</option>
              <option value="open">Open</option>
              <option value="assigned">Assigned</option>
              <option value="in_progress">In Progress</option>
              <option value="escalated">Escalated</option>
              <option value="resolved">Resolved</option>
              <option value="closed">Closed</option>
            </select>

            {/* Priority Filter */}
            <select
              value={priorityFilter}
              onChange={(e) => setPriorityFilter(e.target.value)}
              className="px-4 py-2 border border-gray-200 rounded-xl focus:ring-2 focus:ring-[#1a6b9a]"
            >
              <option value="all">All Priority</option>
              <option value="emergency">Emergency</option>
              <option value="critical">Critical</option>
              <option value="high">High</option>
              <option value="medium">Medium</option>
              <option value="low">Low</option>
            </select>

            {/* Export Button */}
            <ExportButton
              dataType="tickets"
              currentFilters={{ status: statusFilter, priority: priorityFilter }}
              size="md"
            />
          </div>
        </div>

        {/* Tickets List */}
        {loading ? (
          <div className="flex items-center justify-center py-12">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-[#0d4a6f]"></div>
          </div>
        ) : filteredTickets.length === 0 ? (
          <div className="bg-white rounded-xl p-12 border border-gray-200 text-center">
            <Ticket className="w-16 h-16 text-gray-300 mx-auto mb-4" />
            <h3 className="text-lg font-semibold text-gray-700">No tickets found</h3>
            <p className="text-gray-500 mt-1">Try adjusting your filters or search query</p>
          </div>
        ) : (
          <div className="space-y-4">
            {filteredTickets.map((ticket) => {
              const priority = priorityConfig[ticket.priority] || priorityConfig.medium;
              const status = statusConfig[ticket.status] || statusConfig.open;
              const StatusIcon = status.icon;
              const timeRemaining = getTimeRemaining(ticket.resolution_due);
              const overdue = isOverdue(ticket);

              return (
                <div
                  key={ticket.ticket_id}
                  onClick={() => router.push(`/analyst/tickets/${ticket.ticket_id}`)}
                  className={`bg-white rounded-xl border-2 ${overdue ? 'border-red-300 bg-red-50/30' : 'border-gray-200'} p-5 hover:shadow-lg transition-all cursor-pointer group`}
                >
                  <div className="flex items-start gap-4">
                    {/* Priority Indicator */}
                    <div className={`w-1.5 h-full min-h-[80px] rounded-full ${priority.dot}`} />

                    {/* Main Content */}
                    <div className="flex-1 min-w-0">
                      {/* Header Row */}
                      <div className="flex items-start justify-between gap-4 mb-3">
                        <div>
                          <div className="flex items-center gap-2 mb-1">
                            <span className="text-sm font-mono text-gray-500">{ticket.ticket_id}</span>
                            {overdue && (
                              <span className="px-2 py-0.5 bg-red-100 text-red-700 text-xs font-medium rounded-full flex items-center gap-1">
                                <Timer className="w-3 h-3" />
                                OVERDUE
                              </span>
                            )}
                          </div>
                          <h3 className="text-lg font-semibold text-gray-900 group-hover:text-[#0d4a6f] transition-colors line-clamp-1">
                            {ticket.title}
                          </h3>
                        </div>

                        <div className="flex items-center gap-2 flex-shrink-0">
                          {/* Verification Score */}
                          {ticket.metadata?.verification_score && (
                            <div className={`flex items-center gap-1 px-2.5 py-1 rounded-full text-sm font-semibold ${
                              ticket.metadata.verification_score >= 75 ? 'bg-green-100 text-green-700' :
                              ticket.metadata.verification_score >= 40 ? 'bg-yellow-100 text-yellow-700' :
                              'bg-red-100 text-red-700'
                            }`}>
                              <Gauge className="w-4 h-4" />
                              {ticket.metadata.verification_score.toFixed(0)}%
                            </div>
                          )}

                          {/* Priority Badge */}
                          <span className={`px-3 py-1 rounded-full text-xs font-semibold ${priority.bg} ${priority.text}`}>
                            {priority.label}
                          </span>

                          {/* Status Badge */}
                          <span className={`flex items-center gap-1 px-3 py-1 rounded-full text-xs font-semibold ${status.bg} ${status.text}`}>
                            <StatusIcon className="w-3 h-3" />
                            {status.label}
                          </span>
                        </div>
                      </div>

                      {/* Info Row */}
                      <div className="flex flex-wrap items-center gap-4 text-sm text-gray-600">
                        {/* Hazard Type */}
                        <div className="flex items-center gap-1.5">
                          <AlertTriangle className="w-4 h-4 text-orange-500" />
                          <span className="capitalize">{ticket.hazard_type?.replace('_', ' ')}</span>
                        </div>

                        {/* Location */}
                        <div className="flex items-center gap-1.5">
                          <MapPin className="w-4 h-4 text-gray-400" />
                          <span className="truncate max-w-[200px]">{ticket.location_address || 'Unknown'}</span>
                        </div>

                        {/* Reporter */}
                        <div className="flex items-center gap-1.5">
                          <User className="w-4 h-4 text-gray-400" />
                          <span>{ticket.reporter_name || 'Unknown'}</span>
                        </div>

                        {/* Messages */}
                        <div className="flex items-center gap-1.5">
                          <MessageSquare className="w-4 h-4 text-gray-400" />
                          <span>{ticket.total_messages || 0} messages</span>
                        </div>

                        {/* Created Date */}
                        <div className="flex items-center gap-1.5">
                          <Calendar className="w-4 h-4 text-gray-400" />
                          <span>{formatDate(ticket.created_at)}</span>
                        </div>
                      </div>

                      {/* SLA Row */}
                      {timeRemaining && (
                        <div className={`mt-3 flex items-center gap-2 text-sm ${
                          timeRemaining.overdue ? 'text-red-600' :
                          timeRemaining.urgent ? 'text-orange-600' : 'text-gray-500'
                        }`}>
                          <Timer className="w-4 h-4" />
                          <span className="font-medium">{timeRemaining.text}</span>
                          <span className="text-gray-400">|</span>
                          <span>Due: {formatDate(ticket.resolution_due)}</span>
                        </div>
                      )}
                    </div>

                    {/* Arrow */}
                    <ChevronRight className="w-5 h-5 text-gray-400 group-hover:text-[#0d4a6f] transition-colors flex-shrink-0" />
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </DashboardLayout>
  );
}
