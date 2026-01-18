"""
Ticket API Routes
Endpoints for ticket management and three-way communication.
"""

import logging
from datetime import datetime, timezone
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, status, Query
from motor.motor_asyncio import AsyncIOMotorDatabase
from pydantic import BaseModel, Field

from app.database import get_database
from app.models.user import User, UserRole
from app.middleware.rbac import get_current_user, require_analyst, require_authority, require_analyst_or_authority
from app.models.ticket import (
    Ticket, TicketMessage, TicketActivity, TicketFeedback,
    TicketStatus, TicketPriority, MessageThread, AssignmentStatus,
    CreateTicketRequest, AssignTicketRequest, AssignToAuthorityRequest,
    UpdateTicketStatusRequest, UpdateTicketPriorityRequest,
    EscalateTicketRequest, ResolveTicketRequest,
    SendMessageRequest, SubmitFeedbackRequest,
    TicketListResponse, TicketDetailResponse, TicketStatsResponse
)
from app.services.ticket_service import get_ticket_service, TicketService
from app.services.escalation_service import EscalationService
from app.services.sla_service import SLAService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/tickets", tags=["Tickets"])


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

async def get_ticket_service_dep(
    db: AsyncIOMotorDatabase = Depends(get_database)
) -> TicketService:
    """Get initialized ticket service."""
    service = get_ticket_service(db)
    if not service._initialized:
        await service.initialize(db)
    return service


# =============================================================================
# PUBLIC HEALTH CHECK
# =============================================================================

@router.get("/health")
async def ticket_health():
    """
    Health check for ticket service.
    Public endpoint - no authentication required.
    """
    try:
        service = get_ticket_service()
        return {
            "status": "healthy" if service._initialized else "not_initialized",
            "initialized": service._initialized,
            "features": [
                "create_ticket",
                "assign_ticket",
                "escalate",
                "messaging",
                "feedback",
                "sla_tracking"
            ],
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }


# =============================================================================
# TICKET CREATION (Authority Only)
# =============================================================================

@router.post("", status_code=status.HTTP_201_CREATED)
async def create_ticket(
    request: CreateTicketRequest,
    current_user: User = Depends(require_authority),
    service: TicketService = Depends(get_ticket_service_dep),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Create a new ticket from a verified hazard report.

    Only authorities can create tickets.
    The hazard report must be in 'verified' status.

    Returns the created ticket and initial message.
    """
    try:
        ticket, initial_message = await service.create_ticket(
            request=request,
            authority=current_user,
            db=db
        )

        return {
            "success": True,
            "ticket_id": ticket.ticket_id,
            "ticket": ticket.model_dump(),
            "initial_message": initial_message.model_dump(),
            "message": f"Ticket created successfully for report {request.report_id}"
        }

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error creating ticket: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create ticket"
        )


# =============================================================================
# TICKET LISTING
# =============================================================================

@router.get("", response_model=TicketListResponse)
async def list_tickets(
    status_filter: Optional[TicketStatus] = Query(default=None, alias="status"),
    priority: Optional[TicketPriority] = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    service: TicketService = Depends(get_ticket_service_dep),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    List tickets accessible to the current user.

    - Citizens see only their own tickets
    - Analysts see assigned tickets and open tickets
    - Authorities see tickets in their jurisdiction
    - Admins see all tickets

    Supports filtering by status and priority.
    """
    try:
        tickets, total = await service.get_tickets_for_user(
            user=current_user,
            status=status_filter,
            priority=priority,
            page=page,
            page_size=page_size,
            db=db
        )

        return TicketListResponse(
            tickets=tickets,
            total=total,
            page=page,
            page_size=page_size,
            has_more=(page * page_size) < total
        )

    except Exception as e:
        logger.error(f"Error listing tickets: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list tickets"
        )


@router.get("/queue")
async def get_ticket_queue(
    status_filter: Optional[List[TicketStatus]] = Query(default=None, alias="status"),
    priority: Optional[TicketPriority] = None,
    limit: int = Query(default=50, ge=1, le=100),
    current_user: User = Depends(require_analyst),
    service: TicketService = Depends(get_ticket_service_dep),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Get tickets in the queue for analysts/authorities.

    Returns active tickets sorted by priority (emergency first) and creation time (FIFO).

    Requires Analyst role or higher.
    """
    try:
        tickets = await service.get_queue_tickets(
            status=status_filter,
            priority=priority,
            limit=limit,
            db=db
        )

        return {
            "tickets": [t.model_dump() for t in tickets],
            "total": len(tickets),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

    except Exception as e:
        logger.error(f"Error getting ticket queue: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get ticket queue"
        )


# =============================================================================
# TICKET DETAIL
# =============================================================================

@router.get("/{ticket_id}")
async def get_ticket_detail(
    ticket_id: str,
    current_user: User = Depends(get_current_user),
    service: TicketService = Depends(get_ticket_service_dep),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Get detailed information about a ticket.

    Includes ticket data, messages, and activity log.
    Internal messages are hidden from citizens.
    """
    try:
        ticket = await service.get_ticket(ticket_id, db)
        if not ticket:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Ticket {ticket_id} not found"
            )

        # Check access
        if not service._user_can_access_ticket(current_user, ticket):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have access to this ticket"
            )

        # Get messages
        messages = await service.get_messages(ticket_id, current_user, db=db)

        # Get activities
        activities = await service.get_activities(ticket_id, db=db)

        # Get feedback if exists
        feedback_doc = await db.ticket_feedback.find_one({"ticket_id": ticket_id})
        feedback = TicketFeedback(**feedback_doc) if feedback_doc else None

        return {
            "ticket": ticket.model_dump(),
            "messages": [m.model_dump() for m in messages],
            "activities": [a.model_dump() for a in activities],
            "feedback": feedback.model_dump() if feedback else None
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting ticket detail: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get ticket detail"
        )


