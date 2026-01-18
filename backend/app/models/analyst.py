"""
Analyst Module Models
MongoDB document models for analyst features:
- Notes, Saved Queries, Scheduled Reports, Export Jobs, API Keys
"""

from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from enum import Enum
from pydantic import BaseModel, Field, EmailStr
from bson import ObjectId
from app.utils.timezone import to_ist_isoformat


# ============================================================================
# ENUMS
# ============================================================================

class NoteReferenceType(str, Enum):
    """Type of entity a note references"""
    REPORT = "report"
    LOCATION = "location"
    HAZARD_TYPE = "hazard_type"
    ALERT = "alert"
    GENERAL = "general"


class NoteColor(str, Enum):
    """Color coding options for notes"""
    DEFAULT = "default"
    RED = "red"
    ORANGE = "orange"
    YELLOW = "yellow"
    GREEN = "green"
    BLUE = "blue"
    PURPLE = "purple"
    PINK = "pink"


class QueryType(str, Enum):
    """Type of saved query"""
    ANALYTICS = "analytics"
    REPORTS = "reports"
    TRENDS = "trends"
    GEO = "geo"
    NLP = "nlp"
    CUSTOM = "custom"


class ChartType(str, Enum):
    """Chart visualization types"""
    LINE = "line"
    BAR = "bar"
    PIE = "pie"
    DONUT = "donut"
    AREA = "area"
    HEATMAP = "heatmap"
    SCATTER = "scatter"
    RADAR = "radar"


class ScheduleType(str, Enum):
    """Report schedule frequency"""
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    CUSTOM = "custom"


class ReportType(str, Enum):
    """Scheduled report types"""
    DAILY_SUMMARY = "daily_summary"
    WEEKLY_ANALYTICS = "weekly_analytics"
    MONTHLY_OVERVIEW = "monthly_overview"
    HAZARD_REPORT = "hazard_report"
    CUSTOM = "custom"


class DeliveryMethod(str, Enum):
    """Report delivery methods"""
    EMAIL = "email"
    DOWNLOAD = "download"


class ExportFormat(str, Enum):
    """Export file formats"""
    CSV = "csv"
    EXCEL = "excel"
    PDF = "pdf"


class ExportType(str, Enum):
    """Type of data to export"""
    REPORTS = "reports"
    ANALYTICS = "analytics"
    TRENDS = "trends"
    GEO = "geo"
    CUSTOM = "custom"


