"""
Ticket System Models
Three-way communication system between Reporter, Analyst, and Authority.
"""

from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict, Any
from enum import Enum
from pydantic import BaseModel, Field
from app.utils.timezone import to_ist_isoformat


class TicketStatus(str, Enum):
    """Ticket lifecycle states"""
    OPEN = "open"                          # Just created, awaiting assignment
    ASSIGNED = "assigned"                  # Analyst assigned, not yet worked on
    IN_PROGRESS = "in_progress"            # Actively being worked on
    AWAITING_RESPONSE = "awaiting_response"  # Waiting for reporter/external response
    ESCALATED = "escalated"                # Moved to higher authority
    RESOLVED = "resolved"                  # Issue addressed, awaiting closure
    CLOSED = "closed"                      # Completely finished
    REOPENED = "reopened"                  # Previously resolved but issue recurred


class TicketPriority(str, Enum):
    """Ticket priority levels with SLA definitions"""
    EMERGENCY = "emergency"    # Life-threatening, Response: 1h, Resolution: 4h
    CRITICAL = "critical"      # Severe threat, Response: 2h, Resolution: 8h
    HIGH = "high"              # Significant threat, Response: 4h, Resolution: 1d
    MEDIUM = "medium"          # Important but not urgent, Response: 8h, Resolution: 2d
    LOW = "low"                # Non-urgent, Response: 1d, Resolution: 5d


class MessageType(str, Enum):
    """Types of messages in a ticket"""
    TEXT = "text"                  # Regular conversation
    STATUS_UPDATE = "status_update"  # Ticket assigned, status changed
    ASSIGNMENT = "assignment"      # Analyst/authority assignment
    ESCALATION = "escalation"      # Escalation notification
    RESOLUTION = "resolution"      # Resolution notes
    SYSTEM = "system"              # Automatic system messages
    ATTACHMENT = "attachment"      # File/photo upload


class ActivityType(str, Enum):
    """Types of activities for audit trail"""
    TICKET_CREATED = "ticket_created"
    TICKET_ASSIGNED = "ticket_assigned"
    TICKET_REASSIGNED = "ticket_reassigned"
    MESSAGE_ADDED = "message_added"
    STATUS_CHANGED = "status_changed"
    PRIORITY_CHANGED = "priority_changed"
    ESCALATED = "escalated"
    RESOLVED = "resolved"
    CLOSED = "closed"
    REOPENED = "reopened"
    ATTACHMENT_ADDED = "attachment_added"
    SLA_BREACH = "sla_breach"
    FEEDBACK_RECEIVED = "feedback_received"


class AssignmentStatus(str, Enum):
    """Status of ticket assignment (replaces string "PENDING_ASSIGNMENT")"""
    UNASSIGNED = "unassigned"             # No one assigned yet
    ANALYST_ONLY = "analyst_only"         # Only analyst assigned
    AUTHORITY_ONLY = "authority_only"     # Only authority assigned
    FULLY_ASSIGNED = "fully_assigned"     # Both analyst and authority assigned


class SLABreachAction(str, Enum):
    """Configurable action when SLA is breached"""
    NOTIFY_ONLY = "notify_only"       # Just send notifications
    AUTO_ESCALATE = "auto_escalate"   # Automatically escalate the ticket
    BOTH = "both"                     # Notify AND auto-escalate


class MessageThread(str, Enum):
    """Message thread types for 3-way separate conversations"""
    ALL_PARTIES = "all"               # Visible to everyone (reporter, analyst, authority)
    REPORTER_ANALYST = "ra"           # Private: Reporter ↔ Analyst
    ANALYST_AUTHORITY = "aa"          # Private: Analyst ↔ Authority
    INTERNAL = "internal"             # Internal notes (analyst + authority only, hidden from reporter)


# =============================================================================
# SLA CONFIGURATION
# =============================================================================

