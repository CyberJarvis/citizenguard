"""
MultiHazard Detection Models
Pydantic models for real-time coastal hazard monitoring
"""

from datetime import datetime, timezone
from typing import Optional, List, Dict, Any, Literal
from pydantic import BaseModel, Field
from enum import IntEnum, Enum


class AlertLevel(IntEnum):
    """Alert severity levels (1-5 scale)"""
    NORMAL = 1
    ADVISORY = 2
    WATCH = 3
    WARNING = 4
    CRITICAL = 5


class HazardType(str, Enum):
    """Types of coastal hazards detected"""
    TSUNAMI = "tsunami"
    CYCLONE = "cyclone"
    HIGH_WAVES = "high_waves"
    COASTAL_FLOOD = "coastal_flood"
    RIP_CURRENTS = "rip_currents"


class DetectionMethod(str, Enum):
    """Method used for hazard detection"""
    RULE_BASED = "rule_based"
    ML_MODEL = "ml_model"


# Core Data Models

class Coordinates(BaseModel):
    """Geographic coordinates"""
    lat: float = Field(..., ge=-90, le=90, description="Latitude")
    lon: float = Field(..., ge=-180, le=180, description="Longitude")


class WeatherParams(BaseModel):
    """Weather data snapshot"""
    temperature_c: Optional[float] = Field(default=None, description="Temperature in Celsius")
    wind_kph: Optional[float] = Field(default=None, description="Wind speed in km/h")
    wind_dir: Optional[str] = Field(default=None, description="Wind direction")
    gust_kph: Optional[float] = Field(default=None, description="Wind gust speed")
    pressure_mb: Optional[float] = Field(default=None, description="Atmospheric pressure in mb")
    humidity: Optional[int] = Field(default=None, description="Humidity percentage")
    precip_mm: Optional[float] = Field(default=None, description="Precipitation in mm")
    visibility_km: Optional[float] = Field(default=None, description="Visibility in km")
    cloud: Optional[int] = Field(default=None, description="Cloud cover percentage")
    condition: Optional[str] = Field(default=None, description="Weather condition text")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class MarineParams(BaseModel):
    """Marine/ocean data snapshot"""
    sig_ht_mt: Optional[float] = Field(default=None, description="Significant wave height in meters")
    swell_ht_mt: Optional[float] = Field(default=None, description="Swell height in meters")
    swell_period_secs: Optional[float] = Field(default=None, description="Swell period in seconds")
    swell_dir: Optional[str] = Field(default=None, description="Swell direction")
    tide_height_mt: Optional[float] = Field(default=None, description="Tide height in meters")
    water_temp_c: Optional[float] = Field(default=None, description="Water temperature in Celsius")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class EarthquakeData(BaseModel):
    """Earthquake event data"""
    earthquake_id: str = Field(..., description="Unique earthquake ID")
    magnitude: float = Field(..., description="Earthquake magnitude")
    depth_km: float = Field(..., description="Depth in kilometers")
    coordinates: Coordinates = Field(..., description="Epicenter coordinates")
    location_description: str = Field(..., description="Location description")
    timestamp: datetime = Field(..., description="Event timestamp")
    is_oceanic: bool = Field(default=False, description="Whether earthquake is oceanic")
    distance_to_coast_km: Optional[float] = Field(default=None, description="Distance to nearest coast")


class HazardAlert(BaseModel):
    """Individual hazard alert"""
    alert_id: str = Field(..., description="Unique alert ID")
    hazard_type: HazardType = Field(..., description="Type of hazard")
    alert_level: AlertLevel = Field(..., description="Severity level (1-5)")
    location_id: str = Field(..., description="Monitoring location ID")
    location_name: str = Field(..., description="Location name")
    coordinates: Coordinates = Field(..., description="Alert coordinates")
    detected_at: datetime = Field(..., description="Detection timestamp")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Detection parameters")
    detection_method: DetectionMethod = Field(..., description="Detection method used")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="Detection confidence")
    source_earthquake_id: Optional[str] = Field(default=None, description="Source earthquake ID (for tsunami)")
    weather_snapshot: Optional[WeatherParams] = Field(default=None, description="Weather at detection time")
    marine_snapshot: Optional[MarineParams] = Field(default=None, description="Marine data at detection time")
    recommendations: List[str] = Field(default_factory=list, description="Action recommendations")
    affected_population: Optional[int] = Field(default=None, description="Estimated affected population")
    is_active: bool = Field(default=True, description="Whether alert is still active")
    expires_at: Optional[datetime] = Field(default=None, description="Alert expiration time")


class MonitoredLocation(BaseModel):
    """Monitored coastal location"""
    location_id: str = Field(..., description="Unique location ID")
    name: str = Field(..., description="Location name")
    country: str = Field(..., description="Country")
    coordinates: Coordinates = Field(..., description="Location coordinates")
    region: str = Field(..., description="Ocean/sea region")
    coastline_type: str = Field(..., description="Coastline orientation")
    population: int = Field(default=0, description="Population at risk")
    risk_profile: Literal["low", "medium", "high", "critical"] = Field(default="medium")


