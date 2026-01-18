"""
Hazard Report Model
MongoDB document models for hazard reporting system
"""

from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from enum import Enum
from pydantic import BaseModel, Field, validator
from bson import ObjectId
from app.utils.timezone import to_ist_isoformat


class HazardCategory(str, Enum):
    """Hazard category enumeration"""
    NATURAL = "natural"
    HUMAN_MADE = "humanMade"


class HazardType(str, Enum):
    """Hazard type enumeration"""
    # Natural hazards
    HIGH_WAVES = "High Waves"
    RIP_CURRENT = "Rip Current"
    STORM_SURGE = "Storm Surge/Cyclone Effects"
    FLOODED_COASTLINE = "Flooded Coastline"
    BEACHED_ANIMAL = "Beached Aquatic Animal"

    # Human-made hazards
    OIL_SPILL = "Oil Spill"
    FISHER_NETS = "Fisher Nets Entanglement"
    SHIP_WRECK = "Ship Wreck"
    CHEMICAL_SPILL = "Chemical Spill"
    PLASTIC_POLLUTION = "Plastic Pollution"


class VerificationStatus(str, Enum):
    """Simplified verification status enumeration for 6-layer pipeline"""
    PENDING = "pending"                        # Legacy - treated same as needs_manual_review
    VERIFIED = "verified"                      # Auto-approved (≥85%) or manually approved
    REJECTED = "rejected"                      # Manually rejected by analyst/authority
    AUTO_REJECTED = "auto_rejected"            # Failed geofence (outside coastal area)
    NEEDS_MANUAL_REVIEW = "needs_manual_review"  # Score 40-85%, awaiting analyst/authority decision
    AI_RECOMMENDED = "ai_recommended"          # Legacy - treated same as needs_manual_review


class ApprovalSource(str, Enum):
    """Source of report approval for hybrid verification mode"""
    AI_AUTO = "ai_auto"                    # Score ≥85%, fully automated approval
    AI_RECOMMENDED = "ai_recommended"      # Score 75-85%, AI recommended + authority/analyst confirmed
    AUTHORITY_MANUAL = "authority_manual"  # Authority manually verified
    ANALYST_VERIFIED = "analyst_verified"  # Analyst manually verified


class TicketCreationStatus(str, Enum):
    """Status of ticket creation for a report"""
    NOT_ELIGIBLE = "not_eligible"  # Report not verified yet or rejected
    PENDING = "pending"            # Awaiting ticket creation
    CREATED = "created"            # Ticket successfully created
    FAILED = "failed"              # Ticket creation failed (needs retry)


class Location(BaseModel):
    """Location data model"""
    latitude: float = Field(..., description="Latitude coordinate")
    longitude: float = Field(..., description="Longitude coordinate")
    address: Optional[str] = Field(default=None, description="Human-readable address")
    region: Optional[str] = Field(default=None, description="Region/state name")
    district: Optional[str] = Field(default=None, description="District/city name")

    # GeoJSON Point for MongoDB geospatial queries
    @property
    def geojson(self) -> Dict[str, Any]:
        """Convert to GeoJSON Point format for MongoDB"""
        return {
            "type": "Point",
            "coordinates": [self.longitude, self.latitude]
        }


class ThreatLevel(str, Enum):
    """Multi-hazard threat classification levels"""
    WARNING = "warning"      # Currently occurring
    ALERT = "alert"          # Will occur soon
    WATCH = "watch"          # Possible
    NO_THREAT = "no_threat"  # Will not occur


class WeatherData(BaseModel):
    """Weather data model (basic - for backward compatibility)"""
    temperature: float = Field(..., description="Temperature in Celsius")
    feelsLike: float = Field(..., description="Feels like temperature in Celsius")
    condition: str = Field(..., description="Weather condition")
    visibility: float = Field(..., description="Visibility in km")
    wind: float = Field(..., description="Wind speed in km/h")
    windDirection: str = Field(..., description="Wind direction (N, NE, E, etc.)")
    windDegree: int = Field(..., description="Wind degree (0-360)")
    pressure: float = Field(..., description="Pressure in inches Hg")
    humidity: int = Field(..., description="Humidity percentage")
    description: str = Field(..., description="Weather description")