SLA_CONFIG: Dict[TicketPriority, Dict[str, int]] = {
    TicketPriority.EMERGENCY: {
        "response_hours": 1,
        "resolution_hours": 4
    },
    TicketPriority.CRITICAL: {
        "response_hours": 2,
        "resolution_hours": 8
    },
    TicketPriority.HIGH: {
        "response_hours": 4,
        "resolution_hours": 24  # 1 day
    },
    TicketPriority.MEDIUM: {
        "response_hours": 8,
        "resolution_hours": 48  # 2 days
    },
    TicketPriority.LOW: {
        "response_hours": 24,  # 1 day
        "resolution_hours": 120  # 5 days
    }
}


def calculate_sla_deadlines(priority: TicketPriority, created_at: datetime) -> Dict[str, datetime]:
    """Calculate SLA deadlines based on priority"""
    config = SLA_CONFIG[priority]
    return {
        "response_due": created_at + timedelta(hours=config["response_hours"]),
        "resolution_due": created_at + timedelta(hours=config["resolution_hours"])
    }


# =============================================================================
# NEW EMBEDDED MODELS (V2)
# =============================================================================

class TicketAssignment(BaseModel):
    """Structured assignment tracking - replaces scattered assignment fields"""
    # Analyst assignment
    analyst_id: Optional[str] = Field(default=None, description="Assigned analyst user ID")
    analyst_name: Optional[str] = Field(default=None, description="Assigned analyst name")
    analyst_assigned_at: Optional[datetime] = Field(default=None, description="When analyst was assigned")
    analyst_assigned_by: Optional[str] = Field(default=None, description="Who assigned the analyst")

    # Authority assignment
    authority_id: Optional[str] = Field(default=None, description="Assigned authority user ID (NULL instead of PENDING_ASSIGNMENT)")
    authority_name: Optional[str] = Field(default=None, description="Assigned authority name")
    authority_assigned_at: Optional[datetime] = Field(default=None, description="When authority was assigned")
    authority_assigned_by: Optional[str] = Field(default=None, description="Who assigned the authority")

    # Overall assignment status
    status: AssignmentStatus = Field(default=AssignmentStatus.UNASSIGNED, description="Current assignment status")

    class Config:
        json_encoders = {datetime: lambda v: to_ist_isoformat(v)}

    def compute_status(self) -> AssignmentStatus:
        """Compute assignment status based on current assignments"""
        has_analyst = self.analyst_id is not None
        has_authority = self.authority_id is not None

        if has_analyst and has_authority:
            return AssignmentStatus.FULLY_ASSIGNED
        elif has_analyst:
            return AssignmentStatus.ANALYST_ONLY
        elif has_authority:
            return AssignmentStatus.AUTHORITY_ONLY
        else:
            return AssignmentStatus.UNASSIGNED


class TicketApproval(BaseModel):
    """Structured approval tracking - tracks how report was approved to create ticket"""
    approval_source: str = Field(..., description="Source: ai_auto, ai_recommended, authority_manual, analyst_verified")
    approved_by_id: Optional[str] = Field(default=None, description="User ID who approved (NULL for ai_auto)")
    approved_by_name: Optional[str] = Field(default=None, description="Name of approver")
    approved_by_role: Optional[str] = Field(default=None, description="Role: 'ai', 'analyst', 'authority'")
    ai_verification_score: Optional[float] = Field(default=None, description="AI verification score at time of approval")
    approved_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="When approved")
    approval_notes: Optional[str] = Field(default=None, description="Notes about the approval")

    class Config:
        json_encoders = {datetime: lambda v: to_ist_isoformat(v)}


class TicketSLAConfig(BaseModel):
    """Per-ticket SLA configuration override"""
    response_hours: int = Field(..., description="Hours for first response SLA")
    resolution_hours: int = Field(..., description="Hours for resolution SLA")
    breach_action: SLABreachAction = Field(default=SLABreachAction.NOTIFY_ONLY, description="Action on SLA breach")
    is_custom: bool = Field(default=False, description="Whether this is a custom override from defaults")

    class Config:
        json_encoders = {datetime: lambda v: to_ist_isoformat(v)}


# =============================================================================
# MESSAGE MODELS
# =============================================================================