class LocationStatus(BaseModel):
    """Current status of a monitored location"""
    location_id: str = Field(..., description="Location ID")
    location_name: str = Field(..., description="Location name")
    country: str = Field(default="India", description="Country")
    coordinates: Coordinates = Field(..., description="Location coordinates")
    max_alert_level: AlertLevel = Field(default=AlertLevel.NORMAL, description="Maximum alert level")
    active_hazards: List[HazardAlert] = Field(default_factory=list, description="Active hazard alerts")
    weather: Optional[WeatherParams] = Field(default=None, description="Current weather")
    marine: Optional[MarineParams] = Field(default=None, description="Current marine conditions")
    last_updated: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    recommendations: List[str] = Field(default_factory=list, description="Current recommendations")
    weather_score: Optional[int] = Field(default=None, ge=0, le=100, description="Weather hazard score")


class MultiHazardSummary(BaseModel):
    """Global monitoring summary"""
    total_locations: int = Field(..., description="Total monitored locations")
    active_alerts_count: int = Field(..., description="Total active alerts")
    critical_alerts: int = Field(default=0, description="Critical level alerts")
    warning_alerts: int = Field(default=0, description="Warning level alerts")
    watch_alerts: int = Field(default=0, description="Watch level alerts")
    tsunami_alerts: int = Field(default=0, description="Tsunami alerts")
    cyclone_alerts: int = Field(default=0, description="Cyclone alerts")
    high_waves_alerts: int = Field(default=0, description="High waves alerts")
    coastal_flood_alerts: int = Field(default=0, description="Coastal flood alerts")
    rip_current_alerts: int = Field(default=0, description="Rip current alerts")
    recent_earthquakes: int = Field(default=0, description="Recent significant earthquakes")
    last_detection_cycle: datetime = Field(..., description="Last detection cycle time")
    next_detection_cycle: datetime = Field(..., description="Next scheduled detection")
    is_monitoring_active: bool = Field(..., description="Whether monitoring is active")


class MultiHazardResponse(BaseModel):
    """Full multi-hazard monitoring response"""
    locations: Dict[str, LocationStatus] = Field(..., description="Status by location")
    summary: MultiHazardSummary = Field(..., description="Global summary")
    recent_earthquakes: List[EarthquakeData] = Field(default_factory=list, description="Recent earthquakes")
    global_alerts: List[HazardAlert] = Field(default_factory=list, description="All active alerts")


# API Response Models

class MultiHazardHealthResponse(BaseModel):
    """Health check response"""
    status: str = Field(..., description="Service status")
    is_monitoring: bool = Field(..., description="Whether monitoring is active")
    locations_count: int = Field(..., description="Number of monitored locations")
    last_cycle: Optional[datetime] = Field(default=None, description="Last detection cycle")
    active_alerts: int = Field(..., description="Number of active alerts")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class PublicAlertResponse(BaseModel):
    """Public-facing alert response (simplified)"""
    location_id: str
    location_name: str
    hazard_type: str
    alert_level: int
    alert_level_name: str
    message: str
    recommendations: List[str]
    detected_at: datetime
    is_active: bool


class PublicStatusResponse(BaseModel):
    """Public-facing status summary"""
    total_locations: int
    locations_at_risk: int
    active_alerts: List[PublicAlertResponse]
    highest_alert_level: int
    highest_alert_level_name: str
    last_updated: datetime
    message: str


# Request Models

class RefreshRequest(BaseModel):
    """Request to force detection cycle"""
    location_ids: Optional[List[str]] = Field(default=None, description="Specific locations (None = all)")


class MonitoringControlRequest(BaseModel):
    """Request to control monitoring"""
    interval_seconds: Optional[int] = Field(default=300, ge=60, le=3600, description="Monitoring interval")


# Detection Result Models

class DetectionCycleResult(BaseModel):
    """Result of a detection cycle"""
    success: bool = Field(..., description="Whether cycle completed successfully")
    alerts_generated: int = Field(..., description="Number of new alerts")
    locations_processed: int = Field(..., description="Locations processed")
    processing_time_ms: float = Field(..., description="Processing time in ms")
    errors: List[str] = Field(default_factory=list, description="Any errors encountered")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# Threshold Configuration Models

class HazardThresholds(BaseModel):
    """Configuration for hazard detection thresholds"""
    tsunami: Dict[str, Any] = Field(
        default={
            "earthquake_magnitude": 6.5,
            "earthquake_depth_km": 70,
            "oceanic_only": True
        }
    )
    cyclone: Dict[str, Any] = Field(
        default={
            "wind_kph": 90,
            "pressure_mb": 980
        }
    )
    high_waves: Dict[str, Any] = Field(
        default={
            "sig_ht_mt": 4.0,
            "swell_ht_mt": 3.0
        }
    )
    coastal_flood: Dict[str, Any] = Field(
        default={
            "tide_height_mt": 3.5,
            "precip_mm": 20
        }
    )
    rip_currents: Dict[str, Any] = Field(
        default={
            "swell_period_secs": 14,
            "sig_ht_mt": 2.5
        }
    )
