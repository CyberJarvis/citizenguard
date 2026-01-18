"""
Monitoring location and hazard detection models for ML-powered real-time monitoring.
"""
from datetime import datetime
from typing import Optional, Dict, List
from pydantic import BaseModel, Field
from enum import Enum


class AlertLevel(int, Enum):
    """Alert levels for hazards (1=Normal, 5=Critical)"""
    NORMAL = 1
    LOW = 2
    WARNING = 3
    HIGH = 4
    CRITICAL = 5


class AlertStatus(str, Enum):
    """Overall status based on max alert level"""
    NORMAL = "NORMAL"
    LOW = "LOW"
    WARNING = "WARNING"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class HazardType(str, Enum):
    """Types of hazards monitored by ML model"""
    TSUNAMI = "tsunami"
    CYCLONE = "cyclone"
    HIGH_WAVES = "high_waves"
    FLOOD = "flood"


class CycloneCategory(str, Enum):
    """Cyclone categories"""
    DEPRESSION = "DEPRESSION"
    STORM = "STORM"
    SEVERE_STORM = "SEVERE_STORM"
    CYCLONE = "CYCLONE"
    SEVERE_CYCLONE = "SEVERE_CYCLONE"


class BeachFlag(str, Enum):
    """Beach safety flag colors"""
    GREEN = "GREEN"
    YELLOW = "YELLOW"
    RED = "RED"
    DOUBLE_RED = "DOUBLE_RED"


# Pydantic models for hazard details
class TsunamiHazard(BaseModel):
    """Tsunami hazard details"""
    alert_level: AlertLevel
    probability: float = Field(..., ge=0.0, le=1.0, description="Probability (0-1)")
    estimated_arrival_minutes: Optional[int] = None
    wave_height_meters: Optional[float] = None


class CycloneHazard(BaseModel):
    """Cyclone hazard details"""
    alert_level: AlertLevel
    category: CycloneCategory
    wind_speed_kmh: Optional[float] = None
    distance_km: Optional[float] = None
    direction: Optional[str] = None


class HighWavesHazard(BaseModel):
    """High waves hazard details"""
    alert_level: AlertLevel
    beach_flag: BeachFlag
    wave_height_meters: float
    wind_speed_kmh: float


class FloodHazard(BaseModel):
    """Flood hazard details"""
    alert_level: AlertLevel
    flood_score: int = Field(..., ge=0, le=100, description="Flood risk score (0-100)")
    rainfall_mm: Optional[float] = None
    affected_areas: Optional[List[str]] = None


class CurrentHazards(BaseModel):
    """All current hazards for a location"""
    tsunami: Optional[TsunamiHazard] = None
    cyclone: Optional[CycloneHazard] = None
    high_waves: Optional[HighWavesHazard] = None
    flood: Optional[FloodHazard] = None


class Coordinates(BaseModel):
    """Geographic coordinates"""
    lat: float = Field(..., ge=-90, le=90)
    lon: float = Field(..., ge=-180, le=180)


class WeatherData(BaseModel):
    """Current weather conditions"""
    temperature_c: Optional[float] = None
    feels_like_c: Optional[float] = None
    condition: Optional[str] = None
    wind_kph: Optional[float] = None
    wind_dir: Optional[str] = None
    pressure_mb: Optional[float] = None
    humidity: Optional[int] = None
    visibility_km: Optional[float] = None
    uv: Optional[float] = None
    cloud: Optional[int] = None
    timestamp: Optional[str] = None


class MarineData(BaseModel):
    """Marine and tide conditions"""
    wave_height_m: Optional[float] = None
    wave_direction_degree: Optional[int] = None
    swell_height_m: Optional[float] = None
    swell_period_secs: Optional[float] = None
    water_temp_c: Optional[float] = None
    tide_data: Optional[Dict] = None
    timestamp: Optional[str] = None


class MonitoringLocation(BaseModel):
    """A monitored location with current hazard data"""
    location_id: str
    name: str
    country: str
    coordinates: Coordinates
    population: Optional[int] = None
    current_hazards: CurrentHazards
    max_alert: AlertLevel
    status: AlertStatus
    recommendations: List[str] = []
    weather: Optional[WeatherData] = None
    marine: Optional[MarineData] = None
    last_updated: datetime


class EarthquakeData(BaseModel):
    """Recent earthquake data"""
    earthquake_id: str
    magnitude: float
    depth_km: float
    coordinates: Coordinates
    location_description: str
    timestamp: datetime
    distance_from_coast_km: Optional[float] = None


class MonitoringSummary(BaseModel):
    """Summary statistics for all monitored locations"""
    total_locations: int
    critical_alerts: int
    high_alerts: int
    warning_alerts: int
    low_alerts: int
    normal_alerts: int
    active_tsunamis: int
    active_cyclones: int
    active_high_waves: int
    active_floods: int
    last_updated: datetime


class MonitoringResponse(BaseModel):
    """Complete monitoring data response"""
    locations: Dict[str, MonitoringLocation]
    summary: MonitoringSummary
    recent_earthquakes: List[EarthquakeData] = []


# Database document schemas (for MongoDB storage)
class MonitoringLocationDocument(BaseModel):
    """MongoDB document for monitoring location"""
    location_id: str
    name: str
    country: str
    latitude: float
    longitude: float
    population: Optional[int] = None
    is_active: bool = True
    created_at: datetime
    updated_at: datetime


class HazardDetectionDocument(BaseModel):
    """MongoDB document for hazard detection results"""
    detection_id: str
    location_id: str
    timestamp: datetime
    hazards: Dict  # Stores CurrentHazards as dict
    max_alert: int
    status: str
    recommendations: List[str]
    model_version: str
    confidence_score: float
