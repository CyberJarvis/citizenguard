'use client';

import { useEffect, useState, useRef } from 'react';
import { useRouter, useParams } from 'next/navigation';
import DashboardLayout from '@/components/DashboardLayout';
import PageHeader from '@/components/PageHeader';
import useAuthStore from '@/context/AuthContext';
import api from '@/lib/api';
import {
  ThreadTabs,
  ThreadSelector,
  getAllowedThreads,
  MessageBubble,
  SLAIndicator
} from '@/components/tickets';
import {
  Ticket,
  ChevronLeft,
  Clock,
  AlertTriangle,
  CheckCircle,
  XCircle,
  MapPin,
  Calendar,
  User,
  MessageSquare,
  Send,
  Gauge,
  Zap,
  Timer,
  FileText,
  Activity,
  ExternalLink,
  Shield,
  Thermometer,
  Wind,
  Waves,
  Eye,
  Lock,
  Unlock,
  RefreshCw,
  Play,
  CheckCheck,
  X as XIcon,
  UserPlus,
  Users,
  Building2,
  Search,
  ChevronDown,
  ChevronUp,
  Trash2,
  Forward,
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
  escalated: { bg: 'bg-red-100', text: 'text-red-700', label: 'Escalated' },
  resolved: { bg: 'bg-[#c5e1f5]', text: 'text-[#0d4a6f]', label: 'Resolved' },
  closed: { bg: 'bg-gray-100', text: 'text-gray-600', label: 'Closed' }
};