class ExtendedWeatherData(BaseModel):
    """Extended weather parameters from WeatherAPI"""
    # Temperature
    temp_c: Optional[float] = Field(default=None, description="Temperature in Celsius")
    feelslike_c: Optional[float] = Field(default=None, description="Feels like temperature in Celsius")

    # Wind parameters
    wind_mph: Optional[float] = Field(default=None, description="Wind speed in mph")
    wind_kph: Optional[float] = Field(default=None, description="Wind speed in kph")
    wind_degree: Optional[int] = Field(default=None, description="Wind direction in degrees")
    wind_dir: Optional[str] = Field(default=None, description="Wind direction (N, NE, E, etc.)")
    gust_mph: Optional[float] = Field(default=None, description="Wind gust in mph")
    gust_kph: Optional[float] = Field(default=None, description="Wind gust in kph")

    # Pressure & Precipitation
    pressure_mb: Optional[float] = Field(default=None, description="Pressure in millibars")
    precip_mm: Optional[float] = Field(default=None, description="Precipitation in mm")
    will_it_rain: Optional[int] = Field(default=None, description="Will it rain (1=yes, 0=no)")

    # Visibility & Conditions
    vis_km: Optional[float] = Field(default=None, description="Visibility in km")
    humidity: Optional[int] = Field(default=None, description="Humidity percentage")
    cloud: Optional[int] = Field(default=None, description="Cloud cover percentage")
    uv: Optional[float] = Field(default=None, description="UV index")
    condition: Optional[str] = Field(default=None, description="Weather condition text")
    condition_code: Optional[int] = Field(default=None, description="Weather condition code")

    # Timestamps
    time: Optional[str] = Field(default=None, description="Local time")
    last_updated: Optional[str] = Field(default=None, description="Last update time")
    last_updated_epoch: Optional[int] = Field(default=None, description="Last update epoch")


class MarineData(BaseModel):
    """Marine parameters from WeatherAPI Marine"""
    # Wave data
    sig_ht_mt: Optional[float] = Field(default=None, description="Significant wave height in meters")
    swell_ht_mt: Optional[float] = Field(default=None, description="Swell height in meters")
    swell_period_secs: Optional[float] = Field(default=None, description="Swell period in seconds")
    swell_dir: Optional[int] = Field(default=None, description="Swell direction in degrees")
    swell_dir_16_point: Optional[str] = Field(default=None, description="Swell direction (16-point)")

    # Water temperature
    water_temp_c: Optional[float] = Field(default=None, description="Water temperature in Celsius")
    water_temp_f: Optional[float] = Field(default=None, description="Water temperature in Fahrenheit")

    # Tide data
    tide_time: Optional[str] = Field(default=None, description="Tide time")
    tide_height_mt: Optional[float] = Field(default=None, description="Tide height in meters")
    tide_type: Optional[str] = Field(default=None, description="Tide type (HIGH/LOW)")


class AstronomyData(BaseModel):
    """Astronomy parameters from WeatherAPI"""
    sunrise: Optional[str] = Field(default=None, description="Sunrise time")
    sunset: Optional[str] = Field(default=None, description="Sunset time")
    moonrise: Optional[str] = Field(default=None, description="Moonrise time")
    moonset: Optional[str] = Field(default=None, description="Moonset time")
    moon_phase: Optional[str] = Field(default=None, description="Moon phase")
    moon_illumination: Optional[int] = Field(default=None, description="Moon illumination percentage")
    is_day: Optional[int] = Field(default=None, description="Is daytime (1=yes, 0=no)")


class SeismicData(BaseModel):
    """USGS Earthquake/Seismic parameters"""
    # Earthquake properties
    magnitude: Optional[float] = Field(default=None, description="Earthquake magnitude")
    depth_km: Optional[float] = Field(default=None, description="Earthquake depth in km")
    place: Optional[str] = Field(default=None, description="Earthquake location description")
    time: Optional[datetime] = Field(default=None, description="Earthquake time")
    time_epoch: Optional[int] = Field(default=None, description="Earthquake time (epoch ms)")

    # Tsunami & Alert
    tsunami: Optional[int] = Field(default=None, description="Tsunami warning (1=yes, 0=no)")
    alert: Optional[str] = Field(default=None, description="Alert level (green/yellow/orange/red)")

    # Additional seismic info
    earthquake_id: Optional[str] = Field(default=None, description="USGS earthquake ID")
    distance_km: Optional[float] = Field(default=None, description="Distance from report location in km")
    felt: Optional[int] = Field(default=None, description="Number of felt reports")
    significance: Optional[int] = Field(default=None, description="Significance score")


