"""
Predictive Alert Service
Rule-based alert engine using IMD standards for maritime safety
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from math import radians, sin, cos, sqrt, atan2
from pydantic import BaseModel
from enum import Enum

from app.database import MongoDB

logger = logging.getLogger(__name__)


class AlertSeverity(str, Enum):
    """Alert severity levels based on IMD standards"""
    INFO = "info"
    ADVISORY = "advisory"
    WATCH = "watch"
    WARNING = "warning"
    CRITICAL = "critical"


class AlertType(str, Enum):
    """Types of predictive alerts"""
    HIGH_WAVE = "high_wave"
    HIGH_WIND = "high_wind"
    CYCLONE_WATCH = "cyclone_watch"
    STORM_SURGE = "storm_surge"
    TEMPERATURE_DROP = "temperature_drop"
    VISIBILITY_LOW = "visibility_low"
    FISHING_BAN = "fishing_ban"


class PredictiveAlert(BaseModel):
    """Predictive alert data model"""
    alert_id: str
    alert_type: AlertType
    severity: AlertSeverity
    title: str
    message: str
    location_name: Optional[str] = None
    latitude: float
    longitude: float
    radius_km: float
    current_value: float
    threshold_value: float
    unit: str
    source: str
    issued_at: datetime
    valid_from: datetime
    valid_until: datetime
    affected_areas: List[str] = []
    recommendations: List[str] = []
    metadata: Dict[str, Any] = {}


class IMDThresholds:
    """
    IMD (India Meteorological Department) Standard Thresholds
    Based on official IMD marine weather warning criteria
    """

    # Wave height thresholds (meters)
    WAVE_HEIGHT = {
        "small_craft_advisory": 2.0,  # Advisory for small boats
        "fishing_warning": 2.5,       # Warning for fishing vessels
        "high_wave_warning": 3.5,     # High wave warning
        "very_high_wave": 6.0,        # Dangerous conditions
    }

    # Wind speed thresholds (knots)
    WIND_SPEED = {
        "small_craft_advisory": 25,   # Advisory
        "gale_warning": 35,           # Gale force
        "storm_warning": 48,          # Storm force
        "hurricane_force": 64,        # Hurricane force
    }

    # Cyclone proximity (km)
    CYCLONE_DISTANCE = {
        "cyclone_watch": 500,         # Watch area
        "cyclone_warning": 300,       # Warning area
        "cyclone_alert": 150,         # Alert area
        "immediate_danger": 75,       # Immediate danger zone
    }

    # Storm surge (meters)
    STORM_SURGE = {
        "advisory": 0.5,
        "warning": 1.0,
        "danger": 1.5,
        "extreme": 2.5,
    }

    # Visibility (km)
    VISIBILITY = {
        "poor": 4.0,
        "very_poor": 1.0,
        "fog": 0.5,
    }

    # Sea surface temperature drop (celsius per hour)
    TEMPERATURE_DROP = {
        "rapid_cooling": 2.0,
        "significant_drop": 5.0,
    }


class PredictiveAlertService:
    """
    Service for generating predictive alerts based on weather and marine conditions
    """

    def __init__(self):
        self.thresholds = IMDThresholds()
        self._initialized = False
        self._alert_counter = 0

    async def initialize(self):
        """Initialize the service"""
        logger.info("Initializing Predictive Alert Service...")

        try:
            # Create database indexes
            db = MongoDB.get_database()

            # Index for predictive alerts
            await db.predictive_alerts.create_index([("alert_id", 1)], unique=True)
            await db.predictive_alerts.create_index([("issued_at", -1)])
            await db.predictive_alerts.create_index([("valid_until", 1)])
            await db.predictive_alerts.create_index([("alert_type", 1)])
            await db.predictive_alerts.create_index([("severity", 1)])
            await db.predictive_alerts.create_index([
                ("location", "2dsphere")
            ])

            # Index for user alert subscriptions
            await db.alert_subscriptions.create_index([("user_id", 1)], unique=True)
            await db.alert_subscriptions.create_index([("location", "2dsphere")])
            await db.alert_subscriptions.create_index([("enabled", 1)])

            self._initialized = True
            logger.info("[OK] Predictive Alert Service initialized")

        except Exception as e:
            logger.error(f"[ERROR] Failed to initialize Predictive Alert Service: {e}")
            raise

    def _generate_alert_id(self) -> str:
        """Generate unique alert ID"""
        self._alert_counter += 1
        timestamp = datetime.utcnow().strftime("%Y%m%d%H%M")
        return f"PA-{timestamp}-{self._alert_counter:04d}"

    def _calculate_distance(
        self, lat1: float, lon1: float, lat2: float, lon2: float
    ) -> float:
        """Calculate distance between two points in km using Haversine formula"""
        R = 6371  # Earth's radius in km

        lat1_rad = radians(lat1)
        lat2_rad = radians(lat2)
        delta_lat = radians(lat2 - lat1)
        delta_lon = radians(lon2 - lon1)

        a = sin(delta_lat / 2) ** 2 + cos(lat1_rad) * cos(lat2_rad) * sin(delta_lon / 2) ** 2
        c = 2 * atan2(sqrt(a), sqrt(1 - a))

        return R * c

    def _get_severity_for_wave(self, wave_height: float) -> AlertSeverity:
        """Determine severity based on wave height"""
        if wave_height >= self.thresholds.WAVE_HEIGHT["very_high_wave"]:
            return AlertSeverity.CRITICAL
        elif wave_height >= self.thresholds.WAVE_HEIGHT["high_wave_warning"]:
            return AlertSeverity.WARNING
        elif wave_height >= self.thresholds.WAVE_HEIGHT["fishing_warning"]:
            return AlertSeverity.WATCH
        elif wave_height >= self.thresholds.WAVE_HEIGHT["small_craft_advisory"]:
            return AlertSeverity.ADVISORY
        return AlertSeverity.INFO

    def _get_severity_for_wind(self, wind_speed: float) -> AlertSeverity:
        """Determine severity based on wind speed (knots)"""
        if wind_speed >= self.thresholds.WIND_SPEED["hurricane_force"]:
            return AlertSeverity.CRITICAL
        elif wind_speed >= self.thresholds.WIND_SPEED["storm_warning"]:
            return AlertSeverity.WARNING
        elif wind_speed >= self.thresholds.WIND_SPEED["gale_warning"]:
            return AlertSeverity.WATCH
        elif wind_speed >= self.thresholds.WIND_SPEED["small_craft_advisory"]:
            return AlertSeverity.ADVISORY
        return AlertSeverity.INFO

    def _get_recommendations_for_wave(self, severity: AlertSeverity) -> List[str]:
        """Get safety recommendations based on wave severity"""
        base = ["Monitor weather updates regularly"]

        if severity == AlertSeverity.CRITICAL:
            return [
                "All vessels should return to port immediately",
                "Avoid coastal areas",
                "Secure all loose items on shore",
                "Be prepared for emergency evacuation",
            ] + base
        elif severity == AlertSeverity.WARNING:
            return [
                "Small boats should not venture out to sea",
                "Fishing activities should be suspended",
                "Stay away from beaches and coastal structures",
            ] + base
        elif severity == AlertSeverity.WATCH:
            return [
                "Small craft advisory in effect",
                "Exercise caution if at sea",
                "Keep communication devices charged",
            ] + base
        elif severity == AlertSeverity.ADVISORY:
            return [
                "Small boats should exercise caution",
                "Check tide timings before venturing out",
            ] + base
        return base

    def _get_recommendations_for_wind(self, severity: AlertSeverity) -> List[str]:
        """Get safety recommendations based on wind severity"""
        base = ["Secure loose objects", "Monitor weather updates"]

        if severity == AlertSeverity.CRITICAL:
            return [
                "Seek immediate shelter",
                "All maritime activities suspended",
                "Stay indoors away from windows",
                "Be prepared for power outages",
            ] + base
        elif severity == AlertSeverity.WARNING:
            return [
                "Storm force winds expected",
                "All vessels should return to port",
                "Avoid open areas",
            ] + base
        elif severity == AlertSeverity.WATCH:
            return [
                "Gale force winds possible",
                "Small boats should stay in port",
                "Secure outdoor furniture",
            ] + base
        elif severity == AlertSeverity.ADVISORY:
            return [
                "Strong winds expected",
                "Exercise caution on water",
            ] + base
        return base

    async def evaluate_wave_conditions(
        self,
        latitude: float,
        longitude: float,
        wave_height: float,
        location_name: Optional[str] = None,
    ) -> Optional[PredictiveAlert]:
        """
        Evaluate wave conditions and generate alert if thresholds exceeded

        Args:
            latitude: Location latitude
            longitude: Location longitude
            wave_height: Current or forecast wave height in meters
            location_name: Optional name for the location
        """
        min_threshold = self.thresholds.WAVE_HEIGHT["small_craft_advisory"]

        if wave_height < min_threshold:
            return None

        severity = self._get_severity_for_wave(wave_height)
        recommendations = self._get_recommendations_for_wave(severity)

        # Determine which threshold was crossed
        threshold_name = "small_craft_advisory"
        threshold_value = min_threshold
        for name, value in sorted(
            self.thresholds.WAVE_HEIGHT.items(),
            key=lambda x: x[1],
            reverse=True
        ):
            if wave_height >= value:
                threshold_name = name
                threshold_value = value
                break

        now = datetime.utcnow()

        alert = PredictiveAlert(
            alert_id=self._generate_alert_id(),
            alert_type=AlertType.HIGH_WAVE,
            severity=severity,
            title=f"High Wave {severity.value.title()}: {wave_height}m",
            message=f"Wave height of {wave_height}m exceeds the {threshold_name.replace('_', ' ')} threshold of {threshold_value}m",
            location_name=location_name,
            latitude=latitude,
            longitude=longitude,
            radius_km=50,  # Alert radius
            current_value=wave_height,
            threshold_value=threshold_value,
            unit="meters",
            source="IMD Standards",
            issued_at=now,
            valid_from=now,
            valid_until=now + timedelta(hours=6),
            recommendations=recommendations,
            metadata={
                "threshold_name": threshold_name,
            }
        )

        return alert

    async def evaluate_wind_conditions(
        self,
        latitude: float,
        longitude: float,
        wind_speed: float,
        location_name: Optional[str] = None,
    ) -> Optional[PredictiveAlert]:
        """
        Evaluate wind conditions and generate alert if thresholds exceeded

        Args:
            latitude: Location latitude
            longitude: Location longitude
            wind_speed: Current or forecast wind speed in knots
            location_name: Optional name for the location
        """
        min_threshold = self.thresholds.WIND_SPEED["small_craft_advisory"]

        if wind_speed < min_threshold:
            return None

        severity = self._get_severity_for_wind(wind_speed)
        recommendations = self._get_recommendations_for_wind(severity)

        # Determine which threshold was crossed
        threshold_name = "small_craft_advisory"
        threshold_value = min_threshold
        for name, value in sorted(
            self.thresholds.WIND_SPEED.items(),
            key=lambda x: x[1],
            reverse=True
        ):
            if wind_speed >= value:
                threshold_name = name
                threshold_value = value
                break

        now = datetime.utcnow()

        alert = PredictiveAlert(
            alert_id=self._generate_alert_id(),
            alert_type=AlertType.HIGH_WIND,
            severity=severity,
            title=f"High Wind {severity.value.title()}: {wind_speed} knots",
            message=f"Wind speed of {wind_speed} knots exceeds the {threshold_name.replace('_', ' ')} threshold of {threshold_value} knots",
            location_name=location_name,
            latitude=latitude,
            longitude=longitude,
            radius_km=100,  # Alert radius
            current_value=wind_speed,
            threshold_value=threshold_value,
            unit="knots",
            source="IMD Standards",
            issued_at=now,
            valid_from=now,
            valid_until=now + timedelta(hours=6),
            recommendations=recommendations,
            metadata={
                "threshold_name": threshold_name,
            }
        )

        return alert

    async def evaluate_cyclone_proximity(
        self,
        user_latitude: float,
        user_longitude: float,
        cyclone_latitude: float,
        cyclone_longitude: float,
        cyclone_name: str,
        cyclone_category: str = "Unknown",
    ) -> Optional[PredictiveAlert]:
        """
        Evaluate cyclone proximity and generate alert if within watch distance

        Args:
            user_latitude: User's location latitude
            user_longitude: User's location longitude
            cyclone_latitude: Cyclone center latitude
            cyclone_longitude: Cyclone center longitude
            cyclone_name: Name of the cyclone
            cyclone_category: Category/intensity of the cyclone
        """
        distance = self._calculate_distance(
            user_latitude, user_longitude,
            cyclone_latitude, cyclone_longitude
        )

        # Check if within any threshold
        if distance > self.thresholds.CYCLONE_DISTANCE["cyclone_watch"]:
            return None

        # Determine severity based on distance
        if distance <= self.thresholds.CYCLONE_DISTANCE["immediate_danger"]:
            severity = AlertSeverity.CRITICAL
            threshold_name = "immediate_danger"
            threshold_value = self.thresholds.CYCLONE_DISTANCE["immediate_danger"]
        elif distance <= self.thresholds.CYCLONE_DISTANCE["cyclone_alert"]:
            severity = AlertSeverity.WARNING
            threshold_name = "cyclone_alert"
            threshold_value = self.thresholds.CYCLONE_DISTANCE["cyclone_alert"]
        elif distance <= self.thresholds.CYCLONE_DISTANCE["cyclone_warning"]:
            severity = AlertSeverity.WATCH
            threshold_name = "cyclone_warning"
            threshold_value = self.thresholds.CYCLONE_DISTANCE["cyclone_warning"]
        else:
            severity = AlertSeverity.ADVISORY
            threshold_name = "cyclone_watch"
            threshold_value = self.thresholds.CYCLONE_DISTANCE["cyclone_watch"]

        recommendations = [
            "Monitor official weather bulletins",
            "Prepare emergency supplies",
            "Know your evacuation route",
            "Secure important documents",
        ]

        if severity in [AlertSeverity.CRITICAL, AlertSeverity.WARNING]:
            recommendations = [
                "Follow evacuation orders immediately",
                "Move to designated shelters",
                "Stay away from coastal areas",
                "Keep emergency kit ready",
            ] + recommendations

        now = datetime.utcnow()

        alert = PredictiveAlert(
            alert_id=self._generate_alert_id(),
            alert_type=AlertType.CYCLONE_WATCH,
            severity=severity,
            title=f"Cyclone {cyclone_name} - {severity.value.title()}",
            message=f"Cyclone {cyclone_name} ({cyclone_category}) is {distance:.0f}km away. This is within the {threshold_name.replace('_', ' ')} zone ({threshold_value}km)",
            location_name=None,  # User's location
            latitude=user_latitude,
            longitude=user_longitude,
            radius_km=threshold_value,
            current_value=distance,
            threshold_value=threshold_value,
            unit="km",
            source="IMD Cyclone Tracking",
            issued_at=now,
            valid_from=now,
            valid_until=now + timedelta(hours=12),
            recommendations=recommendations,
            metadata={
                "cyclone_name": cyclone_name,
                "cyclone_category": cyclone_category,
                "cyclone_lat": cyclone_latitude,
                "cyclone_lon": cyclone_longitude,
                "distance_km": distance,
                "threshold_name": threshold_name,
            }
        )

        return alert

    async def evaluate_storm_surge(
        self,
        latitude: float,
        longitude: float,
        surge_height: float,
        location_name: Optional[str] = None,
    ) -> Optional[PredictiveAlert]:
        """
        Evaluate storm surge conditions

        Args:
            latitude: Location latitude
            longitude: Location longitude
            surge_height: Expected storm surge height in meters
            location_name: Optional name for the location
        """
        min_threshold = self.thresholds.STORM_SURGE["advisory"]

        if surge_height < min_threshold:
            return None

        # Determine severity
        if surge_height >= self.thresholds.STORM_SURGE["extreme"]:
            severity = AlertSeverity.CRITICAL
            threshold_name = "extreme"
            threshold_value = self.thresholds.STORM_SURGE["extreme"]
        elif surge_height >= self.thresholds.STORM_SURGE["danger"]:
            severity = AlertSeverity.WARNING
            threshold_name = "danger"
            threshold_value = self.thresholds.STORM_SURGE["danger"]
        elif surge_height >= self.thresholds.STORM_SURGE["warning"]:
            severity = AlertSeverity.WATCH
            threshold_name = "warning"
            threshold_value = self.thresholds.STORM_SURGE["warning"]
        else:
            severity = AlertSeverity.ADVISORY
            threshold_name = "advisory"
            threshold_value = self.thresholds.STORM_SURGE["advisory"]

        recommendations = [
            "Move to higher ground if in low-lying areas",
            "Avoid beaches and coastal roads",
            "Do not walk or drive through flood waters",
            "Monitor tide timings",
        ]

        if severity in [AlertSeverity.CRITICAL, AlertSeverity.WARNING]:
            recommendations = [
                "Evacuate low-lying coastal areas immediately",
                "Seek shelter on higher floors or elevated areas",
            ] + recommendations

        now = datetime.utcnow()

        alert = PredictiveAlert(
            alert_id=self._generate_alert_id(),
            alert_type=AlertType.STORM_SURGE,
            severity=severity,
            title=f"Storm Surge {severity.value.title()}: {surge_height}m",
            message=f"Storm surge of {surge_height}m expected, exceeding {threshold_name} threshold of {threshold_value}m",
            location_name=location_name,
            latitude=latitude,
            longitude=longitude,
            radius_km=30,
            current_value=surge_height,
            threshold_value=threshold_value,
            unit="meters",
            source="IMD Storm Surge Model",
            issued_at=now,
            valid_from=now,
            valid_until=now + timedelta(hours=24),
            recommendations=recommendations,
            metadata={
                "threshold_name": threshold_name,
            }
        )

        return alert

    async def evaluate_all_conditions(
        self,
        latitude: float,
        longitude: float,
        weather_data: Dict[str, Any],
        marine_data: Optional[Dict[str, Any]] = None,
        cyclone_data: Optional[Dict[str, Any]] = None,
    ) -> List[PredictiveAlert]:
        """
        Evaluate all conditions and return list of active alerts

        Args:
            latitude: Location latitude
            longitude: Location longitude
            weather_data: Weather data containing wind, visibility etc.
            marine_data: Marine data containing wave height, SST etc.
            cyclone_data: Active cyclone data if any
        """
        alerts = []

        # Evaluate wave conditions
        if marine_data and "wave_height" in marine_data:
            wave_alert = await self.evaluate_wave_conditions(
                latitude, longitude,
                marine_data["wave_height"],
                marine_data.get("location_name")
            )
            if wave_alert:
                alerts.append(wave_alert)

        # Evaluate wind conditions
        if weather_data and "wind_speed_kts" in weather_data:
            wind_alert = await self.evaluate_wind_conditions(
                latitude, longitude,
                weather_data["wind_speed_kts"],
                weather_data.get("location_name")
            )
            if wind_alert:
                alerts.append(wind_alert)

        # Evaluate storm surge
        if marine_data and "storm_surge" in marine_data:
            surge_alert = await self.evaluate_storm_surge(
                latitude, longitude,
                marine_data["storm_surge"],
                marine_data.get("location_name")
            )
            if surge_alert:
                alerts.append(surge_alert)

        # Evaluate cyclone proximity
        if cyclone_data:
            cyclone_alert = await self.evaluate_cyclone_proximity(
                latitude, longitude,
                cyclone_data["latitude"],
                cyclone_data["longitude"],
                cyclone_data.get("name", "Unknown"),
                cyclone_data.get("category", "Unknown")
            )
            if cyclone_alert:
                alerts.append(cyclone_alert)

        return alerts

    async def save_alert(self, alert: PredictiveAlert) -> bool:
        """Save alert to database"""
        try:
            db = MongoDB.get_database()

            alert_doc = alert.model_dump()
            alert_doc["location"] = {
                "type": "Point",
                "coordinates": [alert.longitude, alert.latitude]
            }

            await db.predictive_alerts.insert_one(alert_doc)
            return True
        except Exception as e:
            logger.error(f"Failed to save alert: {e}")
            return False

    async def get_active_alerts(
        self,
        latitude: Optional[float] = None,
        longitude: Optional[float] = None,
        radius_km: float = 100,
        alert_types: Optional[List[AlertType]] = None,
        min_severity: Optional[AlertSeverity] = None,
    ) -> List[Dict]:
        """
        Get active alerts, optionally filtered by location and type

        Args:
            latitude: Optional center latitude for location filter
            longitude: Optional center longitude for location filter
            radius_km: Radius in km for location filter
            alert_types: Filter by alert types
            min_severity: Minimum severity to include
        """
        try:
            db = MongoDB.get_database()
            now = datetime.utcnow()

            query = {
                "valid_until": {"$gte": now}
            }

            # Location filter
            if latitude is not None and longitude is not None:
                query["location"] = {
                    "$geoWithin": {
                        "$centerSphere": [
                            [longitude, latitude],
                            radius_km / 6371  # Convert km to radians
                        ]
                    }
                }

            # Type filter
            if alert_types:
                query["alert_type"] = {"$in": [t.value for t in alert_types]}

            # Severity filter
            if min_severity:
                severity_order = [
                    AlertSeverity.INFO.value,
                    AlertSeverity.ADVISORY.value,
                    AlertSeverity.WATCH.value,
                    AlertSeverity.WARNING.value,
                    AlertSeverity.CRITICAL.value,
                ]
                min_idx = severity_order.index(min_severity.value)
                query["severity"] = {"$in": severity_order[min_idx:]}

            cursor = db.predictive_alerts.find(query).sort("issued_at", -1)
            alerts = await cursor.to_list(length=100)

            # Clean up MongoDB-specific fields
            for alert in alerts:
                alert.pop("_id", None)
                alert.pop("location", None)

            return alerts
        except Exception as e:
            logger.error(f"Failed to get active alerts: {e}")
            return []

    async def get_alerts_for_user(self, user_id: str) -> List[Dict]:
        """
        Get alerts relevant to a user based on their subscription
        """
        try:
            db = MongoDB.get_database()

            # Get user's subscription
            subscription = await db.alert_subscriptions.find_one({"user_id": user_id})

            if not subscription or not subscription.get("enabled", True):
                return []

            # Get alerts for user's location
            location = subscription.get("location", {}).get("coordinates", [])
            if len(location) < 2:
                return []

            longitude, latitude = location
            radius = subscription.get("radius_km", 100)

            # Filter by user preferences
            alert_types = subscription.get("alert_types")
            min_severity = subscription.get("min_severity")

            if min_severity:
                min_severity = AlertSeverity(min_severity)

            if alert_types:
                alert_types = [AlertType(t) for t in alert_types]

            return await self.get_active_alerts(
                latitude=latitude,
                longitude=longitude,
                radius_km=radius,
                alert_types=alert_types,
                min_severity=min_severity,
            )
        except Exception as e:
            logger.error(f"Failed to get alerts for user {user_id}: {e}")
            return []


# Global service instance
_predictive_alert_service: Optional[PredictiveAlertService] = None


async def initialize_predictive_alert_service():
    """Initialize the predictive alert service"""
    global _predictive_alert_service

    if _predictive_alert_service is None:
        _predictive_alert_service = PredictiveAlertService()
        await _predictive_alert_service.initialize()

    return _predictive_alert_service


def get_predictive_alert_service() -> PredictiveAlertService:
    """Get the predictive alert service instance"""
    global _predictive_alert_service

    if _predictive_alert_service is None:
        raise RuntimeError("Predictive Alert Service not initialized")

    return _predictive_alert_service
