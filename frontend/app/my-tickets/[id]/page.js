'use client';

import { useEffect, useState, useRef } from 'react';
import { useRouter, useParams } from 'next/navigation';
import { motion, AnimatePresence } from 'framer-motion';
import ProtectedRoute from '@/components/ProtectedRoute';
import DashboardLayout from '@/components/DashboardLayout';
import useAuthStore from '@/context/AuthContext';
import api from '@/lib/api';
import { formatDateTimeIST, getRelativeTimeIST, formatCompactDateTimeIST } from '@/lib/dateUtils';
import {
  Ticket,
  ChevronLeft,
  ChevronDown,
  ChevronUp,
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
  ExternalLink,
  Shield,
  Eye,
  RefreshCw,
  Star,
  ThumbsUp,
  Info
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
  awaiting_response: { bg: 'bg-yellow-100', text: 'text-yellow-700', label: 'Awaiting Your Response' },
  escalated: { bg: 'bg-red-100', text: 'text-red-700', label: 'Escalated' },
  resolved: { bg: 'bg-[#e8f4fc]', text: 'text-[#083a57]', label: 'Resolved' },
  closed: { bg: 'bg-gray-100', text: 'text-gray-600', label: 'Closed' }
};

function UserTicketDetailContent() {
  const router = useRouter();
  const params = useParams();
  const { user } = useAuthStore();
  const messagesEndRef = useRef(null);

  const [ticket, setTicket] = useState(null);
  const [messages, setMessages] = useState([]);
  const [loading, setLoading] = useState(true);
  const [newMessage, setNewMessage] = useState('');
  const [sending, setSending] = useState(false);
  const [showFeedback, setShowFeedback] = useState(false);
  const [feedbackRating, setFeedbackRating] = useState(0);
  const [feedbackComment, setFeedbackComment] = useState('');
  const [submittingFeedback, setSubmittingFeedback] = useState(false);
  const [showMobileDetails, setShowMobileDetails] = useState(false);

  useEffect(() => {
    if (params.id) {
      fetchTicketDetails();
      // Auto-refresh every 30 seconds for real-time updates
      const interval = setInterval(fetchTicketDetails, 30000);
      return () => clearInterval(interval);
    }
  }, [params.id]);

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
      const ticketData = ticketRes.data.ticket || ticketRes.data;
      setTicket(ticketData);
      setMessages(messagesRes.data.messages || []);

      // Show feedback prompt for resolved tickets without feedback
      if (['resolved', 'closed'].includes(ticketData.status) && !ticketData.feedback_received) {
        setShowFeedback(true);
      }
    } catch (error) {
      console.error('Error fetching ticket:', error);
      if (error.response?.status === 403) {
        alert("You don't have access to this ticket");
        router.push('/my-tickets');
      }
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
        is_internal: false
      });
      setNewMessage('');
      fetchTicketDetails();
    } catch (error) {
      console.error('Error sending message:', error);
      alert('Failed to send message. Please try again.');
    } finally {
      setSending(false);
    }
  };

  const submitFeedback = async () => {
    if (feedbackRating === 0) {
      alert('Please select a rating');
      return;
    }

    try {
      setSubmittingFeedback(true);
      await api.post(`/tickets/${params.id}/feedback`, {
        satisfaction_rating: feedbackRating,
        comments: feedbackComment || undefined,
        response_time_good: feedbackRating >= 4,
        communication_clear: feedbackRating >= 4,
        issue_resolved_effectively: feedbackRating >= 4,
        analyst_helpful: feedbackRating >= 4,
        authority_action_appropriate: feedbackRating >= 4
      });
      alert('Thank you for your feedback!');
      setShowFeedback(false);
      fetchTicketDetails();
    } catch (error) {
      console.error('Error submitting feedback:', error);
      alert(error.response?.data?.detail || 'Failed to submit feedback');
    } finally {
      setSubmittingFeedback(false);
    }
  };

  const formatDate = (dateStr) => {
    if (!dateStr) return 'N/A';
    return formatDateTimeIST(dateStr);
  };

  const formatMessageTime = (dateStr) => {
    if (!dateStr) return '';
    const relativeTime = getRelativeTimeIST(dateStr);
    // For very recent times (within a day), show relative
    // For older times, show compact format
    const date = new Date(dateStr);
    const now = new Date();
    const diff = now - date;
    const hours = Math.floor(diff / (1000 * 60 * 60));

    if (hours < 24) return relativeTime;
    return formatCompactDateTimeIST(dateStr);
  };

  if (loading || !ticket) {
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
          <p className="text-slate-600 font-medium">Loading ticket details...</p>
        </motion.div>
      </div>
    );
  }

  const priority = priorityConfig[ticket.priority] || priorityConfig.medium;
  const status = statusConfig[ticket.status] || statusConfig.open;
  const isOverdue = new Date(ticket.resolution_due) < new Date() && !['resolved', 'closed'].includes(ticket.status);
  const isResolved = ['resolved', 'closed'].includes(ticket.status);

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      className="h-[calc(100vh-64px)] flex flex-col bg-slate-50"
    >
      {/* Header */}
      <div className="p-4 bg-white border-b border-slate-200 flex-shrink-0">
        <div className="flex items-center gap-4 max-w-4xl mx-auto">
          <motion.button
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
            onClick={() => router.push('/my-tickets')}
            className="p-2 hover:bg-slate-100 rounded-xl transition-colors"
          >
            <ChevronLeft className="w-5 h-5 text-slate-600" />
          </motion.button>
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 mb-1">
              <span className="text-sm font-mono text-slate-500">{ticket.ticket_id}</span>
              {isOverdue && (
                <span className="px-2 py-0.5 bg-red-100 text-red-700 text-xs font-medium rounded-full flex items-center gap-1">
                  <Timer className="w-3 h-3" />
                  OVERDUE
                </span>
              )}
            </div>
            <h1 className="text-lg font-semibold text-slate-900 truncate">{ticket.title}</h1>
          </div>

          <div className="flex items-center gap-2">
            <span className={`px-3 py-1.5 rounded-xl text-sm font-semibold ${priority.bg} ${priority.text}`}>
              {priority.label}
            </span>
            <span className={`px-3 py-1.5 rounded-xl text-sm font-semibold ${status.bg} ${status.text}`}>
              {status.label}
            </span>
          </div>
        </div>
      </div>

      {/* Mobile Details Toggle */}
      <div className="lg:hidden bg-white border-b border-slate-200">
        <button
          onClick={() => setShowMobileDetails(!showMobileDetails)}
          className="w-full px-4 py-3 flex items-center justify-between text-sm font-medium text-slate-700"
        >
          <span className="flex items-center gap-2">
            <Info className="w-4 h-4 text-[#0d4a6f]" />
            Ticket Details
          </span>
          {showMobileDetails ? (
            <ChevronUp className="w-5 h-5 text-slate-400" />
          ) : (
            <ChevronDown className="w-5 h-5 text-slate-400" />
          )}
        </button>

        {/* Mobile Details Content */}
        <AnimatePresence>
          {showMobileDetails && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            className="px-4 pb-4 space-y-3 border-t border-slate-100 bg-slate-50"
          >
            {/* Quick Info Row */}
            <div className="grid grid-cols-2 gap-3 pt-3">
              <div className="bg-white rounded-lg p-3">
                <p className="text-xs text-gray-500 mb-1">Hazard Type</p>
                <p className="text-sm font-medium capitalize">{ticket.hazard_type?.replace('_', ' ')}</p>
              </div>
              <div className="bg-white rounded-lg p-3">
                <p className="text-xs text-gray-500 mb-1">Created</p>
                <p className="text-sm font-medium">{formatDate(ticket.created_at)}</p>
              </div>
            </div>

            {/* Location */}
            <div className="bg-white rounded-lg p-3">
              <div className="flex items-center gap-2 mb-1">
                <MapPin className="w-3.5 h-3.5 text-blue-500" />
                <p className="text-xs text-gray-500">Location</p>
              </div>
              <p className="text-sm text-gray-800">{ticket.location_address || 'Location N/A'}</p>
              {ticket.location_latitude && ticket.location_longitude && (
                <a
                  href={`https://www.google.com/maps?q=${ticket.location_latitude},${ticket.location_longitude}`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-xs text-[#0d4a6f] hover:underline mt-1 flex items-center gap-1"
                >
                  <ExternalLink className="w-3 h-3" />
                  View on Map
                </a>
              )}
            </div>

            {/* Handling Team */}
            <div className="bg-white rounded-lg p-3">
              <p className="text-xs text-gray-500 mb-2">Handling Team</p>
              <div className="flex flex-wrap gap-2">
                {ticket.assigned_analyst_name && (
                  <div className="flex items-center gap-1.5 px-2 py-1 bg-green-50 rounded-full">
                    <Eye className="w-3 h-3 text-green-600" />
                    <span className="text-xs font-medium text-green-700">{ticket.assigned_analyst_name}</span>
                  </div>
                )}
                {ticket.authority_name && (
                  <div className="flex items-center gap-1.5 px-2 py-1 bg-purple-50 rounded-full">
                    <Shield className="w-3 h-3 text-purple-600" />
                    <span className="text-xs font-medium text-purple-700">{ticket.authority_name}</span>
                  </div>
                )}
              </div>
            </div>
          </motion.div>
        )}
        </AnimatePresence>
      </div>

      {/* Main Content */}
      <div className="flex-1 flex flex-col lg:flex-row overflow-hidden max-w-6xl mx-auto w-full">
        {/* Left Panel - Ticket Details (hidden on mobile, shown on larger screens) */}
        <div className="hidden lg:block w-80 border-r border-gray-200 bg-white overflow-y-auto">
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
                    <Gauge className="w-5 h-5" />
                  </div>
                  <div>
                    <p className="text-xs text-white/80">Verification Score</p>
                    <p className="text-xl font-bold">{ticket.metadata.verification_score.toFixed(1)}%</p>
                  </div>
                </div>
              </div>
            )}

            {/* Hazard Info */}
            <div className="bg-gray-50 rounded-xl p-4">
              <h3 className="text-sm font-semibold text-gray-700 mb-3 flex items-center gap-2">
                <AlertTriangle className="w-4 h-4 text-orange-500" />
                Hazard Information
              </h3>
              <div className="space-y-2 text-sm">
                <div className="flex justify-between">
                  <span className="text-gray-500">Type</span>
                  <span className="font-medium capitalize">{ticket.hazard_type?.replace('_', ' ')}</span>
                </div>
              </div>
            </div>

            {/* Location */}
            <div className="bg-gray-50 rounded-xl p-4">
              <h3 className="text-sm font-semibold text-gray-700 mb-3 flex items-center gap-2">
                <MapPin className="w-4 h-4 text-blue-500" />
                Location
              </h3>
              <p className="text-sm text-gray-800">{ticket.location_address || 'Location N/A'}</p>
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

            {/* Timeline */}
            <div className="bg-gray-50 rounded-xl p-4">
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

            {/* People */}
            <div className="bg-gray-50 rounded-xl p-4">
              <h3 className="text-sm font-semibold text-gray-700 mb-3 flex items-center gap-2">
                <User className="w-4 h-4 text-gray-500" />
                Handling Team
              </h3>
              <div className="space-y-3">
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
              title="Refresh messages"
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
                <p className="text-sm text-gray-400">The handling team will update you here</p>
              </div>
            ) : (
              messages.filter(msg => !msg.is_internal).map((msg, idx) => {
                const isSystem = msg.sender_role === 'system';
                const isOwn = msg.sender_id === user?.user_id;

                return (
                  <div key={msg.message_id || idx} className={`${isOwn ? 'ml-12' : 'mr-12'}`}>
                    {isSystem ? (
                      <div className="bg-gray-50 border border-gray-200 rounded-xl p-4">
                        <div className="flex items-center gap-2 mb-2">
                          <Zap className="w-4 h-4 text-gray-500" />
                          <span className="text-sm font-medium text-gray-700">{msg.sender_name}</span>
                          <span className="text-xs text-gray-400">{formatMessageTime(msg.created_at)}</span>
                        </div>
                        <pre className="text-sm text-gray-600 whitespace-pre-wrap font-sans">{msg.content}</pre>
                      </div>
                    ) : (
                      <div className={`rounded-xl p-4 ${
                        isOwn ? 'bg-[#0d4a6f] text-white' : 'bg-gray-100'
                      }`}>
                        <div className="flex items-center gap-2 mb-2">
                          <span className={`text-sm font-medium ${isOwn ? 'text-white' : 'text-gray-700'}`}>
                            {isOwn ? 'You' : msg.sender_name}
                          </span>
                          {!isOwn && (
                            <span className="text-xs px-1.5 py-0.5 bg-gray-200 text-gray-600 rounded capitalize">
                              {msg.sender_role}
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

          {/* Feedback Card */}
          {showFeedback && (
            <div className="p-4 border-t border-gray-200 bg-gradient-to-r from-[#e8f4fc] to-green-50">
              <div className="flex items-start gap-3">
                <div className="w-10 h-10 bg-[#e8f4fc] rounded-full flex items-center justify-center flex-shrink-0">
                  <ThumbsUp className="w-5 h-5 text-[#0d4a6f]" />
                </div>
                <div className="flex-1">
                  <h4 className="font-semibold text-gray-900 mb-2">How was your experience?</h4>
                  <p className="text-sm text-gray-600 mb-3">Your feedback helps us improve our service</p>

                  {/* Star Rating */}
                  <div className="flex items-center gap-1 mb-3">
                    {[1, 2, 3, 4, 5].map((star) => (
                      <button
                        key={star}
                        onClick={() => setFeedbackRating(star)}
                        className="p-1"
                      >
                        <Star
                          className={`w-8 h-8 transition-colors ${
                            star <= feedbackRating
                              ? 'text-yellow-400 fill-yellow-400'
                              : 'text-gray-300'
                          }`}
                        />
                      </button>
                    ))}
                  </div>

                  {/* Comment */}
                  <textarea
                    value={feedbackComment}
                    onChange={(e) => setFeedbackComment(e.target.value)}
                    placeholder="Any additional comments? (optional)"
                    className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm resize-none mb-3"
                    rows={2}
                  />

                  {/* Submit Button */}
                  <div className="flex gap-2">
                    <button
                      onClick={submitFeedback}
                      disabled={submittingFeedback || feedbackRating === 0}
                      className="px-4 py-2 bg-[#0d4a6f] text-white rounded-lg text-sm font-medium hover:bg-[#083a57] disabled:opacity-50 transition-colors"
                    >
                      {submittingFeedback ? 'Submitting...' : 'Submit Feedback'}
                    </button>
                    <button
                      onClick={() => setShowFeedback(false)}
                      className="px-4 py-2 text-gray-600 hover:bg-gray-100 rounded-lg text-sm transition-colors"
                    >
                      Later
                    </button>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Message Input */}
          {!isResolved && (
            <div className="p-4 border-t border-gray-200">
              <div className="flex gap-2">
                <input
                  type="text"
                  value={newMessage}
                  onChange={(e) => setNewMessage(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && !e.shiftKey && sendMessage()}
                  placeholder="Type your message..."
                  className="flex-1 px-4 py-3 border border-gray-200 rounded-xl focus:ring-2 focus:ring-[#1a6b9a] focus:border-transparent"
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

          {/* Resolved Message */}
          {isResolved && !showFeedback && (
            <div className="p-4 border-t border-slate-200 bg-[#e8f4fc]">
              <div className="flex items-center gap-3 text-[#083a57]">
                <CheckCircle className="w-5 h-5" />
                <span className="text-sm font-medium">
                  This ticket has been {ticket.status}. Thank you for reporting!
                </span>
              </div>
            </div>
          )}
        </div>
      </div>
    </motion.div>
  );
}

export default function UserTicketDetailPage() {
  return (
    <ProtectedRoute>
      <DashboardLayout>
        <UserTicketDetailContent />
      </DashboardLayout>
    </ProtectedRoute>
  );
}