class EnvironmentalSnapshot(BaseModel):
    """Complete environmental snapshot at time of report"""
    # Weather data
    weather: Optional[ExtendedWeatherData] = Field(default=None, description="Extended weather data")

    # Marine data
    marine: Optional[MarineData] = Field(default=None, description="Marine/ocean data")

    # Astronomy data
    astronomy: Optional[AstronomyData] = Field(default=None, description="Astronomy data")

    # Seismic data
    seismic: Optional[SeismicData] = Field(default=None, description="Seismic/earthquake data")

    # Fetch metadata
    fetched_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Data fetch timestamp")
    fetch_success: bool = Field(default=True, description="Whether all data was fetched successfully")
    fetch_errors: Optional[List[str]] = Field(default=None, description="Any fetch errors")


class HazardClassification(BaseModel):
    """Multi-hazard detection classification result"""
    # Primary classification
    threat_level: ThreatLevel = Field(..., description="Overall threat level")
    hazard_type: Optional[str] = Field(default=None, description="Detected hazard type (tsunami, cyclone, etc.)")

    # Confidence & reasoning
    confidence: float = Field(default=0.0, ge=0.0, le=1.0, description="Classification confidence")
    reasoning: str = Field(default="", description="Classification reasoning")

    # Individual hazard assessments
    tsunami_threat: Optional[ThreatLevel] = Field(default=ThreatLevel.NO_THREAT, description="Tsunami threat")
    cyclone_threat: Optional[ThreatLevel] = Field(default=ThreatLevel.NO_THREAT, description="Cyclone threat")
    high_waves_threat: Optional[ThreatLevel] = Field(default=ThreatLevel.NO_THREAT, description="High waves threat")
    coastal_flood_threat: Optional[ThreatLevel] = Field(default=ThreatLevel.NO_THREAT, description="Coastal flood threat")
    rip_current_threat: Optional[ThreatLevel] = Field(default=ThreatLevel.NO_THREAT, description="Rip current threat")

    # Recommendations
    recommendations: Optional[List[str]] = Field(default=None, description="Safety recommendations")

    # Classification metadata
    classified_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Classification timestamp")
    model_version: str = Field(default="1.0", description="Classifier model version")


