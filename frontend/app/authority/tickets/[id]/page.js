'use client';

import { useEffect, useState, useRef } from 'react';
import { useRouter, useParams } from 'next/navigation';
import DashboardLayout from '@/components/DashboardLayout';
import PageHeader from '@/components/PageHeader';
import useAuthStore from '@/context/AuthContext';
import api from '@/lib/api';
import {
  ChevronLeft,
  AlertTriangle,
  XCircle,
  MapPin,
  Calendar,
  User,
  MessageSquare,
  Send,
  Gauge,
  Zap,
  Timer,
  Activity,
  ExternalLink,
  Shield,
  Eye,
  Lock,
  Unlock,
  RefreshCw,
  Play,
  CheckCheck,
  UserPlus,
  Users,
  Building2,
  Search,
  Trash2,
  ArrowUpCircle
} from 'lucide-react';

const priorityConfig = {
  emergency: { bg: 'bg-red-100', text: 'text-red-700', border: 'border-red-300', label: 'Emergency' },
  critical: { bg: 'bg-orange-100', text: 'text-orange-700', border: 'border-orange-300', label: 'Critical' },
  high: { bg: 'bg-yellow-100', text: 'text-yellow-700', border: 'border-yellow-300', label: 'High' },
  medium: { bg: 'bg-blue-100', text: 'text-blue-700', border: 'border-blue-300', label: 'Medium' },
  low: { bg: 'bg-gray-100', text: 'text-gray-700', border: 'border-gray-300', label: 'Low' }
};

const statusConfig = {
  open: { bg: 'bg-green-100', text: 'text-green-700', label: 'Open' },
  assigned: { bg: 'bg-blue-100', text: 'text-blue-700', label: 'Assigned' },
  in_progress: { bg: 'bg-purple-100', text: 'text-purple-700', label: 'In Progress' },
  awaiting_response: { bg: 'bg-amber-100', text: 'text-amber-700', label: 'Awaiting Response' },
  escalated: { bg: 'bg-red-100', text: 'text-red-700', label: 'Escalated' },
  resolved: { bg: 'bg-[#e8f4fc]', text: 'text-[#083a57]', label: 'Resolved' },
  closed: { bg: 'bg-gray-100', text: 'text-gray-600', label: 'Closed' }
};

