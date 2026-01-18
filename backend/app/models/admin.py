"""
Admin Module Models
MongoDB document models for admin functionality
"""

from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from enum import Enum
from pydantic import BaseModel, Field
from bson import ObjectId
from app.utils.timezone import to_ist_isoformat


class SettingCategory(str, Enum):
    """System setting categories"""
    GENERAL = "general"
    SECURITY = "security"
    NOTIFICATIONS = "notifications"
    API = "api"
    MONITORING = "monitoring"
    STORAGE = "storage"


class SettingValueType(str, Enum):
    """Setting value types"""
    STRING = "string"
    NUMBER = "number"
    BOOLEAN = "boolean"
    JSON = "json"


class HealthStatus(str, Enum):
    """System health status levels"""
    HEALTHY = "healthy"
    WARNING = "warning"
    CRITICAL = "critical"
    UNKNOWN = "unknown"


class AdminActionType(str, Enum):
    """Types of admin actions for logging"""
    # User Management
    USER_CREATED = "user_created"
    USER_UPDATED = "user_updated"
    USER_DELETED = "user_deleted"
    USER_BANNED = "user_banned"
    USER_UNBANNED = "user_unbanned"
    ROLE_CHANGED = "role_changed"

    # Content Moderation
    REPORT_DELETED = "report_deleted"
    REPORT_EDITED = "report_edited"
    ALERT_CREATED = "alert_created"
    ALERT_UPDATED = "alert_updated"
    ALERT_DELETED = "alert_deleted"
    MESSAGE_DELETED = "message_deleted"

    # System Settings
    SETTING_CREATED = "setting_created"
    SETTING_UPDATED = "setting_updated"
    SETTING_DELETED = "setting_deleted"

    # System Actions
    SYSTEM_BACKUP = "system_backup"
    CACHE_CLEARED = "cache_cleared"
    LOGS_EXPORTED = "logs_exported"


class SystemSettings(BaseModel):
    """Global application settings managed by admin"""

    id: Optional[str] = Field(default=None, alias="_id")
    setting_id: str = Field(..., description="Unique setting identifier")
    category: SettingCategory = Field(..., description="Setting category")
    key: str = Field(..., description="Setting key name")
    value: Any = Field(..., description="Setting value")
    value_type: SettingValueType = Field(..., description="Value type for validation")
    label: str = Field(..., description="Human-readable label")
    description: str = Field(..., description="Setting description")
    is_sensitive: bool = Field(default=False, description="Hide value in responses")
    is_editable: bool = Field(default=True, description="Can be edited by admin")
    validation_rules: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Validation rules (min, max, pattern, etc.)"
    )
    updated_by: Optional[str] = Field(default=None, description="Admin who last updated")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
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
        return data

    def to_response(self) -> Dict[str, Any]:
        """Convert to API response, hiding sensitive values"""
        data = self.model_dump(exclude={"id"})
        if self.is_sensitive:
            data["value"] = "********"
        return data

    @classmethod
    def from_mongo(cls, data: Dict[str, Any]) -> "SystemSettings":
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


class AdminActivityLog(BaseModel):
    """Detailed admin action tracking"""

    id: Optional[str] = Field(default=None, alias="_id")
    log_id: str = Field(..., description="Unique log identifier")
    admin_id: str = Field(..., description="Admin user ID")
    admin_name: Optional[str] = Field(default=None, description="Admin name for display")
    admin_email: Optional[str] = Field(default=None, description="Admin email")
    action: AdminActionType = Field(..., description="Action type")
    target_type: str = Field(..., description="Target entity type (user, report, alert, setting)")
    target_id: Optional[str] = Field(default=None, description="Target entity ID")
    target_name: Optional[str] = Field(default=None, description="Target name for display")
    details: Dict[str, Any] = Field(default_factory=dict, description="Action details")
    previous_value: Optional[Any] = Field(default=None, description="Previous value (for updates)")
    new_value: Optional[Any] = Field(default=None, description="New value (for updates)")
    ip_address: Optional[str] = Field(default=None, description="Admin IP address")
    user_agent: Optional[str] = Field(default=None, description="Browser user agent")
    success: bool = Field(default=True, description="Action success status")
    error_message: Optional[str] = Field(default=None, description="Error if failed")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

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
    def from_mongo(cls, data: Dict[str, Any]) -> "AdminActivityLog":
        """Create instance from MongoDB document"""
        if not data:
            return None
        if "_id" in data:
            data["_id"] = str(data["_id"])

        if "timestamp" in data and data["timestamp"] is not None:
            dt_value = data["timestamp"]
            if isinstance(dt_value, datetime) and dt_value.tzinfo is None:
                data["timestamp"] = dt_value.replace(tzinfo=timezone.utc)

        return cls(**data)