export default function TicketDetailPage() {
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

  // V2 Thread-based messaging
  const [activeThread, setActiveThread] = useState('all');
  const [selectedSendThread, setSelectedSendThread] = useState('all');
  const [threadCounts, setThreadCounts] = useState({});
  const [useV2Messages, setUseV2Messages] = useState(true);

  // Escalation states
  const [showEscalateModal, setShowEscalateModal] = useState(false);
  const [escalationTargets, setEscalationTargets] = useState([]);
  const [escalationReason, setEscalationReason] = useState('');
  const [escalating, setEscalating] = useState(false);

  // Authority assignment states
  const [showAuthorityPanel, setShowAuthorityPanel] = useState(false);
  const [authorities, setAuthorities] = useState([]);
  const [loadingAuthorities, setLoadingAuthorities] = useState(false);
  const [authoritySearch, setAuthoritySearch] = useState('');
  const [addingAuthority, setAddingAuthority] = useState(false);
  const [participants, setParticipants] = useState({});
  const [participantsLoaded, setParticipantsLoaded] = useState(false);

  // Assign to authority (not just add as participant)
  const [showAssignModal, setShowAssignModal] = useState(false);
  const [assigningToAuthority, setAssigningToAuthority] = useState(false);
  const [assignmentMessage, setAssignmentMessage] = useState('');

  useEffect(() => {
    if (!authLoading && user) {
      if (!['analyst', 'authority', 'authority_admin', 'admin'].includes(user.role)) {
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

      // Fetch ticket details
      const ticketRes = await api.get(`/tickets/${params.id}`);
      const ticketData = ticketRes.data.ticket || ticketRes.data;
      setTicket(ticketData);

      // Try V2 messages API first
      if (useV2Messages) {
        try {
          const threadParam = activeThread !== 'all' ? `?thread=${activeThread}` : '';
          const messagesRes = await api.get(`/tickets/${params.id}/messages/v2${threadParam}`);
          setMessages(messagesRes.data.messages || []);
          setThreadCounts(messagesRes.data.thread_counts || {});
        } catch (e) {
          // Fallback to V1
          console.log('V2 messages not available, falling back to V1');
          setUseV2Messages(false);
          const messagesRes = await api.get(`/tickets/${params.id}/messages`);
          setMessages(messagesRes.data.messages || []);
        }
      } else {
        const messagesRes = await api.get(`/tickets/${params.id}/messages`);
        setMessages(messagesRes.data.messages || []);
      }
    } catch (error) {
      console.error('Error fetching ticket:', error);
      alert('Failed to load ticket details');
      router.push('/analyst/tickets');
    } finally {
      setLoading(false);
    }
  };

  // Refetch messages when thread changes
  useEffect(() => {
    if (ticket && useV2Messages) {
      fetchMessages();
    }
  }, [activeThread]);

  const fetchMessages = async () => {
    try {
      const threadParam = activeThread !== 'all' ? `?thread=${activeThread}` : '';
      const messagesRes = await api.get(`/tickets/${params.id}/messages/v2${threadParam}`);
      setMessages(messagesRes.data.messages || []);
      setThreadCounts(messagesRes.data.thread_counts || {});
    } catch (e) {
      console.log('Error fetching messages:', e);
    }
  };

  const sendMessage = async () => {
    if (!newMessage.trim()) return;

    try {
      setSending(true);

      if (useV2Messages) {
        // Use V2 threaded messages endpoint
        await api.post(`/tickets/${params.id}/messages/v2`, {
          content: newMessage,
          thread: selectedSendThread,
          attachments: null
        });
      } else {
        // Fallback to V1
        await api.post(`/tickets/${params.id}/messages`, {
          content: newMessage,
          is_internal: isInternal
        });
      }

      setNewMessage('');
      fetchMessages();
    } catch (error) {
      console.error('Error sending message:', error);
      alert('Failed to send message');
    } finally {
      setSending(false);
    }
  };

  // Fetch escalation targets
  const fetchEscalationTargets = async () => {
    try {
      const response = await api.get(`/tickets/${params.id}/escalation-targets`);
      setEscalationTargets(response.data.targets || []);
    } catch (e) {
      console.error('Error fetching escalation targets:', e);
      setEscalationTargets([]);
    }
  };

  // Escalate ticket to target
  const escalateTicket = async (targetUserId) => {
    if (!escalationReason.trim() || escalationReason.length < 10) {
      alert('Please provide a reason for escalation (at least 10 characters)');
      return;
    }

    try {
      setEscalating(true);
      await api.post(`/tickets/${params.id}/escalate-v2`, {
        target_user_id: targetUserId,
        reason: escalationReason
      });
      alert('Ticket escalated successfully');
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

  // Fetch authorities for assignment
  const fetchAuthorities = async (search = '') => {
    try {
      setLoadingAuthorities(true);
      // Use the dedicated endpoint for analysts to lookup authorities
      const response = await api.get('/tickets/lookup/authorities', {
        params: {
          search: search || undefined,
          limit: 20
        }
      });
      setAuthorities(response.data.authorities || []);
    } catch (error) {
      console.error('Error fetching authorities:', error);
      setAuthorities([]);
    } finally {
      setLoadingAuthorities(false);
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
      setParticipantsLoaded(true); // Mark as loaded even on error
    }
  };

  // Add authority to ticket
  const addAuthority = async (authorityUser) => {
    // Pre-validation check (defense in depth - backend also validates)
    const isAlreadyAdded = isAlreadyParticipant(authorityUser.user_id);
    console.log('[addAuthority] Starting add for:', authorityUser.user_id, authorityUser.name);
    console.log('[addAuthority] isAlreadyParticipant check result:', isAlreadyAdded);

    if (isAlreadyAdded) {
      alert(`${authorityUser.name} is already a participant in this ticket`);
      return;
    }

    try {
      setAddingAuthority(true);

      // Build clean notes string (avoid special characters that might cause URL issues)
      const orgName = authorityUser.authority_organization || 'Authority';
      const notes = `Added ${orgName} - ${authorityUser.name}`.replace(/[&?#]/g, '');

      console.log('[addAuthority] Making API call to:', `/tickets/${params.id}/participants`);
      console.log('[addAuthority] Params:', { user_id: authorityUser.user_id, notes, can_message: true });

      const response = await api.post(`/tickets/${params.id}/participants`, null, {
        params: {
          user_id: authorityUser.user_id,
          notes: notes,
          can_message: true
        }
      });

      console.log('[addAuthority] Success response:', response.data);
      alert(`${authorityUser.name} has been added to this ticket`);
      fetchTicketDetails();
      fetchParticipants();
      setShowAuthorityPanel(false);
    } catch (error) {
      // Comprehensive error logging
      console.error('[addAuthority] Error object:', error);
      console.error('[addAuthority] Error message:', error.message);
      console.error('[addAuthority] Error response:', error.response);
      console.error('[addAuthority] Error response status:', error.response?.status);
      console.error('[addAuthority] Error response data:', error.response?.data);
      console.error('[addAuthority] Error response data detail:', error.response?.data?.detail);

      // Extract error message from various possible response formats
      let errorMsg = 'Failed to add authority';
      const detail = error.response?.data?.detail;

      // Handle FastAPI error formats
      if (detail) {
        if (typeof detail === 'string') {
          // Standard HTTPException: {"detail": "error message"}
          errorMsg = detail;
        } else if (Array.isArray(detail) && detail.length > 0) {
          // Validation error (422): {"detail": [{"loc": [...], "msg": "...", "type": "..."}]}
          errorMsg = detail.map(d => d.msg || d.message || JSON.stringify(d)).join(', ');
        } else if (typeof detail === 'object') {
          // Object format: try to extract message
          errorMsg = detail.msg || detail.message || JSON.stringify(detail);
        }
      } else if (error.response?.data?.message) {
        errorMsg = error.response.data.message;
      } else if (typeof error.response?.data === 'string' && error.response.data.trim()) {
        errorMsg = error.response.data;
      } else if (error.message) {
        errorMsg = error.message;
      }

      console.log('[addAuthority] Final error message:', errorMsg);

      // Ensure errorMsg is a string before calling string methods
      const errorString = String(errorMsg);
      const lowerMsg = errorString.toLowerCase();

      // Make the error message more user-friendly based on content or status
      if (lowerMsg.includes('already a participant') || lowerMsg.includes('already a main participant')) {
        alert(`${authorityUser.name} is already a participant in this ticket`);
        fetchParticipants(); // Refresh to update UI
      } else if (error.response?.status === 400) {
        // Bad request - show the actual error from backend
        alert(errorString);
      } else if (error.response?.status === 403) {
        alert('You do not have permission to add participants to this ticket');
      } else if (error.response?.status === 404) {
        alert('Ticket or user not found');
      } else if (error.response?.status === 401) {
        alert('Session expired. Please log in again.');
      } else if (error.response?.status === 422) {
        // Validation error - show the extracted message
        alert(`Validation error: ${errorString}`);
      } else if (!error.response) {
        alert('Network error. Please check your connection and try again.');
      } else {
        alert(errorString);
      }
    } finally {
      setAddingAuthority(false);
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

  // Assign ticket to a specific authority (makes it visible in their tickets page)
  const assignToAuthority = async (authorityUser) => {
    try {
      setAssigningToAuthority(true);
      await api.post(`/tickets/${params.id}/assign-authority`, {
        authority_id: authorityUser.user_id,
        message: assignmentMessage || `Ticket assigned to ${authorityUser.name} for action`
      });
      alert(`Ticket has been assigned to ${authorityUser.name}. They will now see it in their tickets page.`);
      setShowAssignModal(false);
      setAssignmentMessage('');
      fetchTicketDetails();
    } catch (error) {
      console.error('Error assigning to authority:', error);
      const detail = error.response?.data?.detail;
      let errorMsg = 'Failed to assign ticket to authority';
      if (detail) {
        errorMsg = typeof detail === 'string' ? detail : JSON.stringify(detail);
      }
      alert(errorMsg);
    } finally {
      setAssigningToAuthority(false);
    }
  };

  // Check if authority is already a participant
  const isAlreadyParticipant = (authorityUserId) => {
    if (!ticket || !authorityUserId) {
      console.log('[isAlreadyParticipant] No ticket data or user ID:', { hasTicket: !!ticket, authorityUserId });
      return false;
    }

    // Normalize the user ID for comparison (handle potential type mismatches)
    const normalizedUserId = String(authorityUserId).trim();

    // Check main participants from ticket data
    if (ticket.reporter_id && String(ticket.reporter_id).trim() === normalizedUserId) {
      console.log('[isAlreadyParticipant] Match: reporter_id');
      return true;
    }
    if (ticket.assigned_analyst_id && String(ticket.assigned_analyst_id).trim() === normalizedUserId) {
      console.log('[isAlreadyParticipant] Match: assigned_analyst_id');
      return true;
    }
    if (ticket.authority_id && String(ticket.authority_id).trim() === normalizedUserId) {
      console.log('[isAlreadyParticipant] Match: authority_id');
      return true;
    }

    // Check main participants from participants API response (if loaded)
    if (participants && typeof participants === 'object' && !Array.isArray(participants)) {
      if (participants.reporter?.user_id && String(participants.reporter.user_id).trim() === normalizedUserId) {
        console.log('[isAlreadyParticipant] Match: participants.reporter');
        return true;
      }
      if (participants.assigned_analyst?.user_id && String(participants.assigned_analyst.user_id).trim() === normalizedUserId) {
        console.log('[isAlreadyParticipant] Match: participants.assigned_analyst');
        return true;
      }
      if (participants.authority?.user_id && String(participants.authority.user_id).trim() === normalizedUserId) {
        console.log('[isAlreadyParticipant] Match: participants.authority');
        return true;
      }
    }

    // Check additional participants (from API response or ticket data)
    const additionalParticipants = (participants && !Array.isArray(participants) ? participants.additional_participants : null)
      || ticket.additional_participants
      || [];

    for (const p of additionalParticipants) {
      if (p.user_id && String(p.user_id).trim() === normalizedUserId && p.is_active !== false) {
        console.log('[isAlreadyParticipant] Match: additional_participant', p);
        return true;
      }
    }

    console.log('[isAlreadyParticipant] No match found for:', normalizedUserId);
    return false;
  };

  // Load authorities when panel opens
  useEffect(() => {
    if (showAuthorityPanel) {
      fetchAuthorities();
      fetchParticipants();
    }
  }, [showAuthorityPanel]);

  // Debounced search for authorities
  useEffect(() => {
    const timer = setTimeout(() => {
      if (showAuthorityPanel) {
        fetchAuthorities(authoritySearch);
      }
    }, 300);
    return () => clearTimeout(timer);
  }, [authoritySearch]);

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
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-600"></div>
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
              onClick={() => router.push('/analyst/tickets')}
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
              </div>
              <h1 className="text-lg font-semibold text-gray-900 truncate">{ticket.title}</h1>
            </div>

            {/* Status Actions */}
            <div className="flex items-center gap-2">
              <span className={`px-3 py-1.5 rounded-full text-sm font-semibold ${priority.bg} ${priority.text}`}>
                {priority.label}
              </span>
              <span className={`px-3 py-1.5 rounded-full text-sm font-semibold ${status.bg} ${status.text}`}>
                {status.label}
              </span>

              {/* Quick Actions */}
              {ticket.status === 'open' && (
                <button
                  onClick={() => updateStatus('in_progress')}
                  disabled={updatingStatus}
                  className="flex items-center gap-1 px-3 py-1.5 bg-purple-600 text-white rounded-lg text-sm font-medium hover:bg-purple-700 transition-colors disabled:opacity-50"
                >
                  <Play className="w-4 h-4" />
                  Start
                </button>
              )}
              {ticket.status === 'in_progress' && (
                <button
                  onClick={() => updateStatus('resolved')}
                  disabled={updatingStatus}
                  className="flex items-center gap-1 px-3 py-1.5 bg-[#0d4a6f] text-white rounded-lg text-sm font-medium hover:bg-[#083a57] transition-colors disabled:opacity-50"
                >
                  <CheckCheck className="w-4 h-4" />
                  Resolve
                </button>
              )}
              {/* Assign to Authority button - visible for analysts on non-closed tickets */}
              {!['resolved', 'closed'].includes(ticket.status) && user?.role === 'analyst' && (
                <button
                  onClick={() => {
                    setShowAssignModal(true);
                    fetchAuthorities();
                  }}
                  className="flex items-center gap-1 px-3 py-1.5 bg-orange-600 text-white rounded-lg text-sm font-medium hover:bg-orange-700 transition-colors"
                >
                  <Forward className="w-4 h-4" />
                  Assign
                </button>
              )}
              {/* Escalate button - for in_progress tickets */}
              {['in_progress', 'assigned'].includes(ticket.status) && (
                <button
                  onClick={() => {
                    setShowEscalateModal(true);
                    fetchEscalationTargets();
                  }}
                  className="flex items-center gap-1 px-3 py-1.5 bg-red-600 text-white rounded-lg text-sm font-medium hover:bg-red-700 transition-colors"
                >
                  <ArrowUpCircle className="w-4 h-4" />
                  Escalate
                </button>
              )}
              {/* Show assigned authority if any */}
              {ticket.assigned_authority_name && (
                <span className="px-3 py-1.5 bg-green-100 text-green-700 rounded-lg text-sm font-medium flex items-center gap-1">
                  <Shield className="w-4 h-4" />
                  Assigned: {ticket.assigned_authority_name}
                </span>
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
                    <a href={`/analyst/reports`} className="font-mono text-indigo-600 hover:underline flex items-center gap-1">
                      {ticket.report_id}
                      <ExternalLink className="w-3 h-3" />
                    </a>
                  </div>
                </div>
              </div>

              {/* Location */}
              <div className="bg-white rounded-xl p-4 border border-gray-200">
                <h3 className="text-sm font-semibold text-gray-700 mb-3 flex items-center gap-2">
                  <MapPin className="w-4 h-4 text-blue-500" />
                  Location
                </h3>
                <p className="text-sm text-gray-800">{ticket.location_address}</p>
                {ticket.location_latitude && ticket.location_longitude && (
                  <a
                    href={`https://www.google.com/maps?q=${ticket.location_latitude},${ticket.location_longitude}`}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-xs text-indigo-600 hover:underline mt-2 flex items-center gap-1"
                  >
                    <ExternalLink className="w-3 h-3" />
                    View on Map
                  </a>
                )}
              </div>

              {/* People & Authority Assignment */}
              <div className="bg-white rounded-xl p-4 border border-gray-200">
                <div className="flex items-center justify-between mb-3">
                  <h3 className="text-sm font-semibold text-gray-700 flex items-center gap-2">
                    <Users className="w-4 h-4 text-gray-500" />
                    People Involved
                  </h3>
                  <button
                    onClick={() => setShowAuthorityPanel(!showAuthorityPanel)}
                    className="flex items-center gap-1 px-2 py-1 text-xs font-medium text-indigo-600 hover:bg-indigo-50 rounded-lg transition-colors"
                  >
                    <UserPlus className="w-3.5 h-3.5" />
                    Add Authority
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
                      <div className="w-8 h-8 bg-purple-100 rounded-full flex items-center justify-center">
                        <Shield className="w-4 h-4 text-purple-600" />
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

                {/* Authority Assignment Panel */}
                {showAuthorityPanel && (
                  <div className="mt-4 pt-4 border-t border-gray-200">
                    <div className="flex items-center gap-2 mb-3">
                      <Search className="w-4 h-4 text-gray-400" />
                      <input
                        type="text"
                        placeholder="Search authorities..."
                        value={authoritySearch}
                        onChange={(e) => setAuthoritySearch(e.target.value)}
                        className="flex-1 text-sm px-2 py-1.5 border border-gray-200 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
                      />
                    </div>

                    {loadingAuthorities || !participantsLoaded ? (
                      <div className="text-center py-4">
                        <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-indigo-600 mx-auto"></div>
                        <p className="text-xs text-gray-500 mt-2">
                          {loadingAuthorities ? 'Loading authorities...' : 'Loading participants...'}
                        </p>
                      </div>
                    ) : authorities.length === 0 ? (
                      <div className="text-center py-4">
                        <p className="text-sm text-gray-500">No authorities found</p>
                      </div>
                    ) : (
                      <div className="space-y-2 max-h-48 overflow-y-auto">
                        {authorities.map((auth) => {
                          const alreadyAdded = isAlreadyParticipant(auth.user_id);
                          return (
                            <div
                              key={auth.user_id}
                              className={`flex items-center justify-between p-2 rounded-lg transition-colors ${alreadyAdded ? 'bg-gray-50 opacity-60' : 'hover:bg-gray-50'}`}
                            >
                              <div className="flex items-center gap-2">
                                <div className={`w-7 h-7 rounded-full flex items-center justify-center ${alreadyAdded ? 'bg-green-100' : 'bg-indigo-100'}`}>
                                  <Building2 className={`w-3.5 h-3.5 ${alreadyAdded ? 'text-green-600' : 'text-indigo-600'}`} />
                                </div>
                                <div>
                                  <p className="text-sm font-medium">{auth.name}</p>
                                  <p className="text-xs text-gray-500">
                                    {auth.authority_organization || auth.authority_designation || 'Authority'}
                                  </p>
                                </div>
                              </div>
                              {alreadyAdded ? (
                                <span className="px-2 py-1 text-xs font-medium text-green-700 bg-green-100 rounded-lg">
                                  Added
                                </span>
                              ) : (
                                <button
                                  onClick={() => addAuthority(auth)}
                                  disabled={addingAuthority}
                                  className="px-2.5 py-1 text-xs font-medium text-white bg-indigo-600 rounded-lg hover:bg-indigo-700 disabled:opacity-50 transition-colors"
                                >
                                  {addingAuthority ? '...' : 'Add'}
                                </button>
                              )}
                            </div>
                          );
                        })}
                      </div>
                    )}

                    <button
                      onClick={() => setShowAuthorityPanel(false)}
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
                  {ticket.resolved_at && (
                    <div className="flex justify-between">
                      <span className="text-gray-500">Resolved</span>
                      <span className="font-medium text-green-600">{formatDate(ticket.resolved_at)}</span>
                    </div>
                  )}
                </div>
              </div>
            </div>
          </div>

          {/* Right Panel - Messages */}
          <div className="flex-1 flex flex-col bg-white">
            {/* Messages Header */}
            <div className="border-b border-gray-200">
              <div className="p-4 flex items-center justify-between">
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

              {/* Thread Tabs - V2 */}
              {useV2Messages && user && (
                <ThreadTabs
                  activeThread={activeThread}
                  onThreadChange={setActiveThread}
                  allowedThreads={getAllowedThreads(user.role)}
                  threadCounts={threadCounts}
                />
              )}
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
                          isOwn ? 'bg-indigo-600 text-white' :
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
                            <span className={`text-xs ${isOwn ? 'text-indigo-200' : 'text-gray-400'}`}>
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
                  {useV2Messages ? (
                    /* V2 Thread Selector */
                    <ThreadSelector
                      selectedThread={selectedSendThread}
                      onThreadChange={setSelectedSendThread}
                      allowedThreads={getAllowedThreads(user?.role)}
                    />
                  ) : (
                    /* V1 Internal toggle */
                    <>
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
                    </>
                  )}
                </div>
                <div className="flex gap-2">
                  <input
                    type="text"
                    value={newMessage}
                    onChange={(e) => setNewMessage(e.target.value)}
                    onKeyDown={(e) => e.key === 'Enter' && !e.shiftKey && sendMessage()}
                    placeholder={
                      useV2Messages
                        ? `Message to ${selectedSendThread === 'all' ? 'all parties' : selectedSendThread === 'ra' ? 'reporter' : selectedSendThread === 'aa' ? 'authority' : 'internal'}...`
                        : isInternal ? "Add internal note..." : "Type your message..."
                    }
                    className={`flex-1 px-4 py-3 border rounded-xl focus:ring-2 focus:ring-indigo-500 focus:border-transparent ${
                      (useV2Messages ? selectedSendThread === 'internal' : isInternal)
                        ? 'border-yellow-300 bg-yellow-50'
                        : 'border-gray-200'
                    }`}
                  />
                  <button
                    onClick={sendMessage}
                    disabled={sending || !newMessage.trim()}
                    className="px-6 py-3 bg-indigo-600 text-white rounded-xl hover:bg-indigo-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
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

      {/* Assign to Authority Modal */}
      {showAssignModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl p-6 w-full max-w-md mx-4 shadow-xl max-h-[80vh] overflow-hidden flex flex-col">
            <div className="flex items-center gap-3 mb-4">
              <div className="p-2 bg-orange-100 rounded-lg">
                <Forward className="w-6 h-6 text-orange-600" />
              </div>
              <div>
                <h3 className="text-lg font-semibold text-gray-900">Assign to Authority</h3>
                <p className="text-sm text-gray-500">Select an authority to handle this ticket</p>
              </div>
            </div>

            {/* Assignment message */}
            <textarea
              value={assignmentMessage}
              onChange={(e) => setAssignmentMessage(e.target.value)}
              placeholder="Add a note for the authority (optional)..."
              className="w-full px-4 py-3 border border-gray-200 rounded-xl focus:ring-2 focus:ring-orange-500 focus:border-transparent resize-none mb-4"
              rows={2}
            />

            {/* Search */}
            <div className="flex items-center gap-2 mb-3">
              <Search className="w-4 h-4 text-gray-400" />
              <input
                type="text"
                placeholder="Search authorities..."
                value={authoritySearch}
                onChange={(e) => setAuthoritySearch(e.target.value)}
                className="flex-1 text-sm px-3 py-2 border border-gray-200 rounded-lg focus:ring-2 focus:ring-orange-500 focus:border-transparent"
              />
            </div>

            {/* Authority List */}
            <div className="flex-1 overflow-y-auto mb-4 border border-gray-200 rounded-lg">
              {loadingAuthorities ? (
                <div className="text-center py-8">
                  <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-orange-600 mx-auto"></div>
                  <p className="text-sm text-gray-500 mt-2">Loading authorities...</p>
                </div>
              ) : authorities.length === 0 ? (
                <div className="text-center py-8">
                  <Building2 className="w-12 h-12 text-gray-300 mx-auto mb-2" />
                  <p className="text-sm text-gray-500">No authorities found</p>
                </div>
              ) : (
                <div className="divide-y divide-gray-100">
                  {authorities.map((auth) => {
                    const isCurrentlyAssigned = ticket.assigned_authority_id === auth.user_id;
                    return (
                      <div
                        key={auth.user_id}
                        className={`flex items-center justify-between p-3 hover:bg-gray-50 transition-colors ${
                          isCurrentlyAssigned ? 'bg-green-50' : ''
                        }`}
                      >
                        <div className="flex items-center gap-3">
                          <div className={`w-10 h-10 rounded-full flex items-center justify-center ${
                            isCurrentlyAssigned ? 'bg-green-100' : 'bg-orange-100'
                          }`}>
                            <Building2 className={`w-5 h-5 ${
                              isCurrentlyAssigned ? 'text-green-600' : 'text-orange-600'
                            }`} />
                          </div>
                          <div>
                            <p className="text-sm font-medium text-gray-900">{auth.name}</p>
                            <p className="text-xs text-gray-500">
                              {auth.authority_organization || auth.authority_designation || 'Authority'}
                            </p>
                          </div>
                        </div>
                        {isCurrentlyAssigned ? (
                          <span className="px-3 py-1.5 text-xs font-medium text-green-700 bg-green-100 rounded-lg">
                            Currently Assigned
                          </span>
                        ) : (
                          <button
                            onClick={() => assignToAuthority(auth)}
                            disabled={assigningToAuthority}
                            className="px-4 py-1.5 text-sm font-medium text-white bg-orange-600 rounded-lg hover:bg-orange-700 disabled:opacity-50 transition-colors"
                          >
                            {assigningToAuthority ? 'Assigning...' : 'Assign'}
                          </button>
                        )}
                      </div>
                    );
                  })}
                </div>
              )}
            </div>

            <button
              onClick={() => {
                setShowAssignModal(false);
                setAssignmentMessage('');
              }}
              className="w-full py-2.5 text-sm text-gray-600 hover:bg-gray-100 rounded-lg transition-colors border border-gray-200"
            >
              Cancel
            </button>
          </div>
        </div>
      )}

      {/* Escalation Modal */}
      {showEscalateModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl p-6 w-full max-w-md mx-4 shadow-xl max-h-[80vh] overflow-hidden flex flex-col">
            <div className="flex items-center gap-3 mb-4">
              <div className="p-2 bg-red-100 rounded-lg">
                <ArrowUpCircle className="w-6 h-6 text-red-600" />
              </div>
              <div>
                <h3 className="text-lg font-semibold text-gray-900">Escalate Ticket</h3>
                <p className="text-sm text-gray-500">Select someone to escalate this ticket to</p>
              </div>
            </div>

            {/* Escalation reason */}
            <textarea
              value={escalationReason}
              onChange={(e) => setEscalationReason(e.target.value)}
              placeholder="Reason for escalation (required, min 10 characters)..."
              className="w-full px-4 py-3 border border-gray-200 rounded-xl focus:ring-2 focus:ring-red-500 focus:border-transparent resize-none mb-4"
              rows={3}
            />

            {/* Escalation targets */}
            <div className="flex-1 overflow-y-auto mb-4 border border-gray-200 rounded-lg">
              {escalationTargets.length === 0 ? (
                <div className="text-center py-8">
                  <ArrowUpCircle className="w-12 h-12 text-gray-300 mx-auto mb-2" />
                  <p className="text-sm text-gray-500">Loading escalation targets...</p>
                </div>
              ) : (
                <div className="divide-y divide-gray-100">
                  {escalationTargets.map((target) => (
                    <div
                      key={target.user_id}
                      className="flex items-center justify-between p-3 hover:bg-gray-50 transition-colors"
                    >
                      <div className="flex items-center gap-3">
                        <div className="w-10 h-10 rounded-full bg-red-100 flex items-center justify-center">
                          <Shield className="w-5 h-5 text-red-600" />
                        </div>
                        <div>
                          <p className="text-sm font-medium text-gray-900">{target.name}</p>
                          <p className="text-xs text-gray-500">
                            {target.authority_organization || target.role || 'Authority'}
                          </p>
                        </div>
                      </div>
                      <button
                        onClick={() => escalateTicket(target.user_id)}
                        disabled={escalating || escalationReason.length < 10}
                        className="px-4 py-1.5 text-sm font-medium text-white bg-red-600 rounded-lg hover:bg-red-700 disabled:opacity-50 transition-colors"
                      >
                        {escalating ? 'Escalating...' : 'Escalate'}
                      </button>
                    </div>
                  ))}
                </div>
              )}
            </div>

            <button
              onClick={() => {
                setShowEscalateModal(false);
                setEscalationReason('');
              }}
              className="w-full py-2.5 text-sm text-gray-600 hover:bg-gray-100 rounded-lg transition-colors border border-gray-200"
            >
              Cancel
            </button>
          </div>
        </div>
      )}
    </DashboardLayout>
  );
}
