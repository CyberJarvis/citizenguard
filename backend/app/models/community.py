"""
Community Response Module Models
Pydantic models for organizer applications, communities, events, and related entities
"""

from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from enum import Enum
from pydantic import BaseModel, Field, EmailStr
from bson import ObjectId
from app.utils.timezone import to_ist_isoformat


# ============================================================================
# CONSTANTS
# ============================================================================

INDIAN_COASTAL_ZONES = [
    "Mumbai", "Chennai", "Kolkata", "Visakhapatnam", "Kochi",
    "Goa", "Mangalore", "Puri", "Thiruvananthapuram", "Paradip"
]

INDIAN_COASTAL_STATES = [
    "Maharashtra", "Gujarat", "Goa", "Karnataka", "Kerala",
    "Tamil Nadu", "Andhra Pradesh", "Odisha", "West Bengal"
]


# ============================================================================
# ENUMS
# ============================================================================

class ApplicationStatus(str, Enum):
    """Organizer application status"""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class CommunityCategory(str, Enum):
    """Community category types"""
    CLEANUP = "cleanup"
    ANIMAL_RESCUE = "animal_rescue"
    AWARENESS = "awareness"
    GENERAL = "general"


class EventType(str, Enum):
    """Event type classification"""
    BEACH_CLEANUP = "beach_cleanup"
    MANGROVE_PLANTATION = "mangrove_plantation"
    AWARENESS_DRIVE = "awareness_drive"
    RESCUE_OPERATION = "rescue_operation"
    TRAINING_WORKSHOP = "training_workshop"
    EMERGENCY_RESPONSE = "emergency_response"


class EventStatus(str, Enum):
    """Event status lifecycle"""
    DRAFT = "draft"
    PUBLISHED = "published"
    ONGOING = "ongoing"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class RegistrationStatus(str, Enum):
    """Event registration status"""
    REGISTERED = "registered"
    CONFIRMED = "confirmed"
    ATTENDED = "attended"
    NO_SHOW = "no_show"
    CANCELLED = "cancelled"


class NotificationType(str, Enum):
    """Organizer notification types"""
    HAZARD_DETECTED = "hazard_detected"
    APPLICATION_APPROVED = "application_approved"
    APPLICATION_REJECTED = "application_rejected"
    EVENT_REMINDER = "event_reminder"
    MEMBER_JOINED = "member_joined"


# ============================================================================
# BADGE DEFINITIONS
# ============================================================================

BADGE_DEFINITIONS = {
    "first_timer": {
        "name": "First Timer",
        "description": "Attended your first volunteer event",
        "icon": "star",
        "requirement": {"events_attended": 1}
    },
    "active_volunteer": {
        "name": "Active Volunteer",
        "description": "Attended 3 volunteer events",
        "icon": "award",
        "requirement": {"events_attended": 3}
    },
    "ocean_defender": {
        "name": "Ocean Defender",
        "description": "Attended 5 volunteer events",
        "icon": "shield",
        "requirement": {"events_attended": 5}
    },
    "beach_warrior": {
        "name": "Beach Warrior",
        "description": "Attended 10 volunteer events",
        "icon": "trophy",
        "requirement": {"events_attended": 10}
    },
    "super_volunteer": {
        "name": "Super Volunteer",
        "description": "Attended 25 volunteer events",
        "icon": "crown",
        "requirement": {"events_attended": 25}
    },
    "emergency_responder": {
        "name": "Emergency Responder",
        "description": "Responded to an emergency event",
        "icon": "alert-triangle",
        "requirement": {"emergency_events_attended": 1}
    },
    "community_builder": {
        "name": "Community Builder",
        "description": "Organized 5 events",
        "icon": "users",
        "requirement": {"events_organized": 5}
    }
}


# ============================================================================
# ORGANIZER APPLICATION MODEL
# ============================================================================