class Attachment(BaseModel):
    """File attachment in a message"""
    attachment_id: str = Field(..., description="Unique attachment ID")
    filename: str = Field(..., description="Original filename")
    file_path: str = Field(..., description="Storage path")
    file_type: str = Field(..., description="MIME type")
    file_size: int = Field(..., description="Size in bytes")
    thumbnail_path: Optional[str] = Field(default=None, description="Thumbnail for images")
    uploaded_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Config:
        json_encoders = {datetime: lambda v: to_ist_isoformat(v)}


class MessageReaction(BaseModel):
    """Emoji reaction to a message"""
    user_id: str
    user_name: str
    emoji: str  # 👍, ❤️, ⚠️, ✅
    reacted_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class TicketParticipant(BaseModel):
    """Additional participant added to a ticket"""
    user_id: str = Field(..., description="User ID of the participant")
    user_name: str = Field(..., description="Display name of the participant")
    user_role: str = Field(..., description="Role: citizen, analyst, authority, authority_admin")
    added_by_id: str = Field(..., description="User ID of who added this participant")
    added_by_name: str = Field(..., description="Name of who added this participant")
    added_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    can_message: bool = Field(default=True, description="Can send messages in the ticket")
    is_active: bool = Field(default=True, description="Is still an active participant")
    notes: Optional[str] = Field(default=None, description="Reason for adding this participant")


class ReadReceipt(BaseModel):
    """Read receipt for a message"""
    user_id: str
    user_name: str
    read_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class TicketMessage(BaseModel):
    """Individual message in a ticket thread"""
    message_id: str = Field(..., description="Unique message ID")
    ticket_id: str = Field(..., description="Parent ticket ID")

    # Sender info
    sender_id: str = Field(..., description="User ID of sender")
    sender_name: str = Field(..., description="Name of sender")
    sender_role: str = Field(..., description="Role: citizen, analyst, authority")

    # Message content
    message_type: MessageType = Field(default=MessageType.TEXT)
    content: str = Field(..., description="Message text content")

    # Thread & Visibility (V2)
    thread: str = Field(
        default="all",
        description="Message thread: all (everyone), ra (reporter-analyst), aa (analyst-authority), internal"
    )
    visible_to: List[str] = Field(
        default=[],
        description="User IDs who can see this message (computed from thread)"
    )
    is_internal: bool = Field(
        default=False,
        description="DEPRECATED: Use thread='internal' instead. Kept for backward compatibility."
    )

    # Reply to specific message
    reply_to_message_id: Optional[str] = Field(
        default=None,
        description="ID of message being replied to"
    )

    # Attachments
    attachments: List[Attachment] = Field(default=[])

    # Reactions and read receipts
    reactions: List[MessageReaction] = Field(default=[])
    read_by: List[ReadReceipt] = Field(default=[])

    # Timestamps
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    edited_at: Optional[datetime] = Field(default=None)
    is_edited: bool = Field(default=False)

    # Metadata
    metadata: Dict[str, Any] = Field(default={})

    class Config:
        json_encoders = {datetime: lambda v: to_ist_isoformat(v)}

    def compute_visible_to(self, reporter_id: str, analyst_id: Optional[str], authority_id: Optional[str]) -> List[str]:
        """Compute which user IDs can see this message based on thread type"""
        visible = []
        thread_type = self.thread

        if thread_type == "all" or thread_type == MessageThread.ALL_PARTIES.value:
            # Everyone can see
            visible.append(reporter_id)
            if analyst_id:
                visible.append(analyst_id)
            if authority_id:
                visible.append(authority_id)
        elif thread_type == "ra" or thread_type == MessageThread.REPORTER_ANALYST.value:
            # Reporter and Analyst only
            visible.append(reporter_id)
            if analyst_id:
                visible.append(analyst_id)
        elif thread_type == "aa" or thread_type == MessageThread.ANALYST_AUTHORITY.value:
            # Analyst and Authority only
            if analyst_id:
                visible.append(analyst_id)
            if authority_id:
                visible.append(authority_id)
        elif thread_type == "internal" or thread_type == MessageThread.INTERNAL.value:
            # Internal notes - analyst and authority only
            if analyst_id:
                visible.append(analyst_id)
            if authority_id:
                visible.append(authority_id)

        return visible

    def can_user_see(self, user_id: str, user_role: str, reporter_id: str, analyst_id: Optional[str], authority_id: Optional[str]) -> bool:
        """Check if a specific user can see this message"""
        # If visible_to is already computed, use it
        if self.visible_to:
            return user_id in self.visible_to

        # Otherwise compute based on thread
        thread_type = self.thread

        if thread_type == "all":
            return True
        elif thread_type == "ra":
            return user_id == reporter_id or user_id == analyst_id
        elif thread_type == "aa":
            return user_id == analyst_id or user_id == authority_id
        elif thread_type == "internal":
            return user_role in ["analyst", "authority", "authority_admin"]

        return False