# =============================================================================
# TICKET ASSIGNMENT
# =============================================================================

@router.post("/{ticket_id}/assign")
async def assign_ticket(
    ticket_id: str,
    request: AssignTicketRequest,
    current_user: User = Depends(require_analyst),
    service: TicketService = Depends(get_ticket_service_dep),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Assign a ticket to an analyst.

    Requires Analyst role or higher.
    """
    try:
        ticket = await service.assign_ticket(
            ticket_id=ticket_id,
            request=request,
            assigner=current_user,
            db=db
        )

        return {
            "success": True,
            "ticket_id": ticket_id,
            "assigned_to": ticket.assigned_analyst_name,
            "status": ticket.status.value,
            "message": f"Ticket assigned to {ticket.assigned_analyst_name}"
        }

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error assigning ticket: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to assign ticket"
        )


@router.post("/{ticket_id}/assign-authority")
async def assign_ticket_to_authority(
    ticket_id: str,
    request: AssignToAuthorityRequest,
    current_user: User = Depends(require_analyst),
    service: TicketService = Depends(get_ticket_service_dep),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Assign a ticket to a specific authority.

    This makes the ticket visible in that authority's ticket list.
    Requires Analyst role or higher.

    The assigned authority will:
    - See this ticket in their tickets page
    - Receive a notification about the assignment
    - Be able to take action on the ticket
    """
    try:
        ticket = await service.assign_to_authority(
            ticket_id=ticket_id,
            authority_id=request.authority_id,
            assigner=current_user,
            message=request.message,
            db=db
        )

        return {
            "success": True,
            "ticket_id": ticket_id,
            "assigned_to_authority": ticket.assigned_authority_name,
            "status": ticket.status.value,
            "message": f"Ticket assigned to authority: {ticket.assigned_authority_name}"
        }

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error assigning ticket to authority: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to assign ticket to authority"
        )


# =============================================================================
# STATUS MANAGEMENT
# =============================================================================

@router.put("/{ticket_id}/status")
@router.patch("/{ticket_id}/status")
async def update_ticket_status(
    ticket_id: str,
    request: UpdateTicketStatusRequest,
    current_user: User = Depends(require_analyst),
    service: TicketService = Depends(get_ticket_service_dep),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Update ticket status.

    Valid transitions depend on current status.
    Requires Analyst role or higher.
    """
    try:
        ticket = await service.update_status(
            ticket_id=ticket_id,
            new_status=request.status,
            user=current_user,
            notes=request.notes,
            db=db
        )

        return {
            "success": True,
            "ticket_id": ticket_id,
            "new_status": ticket.status.value,
            "message": f"Status updated to {ticket.status.value}"
        }

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error updating ticket status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update ticket status"
        )


# =============================================================================
# PRIORITY MANAGEMENT
# =============================================================================

@router.put("/{ticket_id}/priority")
async def update_ticket_priority(
    ticket_id: str,
    request: UpdateTicketPriorityRequest,
    current_user: User = Depends(require_analyst),
    service: TicketService = Depends(get_ticket_service_dep),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Update ticket priority.

    SLA deadlines are recalculated based on new priority.
    Requires Analyst role or higher.
    """
    try:
        ticket = await service.update_priority(
            ticket_id=ticket_id,
            new_priority=request.priority,
            user=current_user,
            reason=request.reason,
            db=db
        )

        return {
            "success": True,
            "ticket_id": ticket_id,
            "new_priority": ticket.priority.value,
            "response_due": ticket.response_due.isoformat(),
            "resolution_due": ticket.resolution_due.isoformat(),
            "message": f"Priority updated to {ticket.priority.value}"
        }

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error updating ticket priority: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update ticket priority"
        )


