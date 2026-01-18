"""
ML-powered hazard monitoring service.

This service manages:
1. Monitored locations (12+ coastal areas)
2. ML model execution for hazard detection
3. Real-time data updates every 5 minutes
4. Earthquake data integration

NOTE: Currently uses mock data. Replace run_ml_model() with actual ML model integration.
"""
import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional
import random
from uuid import uuid4

from app.models.monitoring import (
    MonitoringLocation,
    MonitoringResponse,
    MonitoringSummary,
    EarthquakeData,
    CurrentHazards,
    TsunamiHazard,
    CycloneHazard,
    HighWavesHazard,
    FloodHazard,
    Coordinates,
    AlertLevel,
    AlertStatus,
    CycloneCategory,
    BeachFlag
)

logger = logging.getLogger(__name__)


class MLMonitorService:
    """
    Service for ML-powered hazard monitoring.

    Singleton service that:
    - Maintains list of monitored locations
    - Runs ML detection every 5 minutes (background task)
    - Provides current monitoring data to API endpoints
    - Fetches and processes earthquake data
    """

    def __init__(self):
        self.locations_config = self._initialize_locations()
        self.current_data: Optional[MonitoringResponse] = None
        self.last_update: Optional[datetime] = None
        self.model_version = "1.0.0"
        self.is_running = False
        self.background_task = None
        self._initialized = False

        logger.info("ML Monitoring Service created (will initialize on first request)")

    def _initialize_locations(self) -> Dict:
        """
        Initialize monitored locations with their coordinates and metadata.

        These are the 12+ locations being monitored by the ML system.
        Coordinates are approximate centers of coastal cities.
        """
        return {
            "mumbai": {
                "name": "Mumbai",
                "country": "India",
                "coordinates": {"lat": 19.0760, "lon": 72.8777},
                "population": 12442373
            },
            "chennai": {
                "name": "Chennai",
                "country": "India",
                "coordinates": {"lat": 13.0827, "lon": 80.2707},
                "population": 7088000
            },
            "kolkata": {
                "name": "Kolkata",
                "country": "India",
                "coordinates": {"lat": 22.5726, "lon": 88.3639},
                "population": 4496694
            },
            "vishakhapatnam": {
                "name": "Visakhapatnam",
                "country": "India",
                "coordinates": {"lat": 17.6868, "lon": 83.2185},
                "population": 2035922
            },
            "kochi": {
                "name": "Kochi",
                "country": "India",
                "coordinates": {"lat": 9.9312, "lon": 76.2673},
                "population": 2117990
            },
            "port_blair": {
                "name": "Port Blair",
                "country": "India (Andaman Islands)",
                "coordinates": {"lat": 11.6234, "lon": 92.7265},
                "population": 100186
            },
            "puducherry": {
                "name": "Puducherry",
                "country": "India",
                "coordinates": {"lat": 11.9416, "lon": 79.8083},
                "population": 244377
            },
            "goa": {
                "name": "Goa",
                "country": "India",
                "coordinates": {"lat": 15.2993, "lon": 74.1240},
                "population": 1458545
            },
            "mangalore": {
                "name": "Mangalore",
                "country": "India",
                "coordinates": {"lat": 12.9141, "lon": 74.8560},
                "population": 623841
            },
            "thiruvananthapuram": {
                "name": "Thiruvananthapuram",
                "country": "India",
                "coordinates": {"lat": 8.5241, "lon": 76.9366},
                "population": 957730
            },
            "karachi": {
                "name": "Karachi",
                "country": "Pakistan",
                "coordinates": {"lat": 24.8607, "lon": 67.0011},
                "population": 14910352
            },
            "dhaka": {
                "name": "Dhaka",
                "country": "Bangladesh",
                "coordinates": {"lat": 23.8103, "lon": 90.4125},
                "population": 8906039
            },
            "colombo": {
                "name": "Colombo",
                "country": "Sri Lanka",
                "coordinates": {"lat": 6.9271, "lon": 79.8612},
                "population": 752993
            },
            "male": {
                "name": "Male",
                "country": "Maldives",
                "coordinates": {"lat": 4.1755, "lon": 73.5093},
                "population": 133019
            }
        }

    async def run_detection_cycle(self) -> bool:
        """
        Run a complete detection cycle.

        This should be called:
        1. On service initialization
        2. Every 5 minutes by background task
        3. Manually via API endpoint (admin only)

        Returns True if successful, False otherwise.
        """
        try:
            if self.is_running:
                logger.warning("Detection cycle already running, skipping...")
                return False

            self.is_running = True
            logger.info("Starting hazard detection cycle...")

            # Step 1: Run ML model for all locations
            all_hazards, all_weather, all_marine = await self._run_ml_model()

            # Step 2: Fetch recent earthquake data
            earthquakes = await self._fetch_earthquake_data()

            # Step 3: Build monitoring locations with hazard data
            locations_dict = {}
            all_location_data = []

            for loc_id, loc_config in self.locations_config.items():
                hazards = all_hazards.get(loc_id, {})
                weather = all_weather.get(loc_id)
                marine = all_marine.get(loc_id)

                # Determine max alert level
                max_alert = self._get_max_alert_level(hazards)

                # Determine status
                status = self._alert_level_to_status(max_alert)

                # Generate recommendations
                recommendations = self._generate_recommendations(hazards, max_alert)

                # Import weather/marine data models
                from app.models.monitoring import WeatherData, MarineData

                # Build location object
                location = MonitoringLocation(
                    location_id=loc_id,
                    name=loc_config["name"],
                    country=loc_config["country"],
                    coordinates=Coordinates(**loc_config["coordinates"]),
                    population=loc_config["population"],
                    current_hazards=CurrentHazards(**hazards),
                    max_alert=max_alert,
                    status=status,
                    recommendations=recommendations,
                    weather=WeatherData(**weather) if weather else None,
                    marine=MarineData(**marine) if marine else None,
                    last_updated=datetime.now(timezone.utc)
                )

                locations_dict[loc_id] = location
                all_location_data.append(location)

            # Step 4: Calculate summary statistics
            summary = self._calculate_summary(all_location_data)

            # Step 5: Update current data
            self.current_data = MonitoringResponse(
                locations=locations_dict,
                summary=summary,
                recent_earthquakes=earthquakes
            )

            self.last_update = datetime.now(timezone.utc)
            logger.info(f"Detection cycle completed successfully. Found {summary.critical_alerts} critical alerts.")

            return True

        except Exception as e:
            logger.error(f"Error in detection cycle: {e}", exc_info=True)
            return False
        finally:
            self.is_running = False

    async def _run_ml_model(self) -> tuple:
        """
        Run ML model for hazard detection with real-time weather and tide data.

        This function fetches weather/marine data for each location and
        generates hazard predictions using the ML model.

        Returns:
            Tuple of (hazards_dict, weather_dict, marine_dict) mapping location_id to data
        """
        logger.info("Running ML model with real-time weather and seismic data...")

        # Import weather service
        from app.services.weather_service import weather_service

        hazards_by_location = {}
        weather_by_location = {}
        marine_by_location = {}

        for loc_id, loc_config in self.locations_config.items():
            try:
                # Get coordinates for this location
                lat = loc_config["coordinates"]["lat"]
                lon = loc_config["coordinates"]["lon"]

                # Fetch real-time weather data
                weather_data = await weather_service.fetch_current_weather(lat, lon)
                weather_by_location[loc_id] = weather_data

                # Fetch marine/tide data for coastal analysis
                marine_data = await weather_service.fetch_marine_data(lat, lon)
                marine_by_location[loc_id] = marine_data

                # Get recent earthquakes near this location
                nearby_earthquakes = self._get_nearby_earthquakes(lat, lon, radius_km=500)

                # Run ML prediction model
                hazards = await self._generate_predictions(
                    location_id=loc_id,
                    location_config=loc_config,
                    weather=weather_data,
                    marine=marine_data,
                    earthquakes=nearby_earthquakes
                )

                hazards_by_location[loc_id] = hazards

            except Exception as e:
                logger.error(f"Error running ML model for {loc_id}: {e}")
                # Return empty hazards for this location if error occurs
                hazards_by_location[loc_id] = {}
                weather_by_location[loc_id] = None
                marine_by_location[loc_id] = None

        return hazards_by_location, weather_by_location, marine_by_location

    async def _fetch_earthquake_data(self) -> List[EarthquakeData]:
        """
        Fetch recent earthquake data from USGS API.

        Returns:
            List of recent earthquakes from USGS
        """
        try:
            from app.services.real_data_fetcher import real_data_fetcher

            # Fetch REAL earthquakes from USGS
            earthquakes = await real_data_fetcher.fetch_earthquakes(
                hours=24,
                min_magnitude=4.0,
                min_lat=0,
                max_lat=25,
                min_lon=65,
                max_lon=95
            )

            logger.info(f"✓ Fetched {len(earthquakes)} REAL earthquakes from USGS")
            return earthquakes

        except Exception as e:
            logger.error(f"✗ Error fetching earthquake data: {e}")
            # Return empty list if API fails
            return []

    def _get_nearby_earthquakes(self, lat: float, lon: float, radius_km: float) -> List[EarthquakeData]:
        """
        Get earthquakes within a certain radius of a location.

        Args:
            lat: Location latitude
            lon: Location longitude
            radius_km: Search radius in kilometers

        Returns:
            List of nearby earthquakes
        """
        if not self.current_data or not self.current_data.recent_earthquakes:
            return []

        nearby = []
        for eq in self.current_data.recent_earthquakes:
            distance = self._calculate_distance(
                lat, lon,
                eq.coordinates.lat, eq.coordinates.lon
            )
            if distance <= radius_km:
                nearby.append(eq)

        return nearby

    def _calculate_distance(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """
        Calculate distance between two coordinates using Haversine formula.

        Args:
            lat1, lon1: First coordinate
            lat2, lon2: Second coordinate

        Returns:
            Distance in kilometers
        """
        from math import radians, sin, cos, sqrt, atan2

        R = 6371  # Earth's radius in kilometers

        lat1_rad = radians(lat1)
        lat2_rad = radians(lat2)
        delta_lat = radians(lat2 - lat1)
        delta_lon = radians(lon2 - lon1)

        a = sin(delta_lat / 2) ** 2 + cos(lat1_rad) * cos(lat2_rad) * sin(delta_lon / 2) ** 2
        c = 2 * atan2(sqrt(a), sqrt(1 - a))

        return R * c

    async def _generate_predictions(
        self,
        location_id: str,
        location_config: Dict,
        weather: Optional[Dict],
        marine: Optional[Dict],
        earthquakes: List[EarthquakeData]
    ) -> Dict:
        """
        Generate hazard predictions using ML model with real-time data.

        This is the core ML prediction function that analyzes:
        - Weather conditions (temperature, wind, pressure, humidity)
        - Marine data (wave height, water temp, swell)
        - Recent seismic activity
        - Historical patterns

        Args:
            location_id: Location identifier
            location_config: Location configuration dict
            weather: Current weather data
            marine: Marine/tide data
            earthquakes: Recent earthquakes near this location

        Returns:
            Dict with hazard predictions
        """
        hazards = {}

        # TSUNAMI DETECTION
        # Use earthquake data + marine conditions
        tsunami_prediction = self._predict_tsunami(
            earthquakes=earthquakes,
            location=location_config,
            marine=marine
        )
        if tsunami_prediction:
            hazards["tsunami"] = tsunami_prediction

        # CYCLONE DETECTION
        # Use weather patterns (pressure, wind speed, temperature)
        cyclone_prediction = self._predict_cyclone(
            weather=weather,
            location=location_config
        )
        if cyclone_prediction:
            hazards["cyclone"] = cyclone_prediction

        # HIGH WAVES DETECTION
        # Use marine data (wave height, swell period)
        high_waves_prediction = self._predict_high_waves(
            marine=marine,
            weather=weather
        )
        if high_waves_prediction:
            hazards["high_waves"] = high_waves_prediction

        # FLOOD DETECTION
        # Use weather data (rainfall, pressure trends)
        flood_prediction = self._predict_flood(
            weather=weather,
            location=location_config
        )
        if flood_prediction:
            hazards["flood"] = flood_prediction

        return hazards

    def _predict_tsunami(
        self,
        earthquakes: List[EarthquakeData],
        location: Dict,
        marine: Optional[Dict]
    ) -> Optional[Dict]:
        """
        Predict tsunami risk based on earthquake data and marine conditions.

        Tsunami risk factors:
        - Earthquake magnitude >= 6.5 (shallow depth < 70km)
        - Distance from coastline
        - Abnormal wave patterns

        Returns:
            Tsunami prediction dict or None
        """
        if not earthquakes:
            return None

        # Analyze each nearby earthquake for tsunami potential
        max_risk = 0.0
        triggering_earthquake = None

        for eq in earthquakes:
            # Tsunami generation criteria (NOAA/PTWC standards)
            if eq.magnitude >= 6.5 and eq.depth_km < 70:
                # Calculate risk score based on magnitude and depth
                magnitude_factor = min((eq.magnitude - 6.5) / 2.5, 1.0)  # 6.5-9.0 scale
                depth_factor = 1.0 - (eq.depth_km / 70.0)  # Shallower = higher risk

                risk = magnitude_factor * 0.7 + depth_factor * 0.3

                if risk > max_risk:
                    max_risk = risk
                    triggering_earthquake = eq

        if max_risk < 0.1:  # Below 10% risk threshold
            return None

        # Calculate alert level from risk probability
        alert_level = self._probability_to_alert_level(max_risk)

        # Estimate tsunami arrival time (rough approximation: 500 km/h tsunami speed)
        distance_km = self._calculate_distance(
            location["coordinates"]["lat"],
            location["coordinates"]["lon"],
            triggering_earthquake.coordinates.lat,
            triggering_earthquake.coordinates.lon
        )
        estimated_arrival_minutes = int((distance_km / 500) * 60)

        # Estimate wave height based on magnitude
        estimated_wave_height = max(1.0, (triggering_earthquake.magnitude - 6.0) * 2.0)

        return {
            "alert_level": alert_level,
            "probability": round(max_risk, 3),
            "estimated_arrival_minutes": estimated_arrival_minutes,
            "wave_height_meters": round(estimated_wave_height, 1),
            "source_earthquake_id": triggering_earthquake.earthquake_id,
            "source_magnitude": triggering_earthquake.magnitude,
            "source_depth_km": triggering_earthquake.depth_km
        }

    def _predict_cyclone(
        self,
        weather: Optional[Dict],
        location: Dict
    ) -> Optional[Dict]:
        """
        Predict cyclone risk based on weather patterns.

        Cyclone indicators:
        - Low atmospheric pressure (< 990 mb)
        - High wind speeds (> 60 km/h)
        - High humidity (> 80%)

        Returns:
            Cyclone prediction dict or None
        """
        if not weather:
            return None

        risk_score = 0.0

        # Analyze pressure (critical indicator)
        pressure = weather.get("pressure_mb", 1013)
        if pressure < 990:
            risk_score += 0.4
        elif pressure < 1000:
            risk_score += 0.2

        # Analyze wind speed
        wind_kph = weather.get("wind_kph", 0)
        if wind_kph > 80:
            risk_score += 0.3
        elif wind_kph > 60:
            risk_score += 0.15

        # Analyze humidity
        humidity = weather.get("humidity", 50)
        if humidity > 85:
            risk_score += 0.2
        elif humidity > 75:
            risk_score += 0.1

        # Temperature factor (cyclones form in warm waters)
        temp_c = weather.get("temperature_c", 25)
        if temp_c > 28:
            risk_score += 0.1

        if risk_score < 0.2:  # Below 20% risk threshold
            return None

        alert_level = self._probability_to_alert_level(risk_score)

        # Determine cyclone category based on wind speed
        if wind_kph >= 119:
            category = CycloneCategory.SEVERE_CYCLONIC_STORM
        elif wind_kph >= 89:
            category = CycloneCategory.VERY_SEVERE_CYCLONIC_STORM
        elif wind_kph >= 62:
            category = CycloneCategory.CYCLONIC_STORM
        else:
            category = CycloneCategory.DEPRESSION

        return {
            "alert_level": alert_level,
            "category": category,
            "wind_speed_kmh": wind_kph,
            "pressure_mb": pressure,
            "distance_km": 0,  # Current location
            "direction": weather.get("wind_dir", "Unknown")
        }

    def _predict_high_waves(
        self,
        marine: Optional[Dict],
        weather: Optional[Dict]
    ) -> Optional[Dict]:
        """
        Predict high wave conditions based on marine data.

        High wave indicators:
        - Wave height > 2.5m
        - Strong winds
        - Low visibility

        Returns:
            High waves prediction dict or None
        """
        if not marine and not weather:
            return None

        wave_height = 0.0
        if marine:
            wave_height = marine.get("wave_height_m", 0) or marine.get("max_wave_height_m", 0)

        # Also consider wind-driven waves
        if weather and wave_height == 0:
            wind_kph = weather.get("wind_kph", 0)
            # Estimate wave height from wind (rough approximation)
            wave_height = wind_kph / 40.0  # 40 km/h wind ≈ 1m waves

        if wave_height < 2.0:  # Below 2m threshold
            return None

        # Determine beach flag and alert level
        if wave_height >= 5.0:
            beach_flag = BeachFlag.DOUBLE_RED
            alert_level = AlertLevel.CRITICAL
        elif wave_height >= 3.5:
            beach_flag = BeachFlag.RED
            alert_level = AlertLevel.HIGH
        elif wave_height >= 2.5:
            beach_flag = BeachFlag.YELLOW
            alert_level = AlertLevel.WARNING
        else:
            beach_flag = BeachFlag.YELLOW
            alert_level = AlertLevel.LOW

        return {
            "alert_level": alert_level,
            "beach_flag": beach_flag,
            "wave_height_m": round(wave_height, 1),
            "swell_period_secs": marine.get("swell_period_secs", 0) if marine else 0
        }

    def _predict_flood(
        self,
        weather: Optional[Dict],
        location: Dict
    ) -> Optional[Dict]:
        """
        Predict flood risk based on weather conditions.

        Flood indicators:
        - High humidity (> 85%)
        - Low pressure (< 1000 mb)
        - Poor visibility (< 2 km indicates heavy rain)

        Returns:
            Flood prediction dict or None
        """
        if not weather:
            return None

        flood_score = 0

        # Analyze humidity (rainfall indicator)
        humidity = weather.get("humidity", 50)
        if humidity > 90:
            flood_score += 40
        elif humidity > 85:
            flood_score += 25
        elif humidity > 75:
            flood_score += 15

        # Analyze visibility (heavy rain indicator)
        visibility_km = weather.get("visibility_km", 10)
        if visibility_km < 2:
            flood_score += 30
        elif visibility_km < 5:
            flood_score += 15

        # Analyze pressure (storm system indicator)
        pressure = weather.get("pressure_mb", 1013)
        if pressure < 995:
            flood_score += 20
        elif pressure < 1005:
            flood_score += 10

        # Wind factor
        wind_kph = weather.get("wind_kph", 0)
        if wind_kph > 50:
            flood_score += 10

        if flood_score < 30:  # Below 30% risk threshold
            return None

        # Convert flood score to alert level
        if flood_score >= 80:
            alert_level = AlertLevel.CRITICAL
        elif flood_score >= 65:
            alert_level = AlertLevel.HIGH
        elif flood_score >= 50:
            alert_level = AlertLevel.WARNING
        elif flood_score >= 35:
            alert_level = AlertLevel.LOW
        else:
            alert_level = AlertLevel.NORMAL

        return {
            "alert_level": alert_level,
            "flood_score": flood_score,
            "rainfall_intensity": "Heavy" if visibility_km < 2 else "Moderate" if visibility_km < 5 else "Light",
            "affected_zones": []  # Can be populated with local zone data
        }

    def _get_max_alert_level(self, hazards: Dict) -> AlertLevel:
        """Get the maximum alert level from all hazards."""
        max_level = 1

        for hazard_type, hazard_data in hazards.items():
            if isinstance(hazard_data, dict) and "alert_level" in hazard_data:
                max_level = max(max_level, hazard_data["alert_level"])

        return AlertLevel(max_level)

    def _alert_level_to_status(self, alert_level: AlertLevel) -> AlertStatus:
        """Convert alert level to status string."""
        mapping = {
            1: AlertStatus.NORMAL,
            2: AlertStatus.LOW,
            3: AlertStatus.WARNING,
            4: AlertStatus.HIGH,
            5: AlertStatus.CRITICAL
        }
        return mapping.get(alert_level, AlertStatus.NORMAL)

    def _probability_to_alert_level(self, probability: float) -> int:
        """Convert probability (0-1) to alert level (1-5)."""
        if probability >= 0.8:
            return 5
        elif probability >= 0.6:
            return 4
        elif probability >= 0.4:
            return 3
        elif probability >= 0.2:
            return 2
        else:
            return 1

    def _generate_recommendations(self, hazards: Dict, max_alert: AlertLevel) -> List[str]:
        """Generate safety recommendations based on hazards and alert level."""
        recommendations = []

        # Critical alerts
        if max_alert == AlertLevel.CRITICAL:
            recommendations.append("⚠️ EVACUATE coastal areas immediately")
            recommendations.append("Move to higher ground (>30m elevation)")
            recommendations.append("Follow official evacuation routes")

        # High alerts
        elif max_alert == AlertLevel.HIGH:
            recommendations.append("⚠️ Prepare for possible evacuation")
            recommendations.append("Stay away from beaches and coastal areas")
            recommendations.append("Monitor official updates closely")

        # Warning
        elif max_alert == AlertLevel.WARNING:
            recommendations.append("Stay informed of weather conditions")
            recommendations.append("Avoid non-essential coastal activities")
            recommendations.append("Keep emergency supplies ready")

        # Specific hazard recommendations
        if "tsunami" in hazards and hazards["tsunami"].get("alert_level", 0) >= 3:
            recommendations.append("🌊 Tsunami threat - move inland immediately")

        if "cyclone" in hazards and hazards["cyclone"].get("alert_level", 0) >= 4:
            recommendations.append("🌀 Severe cyclone - secure property and stay indoors")

        if "high_waves" in hazards and hazards["high_waves"].get("beach_flag") in ["RED", "DOUBLE_RED"]:
            recommendations.append("🏖️ No swimming - dangerous surf conditions")

        if "flood" in hazards and hazards["flood"].get("alert_level", 0) >= 3:
            recommendations.append("💧 Flood risk - avoid low-lying areas")

        # Default for low/normal
        if not recommendations:
            recommendations.append("✅ Normal conditions - exercise usual caution")

        return recommendations

    def _calculate_summary(self, locations: List[MonitoringLocation]) -> MonitoringSummary:
        """Calculate summary statistics from all locations."""
        critical = sum(1 for loc in locations if loc.max_alert == AlertLevel.CRITICAL)
        high = sum(1 for loc in locations if loc.max_alert == AlertLevel.HIGH)
        warning = sum(1 for loc in locations if loc.max_alert == AlertLevel.WARNING)
        low = sum(1 for loc in locations if loc.max_alert == AlertLevel.LOW)
        normal = sum(1 for loc in locations if loc.max_alert == AlertLevel.NORMAL)

        # Count active hazards
        tsunamis = sum(1 for loc in locations if loc.current_hazards.tsunami is not None)
        cyclones = sum(1 for loc in locations if loc.current_hazards.cyclone is not None)
        high_waves = sum(1 for loc in locations if loc.current_hazards.high_waves is not None)
        floods = sum(1 for loc in locations if loc.current_hazards.flood is not None)

        return MonitoringSummary(
            total_locations=len(locations),
            critical_alerts=critical,
            high_alerts=high,
            warning_alerts=warning,
            low_alerts=low,
            normal_alerts=normal,
            active_tsunamis=tsunamis,
            active_cyclones=cyclones,
            active_high_waves=high_waves,
            active_floods=floods,
            last_updated=datetime.now(timezone.utc)
        )

    # Public methods for API endpoints

    def get_locations(self) -> List[Dict]:
        """Get list of all monitored locations (basic info only)."""
        return [
            {
                "location_id": loc_id,
                "name": config["name"],
                "country": config["country"],
                "coordinates": config["coordinates"],
                "population": config["population"]
            }
            for loc_id, config in self.locations_config.items()
        ]

    async def initialize(self):
        """
        Initialize the service with first data load.
        Should be called during FastAPI startup.
        """
        if not self._initialized:
            logger.info("Running initial hazard detection...")
            await self.run_detection_cycle()
            self._initialized = True
            logger.info("ML Monitoring Service initialized successfully")

    def get_current_data(self) -> MonitoringResponse:
        """Get current monitoring data for all locations."""
        if self.current_data is None:
            # Return empty data structure if not initialized yet
            logger.warning("Monitoring data not yet available, returning empty response")
            return MonitoringResponse(
                locations={},
                summary=MonitoringSummary(
                    total_locations=0,
                    critical_alerts=0,
                    high_alerts=0,
                    warning_alerts=0,
                    low_alerts=0,
                    normal_alerts=0,
                    active_tsunamis=0,
                    active_cyclones=0,
                    active_high_waves=0,
                    active_floods=0,
                    last_updated=datetime.now(timezone.utc)
                ),
                recent_earthquakes=[]
            )

        return self.current_data

    def get_location_by_id(self, location_id: str) -> Optional[MonitoringLocation]:
        """Get monitoring data for a specific location."""
        if self.current_data is None:
            return None

        return self.current_data.locations.get(location_id)

    def get_recent_earthquakes(self, hours: int = 24, min_magnitude: float = 4.0) -> List[EarthquakeData]:
        """Get recent earthquakes filtered by time and magnitude."""
        if self.current_data is None or not self.current_data.recent_earthquakes:
            return []

        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)

        filtered = [
            eq for eq in self.current_data.recent_earthquakes
            if eq.timestamp >= cutoff_time and eq.magnitude >= min_magnitude
        ]

        return filtered

    def get_health_status(self) -> Dict:
        """Get health status of monitoring service."""
        return {
            "status": "healthy" if self.current_data is not None else "initializing",
            "last_update": self.last_update.isoformat() if self.last_update else None,
            "is_running": self.is_running,
            "model_version": self.model_version,
            "monitored_locations": len(self.locations_config),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }


# Create singleton instance
ml_service = MLMonitorService()