class SystemHealthMetric(BaseModel):
    """System health metrics snapshot"""

    id: Optional[str] = Field(default=None, alias="_id")
    metric_id: str = Field(..., description="Unique metric identifier")
    metric_type: str = Field(..., description="Metric type (api, database, cache, storage)")
    metric_name: str = Field(..., description="Human-readable metric name")
    value: float = Field(..., description="Metric value")
    unit: str = Field(..., description="Measurement unit")
    status: HealthStatus = Field(default=HealthStatus.HEALTHY, description="Health status")
    threshold_warning: Optional[float] = Field(default=None, description="Warning threshold")
    threshold_critical: Optional[float] = Field(default=None, description="Critical threshold")
    details: Optional[Dict[str, Any]] = Field(default=None, description="Additional details")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

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
    def from_mongo(cls, data: Dict[str, Any]) -> "SystemHealthMetric":
        """Create instance from MongoDB document"""
        if not data:
            return None
        if "_id" in data:
            data["_id"] = str(data["_id"])

        if "timestamp" in data and data["timestamp"] is not None:
            dt_value = data["timestamp"]
            if isinstance(dt_value, datetime) and dt_value.tzinfo is None:
                data["timestamp"] = dt_value.replace(tzinfo=timezone.utc)

        return cls(**data)


class ErrorLog(BaseModel):
    """Application error logs for monitoring"""

    id: Optional[str] = Field(default=None, alias="_id")
    error_id: str = Field(..., description="Unique error identifier")
    level: str = Field(..., description="Error level (error, warning, critical)")
    message: str = Field(..., description="Error message")
    source: str = Field(..., description="Error source (endpoint, service, etc.)")
    stack_trace: Optional[str] = Field(default=None, description="Stack trace")
    user_id: Optional[str] = Field(default=None, description="User ID if applicable")
    request_path: Optional[str] = Field(default=None, description="Request path")
    request_method: Optional[str] = Field(default=None, description="HTTP method")
    request_body: Optional[Dict[str, Any]] = Field(default=None, description="Request body (sanitized)")
    ip_address: Optional[str] = Field(default=None, description="Client IP")
    user_agent: Optional[str] = Field(default=None, description="User agent")
    resolved: bool = Field(default=False, description="Error resolved status")
    resolved_by: Optional[str] = Field(default=None, description="Admin who resolved")
    resolved_at: Optional[datetime] = Field(default=None, description="Resolution timestamp")
    resolution_notes: Optional[str] = Field(default=None, description="Resolution notes")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

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
    def from_mongo(cls, data: Dict[str, Any]) -> "ErrorLog":
        """Create instance from MongoDB document"""
        if not data:
            return None
        if "_id" in data:
            data["_id"] = str(data["_id"])

        datetime_fields = ["timestamp", "resolved_at"]
        for field in datetime_fields:
            if field in data and data[field] is not None:
                dt_value = data[field]
                if isinstance(dt_value, datetime) and dt_value.tzinfo is None:
                    data[field] = dt_value.replace(tzinfo=timezone.utc)

        return cls(**data)