class OrganizerApplication(BaseModel):
    """Organizer application document model"""

    # MongoDB ObjectId (internal)
    id: Optional[str] = Field(default=None, alias="_id")

    # Public application ID (ORG-YYYYMMDD-XXXXX)
    application_id: str = Field(..., description="Unique application identifier")

    # Applicant info
    user_id: str = Field(..., description="Applicant user ID")
    name: str = Field(..., description="Full name")
    email: EmailStr = Field(..., description="Email address")
    phone: str = Field(..., description="Phone number")

    # Location
    coastal_zone: str = Field(..., description="Primary coastal zone from 10 zones")
    state: str = Field(..., description="State from 9 coastal states")

    # Verification document
    aadhaar_document_url: str = Field(..., description="Uploaded Aadhaar document path")

    # Credibility at application time
    credibility_at_application: int = Field(..., ge=0, le=100, description="User credibility score at application time")

    # Application status
    status: ApplicationStatus = Field(default=ApplicationStatus.PENDING, description="Application status")

    # Review info (filled when reviewed)
    reviewed_by_id: Optional[str] = Field(default=None, description="Admin user ID who reviewed")
    reviewed_by_name: Optional[str] = Field(default=None, description="Admin name who reviewed")
    reviewed_at: Optional[datetime] = Field(default=None, description="Review timestamp")
    rejection_reason: Optional[str] = Field(default=None, description="Reason for rejection if rejected")

    # Timestamps
    applied_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Config:
        populate_by_name = True
        json_encoders = {
            ObjectId: str,
            datetime: lambda v: to_ist_isoformat(v)
        }
        json_schema_extra = {
            "example": {
                "application_id": "ORG-20250101-00001",
                "user_id": "USR-001",
                "name": "Roshan Kumar",
                "email": "roshan@example.com",
                "phone": "+919876543210",
                "coastal_zone": "Mumbai",
                "state": "Maharashtra",
                "credibility_at_application": 85,
                "status": "pending"
            }
        }

    def to_mongo(self) -> Dict[str, Any]:
        """Convert to MongoDB document format"""
        data = self.model_dump(by_alias=True, exclude_none=True)
        if data.get("_id") is None:
            data.pop("_id", None)
        return data

    @classmethod
    def from_mongo(cls, data: Dict[str, Any]) -> "OrganizerApplication":
        """Create instance from MongoDB document"""
        if not data:
            return None

        if "_id" in data:
            data["_id"] = str(data["_id"])

        # Handle datetime fields
        datetime_fields = ["applied_at", "reviewed_at"]
        for field in datetime_fields:
            if field in data and data[field] is not None:
                dt_value = data[field]
                if isinstance(dt_value, datetime) and dt_value.tzinfo is None:
                    data[field] = dt_value.replace(tzinfo=timezone.utc)

        return cls(**data)


# ============================================================================
# COMMUNITY MODEL
# ============================================================================

class Community(BaseModel):
    """Community document model"""

    id: Optional[str] = Field(default=None, alias="_id")

    # Public community ID (COM-YYYYMMDD-XXXXX)
    community_id: str = Field(..., description="Unique community identifier")

    # Basic info
    name: str = Field(..., min_length=3, max_length=100, description="Community name")
    description: str = Field(..., min_length=10, max_length=2000, description="Community description")
    category: CommunityCategory = Field(default=CommunityCategory.GENERAL, description="Community category")

    # Organizer info
    organizer_id: str = Field(..., description="Organizer user ID")
    organizer_name: str = Field(..., description="Organizer display name")

    # Location
    coastal_zone: str = Field(..., description="Primary coastal zone")
    state: str = Field(..., description="State")

    # Members
    member_ids: List[str] = Field(default_factory=list, description="List of member user IDs")
    member_count: int = Field(default=0, description="Current member count")

    # Media
    cover_image_url: Optional[str] = Field(default=None, description="Cover image URL")
    logo_url: Optional[str] = Field(default=None, description="Logo/avatar URL")

    # Statistics
    total_events: int = Field(default=0, description="Total events organized")
    total_volunteers: int = Field(default=0, description="Total unique volunteers across events")

    # Status
    is_active: bool = Field(default=True, description="Community active status")
    is_public: bool = Field(default=True, description="Public visibility")

    # Timestamps
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Config:
        populate_by_name = True
        json_encoders = {
            ObjectId: str,
            datetime: lambda v: to_ist_isoformat(v)
        }
        json_schema_extra = {
            "example": {
                "community_id": "COM-20250101-00001",
                "name": "Mumbai Beach Warriors",
                "description": "A community dedicated to keeping Mumbai beaches clean",
                "category": "cleanup",
                "organizer_id": "USR-001",
                "organizer_name": "Roshan Kumar",
                "coastal_zone": "Mumbai",
                "state": "Maharashtra",
                "member_count": 50,
                "is_active": True
            }
        }

    def to_mongo(self) -> Dict[str, Any]:
        """Convert to MongoDB document format"""
        data = self.model_dump(by_alias=True, exclude_none=True)
        if data.get("_id") is None:
            data.pop("_id", None)
        return data

    @classmethod
    def from_mongo(cls, data: Dict[str, Any]) -> "Community":
        """Create instance from MongoDB document"""
        if not data:
            return None

        if "_id" in data:
            data["_id"] = str(data["_id"])

        datetime_fields = ["created_at", "updated_at"]
        for field in datetime_fields:
            if field in data and data[field] is not None:
                dt_value = data[field]
                if isinstance(dt_value, datetime) and dt_value.tzinfo is None:
                    data[field] = dt_value.replace(tzinfo=timezone.utc)

        return cls(**data)


