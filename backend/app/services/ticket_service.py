"""
Ticket Service (V2)
Handles ticket CRUD operations, assignment, escalation, and messaging.

V2 Changes:
- Full status sync to hazard reports on all transitions
- Thread-based message filtering (all, ra, aa, internal)
- Uses null instead of "PENDING_ASSIGNMENT" for unassigned authority
- Uses new TicketAssignment embedded model for structured assignment tracking
- Supports sync_version for optimistic concurrency control
"""

import logging
import uuid
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any, Tuple

from motor.motor_asyncio import AsyncIOMotorDatabase

from app.models.ticket import (
    Ticket, TicketMessage, TicketActivity, TicketFeedback, Escalation,
    TicketStatus, TicketPriority, MessageType, ActivityType, Attachment,
    calculate_sla_deadlines, SLA_CONFIG,
    CreateTicketRequest, AssignTicketRequest, EscalateTicketRequest,
    ResolveTicketRequest, SendMessageRequest, SubmitFeedbackRequest,
    AssignmentStatus, TicketAssignment, TicketApproval, MessageThread
)
from app.models.hazard import HazardReport, VerificationStatus, TicketCreationStatus
from app.models.user import User, UserRole
from app.models.notification import NotificationType, NotificationSeverity

logger = logging.getLogger(__name__)

# Global service instance
_ticket_service: Optional["TicketService"] = None


def get_ticket_service(db: AsyncIOMotorDatabase = None) -> "TicketService":
    """Get or create ticket service singleton"""
    global _ticket_service
    if _ticket_service is None:
        _ticket_service = TicketService(db)
    elif db is not None:
        _ticket_service.db = db
    return _ticket_service


