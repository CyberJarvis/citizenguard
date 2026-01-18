'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { motion, AnimatePresence } from 'framer-motion';
import ProtectedRoute from '@/components/ProtectedRoute';
import DashboardLayout from '@/components/DashboardLayout';
import useAuthStore from '@/context/AuthContext';
import api from '@/lib/api';
import { formatDateIST, getRelativeTimeIST } from '@/lib/dateUtils';
import {
  Ticket,
  Clock,
  CheckCircle,
  AlertTriangle,
  MapPin,
  Calendar,
  MessageSquare,
  ChevronRight,
  Loader2,
  Inbox,
  Timer,
  Zap,
  Bell,
  Plus
} from 'lucide-react';
import PageHeader from '@/components/PageHeader';

const priorityConfig = {
  emergency: { bg: 'bg-red-100', text: 'text-red-700', label: 'Emergency', dot: 'bg-red-500' },
  critical: { bg: 'bg-orange-100', text: 'text-orange-700', label: 'Critical', dot: 'bg-orange-500' },
  high: { bg: 'bg-yellow-100', text: 'text-yellow-700', label: 'High', dot: 'bg-yellow-500' },
  medium: { bg: 'bg-blue-100', text: 'text-blue-700', label: 'Medium', dot: 'bg-blue-500' },
  low: { bg: 'bg-gray-100', text: 'text-gray-700', label: 'Low', dot: 'bg-gray-500' }
};

const statusConfig = {
  open: { bg: 'bg-green-100', text: 'text-green-700', label: 'Open', icon: Clock },
  assigned: { bg: 'bg-blue-100', text: 'text-blue-700', label: 'Assigned', icon: Clock },
  in_progress: { bg: 'bg-purple-100', text: 'text-purple-700', label: 'In Progress', icon: Zap },
  awaiting_response: { bg: 'bg-yellow-100', text: 'text-yellow-700', label: 'Awaiting Response', icon: Bell },
  escalated: { bg: 'bg-red-100', text: 'text-red-700', label: 'Escalated', icon: AlertTriangle },
  resolved: { bg: 'bg-[#e8f4fc]', text: 'text-[#083a57]', label: 'Resolved', icon: CheckCircle },
  closed: { bg: 'bg-gray-100', text: 'text-gray-600', label: 'Closed', icon: CheckCircle }
};