# ============================================================================
# EVENT MODEL
# ============================================================================

class Event(BaseModel):
    """Event document model"""

    id: Optional[str] = Field(default=None, alias="_id")

    # Public event ID (EVT-YYYYMMDD-XXXXX)
    event_id: str = Field(..., description="Unique event identifier")

    # Association
    community_id: str = Field(..., description="Parent community ID")
    organizer_id: str = Field(..., description="Organizer user ID")
    organizer_name: str = Field(..., description="Organizer display name")

    # Basic info
    title: str = Field(..., min_length=5, max_length=200, description="Event title")
    description: str = Field(..., min_length=20, max_length=5000, description="Event description")
    event_type: EventType = Field(..., description="Type of event")

    # Location
    location_address: str = Field(..., description="Full address")
    location_latitude: float = Field(..., ge=-90, le=90, description="Latitude")
    location_longitude: float = Field(..., ge=-180, le=180, description="Longitude")
    coastal_zone: str = Field(..., description="Coastal zone")

    # Timing
    event_date: datetime = Field(..., description="Event start date/time")
    event_end_date: Optional[datetime] = Field(default=None, description="Event end date/time")
    registration_deadline: Optional[datetime] = Field(default=None, description="Registration deadline")

    # Capacity
    max_volunteers: int = Field(default=50, ge=1, le=500, description="Maximum volunteers")
    registered_count: int = Field(default=0, description="Current registrations")
    attended_count: int = Field(default=0, description="Actual attendance")

    # Status
    status: EventStatus = Field(default=EventStatus.DRAFT, description="Event status")

    # Emergency event fields
    is_emergency: bool = Field(default=False, description="Emergency response event")
    related_hazard_id: Optional[str] = Field(default=None, description="Related hazard report ID")
    related_alert_id: Optional[str] = Field(default=None, description="Related alert ID")

    # Points configuration
    points_per_attendee: int = Field(default=50, description="Points awarded to attendees")
    organizer_points_per_attendee: int = Field(default=10, description="Bonus points for organizer per attendee")

    # Media
    cover_image_url: Optional[str] = Field(default=None, description="Event cover image")

    # Timestamps
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: Optional[datetime] = Field(default=None, description="When event was marked complete")

    class Config:
        populate_by_name = True
        json_encoders = {
            ObjectId: str,
            datetime: lambda v: to_ist_isoformat(v)
        }
        json_schema_extra = {
            "example": {
                "event_id": "EVT-20250101-00001",
                "community_id": "COM-20250101-00001",
                "title": "Juhu Beach Cleanup Drive",
                "description": "Join us for a beach cleanup at Juhu Beach",
                "event_type": "beach_cleanup",
                "location_address": "Juhu Beach, Mumbai",
                "location_latitude": 19.0883,
                "location_longitude": 72.8263,
                "coastal_zone": "Mumbai",
                "max_volunteers": 100,
                "status": "published"
            }
        }

    def to_mongo(self) -> Dict[str, Any]:
        """Convert to MongoDB document format"""
        data = self.model_dump(by_alias=True, exclude_none=True)
        if data.get("_id") is None:
            data.pop("_id", None)
        return data

    @classmethod
    def from_mongo(cls, data: Dict[str, Any]) -> "Event":
        """Create instance from MongoDB document"""
        if not data:
            return None

        if "_id" in data:
            data["_id"] = str(data["_id"])

        datetime_fields = ["event_date", "event_end_date", "registration_deadline",
                         "created_at", "updated_at", "completed_at"]
        for field in datetime_fields:
            if field in data and data[field] is not None:
                dt_value = data[field]
                if isinstance(dt_value, datetime) and dt_value.tzinfo is None:
                    data[field] = dt_value.replace(tzinfo=timezone.utc)

        return cls(**data)