class HazardReport(BaseModel):
    """Hazard report document model"""

    # MongoDB ObjectId (internal)
    id: Optional[str] = Field(default=None, alias="_id")

    # Report identification
    report_id: str = Field(..., description="Unique report identifier")

    # Reporter information
    user_id: str = Field(..., description="User ID of the reporter")
    user_name: Optional[str] = Field(default=None, description="Name of the reporter")

    # Hazard details
    hazard_type: HazardType = Field(..., description="Type of hazard")
    category: HazardCategory = Field(..., description="Hazard category")
    description: Optional[str] = Field(default=None, description="Text description of the hazard")

    # Media files
    image_url: str = Field(..., description="URL/path to captured image")
    voice_note_url: Optional[str] = Field(default=None, description="URL/path to voice note")

    # Location data
    location: Location = Field(..., description="Location of the hazard")

    # Weather data at time of report
    weather: Optional[WeatherData] = Field(default=None, description="Weather data at location")

    # Verification (Enhanced for 6-Layer Pipeline)
    verification_status: VerificationStatus = Field(
        default=VerificationStatus.PENDING,
        description="Verification status"
    )
    verified_by: Optional[str] = Field(default=None, description="Authority user ID who verified")
    verified_by_name: Optional[str] = Field(default=None, description="Name of authority who verified")
    verified_at: Optional[datetime] = Field(default=None, description="Verification timestamp")
    verification_notes: Optional[str] = Field(default=None, description="Verification notes/comments")
    rejection_reason: Optional[str] = Field(default=None, description="Reason for rejection if status is rejected")

    # 6-Layer Verification Pipeline Results
    verification_score: Optional[float] = Field(
        default=None,
        ge=0.0, le=100.0,
        description="Composite verification score (0-100)"
    )
    verification_result: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Full verification result including all layer results"
    )
    verification_id: Optional[str] = Field(
        default=None,
        description="Unique verification ID"
    )
    vision_classification: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Image classification results from Vision Model"
    )
    geofence_valid: Optional[bool] = Field(
        default=None,
        description="Whether location passed geofence validation"
    )
    geofence_distance_km: Optional[float] = Field(
        default=None,
        description="Distance to nearest coastline in km"
    )

    # Risk Assessment (for Authorities)
    risk_level: Optional[str] = Field(
        default=None,
        description="Assessed risk level: low, medium, high, critical"
    )
    urgency: Optional[str] = Field(
        default="normal",
        description="Urgency: low, normal, high, urgent"
    )
    requires_immediate_action: bool = Field(
        default=False,
        description="Flag for reports requiring immediate response"
    )

    # NLP Insights (for Analysts)
    nlp_sentiment: Optional[str] = Field(
        default=None,
        description="Sentiment analysis result: positive, neutral, negative, panic"
    )
    nlp_keywords: Optional[List[str]] = Field(
        default=None,
        description="Extracted keywords from description"
    )
    nlp_entities: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Named entities extracted (locations, times, etc.)"
    )
    nlp_risk_score: Optional[float] = Field(
        default=None,
        description="AI-calculated risk score (0.0 to 1.0)"
    )
    nlp_summary: Optional[str] = Field(
        default=None,
        description="AI-generated summary of the report"
    )

    # Additional Data (for Analysts - Remote Sensing, etc.)
    satellite_data: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Satellite/remote sensing data if available"
    )
    wave_height_data: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Wave height measurements"
    )
    tide_data: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Tide information at time of report"
    )

    # Engagement metrics
    likes: int = Field(default=0, description="Number of likes")
    comments: int = Field(default=0, description="Number of comments")
    views: int = Field(default=0, description="Number of views")

    # Credibility impact
    credibility_impact: int = Field(default=0, description="Impact on user credibility score")

    # Timestamps
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Report creation timestamp"
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Last update timestamp"
    )

    # Status flags
    is_active: bool = Field(default=True, description="Is report active/visible")
    is_deleted: bool = Field(default=False, description="Soft delete flag")

    # Environmental data snapshot at time of report (NEW)
    environmental_snapshot: Optional[EnvironmentalSnapshot] = Field(
        default=None,
        description="Complete environmental data snapshot fetched at submission time"
    )

    # Multi-hazard classification result (NEW)
    hazard_classification: Optional[HazardClassification] = Field(
        default=None,
        description="Multi-hazard detection threat classification result"
    )

    # Ticketing System Integration (NEW)
    ticket_id: Optional[str] = Field(
        default=None,
        description="Associated ticket ID for three-way communication"
    )
    has_ticket: bool = Field(
        default=False,
        description="Whether a ticket has been created for this report"
    )
    ticket_status: Optional[str] = Field(
        default=None,
        description="Current status of the associated ticket"
    )
    ticket_created_at: Optional[datetime] = Field(
        default=None,
        description="When the ticket was created"
    )

    # Hybrid Approval System (V2)
    approval_source: Optional[str] = Field(
        default=None,
        description="Source of approval: ai_auto, ai_recommended, authority_manual, analyst_verified"
    )
    approval_source_details: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Details about approval: {approved_by, approved_at, ai_score, confirmation_by, etc.}"
    )
    ticket_creation_status: str = Field(
        default="not_eligible",
        description="Status of ticket creation: not_eligible, pending, created, failed"
    )
    ticket_creation_attempted_at: Optional[datetime] = Field(
        default=None,
        description="When ticket creation was last attempted"
    )
    requires_authority_confirmation: bool = Field(
        default=False,
        description="Whether this report needs authority/analyst to confirm AI recommendation (75-85% score)"
    )
    confirmation_received_at: Optional[datetime] = Field(
        default=None,
        description="When authority/analyst confirmed the AI recommendation"
    )
    confirmed_by: Optional[str] = Field(
        default=None,
        description="User ID of authority/analyst who confirmed the AI recommendation"
    )
    confirmed_by_name: Optional[str] = Field(
        default=None,
        description="Name of authority/analyst who confirmed"
    )

    @classmethod
    def from_mongo(cls, data: Dict[str, Any]) -> "HazardReport":
        """Create HazardReport instance from MongoDB document"""
        if not data:
            return None

        # Make a copy to avoid modifying the original
        data = data.copy()

        # Convert ObjectId to string
        if "_id" in data:
            data["_id"] = str(data["_id"])

        # Ensure all datetime fields are timezone-aware
        datetime_fields = ["created_at", "updated_at", "verified_at", "ticket_created_at",
                          "ticket_creation_attempted_at", "confirmation_received_at"]

        for field in datetime_fields:
            if field in data and data[field] is not None:
                dt_value = data[field]
                if isinstance(dt_value, datetime) and dt_value.tzinfo is None:
                    # If timezone-naive, assume it's UTC (MongoDB default)
                    data[field] = dt_value.replace(tzinfo=timezone.utc)

        # Normalize hazard_type to valid enum value
        if "hazard_type" in data:
            hazard_type = data["hazard_type"]
            # Try to match to a valid HazardType enum value
            valid_hazard_types = {e.value: e for e in HazardType}
            if hazard_type not in valid_hazard_types:
                # Try case-insensitive match or default to HIGH_WAVES
                hazard_type_lower = str(hazard_type).lower()
                matched = False
                for enum_val, enum_member in valid_hazard_types.items():
                    if enum_val.lower() == hazard_type_lower:
                        data["hazard_type"] = enum_member
                        matched = True
                        break
                if not matched:
                    # Default to HIGH_WAVES for unknown types
                    data["hazard_type"] = HazardType.HIGH_WAVES

        # Normalize category to valid enum value
        if "category" in data:
            category = data["category"]
            valid_categories = {e.value: e for e in HazardCategory}
            if category not in valid_categories:
                # Try case-insensitive match or default to NATURAL
                category_lower = str(category).lower()
                matched = False
                for enum_val, enum_member in valid_categories.items():
                    if enum_val.lower() == category_lower:
                        data["category"] = enum_member
                        matched = True
                        break
                if not matched:
                    # Default to NATURAL for unknown categories
                    data["category"] = HazardCategory.NATURAL

        # Normalize verification_status to valid enum value
        if "verification_status" in data:
            status = data["verification_status"]
            valid_statuses = {e.value: e for e in VerificationStatus}
            if status not in valid_statuses:
                # Try case-insensitive match or default to PENDING
                status_lower = str(status).lower()
                matched = False
                for enum_val, enum_member in valid_statuses.items():
                    if enum_val.lower() == status_lower:
                        data["verification_status"] = enum_member
                        matched = True
                        break
                if not matched:
                    # Default to PENDING for unknown statuses
                    data["verification_status"] = VerificationStatus.PENDING

        return cls(**data)

    class Config:
        populate_by_name = True
        json_encoders = {
            datetime: lambda v: to_ist_isoformat(v),
            ObjectId: lambda v: str(v)
        }
        json_schema_extra = {
            "example": {
                "report_id": "RPT_1234567890",
                "user_id": "USR_0987654321",
                "user_name": "John Doe",
                "hazard_type": "High Waves",
                "category": "natural",
                "description": "Large waves breaking onto the shore, dangerous conditions",
                "image_url": "/uploads/hazards/image_123.jpg",
                "voice_note_url": "/uploads/hazards/voice_123.wav",
                "location": {
                    "latitude": 37.7749,
                    "longitude": -122.4194,
                    "address": "Main Beach, San Francisco"
                },
                "weather": {
                    "temperature": 18.5,
                    "feelsLike": 17.8,
                    "condition": "Cloudy",
                    "visibility": 10,
                    "wind": 25.5,
                    "windDirection": "NW",
                    "windDegree": 315,
                    "pressure": 29.92,
                    "humidity": 75,
                    "description": "Partly cloudy"
                },
                "verification_status": "pending",
                "likes": 0,
                "comments": 0,
                "views": 0
            }
        }


