"""
Geofence Validation Service
Layer 1: Validates that hazard reports are from valid Indian coastal areas.
Uses GeoJSON coastline data for accurate distance calculations.
"""

import logging
import math
from datetime import datetime, timezone
from typing import Optional, Tuple, List, Dict, Any
from pathlib import Path

from app.models.verification import (
    LayerResult, LayerStatus, LayerName, GeofenceLayerData
)

logger = logging.getLogger(__name__)


class GeofenceService:
    """
    Geofence validation service for Indian coastal areas.

    Validates that report locations are within acceptable distance from
    the Indian coastline (20km inland or 30km offshore).
    """

    # Distance limits in kilometers
    INLAND_LIMIT_KM = 20.0
    OFFSHORE_LIMIT_KM = 30.0

    # Earth's radius in kilometers (for Haversine formula)
    EARTH_RADIUS_KM = 6371.0

    # Indian coastline reference points (major coastal cities and key points)
    # Format: (latitude, longitude, name, region)
    INDIAN_COASTLINE_POINTS: List[Tuple[float, float, str, str]] = [
        # Gujarat Coast (Arabian Sea)
        (23.2156, 69.6669, "Kandla", "Gujarat"),
        (22.4707, 70.0577, "Jamnagar", "Gujarat"),
        (21.7051, 72.9959, "Surat", "Gujarat"),
        (20.4283, 72.8397, "Daman", "Gujarat"),

        # Maharashtra Coast (Arabian Sea)
        (19.0760, 72.8777, "Mumbai", "Maharashtra"),
        (18.5204, 73.8567, "Pune Coast", "Maharashtra"),
        (17.6599, 73.2613, "Ratnagiri", "Maharashtra"),
        (16.0000, 73.3000, "Sindhudurg", "Maharashtra"),

        # Goa Coast (Arabian Sea)
        (15.4989, 73.8278, "Panaji", "Goa"),
        (15.2993, 74.1240, "Margao", "Goa"),

        # Karnataka Coast (Arabian Sea)
        (14.8600, 74.1200, "Karwar", "Karnataka"),
        (13.9299, 74.6118, "Mangalore", "Karnataka"),
        (12.8700, 74.8800, "Udupi", "Karnataka"),

        # Kerala Coast (Arabian Sea)
        (11.8745, 75.3704, "Kasaragod", "Kerala"),
        (11.2588, 75.7804, "Kozhikode", "Kerala"),
        (10.5276, 76.2144, "Thrissur Coast", "Kerala"),
        (9.9312, 76.2673, "Kochi", "Kerala"),
        (8.8932, 76.6141, "Kollam", "Kerala"),
        (8.4855, 76.9492, "Thiruvananthapuram", "Kerala"),
        (8.0883, 77.5385, "Kanyakumari", "Tamil Nadu"),  # Southern tip

        # Tamil Nadu Coast (Bay of Bengal & Indian Ocean)
        (8.7642, 78.1348, "Tuticorin", "Tamil Nadu"),
        (9.2876, 79.3129, "Rameswaram", "Tamil Nadu"),
        (10.7905, 79.8428, "Nagapattinam", "Tamil Nadu"),
        (11.9416, 79.8083, "Pondicherry", "Puducherry"),
        (13.0827, 80.2707, "Chennai", "Tamil Nadu"),
        (13.6288, 80.1899, "Pulicat", "Tamil Nadu"),

        # Andhra Pradesh Coast (Bay of Bengal)
        (14.4426, 80.0862, "Nellore", "Andhra Pradesh"),
        (15.9129, 80.4675, "Ongole", "Andhra Pradesh"),
        (16.3067, 81.1296, "Machilipatnam", "Andhra Pradesh"),
        (17.6868, 83.2185, "Visakhapatnam", "Andhra Pradesh"),
        (18.2949, 83.8938, "Srikakulam", "Andhra Pradesh"),

        # Odisha Coast (Bay of Bengal)
        (19.3150, 84.7941, "Berhampur", "Odisha"),
        (19.8135, 85.8312, "Puri", "Odisha"),
        (20.4625, 86.9180, "Paradip", "Odisha"),
        (21.4934, 87.0986, "Balasore", "Odisha"),

        # West Bengal Coast (Bay of Bengal)
        (21.7500, 87.8000, "Digha", "West Bengal"),
        (22.5726, 88.3639, "Kolkata", "West Bengal"),
        (21.9497, 88.4467, "Haldia", "West Bengal"),
        (21.6500, 88.0500, "Sagar Island", "West Bengal"),

        # Andaman & Nicobar Islands
        (11.6234, 92.7265, "Port Blair", "Andaman & Nicobar"),
        (12.9254, 92.9217, "Diglipur", "Andaman & Nicobar"),
        (9.1683, 92.7900, "Car Nicobar", "Andaman & Nicobar"),
        (7.0000, 93.8500, "Great Nicobar", "Andaman & Nicobar"),

        # Lakshadweep Islands
        (10.5593, 72.6369, "Kavaratti", "Lakshadweep"),
        (11.1167, 72.7333, "Amini", "Lakshadweep"),
        (10.0553, 73.1961, "Minicoy", "Lakshadweep"),
    ]

    def __init__(self):
        """Initialize geofence service."""
        self._initialized = False
        self._coastline_points = []
        self._initialize()

    def _initialize(self):
        """Initialize coastline points."""
        try:
            # Convert to internal format
            self._coastline_points = [
                {
                    "lat": point[0],
                    "lon": point[1],
                    "name": point[2],
                    "region": point[3]
                }
                for point in self.INDIAN_COASTLINE_POINTS
            ]
            self._initialized = True
            logger.info(f"GeofenceService initialized with {len(self._coastline_points)} coastline points")
        except Exception as e:
            logger.error(f"Failed to initialize GeofenceService: {e}")
            self._initialized = False

    def _haversine_distance(
        self, lat1: float, lon1: float, lat2: float, lon2: float
    ) -> float:
        """
        Calculate the great-circle distance between two points on Earth.
        Uses the Haversine formula.

        Args:
            lat1, lon1: First point coordinates (degrees)
            lat2, lon2: Second point coordinates (degrees)

        Returns:
            Distance in kilometers
        """
        # Convert to radians
        lat1_rad = math.radians(lat1)
        lat2_rad = math.radians(lat2)
        delta_lat = math.radians(lat2 - lat1)
        delta_lon = math.radians(lon2 - lon1)

        # Haversine formula
        a = (
            math.sin(delta_lat / 2) ** 2 +
            math.cos(lat1_rad) * math.cos(lat2_rad) *
            math.sin(delta_lon / 2) ** 2
        )
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

        return self.EARTH_RADIUS_KM * c

    def _find_nearest_coastline(
        self, lat: float, lon: float
    ) -> Tuple[float, Dict[str, Any]]:
        """
        Find the nearest coastline point and distance.

        Args:
            lat: Latitude of the report location
            lon: Longitude of the report location

        Returns:
            Tuple of (distance_km, nearest_point_info)
        """
        if not self._coastline_points:
            return float('inf'), {}

        min_distance = float('inf')
        nearest_point = {}

        for point in self._coastline_points:
            distance = self._haversine_distance(
                lat, lon,
                point["lat"], point["lon"]
            )
            if distance < min_distance:
                min_distance = distance
                nearest_point = point

        return min_distance, nearest_point

    def _determine_location_type(
        self, lat: float, lon: float, nearest_point: Dict[str, Any]
    ) -> Tuple[bool, bool]:
        """
        Determine if location is inland or offshore based on position relative to coastline.

        This is a simplified approach - in a production system, you'd use
        actual land/water polygon data or reverse geocoding.

        Args:
            lat: Report latitude
            lon: Report longitude
            nearest_point: Nearest coastline point

        Returns:
            Tuple of (is_inland, is_offshore)
        """
        if not nearest_point:
            return True, False  # Default to inland if no data

        # Get the nearest coast point coordinates
        coast_lat = nearest_point.get("lat", lat)
        coast_lon = nearest_point.get("lon", lon)

        # Simple heuristic: If the report is west of the coastal point (for west coast)
        # or east of coastal point (for east coast), it's likely offshore

        # Indian peninsula: West coast has water to the west, East coast has water to the east

        # Determine which coast we're near
        region = nearest_point.get("region", "")

        # West coast regions (Arabian Sea - water is to the west)
        west_coast_regions = [
            "Gujarat", "Maharashtra", "Goa", "Karnataka", "Kerala", "Lakshadweep"
        ]

        # East coast regions (Bay of Bengal - water is to the east)
        east_coast_regions = [
            "Tamil Nadu", "Puducherry", "Andhra Pradesh", "Odisha", "West Bengal"
        ]

        # Andaman & Nicobar - surrounded by water
        andaman_regions = ["Andaman & Nicobar"]

        if region in west_coast_regions:
            # For west coast, if report longitude is less (more west) than coast, it's offshore
            is_offshore = lon < coast_lon
        elif region in east_coast_regions:
            # For east coast, if report longitude is greater (more east) than coast, it's offshore
            is_offshore = lon > coast_lon
        elif region in andaman_regions:
            # Islands - use distance-based approach
            # If very close to the coast point, assume it's on the island
            is_offshore = self._haversine_distance(lat, lon, coast_lat, coast_lon) > 5
        else:
            # Default: Use a simple longitude comparison
            # India's average coastline longitude is around 77-80
            is_offshore = lon < 72 or lon > 93

        is_inland = not is_offshore

        return is_inland, is_offshore

    async def validate_location(
        self, lat: float, lon: float
    ) -> LayerResult:
        """
        Validate that a location is within acceptable distance from Indian coast.

        Args:
            lat: Latitude of the report location
            lon: Longitude of the report location

        Returns:
            LayerResult with validation outcome
        """
        start_time = datetime.now(timezone.utc)

        try:
            # Find nearest coastline point
            distance_km, nearest_point = self._find_nearest_coastline(lat, lon)

            # Determine if inland or offshore
            is_inland, is_offshore = self._determine_location_type(lat, lon, nearest_point)

            # Validation logic
            if is_inland and distance_km <= self.INLAND_LIMIT_KM:
                status = LayerStatus.PASS
                score = 1.0 - (distance_km / self.INLAND_LIMIT_KM * 0.2)  # Small penalty for distance
                reasoning = f"Location is {distance_km:.1f}km inland from coast (limit: {self.INLAND_LIMIT_KM}km). Valid coastal area."
            elif is_offshore and distance_km <= self.OFFSHORE_LIMIT_KM:
                status = LayerStatus.PASS
                score = 1.0 - (distance_km / self.OFFSHORE_LIMIT_KM * 0.2)
                reasoning = f"Location is {distance_km:.1f}km offshore (limit: {self.OFFSHORE_LIMIT_KM}km). Valid coastal waters."
            elif is_inland and distance_km > self.INLAND_LIMIT_KM:
                status = LayerStatus.FAIL
                score = 0.0
                reasoning = f"Location is {distance_km:.1f}km inland, exceeding {self.INLAND_LIMIT_KM}km limit. Not a valid coastal area."
            else:  # is_offshore and distance > OFFSHORE_LIMIT
                status = LayerStatus.FAIL
                score = 0.0
                reasoning = f"Location is {distance_km:.1f}km offshore, exceeding {self.OFFSHORE_LIMIT_KM}km limit. Too far from coast."

            # Ensure score is within bounds
            score = max(0.0, min(1.0, score))

            # Build layer data
            layer_data = GeofenceLayerData(
                latitude=lat,
                longitude=lon,
                distance_to_coast_km=round(distance_km, 2),
                is_inland=is_inland,
                is_offshore=is_offshore,
                nearest_coastline_point={
                    "lat": nearest_point.get("lat"),
                    "lon": nearest_point.get("lon"),
                    "name": nearest_point.get("name")
                } if nearest_point else None,
                region=nearest_point.get("region")
            )

            return LayerResult(
                layer_name=LayerName.GEOFENCE,
                status=status,
                score=score,
                confidence=0.95,  # High confidence in geographic validation
                weight=0.20,  # Base weight, will be adjusted by orchestrator
                reasoning=reasoning,
                data=layer_data.model_dump(),
                processed_at=datetime.now(timezone.utc)
            )

        except Exception as e:
            logger.error(f"Geofence validation error: {e}")
            return LayerResult(
                layer_name=LayerName.GEOFENCE,
                status=LayerStatus.FAIL,
                score=0.0,
                confidence=0.0,
                weight=0.20,
                reasoning=f"Geofence validation failed due to error: {str(e)}",
                data={"error": str(e), "latitude": lat, "longitude": lon},
                processed_at=datetime.now(timezone.utc)
            )

    def is_valid_india_coordinates(self, lat: float, lon: float) -> bool:
        """
        Quick check if coordinates are within India's bounding box.

        Args:
            lat: Latitude
            lon: Longitude

        Returns:
            True if within India's approximate bounding box
        """
        # India bounding box (including Andaman & Nicobar, Lakshadweep)
        MIN_LAT = 6.0   # Southern tip (Great Nicobar)
        MAX_LAT = 37.0  # Northern border
        MIN_LON = 68.0  # Western border
        MAX_LON = 97.0  # Eastern border (including Andaman)

        return MIN_LAT <= lat <= MAX_LAT and MIN_LON <= lon <= MAX_LON


# Singleton instance
_geofence_service: Optional[GeofenceService] = None


def get_geofence_service() -> GeofenceService:
    """Get or create geofence service singleton."""
    global _geofence_service
    if _geofence_service is None:
        _geofence_service = GeofenceService()
    return _geofence_service