# ============================================================================
# EVENT REGISTRATION MODEL
# ============================================================================

class EventRegistration(BaseModel):
    """Event registration document model"""

    id: Optional[str] = Field(default=None, alias="_id")

    # Public registration ID (REG-YYYYMMDD-XXXXX)
    registration_id: str = Field(..., description="Unique registration identifier")

    # References
    event_id: str = Field(..., description="Event ID")
    user_id: str = Field(..., description="User ID")

    # User info (denormalized for quick access)
    user_name: str = Field(..., description="User display name")
    user_email: EmailStr = Field(..., description="User email")

    # Status
    registration_status: RegistrationStatus = Field(
        default=RegistrationStatus.REGISTERED,
        description="Registration status"
    )

    # Attendance tracking
    attendance_marked_at: Optional[datetime] = Field(default=None, description="When attendance was marked")
    attendance_marked_by: Optional[str] = Field(default=None, description="Who marked attendance")

    # Certificate
    certificate_generated: bool = Field(default=False, description="Certificate generation status")
    certificate_url: Optional[str] = Field(default=None, description="Certificate file path")
    certificate_id: Optional[str] = Field(default=None, description="Certificate unique ID")

    # Points
    points_awarded: int = Field(default=0, description="Points awarded for this event")

    # Timestamps
    registered_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Config:
        populate_by_name = True
        json_encoders = {
            ObjectId: str,
            datetime: lambda v: to_ist_isoformat(v)
        }

    def to_mongo(self) -> Dict[str, Any]:
        """Convert to MongoDB document format"""
        data = self.model_dump(by_alias=True, exclude_none=True)
        if data.get("_id") is None:
            data.pop("_id", None)
        return data

    @classmethod
    def from_mongo(cls, data: Dict[str, Any]) -> "EventRegistration":
        """Create instance from MongoDB document"""
        if not data:
            return None

        if "_id" in data:
            data["_id"] = str(data["_id"])

        datetime_fields = ["registered_at", "attendance_marked_at"]
        for field in datetime_fields:
            if field in data and data[field] is not None:
                dt_value = data[field]
                if isinstance(dt_value, datetime) and dt_value.tzinfo is None:
                    data[field] = dt_value.replace(tzinfo=timezone.utc)

        return cls(**data)


# ============================================================================
# USER POINTS MODEL
# ============================================================================