class TicketService:
    """Service for managing tickets and messages"""

    def __init__(self, db: AsyncIOMotorDatabase = None):
        self.db = db
        self._initialized = False

    def _get_user_name(self, user: User) -> str:
        """Get display name for a user (handles both name and first_name/last_name formats)"""
        if hasattr(user, 'name') and user.name:
            return user.name
        # Fallback for compatibility
        first = getattr(user, 'first_name', '') or ''
        last = getattr(user, 'last_name', '') or ''
        if first or last:
            return f"{first} {last}".strip()
        return user.email or user.user_id or "Unknown User"

    async def initialize(self, db: AsyncIOMotorDatabase = None):
        """Initialize the service with database connection"""
        if db is not None:
            self.db = db

        if self.db is None:
            logger.warning("No database connection provided to TicketService")
            return

        # Create indexes
        await self._create_indexes()
        self._initialized = True
        logger.info("TicketService initialized successfully")

    async def _create_indexes(self):
        """Create database indexes for ticket collections"""
        try:
            # Tickets collection indexes
            await self.db.tickets.create_index("ticket_id", unique=True)
            await self.db.tickets.create_index("report_id")
            await self.db.tickets.create_index("status")
            await self.db.tickets.create_index("priority")
            await self.db.tickets.create_index("reporter_id")
            await self.db.tickets.create_index("assigned_analyst_id")
            await self.db.tickets.create_index("authority_id")
            await self.db.tickets.create_index("created_at")
            await self.db.tickets.create_index([("status", 1), ("priority", -1), ("created_at", 1)])

            # Messages collection indexes
            await self.db.ticket_messages.create_index("message_id", unique=True)
            await self.db.ticket_messages.create_index("ticket_id")
            await self.db.ticket_messages.create_index([("ticket_id", 1), ("created_at", 1)])

            # Activities collection indexes
            await self.db.ticket_activities.create_index("activity_id", unique=True)
            await self.db.ticket_activities.create_index("ticket_id")
            await self.db.ticket_activities.create_index([("ticket_id", 1), ("created_at", 1)])

            # Feedback collection indexes
            await self.db.ticket_feedback.create_index("feedback_id", unique=True)
            await self.db.ticket_feedback.create_index("ticket_id", unique=True)

            logger.info("✓ Ticket database indexes created")
        except Exception as e:
            logger.error(f"Error creating ticket indexes: {e}")

    # =========================================================================
    # TICKET CRUD OPERATIONS
    # =========================================================================

    def _generate_ticket_id(self) -> str:
        """Generate unique ticket ID"""
        date_str = datetime.now().strftime("%Y%m%d")
        unique_part = uuid.uuid4().hex[:6].upper()
        return f"TKT-{date_str}-{unique_part}"

    def _generate_message_id(self) -> str:
        """Generate unique message ID"""
        return f"MSG-{uuid.uuid4().hex[:12].upper()}"

    def _generate_activity_id(self) -> str:
        """Generate unique activity ID"""
        return f"ACT-{uuid.uuid4().hex[:12].upper()}"

    async def create_ticket(
        self,
        request: CreateTicketRequest,
        authority: User,
        db: AsyncIOMotorDatabase = None
    ) -> Tuple[Ticket, TicketMessage]:
        """
        Create a new ticket from a verified hazard report.

        Only authorities can create tickets.
        """
        db = db if db is not None else self.db

        # Validate authority role
        if authority.role not in [UserRole.AUTHORITY, UserRole.AUTHORITY_ADMIN]:
            raise ValueError("Only authorities can create tickets")

        # Get the hazard report
        report_doc = await db.hazard_reports.find_one({"report_id": request.report_id})
        if not report_doc:
            raise ValueError(f"Report {request.report_id} not found")

        report = HazardReport.from_mongo(report_doc)

        # Validate report is verified
        if report.verification_status != VerificationStatus.VERIFIED:
            raise ValueError(
                f"Cannot create ticket for report with status '{report.verification_status.value}'. "
                "Only verified reports can have tickets."
            )

        # Check if ticket already exists for this report
        existing = await db.tickets.find_one({"report_id": request.report_id})
        if existing:
            raise ValueError(f"Ticket already exists for report {request.report_id}")

        # Generate ticket ID
        ticket_id = self._generate_ticket_id()
        now = datetime.now(timezone.utc)

        # Calculate SLA deadlines
        sla = calculate_sla_deadlines(request.priority, now)

        # Generate title if not provided
        title = request.title or f"{report.hazard_type.value.replace('_', ' ').title()} at {report.location.address or 'Unknown Location'}"

        # Create ticket
        ticket = Ticket(
            ticket_id=ticket_id,
            report_id=request.report_id,
            hazard_type=report.hazard_type.value,
            title=title,
            description=report.description or "",
            location_latitude=report.location.latitude,
            location_longitude=report.location.longitude,
            location_address=report.location.address,
            status=TicketStatus.OPEN,
            priority=request.priority,
            reporter_id=report.user_id,
            reporter_name=report.user_name or "Unknown Reporter",
            authority_id=authority.user_id,
            authority_name=self._get_user_name(authority),
            response_due=sla["response_due"],
            resolution_due=sla["resolution_due"],
            tags=request.tags,
            created_at=now,
            updated_at=now
        )

        # Save ticket to database
        await db.tickets.insert_one(ticket.to_mongo())

        # Create initial system message
        initial_message = TicketMessage(
            message_id=self._generate_message_id(),
            ticket_id=ticket_id,
            sender_id="SYSTEM",
            sender_name="System",
            sender_role="system",
            message_type=MessageType.SYSTEM,
            content=f"Ticket created by {self._get_user_name(authority)} for hazard report {request.report_id}",
            is_internal=False
        )
        await db.ticket_messages.insert_one(initial_message.model_dump())

        # Add custom initial message if provided
        if request.initial_message:
            custom_message = TicketMessage(
                message_id=self._generate_message_id(),
                ticket_id=ticket_id,
                sender_id=authority.user_id,
                sender_name=self._get_user_name(authority),
                sender_role="authority",
                message_type=MessageType.TEXT,
                content=request.initial_message,
                is_internal=False
            )
            await db.ticket_messages.insert_one(custom_message.model_dump())
            ticket.total_messages = 2
            ticket.last_message_at = now
            ticket.last_message_by = authority.user_id
            await db.tickets.update_one(
                {"ticket_id": ticket_id},
                {"$set": {
                    "total_messages": 2,
                    "last_message_at": now,
                    "last_message_by": authority.user_id
                }}
            )

        # Log activity
        await self._log_activity(
            ticket_id=ticket_id,
            activity_type=ActivityType.TICKET_CREATED,
            performed_by=authority,
            description=f"Ticket created with priority {request.priority.value}",
            details={
                "report_id": request.report_id,
                "priority": request.priority.value,
                "hazard_type": report.hazard_type.value
            },
            db=db
        )

        # If assign_to_analyst_id provided, assign immediately
        if request.assign_to_analyst_id:
            await self.assign_ticket(
                ticket_id=ticket_id,
                request=AssignTicketRequest(analyst_id=request.assign_to_analyst_id),
                assigner=authority,
                db=db
            )

        # Update hazard report with ticket reference
        await db.hazard_reports.update_one(
            {"report_id": request.report_id},
            {"$set": {
                "ticket_id": ticket_id,
                "has_ticket": True,
                "ticket_status": TicketStatus.OPEN.value,
                "ticket_created_at": now,
                "updated_at": now
            }}
        )

        # Notify reporter that a ticket was created for their report
        await self._create_ticket_notification(
            user_id=report.user_id,
            notification_type=NotificationType.TICKET_CREATED,
            severity=NotificationSeverity.MEDIUM,
            title="Support Ticket Created",
            message=f"A support ticket has been created for your hazard report: {title}",
            ticket_id=ticket_id,
            report_id=request.report_id,
            metadata={"priority": request.priority.value, "hazard_type": report.hazard_type.value},
            db=db
        )

        logger.info(f"Created ticket {ticket_id} for report {request.report_id}")
        return ticket, initial_message

    async def get_ticket(
        self,
        ticket_id: str,
        db: AsyncIOMotorDatabase = None
    ) -> Optional[Ticket]:
        """Get ticket by ID"""
        db = db if db is not None else self.db
        doc = await db.tickets.find_one({"ticket_id": ticket_id})
        return Ticket.from_mongo(doc) if doc else None

    async def get_tickets_for_user(
        self,
        user: User,
        status: Optional[TicketStatus] = None,
        priority: Optional[TicketPriority] = None,
        page: int = 1,
        page_size: int = 20,
        db: AsyncIOMotorDatabase = None
    ) -> Tuple[List[Ticket], int]:
        """Get tickets accessible to user based on their role"""
        db = db if db is not None else self.db

        # Build query based on user role
        query: Dict[str, Any] = {}

        if user.role == UserRole.CITIZEN:
            query["reporter_id"] = user.user_id
        elif user.role == UserRole.ANALYST:
            query["$or"] = [
                {"assigned_analyst_id": user.user_id},
                {"status": TicketStatus.OPEN.value}  # Can see unassigned tickets
            ]
        elif user.role in [UserRole.AUTHORITY, UserRole.AUTHORITY_ADMIN]:
            # Authorities can ONLY see tickets:
            # 1. Directly assigned to them (assigned_authority_id matches)
            # 2. They created the ticket (authority_id matches AND it's not PENDING)
            # 3. Escalated to them
            # 4. They are a participant on
            # 5. They approved the report (approved_by matches their user_id)
            query["$or"] = [
                {"assigned_authority_id": user.user_id},  # Specifically assigned to this authority
                {"$and": [
                    {"authority_id": user.user_id},
                    {"authority_id": {"$ne": "PENDING_ASSIGNMENT"}}
                ]},  # They created it (not PENDING)
                {"escalated_to_id": user.user_id},
                {"additional_participants.user_id": user.user_id},
                {"approved_by": user.user_id}  # They approved the report
            ]
        # Admins see all tickets (no filter)

        # Add status filter
        if status:
            query["status"] = status.value

        # Add priority filter
        if priority:
            query["priority"] = priority.value

        # Count total
        total = await db.tickets.count_documents(query)

        # Get paginated results
        skip = (page - 1) * page_size
        cursor = db.tickets.find(query).sort([
            ("priority", -1),  # Emergency first
            ("created_at", 1)  # FIFO within same priority
        ]).skip(skip).limit(page_size)

        tickets = []
        async for doc in cursor:
            tickets.append(Ticket.from_mongo(doc))

        return tickets, total

    async def get_queue_tickets(
        self,
        status: Optional[List[TicketStatus]] = None,
        priority: Optional[TicketPriority] = None,
        limit: int = 50,
        db: AsyncIOMotorDatabase = None
    ) -> List[Ticket]:
        """Get tickets in the queue (for analysts/authorities)"""
        db = db if db is not None else self.db

        query: Dict[str, Any] = {}

        if status:
            query["status"] = {"$in": [s.value for s in status]}
        else:
            # Default: open, assigned, in_progress
            query["status"] = {"$in": [
                TicketStatus.OPEN.value,
                TicketStatus.ASSIGNED.value,
                TicketStatus.IN_PROGRESS.value,
                TicketStatus.AWAITING_RESPONSE.value,
                TicketStatus.ESCALATED.value
            ]}

        if priority:
            query["priority"] = priority.value

        cursor = db.tickets.find(query).sort([
            ("priority", -1),
            ("created_at", 1)
        ]).limit(limit)

        tickets = []
        async for doc in cursor:
            tickets.append(Ticket.from_mongo(doc))

        return tickets

    # =========================================================================
    # TICKET ASSIGNMENT
    # =========================================================================

    async def assign_ticket(
        self,
        ticket_id: str,
        request: AssignTicketRequest,
        assigner: User,
        db: AsyncIOMotorDatabase = None
    ) -> Ticket:
        """Assign ticket to an analyst"""
        db = db if db is not None else self.db

        # Get ticket
        ticket = await self.get_ticket(ticket_id, db)
        if not ticket:
            raise ValueError(f"Ticket {ticket_id} not found")

        # Validate assigner has permission
        if assigner.role not in [UserRole.ANALYST, UserRole.AUTHORITY, UserRole.AUTHORITY_ADMIN]:
            raise ValueError("Only analysts, authorities, or admins can assign tickets")

        # Get analyst user
        analyst_doc = await db.users.find_one({"user_id": request.analyst_id})
        if not analyst_doc:
            raise ValueError(f"Analyst {request.analyst_id} not found")

        analyst = User.from_mongo(analyst_doc)
        if analyst.role not in [UserRole.ANALYST, UserRole.AUTHORITY, UserRole.AUTHORITY_ADMIN]:
            raise ValueError("Can only assign to analysts or authorities")

        now = datetime.now(timezone.utc)
        previous_analyst_id = ticket.assigned_analyst_id
        previous_analyst_name = ticket.assigned_analyst_name

        # Update ticket
        update_data = {
            "assigned_analyst_id": analyst.user_id,
            "assigned_analyst_name": self._get_user_name(analyst),
            "status": TicketStatus.ASSIGNED.value,
            "updated_at": now
        }

        await db.tickets.update_one({"ticket_id": ticket_id}, {"$set": update_data})

        # Sync status to hazard report
        await self._sync_ticket_status_to_report(ticket.report_id, TicketStatus.ASSIGNED, db)

        # Log activity
        activity_type = ActivityType.TICKET_REASSIGNED if previous_analyst_id else ActivityType.TICKET_ASSIGNED
        await self._log_activity(
            ticket_id=ticket_id,
            activity_type=activity_type,
            performed_by=assigner,
            description=f"Ticket assigned to {self._get_user_name(analyst)}",
            details={"analyst_id": analyst.user_id, "analyst_name": self._get_user_name(analyst)},
            previous_value=previous_analyst_name,
            new_value=self._get_user_name(analyst),
            db=db
        )

        # Add assignment message
        message = TicketMessage(
            message_id=self._generate_message_id(),
            ticket_id=ticket_id,
            sender_id="SYSTEM",
            sender_name="System",
            sender_role="system",
            message_type=MessageType.ASSIGNMENT,
            content=f"Ticket assigned to {self._get_user_name(analyst)}",
            is_internal=False
        )
        await db.ticket_messages.insert_one(message.model_dump())

        # Add custom message if provided
        if request.message:
            custom_msg = TicketMessage(
                message_id=self._generate_message_id(),
                ticket_id=ticket_id,
                sender_id=assigner.user_id,
                sender_name=self._get_user_name(assigner),
                sender_role=assigner.role.value,
                message_type=MessageType.TEXT,
                content=request.message,
                is_internal=True  # Assignment messages are internal
            )
            await db.ticket_messages.insert_one(custom_msg.model_dump())

        # Notify assigned analyst
        await self._create_ticket_notification(
            user_id=analyst.user_id,
            notification_type=NotificationType.TICKET_ASSIGNED,
            severity=NotificationSeverity.HIGH,
            title="Ticket Assigned to You",
            message=f"You have been assigned ticket {ticket_id}: {ticket.title}",
            ticket_id=ticket_id,
            report_id=ticket.report_id,
            metadata={"priority": ticket.priority.value},
            db=db
        )

        # Notify reporter that their ticket is being worked on
        await self._create_ticket_notification(
            user_id=ticket.reporter_id,
            notification_type=NotificationType.TICKET_STATUS,
            severity=NotificationSeverity.INFO,
            title="Ticket Assigned",
            message=f"An analyst has been assigned to your ticket: {ticket.title}",
            ticket_id=ticket_id,
            report_id=ticket.report_id,
            db=db
        )

        logger.info(f"Assigned ticket {ticket_id} to analyst {analyst.user_id}")
        return await self.get_ticket(ticket_id, db)

    async def assign_to_authority(
        self,
        ticket_id: str,
        authority_id: str,
        assigner: User,
        message: Optional[str] = None,
        db: AsyncIOMotorDatabase = None
    ) -> Ticket:
        """
        Assign ticket to a specific authority.

        This makes the ticket visible in that authority's ticket list.
        Can be called by analysts or other authorities.
        """
        db = db if db is not None else self.db

        # Get ticket
        ticket = await self.get_ticket(ticket_id, db)
        if not ticket:
            raise ValueError(f"Ticket {ticket_id} not found")

        # Validate assigner has permission (analyst or authority)
        if assigner.role not in [UserRole.ANALYST, UserRole.AUTHORITY, UserRole.AUTHORITY_ADMIN]:
            raise ValueError("Only analysts or authorities can assign tickets to authorities")

        # Get authority user
        authority_doc = await db.users.find_one({"user_id": authority_id})
        if not authority_doc:
            raise ValueError(f"Authority user {authority_id} not found")

        authority = User.from_mongo(authority_doc)
        if authority.role not in [UserRole.AUTHORITY, UserRole.AUTHORITY_ADMIN]:
            raise ValueError("Target user must be an authority")

        now = datetime.now(timezone.utc)
        previous_authority_id = ticket.assigned_authority_id
        previous_authority_name = ticket.assigned_authority_name

        # Update ticket with assigned authority
        update_data = {
            "assigned_authority_id": authority.user_id,
            "assigned_authority_name": self._get_user_name(authority),
            "updated_at": now
        }

        # Also update authority_id if it's PENDING_ASSIGNMENT
        if ticket.authority_id == "PENDING_ASSIGNMENT":
            update_data["authority_id"] = authority.user_id
            update_data["authority_name"] = self._get_user_name(authority)

        await db.tickets.update_one({"ticket_id": ticket_id}, {"$set": update_data})

        # Log activity
        activity_type = ActivityType.TICKET_REASSIGNED if previous_authority_id else ActivityType.TICKET_ASSIGNED
        await self._log_activity(
            ticket_id=ticket_id,
            activity_type=activity_type,
            performed_by=assigner,
            description=f"Ticket assigned to authority {self._get_user_name(authority)}",
            details={"authority_id": authority.user_id, "authority_name": self._get_user_name(authority)},
            previous_value=previous_authority_name,
            new_value=self._get_user_name(authority),
            db=db
        )

        # Add assignment message
        msg = TicketMessage(
            message_id=self._generate_message_id(),
            ticket_id=ticket_id,
            sender_id="SYSTEM",
            sender_name="System",
            sender_role="system",
            message_type=MessageType.ASSIGNMENT,
            content=f"Ticket assigned to authority: {self._get_user_name(authority)}",
            is_internal=False
        )
        await db.ticket_messages.insert_one(msg.model_dump())

        # Add custom message if provided
        if message:
            custom_msg = TicketMessage(
                message_id=self._generate_message_id(),
                ticket_id=ticket_id,
                sender_id=assigner.user_id,
                sender_name=self._get_user_name(assigner),
                sender_role=assigner.role.value,
                message_type=MessageType.TEXT,
                content=message,
                is_internal=True  # Assignment notes are internal
            )
            await db.ticket_messages.insert_one(custom_msg.model_dump())

        # Notify assigned authority
        await self._create_ticket_notification(
            user_id=authority.user_id,
            notification_type=NotificationType.TICKET_ASSIGNED,
            severity=NotificationSeverity.HIGH,
            title="Ticket Assigned to You",
            message=f"A ticket has been assigned to you: {ticket.title}",
            ticket_id=ticket_id,
            report_id=ticket.report_id,
            metadata={"priority": ticket.priority.value, "assigned_by": self._get_user_name(assigner)},
            db=db
        )

        logger.info(f"Assigned ticket {ticket_id} to authority {authority.user_id} by {assigner.user_id}")
        return await self.get_ticket(ticket_id, db)

    # =========================================================================
    # STATUS MANAGEMENT
    # =========================================================================

    async def update_status(
        self,
        ticket_id: str,
        new_status: TicketStatus,
        user: User,
        notes: Optional[str] = None,
        db: AsyncIOMotorDatabase = None
    ) -> Ticket:
        """Update ticket status"""
        db = db if db is not None else self.db

        ticket = await self.get_ticket(ticket_id, db)
        if not ticket:
            raise ValueError(f"Ticket {ticket_id} not found")

        # Validate status transition
        valid_transitions = self._get_valid_status_transitions(ticket.status)
        if new_status not in valid_transitions:
            raise ValueError(
                f"Invalid status transition from {ticket.status.value} to {new_status.value}. "
                f"Valid transitions: {[s.value for s in valid_transitions]}"
            )

        now = datetime.now(timezone.utc)
        previous_status = ticket.status

        update_data = {
            "status": new_status.value,
            "updated_at": now
        }

        # Handle specific status changes
        if new_status == TicketStatus.IN_PROGRESS and not ticket.first_response_at:
            update_data["first_response_at"] = now

        await db.tickets.update_one({"ticket_id": ticket_id}, {"$set": update_data})

        # Sync status to hazard report
        await self._sync_ticket_status_to_report(ticket.report_id, new_status, db)

        # Log activity
        await self._log_activity(
            ticket_id=ticket_id,
            activity_type=ActivityType.STATUS_CHANGED,
            performed_by=user,
            description=f"Status changed from {previous_status.value} to {new_status.value}",
            details={"notes": notes} if notes else {},
            previous_value=previous_status.value,
            new_value=new_status.value,
            db=db
        )

        # Add status update message
        message = TicketMessage(
            message_id=self._generate_message_id(),
            ticket_id=ticket_id,
            sender_id="SYSTEM",
            sender_name="System",
            sender_role="system",
            message_type=MessageType.STATUS_UPDATE,
            content=f"Status changed to {new_status.value.replace('_', ' ').title()}",
            is_internal=False
        )
        await db.ticket_messages.insert_one(message.model_dump())

        logger.info(f"Updated ticket {ticket_id} status to {new_status.value}")
        return await self.get_ticket(ticket_id, db)

    async def _sync_ticket_status_to_report(
        self,
        report_id: str,
        new_status: TicketStatus,
        db: AsyncIOMotorDatabase,
        ticket_id: Optional[str] = None,
        additional_data: Optional[Dict[str, Any]] = None
    ):
        """
        Sync ticket status back to hazard report (V2: full sync on all transitions).

        This method is called on ALL status changes to ensure report and ticket
        are always in sync.

        Args:
            report_id: The report ID to update
            new_status: The new ticket status
            db: Database connection
            ticket_id: Optional ticket ID (for initial sync)
            additional_data: Optional additional fields to sync
        """
        now = datetime.now(timezone.utc)

        update_data = {
            "ticket_status": new_status.value,
            "updated_at": now
        }

        # Add ticket_id if provided (for initial ticket creation)
        if ticket_id:
            update_data["ticket_id"] = ticket_id
            update_data["has_ticket"] = True
            update_data["ticket_creation_status"] = TicketCreationStatus.CREATED.value

        # Sync resolution/closure timestamps
        if new_status == TicketStatus.RESOLVED:
            update_data["ticket_resolved_at"] = now
        elif new_status == TicketStatus.CLOSED:
            update_data["ticket_closed_at"] = now
        elif new_status == TicketStatus.REOPENED:
            # Clear resolution/closure data when reopened
            update_data["ticket_resolved_at"] = None
            update_data["ticket_closed_at"] = None

        # Merge any additional data
        if additional_data:
            update_data.update(additional_data)

        await db.hazard_reports.update_one(
            {"report_id": report_id},
            {"$set": update_data}
        )

        logger.debug(f"Synced ticket status '{new_status.value}' to report {report_id}")

    def _get_valid_status_transitions(self, current: TicketStatus) -> List[TicketStatus]:
        """Get valid status transitions from current status"""
        transitions = {
            TicketStatus.OPEN: [TicketStatus.ASSIGNED, TicketStatus.IN_PROGRESS, TicketStatus.ESCALATED],
            TicketStatus.ASSIGNED: [TicketStatus.IN_PROGRESS, TicketStatus.AWAITING_RESPONSE, TicketStatus.ESCALATED],
            TicketStatus.IN_PROGRESS: [TicketStatus.AWAITING_RESPONSE, TicketStatus.RESOLVED, TicketStatus.ESCALATED],
            TicketStatus.AWAITING_RESPONSE: [TicketStatus.IN_PROGRESS, TicketStatus.RESOLVED, TicketStatus.ESCALATED],
            TicketStatus.ESCALATED: [TicketStatus.IN_PROGRESS, TicketStatus.RESOLVED],
            TicketStatus.RESOLVED: [TicketStatus.CLOSED, TicketStatus.REOPENED],
            TicketStatus.CLOSED: [TicketStatus.REOPENED],
            TicketStatus.REOPENED: [TicketStatus.IN_PROGRESS, TicketStatus.RESOLVED]
        }
        return transitions.get(current, [])

    # =========================================================================
    # PRIORITY MANAGEMENT
    # =========================================================================

    async def update_priority(
        self,
        ticket_id: str,
        new_priority: TicketPriority,
        user: User,
        reason: str,
        db: AsyncIOMotorDatabase = None
    ) -> Ticket:
        """Update ticket priority"""
        db = db if db is not None else self.db

        ticket = await self.get_ticket(ticket_id, db)
        if not ticket:
            raise ValueError(f"Ticket {ticket_id} not found")

        # Validate user can change priority
        if user.role not in [UserRole.ANALYST, UserRole.AUTHORITY, UserRole.AUTHORITY_ADMIN]:
            raise ValueError("Only analysts, authorities, or admins can change priority")

        now = datetime.now(timezone.utc)
        previous_priority = ticket.priority

        # Recalculate SLA deadlines based on new priority
        new_sla = calculate_sla_deadlines(new_priority, ticket.created_at)

        update_data = {
            "priority": new_priority.value,
            "response_due": new_sla["response_due"],
            "resolution_due": new_sla["resolution_due"],
            "updated_at": now
        }

        await db.tickets.update_one({"ticket_id": ticket_id}, {"$set": update_data})

        # Log activity
        await self._log_activity(
            ticket_id=ticket_id,
            activity_type=ActivityType.PRIORITY_CHANGED,
            performed_by=user,
            description=f"Priority changed from {previous_priority.value} to {new_priority.value}",
            details={"reason": reason},
            previous_value=previous_priority.value,
            new_value=new_priority.value,
            db=db
        )

        # Add priority change message
        message = TicketMessage(
            message_id=self._generate_message_id(),
            ticket_id=ticket_id,
            sender_id=user.user_id,
            sender_name=self._get_user_name(user),
            sender_role=user.role.value,
            message_type=MessageType.STATUS_UPDATE,
            content=f"Priority changed to {new_priority.value.upper()}: {reason}",
            is_internal=False
        )
        await db.ticket_messages.insert_one(message.model_dump())

        logger.info(f"Updated ticket {ticket_id} priority to {new_priority.value}")
        return await self.get_ticket(ticket_id, db)

    # =========================================================================
    # ESCALATION
    # =========================================================================

    async def escalate_ticket(
        self,
        ticket_id: str,
        request: EscalateTicketRequest,
        user: User,
        db: AsyncIOMotorDatabase = None
    ) -> Ticket:
        """Escalate ticket to higher authority"""
        db = db if db is not None else self.db

        ticket = await self.get_ticket(ticket_id, db)
        if not ticket:
            raise ValueError(f"Ticket {ticket_id} not found")

        # Validate user can escalate
        if user.role == UserRole.CITIZEN:
            # Citizens can request escalation on their own tickets
            if ticket.reporter_id != user.user_id:
                raise ValueError("Citizens can only escalate their own tickets")

        now = datetime.now(timezone.utc)

        # Determine escalation target
        escalate_to_id = request.escalate_to_id
        escalate_to_name = "Senior Authority"

        if escalate_to_id:
            target_doc = await db.users.find_one({"user_id": escalate_to_id})
            if target_doc:
                target = User.from_mongo(target_doc)
                escalate_to_name = self._get_user_name(target)

        # Store previous state
        previous_priority = ticket.priority
        previous_status = ticket.status
        previous_assignee_id = ticket.assigned_analyst_id
        previous_assignee_name = ticket.assigned_analyst_name

        # Update ticket
        update_data = {
            "is_escalated": True,
            "escalated_to_id": escalate_to_id,
            "escalated_to_name": escalate_to_name,
            "escalation_reason": request.reason,
            "escalation_count": ticket.escalation_count + 1,
            "status": TicketStatus.ESCALATED.value,
            "priority": request.suggested_priority.value,
            "updated_at": now
        }

        # Recalculate SLA for new priority
        new_sla = calculate_sla_deadlines(request.suggested_priority, now)
        update_data["response_due"] = new_sla["response_due"]
        update_data["resolution_due"] = new_sla["resolution_due"]

        await db.tickets.update_one({"ticket_id": ticket_id}, {"$set": update_data})

        # Sync status to hazard report
        await self._sync_ticket_status_to_report(ticket.report_id, TicketStatus.ESCALATED, db)

        # Create escalation record
        escalation = Escalation(
            escalation_id=f"ESC-{uuid.uuid4().hex[:12].upper()}",
            ticket_id=ticket_id,
            escalated_by_id=user.user_id,
            escalated_by_name=self._get_user_name(user),
            escalated_by_role=user.role.value,
            escalated_to_id=escalate_to_id or "SENIOR_AUTHORITY",
            escalated_to_name=escalate_to_name,
            reason=request.reason,
            previous_priority=previous_priority,
            previous_status=previous_status,
            previous_assignee_id=previous_assignee_id,
            previous_assignee_name=previous_assignee_name,
            new_priority=request.suggested_priority,
            new_status=TicketStatus.ESCALATED
        )
        await db.ticket_escalations.insert_one(escalation.model_dump())

        # Log activity
        await self._log_activity(
            ticket_id=ticket_id,
            activity_type=ActivityType.ESCALATED,
            performed_by=user,
            description=f"Ticket escalated: {request.reason}",
            details={
                "escalated_to": escalate_to_name,
                "reason": request.reason,
                "new_priority": request.suggested_priority.value
            },
            previous_value=previous_status.value,
            new_value=TicketStatus.ESCALATED.value,
            db=db
        )

        # Add escalation message
        message = TicketMessage(
            message_id=self._generate_message_id(),
            ticket_id=ticket_id,
            sender_id=user.user_id,
            sender_name=self._get_user_name(user),
            sender_role=user.role.value,
            message_type=MessageType.ESCALATION,
            content=f"⚠️ ESCALATED: {request.reason}",
            is_internal=False
        )
        await db.ticket_messages.insert_one(message.model_dump())

        # Notify all participants about escalation
        updated_ticket = await self.get_ticket(ticket_id, db)
        await self._notify_ticket_participants(
            ticket=updated_ticket,
            notification_type=NotificationType.TICKET_ESCALATED,
            severity=NotificationSeverity.HIGH,
            title="Ticket Escalated",
            message=f"Ticket {ticket_id} has been escalated: {request.reason}",
            exclude_user_id=user.user_id,
            metadata={
                "reason": request.reason,
                "new_priority": request.suggested_priority.value
            },
            db=db
        )

        # Specifically notify escalation target
        if escalate_to_id:
            await self._create_ticket_notification(
                user_id=escalate_to_id,
                notification_type=NotificationType.TICKET_ESCALATED,
                severity=NotificationSeverity.CRITICAL,
                title="Escalated Ticket Needs Attention",
                message=f"A ticket has been escalated to you: {ticket.title}",
                ticket_id=ticket_id,
                report_id=ticket.report_id,
                metadata={"reason": request.reason},
                db=db
            )

        logger.info(f"Escalated ticket {ticket_id} by {user.user_id}")
        return updated_ticket

    # =========================================================================
    # RESOLUTION & CLOSURE
    # =========================================================================

    async def resolve_ticket(
        self,
        ticket_id: str,
        request: ResolveTicketRequest,
        user: User,
        db: AsyncIOMotorDatabase = None
    ) -> Ticket:
        """Resolve a ticket"""
        db = db if db is not None else self.db

        ticket = await self.get_ticket(ticket_id, db)
        if not ticket:
            raise ValueError(f"Ticket {ticket_id} not found")

        # Validate user can resolve
        if user.role not in [UserRole.ANALYST, UserRole.AUTHORITY, UserRole.AUTHORITY_ADMIN]:
            raise ValueError("Only analysts, authorities, or admins can resolve tickets")

        now = datetime.now(timezone.utc)

        update_data = {
            "status": TicketStatus.RESOLVED.value,
            "resolution_notes": request.resolution_notes,
            "actions_taken": request.actions_taken,
            "resolved_at": now,
            "resolved_by_id": user.user_id,
            "resolved_by_name": self._get_user_name(user),
            "updated_at": now
        }

        await db.tickets.update_one({"ticket_id": ticket_id}, {"$set": update_data})

        # Sync status to hazard report
        await self._sync_ticket_status_to_report(ticket.report_id, TicketStatus.RESOLVED, db)

        # Log activity
        await self._log_activity(
            ticket_id=ticket_id,
            activity_type=ActivityType.RESOLVED,
            performed_by=user,
            description="Ticket resolved",
            details={
                "resolution_notes": request.resolution_notes,
                "actions_taken": request.actions_taken
            },
            db=db
        )

        # Add resolution message
        actions_text = "\n".join([f"• {action}" for action in request.actions_taken])
        message = TicketMessage(
            message_id=self._generate_message_id(),
            ticket_id=ticket_id,
            sender_id=user.user_id,
            sender_name=self._get_user_name(user),
            sender_role=user.role.value,
            message_type=MessageType.RESOLUTION,
            content=f"✅ RESOLVED\n\n{request.resolution_notes}\n\nActions Taken:\n{actions_text}",
            is_internal=False
        )
        await db.ticket_messages.insert_one(message.model_dump())

        # Notify reporter that their issue has been resolved
        await self._create_ticket_notification(
            user_id=ticket.reporter_id,
            notification_type=NotificationType.TICKET_RESOLVED,
            severity=NotificationSeverity.MEDIUM,
            title="Issue Resolved",
            message=f"Your hazard report ticket has been resolved: {ticket.title}",
            ticket_id=ticket_id,
            report_id=ticket.report_id,
            metadata={"resolution_notes": request.resolution_notes},
            db=db
        )

        logger.info(f"Resolved ticket {ticket_id}")
        return await self.get_ticket(ticket_id, db)

    async def close_ticket(
        self,
        ticket_id: str,
        user: User,
        reason: Optional[str] = None,
        db: AsyncIOMotorDatabase = None
    ) -> Ticket:
        """Close a resolved ticket"""
        db = db if db is not None else self.db

        ticket = await self.get_ticket(ticket_id, db)
        if not ticket:
            raise ValueError(f"Ticket {ticket_id} not found")

        # Only resolved tickets can be closed
        if ticket.status != TicketStatus.RESOLVED:
            raise ValueError("Only resolved tickets can be closed")

        # Validate user can close
        if user.role not in [UserRole.AUTHORITY, UserRole.AUTHORITY_ADMIN]:
            raise ValueError("Only authorities or admins can close tickets")

        now = datetime.now(timezone.utc)

        update_data = {
            "status": TicketStatus.CLOSED.value,
            "closed_at": now,
            "closed_by_id": user.user_id,
            "closed_by_name": self._get_user_name(user),
            "closure_reason": reason,
            "updated_at": now
        }

        await db.tickets.update_one({"ticket_id": ticket_id}, {"$set": update_data})

        # Sync status to hazard report
        await self._sync_ticket_status_to_report(ticket.report_id, TicketStatus.CLOSED, db)

        # Log activity
        await self._log_activity(
            ticket_id=ticket_id,
            activity_type=ActivityType.CLOSED,
            performed_by=user,
            description="Ticket closed",
            details={"reason": reason} if reason else {},
            db=db
        )

        # Notify reporter that the ticket is closed
        await self._create_ticket_notification(
            user_id=ticket.reporter_id,
            notification_type=NotificationType.TICKET_CLOSED,
            severity=NotificationSeverity.INFO,
            title="Ticket Closed",
            message=f"Your support ticket has been closed: {ticket.title}",
            ticket_id=ticket_id,
            report_id=ticket.report_id,
            metadata={"closure_reason": reason} if reason else {},
            db=db
        )

        logger.info(f"Closed ticket {ticket_id}")
        return await self.get_ticket(ticket_id, db)

    async def reopen_ticket(
        self,
        ticket_id: str,
        user: User,
        reason: str,
        db: AsyncIOMotorDatabase = None
    ) -> Ticket:
        """Reopen a closed or resolved ticket"""
        db = db if db is not None else self.db

        ticket = await self.get_ticket(ticket_id, db)
        if not ticket:
            raise ValueError(f"Ticket {ticket_id} not found")

        # Only resolved or closed tickets can be reopened
        if ticket.status not in [TicketStatus.RESOLVED, TicketStatus.CLOSED]:
            raise ValueError("Only resolved or closed tickets can be reopened")

        now = datetime.now(timezone.utc)

        # Recalculate SLA from now
        new_sla = calculate_sla_deadlines(ticket.priority, now)

        update_data = {
            "status": TicketStatus.REOPENED.value,
            "response_due": new_sla["response_due"],
            "resolution_due": new_sla["resolution_due"],
            "resolved_at": None,
            "resolved_by_id": None,
            "resolved_by_name": None,
            "closed_at": None,
            "closed_by_id": None,
            "closed_by_name": None,
            "updated_at": now
        }

        await db.tickets.update_one({"ticket_id": ticket_id}, {"$set": update_data})

        # Sync status to hazard report
        await self._sync_ticket_status_to_report(ticket.report_id, TicketStatus.REOPENED, db)

        # Log activity
        await self._log_activity(
            ticket_id=ticket_id,
            activity_type=ActivityType.REOPENED,
            performed_by=user,
            description=f"Ticket reopened: {reason}",
            details={"reason": reason},
            db=db
        )

        # Add reopen message
        message = TicketMessage(
            message_id=self._generate_message_id(),
            ticket_id=ticket_id,
            sender_id=user.user_id,
            sender_name=self._get_user_name(user),
            sender_role=user.role.value,
            message_type=MessageType.STATUS_UPDATE,
            content=f"🔄 Ticket Reopened: {reason}",
            is_internal=False
        )
        await db.ticket_messages.insert_one(message.model_dump())

        logger.info(f"Reopened ticket {ticket_id}")
        return await self.get_ticket(ticket_id, db)

    # =========================================================================
    # MESSAGING
    # =========================================================================

    async def send_message(
        self,
        ticket_id: str,
        request: SendMessageRequest,
        user: User,
        db: AsyncIOMotorDatabase = None
    ) -> TicketMessage:
        """
        Send a message in a ticket (V2: with thread support).

        The thread parameter controls who can see the message:
        - "all": Everyone (reporter, analyst, authority)
        - "ra": Reporter-Analyst private conversation
        - "aa": Analyst-Authority private conversation
        - "internal": Internal notes (analyst + authority only)
        """
        db = db if db is not None else self.db

        ticket = await self.get_ticket(ticket_id, db)
        if not ticket:
            raise ValueError(f"Ticket {ticket_id} not found")

        # Validate user can send message
        can_access = self._user_can_access_ticket(user, ticket)
        if not can_access:
            raise ValueError("User does not have access to this ticket")

        # V2: Determine thread from request or default based on role and is_internal
        thread = getattr(request, 'thread', None) or "all"

        # Validate thread access
        allowed_threads = self._get_allowed_threads_for_user(user, ticket)
        if thread not in allowed_threads:
            raise ValueError(f"User does not have permission to send to thread '{thread}'")

        # Legacy compatibility: Citizens cannot send internal messages
        if request.is_internal and user.role == UserRole.CITIZEN:
            raise ValueError("Citizens cannot send internal messages")

        # If is_internal is True, override thread to "internal"
        if request.is_internal:
            thread = "internal"

        now = datetime.now(timezone.utc)

        # V2: Compute visible_to list based on thread
        visible_to = self._compute_visible_to_for_thread(thread, ticket)

        message = TicketMessage(
            message_id=self._generate_message_id(),
            ticket_id=ticket_id,
            sender_id=user.user_id,
            sender_name=self._get_user_name(user),
            sender_role=user.role.value,
            message_type=MessageType.TEXT,
            content=request.content,
            is_internal=request.is_internal or thread == "internal",
            reply_to_message_id=request.reply_to_message_id,
            thread=thread,
            visible_to=visible_to,
            created_at=now
        )

        await db.ticket_messages.insert_one(message.model_dump())

        # Update ticket with message count and last message info
        update_data = {
            "total_messages": ticket.total_messages + 1,
            "last_message_at": now,
            "last_message_by": user.user_id,
            "updated_at": now
        }

        # Update unread counts for other participants
        if user.role == UserRole.CITIZEN:
            update_data["unread_count_analyst"] = ticket.unread_count_analyst + 1
            update_data["unread_count_authority"] = ticket.unread_count_authority + 1
        elif user.role == UserRole.ANALYST:
            if not request.is_internal:
                update_data["unread_count_reporter"] = ticket.unread_count_reporter + 1
            update_data["unread_count_authority"] = ticket.unread_count_authority + 1
        elif user.role == UserRole.AUTHORITY:
            if not request.is_internal:
                update_data["unread_count_reporter"] = ticket.unread_count_reporter + 1
            update_data["unread_count_analyst"] = ticket.unread_count_analyst + 1

        # If this is first response from analyst/authority, update first_response_at
        if not ticket.first_response_at and user.role in [UserRole.ANALYST, UserRole.AUTHORITY]:
            update_data["first_response_at"] = now
            # Also update status to IN_PROGRESS if it was ASSIGNED
            if ticket.status == TicketStatus.ASSIGNED:
                update_data["status"] = TicketStatus.IN_PROGRESS.value

        await db.tickets.update_one({"ticket_id": ticket_id}, {"$set": update_data})

        # Log activity
        await self._log_activity(
            ticket_id=ticket_id,
            activity_type=ActivityType.MESSAGE_ADDED,
            performed_by=user,
            description="Message added",
            details={"is_internal": request.is_internal},
            db=db
        )

        # Send notifications for new messages (only for non-internal messages)
        if not request.is_internal:
            sender_name = self._get_user_name(user)

            # Notify all participants except the sender
            await self._notify_ticket_participants(
                ticket=ticket,
                notification_type=NotificationType.TICKET_MESSAGE,
                severity=NotificationSeverity.INFO,
                title="New Ticket Message",
                message=f"{sender_name} sent a message: {request.content[:100]}{'...' if len(request.content) > 100 else ''}",
                exclude_user_id=user.user_id,
                metadata={"sender_name": sender_name, "sender_role": user.role.value},
                db=db
            )

        return message

    async def get_messages(
        self,
        ticket_id: str,
        user: User,
        limit: int = 100,
        before_message_id: Optional[str] = None,
        thread: Optional[str] = None,
        db: AsyncIOMotorDatabase = None
    ) -> List[TicketMessage]:
        """
        Get messages for a ticket with V2 thread filtering.

        Args:
            ticket_id: The ticket ID
            user: The requesting user
            limit: Maximum number of messages to return
            before_message_id: For pagination - return messages before this ID
            thread: V2 filter - "all", "ra" (reporter-analyst), "aa" (analyst-authority), "internal"
            db: Database connection

        Returns:
            List of TicketMessage visible to the user
        """
        db = db if db is not None else self.db

        ticket = await self.get_ticket(ticket_id, db)
        if not ticket:
            raise ValueError(f"Ticket {ticket_id} not found")

        # Validate user can access
        can_access = self._user_can_access_ticket(user, ticket)
        if not can_access:
            raise ValueError("User does not have access to this ticket")

        query: Dict[str, Any] = {"ticket_id": ticket_id}

        # V2: Thread-based filtering
        if thread:
            # Validate thread access based on user role
            allowed_threads = self._get_allowed_threads_for_user(user, ticket)
            if thread not in allowed_threads:
                raise ValueError(f"User does not have access to thread '{thread}'")
            query["thread"] = thread
        else:
            # No thread specified - show messages user can see based on role
            allowed_threads = self._get_allowed_threads_for_user(user, ticket)
            query["$or"] = [
                {"thread": {"$in": allowed_threads}},
                {"thread": {"$exists": False}},  # Legacy messages without thread field
                {"thread": None}
            ]

        # Legacy: Citizens cannot see internal messages
        if user.role == UserRole.CITIZEN:
            query["is_internal"] = False
            # Also filter out internal thread
            if "$or" in query:
                # Already handled by thread filtering
                pass

        # Pagination
        if before_message_id:
            before_msg = await db.ticket_messages.find_one({"message_id": before_message_id})
            if before_msg:
                query["created_at"] = {"$lt": before_msg["created_at"]}

        cursor = db.ticket_messages.find(query).sort("created_at", 1).limit(limit)

        messages = []
        async for doc in cursor:
            messages.append(TicketMessage(**doc))

        # Mark as read for this user
        await self._mark_messages_read(ticket_id, user, db)

        return messages

    def _get_allowed_threads_for_user(self, user: User, ticket: Ticket) -> List[str]:
        """
        V2: Get list of threads a user can access based on their role.

        Thread visibility:
        - "all": Everyone (reporter, analyst, authority)
        - "ra": Reporter and Analyst only
        - "aa": Analyst and Authority only
        - "internal": Analyst and Authority only (hidden from reporter)
        """
        if user.role == UserRole.CITIZEN:
            # Citizens can only see 'all' and 'ra' threads
            return ["all", "ra"]
        elif user.role == UserRole.ANALYST:
            # Analysts can see all threads
            return ["all", "ra", "aa", "internal"]
        elif user.role in [UserRole.AUTHORITY, UserRole.AUTHORITY_ADMIN]:
            # Authorities can see 'all', 'aa', and 'internal' threads
            return ["all", "aa", "internal"]
        else:
            # Unknown role - only public messages
            return ["all"]

    def _compute_visible_to_for_thread(self, thread: str, ticket: Ticket) -> List[str]:
        """
        V2: Compute the list of user IDs who can see a message based on thread.

        Returns empty list for 'all' thread (everyone can see).
        Returns specific user IDs for private threads.
        """
        if thread == "all":
            # Empty list means everyone can see
            return []
        elif thread == "ra":
            # Reporter and Analyst only
            visible = [ticket.reporter_id]
            if ticket.assigned_analyst_id:
                visible.append(ticket.assigned_analyst_id)
            return visible
        elif thread == "aa":
            # Analyst and Authority only
            visible = []
            if ticket.assigned_analyst_id:
                visible.append(ticket.assigned_analyst_id)
            if ticket.authority_id:
                visible.append(ticket.authority_id)
            if ticket.assigned_authority_id and ticket.assigned_authority_id not in visible:
                visible.append(ticket.assigned_authority_id)
            return visible
        elif thread == "internal":
            # Same as aa - analyst and authority
            visible = []
            if ticket.assigned_analyst_id:
                visible.append(ticket.assigned_analyst_id)
            if ticket.authority_id:
                visible.append(ticket.authority_id)
            if ticket.assigned_authority_id and ticket.assigned_authority_id not in visible:
                visible.append(ticket.assigned_authority_id)
            return visible
        else:
            # Unknown thread - default to all
            return []

    async def _mark_messages_read(
        self,
        ticket_id: str,
        user: User,
        db: AsyncIOMotorDatabase
    ):
        """Mark messages as read for a user"""
        update_field = None
        if user.role == UserRole.CITIZEN:
            update_field = "unread_count_reporter"
        elif user.role == UserRole.ANALYST:
            update_field = "unread_count_analyst"
        elif user.role in [UserRole.AUTHORITY, UserRole.AUTHORITY_ADMIN]:
            update_field = "unread_count_authority"

        if update_field:
            await db.tickets.update_one(
                {"ticket_id": ticket_id},
                {"$set": {update_field: 0}}
            )

    def _user_can_access_ticket(self, user: User, ticket: Ticket) -> bool:
        """Check if user can access a ticket"""
        if user.role == UserRole.AUTHORITY_ADMIN:
            return True
        if user.role == UserRole.CITIZEN:
            return ticket.reporter_id == user.user_id
        if user.role == UserRole.ANALYST:
            return (
                ticket.assigned_analyst_id == user.user_id or
                ticket.status == TicketStatus.OPEN
            )
        if user.role == UserRole.AUTHORITY:
            # Check all the ways an authority can have access to a ticket:
            # 1. They are the assigned authority (analyst assigned this ticket to them)
            if ticket.assigned_authority_id == user.user_id:
                return True
            # 2. They created the ticket (authority_id) and it's not pending
            if ticket.authority_id == user.user_id and ticket.authority_id != "PENDING_ASSIGNMENT":
                return True
            # 3. They are the escalation target
            if ticket.escalated_to_id == user.user_id:
                return True
            # 4. They are in additional participants
            if ticket.additional_participants:
                for p in ticket.additional_participants:
                    if p.get("user_id") == user.user_id and p.get("is_active", True):
                        return True
            # 5. They approved the underlying report
            if ticket.approved_by and ticket.approved_by == user.user_id:
                return True
            return False
        return False

    # =========================================================================
    # FEEDBACK
    # =========================================================================

    async def submit_feedback(
        self,
        ticket_id: str,
        request: SubmitFeedbackRequest,
        user: User,
        db: AsyncIOMotorDatabase = None
    ) -> TicketFeedback:
        """Submit feedback for a resolved ticket"""
        db = db if db is not None else self.db

        ticket = await self.get_ticket(ticket_id, db)
        if not ticket:
            raise ValueError(f"Ticket {ticket_id} not found")

        # Only reporter can submit feedback
        if ticket.reporter_id != user.user_id:
            raise ValueError("Only the reporter can submit feedback")

        # Only resolved/closed tickets can receive feedback
        if ticket.status not in [TicketStatus.RESOLVED, TicketStatus.CLOSED]:
            raise ValueError("Feedback can only be submitted for resolved or closed tickets")

        # Check if feedback already submitted
        existing = await db.ticket_feedback.find_one({"ticket_id": ticket_id})
        if existing:
            raise ValueError("Feedback already submitted for this ticket")

        feedback = TicketFeedback(
            feedback_id=f"FB-{uuid.uuid4().hex[:12].upper()}",
            ticket_id=ticket_id,
            reporter_id=user.user_id,
            reporter_name=self._get_user_name(user),
            satisfaction_rating=request.satisfaction_rating,
            comments=request.comments,
            response_time_good=request.response_time_good,
            communication_clear=request.communication_clear,
            issue_resolved_effectively=request.issue_resolved_effectively,
            analyst_helpful=request.analyst_helpful,
            authority_action_appropriate=request.authority_action_appropriate
        )

        await db.ticket_feedback.insert_one(feedback.model_dump())

        # Update ticket
        await db.tickets.update_one(
            {"ticket_id": ticket_id},
            {"$set": {
                "feedback_received": True,
                "satisfaction_rating": request.satisfaction_rating,
                "updated_at": datetime.now(timezone.utc)
            }}
        )

        # Log activity
        await self._log_activity(
            ticket_id=ticket_id,
            activity_type=ActivityType.FEEDBACK_RECEIVED,
            performed_by=user,
            description=f"Feedback received: {request.satisfaction_rating}/5 stars",
            details={
                "rating": request.satisfaction_rating,
                "has_comments": bool(request.comments)
            },
            db=db
        )

        logger.info(f"Feedback submitted for ticket {ticket_id}: {request.satisfaction_rating}/5")
        return feedback

    # =========================================================================
    # ACTIVITY LOGGING
    # =========================================================================

    async def _log_activity(
        self,
        ticket_id: str,
        activity_type: ActivityType,
        performed_by: User,
        description: str,
        details: Dict[str, Any] = None,
        previous_value: Optional[str] = None,
        new_value: Optional[str] = None,
        db: AsyncIOMotorDatabase = None
    ):
        """Log an activity for a ticket"""
        db = db if db is not None else self.db

        activity = TicketActivity(
            activity_id=self._generate_activity_id(),
            ticket_id=ticket_id,
            activity_type=activity_type,
            performed_by_id=performed_by.user_id,
            performed_by_name=self._get_user_name(performed_by),
            performed_by_role=performed_by.role.value,
            description=description,
            details=details or {},
            previous_value=previous_value,
            new_value=new_value
        )

        await db.ticket_activities.insert_one(activity.model_dump())

    async def _create_ticket_notification(
        self,
        user_id: str,
        notification_type: NotificationType,
        severity: NotificationSeverity,
        title: str,
        message: str,
        ticket_id: str,
        report_id: str,
        action_url: Optional[str] = None,
        metadata: Dict[str, Any] = None,
        db: AsyncIOMotorDatabase = None
    ):
        """Create a ticket-related notification"""
        db = db if db is not None else self.db

        notification_id = f"NTF-{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:8].upper()}"

        notification_doc = {
            "notification_id": notification_id,
            "user_id": user_id,
            "type": notification_type.value,
            "severity": severity.value,
            "title": title,
            "message": message,
            "ticket_id": ticket_id,
            "report_id": report_id,
            "action_url": action_url or f"/tickets/{ticket_id}",
            "action_label": "View Ticket",
            "is_read": False,
            "is_dismissed": False,
            "metadata": metadata or {},
            "created_at": datetime.now(timezone.utc)
        }

        await db.notifications.insert_one(notification_doc)
        logger.debug(f"Created notification {notification_id} for user {user_id}")

    async def _notify_ticket_participants(
        self,
        ticket: Ticket,
        notification_type: NotificationType,
        severity: NotificationSeverity,
        title: str,
        message: str,
        exclude_user_id: Optional[str] = None,
        metadata: Dict[str, Any] = None,
        db: AsyncIOMotorDatabase = None
    ):
        """Send notifications to all ticket participants"""
        db = db if db is not None else self.db

        participants = set()

        # Always include reporter
        if ticket.reporter_id:
            participants.add(ticket.reporter_id)

        # Include assigned analyst
        if ticket.assigned_analyst_id:
            participants.add(ticket.assigned_analyst_id)

        # Include authority
        if ticket.authority_id:
            participants.add(ticket.authority_id)

        # Include escalation target
        if ticket.escalated_to_id:
            participants.add(ticket.escalated_to_id)

        # Remove excluded user (typically the one who triggered the action)
        if exclude_user_id:
            participants.discard(exclude_user_id)

        for user_id in participants:
            try:
                await self._create_ticket_notification(
                    user_id=user_id,
                    notification_type=notification_type,
                    severity=severity,
                    title=title,
                    message=message,
                    ticket_id=ticket.ticket_id,
                    report_id=ticket.report_id,
                    metadata=metadata,
                    db=db
                )
            except Exception as e:
                logger.error(f"Failed to create notification for user {user_id}: {e}")

    async def get_activities(
        self,
        ticket_id: str,
        limit: int = 50,
        db: AsyncIOMotorDatabase = None
    ) -> List[TicketActivity]:
        """Get activity log for a ticket"""
        db = db if db is not None else self.db

        cursor = db.ticket_activities.find(
            {"ticket_id": ticket_id}
        ).sort("created_at", -1).limit(limit)

        activities = []
        async for doc in cursor:
            activities.append(TicketActivity(**doc))

        return activities

    # =========================================================================
    # PARTICIPANT MANAGEMENT
    # =========================================================================

    async def add_participant(
        self,
        ticket_id: str,
        participant_user_id: str,
        user: User,
        notes: Optional[str] = None,
        can_message: bool = True,
        db: AsyncIOMotorDatabase = None
    ) -> Ticket:
        """Add a participant to a ticket"""
        db = db if db is not None else self.db

        ticket = await self.get_ticket(ticket_id, db)
        if not ticket:
            raise ValueError(f"Ticket {ticket_id} not found")

        # Validate user can add participants
        if user.role not in [UserRole.ANALYST, UserRole.AUTHORITY, UserRole.AUTHORITY_ADMIN]:
            raise ValueError("Only analysts, authorities, or admins can add participants")

        # Get the participant user
        participant_doc = await db.users.find_one({"user_id": participant_user_id})
        if not participant_doc:
            raise ValueError(f"User {participant_user_id} not found")

        participant = User.from_mongo(participant_doc)

        # Check if already a main participant
        main_participants = [ticket.reporter_id, ticket.assigned_analyst_id, ticket.authority_id]
        if participant_user_id in main_participants:
            raise ValueError("User is already a main participant in this ticket")

        # Check if already in additional participants
        existing_participants = ticket.additional_participants or []
        for p in existing_participants:
            if p.get("user_id") == participant_user_id and p.get("is_active", True):
                raise ValueError("User is already a participant in this ticket")

        now = datetime.now(timezone.utc)

        # Create participant record
        new_participant = {
            "user_id": participant.user_id,
            "user_name": self._get_user_name(participant),
            "user_role": participant.role.value,
            "added_by_id": user.user_id,
            "added_by_name": self._get_user_name(user),
            "added_at": now,
            "can_message": can_message,
            "is_active": True,
            "notes": notes
        }

        # Update ticket
        await db.tickets.update_one(
            {"ticket_id": ticket_id},
            {
                "$push": {"additional_participants": new_participant},
                "$set": {"updated_at": now}
            }
        )

        # Log activity
        await self._log_activity(
            ticket_id=ticket_id,
            activity_type=ActivityType.MESSAGE_ADDED,  # Using closest activity type
            performed_by=user,
            description=f"Added participant: {self._get_user_name(participant)}",
            details={
                "participant_id": participant.user_id,
                "participant_name": self._get_user_name(participant),
                "notes": notes
            },
            db=db
        )

        # Add system message about new participant
        message = TicketMessage(
            message_id=self._generate_message_id(),
            ticket_id=ticket_id,
            sender_id="SYSTEM",
            sender_name="System",
            sender_role="system",
            message_type=MessageType.SYSTEM,
            content=f"{self._get_user_name(participant)} has been added to this ticket by {self._get_user_name(user)}" +
                    (f"\nReason: {notes}" if notes else ""),
            is_internal=False
        )
        await db.ticket_messages.insert_one(message.model_dump())

        # Notify the new participant
        await self._create_ticket_notification(
            user_id=participant.user_id,
            notification_type=NotificationType.TICKET_MESSAGE,
            severity=NotificationSeverity.MEDIUM,
            title="You've Been Added to a Ticket",
            message=f"You have been added as a participant to ticket: {ticket.title}",
            ticket_id=ticket_id,
            report_id=ticket.report_id,
            metadata={"added_by": self._get_user_name(user)},
            db=db
        )

        logger.info(f"Added participant {participant.user_id} to ticket {ticket_id}")
        return await self.get_ticket(ticket_id, db)

    async def remove_participant(
        self,
        ticket_id: str,
        participant_user_id: str,
        user: User,
        db: AsyncIOMotorDatabase = None
    ) -> Ticket:
        """Remove a participant from a ticket"""
        db = db if db is not None else self.db

        ticket = await self.get_ticket(ticket_id, db)
        if not ticket:
            raise ValueError(f"Ticket {ticket_id} not found")

        # Validate user can remove participants
        if user.role not in [UserRole.ANALYST, UserRole.AUTHORITY, UserRole.AUTHORITY_ADMIN]:
            raise ValueError("Only analysts, authorities, or admins can remove participants")

        # Can't remove main participants via this method
        main_participants = [ticket.reporter_id, ticket.assigned_analyst_id, ticket.authority_id]
        if participant_user_id in main_participants:
            raise ValueError("Cannot remove main participants (reporter, analyst, authority) via this method")

        # Find and deactivate the participant
        existing_participants = ticket.additional_participants or []
        found = False
        participant_name = "Unknown"
        for p in existing_participants:
            if p.get("user_id") == participant_user_id and p.get("is_active", True):
                found = True
                participant_name = p.get("user_name", "Unknown")
                break

        if not found:
            raise ValueError("User is not an active participant in this ticket")

        now = datetime.now(timezone.utc)

        # Update the participant's is_active status
        await db.tickets.update_one(
            {"ticket_id": ticket_id, "additional_participants.user_id": participant_user_id},
            {
                "$set": {
                    "additional_participants.$.is_active": False,
                    "updated_at": now
                }
            }
        )

        # Log activity
        await self._log_activity(
            ticket_id=ticket_id,
            activity_type=ActivityType.MESSAGE_ADDED,
            performed_by=user,
            description=f"Removed participant: {participant_name}",
            details={"participant_id": participant_user_id},
            db=db
        )

        # Add system message
        message = TicketMessage(
            message_id=self._generate_message_id(),
            ticket_id=ticket_id,
            sender_id="SYSTEM",
            sender_name="System",
            sender_role="system",
            message_type=MessageType.SYSTEM,
            content=f"{participant_name} has been removed from this ticket by {self._get_user_name(user)}",
            is_internal=False
        )
        await db.ticket_messages.insert_one(message.model_dump())

        logger.info(f"Removed participant {participant_user_id} from ticket {ticket_id}")
        return await self.get_ticket(ticket_id, db)

    async def get_ticket_participants(
        self,
        ticket_id: str,
        db: AsyncIOMotorDatabase = None
    ) -> Dict[str, Any]:
        """Get all participants of a ticket"""
        db = db if db is not None else self.db

        ticket = await self.get_ticket(ticket_id, db)
        if not ticket:
            raise ValueError(f"Ticket {ticket_id} not found")

        participants = {
            "reporter": {
                "user_id": ticket.reporter_id,
                "user_name": ticket.reporter_name,
                "role": "reporter"
            },
            "assigned_analyst": None,
            "authority": {
                "user_id": ticket.authority_id,
                "user_name": ticket.authority_name,
                "role": "authority"
            },
            "additional_participants": []
        }

        if ticket.assigned_analyst_id:
            participants["assigned_analyst"] = {
                "user_id": ticket.assigned_analyst_id,
                "user_name": ticket.assigned_analyst_name,
                "role": "analyst"
            }

        # Add active additional participants
        for p in ticket.additional_participants or []:
            if p.get("is_active", True):
                participants["additional_participants"].append(p)

        return participants

    # =========================================================================
    # STATISTICS
    # =========================================================================

    async def get_statistics(
        self,
        days: int = 7,
        db: AsyncIOMotorDatabase = None
    ) -> Dict[str, Any]:
        """Get ticket statistics"""
        db = db if db is not None else self.db

        from datetime import timedelta
        end_date = datetime.now(timezone.utc)
        start_date = end_date - timedelta(days=days)

        # Aggregate statistics
        pipeline = [
            {"$match": {"created_at": {"$gte": start_date, "$lte": end_date}}},
            {"$group": {
                "_id": None,
                "total": {"$sum": 1},
                "open": {"$sum": {"$cond": [{"$eq": ["$status", "open"]}, 1, 0]}},
                "in_progress": {"$sum": {"$cond": [{"$eq": ["$status", "in_progress"]}, 1, 0]}},
                "resolved": {"$sum": {"$cond": [{"$eq": ["$status", "resolved"]}, 1, 0]}},
                "closed": {"$sum": {"$cond": [{"$eq": ["$status", "closed"]}, 1, 0]}},
                "escalated": {"$sum": {"$cond": [{"$eq": ["$status", "escalated"]}, 1, 0]}},
                "avg_satisfaction": {"$avg": "$satisfaction_rating"},
                "sla_response_breaches": {"$sum": {"$cond": ["$sla_response_breached", 1, 0]}},
                "sla_resolution_breaches": {"$sum": {"$cond": ["$sla_resolution_breached", 1, 0]}}
            }}
        ]

        result = await db.tickets.aggregate(pipeline).to_list(1)

        if result:
            stats = result[0]
            total = stats.get("total", 0)
            sla_compliance = 1.0 - (
                (stats.get("sla_response_breaches", 0) + stats.get("sla_resolution_breaches", 0)) /
                (total * 2) if total > 0 else 0
            )
        else:
            stats = {}
            total = 0
            sla_compliance = 1.0

        # Get counts by priority
        priority_pipeline = [
            {"$match": {"created_at": {"$gte": start_date, "$lte": end_date}}},
            {"$group": {"_id": "$priority", "count": {"$sum": 1}}}
        ]
        priority_result = await db.tickets.aggregate(priority_pipeline).to_list(10)
        tickets_by_priority = {item["_id"]: item["count"] for item in priority_result}

        # Get counts by status
        status_pipeline = [
            {"$match": {"created_at": {"$gte": start_date, "$lte": end_date}}},
            {"$group": {"_id": "$status", "count": {"$sum": 1}}}
        ]
        status_result = await db.tickets.aggregate(status_pipeline).to_list(10)
        tickets_by_status = {item["_id"]: item["count"] for item in status_result}

        return {
            "total_tickets": total,
            "open_tickets": stats.get("open", 0),
            "in_progress_tickets": stats.get("in_progress", 0),
            "resolved_tickets": stats.get("resolved", 0),
            "closed_tickets": stats.get("closed", 0),
            "escalated_tickets": stats.get("escalated", 0),
            "avg_response_time_hours": 0,  # Would need more calculation
            "avg_resolution_time_hours": 0,  # Would need more calculation
            "sla_compliance_rate": sla_compliance,
            "avg_satisfaction_rating": stats.get("avg_satisfaction") or 0,
            "tickets_by_priority": tickets_by_priority,
            "tickets_by_status": tickets_by_status,
            "period_start": start_date,
            "period_end": end_date
        }