# =============================================================================
# ACTIVITY LOG MODEL
# =============================================================================

class TicketActivity(BaseModel):
    """Audit trail entry for ticket actions"""
    activity_id: str = Field(..., description="Unique activity ID")
    ticket_id: str = Field(..., description="Associated ticket ID")

    # Action details
    activity_type: ActivityType = Field(..., description="Type of activity")

    # Who performed the action
    performed_by_id: str = Field(..., description="User ID")
    performed_by_name: str = Field(..., description="User name")
    performed_by_role: str = Field(..., description="User role")

    # Activity details
    description: str = Field(..., description="Human-readable description")
    details: Dict[str, Any] = Field(default={}, description="Additional context")

    # Previous/new values for changes
    previous_value: Optional[str] = Field(default=None)
    new_value: Optional[str] = Field(default=None)

    # Security tracking
    ip_address: Optional[str] = Field(default=None)
    user_agent: Optional[str] = Field(default=None)

    # Timestamp
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Config:
        json_encoders = {datetime: lambda v: to_ist_isoformat(v)}


# =============================================================================
# FEEDBACK MODEL
# =============================================================================

class TicketFeedback(BaseModel):
    """Reporter feedback after ticket resolution"""
    feedback_id: str = Field(..., description="Unique feedback ID")
    ticket_id: str = Field(..., description="Associated ticket ID")

    # Who gave feedback
    reporter_id: str = Field(..., description="Reporter user ID")
    reporter_name: str = Field(..., description="Reporter name")

    # Rating (1-5 stars)
    satisfaction_rating: int = Field(..., ge=1, le=5, description="1-5 star rating")

    # Text feedback
    comments: Optional[str] = Field(default=None, description="Free text comments")

    # Specific aspects
    response_time_good: bool = Field(default=False)
    communication_clear: bool = Field(default=False)
    issue_resolved_effectively: bool = Field(default=False)
    analyst_helpful: bool = Field(default=False)
    authority_action_appropriate: bool = Field(default=False)

    # Timestamp
    submitted_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Config:
        json_encoders = {datetime: lambda v: to_ist_isoformat(v)}


# =============================================================================
# ESCALATION MODEL
# =============================================================================

class Escalation(BaseModel):
    """Escalation record"""
    escalation_id: str = Field(..., description="Unique escalation ID")
    ticket_id: str = Field(..., description="Associated ticket ID")

    # Who escalated
    escalated_by_id: str = Field(..., description="User who escalated")
    escalated_by_name: str = Field(..., description="Name of escalator")
    escalated_by_role: str = Field(..., description="Role of escalator")

    # Escalation target
    escalated_to_id: str = Field(..., description="Target user/authority ID")
    escalated_to_name: str = Field(..., description="Target name")

    # Reason
    reason: str = Field(..., min_length=10, description="Reason for escalation")

    # Previous state
    previous_priority: TicketPriority
    previous_status: TicketStatus
    previous_assignee_id: Optional[str] = None
    previous_assignee_name: Optional[str] = None

    # New state after escalation
    new_priority: TicketPriority = TicketPriority.CRITICAL
    new_status: TicketStatus = TicketStatus.ESCALATED

    # Timestamps
    escalated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    accepted_at: Optional[datetime] = Field(default=None)
    resolved_at: Optional[datetime] = Field(default=None)

    class Config:
        json_encoders = {datetime: lambda v: to_ist_isoformat(v)}


