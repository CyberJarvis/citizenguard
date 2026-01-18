"""
User Model and Related Models
MongoDB document models for authentication
"""

from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from enum import Enum
from pydantic import BaseModel, Field, EmailStr
from bson import ObjectId

# Import UserRole from RBAC module
from app.models.rbac import UserRole
from app.utils.timezone import to_ist_isoformat


class AuthProvider(str, Enum):
    """Authentication provider enumeration"""
    LOCAL = "local"
    GOOGLE = "google"
    FACEBOOK = "facebook"


class TrustEventType(str, Enum):
    """Types of events that affect user trust score"""
    # AI Layer Events (low impact)
    AI_TEXT_PASS = "ai_text_pass"
    AI_TEXT_FAIL = "ai_text_fail"
    AI_IMAGE_PASS = "ai_image_pass"
    AI_IMAGE_FAIL = "ai_image_fail"
    # Analyst/Authority Events (high impact)
    ANALYST_VERIFY = "analyst_verify"
    ANALYST_REJECT = "analyst_reject"


# Alpha values for asymptotic trust score updates
# Formula: NewScore = OldScore + α × (Target - OldScore)
# Target = 100 for rewards, 0 for penalties
TRUST_ALPHA_VALUES = {
    # AI Layer impacts (low)
    TrustEventType.AI_TEXT_PASS: 0.025,
    TrustEventType.AI_TEXT_FAIL: 0.025,
    TrustEventType.AI_IMAGE_PASS: 0.05,
    TrustEventType.AI_IMAGE_FAIL: 0.05,
    # Analyst impacts (high)
    TrustEventType.ANALYST_VERIFY: 0.10,
    TrustEventType.ANALYST_REJECT: 0.15,  # Softened from 0.25
}


def calculate_trust_score(current_score: float, event_type: TrustEventType) -> float:
    """
    Calculate new trust score using asymptotic formula.

    Formula: NewScore = OldScore + α × (Target - OldScore)

    This creates an asymptotic curve where:
    - It's easier to gain points when score is low
    - It's harder to reach perfection (100)
    - Penalties are heavier at high scores

    Args:
        current_score: Current trust score (0-100)
        event_type: Type of event that triggered the update

    Returns:
        New trust score bounded to 0-100
    """
    alpha = TRUST_ALPHA_VALUES.get(event_type, 0.05)

    # Determine target based on event type (reward vs penalty)
    if event_type in [
        TrustEventType.AI_TEXT_PASS,
        TrustEventType.AI_IMAGE_PASS,
        TrustEventType.ANALYST_VERIFY
    ]:
        target = 100  # Reward: move toward 100
    else:
        target = 0    # Penalty: move toward 0

    # Asymptotic formula
    new_score = current_score + alpha * (target - current_score)

    # Bound to 0-100
    return round(min(100, max(0, new_score)), 1)


