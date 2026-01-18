"""
Auto Ticket Generation Service (V2)
Automatically creates tickets with comprehensive insights when reports are approved.

V2 Changes:
- Atomic ticket creation to prevent double-ticket race conditions
- Uses new TicketAssignment and TicketApproval embedded models
- Uses null instead of "PENDING_ASSIGNMENT" for unassigned fields
- Updates ticket_creation_status atomically on the report
- Tracks approval source (AI_AUTO, AI_RECOMMENDED, AUTHORITY_MANUAL, ANALYST_VERIFIED)
"""

import logging
import uuid
from datetime import datetime, timezone
from typing import Optional, Dict, Any, Tuple

from motor.motor_asyncio import AsyncIOMotorDatabase
from pymongo import ReturnDocument
from pymongo.errors import DuplicateKeyError

from app.models.hazard import HazardReport, VerificationStatus, ApprovalSource, TicketCreationStatus
from app.models.ticket import (
    Ticket, TicketMessage, TicketActivity, TicketStatus, TicketPriority,
    MessageType, ActivityType, calculate_sla_deadlines,
    AssignmentStatus, TicketAssignment, TicketApproval, TicketSLAConfig, SLABreachAction
)
from app.models.user import User, UserRole
from app.models.notification import NotificationType, NotificationSeverity

logger = logging.getLogger(__name__)


