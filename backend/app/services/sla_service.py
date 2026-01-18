"""
SLA Service (V2)
Handles SLA breach detection, notifications, and configurable breach actions.

Features:
- Check for response and resolution SLA breaches
- Configurable breach actions per priority (notify only, auto-escalate, both)
- Background job support for periodic SLA checks
- SLA metrics and reporting
"""

import logging
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict, Any, Tuple

from motor.motor_asyncio import AsyncIOMotorDatabase

from app.models.ticket import (
    Ticket, TicketStatus, TicketPriority, SLA_CONFIG,
    SLABreachAction, TicketSLAConfig
)
from app.models.notification import NotificationType, NotificationSeverity
from app.models.user import User, UserRole

logger = logging.getLogger(__name__)


# Default SLA configurations by priority (can be overridden per-ticket)
DEFAULT_SLA_CONFIG = {
    TicketPriority.EMERGENCY: {
        "response_hours": 1,
        "resolution_hours": 4,
        "breach_action": SLABreachAction.BOTH
    },
    TicketPriority.CRITICAL: {
        "response_hours": 2,
        "resolution_hours": 8,
        "breach_action": SLABreachAction.BOTH
    },
    TicketPriority.HIGH: {
        "response_hours": 4,
        "resolution_hours": 24,
        "breach_action": SLABreachAction.AUTO_ESCALATE
    },
    TicketPriority.MEDIUM: {
        "response_hours": 8,
        "resolution_hours": 48,
        "breach_action": SLABreachAction.NOTIFY_ONLY
    },
    TicketPriority.LOW: {
        "response_hours": 24,
        "resolution_hours": 72,
        "breach_action": SLABreachAction.NOTIFY_ONLY
    }
}