# =============================================================================
# MAIN TICKET MODEL
# =============================================================================

class Ticket(BaseModel):
    """Main ticket model for three-way communication"""
    ticket_id: str = Field(..., description="Unique ticket ID (TKT-YYYYMMDD-XXXX)")

    # Linked hazard report
    report_id: str = Field(..., description="Associated hazard report ID")
    hazard_type: str = Field(..., description="Type of hazard from report")

    # Title and description
    title: str = Field(..., description="Ticket title")
    description: str = Field(..., description="Initial description from report")

    # Location info (copied from report)
    location_latitude: float
    location_longitude: float
    location_address: Optional[str] = None

    # Status and priority
    status: TicketStatus = Field(default=TicketStatus.OPEN)
    priority: TicketPriority = Field(default=TicketPriority.MEDIUM)

    # Participants
    reporter_id: str = Field(..., description="Original reporter user ID")
    reporter_name: str = Field(..., description="Reporter name")

    assigned_analyst_id: Optional[str] = Field(default=None)
    assigned_analyst_name: Optional[str] = Field(default=None)

    authority_id: str = Field(..., description="Authority who created ticket")
    authority_name: str = Field(..., description="Authority name")

    # Assigned authority (specific authority user this ticket is assigned to)
    assigned_authority_id: Optional[str] = Field(default=None, description="Specific authority user assigned to this ticket")
    assigned_authority_name: Optional[str] = Field(default=None, description="Name of assigned authority")

    # Approver info (who approved the report to create this ticket)
    approved_by: Optional[str] = Field(default=None, description="User ID of who approved the report")
    approved_by_name: Optional[str] = Field(default=None, description="Name of who approved the report")
    approved_by_role: Optional[str] = Field(default=None, description="Role of approver (analyst/authority)")

    # Escalation info
    is_escalated: bool = Field(default=False)
    escalated_to_id: Optional[str] = Field(default=None)
    escalated_to_name: Optional[str] = Field(default=None)
    escalation_reason: Optional[str] = Field(default=None)
    escalation_count: int = Field(default=0)

    # SLA tracking
    response_due: datetime = Field(..., description="SLA response deadline")
    resolution_due: datetime = Field(..., description="SLA resolution deadline")
    first_response_at: Optional[datetime] = Field(default=None)
    sla_response_breached: bool = Field(default=False)
    sla_resolution_breached: bool = Field(default=False)

    # Resolution info
    resolution_notes: Optional[str] = Field(default=None)
    actions_taken: List[str] = Field(default=[])
    resolved_at: Optional[datetime] = Field(default=None)
    resolved_by_id: Optional[str] = Field(default=None)
    resolved_by_name: Optional[str] = Field(default=None)

    # Closure info
    closed_at: Optional[datetime] = Field(default=None)
    closed_by_id: Optional[str] = Field(default=None)
    closed_by_name: Optional[str] = Field(default=None)
    closure_reason: Optional[str] = Field(default=None)

    # Feedback
    feedback_received: bool = Field(default=False)
    satisfaction_rating: Optional[int] = Field(default=None, ge=1, le=5)

    # Additional participants (beyond reporter, analyst, authority)
    additional_participants: List[Dict[str, Any]] = Field(
        default=[],
        description="Additional users added to this ticket"
    )

    # Related tickets
    parent_ticket_id: Optional[str] = Field(default=None, description="Parent ticket if this is a sub-task")
    child_ticket_ids: List[str] = Field(default=[], description="Child/sub-task tickets")
    related_ticket_ids: List[str] = Field(default=[], description="Related linked tickets")

    # Message summary
    total_messages: int = Field(default=0)
    unread_count_reporter: int = Field(default=0)
    unread_count_analyst: int = Field(default=0)
    unread_count_authority: int = Field(default=0)
    last_message_at: Optional[datetime] = Field(default=None)
    last_message_by: Optional[str] = Field(default=None)

    # Timestamps
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    # Metadata
    tags: List[str] = Field(default=[])
    metadata: Dict[str, Any] = Field(default={})

    # V2 Structured Fields (new)
    assignment: Optional[Dict[str, Any]] = Field(
        default=None,
        description="V2: Structured assignment (TicketAssignment). If None, use legacy fields."
    )
    approval: Optional[Dict[str, Any]] = Field(
        default=None,
        description="V2: Structured approval info (TicketApproval). Tracks how report was approved."
    )
    sla_config: Optional[Dict[str, Any]] = Field(
        default=None,
        description="V2: Per-ticket SLA configuration override (TicketSLAConfig)."
    )
    sync_version: int = Field(
        default=0,
        description="V2: Optimistic concurrency control version"
    )

    class Config:
        json_encoders = {datetime: lambda v: to_ist_isoformat(v)}

    @classmethod
    def from_mongo(cls, doc: Dict[str, Any]) -> "Ticket":
        """Create Ticket instance from MongoDB document"""
        if doc is None:
            return None
        if "_id" in doc:
            doc.pop("_id")
        return cls(**doc)

    def to_mongo(self) -> Dict[str, Any]:
        """Convert to MongoDB document format"""
        return self.model_dump()

    def get_time_in_status(self) -> int:
        """Get minutes the ticket has been in current status"""
        return int((datetime.now(timezone.utc) - self.updated_at).total_seconds() / 60)

    def is_response_sla_at_risk(self, warning_threshold_minutes: int = 30) -> bool:
        """Check if response SLA is at risk"""
        if self.first_response_at:
            return False
        minutes_to_deadline = (self.response_due - datetime.now(timezone.utc)).total_seconds() / 60
        return minutes_to_deadline <= warning_threshold_minutes

    def is_resolution_sla_at_risk(self, warning_threshold_minutes: int = 60) -> bool:
        """Check if resolution SLA is at risk"""
        if self.resolved_at:
            return False
        minutes_to_deadline = (self.resolution_due - datetime.now(timezone.utc)).total_seconds() / 60
        return minutes_to_deadline <= warning_threshold_minutes

    def get_assignment_v2(self) -> TicketAssignment:
        """Get V2 structured assignment, creating from legacy fields if needed"""
        if self.assignment:
            return TicketAssignment(**self.assignment)

        # Create from legacy fields
        assignment = TicketAssignment(
            analyst_id=self.assigned_analyst_id,
            analyst_name=self.assigned_analyst_name,
            authority_id=self.assigned_authority_id if self.assigned_authority_id != "PENDING_ASSIGNMENT" else None,
            authority_name=self.assigned_authority_name if self.assigned_authority_id != "PENDING_ASSIGNMENT" else None
        )
        assignment.status = assignment.compute_status()
        return assignment

    def get_approval_v2(self) -> Optional[TicketApproval]:
        """Get V2 structured approval info"""
        if self.approval:
            return TicketApproval(**self.approval)

        # Create from legacy fields if available
        if self.approved_by:
            return TicketApproval(
                approval_source="authority_manual",  # Default for legacy
                approved_by_id=self.approved_by,
                approved_by_name=self.approved_by_name,
                approved_by_role=self.approved_by_role,
                approved_at=self.created_at
            )
        return None

    def get_sla_config_v2(self) -> TicketSLAConfig:
        """Get V2 SLA config, using defaults if not customized"""
        if self.sla_config:
            return TicketSLAConfig(**self.sla_config)

        # Use defaults from priority
        config = SLA_CONFIG[self.priority]
        return TicketSLAConfig(
            response_hours=config["response_hours"],
            resolution_hours=config["resolution_hours"],
            breach_action=SLABreachAction.NOTIFY_ONLY,
            is_custom=False
        )