class ExportStatus(str, Enum):
    """Export job status"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class ApiKeyPermission(str, Enum):
    """API key permission scopes"""
    READ_ANALYTICS = "read_analytics"
    READ_REPORTS = "read_reports"
    READ_MONITORING = "read_monitoring"
    EXPORT = "export"


# ============================================================================
# ANALYST NOTE MODEL
# ============================================================================

class AnalystNote(BaseModel):
    """Personal notes/annotations for analysts"""

    # MongoDB ObjectId (internal)
    id: Optional[str] = Field(default=None, alias="_id")

    # Unique identifier
    note_id: str = Field(..., description="Unique note identifier (NOTE_timestamp_uuid)")

    # Owner
    user_id: str = Field(..., description="Analyst's user_id")

    # Content
    title: str = Field(..., min_length=1, max_length=200, description="Note title")
    content: str = Field(default="", max_length=10000, description="Markdown content")
    tags: List[str] = Field(default_factory=list, description="Tags for categorization")

    # Reference (optional - what this note is about)
    reference_type: Optional[NoteReferenceType] = Field(
        default=None,
        description="Type of entity this note references"
    )
    reference_id: Optional[str] = Field(
        default=None,
        description="ID of referenced entity"
    )
    reference_data: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Cached reference metadata"
    )

    # Location context (optional)
    location: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Location context {lat, lon, name}"
    )

    # Data snapshot
    data_snapshot: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Captured analytics data at time of note"
    )

    # Organization
    is_pinned: bool = Field(default=False, description="Pin to top of list")
    color: NoteColor = Field(default=NoteColor.DEFAULT, description="Color coding")

    # Timestamps
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

    @classmethod
    def from_mongo(cls, data: Dict[str, Any]) -> "AnalystNote":
        """Create AnalystNote instance from MongoDB document"""
        if not data:
            return None

        if "_id" in data:
            data["_id"] = str(data["_id"])

        # Ensure datetime fields are timezone-aware
        for field in ["created_at", "updated_at"]:
            if field in data and data[field] is not None:
                dt_value = data[field]
                if isinstance(dt_value, datetime) and dt_value.tzinfo is None:
                    data[field] = dt_value.replace(tzinfo=timezone.utc)

        return cls(**data)


# ============================================================================
# SAVED QUERY MODEL
# ============================================================================

class SavedQuery(BaseModel):
    """Saved query configurations for analysts"""

    id: Optional[str] = Field(default=None, alias="_id")

    query_id: str = Field(..., description="Unique query identifier")
    user_id: str = Field(..., description="Owner analyst's user_id")

    # Query metadata
    name: str = Field(..., min_length=1, max_length=100, description="Query name")
    description: Optional[str] = Field(default=None, max_length=500, description="Query description")

    # Query configuration
    query_type: QueryType = Field(..., description="Type of query")
    filters: Dict[str, Any] = Field(default_factory=dict, description="Filter parameters")
    aggregations: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Aggregation pipeline config"
    )
    date_range: Dict[str, Any] = Field(
        default_factory=lambda: {"relative": "7days"},
        description="Date range {start, end, relative}"
    )

    # Visualization preferences
    chart_type: Optional[ChartType] = Field(default=None, description="Preferred chart type")
    chart_config: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Chart-specific configuration"
    )

    # Usage tracking
    last_executed: Optional[datetime] = Field(default=None, description="Last execution time")
    execution_count: int = Field(default=0, ge=0, description="Number of executions")

    # Timestamps
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Config:
        populate_by_name = True
        json_encoders = {
            ObjectId: str,
            datetime: lambda v: to_ist_isoformat(v)
        }

    def to_mongo(self) -> Dict[str, Any]:
        data = self.model_dump(by_alias=True, exclude_none=True)
        if data.get("_id") is None:
            data.pop("_id", None)
        return data

    @classmethod
    def from_mongo(cls, data: Dict[str, Any]) -> "SavedQuery":
        if not data:
            return None

        if "_id" in data:
            data["_id"] = str(data["_id"])

        for field in ["created_at", "updated_at", "last_executed"]:
            if field in data and data[field] is not None:
                dt_value = data[field]
                if isinstance(dt_value, datetime) and dt_value.tzinfo is None:
                    data[field] = dt_value.replace(tzinfo=timezone.utc)

        return cls(**data)


# ============================================================================
# SCHEDULED REPORT MODEL
# ============================================================================

class ScheduledReport(BaseModel):
    """Scheduled report configuration"""

    id: Optional[str] = Field(default=None, alias="_id")

    schedule_id: str = Field(..., description="Unique schedule identifier")
    user_id: str = Field(..., description="Owner analyst's user_id")

    # Report metadata
    name: str = Field(..., min_length=1, max_length=100, description="Report name")
    description: Optional[str] = Field(default=None, max_length=500)

    # Report configuration
    report_type: ReportType = Field(..., description="Type of report")
    query_config: Dict[str, Any] = Field(
        default_factory=dict,
        description="Query/filter configuration"
    )
    sections: List[str] = Field(
        default_factory=lambda: ["summary", "trends"],
        description="Report sections to include"
    )

    # Schedule configuration
    schedule_type: ScheduleType = Field(..., description="Schedule frequency")
    schedule_cron: Optional[str] = Field(
        default=None,
        description="Cron expression for custom schedules"
    )
    schedule_time: str = Field(
        default="09:00",
        description="Time of day HH:MM (UTC)"
    )
    schedule_days: Optional[List[int]] = Field(
        default=None,
        description="Days to run (0=Mon, 6=Sun for weekly)"
    )
    timezone: str = Field(default="Asia/Kolkata", description="User's timezone")

    # Delivery configuration
    delivery_method: DeliveryMethod = Field(
        default=DeliveryMethod.EMAIL,
        description="How to deliver report"
    )
    delivery_email: Optional[EmailStr] = Field(
        default=None,
        description="Email address for delivery"
    )
    export_format: ExportFormat = Field(
        default=ExportFormat.PDF,
        description="Report file format"
    )

    # Status
    is_active: bool = Field(default=True, description="Whether schedule is active")
    last_run: Optional[datetime] = Field(default=None, description="Last execution time")
    next_run: Optional[datetime] = Field(default=None, description="Next scheduled run")
    last_status: Optional[str] = Field(default=None, description="Last run status")
    last_error: Optional[str] = Field(default=None, description="Last error message if failed")

    # Timestamps
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Config:
        populate_by_name = True
        json_encoders = {
            ObjectId: str,
            datetime: lambda v: to_ist_isoformat(v)
        }

    def to_mongo(self) -> Dict[str, Any]:
        data = self.model_dump(by_alias=True, exclude_none=True)
        if data.get("_id") is None:
            data.pop("_id", None)
        return data

    @classmethod
    def from_mongo(cls, data: Dict[str, Any]) -> "ScheduledReport":
        if not data:
            return None

        if "_id" in data:
            data["_id"] = str(data["_id"])

        for field in ["created_at", "updated_at", "last_run", "next_run"]:
            if field in data and data[field] is not None:
                dt_value = data[field]
                if isinstance(dt_value, datetime) and dt_value.tzinfo is None:
                    data[field] = dt_value.replace(tzinfo=timezone.utc)

        return cls(**data)


# ============================================================================
# EXPORT JOB MODEL
# ============================================================================

class ExportJob(BaseModel):
    """Export job for tracking export requests"""

    id: Optional[str] = Field(default=None, alias="_id")

    job_id: str = Field(..., description="Unique job identifier")
    user_id: str = Field(..., description="Requesting user's ID")

    # Job configuration
    export_type: ExportType = Field(..., description="Type of data to export")
    export_format: ExportFormat = Field(..., description="Output file format")
    query_config: Dict[str, Any] = Field(
        default_factory=dict,
        description="Query parameters"
    )
    date_range: Dict[str, Any] = Field(
        default_factory=dict,
        description="Date range for data"
    )
    columns: Optional[List[str]] = Field(
        default=None,
        description="Specific columns to include"
    )

    # Job status
    status: ExportStatus = Field(default=ExportStatus.PENDING, description="Current status")
    progress: int = Field(default=0, ge=0, le=100, description="Progress percentage")
    error_message: Optional[str] = Field(default=None, description="Error message if failed")

    # Output
    file_path: Optional[str] = Field(default=None, description="Path to generated file")
    file_name: Optional[str] = Field(default=None, description="Generated file name")
    file_size: Optional[int] = Field(default=None, description="File size in bytes")
    record_count: Optional[int] = Field(default=None, description="Number of records exported")

    # Timestamps
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    started_at: Optional[datetime] = Field(default=None, description="When processing started")
    completed_at: Optional[datetime] = Field(default=None, description="When job completed")
    expires_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Auto-delete after this time (TTL)"
    )

    class Config:
        populate_by_name = True
        json_encoders = {
            ObjectId: str,
            datetime: lambda v: to_ist_isoformat(v)
        }

    def to_mongo(self) -> Dict[str, Any]:
        data = self.model_dump(by_alias=True, exclude_none=True)
        if data.get("_id") is None:
            data.pop("_id", None)
        return data

    @classmethod
    def from_mongo(cls, data: Dict[str, Any]) -> "ExportJob":
        if not data:
            return None

        if "_id" in data:
            data["_id"] = str(data["_id"])

        for field in ["created_at", "started_at", "completed_at", "expires_at"]:
            if field in data and data[field] is not None:
                dt_value = data[field]
                if isinstance(dt_value, datetime) and dt_value.tzinfo is None:
                    data[field] = dt_value.replace(tzinfo=timezone.utc)

        return cls(**data)


# ============================================================================
# API KEY MODEL
# ============================================================================

class AnalystApiKey(BaseModel):
    """API key for external tool access"""

    id: Optional[str] = Field(default=None, alias="_id")

    key_id: str = Field(..., description="Unique key identifier")
    user_id: str = Field(..., description="Owner analyst's user_id")

    # Key metadata
    name: str = Field(..., min_length=1, max_length=100, description="Key name/description")

    # Key value (hashed for storage)
    key_hash: str = Field(..., description="Hashed API key")
    key_prefix: str = Field(..., description="First 8 chars for display (e.g., 'cg_abc123')")

    # Permissions
    permissions: List[ApiKeyPermission] = Field(
        default_factory=lambda: [ApiKeyPermission.READ_ANALYTICS],
        description="Granted permissions"
    )
    rate_limit: int = Field(default=1000, ge=1, le=10000, description="Requests per hour")

    # Usage tracking
    last_used: Optional[datetime] = Field(default=None, description="Last usage time")
    usage_count: int = Field(default=0, ge=0, description="Total usage count")

    # Status
    is_active: bool = Field(default=True, description="Whether key is active")
    expires_at: Optional[datetime] = Field(default=None, description="Key expiration time")

    # Timestamps
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Config:
        populate_by_name = True
        json_encoders = {
            ObjectId: str,
            datetime: lambda v: to_ist_isoformat(v)
        }

    def to_mongo(self) -> Dict[str, Any]:
        data = self.model_dump(by_alias=True, exclude_none=True)
        if data.get("_id") is None:
            data.pop("_id", None)
        return data

    @classmethod
    def from_mongo(cls, data: Dict[str, Any]) -> "AnalystApiKey":
        if not data:
            return None

        if "_id" in data:
            data["_id"] = str(data["_id"])

        for field in ["created_at", "last_used", "expires_at"]:
            if field in data and data[field] is not None:
                dt_value = data[field]
                if isinstance(dt_value, datetime) and dt_value.tzinfo is None:
                    data[field] = dt_value.replace(tzinfo=timezone.utc)

        return cls(**data)


# ============================================================================
# REQUEST/RESPONSE SCHEMAS
# ============================================================================

class CreateNoteRequest(BaseModel):
    """Request schema for creating a note"""
    title: str = Field(..., min_length=1, max_length=200)
    content: str = Field(default="", max_length=10000)
    tags: List[str] = Field(default_factory=list)
    reference_type: Optional[NoteReferenceType] = None
    reference_id: Optional[str] = None
    location: Optional[Dict[str, Any]] = None
    data_snapshot: Optional[Dict[str, Any]] = None
    color: NoteColor = NoteColor.DEFAULT


class UpdateNoteRequest(BaseModel):
    """Request schema for updating a note"""
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    content: Optional[str] = Field(None, max_length=10000)
    tags: Optional[List[str]] = None
    is_pinned: Optional[bool] = None
    color: Optional[NoteColor] = None


class CreateQueryRequest(BaseModel):
    """Request schema for creating a saved query"""
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    query_type: QueryType
    filters: Dict[str, Any] = Field(default_factory=dict)
    date_range: Dict[str, Any] = Field(default_factory=lambda: {"relative": "7days"})
    chart_type: Optional[ChartType] = None
    chart_config: Optional[Dict[str, Any]] = None


class CreateScheduledReportRequest(BaseModel):
    """Request schema for creating a scheduled report"""
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    report_type: ReportType
    query_config: Dict[str, Any] = Field(default_factory=dict)
    sections: List[str] = Field(default_factory=lambda: ["summary", "trends"])
    schedule_type: ScheduleType
    schedule_time: str = Field(default="09:00")
    schedule_days: Optional[List[int]] = None
    timezone: str = Field(default="Asia/Kolkata")
    delivery_method: DeliveryMethod = DeliveryMethod.EMAIL
    delivery_email: Optional[EmailStr] = None
    export_format: ExportFormat = ExportFormat.PDF


class CreateExportRequest(BaseModel):
    """Request schema for creating an export job"""
    export_type: ExportType
    export_format: ExportFormat
    query_config: Dict[str, Any] = Field(default_factory=dict)
    date_range: Dict[str, Any] = Field(default_factory=dict)
    columns: Optional[List[str]] = None


class CreateApiKeyRequest(BaseModel):
    """Request schema for creating an API key"""
    name: str = Field(..., min_length=1, max_length=100)
    permissions: List[ApiKeyPermission] = Field(
        default_factory=lambda: [ApiKeyPermission.READ_ANALYTICS]
    )
    rate_limit: int = Field(default=1000, ge=1, le=10000)
    expires_in_days: Optional[int] = Field(default=None, ge=1, le=365)


# ============================================================================
# EXPORTS
# ============================================================================

__all__ = [
    # Enums
    'NoteReferenceType',
    'NoteColor',
    'QueryType',
    'ChartType',
    'ScheduleType',
    'ReportType',
    'DeliveryMethod',
    'ExportFormat',
    'ExportType',
    'ExportStatus',
    'ApiKeyPermission',

    # Models
    'AnalystNote',
    'SavedQuery',
    'ScheduledReport',
    'ExportJob',
    'AnalystApiKey',

    # Request schemas
    'CreateNoteRequest',
    'UpdateNoteRequest',
    'CreateQueryRequest',
    'CreateScheduledReportRequest',
    'CreateExportRequest',
    'CreateApiKeyRequest',
]
