"""
MultiHazard Detection Service
Real-time coastal hazard monitoring for Indian coastal cities.
Implements 5 hazard detectors: Tsunami, Cyclone, High Waves, Coastal Flood, Rip Currents.
"""

import asyncio
import logging
import uuid
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any
import httpx

from app.config import settings
from app.models.multi_hazard import (
    AlertLevel, HazardType, DetectionMethod,
    Coordinates, WeatherParams, MarineParams, EarthquakeData,
    HazardAlert, MonitoredLocation, LocationStatus,
    MultiHazardSummary, MultiHazardResponse, DetectionCycleResult,
    HazardThresholds
)

logger = logging.getLogger(__name__)


class MultiHazardService:
    """
    Real-time multi-hazard detection service for Indian coastal cities.

    Monitors 7 key coastal locations:
    - Mumbai, Chennai, Kolkata, Visakhapatnam, Kochi, Port Blair, Goa

    Detects 5 hazard types:
    - Tsunami (ML + Rule-based)
    - Cyclone (Rule-based)
    - High Waves (Rule-based)
    - Coastal Flood (Rule-based)
    - Rip Currents (Rule-based)
    """

    # Coastal monitoring locations - India and Indian Ocean region
    MONITORED_LOCATIONS: Dict[str, MonitoredLocation] = {
        # === INDIA - West Coast (Arabian Sea) ===
        "mumbai": MonitoredLocation(
            location_id="mumbai",
            name="Mumbai",
            country="India",
            coordinates=Coordinates(lat=19.0760, lon=72.8777),
            region="Arabian Sea",
            coastline_type="west",
            population=12442373,
            risk_profile="high"
        ),
        "goa": MonitoredLocation(
            location_id="goa",
            name="Goa",
            country="India",
            coordinates=Coordinates(lat=15.2993, lon=74.1240),
            region="Arabian Sea",
            coastline_type="west",
            population=1458545,
            risk_profile="medium"
        ),
        "kochi": MonitoredLocation(
            location_id="kochi",
            name="Kochi",
            country="India",
            coordinates=Coordinates(lat=9.9312, lon=76.2673),
            region="Arabian Sea",
            coastline_type="west",
            population=677381,
            risk_profile="medium"
        ),
        "mangalore": MonitoredLocation(
            location_id="mangalore",
            name="Mangalore",
            country="India",
            coordinates=Coordinates(lat=12.9141, lon=74.8560),
            region="Arabian Sea",
            coastline_type="west",
            population=623841,
            risk_profile="medium"
        ),
        "thiruvananthapuram": MonitoredLocation(
            location_id="thiruvananthapuram",
            name="Thiruvananthapuram",
            country="India",
            coordinates=Coordinates(lat=8.5241, lon=76.9366),
            region="Arabian Sea",
            coastline_type="west",
            population=957730,
            risk_profile="medium"
        ),
        "surat": MonitoredLocation(
            location_id="surat",
            name="Surat",
            country="India",
            coordinates=Coordinates(lat=21.1702, lon=72.8311),
            region="Arabian Sea",
            coastline_type="west",
            population=4467797,
            risk_profile="high"
        ),
        # === INDIA - East Coast (Bay of Bengal) ===
        "chennai": MonitoredLocation(
            location_id="chennai",
            name="Chennai",
            country="India",
            coordinates=Coordinates(lat=13.0827, lon=80.2707),
            region="Bay of Bengal",
            coastline_type="east",
            population=7088000,
            risk_profile="high"
        ),
        "kolkata": MonitoredLocation(
            location_id="kolkata",
            name="Kolkata",
            country="India",
            coordinates=Coordinates(lat=22.5726, lon=88.3639),
            region="Bay of Bengal",
            coastline_type="east",
            population=4496694,
            risk_profile="high"
        ),
        "visakhapatnam": MonitoredLocation(
            location_id="visakhapatnam",
            name="Visakhapatnam",
            country="India",
            coordinates=Coordinates(lat=17.6868, lon=83.2185),
            region="Bay of Bengal",
            coastline_type="east",
            population=2035922,
            risk_profile="medium"
        ),
        "puri": MonitoredLocation(
            location_id="puri",
            name="Puri",
            country="India",
            coordinates=Coordinates(lat=19.8135, lon=85.8312),
            region="Bay of Bengal",
            coastline_type="east",
            population=201026,
            risk_profile="high"
        ),
        "paradip": MonitoredLocation(
            location_id="paradip",
            name="Paradip",
            country="India",
            coordinates=Coordinates(lat=20.3167, lon=86.6167),
            region="Bay of Bengal",
            coastline_type="east",
            population=68585,
            risk_profile="high"
        ),
        "digha": MonitoredLocation(
            location_id="digha",
            name="Digha",
            country="India",
            coordinates=Coordinates(lat=21.6275, lon=87.5097),
            region="Bay of Bengal",
            coastline_type="east",
            population=42498,
            risk_profile="high"
        ),
        "pondicherry": MonitoredLocation(
            location_id="pondicherry",
            name="Pondicherry",
            country="India",
            coordinates=Coordinates(lat=11.9416, lon=79.8083),
            region="Bay of Bengal",
            coastline_type="east",
            population=244377,
            risk_profile="medium"
        ),
        "tuticorin": MonitoredLocation(
            location_id="tuticorin",
            name="Tuticorin",
            country="India",
            coordinates=Coordinates(lat=8.7642, lon=78.1348),
            region="Bay of Bengal",
            coastline_type="east",
            population=410121,
            risk_profile="medium"
        ),
        # === INDIA - Islands ===
        "port_blair": MonitoredLocation(
            location_id="port_blair",
            name="Port Blair",
            country="India",
            coordinates=Coordinates(lat=11.6234, lon=92.7265),
            region="Andaman & Nicobar",
            coastline_type="island",
            population=108050,
            risk_profile="critical"
        ),
        "kavaratti": MonitoredLocation(
            location_id="kavaratti",
            name="Kavaratti",
            country="India",
            coordinates=Coordinates(lat=10.5593, lon=72.6358),
            region="Lakshadweep",
            coastline_type="island",
            population=11210,
            risk_profile="critical"
        ),
        # === INDIA - Additional West Coast ===
        "porbandar": MonitoredLocation(
            location_id="porbandar",
            name="Porbandar",
            country="India",
            coordinates=Coordinates(lat=21.6417, lon=69.6293),
            region="Arabian Sea",
            coastline_type="west",
            population=152760,
            risk_profile="medium"
        ),
        "veraval": MonitoredLocation(
            location_id="veraval",
            name="Veraval",
            country="India",
            coordinates=Coordinates(lat=20.9067, lon=70.3667),
            region="Arabian Sea",
            coastline_type="west",
            population=153696,
            risk_profile="medium"
        ),
        "ratnagiri": MonitoredLocation(
            location_id="ratnagiri",
            name="Ratnagiri",
            country="India",
            coordinates=Coordinates(lat=16.9944, lon=73.3000),
            region="Arabian Sea",
            coastline_type="west",
            population=76239,
            risk_profile="medium"
        ),
        "karwar": MonitoredLocation(
            location_id="karwar",
            name="Karwar",
            country="India",
            coordinates=Coordinates(lat=14.8135, lon=74.1295),
            region="Arabian Sea",
            coastline_type="west",
            population=75438,
            risk_profile="medium"
        ),
        "kannur": MonitoredLocation(
            location_id="kannur",
            name="Kannur",
            country="India",
            coordinates=Coordinates(lat=11.8745, lon=75.3704),
            region="Arabian Sea",
            coastline_type="west",
            population=232486,
            risk_profile="medium"
        ),
        "kozhikode": MonitoredLocation(
            location_id="kozhikode",
            name="Kozhikode (Calicut)",
            country="India",
            coordinates=Coordinates(lat=11.2588, lon=75.7804),
            region="Arabian Sea",
            coastline_type="west",
            population=609224,
            risk_profile="medium"
        ),
        # === INDIA - Additional East Coast ===
        "machilipatnam": MonitoredLocation(
            location_id="machilipatnam",
            name="Machilipatnam",
            country="India",
            coordinates=Coordinates(lat=16.1875, lon=81.1389),
            region="Bay of Bengal",
            coastline_type="east",
            population=179584,
            risk_profile="high"
        ),
        "kakinada": MonitoredLocation(
            location_id="kakinada",
            name="Kakinada",
            country="India",
            coordinates=Coordinates(lat=16.9891, lon=82.2475),
            region="Bay of Bengal",
            coastline_type="east",
            population=443028,
            risk_profile="high"
        ),
        "gopalpur": MonitoredLocation(
            location_id="gopalpur",
            name="Gopalpur",
            country="India",
            coordinates=Coordinates(lat=19.2667, lon=84.9167),
            region="Bay of Bengal",
            coastline_type="east",
            population=10000,
            risk_profile="high"
        ),
        "cuddalore": MonitoredLocation(
            location_id="cuddalore",
            name="Cuddalore",
            country="India",
            coordinates=Coordinates(lat=11.7480, lon=79.7714),
            region="Bay of Bengal",
            coastline_type="east",
            population=173676,
            risk_profile="high"
        ),
        "nagapattinam": MonitoredLocation(
            location_id="nagapattinam",
            name="Nagapattinam",
            country="India",
            coordinates=Coordinates(lat=10.7672, lon=79.8449),
            region="Bay of Bengal",
            coastline_type="east",
            population=102905,
            risk_profile="critical"
        ),
        "rameswaram": MonitoredLocation(
            location_id="rameswaram",
            name="Rameswaram",
            country="India",
            coordinates=Coordinates(lat=9.2876, lon=79.3129),
            region="Bay of Bengal",
            coastline_type="east",
            population=44856,
            risk_profile="high"
        ),
        "kanyakumari": MonitoredLocation(
            location_id="kanyakumari",
            name="Kanyakumari",
            country="India",
            coordinates=Coordinates(lat=8.0883, lon=77.5385),
            region="Indian Ocean",
            coastline_type="south",
            population=19739,
            risk_profile="high"
        ),
        # === INDIA - Additional Bengal/Odisha Coast ===
        "haldia": MonitoredLocation(
            location_id="haldia",
            name="Haldia",
            country="India",
            coordinates=Coordinates(lat=22.0667, lon=88.0698),
            region="Bay of Bengal",
            coastline_type="east",
            population=200827,
            risk_profile="high"
        ),
    }

    # Hazard detection thresholds (from Weather Parameters PDF)
    # IMD Cyclone Classification:
    # - Depression: 31-49 kph
    # - Deep Depression: 50-61 kph
    # - Cyclonic Storm: 62-88 kph
    # - Severe Cyclonic Storm: 89-117 kph
    # - Very Severe Cyclonic Storm: 118-166 kph
    # - Extremely Severe Cyclonic Storm: 167-221 kph
    # - Super Cyclonic Storm: >221 kph
    THRESHOLDS = HazardThresholds(
        tsunami={
            "earthquake_magnitude": 6.5,
            "earthquake_depth_km": 70,
            "oceanic_only": True
        },
        cyclone={
            "wind_kph": 50,  # Lowered to detect Deep Depression and above
            "pressure_mb": 1000  # Lowered threshold for better detection
        },
        high_waves={
            "sig_ht_mt": 4.0,
            "swell_ht_mt": 3.0
        },
        coastal_flood={
            "tide_height_mt": 3.5,
            "precip_mm": 20
        },
        rip_currents={
            "swell_period_secs": 14,
            "sig_ht_mt": 2.5
        }
    )

    def __init__(self):
        self.is_monitoring = False
        self._monitoring_task: Optional[asyncio.Task] = None
        self._initialized = False

        # Active alerts by location
        self.active_alerts: Dict[str, List[HazardAlert]] = {
            loc_id: [] for loc_id in self.MONITORED_LOCATIONS
        }

        # Current location status
        self.location_status: Dict[str, LocationStatus] = {}

        # Recent earthquakes cache
        self.recent_earthquakes: List[EarthquakeData] = []

        # Detection cycle tracking
        self.last_detection_cycle: Optional[datetime] = None
        self.next_detection_cycle: Optional[datetime] = None

        # HTTP client
        self._http_client: Optional[httpx.AsyncClient] = None

    async def initialize(self):
        """Initialize the service and start monitoring if configured."""
        if self._initialized:
            return

        logger.info("Initializing MultiHazard Detection Service...")

        # Initialize HTTP client
        self._http_client = httpx.AsyncClient(timeout=30.0)

        # Initialize location status
        for loc_id, location in self.MONITORED_LOCATIONS.items():
            self.location_status[loc_id] = LocationStatus(
                location_id=loc_id,
                location_name=location.name,
                country=location.country,
                coordinates=location.coordinates,
                max_alert_level=AlertLevel.NORMAL,
                active_hazards=[],
                last_updated=datetime.now(timezone.utc)
            )

        self._initialized = True
        logger.info(f"MultiHazard Service initialized with {len(self.MONITORED_LOCATIONS)} locations")

        # Auto-start monitoring if configured
        if settings.MULTIHAZARD_AUTO_START:
            await self.start_monitoring()

    async def shutdown(self):
        """Cleanup resources."""
        await self.stop_monitoring()
        if self._http_client:
            await self._http_client.aclose()
            self._http_client = None
        self._initialized = False
        logger.info("MultiHazard Service shutdown complete")

    # =========================================================================
    # Monitoring Control
    # =========================================================================

    async def start_monitoring(self, interval_seconds: int = None):
        """Start the background monitoring task."""
        if self.is_monitoring:
            logger.warning("Monitoring already active")
            return

        interval = interval_seconds or settings.MULTIHAZARD_MONITORING_INTERVAL_SECONDS
        self.is_monitoring = True
        self._monitoring_task = asyncio.create_task(
            self._monitoring_loop(interval)
        )
        logger.info(f"MultiHazard monitoring started (interval: {interval}s)")

    async def stop_monitoring(self):
        """Stop the background monitoring task."""
        if not self.is_monitoring:
            return

        self.is_monitoring = False
        if self._monitoring_task:
            self._monitoring_task.cancel()
            try:
                await self._monitoring_task
            except asyncio.CancelledError:
                pass
            self._monitoring_task = None
        logger.info("MultiHazard monitoring stopped")

    async def _monitoring_loop(self, interval: int):
        """Background monitoring loop."""
        while self.is_monitoring:
            try:
                await self.run_detection_cycle()
                self.next_detection_cycle = datetime.now(timezone.utc) + timedelta(seconds=interval)
                await asyncio.sleep(interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                await asyncio.sleep(60)  # Wait before retry

    # =========================================================================
    # Detection Cycle
    # =========================================================================

    async def run_detection_cycle(
        self,
        location_ids: Optional[List[str]] = None
    ) -> DetectionCycleResult:
        """
        Run a complete detection cycle for all or specified locations.

        This:
        1. Fetches weather/marine data for each location
        2. Fetches recent earthquake data
        3. Runs all 5 hazard detectors
        4. Updates alerts and status
        """
        import time
        start_time = time.time()
        errors = []
        alerts_generated = 0

        locations_to_process = location_ids or list(self.MONITORED_LOCATIONS.keys())

        try:
            # Fetch earthquake data first (shared across all locations)
            await self._fetch_earthquake_data()

            # Process each location
            for loc_id in locations_to_process:
                if loc_id not in self.MONITORED_LOCATIONS:
                    errors.append(f"Unknown location: {loc_id}")
                    continue

                try:
                    location = self.MONITORED_LOCATIONS[loc_id]

                    # Fetch weather and marine data
                    weather, marine = await self._fetch_weather_data(location)

                    # Run all detectors
                    new_alerts = await self._detect_hazards(
                        location, weather, marine
                    )

                    # Update alerts
                    alerts_generated += len(new_alerts)
                    self._update_location_alerts(loc_id, new_alerts, weather, marine)

                except Exception as e:
                    errors.append(f"{loc_id}: {str(e)}")
                    logger.error(f"Detection error for {loc_id}: {e}")

            self.last_detection_cycle = datetime.now(timezone.utc)
            processing_time = (time.time() - start_time) * 1000

            logger.info(
                f"Detection cycle complete: {len(locations_to_process)} locations, "
                f"{alerts_generated} alerts, {processing_time:.0f}ms"
            )

            return DetectionCycleResult(
                success=len(errors) == 0,
                alerts_generated=alerts_generated,
                locations_processed=len(locations_to_process),
                processing_time_ms=processing_time,
                errors=errors
            )

        except Exception as e:
            logger.error(f"Detection cycle failed: {e}")
            return DetectionCycleResult(
                success=False,
                alerts_generated=0,
                locations_processed=0,
                processing_time_ms=(time.time() - start_time) * 1000,
                errors=[str(e)]
            )

    # =========================================================================
    # Data Fetching
    # =========================================================================

    async def _fetch_weather_data(
        self,
        location: MonitoredLocation
    ) -> tuple[Optional[WeatherParams], Optional[MarineParams]]:
        """Fetch weather and marine data from WeatherAPI."""
        try:
            url = "http://api.weatherapi.com/v1/forecast.json"
            params = {
                "key": settings.WEATHERAPI_KEY,
                "q": f"{location.coordinates.lat},{location.coordinates.lon}",
                "days": 1,
                "aqi": "no",
                "alerts": "yes"
            }

            response = await self._http_client.get(url, params=params)
            response.raise_for_status()
            data = response.json()

            current = data.get("current", {})

            weather = WeatherParams(
                temperature_c=current.get("temp_c"),
                wind_kph=current.get("wind_kph"),
                wind_dir=current.get("wind_dir"),
                gust_kph=current.get("gust_kph"),
                pressure_mb=current.get("pressure_mb"),
                humidity=current.get("humidity"),
                precip_mm=current.get("precip_mm"),
                visibility_km=current.get("vis_km"),
                cloud=current.get("cloud"),
                condition=current.get("condition", {}).get("text"),
                timestamp=datetime.now(timezone.utc)
            )

            # Marine data from forecast
            forecast_day = data.get("forecast", {}).get("forecastday", [{}])[0]
            day_data = forecast_day.get("day", {})

            marine = MarineParams(
                sig_ht_mt=day_data.get("maxwind_kph", 0) / 30,  # Approximation
                swell_ht_mt=None,
                swell_period_secs=None,
                swell_dir=None,
                tide_height_mt=None,
                water_temp_c=day_data.get("avgtemp_c"),
                timestamp=datetime.now(timezone.utc)
            )

            return weather, marine

        except Exception as e:
            logger.warning(f"Failed to fetch weather for {location.name}: {e}")
            return None, None

    async def _fetch_earthquake_data(self):
        """Fetch recent significant earthquakes from USGS."""
        try:
            # USGS API - significant earthquakes in last 24 hours
            url = "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/significant_day.geojson"

            response = await self._http_client.get(url)
            response.raise_for_status()
            data = response.json()

            self.recent_earthquakes = []

            for feature in data.get("features", []):
                props = feature.get("properties", {})
                coords = feature.get("geometry", {}).get("coordinates", [0, 0, 0])

                # Check if oceanic (simplified - longitude check for Indian Ocean region)
                lon, lat = coords[0], coords[1]
                is_oceanic = self._is_oceanic_location(lat, lon)

                earthquake = EarthquakeData(
                    earthquake_id=feature.get("id", str(uuid.uuid4())),
                    magnitude=props.get("mag", 0),
                    depth_km=coords[2] if len(coords) > 2 else 0,
                    coordinates=Coordinates(lat=lat, lon=lon),
                    location_description=props.get("place", "Unknown"),
                    timestamp=datetime.fromtimestamp(
                        props.get("time", 0) / 1000,
                        tz=timezone.utc
                    ),
                    is_oceanic=is_oceanic,
                    distance_to_coast_km=None
                )

                self.recent_earthquakes.append(earthquake)

            logger.debug(f"Fetched {len(self.recent_earthquakes)} recent earthquakes")

        except Exception as e:
            logger.warning(f"Failed to fetch earthquake data: {e}")

    def _is_oceanic_location(self, lat: float, lon: float) -> bool:
        """Check if coordinates are in oceanic region near India."""
        # Indian Ocean / Bay of Bengal / Arabian Sea approximate bounds
        return (
            (5 <= lat <= 25 and 60 <= lon <= 100) or  # Indian Ocean region
            (lat < 0 and 40 <= lon <= 110)  # Extended Indian Ocean
        )

    # =========================================================================
    # Hazard Detectors
    # =========================================================================

    async def _detect_hazards(
        self,
        location: MonitoredLocation,
        weather: Optional[WeatherParams],
        marine: Optional[MarineParams]
    ) -> List[HazardAlert]:
        """Run all hazard detectors and return generated alerts."""
        alerts = []

        # 1. Tsunami detection (earthquake-based)
        tsunami_alert = self._detect_tsunami(location)
        if tsunami_alert:
            alerts.append(tsunami_alert)

        # Weather-based detectors (only if weather data available)
        if weather:
            # 2. Cyclone detection
            cyclone_alert = self._detect_cyclone(location, weather)
            if cyclone_alert:
                alerts.append(cyclone_alert)

            # 3. High waves detection
            high_waves_alert = self._detect_high_waves(location, weather, marine)
            if high_waves_alert:
                alerts.append(high_waves_alert)

            # 4. Coastal flood detection
            flood_alert = self._detect_coastal_flood(location, weather, marine)
            if flood_alert:
                alerts.append(flood_alert)

            # 5. Rip currents detection
            rip_alert = self._detect_rip_currents(location, weather, marine)
            if rip_alert:
                alerts.append(rip_alert)

        return alerts

    def _detect_tsunami(self, location: MonitoredLocation) -> Optional[HazardAlert]:
        """
        Detect tsunami risk based on recent earthquakes.

        Thresholds (from PDF):
        - Magnitude >= 6.5
        - Depth <= 70 km
        - Oceanic location
        """
        thresholds = self.THRESHOLDS.tsunami

        for eq in self.recent_earthquakes:
            # Check if earthquake meets tsunami criteria
            if (eq.magnitude >= thresholds["earthquake_magnitude"] and
                eq.depth_km <= thresholds["earthquake_depth_km"] and
                (not thresholds["oceanic_only"] or eq.is_oceanic)):

                # Calculate distance to location
                distance = self._calculate_distance(
                    eq.coordinates.lat, eq.coordinates.lon,
                    location.coordinates.lat, location.coordinates.lon
                )

                # Only alert if within 3000km
                if distance > 3000:
                    continue

                # Determine alert level based on magnitude and distance
                if eq.magnitude >= 8.0 and distance < 1000:
                    alert_level = AlertLevel.CRITICAL
                elif eq.magnitude >= 7.5 or distance < 500:
                    alert_level = AlertLevel.WARNING
                elif eq.magnitude >= 7.0:
                    alert_level = AlertLevel.WATCH
                else:
                    alert_level = AlertLevel.ADVISORY

                return HazardAlert(
                    alert_id=f"tsunami_{location.location_id}_{uuid.uuid4().hex[:8]}",
                    hazard_type=HazardType.TSUNAMI,
                    alert_level=alert_level,
                    location_id=location.location_id,
                    location_name=location.name,
                    coordinates=location.coordinates,
                    detected_at=datetime.now(timezone.utc),
                    parameters={
                        "earthquake_magnitude": eq.magnitude,
                        "earthquake_depth_km": eq.depth_km,
                        "distance_km": round(distance, 1),
                        "epicenter": eq.location_description
                    },
                    detection_method=DetectionMethod.RULE_BASED,
                    confidence=min(0.95, 0.5 + eq.magnitude / 20),
                    source_earthquake_id=eq.earthquake_id,
                    recommendations=self._get_tsunami_recommendations(alert_level),
                    affected_population=location.population,
                    expires_at=datetime.now(timezone.utc) + timedelta(hours=6)
                )

        return None

    def _detect_cyclone(
        self,
        location: MonitoredLocation,
        weather: WeatherParams
    ) -> Optional[HazardAlert]:
        """
        Detect cyclone/depression conditions using IMD classification.

        IMD Wind-based Classification:
        - Depression: 31-49 kph
        - Deep Depression: 50-61 kph
        - Cyclonic Storm: 62-88 kph
        - Severe Cyclonic Storm: 89-117 kph
        - Very Severe Cyclonic Storm: 118-166 kph
        - Extremely Severe Cyclonic Storm: 167-221 kph
        - Super Cyclonic Storm: >221 kph

        Also considers:
        - Low pressure (< 1000 mb indicates system)
        - Heavy rainfall conditions
        - Active IMD cyclone bulletins (if available)
        """
        thresholds = self.THRESHOLDS.cyclone

        wind_kph = weather.wind_kph or 0
        pressure_mb = weather.pressure_mb or 1013
        gust_kph = weather.gust_kph or 0
        precip_mm = weather.precip_mm or 0

        # Check for active cyclone conditions
        # 1. Wind-based detection (Deep Depression and above)
        # 2. Pressure-based detection (< 1000 mb indicates system)
        # 3. Combined conditions (moderate wind + low pressure + heavy rain)
        # 4. Condition-based detection (thunderstorm + wind indicates cyclonic activity)
        is_cyclone_wind = wind_kph >= thresholds["wind_kph"]  # 50 kph = Deep Depression
        is_cyclone_pressure = pressure_mb < thresholds["pressure_mb"]  # < 1000 mb
        is_depression_conditions = (wind_kph >= 31 and pressure_mb < 1005 and precip_mm > 10)

        # Condition-based detection for cyclonic weather patterns
        # Catches situations where WeatherAPI shows cyclonic conditions but wind data lags
        is_condition_cyclonic = False
        if weather.condition:
            condition_lower = weather.condition.lower()
            cyclonic_conditions = [
                "thunder", "storm", "cyclone", "heavy rain",
                "torrential", "squally"
            ]
            is_condition_cyclonic = (
                any(c in condition_lower for c in cyclonic_conditions) and
                wind_kph >= 25 and  # At least moderate winds
                pressure_mb < 1010  # Slightly low pressure
            )

        is_cyclone = (
            is_cyclone_wind or
            is_cyclone_pressure or
            is_depression_conditions or
            is_condition_cyclonic
        )

        if not is_cyclone:
            return None

        # Determine IMD classification and alert level
        cyclone_category = self._classify_cyclone_imd(wind_kph, pressure_mb)

        # Map IMD category to alert level
        if cyclone_category in ["Super Cyclonic Storm", "Extremely Severe Cyclonic Storm"]:
            alert_level = AlertLevel.CRITICAL
        elif cyclone_category in ["Very Severe Cyclonic Storm", "Severe Cyclonic Storm"]:
            alert_level = AlertLevel.WARNING
        elif cyclone_category in ["Cyclonic Storm", "Deep Depression"]:
            alert_level = AlertLevel.WATCH
        else:  # Depression
            alert_level = AlertLevel.ADVISORY

        return HazardAlert(
            alert_id=f"cyclone_{location.location_id}_{uuid.uuid4().hex[:8]}",
            hazard_type=HazardType.CYCLONE,
            alert_level=alert_level,
            location_id=location.location_id,
            location_name=location.name,
            coordinates=location.coordinates,
            detected_at=datetime.now(timezone.utc),
            parameters={
                "wind_kph": wind_kph,
                "gust_kph": gust_kph,
                "pressure_mb": pressure_mb,
                "wind_direction": weather.wind_dir,
                "precipitation_mm": precip_mm,
                "imd_category": cyclone_category,
                "condition": weather.condition
            },
            detection_method=DetectionMethod.RULE_BASED,
            confidence=0.85 if wind_kph >= 62 else 0.70,  # Higher confidence for cyclonic storms
            weather_snapshot=weather,
            recommendations=self._get_cyclone_recommendations(alert_level, cyclone_category),
            affected_population=location.population,
            expires_at=datetime.now(timezone.utc) + timedelta(hours=12)
        )

    def _classify_cyclone_imd(self, wind_kph: float, pressure_mb: float) -> str:
        """Classify cyclone system using IMD standards."""
        # Wind-based classification (primary)
        if wind_kph >= 222:
            return "Super Cyclonic Storm"
        elif wind_kph >= 167:
            return "Extremely Severe Cyclonic Storm"
        elif wind_kph >= 118:
            return "Very Severe Cyclonic Storm"
        elif wind_kph >= 89:
            return "Severe Cyclonic Storm"
        elif wind_kph >= 62:
            return "Cyclonic Storm"
        elif wind_kph >= 50:
            return "Deep Depression"
        elif wind_kph >= 31:
            return "Depression"

        # Pressure-based fallback classification
        if pressure_mb < 950:
            return "Severe Cyclonic Storm"
        elif pressure_mb < 980:
            return "Cyclonic Storm"
        elif pressure_mb < 1000:
            return "Deep Depression"
        elif pressure_mb < 1005:
            return "Depression"

        return "Low Pressure Area"

    def _detect_high_waves(
        self,
        location: MonitoredLocation,
        weather: WeatherParams,
        marine: Optional[MarineParams]
    ) -> Optional[HazardAlert]:
        """
        Detect dangerous wave conditions.

        Thresholds (from PDF):
        - Significant wave height > 4.0m OR
        - Swell height > 3.0m
        """
        thresholds = self.THRESHOLDS.high_waves

        sig_ht = marine.sig_ht_mt if marine else 0
        swell_ht = marine.swell_ht_mt if marine else 0

        # Also consider high winds as wave indicator
        wind_kph = weather.wind_kph or 0
        estimated_wave_ht = wind_kph / 25  # Rough approximation

        effective_sig_ht = max(sig_ht or 0, estimated_wave_ht)

        is_high_waves = (
            effective_sig_ht > thresholds["sig_ht_mt"] or
            (swell_ht and swell_ht > thresholds["swell_ht_mt"])
        )

        if not is_high_waves:
            return None

        # Determine alert level
        max_wave = max(effective_sig_ht, swell_ht or 0)
        if max_wave > 8.0:
            alert_level = AlertLevel.CRITICAL
        elif max_wave > 6.0:
            alert_level = AlertLevel.WARNING
        elif max_wave > 5.0:
            alert_level = AlertLevel.WATCH
        else:
            alert_level = AlertLevel.ADVISORY

        return HazardAlert(
            alert_id=f"high_waves_{location.location_id}_{uuid.uuid4().hex[:8]}",
            hazard_type=HazardType.HIGH_WAVES,
            alert_level=alert_level,
            location_id=location.location_id,
            location_name=location.name,
            coordinates=location.coordinates,
            detected_at=datetime.now(timezone.utc),
            parameters={
                "significant_wave_height_m": round(effective_sig_ht, 1),
                "swell_height_m": swell_ht,
                "wind_kph": wind_kph
            },
            detection_method=DetectionMethod.RULE_BASED,
            confidence=0.80,
            weather_snapshot=weather,
            marine_snapshot=marine,
            recommendations=self._get_high_waves_recommendations(alert_level),
            affected_population=location.population // 10,  # Beach-goers estimate
            expires_at=datetime.now(timezone.utc) + timedelta(hours=6)
        )

    def _detect_coastal_flood(
        self,
        location: MonitoredLocation,
        weather: WeatherParams,
        marine: Optional[MarineParams]
    ) -> Optional[HazardAlert]:
        """
        Detect coastal flooding conditions.

        Triggers:
        1. Tide-based: Tide height > 3.5m AND Precipitation >= 20mm
        2. Rainfall-based: Heavy rain > 30mm (lowered for cyclone aftermath)
        3. Combined risk: Wind + rain + low pressure (storm surge proxy)

        IMD Rainfall Classification:
        - Light: < 15 mm
        - Moderate: 15-64 mm
        - Heavy: 64-115 mm
        - Very Heavy: 115-204 mm
        - Extremely Heavy: > 204 mm
        """
        thresholds = self.THRESHOLDS.coastal_flood

        tide_ht = marine.tide_height_mt if marine else 0
        precip = weather.precip_mm or 0
        wind_kph = weather.wind_kph or 0
        pressure_mb = weather.pressure_mb or 1013
        humidity = weather.humidity or 0

        # Calculate storm surge risk factor
        # Low pressure + high winds = higher surge risk
        surge_factor = 0
        if pressure_mb < 1000:
            surge_factor += (1000 - pressure_mb) / 50  # Up to 1.0 for 950mb
        if wind_kph > 40:
            surge_factor += wind_kph / 200  # Up to 0.5 for 100kph

        # Consider high wind + rain as flood risk
        wind_factor = wind_kph / 100
        effective_tide = (tide_ht or 0) + wind_factor + surge_factor

        # Multiple flood detection conditions
        is_tidal_flood = (
            effective_tide > thresholds["tide_height_mt"] and
            precip >= thresholds["precip_mm"]
        )

        # Rainfall-based flood detection (IMD classification)
        # Lowered threshold to 30mm to catch heavy rainfall from cyclone systems
        is_heavy_rain_flood = precip > 30

        # Storm surge risk (cyclone-induced)
        is_storm_surge_risk = (
            pressure_mb < 1000 and  # Low pressure system
            wind_kph > 40 and  # Significant winds
            precip > 15  # Some rainfall
        )

        # High humidity with moderate rain indicates saturated conditions
        is_saturated_flood = (
            humidity > 85 and
            precip > 20 and
            (weather.condition and any(word in weather.condition.lower()
                for word in ["rain", "thunder", "storm", "shower"]))
        )

        # Condition-based detection (WeatherAPI sometimes shows condition but low precip values)
        # This catches situations like "Heavy rain with thunder" where API data lags
        is_condition_based_flood = (
            weather.condition and
            any(phrase in weather.condition.lower() for phrase in [
                "heavy rain", "torrential", "flood", "thunder",
                "moderate or heavy rain", "downpour"
            ]) and
            humidity > 80  # High humidity confirms wet conditions
        )

        if not (is_tidal_flood or is_heavy_rain_flood or is_storm_surge_risk or is_saturated_flood or is_condition_based_flood):
            return None

        # If detected via condition but precip is low, estimate from condition
        if is_condition_based_flood and precip < 10:
            if "heavy" in weather.condition.lower():
                precip = 40  # Estimate heavy rain
            elif "moderate" in weather.condition.lower():
                precip = 25  # Estimate moderate rain

        # Determine alert level based on IMD rainfall classification
        if precip > 115 or effective_tide > 5.0:  # Very Heavy rainfall
            alert_level = AlertLevel.CRITICAL
            flood_type = "Very Heavy Rainfall Flood"
        elif precip > 64 or effective_tide > 4.5:  # Heavy rainfall
            alert_level = AlertLevel.WARNING
            flood_type = "Heavy Rainfall Flood"
        elif precip > 30 or effective_tide > 4.0:  # Moderate to Heavy
            alert_level = AlertLevel.WATCH
            flood_type = "Moderate Rainfall Flood Risk"
        else:
            alert_level = AlertLevel.ADVISORY
            flood_type = "Flood Watch"

        return HazardAlert(
            alert_id=f"flood_{location.location_id}_{uuid.uuid4().hex[:8]}",
            hazard_type=HazardType.COASTAL_FLOOD,
            alert_level=alert_level,
            location_id=location.location_id,
            location_name=location.name,
            coordinates=location.coordinates,
            detected_at=datetime.now(timezone.utc),
            parameters={
                "precipitation_mm": precip,
                "tide_height_m": tide_ht,
                "effective_tide_m": round(effective_tide, 1),
                "storm_surge_factor": round(surge_factor, 2),
                "humidity": humidity,
                "pressure_mb": pressure_mb,
                "flood_type": flood_type,
                "condition": weather.condition
            },
            detection_method=DetectionMethod.RULE_BASED,
            confidence=0.80 if precip > 50 else 0.70,
            weather_snapshot=weather,
            marine_snapshot=marine,
            recommendations=self._get_flood_recommendations(alert_level),
            affected_population=location.population // 5,  # Low-lying areas
            expires_at=datetime.now(timezone.utc) + timedelta(hours=12)
        )

    def _detect_rip_currents(
        self,
        location: MonitoredLocation,
        weather: WeatherParams,
        marine: Optional[MarineParams]
    ) -> Optional[HazardAlert]:
        """
        Detect rip current conditions.

        Thresholds (from PDF):
        - Swell period > 14 seconds AND
        - Significant wave height > 2.5m
        """
        thresholds = self.THRESHOLDS.rip_currents

        swell_period = marine.swell_period_secs if marine else 0
        sig_ht = marine.sig_ht_mt if marine else 0

        # Use wind as proxy for wave height if marine data unavailable
        if not sig_ht and weather.wind_kph:
            sig_ht = weather.wind_kph / 25

        # Estimate swell period from wind persistence (rough approximation)
        if not swell_period and weather.wind_kph and weather.wind_kph > 30:
            swell_period = 10 + (weather.wind_kph - 30) / 10

        is_rip_current_risk = (
            (swell_period or 0) > thresholds["swell_period_secs"] and
            (sig_ht or 0) > thresholds["sig_ht_mt"]
        )

        if not is_rip_current_risk:
            return None

        # Determine alert level
        if sig_ht > 4.0 and swell_period > 18:
            alert_level = AlertLevel.WARNING
        elif sig_ht > 3.5 or swell_period > 16:
            alert_level = AlertLevel.WATCH
        else:
            alert_level = AlertLevel.ADVISORY

        return HazardAlert(
            alert_id=f"rip_{location.location_id}_{uuid.uuid4().hex[:8]}",
            hazard_type=HazardType.RIP_CURRENTS,
            alert_level=alert_level,
            location_id=location.location_id,
            location_name=location.name,
            coordinates=location.coordinates,
            detected_at=datetime.now(timezone.utc),
            parameters={
                "swell_period_secs": swell_period,
                "significant_wave_height_m": round(sig_ht, 1),
                "swell_direction": marine.swell_dir if marine else None
            },
            detection_method=DetectionMethod.RULE_BASED,
            confidence=0.70,
            weather_snapshot=weather,
            marine_snapshot=marine,
            recommendations=self._get_rip_current_recommendations(alert_level),
            affected_population=location.population // 20,  # Swimmers estimate
            expires_at=datetime.now(timezone.utc) + timedelta(hours=6)
        )

    # =========================================================================
    # Alert Management
    # =========================================================================

    def _update_location_alerts(
        self,
        location_id: str,
        new_alerts: List[HazardAlert],
        weather: Optional[WeatherParams],
        marine: Optional[MarineParams]
    ):
        """Update alerts and status for a location."""
        # Remove expired alerts
        now = datetime.now(timezone.utc)
        self.active_alerts[location_id] = [
            alert for alert in self.active_alerts[location_id]
            if alert.expires_at and alert.expires_at > now
        ]

        # Add new alerts (avoid duplicates by hazard type)
        existing_types = {a.hazard_type for a in self.active_alerts[location_id]}
        for alert in new_alerts:
            if alert.hazard_type not in existing_types:
                self.active_alerts[location_id].append(alert)

        # Update location status
        all_alerts = self.active_alerts[location_id]
        max_level = max(
            (a.alert_level for a in all_alerts),
            default=AlertLevel.NORMAL
        )

        # Calculate weather hazard score
        weather_score = self._calculate_weather_score(weather, marine)

        location = self.MONITORED_LOCATIONS[location_id]
        self.location_status[location_id] = LocationStatus(
            location_id=location_id,
            location_name=location.name,
            country=location.country,
            coordinates=location.coordinates,
            max_alert_level=max_level,
            active_hazards=all_alerts,
            weather=weather,
            marine=marine,
            last_updated=now,
            recommendations=self._get_location_recommendations(all_alerts),
            weather_score=weather_score
        )

    def _calculate_weather_score(
        self,
        weather: Optional[WeatherParams],
        marine: Optional[MarineParams]
    ) -> int:
        """Calculate overall weather hazard score (0-100)."""
        if not weather:
            return 0

        score = 0

        # Wind contribution (max 30 points)
        wind = weather.wind_kph or 0
        score += min(30, wind / 3)

        # Precipitation contribution (max 25 points)
        precip = weather.precip_mm or 0
        score += min(25, precip / 4)

        # Pressure contribution (max 20 points)
        pressure = weather.pressure_mb or 1013
        if pressure < 1000:
            score += min(20, (1000 - pressure) / 3)

        # Wave contribution (max 25 points)
        if marine and marine.sig_ht_mt:
            score += min(25, marine.sig_ht_mt * 5)

        return min(100, int(score))

    def _get_location_recommendations(
        self,
        alerts: List[HazardAlert]
    ) -> List[str]:
        """Get combined recommendations for a location."""
        if not alerts:
            return ["No active hazards. Normal coastal activities permitted."]

        recommendations = []
        for alert in sorted(alerts, key=lambda a: -a.alert_level):
            recommendations.extend(alert.recommendations[:2])

        return list(dict.fromkeys(recommendations))[:5]

    # =========================================================================
    # Recommendations
    # =========================================================================

    def _get_tsunami_recommendations(self, level: AlertLevel) -> List[str]:
        """Get tsunami-specific recommendations."""
        if level >= AlertLevel.CRITICAL:
            return [
                "IMMEDIATE EVACUATION to higher ground (30m+)",
                "Move inland at least 2km from coast",
                "Do NOT return until official all-clear",
                "Follow emergency broadcast instructions"
            ]
        elif level >= AlertLevel.WARNING:
            return [
                "Prepare for possible evacuation",
                "Move away from beaches and low-lying areas",
                "Monitor official emergency channels",
                "Have emergency supplies ready"
            ]
        else:
            return [
                "Stay alert for updates",
                "Know your evacuation routes",
                "Avoid coastal areas until further notice"
            ]

    def _get_cyclone_recommendations(self, level: AlertLevel, imd_category: str = None) -> List[str]:
        """Get cyclone-specific recommendations based on IMD classification."""
        category_info = f" ({imd_category})" if imd_category else ""

        if level >= AlertLevel.CRITICAL:
            return [
                f"CRITICAL{category_info}: Take shelter in sturdy building immediately",
                "Stay away from windows and doors",
                "Do NOT go outside under any circumstances",
                "Stock emergency supplies and water",
                "Follow evacuation orders from authorities"
            ]
        elif level >= AlertLevel.WARNING:
            return [
                f"WARNING{category_info}: Secure loose outdoor objects",
                "Stock up on food, water, and medicines",
                "Charge phones and emergency devices",
                "Prepare for possible power outages",
                "Avoid coastal areas and low-lying regions"
            ]
        elif level >= AlertLevel.WATCH:
            return [
                f"WATCH{category_info}: Monitor weather updates closely",
                "Avoid unnecessary coastal travel",
                "Keep emergency contacts handy",
                "Secure outdoor furniture and equipment"
            ]
        else:  # ADVISORY - Depression
            return [
                f"ADVISORY{category_info}: Heavy rainfall expected",
                "Avoid waterlogged areas",
                "Monitor local weather updates",
                "Be prepared for potential flooding"
            ]

    def _get_high_waves_recommendations(self, level: AlertLevel) -> List[str]:
        """Get high waves recommendations."""
        if level >= AlertLevel.WARNING:
            return [
                "Beach activities strictly prohibited",
                "Fishing boats should NOT venture out",
                "Stay away from coastal rocks and jetties",
                "Beware of sneaker waves"
            ]
        else:
            return [
                "Exercise caution near shoreline",
                "Avoid swimming and water sports",
                "Keep safe distance from breaking waves"
            ]

    def _get_flood_recommendations(self, level: AlertLevel) -> List[str]:
        """Get coastal flood recommendations."""
        if level >= AlertLevel.WARNING:
            return [
                "Evacuate low-lying coastal areas",
                "Move vehicles to higher ground",
                "Do NOT walk or drive through floodwater",
                "Turn off electricity if water enters home"
            ]
        else:
            return [
                "Avoid low-lying areas near coast",
                "Monitor drainage and water levels",
                "Keep emergency contacts ready"
            ]

    def _get_rip_current_recommendations(self, level: AlertLevel) -> List[str]:
        """Get rip current recommendations."""
        return [
            "Do NOT swim at unguarded beaches",
            "If caught in rip current, swim parallel to shore",
            "Never swim alone",
            "Observe warning flags at beaches",
            "Stay in shallow water only"
        ]

    # =========================================================================
    # Utilities
    # =========================================================================

    def _calculate_distance(
        self,
        lat1: float, lon1: float,
        lat2: float, lon2: float
    ) -> float:
        """Calculate distance between two points in km (Haversine formula)."""
        from math import radians, sin, cos, sqrt, atan2

        R = 6371  # Earth's radius in km

        lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
        dlat = lat2 - lat1
        dlon = lon2 - lon1

        a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
        c = 2 * atan2(sqrt(a), sqrt(1-a))

        return R * c

    # =========================================================================
    # Public API Methods
    # =========================================================================

    def get_all_status(self) -> MultiHazardResponse:
        """Get complete monitoring status."""
        all_alerts = []
        for alerts in self.active_alerts.values():
            all_alerts.extend(alerts)

        # Count by type and level
        hazard_counts = {ht: 0 for ht in HazardType}
        level_counts = {AlertLevel.CRITICAL: 0, AlertLevel.WARNING: 0, AlertLevel.WATCH: 0}

        for alert in all_alerts:
            hazard_counts[alert.hazard_type] = hazard_counts.get(alert.hazard_type, 0) + 1
            if alert.alert_level in level_counts:
                level_counts[alert.alert_level] += 1

        summary = MultiHazardSummary(
            total_locations=len(self.MONITORED_LOCATIONS),
            active_alerts_count=len(all_alerts),
            critical_alerts=level_counts[AlertLevel.CRITICAL],
            warning_alerts=level_counts[AlertLevel.WARNING],
            watch_alerts=level_counts[AlertLevel.WATCH],
            tsunami_alerts=hazard_counts.get(HazardType.TSUNAMI, 0),
            cyclone_alerts=hazard_counts.get(HazardType.CYCLONE, 0),
            high_waves_alerts=hazard_counts.get(HazardType.HIGH_WAVES, 0),
            coastal_flood_alerts=hazard_counts.get(HazardType.COASTAL_FLOOD, 0),
            rip_current_alerts=hazard_counts.get(HazardType.RIP_CURRENTS, 0),
            recent_earthquakes=len(self.recent_earthquakes),
            last_detection_cycle=self.last_detection_cycle or datetime.now(timezone.utc),
            next_detection_cycle=self.next_detection_cycle or datetime.now(timezone.utc),
            is_monitoring_active=self.is_monitoring
        )

        return MultiHazardResponse(
            locations=self.location_status,
            summary=summary,
            recent_earthquakes=self.recent_earthquakes,
            global_alerts=sorted(all_alerts, key=lambda a: -a.alert_level)
        )

    def get_location_status(self, location_id: str) -> Optional[LocationStatus]:
        """Get status for a specific location."""
        return self.location_status.get(location_id)

    def get_active_alerts(
        self,
        location_id: Optional[str] = None,
        hazard_type: Optional[HazardType] = None,
        min_level: AlertLevel = AlertLevel.NORMAL
    ) -> List[HazardAlert]:
        """Get filtered active alerts."""
        alerts = []

        locations = [location_id] if location_id else self.active_alerts.keys()

        for loc_id in locations:
            for alert in self.active_alerts.get(loc_id, []):
                if hazard_type and alert.hazard_type != hazard_type:
                    continue
                if alert.alert_level < min_level:
                    continue
                alerts.append(alert)

        return sorted(alerts, key=lambda a: -a.alert_level)

    def inject_demo_alerts(self) -> List[HazardAlert]:
        """
        Inject simulated demo alerts for testing/demonstration purposes.
        Creates realistic alerts for various coastal locations.
        """
        import random

        demo_alerts = []

        # Cyclone warning for Chennai
        if "chennai" in self.MONITORED_LOCATIONS:
            alert = HazardAlert(
                alert_id=f"demo_cyclone_chennai_{uuid.uuid4().hex[:8]}",
                hazard_type=HazardType.CYCLONE,
                alert_level=AlertLevel.WARNING,
                location_id="chennai",
                location_name="Chennai",
                coordinates=self.MONITORED_LOCATIONS["chennai"].coordinates,
                detected_at=datetime.now(timezone.utc),
                parameters={
                    "wind_kph": 95,
                    "gust_kph": 120,
                    "pressure_mb": 978,
                    "wind_direction": "NE"
                },
                detection_method=DetectionMethod.RULE_BASED,
                confidence=0.88,
                recommendations=[
                    "Secure loose objects and stay indoors",
                    "Avoid coastal areas until further notice",
                    "Keep emergency supplies ready"
                ],
                affected_population=7088000,
                expires_at=datetime.now(timezone.utc) + timedelta(hours=12)
            )
            demo_alerts.append(alert)
            self.active_alerts["chennai"].append(alert)

        # High waves alert for Mumbai
        if "mumbai" in self.MONITORED_LOCATIONS:
            alert = HazardAlert(
                alert_id=f"demo_waves_mumbai_{uuid.uuid4().hex[:8]}",
                hazard_type=HazardType.HIGH_WAVES,
                alert_level=AlertLevel.WATCH,
                location_id="mumbai",
                location_name="Mumbai",
                coordinates=self.MONITORED_LOCATIONS["mumbai"].coordinates,
                detected_at=datetime.now(timezone.utc),
                parameters={
                    "significant_wave_height_m": 4.5,
                    "swell_height_m": 3.2,
                    "wind_kph": 65
                },
                detection_method=DetectionMethod.RULE_BASED,
                confidence=0.82,
                recommendations=[
                    "Avoid swimming and water sports",
                    "Fishing boats should remain in harbor",
                    "Stay away from rocky coastlines"
                ],
                affected_population=1244237,
                expires_at=datetime.now(timezone.utc) + timedelta(hours=6)
            )
            demo_alerts.append(alert)
            self.active_alerts["mumbai"].append(alert)

        # Coastal flood warning for Kolkata
        if "kolkata" in self.MONITORED_LOCATIONS:
            alert = HazardAlert(
                alert_id=f"demo_flood_kolkata_{uuid.uuid4().hex[:8]}",
                hazard_type=HazardType.COASTAL_FLOOD,
                alert_level=AlertLevel.CRITICAL,
                location_id="kolkata",
                location_name="Kolkata",
                coordinates=self.MONITORED_LOCATIONS["kolkata"].coordinates,
                detected_at=datetime.now(timezone.utc),
                parameters={
                    "tide_height_m": 4.2,
                    "precipitation_mm": 45,
                    "storm_surge_m": 1.8
                },
                detection_method=DetectionMethod.RULE_BASED,
                confidence=0.91,
                recommendations=[
                    "EVACUATE low-lying coastal areas immediately",
                    "Move to higher ground",
                    "Do not attempt to cross flooded areas"
                ],
                affected_population=4496694,
                expires_at=datetime.now(timezone.utc) + timedelta(hours=8)
            )
            demo_alerts.append(alert)
            self.active_alerts["kolkata"].append(alert)

        # Rip currents for Goa
        if "goa" in self.MONITORED_LOCATIONS:
            alert = HazardAlert(
                alert_id=f"demo_rip_goa_{uuid.uuid4().hex[:8]}",
                hazard_type=HazardType.RIP_CURRENTS,
                alert_level=AlertLevel.ADVISORY,
                location_id="goa",
                location_name="Goa",
                coordinates=self.MONITORED_LOCATIONS["goa"].coordinates,
                detected_at=datetime.now(timezone.utc),
                parameters={
                    "swell_period_secs": 15,
                    "significant_wave_height_m": 2.8,
                    "beach_slope": "moderate"
                },
                detection_method=DetectionMethod.RULE_BASED,
                confidence=0.75,
                recommendations=[
                    "Swim only at lifeguard-patrolled beaches",
                    "If caught in rip current, swim parallel to shore",
                    "Supervise children closely near water"
                ],
                affected_population=145854,
                expires_at=datetime.now(timezone.utc) + timedelta(hours=4)
            )
            demo_alerts.append(alert)
            self.active_alerts["goa"].append(alert)

        # High waves for Visakhapatnam
        if "visakhapatnam" in self.MONITORED_LOCATIONS:
            alert = HazardAlert(
                alert_id=f"demo_waves_vizag_{uuid.uuid4().hex[:8]}",
                hazard_type=HazardType.HIGH_WAVES,
                alert_level=AlertLevel.WARNING,
                location_id="visakhapatnam",
                location_name="Visakhapatnam",
                coordinates=self.MONITORED_LOCATIONS["visakhapatnam"].coordinates,
                detected_at=datetime.now(timezone.utc),
                parameters={
                    "significant_wave_height_m": 5.8,
                    "swell_height_m": 4.1,
                    "wind_kph": 78
                },
                detection_method=DetectionMethod.RULE_BASED,
                confidence=0.86,
                recommendations=[
                    "All fishing operations suspended",
                    "Coastal evacuation may be required",
                    "Monitor official updates"
                ],
                affected_population=2035922,
                expires_at=datetime.now(timezone.utc) + timedelta(hours=8)
            )
            demo_alerts.append(alert)
            self.active_alerts["visakhapatnam"].append(alert)

        # Update location statuses
        for alert in demo_alerts:
            loc_id = alert.location_id
            if loc_id in self.location_status:
                status = self.location_status[loc_id]
                status.active_hazards.append({
                    "hazard_type": alert.hazard_type.value,
                    "alert_level": alert.alert_level,
                    "detected_at": alert.detected_at.isoformat()
                })
                if alert.alert_level > status.max_alert_level:
                    status.max_alert_level = alert.alert_level
                status.last_updated = datetime.now(timezone.utc)

        logger.info(f"Injected {len(demo_alerts)} demo alerts for testing")
        return demo_alerts

    def clear_demo_alerts(self):
        """Clear all demo alerts."""
        for loc_id in self.active_alerts:
            self.active_alerts[loc_id] = [
                a for a in self.active_alerts[loc_id]
                if not a.alert_id.startswith("demo_")
            ]
            # Reset location status
            if loc_id in self.location_status:
                status = self.location_status[loc_id]
                status.active_hazards = []
                status.max_alert_level = AlertLevel.NORMAL
                status.last_updated = datetime.now(timezone.utc)

        logger.info("Cleared all demo alerts")


# Singleton instance
_multi_hazard_service: Optional[MultiHazardService] = None


def get_multi_hazard_service() -> MultiHazardService:
    """Get MultiHazard service instance."""
    global _multi_hazard_service
    if _multi_hazard_service is None:
        _multi_hazard_service = MultiHazardService()
    return _multi_hazard_service


async def initialize_multi_hazard_service() -> MultiHazardService:
    """Initialize MultiHazard service."""
    service = get_multi_hazard_service()
    await service.initialize()
    return service