class UserPoints(BaseModel):
    """User points and badges document model"""

    id: Optional[str] = Field(default=None, alias="_id")

    # Reference
    user_id: str = Field(..., description="User ID")

    # Points
    total_points: int = Field(default=0, description="Total accumulated points")

    # Activity counters
    events_attended: int = Field(default=0, description="Total events attended")
    emergency_events_attended: int = Field(default=0, description="Emergency events attended")
    events_organized: int = Field(default=0, description="Events organized (for organizers)")
    communities_joined: int = Field(default=0, description="Communities joined")

    # Badges
    badges: List[str] = Field(default_factory=list, description="List of badge IDs earned")
    badges_earned_at: Dict[str, datetime] = Field(
        default_factory=dict,
        description="Map of badge_id to earned timestamp"
    )

    # Leaderboard
    rank: Optional[int] = Field(default=None, description="Current leaderboard rank")

    # Timestamps
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Config:
        populate_by_name = True
        json_encoders = {
            ObjectId: str,
            datetime: lambda v: to_ist_isoformat(v)
        }

    def to_mongo(self) -> Dict[str, Any]:
        """Convert to MongoDB document format"""
        data = self.model_dump(by_alias=True, exclude_none=True)
        if data.get("_id") is None:
            data.pop("_id", None)

        # Convert datetime values in badges_earned_at dict
        if "badges_earned_at" in data:
            data["badges_earned_at"] = {
                k: v.isoformat() if isinstance(v, datetime) else v
                for k, v in data["badges_earned_at"].items()
            }

        return data

    @classmethod
    def from_mongo(cls, data: Dict[str, Any]) -> "UserPoints":
        """Create instance from MongoDB document"""
        if not data:
            return None

        if "_id" in data:
            data["_id"] = str(data["_id"])

        # Handle updated_at
        if "updated_at" in data and data["updated_at"] is not None:
            dt_value = data["updated_at"]
            if isinstance(dt_value, datetime) and dt_value.tzinfo is None:
                data["updated_at"] = dt_value.replace(tzinfo=timezone.utc)

        # Handle badges_earned_at dict
        if "badges_earned_at" in data:
            badges_earned = {}
            for k, v in data["badges_earned_at"].items():
                if isinstance(v, str):
                    badges_earned[k] = datetime.fromisoformat(v)
                elif isinstance(v, datetime):
                    if v.tzinfo is None:
                        badges_earned[k] = v.replace(tzinfo=timezone.utc)
                    else:
                        badges_earned[k] = v
            data["badges_earned_at"] = badges_earned

        return cls(**data)


# ============================================================================
# ORGANIZER NOTIFICATION MODEL
# ============================================================================

class OrganizerNotification(BaseModel):
    """Organizer notification document model"""

    id: Optional[str] = Field(default=None, alias="_id")

    # Public notification ID
    notification_id: str = Field(..., description="Unique notification identifier")

    # Target
    organizer_id: str = Field(..., description="Target organizer user ID")

    # Content
    type: NotificationType = Field(..., description="Notification type")
    title: str = Field(..., description="Notification title")
    message: str = Field(..., description="Notification message")

    # Pre-fill data for hazard-to-event flow
    prefill_data: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Pre-fill data for event creation form"
    )

    # Related entities
    related_hazard_id: Optional[str] = Field(default=None, description="Related hazard ID")
    related_alert_id: Optional[str] = Field(default=None, description="Related alert ID")
    related_community_id: Optional[str] = Field(default=None, description="Related community ID")
    related_event_id: Optional[str] = Field(default=None, description="Related event ID")

    # Status
    is_read: bool = Field(default=False, description="Read status")

    # Timestamps
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: Optional[datetime] = Field(default=None, description="TTL expiration for auto-deletion")

    class Config:
        populate_by_name = True
        json_encoders = {
            ObjectId: str,
            datetime: lambda v: to_ist_isoformat(v)
        }

    def to_mongo(self) -> Dict[str, Any]:
        """Convert to MongoDB document format"""
        data = self.model_dump(by_alias=True, exclude_none=True)
        if data.get("_id") is None:
            data.pop("_id", None)
        return data

    @classmethod
    def from_mongo(cls, data: Dict[str, Any]) -> "OrganizerNotification":
        """Create instance from MongoDB document"""
        if not data:
            return None

        if "_id" in data:
            data["_id"] = str(data["_id"])

        datetime_fields = ["created_at", "expires_at"]
        for field in datetime_fields:
            if field in data and data[field] is not None:
                dt_value = data[field]
                if isinstance(dt_value, datetime) and dt_value.tzinfo is None:
                    data[field] = dt_value.replace(tzinfo=timezone.utc)

        return cls(**data)


