"""
Notification Model
For sending alerts and updates to citizens
"""

from datetime import datetime, timezone
from typing import Optional, Dict, Any
from enum import Enum
from pydantic import BaseModel, Field
from bson import ObjectId
from app.utils.timezone import to_ist_isoformat


class NotificationType(str, Enum):
    """Types of notifications"""
    ALERT = "alert"  # Authority-created alert
    REPORT_UPDATE = "report_update"  # Update on user's hazard report
    VERIFICATION = "verification"  # Report verification status
    SYSTEM = "system"  # System notifications
    ANNOUNCEMENT = "announcement"  # General announcements
    SMI_ALERT = "smi_alert"  # Social Media Intelligence alert
    # Ticket-related notifications
    TICKET_CREATED = "ticket_created"  # Ticket created for a report
    TICKET_ASSIGNED = "ticket_assigned"  # Ticket assigned to analyst
    TICKET_STATUS = "ticket_status"  # Ticket status changed
    TICKET_MESSAGE = "ticket_message"  # New message in ticket
    TICKET_ESCALATED = "ticket_escalated"  # Ticket escalated
    TICKET_RESOLVED = "ticket_resolved"  # Ticket resolved
    TICKET_CLOSED = "ticket_closed"  # Ticket closed


class NotificationSeverity(str, Enum):
    """Notification severity/priority levels"""
    INFO = "info"  # Informational
    LOW = "low"  # Low priority
    MEDIUM = "medium"  # Medium priority
    HIGH = "high"  # High priority
    CRITICAL = "critical"  # Critical - immediate attention required


class Notification(BaseModel):
    """Notification document model for MongoDB"""

    id: Optional[str] = Field(default=None, alias="_id")

    # Notification identification
    notification_id: str = Field(..., description="Unique notification identifier")
    user_id: str = Field(..., description="User ID this notification is for")

    # Notification details
    type: NotificationType = Field(..., description="Type of notification")
    severity: NotificationSeverity = Field(
        default=NotificationSeverity.INFO,
        description="Severity/priority level"
    )
    title: str = Field(..., description="Notification title")
    message: str = Field(..., description="Notification message/body")

    # Related entities
    alert_id: Optional[str] = Field(default=None, description="Related alert ID")
    report_id: Optional[str] = Field(default=None, description="Related hazard report ID")
    smi_alert_id: Optional[str] = Field(default=None, description="Related SMI alert ID")
    ticket_id: Optional[str] = Field(default=None, description="Related ticket ID")

    # Geographic scope (for alert notifications)
    region: Optional[str] = Field(
        default=None,
        description="Region this notification applies to"
    )
    regions: list[str] = Field(
        default_factory=list,
        description="Multiple regions (for alerts affecting multiple areas)"
    )

    # Status tracking
    is_read: bool = Field(default=False, description="Whether user has read this")
    read_at: Optional[datetime] = Field(default=None, description="When notification was read")
    is_dismissed: bool = Field(default=False, description="Whether user dismissed this")
    dismissed_at: Optional[datetime] = Field(
        default=None,
        description="When notification was dismissed"
    )

    # Timing
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="When notification was created"
    )
    expires_at: Optional[datetime] = Field(
        default=None,
        description="When notification expires (auto-delete)"
    )

    # Action/Link
    action_url: Optional[str] = Field(
        default=None,
        description="URL/route to navigate when notification is clicked"
    )
    action_label: Optional[str] = Field(
        default=None,
        description="Label for action button (e.g., 'View Alert', 'View Report')"
    )

    # Metadata
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata (alert type, creator info, etc.)"
    )

    class Config:
        populate_by_name = True
        json_encoders = {
            ObjectId: str,
            datetime: lambda v: to_ist_isoformat(v)
        }
        json_schema_extra = {
            "example": {
                "notification_id": "NTF-20250124-001",
                "user_id": "USR-001",
                "type": "alert",
                "severity": "critical",
                "title": "Tsunami Warning",
                "message": "Tsunami alert issued for your region. Evacuate immediately to higher ground.",
                "alert_id": "ALT-001",
                "region": "Tamil Nadu",
                "action_url": "/alerts/ALT-001",
                "action_label": "View Alert Details"
            }
        }

    def to_mongo(self) -> Dict[str, Any]:
        """Convert to MongoDB document format"""
        data = self.model_dump(by_alias=True, exclude_none=True)
        if data.get("_id") is None:
            data.pop("_id", None)
        return data

    @classmethod
    def from_mongo(cls, data: Dict[str, Any]) -> "Notification":
        """Create Notification instance from MongoDB document"""
        if not data:
            return None

        # Convert ObjectId to string
        if "_id" in data:
            data["_id"] = str(data["_id"])

        # Ensure all datetime fields are timezone-aware
        datetime_fields = ["created_at", "read_at", "dismissed_at", "expires_at"]

        for field in datetime_fields:
            if field in data and data[field] is not None:
                dt_value = data[field]
                if isinstance(dt_value, datetime) and dt_value.tzinfo is None:
                    data[field] = dt_value.replace(tzinfo=timezone.utc)

        return cls(**data)


class NotificationResponse(BaseModel):
    """Schema for notification responses"""
    notification_id: str
    type: NotificationType
    severity: NotificationSeverity
    title: str
    message: str
    alert_id: Optional[str] = None
    report_id: Optional[str] = None
    smi_alert_id: Optional[str] = None
    ticket_id: Optional[str] = None
    region: Optional[str] = None
    is_read: bool
    read_at: Optional[datetime] = None
    created_at: datetime
    expires_at: Optional[datetime] = None
    action_url: Optional[str] = None
    action_label: Optional[str] = None
    metadata: Dict[str, Any] = {}

    class Config:
        from_attributes = True
        json_encoders = {
            datetime: lambda v: to_ist_isoformat(v)
        }


class NotificationStats(BaseModel):
    """Statistics about user's notifications"""
    total: int = 0
    unread: int = 0
    by_severity: Dict[str, int] = Field(default_factory=dict)
    by_type: Dict[str, int] = Field(default_factory=dict)
    latest_unread: Optional[NotificationResponse] = None