# =============================================================================
# API REQUEST/RESPONSE MODELS
# =============================================================================

class CreateTicketRequest(BaseModel):
    """Request to create a new ticket"""
    report_id: str = Field(..., description="Hazard report ID")
    priority: TicketPriority = Field(default=TicketPriority.MEDIUM)
    title: Optional[str] = Field(default=None, description="Custom title (auto-generated if not provided)")
    initial_message: Optional[str] = Field(default=None, description="Initial message to reporter")
    assign_to_analyst_id: Optional[str] = Field(default=None)
    tags: List[str] = Field(default=[])


class AssignTicketRequest(BaseModel):
    """Request to assign ticket to analyst"""
    analyst_id: str = Field(..., description="Analyst user ID")
    message: Optional[str] = Field(default=None, description="Assignment message")


class AssignToAuthorityRequest(BaseModel):
    """Request to assign ticket to a specific authority"""
    authority_id: str = Field(..., description="Authority user ID to assign the ticket to")
    message: Optional[str] = Field(default=None, description="Assignment message")


class UpdateTicketStatusRequest(BaseModel):
    """Request to update ticket status"""
    status: TicketStatus
    notes: Optional[str] = Field(default=None)


class UpdateTicketPriorityRequest(BaseModel):
    """Request to update ticket priority"""
    priority: TicketPriority
    reason: str = Field(..., min_length=5)