# ============================================================================
# REQUEST/RESPONSE SCHEMAS
# ============================================================================

class OrganizerApplicationCreate(BaseModel):
    """Schema for creating organizer application"""
    name: str = Field(..., min_length=2, max_length=100)
    email: EmailStr
    phone: str = Field(..., pattern=r"^\+?[1-9]\d{9,14}$")
    coastal_zone: str = Field(..., description="Must be from INDIAN_COASTAL_ZONES")
    state: str = Field(..., description="Must be from INDIAN_COASTAL_STATES")


class OrganizerApplicationReview(BaseModel):
    """Schema for reviewing organizer application"""
    action: str = Field(..., pattern="^(approve|reject)$")
    rejection_reason: Optional[str] = Field(default=None, max_length=500)


class CommunityCreate(BaseModel):
    """Schema for creating a community"""
    name: str = Field(..., min_length=3, max_length=100)
    description: str = Field(..., min_length=10, max_length=2000)
    category: CommunityCategory = Field(default=CommunityCategory.GENERAL)
    coastal_zone: str
    state: str
    is_public: bool = Field(default=True)


class CommunityUpdate(BaseModel):
    """Schema for updating a community"""
    name: Optional[str] = Field(default=None, min_length=3, max_length=100)
    description: Optional[str] = Field(default=None, min_length=10, max_length=2000)
    category: Optional[CommunityCategory] = None
    is_public: Optional[bool] = None


class EventCreate(BaseModel):
    """Schema for creating an event"""
    community_id: str
    title: str = Field(..., min_length=5, max_length=200)
    description: str = Field(..., min_length=20, max_length=5000)
    event_type: EventType
    location_address: str
    location_latitude: float = Field(..., ge=-90, le=90)
    location_longitude: float = Field(..., ge=-180, le=180)
    event_date: datetime
    event_end_date: Optional[datetime] = None
    registration_deadline: Optional[datetime] = None
    max_volunteers: int = Field(default=50, ge=1, le=500)
    is_emergency: bool = Field(default=False)
    related_hazard_id: Optional[str] = None
    related_alert_id: Optional[str] = None


class EventUpdate(BaseModel):
    """Schema for updating an event"""
    title: Optional[str] = Field(default=None, min_length=5, max_length=200)
    description: Optional[str] = Field(default=None, min_length=20, max_length=5000)
    location_address: Optional[str] = None
    location_latitude: Optional[float] = Field(default=None, ge=-90, le=90)
    location_longitude: Optional[float] = Field(default=None, ge=-180, le=180)
    event_date: Optional[datetime] = None
    event_end_date: Optional[datetime] = None
    registration_deadline: Optional[datetime] = None
    max_volunteers: Optional[int] = Field(default=None, ge=1, le=500)
    status: Optional[EventStatus] = None


class AttendanceMarkRequest(BaseModel):
    """Schema for marking attendance"""
    user_ids: List[str] = Field(..., min_length=1, description="List of user IDs to mark as attended")


class LeaderboardEntry(BaseModel):
    """Schema for leaderboard entry"""
    rank: int
    user_id: str
    user_name: str
    profile_picture: Optional[str] = None
    total_points: int
    events_attended: int
    badges: List[str]


# ============================================================================
# EXPORTS
# ============================================================================

__all__ = [
    # Constants
    "INDIAN_COASTAL_ZONES",
    "INDIAN_COASTAL_STATES",
    "BADGE_DEFINITIONS",

    # Enums
    "ApplicationStatus",
    "CommunityCategory",
    "EventType",
    "EventStatus",
    "RegistrationStatus",
    "NotificationType",

    # Models
    "OrganizerApplication",
    "Community",
    "Event",
    "EventRegistration",
    "UserPoints",
    "OrganizerNotification",

    # Schemas
    "OrganizerApplicationCreate",
    "OrganizerApplicationReview",
    "CommunityCreate",
    "CommunityUpdate",
    "EventCreate",
    "EventUpdate",
    "AttendanceMarkRequest",
    "LeaderboardEntry",
]