class APIRequestLog(BaseModel):
    """API request logs for monitoring and analytics"""

    id: Optional[str] = Field(default=None, alias="_id")
    request_id: str = Field(..., description="Unique request identifier")
    endpoint: str = Field(..., description="API endpoint path")
    method: str = Field(..., description="HTTP method")
    user_id: Optional[str] = Field(default=None, description="Authenticated user ID")
    user_role: Optional[str] = Field(default=None, description="User role")
    status_code: int = Field(..., description="Response status code")
    response_time_ms: float = Field(..., description="Response time in milliseconds")
    ip_address: Optional[str] = Field(default=None, description="Client IP")
    user_agent: Optional[str] = Field(default=None, description="User agent")
    request_size: Optional[int] = Field(default=None, description="Request size in bytes")
    response_size: Optional[int] = Field(default=None, description="Response size in bytes")
    error: Optional[str] = Field(default=None, description="Error message if any")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

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
    def from_mongo(cls, data: Dict[str, Any]) -> "APIRequestLog":
        """Create instance from MongoDB document"""
        if not data:
            return None
        if "_id" in data:
            data["_id"] = str(data["_id"])

        if "timestamp" in data and data["timestamp"] is not None:
            dt_value = data["timestamp"]
            if isinstance(dt_value, datetime) and dt_value.tzinfo is None:
                data["timestamp"] = dt_value.replace(tzinfo=timezone.utc)

        return cls(**data)


# Request/Response Schemas for API endpoints

class CreateUserRequest(BaseModel):
    """Request schema for creating a new user"""
    email: Optional[str] = Field(default=None, description="User email")
    phone: Optional[str] = Field(default=None, description="User phone")
    name: str = Field(..., min_length=2, max_length=100, description="User name")
    password: str = Field(..., min_length=8, description="User password")
    role: str = Field(default="citizen", description="User role")
    authority_organization: Optional[str] = Field(default=None)
    authority_designation: Optional[str] = Field(default=None)
    authority_jurisdiction: Optional[List[str]] = Field(default=None)


class UpdateUserRequest(BaseModel):
    """Request schema for updating user"""
    name: Optional[str] = Field(default=None, min_length=2, max_length=100)
    email: Optional[str] = Field(default=None)
    phone: Optional[str] = Field(default=None)
    is_active: Optional[bool] = Field(default=None)
    credibility_score: Optional[int] = Field(default=None, ge=0, le=100)
    authority_organization: Optional[str] = Field(default=None)
    authority_designation: Optional[str] = Field(default=None)
    authority_jurisdiction: Optional[List[str]] = Field(default=None)


class BanUserRequest(BaseModel):
    """Request schema for banning a user"""
    reason: str = Field(..., min_length=10, max_length=500, description="Ban reason")


class AssignRoleRequest(BaseModel):
    """Request schema for assigning role"""
    role: str = Field(..., description="New role to assign")
    reason: Optional[str] = Field(default=None, description="Reason for role change")


class CreateSettingRequest(BaseModel):
    """Request schema for creating a setting"""
    category: SettingCategory = Field(...)
    key: str = Field(..., min_length=1, max_length=100)
    value: Any = Field(...)
    value_type: SettingValueType = Field(...)
    label: str = Field(..., min_length=1, max_length=200)
    description: str = Field(..., min_length=1, max_length=500)
    is_sensitive: bool = Field(default=False)
    is_editable: bool = Field(default=True)
    validation_rules: Optional[Dict[str, Any]] = Field(default=None)


class UpdateSettingRequest(BaseModel):
    """Request schema for updating a setting"""
    value: Any = Field(...)


class ExportAuditLogsRequest(BaseModel):
    """Request schema for exporting audit logs"""
    format: str = Field(default="csv", description="Export format (csv, xlsx)")
    start_date: Optional[datetime] = Field(default=None)
    end_date: Optional[datetime] = Field(default=None)
    action_types: Optional[List[str]] = Field(default=None)
    admin_id: Optional[str] = Field(default=None)


# Export for easy imports
__all__ = [
    'SettingCategory',
    'SettingValueType',
    'HealthStatus',
    'AdminActionType',
    'SystemSettings',
    'AdminActivityLog',
    'SystemHealthMetric',
    'ErrorLog',
    'APIRequestLog',
    'CreateUserRequest',
    'UpdateUserRequest',
    'BanUserRequest',
    'AssignRoleRequest',
    'CreateSettingRequest',
    'UpdateSettingRequest',
    'ExportAuditLogsRequest',
]