class EscalateTicketRequest(BaseModel):
    """Request to escalate ticket"""
    reason: str = Field(..., min_length=10, description="Reason for escalation")
    escalate_to_id: Optional[str] = Field(default=None, description="Specific authority to escalate to")
    suggested_priority: TicketPriority = Field(default=TicketPriority.CRITICAL)


class ResolveTicketRequest(BaseModel):
    """Request to resolve ticket"""
    resolution_notes: str = Field(..., min_length=20, description="Resolution summary")
    actions_taken: List[str] = Field(..., min_length=1, description="List of actions taken")


class SendMessageRequest(BaseModel):
    """Request to send a message in ticket"""
    content: str = Field(..., min_length=1, max_length=5000)
    thread: str = Field(
        default="all",
        description="Message thread: all (everyone), ra (reporter-analyst), aa (analyst-authority), internal"
    )
    is_internal: bool = Field(
        default=False,
        description="DEPRECATED: Use thread='internal' instead. Kept for backward compatibility."
    )
    reply_to_message_id: Optional[str] = Field(default=None)


class SubmitFeedbackRequest(BaseModel):
    """Request to submit ticket feedback"""
    satisfaction_rating: int = Field(..., ge=1, le=5)
    comments: Optional[str] = Field(default=None, max_length=1000)
    response_time_good: bool = Field(default=False)
    communication_clear: bool = Field(default=False)
    issue_resolved_effectively: bool = Field(default=False)
    analyst_helpful: bool = Field(default=False)
    authority_action_appropriate: bool = Field(default=False)


class AddParticipantRequest(BaseModel):
    """Request to add a participant to a ticket"""
    user_id: str = Field(..., description="User ID of the participant to add")
    notes: Optional[str] = Field(default=None, max_length=500, description="Reason for adding this participant")
    can_message: bool = Field(default=True, description="Can send messages in the ticket")


class RemoveParticipantRequest(BaseModel):
    """Request to remove a participant from a ticket"""
    user_id: str = Field(..., description="User ID of the participant to remove")


class TicketListResponse(BaseModel):
    """Response for ticket list"""
    tickets: List[Ticket]
    total: int
    page: int
    page_size: int
    has_more: bool


class TicketDetailResponse(BaseModel):
    """Response for ticket detail with messages"""
    ticket: Ticket
    messages: List[TicketMessage]
    activities: List[TicketActivity]
    feedback: Optional[TicketFeedback] = None


class TicketStatsResponse(BaseModel):
    """Ticket statistics response"""
    total_tickets: int
    open_tickets: int
    in_progress_tickets: int
    resolved_tickets: int
    closed_tickets: int
    escalated_tickets: int
    avg_response_time_hours: float
    avg_resolution_time_hours: float
    sla_compliance_rate: float
    avg_satisfaction_rating: float
    tickets_by_priority: Dict[str, int]
    tickets_by_status: Dict[str, int]
    period_start: datetime
    period_end: datetime
