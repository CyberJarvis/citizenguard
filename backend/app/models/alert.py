"""
Alert Model
For authorities to create and manage hazard alerts
"""

from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from enum import Enum
from pydantic import BaseModel, Field
from bson import ObjectId
from app.utils.timezone import to_ist_isoformat


class AlertSeverity(str, Enum):
    """Alert severity levels"""
    INFO = "info"  # Informational
    LOW = "low"  # Low severity
    MEDIUM = "medium"  # Medium severity
    HIGH = "high"  # High severity
    CRITICAL = "critical"  # Critical - immediate action required


class AlertType(str, Enum):
    """Types of alerts"""
    TSUNAMI = "tsunami"
    CYCLONE = "cyclone"
    HIGH_WAVES = "high_waves"
    STORM_SURGE = "storm_surge"
    COASTAL_FLOODING = "coastal_flooding"
    COASTAL_EROSION = "coastal_erosion"
    RIP_CURRENT = "rip_current"
    OIL_SPILL = "oil_spill"
    CHEMICAL_SPILL = "chemical_spill"
    ALGAL_BLOOM = "algal_bloom"
    SEA_LEVEL_RISE = "sea_level_rise"
    MARINE_POLLUTION = "marine_pollution"
    WEATHER_WARNING = "weather_warning"
    GENERAL = "general"
    OTHER = "other"


class AlertStatus(str, Enum):
    """Alert status"""
    DRAFT = "draft"  # Being created
    ACTIVE = "active"  # Currently active
    EXPIRED = "expired"  # Past expiration time
    CANCELLED = "cancelled"  # Manually cancelled


class Alert(BaseModel):
    """Alert document model for MongoDB"""

    id: Optional[str] = Field(default=None, alias="_id")

    # Alert identification
    alert_id: str = Field(..., description="Unique alert identifier")

    # Alert details
    title: str = Field(..., description="Alert title")
    description: str = Field(..., description="Detailed alert description")
    alert_type: AlertType = Field(..., description="Type of hazard")
    severity: AlertSeverity = Field(..., description="Severity level")
    status: AlertStatus = Field(default=AlertStatus.ACTIVE, description="Alert status")

    # Geographic coverage
    regions: List[str] = Field(..., description="Affected regions/areas")
    coordinates: Optional[List[Dict[str, float]]] = Field(
        default=None,
        description="List of coordinates defining affected area"
    )

    # Timing
    issued_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="When alert was issued"
    )
    expires_at: Optional[datetime] = Field(
        default=None,
        description="When alert expires (None = no expiration)"
    )
    effective_from: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="When alert becomes effective"
    )

    # Creator information
    created_by: str = Field(..., description="User ID of creator")
    creator_name: Optional[str] = Field(default=None, description="Name of creator")
    creator_organization: Optional[str] = Field(
        default=None,
        description="Organization of creator"
    )

    # Update tracking
    updated_by: Optional[str] = Field(default=None, description="Last updated by user ID")
    updated_at: Optional[datetime] = Field(default=None, description="Last update timestamp")

    # Cancellation
    cancelled_by: Optional[str] = Field(default=None, description="User who cancelled")
    cancelled_at: Optional[datetime] = Field(default=None, description="Cancellation timestamp")
    cancellation_reason: Optional[str] = Field(default=None, description="Reason for cancellation")

    # Additional information
    instructions: Optional[str] = Field(
        default=None,
        description="Safety instructions for public"
    )
    contact_info: Optional[str] = Field(
        default=None,
        description="Contact information for more details"
    )
    related_reports: Optional[List[str]] = Field(
        default=None,
        description="Related hazard report IDs"
    )

    # Metadata
    tags: List[str] = Field(default_factory=list, description="Tags for categorization")
    priority: int = Field(default=3, ge=1, le=5, description="Priority (1=lowest, 5=highest)")

    # Notification tracking
    notifications_sent: int = Field(default=0, description="Number of notifications sent")
    users_notified: List[str] = Field(
        default_factory=list,
        description="User IDs who were notified"
    )

    # Timestamps
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Config:
        populate_by_name = True
        json_encoders = {
            ObjectId: str,
            datetime: lambda v: to_ist_isoformat(v)
        }
        json_schema_extra = {
            "example": {
                "alert_id": "ALT-001",
                "title": "High Wave Warning",
                "description": "Expected high waves of 4-5 meters in coastal areas",
                "alert_type": "high_waves",
                "severity": "high",
                "regions": ["Mumbai", "Thane", "Raigad"],
                "created_by": "USR-ADMIN-001",
                "effective_from": "2025-01-15T10:00:00Z",
                "expires_at": "2025-01-16T10:00:00Z"
            }
        }

    def to_mongo(self) -> Dict[str, Any]:
        """Convert to MongoDB document format"""
        data = self.model_dump(by_alias=True, exclude_none=True)
        if data.get("_id") is None:
            data.pop("_id", None)
        return data

    @classmethod
    def from_mongo(cls, data: Dict[str, Any]) -> "Alert":
        """Create Alert instance from MongoDB document"""
        if not data:
            return None

        # Convert ObjectId to string
        if "_id" in data:
            data["_id"] = str(data["_id"])

        # Ensure all datetime fields are timezone-aware
        datetime_fields = [
            "created_at", "issued_at", "expires_at", "effective_from",
            "updated_at", "cancelled_at"
        ]

        for field in datetime_fields:
            if field in data and data[field] is not None:
                dt_value = data[field]
                if isinstance(dt_value, datetime) and dt_value.tzinfo is None:
                    data[field] = dt_value.replace(tzinfo=timezone.utc)

        return cls(**data)


class AlertCreate(BaseModel):
    """Schema for creating alerts"""
    title: str = Field(..., min_length=5, max_length=200)
    description: str = Field(..., min_length=10, max_length=2000)
    alert_type: AlertType
    severity: AlertSeverity
    regions: List[str] = Field(..., min_items=1)
    coordinates: Optional[List[Dict[str, float]]] = None
    expires_at: Optional[datetime] = None
    instructions: Optional[str] = None
    contact_info: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    priority: int = Field(default=3, ge=1, le=5)


class AlertUpdate(BaseModel):
    """Schema for updating alerts"""
    title: Optional[str] = Field(default=None, min_length=5, max_length=200)
    description: Optional[str] = Field(default=None, min_length=10, max_length=2000)
    severity: Optional[AlertSeverity] = None
    regions: Optional[List[str]] = None
    expires_at: Optional[datetime] = None
    instructions: Optional[str] = None
    contact_info: Optional[str] = None
    tags: Optional[List[str]] = None
    priority: Optional[int] = Field(default=None, ge=1, le=5)


class AlertResponse(BaseModel):
    """Schema for alert responses"""
    alert_id: str
    title: str
    description: str
    alert_type: AlertType
    severity: AlertSeverity
    status: AlertStatus
    regions: List[str]
    issued_at: datetime
    expires_at: Optional[datetime]
    created_by: str
    creator_name: Optional[str]
    creator_organization: Optional[str]
    instructions: Optional[str]
    tags: List[str]
    priority: int

    class Config:
        from_attributes = True