# =============================================================================
# ESCALATION
# =============================================================================

@router.post("/{ticket_id}/escalate")
async def escalate_ticket(
    ticket_id: str,
    request: EscalateTicketRequest,
    current_user: User = Depends(get_current_user),
    service: TicketService = Depends(get_ticket_service_dep),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Escalate a ticket to higher authority.

    - Citizens can escalate their own tickets
    - Analysts can escalate assigned tickets
    - Authorities can escalate any ticket in their jurisdiction

    Priority is automatically upgraded to CRITICAL.
    """
    try:
        ticket = await service.escalate_ticket(
            ticket_id=ticket_id,
            request=request,
            user=current_user,
            db=db
        )

        return {
            "success": True,
            "ticket_id": ticket_id,
            "new_status": ticket.status.value,
            "new_priority": ticket.priority.value,
            "escalated_to": ticket.escalated_to_name,
            "message": "Ticket escalated successfully"
        }

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error escalating ticket: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to escalate ticket"
        )


# =============================================================================
# RESOLUTION & CLOSURE
# =============================================================================

@router.post("/{ticket_id}/resolve")
async def resolve_ticket(
    ticket_id: str,
    request: ResolveTicketRequest,
    current_user: User = Depends(require_analyst),
    service: TicketService = Depends(get_ticket_service_dep),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Resolve a ticket.

    Requires resolution notes and list of actions taken.
    Requires Analyst role or higher.
    """
    try:
        ticket = await service.resolve_ticket(
            ticket_id=ticket_id,
            request=request,
            user=current_user,
            db=db
        )

        return {
            "success": True,
            "ticket_id": ticket_id,
            "status": ticket.status.value,
            "resolved_at": ticket.resolved_at.isoformat(),
            "resolved_by": ticket.resolved_by_name,
            "message": "Ticket resolved successfully"
        }

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error resolving ticket: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to resolve ticket"
        )


@router.post("/{ticket_id}/close")
async def close_ticket(
    ticket_id: str,
    reason: Optional[str] = None,
    current_user: User = Depends(require_authority),
    service: TicketService = Depends(get_ticket_service_dep),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Close a resolved ticket.

    Only resolved tickets can be closed.
    Requires Authority role or higher.
    """
    try:
        ticket = await service.close_ticket(
            ticket_id=ticket_id,
            user=current_user,
            reason=reason,
            db=db
        )

        return {
            "success": True,
            "ticket_id": ticket_id,
            "status": ticket.status.value,
            "closed_at": ticket.closed_at.isoformat(),
            "closed_by": ticket.closed_by_name,
            "message": "Ticket closed successfully"
        }

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error closing ticket: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to close ticket"
        )


@router.post("/{ticket_id}/reopen")
async def reopen_ticket(
    ticket_id: str,
    reason: str = Query(..., min_length=10),
    current_user: User = Depends(get_current_user),
    service: TicketService = Depends(get_ticket_service_dep),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Reopen a resolved or closed ticket.

    Requires a reason for reopening.
    SLA deadlines are recalculated from current time.
    """
    try:
        ticket = await service.reopen_ticket(
            ticket_id=ticket_id,
            user=current_user,
            reason=reason,
            db=db
        )

        return {
            "success": True,
            "ticket_id": ticket_id,
            "status": ticket.status.value,
            "response_due": ticket.response_due.isoformat(),
            "resolution_due": ticket.resolution_due.isoformat(),
            "message": "Ticket reopened successfully"
        }

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error reopening ticket: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to reopen ticket"
        )


# =============================================================================
# MESSAGING
# =============================================================================

@router.post("/{ticket_id}/messages")
async def send_message(
    ticket_id: str,
    request: SendMessageRequest,
    current_user: User = Depends(get_current_user),
    service: TicketService = Depends(get_ticket_service_dep),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Send a message in a ticket.

    - Citizens can only send external messages
    - Analysts/Authorities can send internal messages (visible only to staff)

    First response from staff automatically updates status to IN_PROGRESS.
    """
    try:
        message = await service.send_message(
            ticket_id=ticket_id,
            request=request,
            user=current_user,
            db=db
        )

        return {
            "success": True,
            "message_id": message.message_id,
            "ticket_id": ticket_id,
            "message": message.model_dump()
        }

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error sending message: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to send message"
        )


@router.get("/{ticket_id}/messages")
async def get_messages(
    ticket_id: str,
    limit: int = Query(default=100, ge=1, le=500),
    before_message_id: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    service: TicketService = Depends(get_ticket_service_dep),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Get messages for a ticket.

    Internal messages are hidden from citizens.
    Supports pagination with before_message_id for loading older messages.
    """
    try:
        messages = await service.get_messages(
            ticket_id=ticket_id,
            user=current_user,
            limit=limit,
            before_message_id=before_message_id,
            db=db
        )

        return {
            "ticket_id": ticket_id,
            "messages": [m.model_dump() for m in messages],
            "total": len(messages),
            "has_more": len(messages) == limit
        }

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error getting messages: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get messages"
        )