class HazardReportCreate(BaseModel):
    """Schema for creating a hazard report"""
    hazard_type: HazardType
    category: HazardCategory
    description: Optional[str] = None
    location: Location
    weather: Optional[WeatherData] = None


class HazardReportUpdate(BaseModel):
    """Schema for updating a hazard report"""
    description: Optional[str] = None
    is_active: Optional[bool] = None


class HazardReportVerify(BaseModel):
    """Schema for verifying a hazard report"""
    verification_status: VerificationStatus
    verification_notes: Optional[str] = None
    credibility_impact: Optional[int] = Field(
        default=5,
        description="Credibility points to award/deduct"
    )


class HazardReportResponse(BaseModel):
    """Response schema for hazard report"""
    id: str = Field(..., alias="_id")
    report_id: str
    user_id: str
    user_name: Optional[str]
    user_profile_picture: Optional[str] = None
    hazard_type: str
    category: str
    description: Optional[str]
    image_url: str
    voice_note_url: Optional[str]
    location: Dict[str, Any]
    weather: Optional[Dict[str, Any]]
    verification_status: str
    verified_by: Optional[str]
    verified_at: Optional[datetime]
    likes: int
    comments: int
    views: int
    created_at: datetime
    updated_at: datetime
    is_active: bool

    class Config:
        populate_by_name = True
        json_encoders = {
            datetime: lambda v: to_ist_isoformat(v)
        }