class AutoTicketService:
    """Service for automatically generating tickets from approved reports"""

    # Map threat levels to ticket priorities
    THREAT_TO_PRIORITY = {
        "warning": TicketPriority.EMERGENCY,
        "alert": TicketPriority.CRITICAL,
        "watch": TicketPriority.HIGH,
        "no_threat": TicketPriority.MEDIUM
    }

    # Map verification scores to priorities
    SCORE_TO_PRIORITY = {
        (90, 100): TicketPriority.HIGH,
        (75, 90): TicketPriority.MEDIUM,
        (0, 75): TicketPriority.LOW
    }

    def __init__(self, db: AsyncIOMotorDatabase = None):
        self.db = db

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

    def _determine_priority(self, report: Dict[str, Any]) -> TicketPriority:
        """Determine ticket priority based on threat level and verification score"""
        # Check threat level first
        hazard_class = report.get("hazard_classification", {})
        if hazard_class:
            threat_level = hazard_class.get("threat_level")
            if threat_level in self.THREAT_TO_PRIORITY:
                return self.THREAT_TO_PRIORITY[threat_level]

        # Fall back to verification score
        score = report.get("verification_score", 0) or 0
        if score >= 90:
            return TicketPriority.HIGH
        elif score >= 75:
            return TicketPriority.MEDIUM
        else:
            return TicketPriority.LOW

    def _build_insights_message(self, report: Dict[str, Any]) -> str:
        """Build a comprehensive insights message for the ticket"""
        lines = []
        lines.append("=" * 60)
        lines.append("HAZARD REPORT VERIFICATION SUMMARY")
        lines.append("=" * 60)
        lines.append("")

        # Basic Info
        lines.append(f"Report ID: {report.get('report_id', 'N/A')}")
        lines.append(f"Hazard Type: {report.get('hazard_type', 'N/A')}")
        lines.append(f"Category: {report.get('category', 'N/A')}")
        lines.append(f"Reporter: {report.get('user_name') or 'Anonymous'}")
        lines.append("")

        # Verification Score (PROMINENT)
        lines.append("-" * 40)
        lines.append("VERIFICATION SCORES")
        lines.append("-" * 40)
        score = report.get("verification_score", 0) or 0
        lines.append(f"Overall Score: {score:.1f}%")

        # Score breakdown
        if report.get("verification_result"):
            vr = report["verification_result"]
            decision = vr.get("decision", "pending")
            lines.append(f"AI Decision: {decision.upper().replace('_', ' ')}")
            lines.append("")

            layer_results = vr.get("layer_results", [])
            if layer_results:
                lines.append("Layer Breakdown:")
                for lr in layer_results:
                    layer_name = lr.get("layer_name", "unknown")
                    layer_score = lr.get("score", 0) * 100
                    layer_status = lr.get("status", "unknown")
                    layer_weight = lr.get("weight", 0) * 100
                    status_icon = "✓" if layer_status == "pass" else "✗" if layer_status == "fail" else "○"
                    lines.append(f"  {status_icon} {layer_name.title()}: {layer_score:.1f}% (weight: {layer_weight:.0f}%)")
                    reasoning = lr.get("reasoning", "")
                    if reasoning:
                        lines.append(f"      └─ {reasoning[:100]}...")
                lines.append("")

        # Location Info
        lines.append("-" * 40)
        lines.append("LOCATION")
        lines.append("-" * 40)
        location = report.get("location", {})
        lines.append(f"Address: {location.get('address', 'N/A')}")
        lines.append(f"Coordinates: {location.get('latitude', 'N/A')}, {location.get('longitude', 'N/A')}")
        if location.get("region"):
            lines.append(f"Region: {location.get('region')}")

        # Geofence validation
        if report.get("geofence_valid") is not None:
            geofence_status = "Valid (Coastal Area)" if report.get("geofence_valid") else "Invalid (Inland)"
            lines.append(f"Geofence: {geofence_status}")
        if report.get("geofence_distance_km") is not None:
            lines.append(f"Distance to Coast: {report.get('geofence_distance_km'):.2f} km")
        lines.append("")

        # Environmental Conditions
        if report.get("environmental_snapshot"):
            lines.append("-" * 40)
            lines.append("ENVIRONMENTAL CONDITIONS")
            lines.append("-" * 40)
            env = report["environmental_snapshot"]

            if env.get("weather"):
                w = env["weather"]
                lines.append(f"Weather: {w.get('condition', 'N/A')}")
                lines.append(f"Temperature: {w.get('temp_c', 'N/A')}°C (Feels: {w.get('feelslike_c', 'N/A')}°C)")
                lines.append(f"Wind: {w.get('wind_kph', 'N/A')} km/h {w.get('wind_dir', '')}")
                if w.get("gust_kph"):
                    lines.append(f"Wind Gusts: {w.get('gust_kph')} km/h")
                lines.append(f"Visibility: {w.get('vis_km', 'N/A')} km")
                lines.append(f"Humidity: {w.get('humidity', 'N/A')}%")

            if env.get("marine"):
                m = env["marine"]
                lines.append("")
                lines.append("Marine Conditions:")
                if m.get("sig_ht_mt"):
                    lines.append(f"  Wave Height: {m.get('sig_ht_mt')} m")
                if m.get("swell_ht_mt"):
                    lines.append(f"  Swell: {m.get('swell_ht_mt')} m ({m.get('swell_dir_16_point', '')})")
                if m.get("water_temp_c"):
                    lines.append(f"  Water Temp: {m.get('water_temp_c')}°C")

            if env.get("seismic") and env["seismic"].get("magnitude"):
                s = env["seismic"]
                lines.append("")
                lines.append("Seismic Activity:")
                lines.append(f"  Magnitude: {s.get('magnitude')}")
                lines.append(f"  Location: {s.get('place', 'N/A')}")
                if s.get("tsunami"):
                    lines.append(f"  Tsunami Warning: {'YES' if s.get('tsunami') else 'No'}")

            lines.append("")

        # Threat Classification
        if report.get("hazard_classification"):
            hc = report["hazard_classification"]
            lines.append("-" * 40)
            lines.append("THREAT ASSESSMENT")
            lines.append("-" * 40)
            threat_level = hc.get("threat_level", "unknown")
            threat_icon = "🔴" if threat_level == "warning" else "🟠" if threat_level == "alert" else "🟡" if threat_level == "watch" else "🟢"
            lines.append(f"Threat Level: {threat_icon} {threat_level.upper()}")
            if hc.get("hazard_type"):
                lines.append(f"Detected Hazard: {hc.get('hazard_type')}")
            if hc.get("confidence"):
                lines.append(f"Confidence: {hc.get('confidence') * 100:.1f}%")
            if hc.get("reasoning"):
                lines.append(f"Assessment: {hc.get('reasoning')}")

            # Individual threat levels
            threat_types = ["tsunami_threat", "cyclone_threat", "high_waves_threat", "coastal_flood_threat", "rip_current_threat"]
            active_threats = []
            for tt in threat_types:
                if hc.get(tt) and hc.get(tt) != "no_threat":
                    active_threats.append(f"{tt.replace('_threat', '').replace('_', ' ').title()}: {hc.get(tt)}")
            if active_threats:
                lines.append("")
                lines.append("Active Threat Indicators:")
                for threat in active_threats:
                    lines.append(f"  • {threat}")

            lines.append("")

        # Image Analysis
        if report.get("vision_classification"):
            vc = report["vision_classification"]
            lines.append("-" * 40)
            lines.append("IMAGE ANALYSIS")
            lines.append("-" * 40)
            lines.append(f"Predicted Class: {vc.get('predicted_class', 'N/A')}")
            if vc.get("confidence_scores"):
                lines.append("Confidence Scores:")
                for cls, conf in vc.get("confidence_scores", {}).items():
                    lines.append(f"  • {cls}: {conf * 100:.1f}%")
            lines.append("")

        # Recommendations
        if report.get("hazard_classification", {}).get("recommendations"):
            recs = report["hazard_classification"]["recommendations"]
            lines.append("-" * 40)
            lines.append("RECOMMENDATIONS")
            lines.append("-" * 40)
            for i, rec in enumerate(recs, 1):
                lines.append(f"{i}. {rec}")
            lines.append("")

        # Reporter Description
        if report.get("description"):
            lines.append("-" * 40)
            lines.append("REPORTER'S DESCRIPTION")
            lines.append("-" * 40)
            lines.append(report.get("description"))
            lines.append("")

        lines.append("=" * 60)
        lines.append(f"Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}")
        lines.append("=" * 60)

        return "\n".join(lines)

    async def create_ticket_for_approved_report(
        self,
        report_doc: Dict[str, Any],
        approver: Optional[User] = None,
        approval_type: str = "auto",  # "auto", "manual", or "ai_recommended"
        db: AsyncIOMotorDatabase = None
    ) -> Optional[Tuple[Ticket, TicketMessage]]:
        """
        Create a ticket with comprehensive insights for an approved report.

        V2: Uses atomic operations to prevent double-ticket race conditions.

        Args:
            report_doc: The hazard report document
            approver: User who approved (None for auto-approval)
            approval_type: "auto" for AI approval, "manual" for authority approval,
                          "ai_recommended" for AI-recommended + authority confirmed
            db: Database connection

        Returns:
            Tuple of (Ticket, initial message) or None if ticket already exists
        """
        db = db if db is not None else self.db

        report_id = report_doc.get("report_id")
        now = datetime.now(timezone.utc)

        # V2: ATOMIC LOCK - Try to set ticket_creation_status to PENDING atomically
        # This prevents race conditions where two processes try to create tickets simultaneously
        lock_result = await db.hazard_reports.find_one_and_update(
            {
                "report_id": report_id,
                "$or": [
                    {"ticket_creation_status": TicketCreationStatus.NOT_ELIGIBLE.value},
                    {"ticket_creation_status": {"$exists": False}},
                    {"ticket_creation_status": None}
                ]
            },
            {
                "$set": {
                    "ticket_creation_status": TicketCreationStatus.PENDING.value,
                    "ticket_creation_attempted_at": now
                }
            },
            return_document=ReturnDocument.AFTER
        )

        if not lock_result:
            # Either report doesn't exist, or ticket creation already in progress/completed
            existing_report = await db.hazard_reports.find_one({"report_id": report_id})
            if existing_report:
                status = existing_report.get("ticket_creation_status")
                if status == TicketCreationStatus.CREATED.value:
                    logger.info(f"Ticket already exists for report {report_id}")
                    return None
                elif status == TicketCreationStatus.PENDING.value:
                    logger.info(f"Ticket creation already in progress for report {report_id}")
                    return None
            logger.warning(f"Could not acquire ticket creation lock for report {report_id}")
            return None

        try:
            ticket_id = self._generate_ticket_id()

            # Determine priority
            priority = self._determine_priority(report_doc)

            # Calculate SLA deadlines
            sla = calculate_sla_deadlines(priority, now)

            # Build title
            hazard_type = report_doc.get("hazard_type", "Unknown Hazard")
            location = report_doc.get("location", {})
            location_str = location.get("address") or location.get("region") or f"{location.get('latitude', 0):.4f}, {location.get('longitude', 0):.4f}"
            title = f"[{approval_type.upper()}] {hazard_type} at {location_str[:50]}"

            # V2: Build TicketAssignment structure (replaces scattered fields)
            analyst_id = None
            analyst_name = None
            authority_id = None
            authority_name = None
            assignment_status = AssignmentStatus.UNASSIGNED

            if approver:
                approver_name = getattr(approver, 'name', None) or approver.email or "Unknown"

                if approver.role in [UserRole.AUTHORITY, UserRole.AUTHORITY_ADMIN]:
                    # Authority approved - fully assigned
                    authority_id = approver.user_id
                    authority_name = approver_name
                    analyst_id = approver.user_id  # They're handling it directly
                    analyst_name = approver_name
                    assignment_status = AssignmentStatus.FULLY_ASSIGNED
                else:
                    # Analyst approved - analyst only
                    analyst_id = approver.user_id
                    analyst_name = approver_name
                    # V2: Use null instead of "PENDING_ASSIGNMENT"
                    authority_id = None
                    authority_name = None
                    assignment_status = AssignmentStatus.ANALYST_ONLY
            else:
                # No approver (auto-approval) - unassigned
                assignment_status = AssignmentStatus.UNASSIGNED

            # V2: Create TicketAssignment embedded document
            assignment = TicketAssignment(
                analyst_id=analyst_id,
                analyst_name=analyst_name,
                analyst_assigned_at=now if analyst_id else None,
                analyst_assigned_by=approver.user_id if approver and analyst_id else None,
                authority_id=authority_id,
                authority_name=authority_name,
                authority_assigned_at=now if authority_id else None,
                authority_assigned_by=approver.user_id if approver and authority_id else None,
                status=assignment_status
            )

            # V2: Determine approval source
            if approval_type == "auto":
                approval_source = ApprovalSource.AI_AUTO
            elif approval_type == "ai_recommended":
                approval_source = ApprovalSource.AI_RECOMMENDED
            elif approver and approver.role in [UserRole.AUTHORITY, UserRole.AUTHORITY_ADMIN]:
                approval_source = ApprovalSource.AUTHORITY_MANUAL
            else:
                approval_source = ApprovalSource.ANALYST_VERIFIED

            # V2: Create TicketApproval embedded document
            approval = TicketApproval(
                approval_source=approval_source,
                approved_by_id=approver.user_id if approver else None,
                approved_by_name=approver_name if approver else None,
                approved_by_role="authority" if approver and approver.role in [UserRole.AUTHORITY, UserRole.AUTHORITY_ADMIN] else ("analyst" if approver else "ai"),
                ai_verification_score=report_doc.get("verification_score"),
                approved_at=now,
                approval_notes=None
            )

            # V2: Create SLA config
            sla_config = TicketSLAConfig(
                priority=priority,
                response_hours=sla.get("response_hours", 24),
                resolution_hours=sla.get("resolution_hours", 72),
                breach_action=SLABreachAction.NOTIFY_ONLY
            )

            # Determine ticket status
            ticket_status = TicketStatus.ASSIGNED if analyst_id else TicketStatus.OPEN

            # Create ticket with V2 structure
            ticket = Ticket(
                ticket_id=ticket_id,
                report_id=report_id,
                hazard_type=hazard_type,
                title=title,
                description=report_doc.get("description", ""),
                location_latitude=location.get("latitude", 0),
                location_longitude=location.get("longitude", 0),
                location_address=location.get("address"),
                status=ticket_status,
                priority=priority,
                reporter_id=report_doc.get("user_id") or "UNKNOWN",
                reporter_name=report_doc.get("user_name") or "Unknown Reporter",
                # Legacy fields (for backward compatibility)
                assigned_analyst_id=analyst_id,
                assigned_analyst_name=analyst_name,
                authority_id=authority_id,
                authority_name=authority_name,
                assigned_authority_id=authority_id,
                assigned_authority_name=authority_name,
                approved_by=approver.user_id if approver else None,
                approved_by_name=approver_name if approver else None,
                approved_by_role=approval.approved_by_role,
                # V2 embedded structures
                assignment=assignment.model_dump(),
                approval=approval.model_dump(),
                sla_config=sla_config.model_dump(),
                sync_version=0,
                # SLA deadlines
                response_due=sla["response_due"],
                resolution_due=sla["resolution_due"],
                tags=[hazard_type, approval_type, priority.value],
                created_at=now,
                updated_at=now,
                metadata={
                    "verification_score": report_doc.get("verification_score"),
                    "threat_level": report_doc.get("hazard_classification", {}).get("threat_level") if report_doc.get("hazard_classification") else None,
                    "approval_type": approval_type,
                    "approval_source": approval_source.value,
                    "auto_generated": True
                }
            )

            # V2: Save ticket with duplicate key handling
            try:
                await db.tickets.insert_one(ticket.to_mongo())
            except DuplicateKeyError:
                logger.warning(f"Duplicate ticket for report {report_id}, rolling back")
                await db.hazard_reports.update_one(
                    {"report_id": report_id},
                    {"$set": {"ticket_creation_status": TicketCreationStatus.NOT_ELIGIBLE.value}}
                )
                return None

            # Create comprehensive insights message
            insights_content = self._build_insights_message(report_doc)

            # Build participants info
            authority_display = authority_name if authority_name else "Pending Assignment"
            participants_info = f"""
TICKET PARTICIPANTS:
- Reporter: {report_doc.get('user_name') or 'Unknown Reporter'} (ID: {report_doc.get('user_id') or 'UNKNOWN'})
- Assigned Analyst: {analyst_name or 'Not Assigned'} {f'(ID: {analyst_id})' if analyst_id else ''}
- Authority: {authority_display}
"""

            # V2: Create initial system message with insights and thread
            initial_message = TicketMessage(
                message_id=self._generate_message_id(),
                ticket_id=ticket_id,
                sender_id="SYSTEM",
                sender_name="AI Verification System",
                sender_role="system",
                message_type=MessageType.SYSTEM,
                content=f"""Ticket auto-generated for {'AI-approved' if approval_type == 'auto' else ('AI-recommended and confirmed' if approval_type == 'ai_recommended' else 'manually approved')} hazard report.

VERIFICATION SCORE: {report_doc.get('verification_score', 0):.1f}%
PRIORITY: {priority.value.upper()}
APPROVAL SOURCE: {approval_source.value.upper()}
SLA Response Due: {sla['response_due'].strftime('%Y-%m-%d %H:%M UTC')}
SLA Resolution Due: {sla['resolution_due'].strftime('%Y-%m-%d %H:%M UTC')}
{participants_info}

{insights_content}""",
                is_internal=False,
                thread="all",  # V2: Default thread for system messages
                visible_to=[],  # V2: Empty = visible to all
                created_at=now
            )
            await db.ticket_messages.insert_one(initial_message.model_dump())

            # Update ticket message count
            await db.tickets.update_one(
                {"ticket_id": ticket_id},
                {"$set": {
                    "total_messages": 1,
                    "last_message_at": now,
                    "last_message_by": "SYSTEM"
                }}
            )

            # Log activity
            activity = TicketActivity(
                activity_id=self._generate_activity_id(),
                ticket_id=ticket_id,
                activity_type=ActivityType.TICKET_CREATED,
                performed_by_id=approver.user_id if approver else "SYSTEM",
                performed_by_name=approver_name if approver else "AI System",
                performed_by_role="system" if approval_type == "auto" else approval.approved_by_role,
                description=f"Ticket auto-generated for {approval_type} approved report with score {report_doc.get('verification_score', 0):.1f}%",
                details={
                    "report_id": report_id,
                    "priority": priority.value,
                    "approval_type": approval_type,
                    "approval_source": approval_source.value,
                    "verification_score": report_doc.get("verification_score")
                },
                created_at=now
            )
            await db.ticket_activities.insert_one(activity.model_dump())

            # V2: Update hazard report with ticket reference AND ticket_creation_status atomically
            await db.hazard_reports.update_one(
                {"report_id": report_id},
                {"$set": {
                    "ticket_id": ticket_id,
                    "has_ticket": True,
                    "ticket_status": ticket_status.value,
                    "ticket_created_at": now,
                    "ticket_creation_status": TicketCreationStatus.CREATED.value,
                    "updated_at": now
                }}
            )

            # Create notification for reporter
            await self._create_notification(
                user_id=report_doc.get("user_id"),
                notification_type=NotificationType.TICKET_CREATED,
                severity=NotificationSeverity.MEDIUM,
                title="Your Report Has Been Verified",
                message=f"Your hazard report has been {'automatically' if approval_type == 'auto' else ''} verified and a support ticket has been created: {title}",
                ticket_id=ticket_id,
                report_id=report_id,
                metadata={
                    "priority": priority.value,
                    "verification_score": report_doc.get("verification_score"),
                    "approval_type": approval_type
                },
                db=db
            )

            # Notify the assigned analyst that they are now assigned to this ticket
            if analyst_id and analyst_id != report_doc.get("user_id"):
                await self._create_notification(
                    user_id=analyst_id,
                    notification_type=NotificationType.TICKET_ASSIGNED,
                    severity=NotificationSeverity.HIGH,
                    title="New Ticket Assigned to You",
                    message=f"A ticket has been created and assigned to you for the report you approved: {title}",
                    ticket_id=ticket_id,
                    report_id=report_id,
                    metadata={
                        "priority": priority.value,
                        "verification_score": report_doc.get("verification_score"),
                        "reporter_name": report_doc.get("user_name", "Unknown Reporter")
                    },
                    db=db
                )

            logger.info(
                f"Auto-generated ticket {ticket_id} for {approval_type} approved report {report_id} "
                f"(score: {report_doc.get('verification_score', 0):.1f}%, priority: {priority.value}, "
                f"approval_source: {approval_source.value})"
            )

            return ticket, initial_message

        except Exception as e:
            # V2: On error, reset ticket_creation_status to FAILED
            logger.error(f"Error creating ticket for report {report_id}: {e}")
            await db.hazard_reports.update_one(
                {"report_id": report_id},
                {"$set": {"ticket_creation_status": TicketCreationStatus.FAILED.value}}
            )
            raise

    async def _create_notification(
        self,
        user_id: str,
        notification_type: NotificationType,
        severity: NotificationSeverity,
        title: str,
        message: str,
        ticket_id: str,
        report_id: str,
        metadata: Dict[str, Any] = None,
        db: AsyncIOMotorDatabase = None
    ):
        """Create a notification for ticket creation"""
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
            "action_url": f"/tickets/{ticket_id}",
            "action_label": "View Ticket",
            "is_read": False,
            "is_dismissed": False,
            "metadata": metadata or {},
            "created_at": datetime.now(timezone.utc)
        }

        await db.notifications.insert_one(notification_doc)


# Singleton instance
_auto_ticket_service: Optional[AutoTicketService] = None


def get_auto_ticket_service(db: AsyncIOMotorDatabase = None) -> AutoTicketService:
    """Get or create auto ticket service singleton"""
    global _auto_ticket_service
    if _auto_ticket_service is None:
        _auto_ticket_service = AutoTicketService(db)
    elif db is not None:
        _auto_ticket_service.db = db
    return _auto_ticket_service