# =============================================================================
# PARTICIPANT MANAGEMENT
# =============================================================================

@router.get("/{ticket_id}/participants")
async def get_ticket_participants(
    ticket_id: str,
    current_user: User = Depends(get_current_user),
    service: TicketService = Depends(get_ticket_service_dep),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Get all participants of a ticket.

    Returns reporter, analyst, authority, and additional participants.
    """
    try:
        participants = await service.get_ticket_participants(
            ticket_id=ticket_id,
            db=db
        )

        return {
            "success": True,
            "ticket_id": ticket_id,
            "participants": participants
        }

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error getting ticket participants: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get ticket participants"
        )


@router.post("/{ticket_id}/participants")
async def add_ticket_participant(
    ticket_id: str,
    user_id: str = Query(..., description="User ID of participant to add"),
    notes: Optional[str] = Query(default=None, max_length=500, description="Reason for adding"),
    can_message: bool = Query(default=True, description="Can send messages"),
    current_user: User = Depends(require_analyst),
    service: TicketService = Depends(get_ticket_service_dep),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Add a participant to a ticket.

    Only analysts, authorities, or admins can add participants.
    """
    try:
        ticket = await service.add_participant(
            ticket_id=ticket_id,
            participant_user_id=user_id,
            user=current_user,
            notes=notes,
            can_message=can_message,
            db=db
        )

        return {
            "success": True,
            "ticket_id": ticket_id,
            "message": f"Participant added successfully",
            "total_participants": len(ticket.additional_participants or []) + 3  # +3 for main participants
        }

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error adding participant: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to add participant"
        )


@router.delete("/{ticket_id}/participants/{participant_user_id}")
async def remove_ticket_participant(
    ticket_id: str,
    participant_user_id: str,
    current_user: User = Depends(require_analyst),
    service: TicketService = Depends(get_ticket_service_dep),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Remove a participant from a ticket.

    Only analysts, authorities, or admins can remove participants.
    Cannot remove main participants (reporter, assigned analyst, authority).
    """
    try:
        ticket = await service.remove_participant(
            ticket_id=ticket_id,
            participant_user_id=participant_user_id,
            user=current_user,
            db=db
        )

        return {
            "success": True,
            "ticket_id": ticket_id,
            "message": "Participant removed successfully"
        }

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error removing participant: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to remove participant"
        )


# =============================================================================
# FEEDBACK
# =============================================================================

@router.post("/{ticket_id}/feedback")
async def submit_feedback(
    ticket_id: str,
    request: SubmitFeedbackRequest,
    current_user: User = Depends(get_current_user),
    service: TicketService = Depends(get_ticket_service_dep),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Submit feedback for a resolved/closed ticket.

    Only the original reporter can submit feedback.
    Feedback can only be submitted once per ticket.
    """
    try:
        feedback = await service.submit_feedback(
            ticket_id=ticket_id,
            request=request,
            user=current_user,
            db=db
        )

        return {
            "success": True,
            "feedback_id": feedback.feedback_id,
            "ticket_id": ticket_id,
            "satisfaction_rating": feedback.satisfaction_rating,
            "message": "Feedback submitted successfully. Thank you!"
        }

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error submitting feedback: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to submit feedback"
        )


# =============================================================================
# STATISTICS
# =============================================================================

