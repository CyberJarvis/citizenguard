"""
Escalation Service (V2)
Handles manual escalation workflows for tickets.

Features:
- Manual escalation with target selection
- Get available escalation targets based on context
- Escalation history tracking
- Escalation notifications
"""

import logging
import uuid
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any, Tuple

from motor.motor_asyncio import AsyncIOMotorDatabase

from app.models.ticket import (
    Ticket, TicketStatus, TicketPriority, Escalation, TicketActivity, ActivityType,
    calculate_sla_deadlines
)
from app.models.user import User, UserRole
from app.models.notification import NotificationType, NotificationSeverity

logger = logging.getLogger(__name__)


class EscalationService:
    """
    Service for manual ticket escalation.

    Responsibilities:
    - Escalate tickets to selected targets
    - Get list of available escalation targets
    - Track escalation history
    - Send escalation notifications
    """

    def __init__(self, db: AsyncIOMotorDatabase):
        """Initialize escalation service with database connection."""
        self.db = db

    async def escalate_ticket(
        self,
        ticket_id: str,
        escalate_to_id: str,
        reason: str,
        escalated_by: User,
        new_priority: Optional[TicketPriority] = None,
        notes: Optional[str] = None
    ) -> Tuple[bool, str, Optional[Ticket]]:
        """
        Escalate a ticket to a selected target.

        Args:
            ticket_id: The ticket to escalate
            escalate_to_id: User ID of the escalation target
            reason: Reason for escalation
            escalated_by: User performing the escalation
            new_priority: Optional new priority for the ticket
            notes: Optional additional notes

        Returns:
            Tuple of (success, message, updated_ticket)
        """
        try:
            # Get the ticket
            doc = await self.db.tickets.find_one({"ticket_id": ticket_id})
            if not doc:
                return False, f"Ticket {ticket_id} not found", None

            ticket = Ticket.from_mongo(doc)

            # Validate escalation is allowed
            if ticket.status in [TicketStatus.CLOSED, TicketStatus.RESOLVED]:
                return False, "Cannot escalate closed or resolved tickets", None

            # Get escalation target
            target_doc = await self.db.users.find_one({"user_id": escalate_to_id})
            if not target_doc:
                return False, f"Escalation target {escalate_to_id} not found", None

            target = User.from_mongo(target_doc)

            # Validate target has appropriate role
            if target.role not in [UserRole.ANALYST, UserRole.AUTHORITY, UserRole.AUTHORITY_ADMIN]:
                return False, "Escalation target must be an analyst or authority", None

            now = datetime.now(timezone.utc)

            # Determine new priority (bump up if not specified)
            if new_priority is None:
                new_priority = self._get_escalated_priority(ticket.priority)

            # Recalculate SLA
            new_sla = calculate_sla_deadlines(new_priority, now)

            # Store previous state
            previous_status = ticket.status
            previous_priority = ticket.priority
            previous_assignee_id = ticket.assigned_analyst_id
            previous_assignee_name = ticket.assigned_analyst_name

            # Get user name
            target_name = target.name or target.email or target.user_id
            escalated_by_name = escalated_by.name or escalated_by.email or escalated_by.user_id

            # Update ticket
            update_data = {
                "status": TicketStatus.ESCALATED.value,
                "is_escalated": True,
                "escalated_to_id": escalate_to_id,
                "escalated_to_name": target_name,
                "escalation_reason": reason,
                "escalation_count": (ticket.escalation_count or 0) + 1,
                "priority": new_priority.value,
                "response_due": new_sla["response_due"],
                "resolution_due": new_sla["resolution_due"],
                "updated_at": now
            }

            # If escalating to authority, update assigned authority
            if target.role in [UserRole.AUTHORITY, UserRole.AUTHORITY_ADMIN]:
                update_data["assigned_authority_id"] = escalate_to_id
                update_data["assigned_authority_name"] = target_name
                # V2: Also update authority_id if it was null
                if not ticket.authority_id:
                    update_data["authority_id"] = escalate_to_id
                    update_data["authority_name"] = target_name

            await self.db.tickets.update_one(
                {"ticket_id": ticket_id},
                {"$set": update_data}
            )

            # Create escalation record
            escalation_id = f"ESC-{uuid.uuid4().hex[:12].upper()}"
            escalation = Escalation(
                escalation_id=escalation_id,
                ticket_id=ticket_id,
                escalated_by_id=escalated_by.user_id,
                escalated_by_name=escalated_by_name,
                escalated_by_role=escalated_by.role.value,
                escalated_to_id=escalate_to_id,
                escalated_to_name=target_name,
                reason=reason,
                previous_priority=previous_priority,
                previous_status=previous_status,
                previous_assignee_id=previous_assignee_id,
                previous_assignee_name=previous_assignee_name,
                new_priority=new_priority,
                new_status=TicketStatus.ESCALATED,
                notes=notes,
                created_at=now
            )
            await self.db.ticket_escalations.insert_one(escalation.model_dump())

            # Log activity
            activity_id = f"ACT-{uuid.uuid4().hex[:12].upper()}"
            activity = TicketActivity(
                activity_id=activity_id,
                ticket_id=ticket_id,
                activity_type=ActivityType.ESCALATED,
                performed_by_id=escalated_by.user_id,
                performed_by_name=escalated_by_name,
                performed_by_role=escalated_by.role.value,
                description=f"Ticket escalated to {target_name}: {reason}",
                details={
                    "escalated_to_id": escalate_to_id,
                    "escalated_to_name": target_name,
                    "reason": reason,
                    "new_priority": new_priority.value,
                    "notes": notes
                },
                previous_value=previous_status.value,
                new_value=TicketStatus.ESCALATED.value,
                created_at=now
            )
            await self.db.ticket_activities.insert_one(activity.model_dump())

            # Sync to hazard report
            await self.db.hazard_reports.update_one(
                {"report_id": ticket.report_id},
                {
                    "$set": {
                        "ticket_status": TicketStatus.ESCALATED.value,
                        "updated_at": now
                    }
                }
            )

            # Send notifications
            await self._send_escalation_notifications(
                ticket=ticket,
                escalated_to=target,
                escalated_by=escalated_by,
                reason=reason,
                new_priority=new_priority
            )

            logger.info(
                f"Ticket {ticket_id} escalated to {target_name} by {escalated_by_name}: {reason}"
            )

            # Fetch updated ticket
            updated_doc = await self.db.tickets.find_one({"ticket_id": ticket_id})
            updated_ticket = Ticket.from_mongo(updated_doc)

            return True, f"Ticket escalated to {target_name}", updated_ticket

        except Exception as e:
            logger.error(f"Error escalating ticket {ticket_id}: {e}")
            return False, f"Error: {str(e)}", None

    async def get_escalation_targets(
        self,
        ticket_id: str,
        user: User
    ) -> List[Dict[str, Any]]:
        """
        Get list of available escalation targets for a ticket.

        Returns users who can receive escalations based on:
        - Their role (analyst, authority, authority_admin)
        - Not already the primary assignee
        - Active account

        Args:
            ticket_id: The ticket being escalated
            user: The user requesting targets

        Returns:
            List of potential escalation targets
        """
        # Get the ticket
        doc = await self.db.tickets.find_one({"ticket_id": ticket_id})
        if not doc:
            return []

        ticket = Ticket.from_mongo(doc)

        # Find eligible users
        query = {
            "role": {"$in": [
                UserRole.ANALYST.value,
                UserRole.AUTHORITY.value,
                UserRole.AUTHORITY_ADMIN.value
            ]},
            "is_active": True,
            "is_banned": {"$ne": True}
        }

        # Exclude current assignees (don't escalate to someone already on the ticket)
        exclude_ids = [user.user_id]  # Don't show yourself
        if ticket.assigned_analyst_id:
            exclude_ids.append(ticket.assigned_analyst_id)
        # Don't exclude authority - might want to escalate to different authority

        query["user_id"] = {"$nin": exclude_ids}

        cursor = self.db.users.find(query).limit(50)

        targets = []
        async for target_doc in cursor:
            target = User.from_mongo(target_doc)
            target_name = target.name or target.email or target.user_id

            targets.append({
                "user_id": target.user_id,
                "name": target_name,
                "email": target.email,
                "role": target.role.value,
                "organization": getattr(target, 'authority_organization', None),
                "designation": getattr(target, 'authority_designation', None)
            })

        # Sort by role (authorities first) then by name
        role_priority = {
            UserRole.AUTHORITY_ADMIN.value: 0,
            UserRole.AUTHORITY.value: 1,
            UserRole.ANALYST.value: 2
        }
        targets.sort(key=lambda x: (role_priority.get(x["role"], 99), x["name"] or ""))

        return targets

    async def get_escalation_history(
        self,
        ticket_id: str,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Get escalation history for a ticket.

        Args:
            ticket_id: The ticket ID
            limit: Maximum number of records to return

        Returns:
            List of escalation records
        """
        cursor = self.db.ticket_escalations.find(
            {"ticket_id": ticket_id}
        ).sort("created_at", -1).limit(limit)

        history = []
        async for doc in cursor:
            # Convert datetime to ISO format for JSON
            if "created_at" in doc and doc["created_at"]:
                doc["created_at"] = doc["created_at"].isoformat()

            # Convert enums to values
            if "previous_priority" in doc and hasattr(doc["previous_priority"], 'value'):
                doc["previous_priority"] = doc["previous_priority"].value
            if "new_priority" in doc and hasattr(doc["new_priority"], 'value'):
                doc["new_priority"] = doc["new_priority"].value
            if "previous_status" in doc and hasattr(doc["previous_status"], 'value'):
                doc["previous_status"] = doc["previous_status"].value
            if "new_status" in doc and hasattr(doc["new_status"], 'value'):
                doc["new_status"] = doc["new_status"].value

            # Remove MongoDB _id
            doc.pop("_id", None)
            history.append(doc)

        return history

    def _get_escalated_priority(self, current: TicketPriority) -> TicketPriority:
        """
        Get the new priority after escalation (bump up one level).

        Args:
            current: Current priority

        Returns:
            New priority (one level higher, capped at EMERGENCY)
        """
        priority_order = [
            TicketPriority.LOW,
            TicketPriority.MEDIUM,
            TicketPriority.HIGH,
            TicketPriority.CRITICAL,
            TicketPriority.EMERGENCY
        ]

        current_index = priority_order.index(current)
        if current_index < len(priority_order) - 1:
            return priority_order[current_index + 1]
        return current

    async def _send_escalation_notifications(
        self,
        ticket: Ticket,
        escalated_to: User,
        escalated_by: User,
        reason: str,
        new_priority: TicketPriority
    ):
        """
        Send notifications about the escalation.

        Args:
            ticket: The escalated ticket
            escalated_to: User receiving the escalation
            escalated_by: User who escalated
            reason: Reason for escalation
            new_priority: New priority level
        """
        now = datetime.now(timezone.utc)
        escalated_by_name = escalated_by.name or escalated_by.email or escalated_by.user_id
        escalated_to_name = escalated_to.name or escalated_to.email or escalated_to.user_id

        # Notify the escalation target
        notification_id = f"NTF-{now.strftime('%Y%m%d')}-{uuid.uuid4().hex[:8].upper()}"
        target_notification = {
            "notification_id": notification_id,
            "user_id": escalated_to.user_id,
            "type": NotificationType.TICKET_ESCALATED.value,
            "severity": NotificationSeverity.CRITICAL.value,
            "title": "Escalated Ticket Assigned to You",
            "message": f"A ticket has been escalated to you by {escalated_by_name}: {reason}",
            "ticket_id": ticket.ticket_id,
            "report_id": ticket.report_id,
            "action_url": f"/tickets/{ticket.ticket_id}",
            "action_label": "View Ticket",
            "is_read": False,
            "is_dismissed": False,
            "metadata": {
                "escalated_by": escalated_by_name,
                "reason": reason,
                "new_priority": new_priority.value
            },
            "created_at": now
        }
        await self.db.notifications.insert_one(target_notification)

        # Notify the reporter
        if ticket.reporter_id and ticket.reporter_id != escalated_to.user_id:
            reporter_notification_id = f"NTF-{now.strftime('%Y%m%d')}-{uuid.uuid4().hex[:8].upper()}"
            reporter_notification = {
                "notification_id": reporter_notification_id,
                "user_id": ticket.reporter_id,
                "type": NotificationType.TICKET_STATUS.value,
                "severity": NotificationSeverity.MEDIUM.value,
                "title": "Your Ticket Has Been Escalated",
                "message": f"Your ticket has been escalated to {escalated_to_name} for faster resolution.",
                "ticket_id": ticket.ticket_id,
                "report_id": ticket.report_id,
                "action_url": f"/tickets/{ticket.ticket_id}",
                "action_label": "View Ticket",
                "is_read": False,
                "is_dismissed": False,
                "metadata": {
                    "escalated_to": escalated_to_name,
                    "new_priority": new_priority.value
                },
                "created_at": now
            }
            await self.db.notifications.insert_one(reporter_notification)

        # Notify original analyst if different from escalator
        if (ticket.assigned_analyst_id and
            ticket.assigned_analyst_id != escalated_by.user_id and
            ticket.assigned_analyst_id != escalated_to.user_id):

            analyst_notification_id = f"NTF-{now.strftime('%Y%m%d')}-{uuid.uuid4().hex[:8].upper()}"
            analyst_notification = {
                "notification_id": analyst_notification_id,
                "user_id": ticket.assigned_analyst_id,
                "type": NotificationType.TICKET_ESCALATED.value,
                "severity": NotificationSeverity.HIGH.value,
                "title": "Assigned Ticket Escalated",
                "message": f"A ticket you were assigned has been escalated to {escalated_to_name}: {reason}",
                "ticket_id": ticket.ticket_id,
                "report_id": ticket.report_id,
                "action_url": f"/tickets/{ticket.ticket_id}",
                "action_label": "View Ticket",
                "is_read": False,
                "is_dismissed": False,
                "metadata": {
                    "escalated_by": escalated_by_name,
                    "escalated_to": escalated_to_name,
                    "reason": reason
                },
                "created_at": now
            }
            await self.db.notifications.insert_one(analyst_notification)

    async def get_escalation_stats(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Get escalation statistics for the specified period.

        Args:
            start_date: Start of period
            end_date: End of period

        Returns:
            Escalation statistics
        """
        from datetime import timedelta

        if not end_date:
            end_date = datetime.now(timezone.utc)
        if not start_date:
            start_date = end_date - timedelta(days=30)

        # Count escalations
        total_escalations = await self.db.ticket_escalations.count_documents({
            "created_at": {"$gte": start_date, "$lte": end_date}
        })

        # Escalations by role
        role_pipeline = [
            {
                "$match": {
                    "created_at": {"$gte": start_date, "$lte": end_date}
                }
            },
            {
                "$group": {
                    "_id": "$escalated_by_role",
                    "count": {"$sum": 1}
                }
            }
        ]
        role_result = await self.db.ticket_escalations.aggregate(role_pipeline).to_list(10)
        by_role = {item["_id"]: item["count"] for item in role_result}

        # Most common escalation reasons (simple word frequency)
        # This is a simplified version - in production you might use more sophisticated analysis

        return {
            "period_start": start_date.isoformat(),
            "period_end": end_date.isoformat(),
            "total_escalations": total_escalations,
            "escalations_by_initiator_role": by_role,
            "avg_escalations_per_day": round(total_escalations / max(1, (end_date - start_date).days), 2)
        }


# Singleton instance
_escalation_service: Optional[EscalationService] = None


def get_escalation_service(db: AsyncIOMotorDatabase) -> EscalationService:
    """Get or create escalation service instance."""
    global _escalation_service
    if _escalation_service is None:
        _escalation_service = EscalationService(db)
    return _escalation_service
