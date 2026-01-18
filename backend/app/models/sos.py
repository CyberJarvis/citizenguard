"""
SOS Alert Model
MongoDB document model for fishermen emergency SOS alerts
"""

from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from enum import Enum
from pydantic import BaseModel, Field
from bson import ObjectId

from app.utils.timezone import to_ist_isoformat


class SOSStatus(str, Enum):
    """SOS Alert status enumeration"""
    ACTIVE = "active"
    ACKNOWLEDGED = "acknowledged"
    DISPATCHED = "dispatched"
    RESOLVED = "resolved"
    CANCELLED = "cancelled"


class SOSPriority(str, Enum):
    """SOS Priority levels"""
    CRITICAL = "critical"  # Life threatening
    HIGH = "high"          # Urgent assistance needed
    MEDIUM = "medium"      # Non-urgent assistance
    LOW = "low"            # Minor issue


class SOSAlert(BaseModel):
    """SOS Alert document model for fishermen emergency situations"""

    # MongoDB ObjectId (internal)
    id: Optional[str] = Field(default=None, alias="_id")

    # Unique SOS ID (format: SOS-YYYYMMDD-XXXX)
    sos_id: str = Field(..., description="Unique SOS identifier")

    # User information
    user_id: str = Field(..., description="User ID of the person triggering SOS")
    user_name: str = Field(..., description="Name of the person in distress")
    user_phone: str = Field(..., description="Phone number for contact")

    # Location (GeoJSON Point)
    location: Dict[str, Any] = Field(
        ...,
        description="GeoJSON Point: {type: 'Point', coordinates: [lon, lat]}"
    )

    # Readable location info
    latitude: float = Field(..., description="Latitude coordinate")
    longitude: float = Field(..., description="Longitude coordinate")
    location_address: Optional[str] = Field(default=None, description="Reverse geocoded address if available")

    # Additional context
    vessel_id: Optional[str] = Field(default=None, description="Fishing vessel registration number")
    vessel_name: Optional[str] = Field(default=None, description="Name of the vessel")
    crew_count: Optional[int] = Field(default=1, ge=1, description="Number of people on board")
    message: Optional[str] = Field(default=None, description="Optional distress message")

    # Status and priority
    status: SOSStatus = Field(default=SOSStatus.ACTIVE, description="Current SOS status")
    priority: SOSPriority = Field(default=SOSPriority.CRITICAL, description="Priority level")

    # Response tracking
    acknowledged_by: Optional[str] = Field(default=None, description="User ID of authority who acknowledged")
    acknowledged_at: Optional[datetime] = Field(default=None, description="When SOS was acknowledged")
    acknowledged_by_name: Optional[str] = Field(default=None, description="Name of acknowledging authority")

    dispatched_by: Optional[str] = Field(default=None, description="User ID who dispatched rescue")
    dispatched_at: Optional[datetime] = Field(default=None, description="When rescue was dispatched")
    dispatch_notes: Optional[str] = Field(default=None, description="Dispatch instructions/notes")

    resolved_by: Optional[str] = Field(default=None, description="User ID who resolved the SOS")
    resolved_at: Optional[datetime] = Field(default=None, description="When SOS was resolved")
    resolution_notes: Optional[str] = Field(default=None, description="Resolution details")

    # Notification tracking
    sms_sent: bool = Field(default=False, description="Whether SMS was sent to emergency contacts")
    sms_sent_at: Optional[datetime] = Field(default=None, description="When SMS was sent")
    sms_recipients: List[str] = Field(default_factory=list, description="Phone numbers that received SMS")
    notification_sent: bool = Field(default=False, description="Whether push notification was sent")

    # Emergency contacts notified
    emergency_contacts_notified: List[Dict[str, str]] = Field(
        default_factory=list,
        description="List of emergency contacts notified: [{name, phone, relationship}]"
    )

    # Nearest resources
    nearest_coast_guard: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Nearest coast guard station info"
    )
    nearest_port: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Nearest port info"
    )

    # Timestamps
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    # Audit trail
    history: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Status change history"
    )

    class Config:
        populate_by_name = True
        json_encoders = {
            ObjectId: str,
            datetime: lambda v: to_ist_isoformat(v)
        }
        json_schema_extra = {
            "example": {
                "sos_id": "SOS-20251205-0001",
                "user_id": "USR-001",
                "user_name": "Rajesh Kumar",
                "user_phone": "+919876543210",
                "latitude": 13.0827,
                "longitude": 80.2707,
                "vessel_id": "TN-CHN-1234",
                "vessel_name": "Sea Star",
                "crew_count": 4,
                "status": "active",
                "priority": "critical"
            }
        }

    def to_mongo(self) -> Dict[str, Any]:
        """Convert to MongoDB document format"""
        data = self.model_dump(by_alias=True, exclude_none=True)

        # Handle ObjectId
        if data.get("_id") is None:
            data.pop("_id", None)

        return data

    @classmethod
    def from_mongo(cls, data: Dict[str, Any]) -> "SOSAlert":
        """Create SOSAlert instance from MongoDB document"""
        if not data:
            return None

        # Convert ObjectId to string
        if "_id" in data:
            data["_id"] = str(data["_id"])

        # Ensure datetime fields are timezone-aware
        datetime_fields = [
            "created_at", "updated_at", "acknowledged_at",
            "dispatched_at", "resolved_at", "sms_sent_at"
        ]

        for field in datetime_fields:
            if field in data and data[field] is not None:
                dt_value = data[field]
                if isinstance(dt_value, datetime) and dt_value.tzinfo is None:
                    data[field] = dt_value.replace(tzinfo=timezone.utc)

        return cls(**data)

    def add_history_entry(self, action: str, user_id: str, user_name: str, notes: Optional[str] = None):
        """Add an entry to the status history"""
        entry = {
            "action": action,
            "user_id": user_id,
            "user_name": user_name,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "notes": notes
        }
        self.history.append(entry)
        self.updated_at = datetime.now(timezone.utc)