@router.get("/stats/summary", response_model=TicketStatsResponse)
async def get_ticket_stats(
    days: int = Query(default=7, ge=1, le=90),
    current_user: User = Depends(require_authority),
    service: TicketService = Depends(get_ticket_service_dep),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Get ticket statistics.

    Returns counts, averages, and trends.
    Requires Authority role or higher.
    """
    try:
        stats = await service.get_statistics(days=days, db=db)
        return TicketStatsResponse(**stats)

    except Exception as e:
        logger.error(f"Error getting ticket stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get ticket statistics"
        )


# =============================================================================
# MY TICKETS (for reporters/citizens)
# =============================================================================

@router.get("/my/tickets")
async def get_my_tickets(
    status_filter: Optional[TicketStatus] = Query(default=None, alias="status"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=50),
    current_user: User = Depends(get_current_user),
    service: TicketService = Depends(get_ticket_service_dep),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Get tickets for the current user (reporter view).

    Shows only tickets where the user is the original reporter.
    """
    try:
        # Build query for user's tickets
        query = {"reporter_id": current_user.user_id}
        if status_filter:
            query["status"] = status_filter.value

        total = await db.tickets.count_documents(query)

        skip = (page - 1) * page_size
        cursor = db.tickets.find(query).sort("created_at", -1).skip(skip).limit(page_size)

        tickets = []
        async for doc in cursor:
            tickets.append(Ticket.from_mongo(doc))

        return {
            "tickets": [t.model_dump() for t in tickets],
            "total": total,
            "page": page,
            "page_size": page_size,
            "has_more": (page * page_size) < total
        }

    except Exception as e:
        logger.error(f"Error getting user tickets: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get your tickets"
        )


# =============================================================================
# AUTHORITIES LIST (for adding participants)
# =============================================================================

@router.get("/lookup/authorities")
async def get_authorities_list(
    search: Optional[str] = Query(default=None, description="Search by name or organization"),
    limit: int = Query(default=20, ge=1, le=50),
    current_user: User = Depends(require_analyst),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Get list of authorities for adding to tickets.

    Allows analysts to find authorities to add as participants.
    Returns only active authority users with limited info.
    """
    try:
        # Build query for authority users only
        query = {
            "role": {"$in": ["authority", "authority_admin"]},
            "is_active": True,
            "is_banned": False
        }

        # Search filter
        if search:
            query["$or"] = [
                {"name": {"$regex": search, "$options": "i"}},
                {"authority_organization": {"$regex": search, "$options": "i"}},
                {"authority_designation": {"$regex": search, "$options": "i"}}
            ]

        # Get authorities
        cursor = db.users.find(query).sort("name", 1).limit(limit)
        authorities = await cursor.to_list(length=limit)

        # Format response with limited info (no sensitive data)
        authority_list = []
        for auth_doc in authorities:
            authority_list.append({
                "user_id": auth_doc.get("user_id"),
                "name": auth_doc.get("name"),
                "role": auth_doc.get("role"),
                "authority_organization": auth_doc.get("authority_organization"),
                "authority_designation": auth_doc.get("authority_designation")
            })

        return {
            "authorities": authority_list,
            "total": len(authority_list)
        }

    except Exception as e:
        logger.error(f"Error getting authorities list: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get authorities list"
        )


# =============================================================================
# ANALYSTS LIST (for authorities to add participants)
# =============================================================================

@router.get("/lookup/analysts")
async def get_analysts_list(
    search: Optional[str] = Query(default=None, description="Search by name or email"),
    limit: int = Query(default=20, ge=1, le=50),
    current_user: User = Depends(require_authority),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Get list of analysts for adding to tickets.

    Allows authorities to find analysts to add as participants.
    Returns only active analyst users with limited info.
    """
    try:
        # Build query for analyst users only
        query = {
            "role": "analyst",
            "is_active": True,
            "is_banned": False
        }

        # Search filter
        if search:
            query["$or"] = [
                {"name": {"$regex": search, "$options": "i"}},
                {"email": {"$regex": search, "$options": "i"}}
            ]

        # Get analysts
        cursor = db.users.find(query).sort("name", 1).limit(limit)
        analysts = await cursor.to_list(length=limit)

        # Format response with limited info (no sensitive data)
        analyst_list = []
        for analyst_doc in analysts:
            analyst_list.append({
                "user_id": analyst_doc.get("user_id"),
                "name": analyst_doc.get("name"),
                "email": analyst_doc.get("email"),
                "role": analyst_doc.get("role")
            })

        return {
            "analysts": analyst_list,
            "total": len(analyst_list)
        }

    except Exception as e:
        logger.error(f"Error getting analysts list: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get analysts list"
        )


# =============================================================================
# V2 ENDPOINTS - Role-Based Queue, Thread Messaging, Escalation
# =============================================================================

class SendThreadedMessageRequest(BaseModel):
    """Request for sending a threaded message."""
    content: str = Field(..., min_length=1, max_length=5000)
    thread: MessageThread = Field(default=MessageThread.ALL_PARTIES)
    attachments: Optional[List[str]] = Field(default=None)


class EscalateToTargetRequest(BaseModel):
    """Request for escalating to a specific target."""
    target_user_id: str = Field(..., description="User ID to escalate to")
    reason: str = Field(..., min_length=10, max_length=1000)
    priority_override: Optional[TicketPriority] = Field(default=None)


@router.get("/v2/queue")
async def get_role_based_queue(
    role: str = Query(..., description="Role filter: analyst, authority"),
    assignment_status: Optional[AssignmentStatus] = Query(default=None),
    status_filter: Optional[List[TicketStatus]] = Query(default=None, alias="status"),
    priority: Optional[TicketPriority] = None,
    assigned_to_me: bool = Query(default=False, description="Show only tickets assigned to me"),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
    current_user: User = Depends(require_analyst_or_authority),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    V2: Get role-based ticket queue.

    Provides filtered view based on role:
    - analyst: Shows tickets assigned to analysts or unassigned
    - authority: Shows tickets assigned to authorities or awaiting authority action

    Supports filtering by assignment status, ticket status, and priority.
    """
    try:
        # Validate role
        if role not in ["analyst", "authority"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Role must be 'analyst' or 'authority'"
            )

        # Build query based on role
        query = {"is_deleted": {"$ne": True}}

        if role == "analyst":
            if assigned_to_me:
                # Using V2 embedded assignment structure
                query["$or"] = [
                    {"assignment.analyst_id": current_user.user_id},
                    {"assigned_analyst_id": current_user.user_id}  # V1 fallback
                ]
            else:
                # Show unassigned or analyst-assigned tickets
                query["$or"] = [
                    {"assignment.assignment_status": {"$in": [
                        AssignmentStatus.UNASSIGNED.value,
                        AssignmentStatus.ANALYST_ONLY.value
                    ]}},
                    {"assigned_analyst_id": {"$in": [None, ""]}},  # V1 fallback
                    {"assignment": {"$exists": False}}  # V1 data without V2 structure
                ]
        else:  # authority
            if assigned_to_me:
                query["$or"] = [
                    {"assignment.authority_id": current_user.user_id},
                    {"assigned_authority_id": current_user.user_id}  # V1 fallback
                ]
            else:
                # Show tickets needing authority attention
                query["$or"] = [
                    {"assignment.assignment_status": {"$in": [
                        AssignmentStatus.ANALYST_ONLY.value,
                        AssignmentStatus.AUTHORITY_ONLY.value,
                        AssignmentStatus.FULLY_ASSIGNED.value
                    ]}},
                    {"assigned_authority_id": {"$ne": None}},  # V1 fallback
                    {"status": TicketStatus.ESCALATED.value}  # All escalated tickets
                ]

        # Assignment status filter
        if assignment_status:
            query["assignment.assignment_status"] = assignment_status.value

        # Status filter
        if status_filter:
            query["status"] = {"$in": [s.value for s in status_filter]}
        else:
            # Default: exclude closed tickets
            query["status"] = {"$ne": TicketStatus.CLOSED.value}

        # Priority filter
        if priority:
            query["priority"] = priority.value

        # Execute query with sorting (priority desc, created_at asc for FIFO)
        priority_order = {"emergency": 0, "critical": 1, "high": 2, "medium": 3, "low": 4}

        cursor = db.tickets.find(query).sort([
            ("priority", 1),  # Lower number = higher priority
            ("created_at", 1)  # FIFO within same priority
        ]).skip(skip).limit(limit)

        tickets = []
        async for doc in cursor:
            ticket = Ticket.from_mongo(doc)
            tickets.append(ticket.model_dump())

        total = await db.tickets.count_documents(query)

        return {
            "tickets": tickets,
            "total": total,
            "skip": skip,
            "limit": limit,
            "role": role,
            "assigned_to_me": assigned_to_me,
            "has_more": (skip + limit) < total
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting role-based queue: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get ticket queue"
        )


@router.get("/{ticket_id}/messages/v2")
async def get_threaded_messages(
    ticket_id: str,
    thread: Optional[MessageThread] = Query(default=None, description="Filter by thread"),
    limit: int = Query(default=100, ge=1, le=500),
    before_message_id: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    service: TicketService = Depends(get_ticket_service_dep),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    V2: Get messages with thread filtering.

    Threads:
    - all: All-party messages (visible to everyone)
    - ra: Reporter ↔ Analyst private thread
    - aa: Analyst ↔ Authority private thread
    - internal: Internal notes (staff only)

    Access control enforced based on user role.
    """
    try:
        # Get ticket to verify access
        ticket = await service.get_ticket(ticket_id, db)
        if not ticket:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Ticket {ticket_id} not found"
            )

        # Check access
        if not service._user_can_access_ticket(current_user, ticket):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have access to this ticket"
            )

        # Get messages with thread filtering
        messages = await service.get_messages(
            ticket_id=ticket_id,
            user=current_user,
            limit=limit,
            before_message_id=before_message_id,
            thread_filter=thread,
            db=db
        )

        # Group messages by thread for response
        thread_counts = {}
        for msg in messages:
            msg_thread = msg.thread if hasattr(msg, 'thread') else MessageThread.ALL_PARTIES
            thread_counts[msg_thread.value] = thread_counts.get(msg_thread.value, 0) + 1

        return {
            "ticket_id": ticket_id,
            "messages": [m.model_dump() for m in messages],
            "total": len(messages),
            "thread_filter": thread.value if thread else "all",
            "thread_counts": thread_counts,
            "has_more": len(messages) == limit
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting threaded messages: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get messages"
        )


@router.post("/{ticket_id}/messages/v2")
async def send_threaded_message(
    ticket_id: str,
    request: SendThreadedMessageRequest,
    current_user: User = Depends(get_current_user),
    service: TicketService = Depends(get_ticket_service_dep),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    V2: Send a message to a specific thread.

    Thread visibility:
    - all: Visible to reporter, analyst, and authority
    - ra: Visible only to reporter and analyst
    - aa: Visible only to analyst and authority
    - internal: Visible only to analyst and authority (hidden from reporter)

    Thread access is validated based on user role.
    """
    try:
        # Get ticket to verify access
        ticket = await service.get_ticket(ticket_id, db)
        if not ticket:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Ticket {ticket_id} not found"
            )

        # Check access
        if not service._user_can_access_ticket(current_user, ticket):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have access to this ticket"
            )

        # Validate thread access based on user role
        user_role = current_user.role

        # Citizens can only post to ALL_PARTIES or REPORTER_ANALYST
        if user_role == UserRole.CITIZEN:
            if request.thread not in [MessageThread.ALL_PARTIES, MessageThread.REPORTER_ANALYST]:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="You can only send messages to all parties or directly to the analyst"
                )

        # Send message with thread
        message = await service.send_message(
            ticket_id=ticket_id,
            request=SendMessageRequest(
                content=request.content,
                attachments=request.attachments,
                is_internal=(request.thread == MessageThread.INTERNAL)
            ),
            user=current_user,
            thread=request.thread,
            db=db
        )

        return {
            "success": True,
            "message_id": message.message_id,
            "ticket_id": ticket_id,
            "thread": request.thread.value,
            "message": message.model_dump()
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error sending threaded message: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to send message"
        )


@router.post("/{ticket_id}/escalate-v2")
async def escalate_to_target(
    ticket_id: str,
    request: EscalateToTargetRequest,
    current_user: User = Depends(require_analyst_or_authority),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    V2: Escalate ticket to a specific target user.

    Unlike V1 auto-escalation, this allows manual selection of:
    - A specific authority to handle the escalation
    - Priority override (optional)

    Records full escalation history.
    """
    try:
        escalation_service = EscalationService(db)

        result = await escalation_service.escalate_ticket(
            ticket_id=ticket_id,
            target_user_id=request.target_user_id,
            escalating_user=current_user,
            reason=request.reason,
            priority_override=request.priority_override
        )

        if not result.get("success"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result.get("error", "Escalation failed")
            )

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error escalating ticket: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to escalate ticket"
        )


@router.get("/{ticket_id}/escalation-targets")
async def get_escalation_targets(
    ticket_id: str,
    current_user: User = Depends(require_analyst_or_authority),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Get available escalation targets for a ticket.

    Returns list of authorities who can receive the escalation,
    filtered by jurisdiction and availability.
    """
    try:
        escalation_service = EscalationService(db)

        targets = await escalation_service.get_escalation_targets(
            ticket_id=ticket_id,
            requesting_user=current_user
        )

        return {
            "ticket_id": ticket_id,
            "targets": targets,
            "total": len(targets)
        }

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error getting escalation targets: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get escalation targets"
        )


@router.get("/{ticket_id}/escalation-history")
async def get_escalation_history(
    ticket_id: str,
    current_user: User = Depends(require_analyst_or_authority),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Get escalation history for a ticket.

    Shows all escalations including:
    - Who escalated
    - Who received
    - Reason
    - Timestamp
    """
    try:
        escalation_service = EscalationService(db)

        history = await escalation_service.get_escalation_history(ticket_id)

        return {
            "ticket_id": ticket_id,
            "history": history,
            "total_escalations": len(history)
        }

    except Exception as e:
        logger.error(f"Error getting escalation history: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get escalation history"
        )


# =============================================================================
# SLA ENDPOINTS
# =============================================================================

@router.get("/v2/sla-breaches")
async def get_sla_breaches(
    breach_type: Optional[str] = Query(default=None, description="response, resolution, or all"),
    priority: Optional[TicketPriority] = None,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
    current_user: User = Depends(require_authority),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Get tickets that have breached or are about to breach SLA.

    Returns tickets sorted by breach severity.
    Authority only.
    """
    try:
        sla_service = SLAService(db)

        now = datetime.now(timezone.utc)

        # Build query for SLA breaches
        query = {
            "status": {"$nin": [TicketStatus.CLOSED.value, TicketStatus.RESOLVED.value]},
            "is_deleted": {"$ne": True}
        }

        if breach_type == "response":
            query["response_due"] = {"$lt": now}
            query["first_response_at"] = None
        elif breach_type == "resolution":
            query["resolution_due"] = {"$lt": now}
        else:
            # All breaches
            query["$or"] = [
                {"response_due": {"$lt": now}, "first_response_at": None},
                {"resolution_due": {"$lt": now}}
            ]

        if priority:
            query["priority"] = priority.value

        cursor = db.tickets.find(query).sort("response_due", 1).skip(skip).limit(limit)

        breached_tickets = []
        async for doc in cursor:
            ticket = Ticket.from_mongo(doc)
            ticket_dict = ticket.model_dump()

            # Add breach info
            if ticket.response_due and ticket.response_due < now and not ticket.first_response_at:
                ticket_dict["response_breached"] = True
                ticket_dict["response_breach_hours"] = (now - ticket.response_due).total_seconds() / 3600
            else:
                ticket_dict["response_breached"] = False

            if ticket.resolution_due and ticket.resolution_due < now:
                ticket_dict["resolution_breached"] = True
                ticket_dict["resolution_breach_hours"] = (now - ticket.resolution_due).total_seconds() / 3600
            else:
                ticket_dict["resolution_breached"] = False

            breached_tickets.append(ticket_dict)

        total = await db.tickets.count_documents(query)

        return {
            "tickets": breached_tickets,
            "total": total,
            "skip": skip,
            "limit": limit,
            "breach_type": breach_type or "all"
        }

    except Exception as e:
        logger.error(f"Error getting SLA breaches: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get SLA breaches"
        )


@router.get("/{ticket_id}/sla-status")
async def get_ticket_sla_status(
    ticket_id: str,
    current_user: User = Depends(get_current_user),
    service: TicketService = Depends(get_ticket_service_dep),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Get SLA status for a specific ticket.

    Returns response and resolution SLA times and status.
    """
    try:
        ticket = await service.get_ticket(ticket_id, db)
        if not ticket:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Ticket {ticket_id} not found"
            )

        # Check access
        if not service._user_can_access_ticket(current_user, ticket):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have access to this ticket"
            )

        now = datetime.now(timezone.utc)

        # Calculate SLA status
        response_sla = {
            "due": ticket.response_due.isoformat() if ticket.response_due else None,
            "met": ticket.first_response_at is not None,
            "met_at": ticket.first_response_at.isoformat() if ticket.first_response_at else None,
            "breached": False,
            "time_remaining_hours": None
        }

        if ticket.response_due:
            if ticket.first_response_at:
                response_sla["time_to_respond_hours"] = (
                    ticket.first_response_at - ticket.created_at
                ).total_seconds() / 3600
            elif now > ticket.response_due:
                response_sla["breached"] = True
                response_sla["breach_hours"] = (now - ticket.response_due).total_seconds() / 3600
            else:
                response_sla["time_remaining_hours"] = (ticket.response_due - now).total_seconds() / 3600

        resolution_sla = {
            "due": ticket.resolution_due.isoformat() if ticket.resolution_due else None,
            "met": ticket.resolved_at is not None,
            "met_at": ticket.resolved_at.isoformat() if ticket.resolved_at else None,
            "breached": False,
            "time_remaining_hours": None
        }

        if ticket.resolution_due:
            if ticket.resolved_at:
                resolution_sla["time_to_resolve_hours"] = (
                    ticket.resolved_at - ticket.created_at
                ).total_seconds() / 3600
            elif now > ticket.resolution_due:
                resolution_sla["breached"] = True
                resolution_sla["breach_hours"] = (now - ticket.resolution_due).total_seconds() / 3600
            else:
                resolution_sla["time_remaining_hours"] = (ticket.resolution_due - now).total_seconds() / 3600

        return {
            "ticket_id": ticket_id,
            "priority": ticket.priority.value,
            "status": ticket.status.value,
            "response_sla": response_sla,
            "resolution_sla": resolution_sla,
            "sla_config": ticket.sla_config.model_dump() if ticket.sla_config else None
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting ticket SLA status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get SLA status"
        )