export default function AuthorityTicketDetailPage() {
  const router = useRouter();
  const params = useParams();
  const { user, isLoading: authLoading } = useAuthStore();
  const messagesEndRef = useRef(null);

  const [ticket, setTicket] = useState(null);
  const [messages, setMessages] = useState([]);
  const [loading, setLoading] = useState(true);
  const [newMessage, setNewMessage] = useState('');
  const [isInternal, setIsInternal] = useState(false);
  const [sending, setSending] = useState(false);
  const [updatingStatus, setUpdatingStatus] = useState(false);

  // Analyst assignment states
  const [showAnalystPanel, setShowAnalystPanel] = useState(false);
  const [analysts, setAnalysts] = useState([]);
  const [loadingAnalysts, setLoadingAnalysts] = useState(false);
  const [analystSearch, setAnalystSearch] = useState('');
  const [addingAnalyst, setAddingAnalyst] = useState(false);
  const [participants, setParticipants] = useState({});
  const [participantsLoaded, setParticipantsLoaded] = useState(false);

  // Escalation states
  const [showEscalateModal, setShowEscalateModal] = useState(false);
  const [escalationReason, setEscalationReason] = useState('');
  const [escalating, setEscalating] = useState(false);

  // Close ticket states
  const [showCloseModal, setShowCloseModal] = useState(false);
  const [closeReason, setCloseReason] = useState('');
  const [closing, setClosing] = useState(false);

  useEffect(() => {
    if (!authLoading && user) {
      if (!['authority', 'authority_admin', 'admin'].includes(user.role)) {
        router.push('/dashboard');
      } else {
        fetchTicketDetails();
        // Auto-refresh every 15 seconds for real-time updates
        const interval = setInterval(() => {
          fetchTicketDetails();
        }, 15000);
        return () => clearInterval(interval);
      }
    }
  }, [user, authLoading, params.id]);

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  const fetchTicketDetails = async () => {
    try {
      setLoading(true);
      const [ticketRes, messagesRes] = await Promise.all([
        api.get(`/tickets/${params.id}`),
        api.get(`/tickets/${params.id}/messages`)
      ]);
      // API returns { ticket: {...}, messages: [...], activities: [...], feedback: ... }
      // Extract the ticket object from the response
      const ticketData = ticketRes.data.ticket || ticketRes.data;
      setTicket(ticketData);
      setMessages(messagesRes.data.messages || []);
    } catch (error) {
      console.error('Error fetching ticket:', error);
      alert('Failed to load ticket details');
      router.push('/authority/tickets');
    } finally {
      setLoading(false);
    }
  };

  const sendMessage = async () => {
    if (!newMessage.trim()) return;

    try {
      setSending(true);
      await api.post(`/tickets/${params.id}/messages`, {
        content: newMessage,
        is_internal: isInternal
      });
      setNewMessage('');
      fetchTicketDetails();
    } catch (error) {
      console.error('Error sending message:', error);
      alert('Failed to send message');
    } finally {
      setSending(false);
    }
  };

  const updateStatus = async (newStatus) => {
    try {
      setUpdatingStatus(true);
      await api.patch(`/tickets/${params.id}/status`, { status: newStatus });
      fetchTicketDetails();
    } catch (error) {
      console.error('Error updating status:', error);
      alert('Failed to update status');
    } finally {
      setUpdatingStatus(false);
    }
  };

  // Fetch analysts for assignment
  const fetchAnalysts = async (search = '') => {
    try {
      setLoadingAnalysts(true);
      const response = await api.get('/tickets/lookup/analysts', {
        params: {
          search: search || undefined,
          limit: 20
        }
      });
      setAnalysts(response.data.analysts || []);
    } catch (error) {
      console.error('Error fetching analysts:', error);
      setAnalysts([]);
    } finally {
      setLoadingAnalysts(false);
    }
  };

  // Fetch current participants
  const fetchParticipants = async () => {
    try {
      setParticipantsLoaded(false);
      const response = await api.get(`/tickets/${params.id}/participants`);
      setParticipants(response.data.participants || {});
      setParticipantsLoaded(true);
    } catch (error) {
      console.error('Error fetching participants:', error);
      setParticipantsLoaded(true);
    }
  };

  // Add analyst to ticket
  const addAnalyst = async (analystUser) => {
    const isAlreadyAdded = isAlreadyParticipant(analystUser.user_id);

    if (isAlreadyAdded) {
      alert(`${analystUser.name} is already a participant in this ticket`);
      return;
    }

    try {
      setAddingAnalyst(true);
      const notes = `Added Analyst - ${analystUser.name}`.replace(/[&?#]/g, '');

      await api.post(`/tickets/${params.id}/participants`, null, {
        params: {
          user_id: analystUser.user_id,
          notes: notes,
          can_message: true
        }
      });

      alert(`${analystUser.name} has been added to this ticket`);
      fetchTicketDetails();
      fetchParticipants();
      setShowAnalystPanel(false);
    } catch (error) {
      console.error('Error adding analyst:', error);
      const errorMsg = error.response?.data?.detail || 'Failed to add analyst';
      alert(typeof errorMsg === 'string' ? errorMsg : JSON.stringify(errorMsg));
    } finally {
      setAddingAnalyst(false);
    }
  };

  // Remove participant from ticket
  const removeParticipant = async (userId) => {
    if (!confirm('Are you sure you want to remove this participant?')) return;
    try {
      await api.delete(`/tickets/${params.id}/participants/${userId}`);
      fetchTicketDetails();
      fetchParticipants();
    } catch (error) {
      console.error('Error removing participant:', error);
      alert(error.response?.data?.detail || 'Failed to remove participant');
    }
  };

  // Escalate ticket
  const escalateTicket = async () => {
    if (!escalationReason.trim()) {
      alert('Please provide a reason for escalation');
      return;
    }

    try {
      setEscalating(true);
      await api.post(`/tickets/${params.id}/escalate`, {
        reason: escalationReason,
        new_priority: 'critical'
      });
      alert('Ticket has been escalated successfully');
      setShowEscalateModal(false);
      setEscalationReason('');
      fetchTicketDetails();
    } catch (error) {
      console.error('Error escalating ticket:', error);
      alert(error.response?.data?.detail || 'Failed to escalate ticket');
    } finally {
      setEscalating(false);
    }
  };

  // Close ticket
  const closeTicket = async () => {
    try {
      setClosing(true);
      await api.post(`/tickets/${params.id}/close`, {
        resolution_notes: closeReason || 'Closed by authority'
      });
      alert('Ticket has been closed successfully');
      setShowCloseModal(false);
      setCloseReason('');
      fetchTicketDetails();
    } catch (error) {
      console.error('Error closing ticket:', error);
      alert(error.response?.data?.detail || 'Failed to close ticket');
    } finally {
      setClosing(false);
    }
  };

  // Check if user is already a participant
  const isAlreadyParticipant = (userId) => {
    if (!ticket || !userId) return false;

    const normalizedUserId = String(userId).trim();

    if (ticket.reporter_id && String(ticket.reporter_id).trim() === normalizedUserId) return true;
    if (ticket.assigned_analyst_id && String(ticket.assigned_analyst_id).trim() === normalizedUserId) return true;
    if (ticket.authority_id && String(ticket.authority_id).trim() === normalizedUserId) return true;

    if (participants && typeof participants === 'object' && !Array.isArray(participants)) {
      if (participants.reporter?.user_id && String(participants.reporter.user_id).trim() === normalizedUserId) return true;
      if (participants.assigned_analyst?.user_id && String(participants.assigned_analyst.user_id).trim() === normalizedUserId) return true;
      if (participants.authority?.user_id && String(participants.authority.user_id).trim() === normalizedUserId) return true;
    }

    const additionalParticipants = (participants && !Array.isArray(participants) ? participants.additional_participants : null)
      || ticket.additional_participants
      || [];

    for (const p of additionalParticipants) {
      if (p.user_id && String(p.user_id).trim() === normalizedUserId && p.is_active !== false) {
        return true;
      }
    }

    return false;
  };

  // Load analysts when panel opens
  useEffect(() => {
    if (showAnalystPanel) {
      fetchAnalysts();
      fetchParticipants();
    }
  }, [showAnalystPanel]);

  // Debounced search for analysts
  useEffect(() => {
    const timer = setTimeout(() => {
      if (showAnalystPanel) {
        fetchAnalysts(analystSearch);
      }
    }, 300);
    return () => clearTimeout(timer);
  }, [analystSearch]);

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

  const formatMessageTime = (dateStr) => {
    if (!dateStr) return '';
    const date = new Date(dateStr);
    const now = new Date();
    const diff = now - date;
    const hours = Math.floor(diff / (1000 * 60 * 60));
    const minutes = Math.floor(diff / (1000 * 60));

    if (minutes < 1) return 'Just now';
    if (minutes < 60) return `${minutes}m ago`;
    if (hours < 24) return `${hours}h ago`;
    return date.toLocaleDateString('en-IN', { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' });
  };

  if (authLoading || loading || !user) {
    return (
      <DashboardLayout>
        <div className="flex items-center justify-center min-h-screen">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-[#0d4a6f]"></div>
        </div>
      </DashboardLayout>
    );
  }

  if (!ticket) {
    return (
      <DashboardLayout>
        <div className="p-6">
          <p className="text-red-600">Ticket not found</p>
        </div>
      </DashboardLayout>
    );
  }

  const priority = priorityConfig[ticket.priority] || priorityConfig.medium;
  const status = statusConfig[ticket.status] || statusConfig.open;
  const isOverdue = new Date(ticket.resolution_due) < new Date() && !['resolved', 'closed'].includes(ticket.status);

  return (
    <DashboardLayout>
      <div className="p-4 lg:p-6">
        {/* Page Header - Desktop Only */}
        <PageHeader />
      </div>
      <div className="h-[calc(100vh-64px)] flex flex-col">
        {/* Header */}
        <div className="p-4 bg-white border-b border-gray-200 flex-shrink-0">
          <div className="flex items-center gap-4">
            <button
              onClick={() => router.push('/authority/tickets')}
              className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
            >
              <ChevronLeft className="w-5 h-5" />
            </button>
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2 mb-1">
                <span className="text-sm font-mono text-gray-500">{ticket.ticket_id}</span>
                {isOverdue && (
                  <span className="px-2 py-0.5 bg-red-100 text-red-700 text-xs font-medium rounded-full flex items-center gap-1">
                    <Timer className="w-3 h-3" />
                    OVERDUE
                  </span>
                )}
                {ticket.is_escalated && (
                  <span className="px-2 py-0.5 bg-orange-100 text-orange-700 text-xs font-medium rounded-full flex items-center gap-1">
                    <ArrowUpCircle className="w-3 h-3" />
                    ESCALATED
                  </span>
                )}
              </div>
              <h1 className="text-lg font-bold text-gray-900 truncate">{ticket.title}</h1>
            </div>

            {/* Status Actions */}
            <div className="flex items-center gap-2">
              <span className={`px-3 py-1.5 rounded-full text-sm font-semibold ${priority.bg} ${priority.text}`}>
                {priority.label}
              </span>
              <span className={`px-3 py-1.5 rounded-full text-sm font-semibold ${status.bg} ${status.text}`}>
                {status.label}
              </span>

              {/* Quick Actions - Authority specific */}
              {ticket.status === 'open' && (
                <button
                  onClick={() => updateStatus('in_progress')}
                  disabled={updatingStatus}
                  className="flex items-center gap-1 px-3 py-1.5 bg-[#0d4a6f] text-white rounded-xl text-sm font-medium hover:bg-[#083a57] transition-colors disabled:opacity-50"
                >
                  <Play className="w-4 h-4" />
                  Start
                </button>
              )}
              {ticket.status === 'in_progress' && (
                <button
                  onClick={() => updateStatus('resolved')}
                  disabled={updatingStatus}
                  className="flex items-center gap-1 px-3 py-1.5 bg-[#0d4a6f] text-white rounded-xl text-sm font-medium hover:bg-[#083a57] transition-colors disabled:opacity-50"
                >
                  <CheckCheck className="w-4 h-4" />
                  Resolve
                </button>
              )}
              {ticket.status === 'resolved' && (
                <button
                  onClick={() => setShowCloseModal(true)}
                  disabled={updatingStatus}
                  className="flex items-center gap-1 px-3 py-1.5 bg-gray-600 text-white rounded-xl text-sm font-medium hover:bg-gray-700 transition-colors disabled:opacity-50"
                >
                  <XCircle className="w-4 h-4" />
                  Close
                </button>
              )}
              {/* Escalate button - show for non-closed tickets */}
              {!['resolved', 'closed'].includes(ticket.status) && !ticket.is_escalated && (
                <button
                  onClick={() => setShowEscalateModal(true)}
                  className="flex items-center gap-1 px-3 py-1.5 bg-orange-600 text-white rounded-xl text-sm font-medium hover:bg-orange-700 transition-colors"
                >
                  <ArrowUpCircle className="w-4 h-4" />
                  Escalate
                </button>
              )}
            </div>
          </div>
        </div>

        {/* Main Content */}
        <div className="flex-1 flex overflow-hidden">
          {/* Left Panel - Ticket Details */}
          <div className="w-1/3 border-r border-gray-200 bg-gray-50 overflow-y-auto">
            <div className="p-4 space-y-4">
              {/* Verification Score */}
              {ticket.metadata?.verification_score && (
                <div className={`p-4 rounded-xl ${
                  ticket.metadata.verification_score >= 75 ? 'bg-gradient-to-r from-green-500 to-emerald-600' :
                  ticket.metadata.verification_score >= 40 ? 'bg-gradient-to-r from-yellow-500 to-orange-500' :
                  'bg-gradient-to-r from-red-500 to-rose-600'
                } text-white`}>
                  <div className="flex items-center gap-3">
                    <div className="p-2 bg-white/20 rounded-lg">
                      <Gauge className="w-6 h-6" />
                    </div>
                    <div>
                      <p className="text-sm text-white/80">AI Verification Score</p>
                      <p className="text-2xl font-bold">{ticket.metadata.verification_score.toFixed(1)}%</p>
                    </div>
                  </div>
                  {ticket.metadata.threat_level && (
                    <div className="mt-2 flex items-center gap-2">
                      <Zap className="w-4 h-4" />
                      <span className="text-sm">Threat Level: <strong className="uppercase">{ticket.metadata.threat_level}</strong></span>
                    </div>
                  )}
                </div>
              )}

              {/* Hazard Info */}
              <div className="bg-white rounded-xl p-4 border border-gray-200">
                <h3 className="text-sm font-semibold text-gray-700 mb-3 flex items-center gap-2">
                  <AlertTriangle className="w-4 h-4 text-orange-500" />
                  Hazard Information
                </h3>
                <div className="space-y-2 text-sm">
                  <div className="flex justify-between">
                    <span className="text-gray-500">Type</span>
                    <span className="font-medium capitalize">{ticket.hazard_type?.replace('_', ' ')}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-500">Report ID</span>
                    <a href={`/authority/verification/${ticket.report_id}`} className="font-mono text-[#0d4a6f] hover:underline flex items-center gap-1">
                      {ticket.report_id}
                      <ExternalLink className="w-3 h-3" />
                    </a>
                  </div>
                </div>
              </div>

              {/* Location */}
              <div className="bg-white rounded-xl p-4 border border-gray-200">
                <h3 className="text-sm font-semibold text-gray-700 mb-3 flex items-center gap-2">
                  <MapPin className="w-4 h-4 text-[#0d4a6f]" />
                  Location
                </h3>
                <p className="text-sm text-gray-800">{ticket.location_address}</p>
                {ticket.location_latitude && ticket.location_longitude && (
                  <a
                    href={`https://www.google.com/maps?q=${ticket.location_latitude},${ticket.location_longitude}`}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-xs text-[#0d4a6f] hover:underline mt-2 flex items-center gap-1"
                  >
                    <ExternalLink className="w-3 h-3" />
                    View on Map
                  </a>
                )}
              </div>

              {/* People & Analyst Assignment */}
              <div className="bg-white rounded-xl p-4 border border-gray-200">
                <div className="flex items-center justify-between mb-3">
                  <h3 className="text-sm font-semibold text-gray-700 flex items-center gap-2">
                    <Users className="w-4 h-4 text-gray-500" />
                    People Involved
                  </h3>
                  <button
                    onClick={() => setShowAnalystPanel(!showAnalystPanel)}
                    className="flex items-center gap-1 px-2 py-1 text-xs font-medium text-[#0d4a6f] hover:bg-[#e8f4fc] rounded-lg transition-colors"
                  >
                    <UserPlus className="w-3.5 h-3.5" />
                    Add Analyst
                  </button>
                </div>

                {/* Existing participants */}
                <div className="space-y-3">
                  <div className="flex items-center gap-3">
                    <div className="w-8 h-8 bg-blue-100 rounded-full flex items-center justify-center">
                      <User className="w-4 h-4 text-blue-600" />
                    </div>
                    <div>
                      <p className="text-sm font-medium">{ticket.reporter_name}</p>
                      <p className="text-xs text-gray-500">Reporter</p>
                    </div>
                  </div>
                  {ticket.assigned_analyst_name && (
                    <div className="flex items-center gap-3">
                      <div className="w-8 h-8 bg-green-100 rounded-full flex items-center justify-center">
                        <Eye className="w-4 h-4 text-green-600" />
                      </div>
                      <div>
                        <p className="text-sm font-medium">{ticket.assigned_analyst_name}</p>
                        <p className="text-xs text-gray-500">Analyst</p>
                      </div>
                    </div>
                  )}
                  {ticket.authority_name && (
                    <div className="flex items-center gap-3">
                      <div className="w-8 h-8 bg-[#e8f4fc] rounded-full flex items-center justify-center">
                        <Shield className="w-4 h-4 text-[#0d4a6f]" />
                      </div>
                      <div>
                        <p className="text-sm font-medium">{ticket.authority_name}</p>
                        <p className="text-xs text-gray-500">Authority</p>
                      </div>
                    </div>
                  )}

                  {/* Additional participants */}
                  {ticket.additional_participants?.map((participant, idx) => (
                    <div key={idx} className="flex items-center justify-between group">
                      <div className="flex items-center gap-3">
                        <div className="w-8 h-8 bg-orange-100 rounded-full flex items-center justify-center">
                          <Building2 className="w-4 h-4 text-orange-600" />
                        </div>
                        <div>
                          <p className="text-sm font-medium">{participant.user_name}</p>
                          <p className="text-xs text-gray-500 capitalize">{participant.user_role}</p>
                        </div>
                      </div>
                      <button
                        onClick={() => removeParticipant(participant.user_id)}
                        className="p-1.5 text-gray-400 hover:text-red-600 hover:bg-red-50 rounded-lg opacity-0 group-hover:opacity-100 transition-all"
                        title="Remove participant"
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  ))}
                </div>

                {/* Analyst Assignment Panel */}
                {showAnalystPanel && (
                  <div className="mt-4 pt-4 border-t border-gray-200">
                    <div className="flex items-center gap-2 mb-3">
                      <Search className="w-4 h-4 text-gray-400" />
                      <input
                        type="text"
                        placeholder="Search analysts..."
                        value={analystSearch}
                        onChange={(e) => setAnalystSearch(e.target.value)}
                        className="flex-1 text-sm px-2 py-1.5 border border-gray-200 rounded-lg focus:ring-2 focus:ring-[#1a6b9a] focus:border-transparent"
                      />
                    </div>

                    {loadingAnalysts || !participantsLoaded ? (
                      <div className="text-center py-4">
                        <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-[#0d4a6f] mx-auto"></div>
                        <p className="text-xs text-gray-500 mt-2">
                          {loadingAnalysts ? 'Loading analysts...' : 'Loading participants...'}
                        </p>
                      </div>
                    ) : analysts.length === 0 ? (
                      <div className="text-center py-4">
                        <p className="text-sm text-gray-500">No analysts found</p>
                      </div>
                    ) : (
                      <div className="space-y-2 max-h-48 overflow-y-auto">
                        {analysts.map((analyst) => {
                          const alreadyAdded = isAlreadyParticipant(analyst.user_id);
                          return (
                            <div
                              key={analyst.user_id}
                              className={`flex items-center justify-between p-2 rounded-lg transition-colors ${alreadyAdded ? 'bg-gray-50 opacity-60' : 'hover:bg-gray-50'}`}
                            >
                              <div className="flex items-center gap-2">
                                <div className={`w-7 h-7 rounded-full flex items-center justify-center ${alreadyAdded ? 'bg-green-100' : 'bg-[#e8f4fc]'}`}>
                                  <Eye className={`w-3.5 h-3.5 ${alreadyAdded ? 'text-green-600' : 'text-[#0d4a6f]'}`} />
                                </div>
                                <div>
                                  <p className="text-sm font-medium">{analyst.name}</p>
                                  <p className="text-xs text-gray-500">{analyst.email}</p>
                                </div>
                              </div>
                              {alreadyAdded ? (
                                <span className="px-2 py-1 text-xs font-medium text-green-700 bg-green-100 rounded-lg">
                                  Added
                                </span>
                              ) : (
                                <button
                                  onClick={() => addAnalyst(analyst)}
                                  disabled={addingAnalyst}
                                  className="px-2.5 py-1 text-xs font-medium text-white bg-[#0d4a6f] rounded-lg hover:bg-[#083a57] disabled:opacity-50 transition-colors"
                                >
                                  {addingAnalyst ? '...' : 'Add'}
                                </button>
                              )}
                            </div>
                          );
                        })}
                      </div>
                    )}

                    <button
                      onClick={() => setShowAnalystPanel(false)}
                      className="mt-3 w-full py-2 text-sm text-gray-600 hover:bg-gray-100 rounded-lg transition-colors"
                    >
                      Cancel
                    </button>
                  </div>
                )}
              </div>

              {/* SLA */}
              <div className={`rounded-xl p-4 border ${isOverdue ? 'bg-red-50 border-red-200' : 'bg-white border-gray-200'}`}>
                <h3 className="text-sm font-semibold text-gray-700 mb-3 flex items-center gap-2">
                  <Timer className="w-4 h-4 text-gray-500" />
                  SLA Deadlines
                </h3>
                <div className="space-y-2 text-sm">
                  <div className="flex justify-between">
                    <span className="text-gray-500">Response Due</span>
                    <span className={`font-medium ${ticket.responded_at ? 'text-green-600' : 'text-gray-800'}`}>
                      {ticket.responded_at ? '✓ Responded' : formatDate(ticket.response_due)}
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-500">Resolution Due</span>
                    <span className={`font-medium ${isOverdue ? 'text-red-600' : 'text-gray-800'}`}>
                      {formatDate(ticket.resolution_due)}
                    </span>
                  </div>
                </div>
              </div>

              {/* Timeline */}
              <div className="bg-white rounded-xl p-4 border border-gray-200">
                <h3 className="text-sm font-semibold text-gray-700 mb-3 flex items-center gap-2">
                  <Calendar className="w-4 h-4 text-gray-500" />
                  Timeline
                </h3>
                <div className="space-y-2 text-sm">
                  <div className="flex justify-between">
                    <span className="text-gray-500">Created</span>
                    <span className="font-medium">{formatDate(ticket.created_at)}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-500">Last Updated</span>
                    <span className="font-medium">{formatDate(ticket.updated_at)}</span>
                  </div>
                  {ticket.escalated_at && (
                    <div className="flex justify-between">
                      <span className="text-gray-500">Escalated</span>
                      <span className="font-medium text-orange-600">{formatDate(ticket.escalated_at)}</span>
                    </div>
                  )}
                  {ticket.resolved_at && (
                    <div className="flex justify-between">
                      <span className="text-gray-500">Resolved</span>
                      <span className="font-medium text-green-600">{formatDate(ticket.resolved_at)}</span>
                    </div>
                  )}
                  {ticket.closed_at && (
                    <div className="flex justify-between">
                      <span className="text-gray-500">Closed</span>
                      <span className="font-medium text-gray-600">{formatDate(ticket.closed_at)}</span>
                    </div>
                  )}
                </div>
              </div>
            </div>
          </div>

          {/* Right Panel - Messages */}
          <div className="flex-1 flex flex-col bg-white">
            {/* Messages Header */}
            <div className="p-4 border-b border-gray-200 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <MessageSquare className="w-5 h-5 text-gray-600" />
                <span className="font-semibold text-gray-900">Messages</span>
                <span className="px-2 py-0.5 bg-gray-100 text-gray-600 text-xs rounded-full">
                  {messages.length}
                </span>
              </div>
              <button
                onClick={fetchTicketDetails}
                className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
              >
                <RefreshCw className="w-4 h-4 text-gray-500" />
              </button>
            </div>

            {/* Messages List */}
            <div className="flex-1 overflow-y-auto p-4 space-y-4">
              {messages.length === 0 ? (
                <div className="text-center py-12">
                  <MessageSquare className="w-12 h-12 text-gray-300 mx-auto mb-3" />
                  <p className="text-gray-500">No messages yet</p>
                  <p className="text-sm text-gray-400">Start the conversation below</p>
                </div>
              ) : (
                messages.map((msg, idx) => {
                  const isSystem = msg.sender_role === 'system';
                  const isOwn = msg.sender_id === user?.user_id;

                  return (
                    <div key={msg.message_id || idx} className={`${isOwn ? 'ml-12' : 'mr-12'}`}>
                      {isSystem ? (
                        <div className="bg-gray-50 border border-gray-200 rounded-xl p-4">
                          <div className="flex items-center gap-2 mb-2">
                            <Activity className="w-4 h-4 text-gray-500" />
                            <span className="text-sm font-medium text-gray-700">{msg.sender_name}</span>
                            <span className="text-xs text-gray-400">{formatMessageTime(msg.created_at)}</span>
                          </div>
                          <pre className="text-sm text-gray-600 whitespace-pre-wrap font-sans">{msg.content}</pre>
                        </div>
                      ) : (
                        <div className={`rounded-xl p-4 ${
                          isOwn ? 'bg-[#0d4a6f] text-white' :
                          msg.is_internal ? 'bg-yellow-50 border-2 border-yellow-200' : 'bg-gray-100'
                        }`}>
                          <div className="flex items-center gap-2 mb-2">
                            <span className={`text-sm font-medium ${isOwn ? 'text-white' : 'text-gray-700'}`}>
                              {msg.sender_name}
                            </span>
                            {msg.is_internal && (
                              <span className="px-1.5 py-0.5 bg-yellow-200 text-yellow-800 text-xs rounded flex items-center gap-1">
                                <Lock className="w-3 h-3" />
                                Internal
                              </span>
                            )}
                            <span className={`text-xs ${isOwn ? 'text-[#9ecbec]' : 'text-gray-400'}`}>
                              {formatMessageTime(msg.created_at)}
                            </span>
                          </div>
                          <p className={`text-sm ${isOwn ? 'text-white' : 'text-gray-800'}`}>{msg.content}</p>
                        </div>
                      )}
                    </div>
                  );
                })
              )}
              <div ref={messagesEndRef} />
            </div>

            {/* Message Input */}
            {!['resolved', 'closed'].includes(ticket.status) && (
              <div className="p-4 border-t border-gray-200">
                <div className="flex items-center gap-2 mb-2">
                  <button
                    onClick={() => setIsInternal(!isInternal)}
                    className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${
                      isInternal ? 'bg-yellow-100 text-yellow-700' : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                    }`}
                  >
                    {isInternal ? <Lock className="w-4 h-4" /> : <Unlock className="w-4 h-4" />}
                    {isInternal ? 'Internal Note' : 'Public Message'}
                  </button>
                  {isInternal && (
                    <span className="text-xs text-yellow-600">Only staff can see internal notes</span>
                  )}
                </div>
                <div className="flex gap-2">
                  <input
                    type="text"
                    value={newMessage}
                    onChange={(e) => setNewMessage(e.target.value)}
                    onKeyDown={(e) => e.key === 'Enter' && !e.shiftKey && sendMessage()}
                    placeholder={isInternal ? "Add internal note..." : "Type your message..."}
                    className={`flex-1 px-4 py-3 border rounded-xl focus:ring-2 focus:ring-[#1a6b9a] focus:border-transparent ${
                      isInternal ? 'border-yellow-300 bg-yellow-50' : 'border-gray-200'
                    }`}
                  />
                  <button
                    onClick={sendMessage}
                    disabled={sending || !newMessage.trim()}
                    className="px-6 py-3 bg-[#0d4a6f] text-white rounded-xl hover:bg-[#083a57] transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
                  >
                    <Send className="w-5 h-5" />
                    Send
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Escalate Modal */}
      {showEscalateModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl p-6 w-full max-w-md mx-4 shadow-xl">
            <div className="flex items-center gap-3 mb-4">
              <div className="p-2 bg-orange-100 rounded-lg">
                <ArrowUpCircle className="w-6 h-6 text-orange-600" />
              </div>
              <div>
                <h3 className="text-lg font-bold text-gray-900">Escalate Ticket</h3>
                <p className="text-sm text-gray-500">This will mark the ticket as urgent</p>
              </div>
            </div>
            <textarea
              value={escalationReason}
              onChange={(e) => setEscalationReason(e.target.value)}
              placeholder="Reason for escalation..."
              className="w-full px-4 py-3 border border-gray-200 rounded-xl focus:ring-2 focus:ring-[#1a6b9a] focus:border-transparent resize-none"
              rows={4}
            />
            <div className="flex gap-3 mt-4">
              <button
                onClick={() => setShowEscalateModal(false)}
                className="flex-1 py-2.5 px-4 border border-gray-200 text-gray-700 rounded-xl hover:bg-gray-50 transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={escalateTicket}
                disabled={escalating || !escalationReason.trim()}
                className="flex-1 py-2.5 px-4 bg-orange-600 text-white rounded-xl hover:bg-orange-700 transition-colors disabled:opacity-50"
              >
                {escalating ? 'Escalating...' : 'Escalate'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Close Modal */}
      {showCloseModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl p-6 w-full max-w-md mx-4 shadow-xl">
            <div className="flex items-center gap-3 mb-4">
              <div className="p-2 bg-gray-100 rounded-lg">
                <XCircle className="w-6 h-6 text-gray-600" />
              </div>
              <div>
                <h3 className="text-lg font-bold text-gray-900">Close Ticket</h3>
                <p className="text-sm text-gray-500">This action cannot be undone</p>
              </div>
            </div>
            <textarea
              value={closeReason}
              onChange={(e) => setCloseReason(e.target.value)}
              placeholder="Resolution notes (optional)..."
              className="w-full px-4 py-3 border border-gray-200 rounded-xl focus:ring-2 focus:ring-[#1a6b9a] focus:border-transparent resize-none"
              rows={4}
            />
            <div className="flex gap-3 mt-4">
              <button
                onClick={() => setShowCloseModal(false)}
                className="flex-1 py-2.5 px-4 border border-gray-200 text-gray-700 rounded-xl hover:bg-gray-50 transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={closeTicket}
                disabled={closing}
                className="flex-1 py-2.5 px-4 bg-gray-600 text-white rounded-xl hover:bg-gray-700 transition-colors disabled:opacity-50"
              >
                {closing ? 'Closing...' : 'Close Ticket'}
              </button>
            </div>
          </div>
        </div>
      )}
    </DashboardLayout>
  );
}