class CredibilityMetrics(BaseModel):
    """Detailed credibility score breakdown (V2)"""
    base_score: int = Field(default=50, description="Base credibility score")
    reports_bonus: int = Field(default=0, ge=0, le=30, description="Bonus from verified reports (+5 per report, max +30)")
    accuracy_bonus: int = Field(default=0, ge=0, le=20, description="Bonus from verified/total ratio (max +20)")
    penalties: int = Field(default=0, ge=0, le=30, description="Penalty from rejected reports (-3 per report, max -30)")
    time_bonus: int = Field(default=0, ge=0, le=10, description="Longevity bonus for long-time users (max +10)")

    @property
    def total(self) -> int:
        """Calculate total credibility score with bounds"""
        raw = self.base_score + self.reports_bonus + self.accuracy_bonus - self.penalties + self.time_bonus
        return min(100, max(0, raw))

    @classmethod
    def calculate(cls, total_reports: int, verified_reports: int, rejected_reports: int, account_age_days: int) -> "CredibilityMetrics":
        """Calculate credibility metrics from user stats"""
        # Reports bonus: +5 per verified report, max +30
        reports_bonus = min(30, verified_reports * 5)

        # Accuracy bonus: based on verified/total ratio, max +20
        accuracy_bonus = 0
        if total_reports > 0:
            accuracy_rate = verified_reports / total_reports
            if accuracy_rate >= 0.9:
                accuracy_bonus = 20
            elif accuracy_rate >= 0.75:
                accuracy_bonus = 15
            elif accuracy_rate >= 0.5:
                accuracy_bonus = 10
            elif accuracy_rate >= 0.3:
                accuracy_bonus = 5

        # Penalties: -3 per rejected report, max -30
        penalties = min(30, rejected_reports * 3)

        # Time bonus: +1 per 30 days, max +10
        time_bonus = min(10, account_age_days // 30)

        return cls(
            base_score=50,
            reports_bonus=reports_bonus,
            accuracy_bonus=accuracy_bonus,
            penalties=penalties,
            time_bonus=time_bonus
        )


class User(BaseModel):
    """User document model"""

    # MongoDB ObjectId (internal)
    id: Optional[str] = Field(default=None, alias="_id")

    # Public user ID
    user_id: str = Field(..., description="Unique user identifier")

    # Authentication
    email: Optional[EmailStr] = Field(default=None, description="User email address")
    phone: Optional[str] = Field(default=None, description="Phone number with country code")
    hashed_password: Optional[str] = Field(default=None, description="Bcrypt hashed password")
    auth_provider: AuthProvider = Field(default=AuthProvider.LOCAL, description="Auth provider")
    provider_id: Optional[str] = Field(default=None, description="OAuth provider user ID")

    # Profile
    name: Optional[str] = Field(default=None, description="Full name")
    profile_picture: Optional[str] = Field(default=None, description="Profile picture URL")

    # Role & Permissions
    role: UserRole = Field(default=UserRole.CITIZEN, description="User role")

    # Location (GeoJSON Point)
    location: Optional[Dict[str, Any]] = Field(
        default=None,
        description="User location for geospatial queries"
    )

    # Credibility & Gamification
    credibility_score: int = Field(default=50, ge=0, le=100, description="User credibility (bounded 0-100)")
    total_reports: int = Field(default=0, description="Total reports submitted")
    verified_reports: int = Field(default=0, description="Number of verified reports")
    rejected_reports: int = Field(default=0, description="Number of rejected reports (V2)")
    credibility_metrics: Optional[Dict[str, Any]] = Field(
        default=None,
        description="V2: Detailed credibility breakdown (CredibilityMetrics)"
    )

    # Notification Preferences
    notification_preferences: Dict[str, Any] = Field(
        default_factory=lambda: {
            "alerts_enabled": True,
            "channels": ["push"],
            "email_notifications": True,
            "sms_notifications": False
        }
    )

    # Security
    email_verified: bool = Field(default=False, description="Email verification status")
    phone_verified: bool = Field(default=False, description="Phone verification status")
    two_factor_enabled: bool = Field(default=False, description="2FA status")
    two_factor_secret: Optional[str] = Field(default=None, description="TOTP secret")

    # OTP verification (fallback when Redis is not available)
    pending_otp: Optional[str] = Field(default=None, description="Pending OTP code")
    pending_otp_expires_at: Optional[datetime] = Field(default=None, description="OTP expiration time")
    pending_otp_type: Optional[str] = Field(default=None, description="OTP type (email/phone)")
    pending_otp_attempts: int = Field(default=0, description="Number of OTP verification attempts")

    # OAuth tokens (encrypted)
    fcm_token: Optional[str] = Field(default=None, description="Firebase Cloud Messaging token")

    # Account status
    is_active: bool = Field(default=True, description="Account active status")
    is_banned: bool = Field(default=False, description="Account banned status")
    ban_reason: Optional[str] = Field(default=None, description="Ban reason if applicable")
    banned_at: Optional[datetime] = Field(default=None, description="When user was banned")
    banned_by: Optional[str] = Field(default=None, description="Admin who banned the user")

    # Role management (RBAC)
    role_assigned_by: Optional[str] = Field(default=None, description="Admin who assigned current role")
    role_assigned_at: Optional[datetime] = Field(default=None, description="When role was assigned")
    previous_role: Optional[str] = Field(default=None, description="Previous role before change")

    # Authority-specific fields
    authority_organization: Optional[str] = Field(
        default=None,
        description="Organization name for authority users (e.g., INCOIS, Coast Guard)"
    )
    authority_designation: Optional[str] = Field(
        default=None,
        description="Designation/title for authority users"
    )
    authority_jurisdiction: Optional[List[str]] = Field(
        default=None,
        description="Geographic jurisdictions for authority users"
    )

    # Timestamps
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    last_login: Optional[datetime] = Field(default=None, description="Last login timestamp")

    class Config:
        populate_by_name = True
        json_encoders = {
            ObjectId: str,
            datetime: lambda v: to_ist_isoformat(v)
        }
        json_schema_extra = {
            "example": {
                "user_id": "USR-001",
                "email": "user@example.com",
                "phone": "+919876543210",
                "name": "John Doe",
                "role": "citizen",
                "credibility_score": 75,
                "email_verified": True,
                "is_active": True
            }
        }

    def dict(self, *args, **kwargs) -> Dict[str, Any]:
        """Override dict to exclude sensitive fields"""
        data = super().dict(*args, **kwargs)

        # Remove sensitive fields when serializing
        sensitive_fields = [
            "hashed_password",
            "two_factor_secret",
            "fcm_token",
            "pending_otp",
            "pending_otp_expires_at",
            "pending_otp_type",
            "pending_otp_attempts"
        ]

        for field in sensitive_fields:
            data.pop(field, None)

        return data

    def to_mongo(self) -> Dict[str, Any]:
        """Convert to MongoDB document format"""
        data = self.model_dump(by_alias=True, exclude_none=True)

        # Handle ObjectId
        if data.get("_id") is None:
            data.pop("_id", None)

        return data

    @classmethod
    def from_mongo(cls, data: Dict[str, Any]) -> "User":
        """Create User instance from MongoDB document"""
        if not data:
            return None

        # Convert ObjectId to string
        if "_id" in data:
            data["_id"] = str(data["_id"])

        # Ensure all datetime fields are timezone-aware
        # MongoDB stores datetimes as UTC but returns them as timezone-naive
        datetime_fields = [
            "created_at", "updated_at", "last_login", "pending_otp_expires_at",
            "banned_at", "role_assigned_at"
        ]

        for field in datetime_fields:
            if field in data and data[field] is not None:
                dt_value = data[field]
                if isinstance(dt_value, datetime) and dt_value.tzinfo is None:
                    # If timezone-naive, assume it's UTC (MongoDB default)
                    data[field] = dt_value.replace(tzinfo=timezone.utc)

        # Ensure credibility_score defaults to 50 if missing or None
        # This handles legacy users created before this field was added
        if data.get("credibility_score") is None:
            data["credibility_score"] = 50

        # Bound credibility score to 0-100 (V2 fix)
        if data.get("credibility_score") is not None:
            data["credibility_score"] = min(100, max(0, data["credibility_score"]))

        # Initialize rejected_reports if missing
        if data.get("rejected_reports") is None:
            data["rejected_reports"] = 0

        return cls(**data)

    def get_credibility_metrics(self) -> CredibilityMetrics:
        """Get or compute credibility metrics (V2)"""
        if self.credibility_metrics:
            return CredibilityMetrics(**self.credibility_metrics)

        # Calculate from user stats
        account_age_days = (datetime.now(timezone.utc) - self.created_at).days if self.created_at else 0
        return CredibilityMetrics.calculate(
            total_reports=self.total_reports,
            verified_reports=self.verified_reports,
            rejected_reports=self.rejected_reports,
            account_age_days=account_age_days
        )

    def update_credibility_from_verification(self, verified: bool) -> int:
        """
        Update credibility after a report verification using asymptotic formula.
        Returns the new score.

        Formula: NewScore = OldScore + α × (Target - OldScore)
        - Verified: α=0.10, Target=100 (reward)
        - Rejected: α=0.15, Target=0 (penalty)
        """
        if verified:
            event_type = TrustEventType.ANALYST_VERIFY
            self.verified_reports += 1
        else:
            event_type = TrustEventType.ANALYST_REJECT
            self.rejected_reports += 1

        # Use asymptotic formula
        self.credibility_score = int(calculate_trust_score(self.credibility_score, event_type))
        self.total_reports += 1
        return self.credibility_score

    def update_credibility_from_ai_layer(self, layer_type: str, passed: bool) -> int:
        """
        Update credibility based on AI layer results (text or image).
        Uses asymptotic formula with lower impact than analyst verification.

        Args:
            layer_type: 'text' or 'image'
            passed: Whether the AI layer passed

        Returns:
            New credibility score
        """
        if layer_type == 'text':
            event_type = TrustEventType.AI_TEXT_PASS if passed else TrustEventType.AI_TEXT_FAIL
        elif layer_type == 'image':
            event_type = TrustEventType.AI_IMAGE_PASS if passed else TrustEventType.AI_IMAGE_FAIL
        else:
            return self.credibility_score  # Unknown layer type, no change

        self.credibility_score = int(calculate_trust_score(self.credibility_score, event_type))
        return self.credibility_score


class AuditLog(BaseModel):
    """Audit log for security-critical events"""

    id: Optional[str] = Field(default=None, alias="_id")
    user_id: Optional[str] = Field(default=None, description="User ID")
    action: str = Field(..., description="Action performed")
    details: Dict[str, Any] = Field(default_factory=dict, description="Additional details")
    ip_address: Optional[str] = Field(default=None, description="IP address")
    user_agent: Optional[str] = Field(default=None, description="User agent string")
    success: bool = Field(default=True, description="Action success status")
    error_message: Optional[str] = Field(default=None, description="Error message if failed")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Config:
        populate_by_name = True
        json_encoders = {
            ObjectId: str,
            datetime: lambda v: to_ist_isoformat(v)
        }

    def to_mongo(self) -> Dict[str, Any]:
        """Convert to MongoDB document"""
        data = self.model_dump(by_alias=True, exclude_none=True)
        if data.get("_id") is None:
            data.pop("_id", None)
        return data

    @classmethod
    def from_mongo(cls, data: Dict[str, Any]) -> "AuditLog":
        """Create AuditLog instance from MongoDB document"""
        if not data:
            return None

        # Convert ObjectId to string
        if "_id" in data:
            data["_id"] = str(data["_id"])

        # Ensure all datetime fields are timezone-aware
        if "timestamp" in data and data["timestamp"] is not None:
            dt_value = data["timestamp"]
            if isinstance(dt_value, datetime) and dt_value.tzinfo is None:
                # If timezone-naive, assume it's UTC (MongoDB default)
                data["timestamp"] = dt_value.replace(tzinfo=timezone.utc)

        return cls(**data)


class RefreshToken(BaseModel):
    """Refresh token storage model"""

    id: Optional[str] = Field(default=None, alias="_id")
    token_id: str = Field(..., description="Unique token identifier (jti)")
    user_id: str = Field(..., description="User ID")
    token_hash: str = Field(..., description="Hashed refresh token")
    device_info: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Device information"
    )
    ip_address: Optional[str] = Field(default=None, description="IP address")
    is_revoked: bool = Field(default=False, description="Token revocation status")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: datetime = Field(..., description="Token expiration time")

    class Config:
        populate_by_name = True
        json_encoders = {
            ObjectId: str,
            datetime: lambda v: to_ist_isoformat(v)
        }

    def to_mongo(self) -> Dict[str, Any]:
        """Convert to MongoDB document"""
        data = self.model_dump(by_alias=True, exclude_none=True)
        if data.get("_id") is None:
            data.pop("_id", None)
        return data

    @classmethod
    def from_mongo(cls, data: Dict[str, Any]) -> "RefreshToken":
        """Create RefreshToken instance from MongoDB document"""
        if not data:
            return None

        # Convert ObjectId to string
        if "_id" in data:
            data["_id"] = str(data["_id"])

        # Ensure all datetime fields are timezone-aware
        datetime_fields = ["created_at", "expires_at"]

        for field in datetime_fields:
            if field in data and data[field] is not None:
                dt_value = data[field]
                if isinstance(dt_value, datetime) and dt_value.tzinfo is None:
                    # If timezone-naive, assume it's UTC (MongoDB default)
                    data[field] = dt_value.replace(tzinfo=timezone.utc)

        return cls(**data)