class VerificationScoreBreakdown(BaseModel):
    """Breakdown of verification scores for display"""
    layer_name: str
    score: float = Field(..., ge=0.0, le=100.0, description="Score as percentage")
    status: str  # pass, fail, skipped
    weight: float
    reasoning: str


class ReportInsights(BaseModel):
    """Aggregated insights from a hazard report for tickets/display"""
    # Verification Scores (prominently displayed)
    composite_score: float = Field(default=0.0, ge=0.0, le=100.0, description="Overall verification score")
    verification_decision: str = Field(default="pending", description="AI decision: auto_approved, manual_review, rejected, auto_rejected")
    score_breakdown: List[VerificationScoreBreakdown] = Field(default=[], description="Individual layer scores")

    # Environmental Context
    threat_level: Optional[str] = Field(default=None, description="Threat level: warning, alert, watch, no_threat")
    weather_summary: Optional[str] = Field(default=None, description="Weather conditions summary")
    marine_conditions: Optional[str] = Field(default=None, description="Marine conditions summary")

    # Location Analysis
    geofence_valid: Optional[bool] = Field(default=None, description="Is location within coastal area")
    distance_to_coast_km: Optional[float] = Field(default=None, description="Distance to nearest coastline")

    # Image Analysis
    image_classification: Optional[str] = Field(default=None, description="Predicted hazard from image")
    image_confidence: Optional[float] = Field(default=None, description="Image classification confidence")
    image_matches_report: Optional[bool] = Field(default=None, description="Does image match reported hazard")

    # Text Analysis
    text_similarity_score: Optional[float] = Field(default=None, description="Text similarity to known hazards")
    predicted_hazard_from_text: Optional[str] = Field(default=None, description="Hazard type predicted from description")
    panic_level: Optional[float] = Field(default=None, description="Urgency/panic level in text (0-1)")
    is_spam: Optional[bool] = Field(default=False, description="Is description flagged as spam")

    # Reporter Credibility
    reporter_credibility_score: Optional[int] = Field(default=None, description="Reporter's credibility (0-100)")
    reporter_historical_accuracy: Optional[float] = Field(default=None, description="Reporter's past accuracy rate")
    reporter_total_reports: Optional[int] = Field(default=None, description="Total reports by this user")

    # Risk Assessment
    risk_level: Optional[str] = Field(default=None, description="Overall risk: low, medium, high, critical")
    urgency: Optional[str] = Field(default=None, description="Urgency level")
    requires_immediate_action: bool = Field(default=False, description="Flag for urgent response")

    # Recommendations
    recommendations: List[str] = Field(default=[], description="Safety and action recommendations")