class SLAService:
    """
    Service for SLA breach detection and management.

    Responsibilities:
    - Check tickets for SLA breaches
    - Send notifications on breach
    - Auto-escalate tickets based on configuration
    - Track SLA metrics
    """

    def __init__(self, db: AsyncIOMotorDatabase):
        """Initialize SLA service with database connection."""
        self.db = db

    async def check_all_tickets_sla(self) -> Dict[str, Any]:
        """
        Check all active tickets for SLA breaches.

        This method is designed to be called by a background job periodically.

        Returns:
            Summary of SLA breaches found and actions taken
        """
        now = datetime.now(timezone.utc)

        # Find active tickets (not resolved, closed, or reopened)
        active_statuses = [
            TicketStatus.OPEN.value,
            TicketStatus.ASSIGNED.value,
            TicketStatus.IN_PROGRESS.value,
            TicketStatus.AWAITING_RESPONSE.value,
            TicketStatus.ESCALATED.value
        ]

        cursor = self.db.tickets.find({
            "status": {"$in": active_statuses}
        })

        response_breaches = []
        resolution_breaches = []
        escalated = []
        notifications_sent = []

        async for doc in cursor:
            ticket = Ticket.from_mongo(doc)

            # Check response SLA
            if not ticket.sla_response_breached and not ticket.first_response_at:
                if ticket.response_due and now > ticket.response_due:
                    response_breach = await self._handle_response_breach(ticket)
                    if response_breach:
                        response_breaches.append(ticket.ticket_id)
                        if response_breach.get("escalated"):
                            escalated.append(ticket.ticket_id)
                        if response_breach.get("notified"):
                            notifications_sent.extend(response_breach["notified"])

            # Check resolution SLA
            if not ticket.sla_resolution_breached:
                if ticket.resolution_due and now > ticket.resolution_due:
                    resolution_breach = await self._handle_resolution_breach(ticket)
                    if resolution_breach:
                        resolution_breaches.append(ticket.ticket_id)
                        if resolution_breach.get("escalated"):
                            escalated.append(ticket.ticket_id)
                        if resolution_breach.get("notified"):
                            notifications_sent.extend(resolution_breach["notified"])

        summary = {
            "checked_at": now.isoformat(),
            "response_breaches": len(response_breaches),
            "response_breach_tickets": response_breaches,
            "resolution_breaches": len(resolution_breaches),
            "resolution_breach_tickets": resolution_breaches,
            "escalated_tickets": escalated,
            "notifications_sent": len(notifications_sent)
        }

        logger.info(
            f"SLA check completed: {len(response_breaches)} response breaches, "
            f"{len(resolution_breaches)} resolution breaches, "
            f"{len(escalated)} escalated"
        )

        return summary

    async def _handle_response_breach(self, ticket: Ticket) -> Optional[Dict[str, Any]]:
        """
        Handle a response SLA breach for a ticket.

        Args:
            ticket: The ticket that breached response SLA

        Returns:
            Dictionary with actions taken, or None if no action
        """
        now = datetime.now(timezone.utc)

        # Mark as breached
        await self.db.tickets.update_one(
            {"ticket_id": ticket.ticket_id},
            {
                "$set": {
                    "sla_response_breached": True,
                    "sla_response_breached_at": now,
                    "updated_at": now
                }
            }
        )

        # Get breach action configuration
        breach_action = self._get_breach_action(ticket)

        result = {"breached": True, "notified": [], "escalated": False}

        # Send notifications if configured
        if breach_action in [SLABreachAction.NOTIFY_ONLY, SLABreachAction.BOTH]:
            notified = await self._send_breach_notifications(
                ticket, "response", "Response SLA breached - no response within SLA"
            )
            result["notified"] = notified

        # Auto-escalate if configured
        if breach_action in [SLABreachAction.AUTO_ESCALATE, SLABreachAction.BOTH]:
            escalated = await self._auto_escalate_ticket(
                ticket, "Response SLA breach - auto-escalated"
            )
            result["escalated"] = escalated

        logger.warning(
            f"Response SLA breach for ticket {ticket.ticket_id} "
            f"(due: {ticket.response_due}, action: {breach_action.value})"
        )

        return result

    async def _handle_resolution_breach(self, ticket: Ticket) -> Optional[Dict[str, Any]]:
        """
        Handle a resolution SLA breach for a ticket.

        Args:
            ticket: The ticket that breached resolution SLA

        Returns:
            Dictionary with actions taken, or None if no action
        """
        now = datetime.now(timezone.utc)

        # Mark as breached
        await self.db.tickets.update_one(
            {"ticket_id": ticket.ticket_id},
            {
                "$set": {
                    "sla_resolution_breached": True,
                    "sla_resolution_breached_at": now,
                    "updated_at": now
                }
            }
        )

        # Get breach action configuration
        breach_action = self._get_breach_action(ticket)

        result = {"breached": True, "notified": [], "escalated": False}

        # Send notifications if configured
        if breach_action in [SLABreachAction.NOTIFY_ONLY, SLABreachAction.BOTH]:
            notified = await self._send_breach_notifications(
                ticket, "resolution", "Resolution SLA breached - not resolved within SLA"
            )
            result["notified"] = notified

        # Auto-escalate if configured (only if not already escalated)
        if breach_action in [SLABreachAction.AUTO_ESCALATE, SLABreachAction.BOTH]:
            if ticket.status != TicketStatus.ESCALATED:
                escalated = await self._auto_escalate_ticket(
                    ticket, "Resolution SLA breach - auto-escalated"
                )
                result["escalated"] = escalated

        logger.warning(
            f"Resolution SLA breach for ticket {ticket.ticket_id} "
            f"(due: {ticket.resolution_due}, action: {breach_action.value})"
        )

        return result

    def _get_breach_action(self, ticket: Ticket) -> SLABreachAction:
        """
        Get the breach action configuration for a ticket.

        Checks ticket-specific SLA config first, then falls back to priority defaults.
        """
        # Check ticket-specific SLA config
        if ticket.sla_config:
            config = ticket.get_sla_config_v2() if hasattr(ticket, 'get_sla_config_v2') else None
            if config and config.breach_action:
                return config.breach_action

        # Fall back to priority-based default
        priority = ticket.priority
        if priority in DEFAULT_SLA_CONFIG:
            return DEFAULT_SLA_CONFIG[priority]["breach_action"]

        # Default to notify only
        return SLABreachAction.NOTIFY_ONLY

    async def _send_breach_notifications(
        self,
        ticket: Ticket,
        breach_type: str,
        message: str
    ) -> List[str]:
        """
        Send SLA breach notifications to relevant parties.

        Args:
            ticket: The ticket that breached SLA
            breach_type: "response" or "resolution"
            message: Notification message

        Returns:
            List of user IDs notified
        """
        import uuid

        notified = []
        now = datetime.now(timezone.utc)

        # Determine who to notify
        recipients = []

        # Always notify assigned analyst
        if ticket.assigned_analyst_id:
            recipients.append({
                "user_id": ticket.assigned_analyst_id,
                "severity": NotificationSeverity.HIGH
            })

        # Notify authority for critical/emergency or resolution breaches
        if ticket.priority in [TicketPriority.EMERGENCY, TicketPriority.CRITICAL] or breach_type == "resolution":
            if ticket.authority_id:
                recipients.append({
                    "user_id": ticket.authority_id,
                    "severity": NotificationSeverity.CRITICAL
                })
            if ticket.assigned_authority_id and ticket.assigned_authority_id != ticket.authority_id:
                recipients.append({
                    "user_id": ticket.assigned_authority_id,
                    "severity": NotificationSeverity.CRITICAL
                })

        # Send notifications
        for recipient in recipients:
            notification_id = f"NTF-{now.strftime('%Y%m%d')}-{uuid.uuid4().hex[:8].upper()}"

            notification_doc = {
                "notification_id": notification_id,
                "user_id": recipient["user_id"],
                "type": NotificationType.SLA_BREACH.value if hasattr(NotificationType, 'SLA_BREACH') else "sla_breach",
                "severity": recipient["severity"].value,
                "title": f"SLA Breach: {breach_type.title()} SLA",
                "message": f"{message}\nTicket: {ticket.title}",
                "ticket_id": ticket.ticket_id,
                "report_id": ticket.report_id,
                "action_url": f"/tickets/{ticket.ticket_id}",
                "action_label": "View Ticket",
                "is_read": False,
                "is_dismissed": False,
                "metadata": {
                    "breach_type": breach_type,
                    "priority": ticket.priority.value,
                    "sla_due": ticket.response_due.isoformat() if breach_type == "response" else ticket.resolution_due.isoformat()
                },
                "created_at": now
            }

            await self.db.notifications.insert_one(notification_doc)
            notified.append(recipient["user_id"])

        return notified

    async def _auto_escalate_ticket(self, ticket: Ticket, reason: str) -> bool:
        """
        Auto-escalate a ticket due to SLA breach.

        Args:
            ticket: The ticket to escalate
            reason: Reason for escalation

        Returns:
            True if escalated, False otherwise
        """
        import uuid

        now = datetime.now(timezone.utc)

        # Don't escalate if already escalated
        if ticket.status == TicketStatus.ESCALATED:
            return False

        # Determine new priority (bump up if possible)
        new_priority = ticket.priority
        priority_order = [
            TicketPriority.LOW,
            TicketPriority.MEDIUM,
            TicketPriority.HIGH,
            TicketPriority.CRITICAL,
            TicketPriority.EMERGENCY
        ]

        current_index = priority_order.index(ticket.priority)
        if current_index < len(priority_order) - 1:
            new_priority = priority_order[current_index + 1]

        # Update ticket
        await self.db.tickets.update_one(
            {"ticket_id": ticket.ticket_id},
            {
                "$set": {
                    "status": TicketStatus.ESCALATED.value,
                    "is_escalated": True,
                    "escalation_reason": reason,
                    "escalation_count": (ticket.escalation_count or 0) + 1,
                    "priority": new_priority.value,
                    "updated_at": now
                }
            }
        )

        # Create escalation record
        escalation_id = f"ESC-{uuid.uuid4().hex[:12].upper()}"
        escalation_doc = {
            "escalation_id": escalation_id,
            "ticket_id": ticket.ticket_id,
            "escalated_by_id": "SYSTEM",
            "escalated_by_name": "SLA Auto-Escalation",
            "escalated_by_role": "system",
            "reason": reason,
            "previous_priority": ticket.priority.value,
            "new_priority": new_priority.value,
            "previous_status": ticket.status.value,
            "new_status": TicketStatus.ESCALATED.value,
            "created_at": now
        }
        await self.db.ticket_escalations.insert_one(escalation_doc)

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

        logger.info(f"Auto-escalated ticket {ticket.ticket_id} due to SLA breach")
        return True

    async def check_single_ticket_sla(self, ticket_id: str) -> Dict[str, Any]:
        """
        Check SLA status for a single ticket.

        Args:
            ticket_id: The ticket ID to check

        Returns:
            SLA status information
        """
        doc = await self.db.tickets.find_one({"ticket_id": ticket_id})
        if not doc:
            raise ValueError(f"Ticket {ticket_id} not found")

        ticket = Ticket.from_mongo(doc)
        now = datetime.now(timezone.utc)

        result = {
            "ticket_id": ticket_id,
            "checked_at": now.isoformat(),
            "response_sla": {
                "due": ticket.response_due.isoformat() if ticket.response_due else None,
                "breached": ticket.sla_response_breached,
                "breached_at": ticket.sla_response_breached_at.isoformat() if hasattr(ticket, 'sla_response_breached_at') and ticket.sla_response_breached_at else None,
                "first_response_at": ticket.first_response_at.isoformat() if ticket.first_response_at else None,
                "time_remaining": None,
                "is_overdue": False
            },
            "resolution_sla": {
                "due": ticket.resolution_due.isoformat() if ticket.resolution_due else None,
                "breached": ticket.sla_resolution_breached,
                "breached_at": ticket.sla_resolution_breached_at.isoformat() if hasattr(ticket, 'sla_resolution_breached_at') and ticket.sla_resolution_breached_at else None,
                "resolved_at": ticket.resolved_at.isoformat() if ticket.resolved_at else None,
                "time_remaining": None,
                "is_overdue": False
            }
        }

        # Calculate response time remaining
        if ticket.response_due and not ticket.first_response_at:
            remaining = ticket.response_due - now
            result["response_sla"]["time_remaining"] = str(remaining) if remaining.total_seconds() > 0 else "OVERDUE"
            result["response_sla"]["is_overdue"] = remaining.total_seconds() <= 0

        # Calculate resolution time remaining
        if ticket.resolution_due and ticket.status not in [TicketStatus.RESOLVED, TicketStatus.CLOSED]:
            remaining = ticket.resolution_due - now
            result["resolution_sla"]["time_remaining"] = str(remaining) if remaining.total_seconds() > 0 else "OVERDUE"
            result["resolution_sla"]["is_overdue"] = remaining.total_seconds() <= 0

        return result

    async def get_sla_metrics(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Get SLA metrics for the specified period.

        Args:
            start_date: Start of period (defaults to 30 days ago)
            end_date: End of period (defaults to now)

        Returns:
            SLA metrics dictionary
        """
        if not end_date:
            end_date = datetime.now(timezone.utc)
        if not start_date:
            start_date = end_date - timedelta(days=30)

        # Aggregate SLA statistics
        pipeline = [
            {
                "$match": {
                    "created_at": {"$gte": start_date, "$lte": end_date}
                }
            },
            {
                "$group": {
                    "_id": None,
                    "total_tickets": {"$sum": 1},
                    "response_breaches": {
                        "$sum": {"$cond": ["$sla_response_breached", 1, 0]}
                    },
                    "resolution_breaches": {
                        "$sum": {"$cond": ["$sla_resolution_breached", 1, 0]}
                    },
                    "resolved_count": {
                        "$sum": {"$cond": [{"$in": ["$status", ["resolved", "closed"]]}, 1, 0]}
                    }
                }
            }
        ]

        result = await self.db.tickets.aggregate(pipeline).to_list(1)

        if result:
            stats = result[0]
            total = stats.get("total_tickets", 0)
            response_breaches = stats.get("response_breaches", 0)
            resolution_breaches = stats.get("resolution_breaches", 0)
            resolved = stats.get("resolved_count", 0)

            response_compliance = (total - response_breaches) / total if total > 0 else 1.0
            resolution_compliance = (total - resolution_breaches) / total if total > 0 else 1.0
            overall_compliance = ((total * 2) - response_breaches - resolution_breaches) / (total * 2) if total > 0 else 1.0
        else:
            total = 0
            response_breaches = 0
            resolution_breaches = 0
            resolved = 0
            response_compliance = 1.0
            resolution_compliance = 1.0
            overall_compliance = 1.0

        # Get breaches by priority
        priority_pipeline = [
            {
                "$match": {
                    "created_at": {"$gte": start_date, "$lte": end_date},
                    "$or": [
                        {"sla_response_breached": True},
                        {"sla_resolution_breached": True}
                    ]
                }
            },
            {
                "$group": {
                    "_id": "$priority",
                    "count": {"$sum": 1}
                }
            }
        ]
        priority_result = await self.db.tickets.aggregate(priority_pipeline).to_list(10)
        breaches_by_priority = {item["_id"]: item["count"] for item in priority_result}

        return {
            "period_start": start_date.isoformat(),
            "period_end": end_date.isoformat(),
            "total_tickets": total,
            "response_breaches": response_breaches,
            "resolution_breaches": resolution_breaches,
            "resolved_tickets": resolved,
            "response_sla_compliance": round(response_compliance * 100, 2),
            "resolution_sla_compliance": round(resolution_compliance * 100, 2),
            "overall_sla_compliance": round(overall_compliance * 100, 2),
            "breaches_by_priority": breaches_by_priority
        }

    async def update_ticket_sla_config(
        self,
        ticket_id: str,
        response_hours: Optional[int] = None,
        resolution_hours: Optional[int] = None,
        breach_action: Optional[SLABreachAction] = None,
        user: Optional[User] = None
    ) -> Dict[str, Any]:
        """
        Update SLA configuration for a specific ticket.

        Args:
            ticket_id: The ticket to update
            response_hours: New response SLA hours
            resolution_hours: New resolution SLA hours
            breach_action: New breach action
            user: User making the change (for audit)

        Returns:
            Updated SLA configuration
        """
        doc = await self.db.tickets.find_one({"ticket_id": ticket_id})
        if not doc:
            raise ValueError(f"Ticket {ticket_id} not found")

        ticket = Ticket.from_mongo(doc)
        now = datetime.now(timezone.utc)

        # Build update
        update_data = {"updated_at": now}

        # Get existing SLA config or create new
        existing_config = ticket.sla_config or {}

        if response_hours is not None:
            existing_config["response_hours"] = response_hours
            # Recalculate response_due
            update_data["response_due"] = ticket.created_at + timedelta(hours=response_hours)

        if resolution_hours is not None:
            existing_config["resolution_hours"] = resolution_hours
            # Recalculate resolution_due
            update_data["resolution_due"] = ticket.created_at + timedelta(hours=resolution_hours)

        if breach_action is not None:
            existing_config["breach_action"] = breach_action.value

        existing_config["priority"] = ticket.priority.value
        update_data["sla_config"] = existing_config

        await self.db.tickets.update_one(
            {"ticket_id": ticket_id},
            {"$set": update_data}
        )

        logger.info(f"Updated SLA config for ticket {ticket_id}: {existing_config}")

        return {
            "ticket_id": ticket_id,
            "sla_config": existing_config,
            "response_due": update_data.get("response_due", ticket.response_due).isoformat() if update_data.get("response_due", ticket.response_due) else None,
            "resolution_due": update_data.get("resolution_due", ticket.resolution_due).isoformat() if update_data.get("resolution_due", ticket.resolution_due) else None
        }


# Singleton instance
_sla_service: Optional[SLAService] = None


def get_sla_service(db: AsyncIOMotorDatabase) -> SLAService:
    """Get or create SLA service instance."""
    global _sla_service
    if _sla_service is None:
        _sla_service = SLAService(db)
    return _sla_service