class SOSTriggerRequest(BaseModel):
    """Request model for triggering SOS"""
    latitude: float = Field(..., ge=-90, le=90, description="Current latitude")
    longitude: float = Field(..., ge=-180, le=180, description="Current longitude")
    vessel_id: Optional[str] = Field(default=None, description="Fishing vessel ID")
    vessel_name: Optional[str] = Field(default=None, description="Vessel name")
    crew_count: Optional[int] = Field(default=1, ge=1, description="Number of people")
    message: Optional[str] = Field(default=None, max_length=500, description="Distress message")
    priority: SOSPriority = Field(default=SOSPriority.CRITICAL, description="Priority level")


class SOSAcknowledgeRequest(BaseModel):
    """Request model for acknowledging SOS"""
    notes: Optional[str] = Field(default=None, max_length=1000, description="Acknowledgement notes")


class SOSDispatchRequest(BaseModel):
    """Request model for dispatching rescue"""
    dispatch_notes: str = Field(..., max_length=2000, description="Dispatch instructions")
    rescue_unit: Optional[str] = Field(default=None, description="Rescue unit assigned")
    eta_minutes: Optional[int] = Field(default=None, ge=0, description="Estimated time of arrival")


class SOSResolveRequest(BaseModel):
    """Request model for resolving SOS"""
    resolution_notes: str = Field(..., max_length=2000, description="Resolution details")
    outcome: str = Field(..., description="Outcome: rescued, false_alarm, self_resolved, other")


class SOSCancelRequest(BaseModel):
    """Request model for cancelling SOS (by user)"""
    reason: str = Field(..., max_length=500, description="Cancellation reason")


class SOSResponse(BaseModel):
    """Response model for SOS operations"""
    success: bool
    message: str
    sos_id: Optional[str] = None
    data: Optional[Dict[str, Any]] = None


class SOSListResponse(BaseModel):
    """Response model for listing SOS alerts"""
    success: bool
    total: int
    active_count: int
    data: List[Dict[str, Any]]