class EnhancedHazardReportResponse(BaseModel):
    """Enhanced response with verification scores and insights prominently displayed"""
    # Core report data
    id: str = Field(..., alias="_id")
    report_id: str
    user_id: str
    user_name: Optional[str]
    hazard_type: str
    category: str
    description: Optional[str]
    image_url: str
    voice_note_url: Optional[str]
    location: Dict[str, Any]
    weather: Optional[Dict[str, Any]]

    # Verification Status & Scores (PROMINENT)
    verification_status: str
    verification_score: Optional[float] = Field(default=None, description="Overall verification score (0-100)")
    verification_decision: Optional[str] = Field(default=None, description="AI decision")
    verified_by: Optional[str] = None
    verified_by_name: Optional[str] = None
    verified_at: Optional[datetime] = None
    verification_notes: Optional[str] = None

    # Score Breakdown (for detailed view)
    score_breakdown: Optional[List[Dict[str, Any]]] = Field(default=None, description="Layer-by-layer score breakdown")

    # Insights Summary
    insights: Optional[ReportInsights] = Field(default=None, description="Aggregated insights")

    # Ticketing
    ticket_id: Optional[str] = None
    has_ticket: bool = False
    ticket_status: Optional[str] = None

    # Risk Assessment
    risk_level: Optional[str] = None
    urgency: Optional[str] = None
    requires_immediate_action: bool = False

    # Threat Classification
    threat_level: Optional[str] = None

    # Engagement
    likes: int = 0
    comments: int = 0
    views: int = 0

    # Timestamps
    created_at: datetime
    updated_at: datetime
    is_active: bool = True

    class Config:
        populate_by_name = True
        json_encoders = {
            datetime: lambda v: to_ist_isoformat(v)
        }

    @classmethod
    def from_report(cls, report: Dict[str, Any]) -> "EnhancedHazardReportResponse":
        """Create enhanced response from a hazard report document"""
        # Extract score breakdown from verification_result
        score_breakdown = None
        insights = None

        if report.get("verification_result"):
            vr = report["verification_result"]
            layer_results = vr.get("layer_results", [])

            score_breakdown = []
            for lr in layer_results:
                score_breakdown.append({
                    "layer_name": lr.get("layer_name", "unknown"),
                    "score": round(lr.get("score", 0) * 100, 1),  # Convert to percentage
                    "status": lr.get("status", "unknown"),
                    "weight": round(lr.get("weight", 0) * 100, 1),
                    "reasoning": lr.get("reasoning", "")
                })

            # Build insights
            insights = cls._build_insights(report, layer_results)

        # Get verification decision label
        verification_decision = None
        if report.get("verification_status"):
            status = report["verification_status"]
            if status == "verified":
                verification_decision = "auto_approved" if not report.get("verified_by") else "manually_approved"
            elif status == "auto_rejected":
                verification_decision = "auto_rejected"
            elif status == "rejected":
                verification_decision = "rejected"
            elif status == "needs_manual_review":
                verification_decision = "manual_review"
            else:
                verification_decision = status

        return cls(
            _id=str(report.get("_id", "")),
            report_id=report.get("report_id", ""),
            user_id=report.get("user_id", ""),
            user_name=report.get("user_name"),
            hazard_type=report.get("hazard_type", ""),
            category=report.get("category", ""),
            description=report.get("description"),
            image_url=report.get("image_url", ""),
            voice_note_url=report.get("voice_note_url"),
            location=report.get("location", {}),
            weather=report.get("weather"),
            verification_status=report.get("verification_status", "pending"),
            verification_score=report.get("verification_score"),
            verification_decision=verification_decision,
            verified_by=report.get("verified_by"),
            verified_by_name=report.get("verified_by_name"),
            verified_at=report.get("verified_at"),
            verification_notes=report.get("verification_notes"),
            score_breakdown=score_breakdown,
            insights=insights,
            ticket_id=report.get("ticket_id"),
            has_ticket=report.get("has_ticket", False),
            ticket_status=report.get("ticket_status"),
            risk_level=report.get("risk_level"),
            urgency=report.get("urgency"),
            requires_immediate_action=report.get("requires_immediate_action", False),
            threat_level=report.get("hazard_classification", {}).get("threat_level") if report.get("hazard_classification") else None,
            likes=report.get("likes", 0),
            comments=report.get("comments", 0),
            views=report.get("views", 0),
            created_at=report.get("created_at", datetime.now(timezone.utc)),
            updated_at=report.get("updated_at", datetime.now(timezone.utc)),
            is_active=report.get("is_active", True)
        )

    @staticmethod
    def _build_insights(report: Dict[str, Any], layer_results: List[Dict]) -> ReportInsights:
        """Build insights from report data and layer results"""
        score_breakdown = []

        # Extract data from each layer
        geofence_data = None
        weather_data = None
        text_data = None
        image_data = None
        reporter_data = None

        for lr in layer_results:
            layer_name = lr.get("layer_name", "")
            score_breakdown.append(VerificationScoreBreakdown(
                layer_name=layer_name,
                score=round(lr.get("score", 0) * 100, 1),
                status=lr.get("status", "unknown"),
                weight=round(lr.get("weight", 0), 2),
                reasoning=lr.get("reasoning", "")
            ))

            data = lr.get("data", {})
            if layer_name == "geofence":
                geofence_data = data
            elif layer_name == "weather":
                weather_data = data
            elif layer_name == "text":
                text_data = data
            elif layer_name == "image":
                image_data = data
            elif layer_name == "reporter":
                reporter_data = data

        # Build weather summary
        weather_summary = None
        if report.get("environmental_snapshot"):
            env = report["environmental_snapshot"]
            if env.get("weather"):
                w = env["weather"]
                weather_summary = f"{w.get('condition', 'Unknown')}, {w.get('temp_c', 'N/A')}°C, Wind: {w.get('wind_kph', 'N/A')} km/h"

        # Build marine summary
        marine_summary = None
        if report.get("environmental_snapshot"):
            env = report["environmental_snapshot"]
            if env.get("marine"):
                m = env["marine"]
                wave_height = m.get("sig_ht_mt", "N/A")
                swell = m.get("swell_ht_mt", "N/A")
                marine_summary = f"Wave Height: {wave_height}m, Swell: {swell}m"

        # Get hazard classification
        hazard_class = report.get("hazard_classification", {})
        threat_level = hazard_class.get("threat_level") if hazard_class else None
        recommendations = hazard_class.get("recommendations", []) if hazard_class else []

        # Determine risk level from score
        score = report.get("verification_score", 0) or 0
        if score >= 75:
            risk_level = "high" if threat_level in ["warning", "alert"] else "medium"
        elif score >= 40:
            risk_level = "medium"
        else:
            risk_level = "low"

        # Check urgency
        requires_immediate = threat_level == "warning" or report.get("requires_immediate_action", False)

        return ReportInsights(
            composite_score=score,
            verification_decision=report.get("verification_result", {}).get("decision", "pending"),
            score_breakdown=score_breakdown,
            threat_level=threat_level,
            weather_summary=weather_summary,
            marine_conditions=marine_summary,
            geofence_valid=geofence_data.get("is_inland") is False if geofence_data else None,
            distance_to_coast_km=geofence_data.get("distance_to_coast_km") if geofence_data else None,
            image_classification=image_data.get("predicted_class") if image_data else None,
            image_confidence=image_data.get("prediction_confidence") if image_data else None,
            image_matches_report=image_data.get("is_match") if image_data else None,
            text_similarity_score=text_data.get("similarity_score") if text_data else None,
            predicted_hazard_from_text=text_data.get("predicted_hazard_type") if text_data else None,
            panic_level=text_data.get("panic_level") if text_data else None,
            is_spam=text_data.get("is_spam", False) if text_data else False,
            reporter_credibility_score=reporter_data.get("credibility_score") if reporter_data else None,
            reporter_historical_accuracy=reporter_data.get("historical_accuracy") if reporter_data else None,
            reporter_total_reports=reporter_data.get("total_reports") if reporter_data else None,
            risk_level=risk_level,
            urgency=report.get("urgency", "normal"),
            requires_immediate_action=requires_immediate,
            recommendations=recommendations
        )


class HazardReportListResponse(BaseModel):
    """Response schema for list of hazard reports"""
    total: int
    page: int
    page_size: int
    reports: List[HazardReportResponse]