function MyTicketsContent() {
  const router = useRouter();
  const { user } = useAuthStore();
  const [tickets, setTickets] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState('all');
  const [stats, setStats] = useState({
    total: 0,
    open: 0,
    in_progress: 0,
    resolved: 0
  });

  useEffect(() => {
    fetchUserTickets();
  }, []);

  const fetchUserTickets = async () => {
    try {
      setLoading(true);
      const response = await api.get('/tickets/my/tickets', {
        params: { page_size: 50 }
      });
      const ticketList = response.data.tickets || [];
      setTickets(ticketList);

      // Calculate stats
      setStats({
        total: ticketList.length,
        open: ticketList.filter(t => ['open', 'assigned'].includes(t.status)).length,
        in_progress: ticketList.filter(t => t.status === 'in_progress').length,
        resolved: ticketList.filter(t => ['resolved', 'closed'].includes(t.status)).length
      });
    } catch (error) {
      console.error('Error fetching tickets:', error);
    } finally {
      setLoading(false);
    }
  };

  const filteredTickets = tickets.filter(ticket => {
    if (filter === 'all') return true;
    if (filter === 'active') return !['resolved', 'closed'].includes(ticket.status);
    if (filter === 'resolved') return ['resolved', 'closed'].includes(ticket.status);
    return ticket.status === filter;
  });

  const formatDate = (dateStr) => {
    if (!dateStr) return 'N/A';
    return formatDateIST(dateStr);
  };

  const getTimeAgo = (dateStr) => {
    if (!dateStr) return '';
    return getRelativeTimeIST(dateStr);
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <motion.div
          initial={{ opacity: 0, scale: 0.9 }}
          animate={{ opacity: 1, scale: 1 }}
          className="text-center"
        >
          <div className="relative w-16 h-16 mx-auto mb-4">
            <div className="absolute inset-0 border-4 border-[#c5e1f5] rounded-full" />
            <div className="absolute inset-0 border-4 border-t-[#0d4a6f] rounded-full animate-spin" />
            <Ticket className="absolute inset-0 m-auto w-6 h-6 text-[#1a6b9a]" />
          </div>
          <p className="text-slate-600 font-medium">Loading your tickets...</p>
          <p className="text-slate-400 text-sm mt-1">Please wait</p>
        </motion.div>
      </div>
    );
  }

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      className="p-4 lg:p-6 pb-24 lg:pb-8"
    >
      {/* Top Icons Bar */}
      <PageHeader />

      {/* Header */}
      <motion.div
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        className="mb-6"
      >
        <h1 className="text-2xl font-semibold text-slate-900 flex items-center gap-3">
          <div className="w-10 h-10 bg-gradient-to-br from-[#0d4a6f] to-[#083a57] rounded-xl flex items-center justify-center shadow-lg shadow-[#0d4a6f]/20">
            <Ticket className="w-5 h-5 text-white" />
          </div>
          My Tickets
        </h1>
        <p className="text-slate-500 mt-1 ml-13">Track the progress of your verified reports</p>
      </motion.div>

      {/* Stats Cards */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.1 }}
        className="grid grid-cols-2 lg:grid-cols-4 gap-3 mb-6"
      >
        <div className="bg-white rounded-2xl shadow-sm border border-slate-100 p-4 hover:shadow-md transition-shadow">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs text-slate-500 font-medium">Total</span>
            <div className="w-8 h-8 bg-[#e8f4fc] rounded-xl flex items-center justify-center">
              <Ticket className="w-4 h-4 text-[#0d4a6f]" />
            </div>
          </div>
          <p className="text-2xl font-semibold text-slate-900">{stats.total}</p>
        </div>

        <div className="bg-white rounded-2xl shadow-sm border border-slate-100 p-4 hover:shadow-md transition-shadow">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs text-slate-500 font-medium">Open</span>
            <div className="w-8 h-8 bg-emerald-100 rounded-xl flex items-center justify-center">
              <Clock className="w-4 h-4 text-emerald-600" />
            </div>
          </div>
          <p className="text-2xl font-semibold text-emerald-600">{stats.open}</p>
        </div>

        <div className="bg-white rounded-2xl shadow-sm border border-slate-100 p-4 hover:shadow-md transition-shadow">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs text-slate-500 font-medium">In Progress</span>
            <div className="w-8 h-8 bg-purple-100 rounded-xl flex items-center justify-center">
              <Zap className="w-4 h-4 text-purple-600" />
            </div>
          </div>
          <p className="text-2xl font-semibold text-purple-600">{stats.in_progress}</p>
        </div>

        <div className="bg-white rounded-2xl shadow-sm border border-slate-100 p-4 hover:shadow-md transition-shadow">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs text-slate-500 font-medium">Resolved</span>
            <div className="w-8 h-8 bg-[#e8f4fc] rounded-xl flex items-center justify-center">
              <CheckCircle className="w-4 h-4 text-[#0d4a6f]" />
            </div>
          </div>
          <p className="text-2xl font-semibold text-[#0d4a6f]">{stats.resolved}</p>
        </div>
      </motion.div>

      {/* Filter Tabs */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.2 }}
        className="bg-white rounded-2xl shadow-sm border border-slate-100 p-1.5 mb-6"
      >
        <div className="flex space-x-1 overflow-x-auto scrollbar-hide">
          {[
            { id: 'all', label: 'All Tickets' },
            { id: 'active', label: 'Active' },
            { id: 'in_progress', label: 'In Progress' },
            { id: 'resolved', label: 'Resolved' }
          ].map((tab) => (
            <button
              key={tab.id}
              onClick={() => setFilter(tab.id)}
              className={`flex-1 min-w-fit px-4 py-2.5 rounded-xl text-sm font-medium transition-all ${
                filter === tab.id
                  ? 'bg-[#0d4a6f] text-white shadow-sm'
                  : 'text-slate-600 hover:bg-slate-50'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>
      </motion.div>

      {/* Tickets List */}
      {filteredTickets.length === 0 ? (
        <motion.div
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          className="bg-white rounded-2xl shadow-sm border border-slate-100 p-12 text-center"
        >
          <div className="w-20 h-20 bg-gradient-to-br from-slate-100 to-slate-50 rounded-2xl flex items-center justify-center mx-auto mb-5 shadow-inner">
            <Inbox className="w-10 h-10 text-slate-300" />
          </div>
          <h3 className="text-xl font-semibold text-slate-900 mb-2">No Tickets Found</h3>
          <p className="text-slate-500 mb-6 max-w-sm mx-auto">
            {filter === 'all'
              ? "You don't have any tickets yet. Tickets are created when your verified reports are being processed."
              : `No ${filter} tickets found.`
            }
          </p>
          {filter === 'all' && (
            <motion.button
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
              onClick={() => router.push('/report-hazard')}
              className="inline-flex items-center gap-2 px-6 py-3 bg-gradient-to-r from-orange-500 to-red-500 text-white rounded-xl font-semibold shadow-lg shadow-orange-500/25 hover:shadow-xl hover:shadow-orange-500/30 transition-all"
            >
              <Plus className="w-5 h-5" />
              Report a Hazard
            </motion.button>
          )}
        </motion.div>
      ) : (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.3 }}
          className="space-y-4"
        >
          <AnimatePresence>
            {filteredTickets.map((ticket, index) => {
              const priority = priorityConfig[ticket.priority] || priorityConfig.medium;
              const status = statusConfig[ticket.status] || statusConfig.open;
              const StatusIcon = status.icon;
              const isOverdue = ticket.resolution_due && new Date(ticket.resolution_due) < new Date() && !['resolved', 'closed'].includes(ticket.status);
              const hasUnread = ticket.unread_count_reporter > 0;

              return (
                <motion.div
                  key={ticket.ticket_id}
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -20 }}
                  transition={{ delay: index * 0.05 }}
                  onClick={() => router.push(`/my-tickets/${ticket.ticket_id}`)}
                  className={`bg-white rounded-2xl shadow-sm border ${hasUnread ? 'border-[#6badd9] ring-2 ring-[#e8f4fc]' : 'border-slate-100'} p-4 hover:shadow-lg hover:border-slate-200 transition-all cursor-pointer`}
                >
                <div className="flex items-start justify-between gap-4">
                  <div className="flex-1 min-w-0">
                    {/* Title & ID */}
                    <div className="flex items-center gap-2 mb-2">
                      {hasUnread && (
                        <span className="w-2 h-2 bg-[#1a6b9a] rounded-full animate-pulse"></span>
                      )}
                      <h3 className="font-semibold text-slate-900 truncate">{ticket.title}</h3>
                    </div>
                    <p className="text-xs font-mono text-slate-400 mb-2">{ticket.ticket_id}</p>

                    {/* Status & Priority Badges */}
                    <div className="flex flex-wrap items-center gap-2 mb-3">
                      <span className={`px-2.5 py-1 rounded-full text-xs font-semibold flex items-center gap-1 ${status.bg} ${status.text}`}>
                        <StatusIcon className="w-3 h-3" />
                        {status.label}
                      </span>
                      <span className={`px-2.5 py-1 rounded-full text-xs font-semibold ${priority.bg} ${priority.text}`}>
                        {priority.label}
                      </span>
                      {isOverdue && (
                        <span className="px-2.5 py-1 bg-red-100 text-red-700 rounded-full text-xs font-semibold flex items-center gap-1">
                          <Timer className="w-3 h-3" />
                          Overdue
                        </span>
                      )}
                      {hasUnread && (
                        <span className="px-2.5 py-1 bg-[#e8f4fc] text-[#083a57] rounded-full text-xs font-semibold flex items-center gap-1">
                          <MessageSquare className="w-3 h-3" />
                          {ticket.unread_count_reporter} new
                        </span>
                      )}
                    </div>

                    {/* Meta Info */}
                    <div className="flex flex-wrap items-center gap-4 text-xs text-slate-500">
                      <div className="flex items-center gap-1">
                        <MapPin className="w-3.5 h-3.5 text-[#0d4a6f]" />
                        <span className="truncate max-w-[150px]">{ticket.location_address || 'Location N/A'}</span>
                      </div>
                      <div className="flex items-center gap-1">
                        <Calendar className="w-3.5 h-3.5 text-slate-400" />
                        <span>{formatDate(ticket.created_at)}</span>
                      </div>
                      {ticket.last_message_at && (
                        <div className="flex items-center gap-1">
                          <MessageSquare className="w-3.5 h-3.5 text-slate-400" />
                          <span>Last update: {getTimeAgo(ticket.last_message_at)}</span>
                        </div>
                      )}
                    </div>
                  </div>

                  <ChevronRight className="w-5 h-5 text-slate-400 flex-shrink-0 group-hover:text-[#0d4a6f] transition-colors" />
                </div>
              </motion.div>
            );
          })}
          </AnimatePresence>
        </motion.div>
      )}
    </motion.div>
  );
}

export default function MyTicketsPage() {
  return (
    <ProtectedRoute>
      <DashboardLayout>
        <MyTicketsContent />
      </DashboardLayout>
    </ProtectedRoute>
  );
}
