"""
Open-Meteo Marine API Service
Free marine weather data - no API key required
https://open-meteo.com/en/docs/marine-weather-api
"""

import httpx
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class MarineConditions:
    """Marine weather conditions data"""
    latitude: float
    longitude: float
    timestamp: datetime

    # Wave data
    wave_height: Optional[float] = None  # meters
    wave_direction: Optional[float] = None  # degrees
    wave_period: Optional[float] = None  # seconds

    # Swell data
    swell_wave_height: Optional[float] = None  # meters
    swell_wave_direction: Optional[float] = None  # degrees
    swell_wave_period: Optional[float] = None  # seconds

    # Wind wave data
    wind_wave_height: Optional[float] = None  # meters
    wind_wave_direction: Optional[float] = None  # degrees
    wind_wave_period: Optional[float] = None  # seconds

    # Ocean data
    ocean_current_velocity: Optional[float] = None  # m/s
    ocean_current_direction: Optional[float] = None  # degrees

    # Source info
    source: str = "Open-Meteo Marine API"


@dataclass
class WeatherConditions:
    """Weather conditions data"""
    latitude: float
    longitude: float
    timestamp: datetime

    # Temperature
    temperature_2m: Optional[float] = None  # celsius

    # Wind
    wind_speed_10m: Optional[float] = None  # m/s
    wind_speed_10m_kts: Optional[float] = None  # knots
    wind_direction_10m: Optional[float] = None  # degrees
    wind_gusts_10m: Optional[float] = None  # m/s

    # Pressure & visibility
    pressure_msl: Optional[float] = None  # hPa
    visibility: Optional[float] = None  # meters

    # Precipitation
    precipitation: Optional[float] = None  # mm

    source: str = "Open-Meteo API"


class OpenMeteoMarineService:
    """
    Service for fetching marine and weather data from Open-Meteo APIs.
    Completely free, no API key required.
    """

    MARINE_API_URL = "https://marine-api.open-meteo.com/v1/marine"
    WEATHER_API_URL = "https://api.open-meteo.com/v1/forecast"

    # Rate limit: Be respectful - max 1 request per second
    REQUEST_TIMEOUT = 30.0

    def __init__(self):
        self._last_request_time = None
        self._cache = {}
        self._cache_ttl = 300  # 5 minutes

    def _get_cache_key(self, lat: float, lon: float, data_type: str) -> str:
        """Generate cache key"""
        return f"{data_type}:{lat:.2f}:{lon:.2f}"

    def _is_cache_valid(self, cache_key: str) -> bool:
        """Check if cache is still valid"""
        if cache_key not in self._cache:
            return False

        data, timestamp = self._cache[cache_key]
        age = (datetime.now(timezone.utc) - timestamp).total_seconds()
        return age < self._cache_ttl

    def _get_from_cache(self, cache_key: str) -> Optional[Any]:
        """Get data from cache"""
        if self._is_cache_valid(cache_key):
            data, _ = self._cache[cache_key]
            return data
        return None

    def _save_to_cache(self, cache_key: str, data: Any):
        """Save to cache"""
        self._cache[cache_key] = (data, datetime.now(timezone.utc))

    async def get_marine_conditions(
        self,
        latitude: float,
        longitude: float,
        use_cache: bool = True
    ) -> Optional[MarineConditions]:
        """
        Fetch current marine conditions for a location.

        Args:
            latitude: Location latitude
            longitude: Location longitude
            use_cache: Whether to use cached data

        Returns:
            MarineConditions object or None if failed
        """
        cache_key = self._get_cache_key(latitude, longitude, "marine")

        if use_cache:
            cached = self._get_from_cache(cache_key)
            if cached:
                logger.debug(f"Cache hit for marine data at {latitude}, {longitude}")
                return cached

        try:
            params = {
                "latitude": latitude,
                "longitude": longitude,
                "current": [
                    "wave_height",
                    "wave_direction",
                    "wave_period",
                    "swell_wave_height",
                    "swell_wave_direction",
                    "swell_wave_period",
                    "wind_wave_height",
                    "wind_wave_direction",
                    "wind_wave_period",
                    "ocean_current_velocity",
                    "ocean_current_direction"
                ],
                "timezone": "UTC"
            }

            async with httpx.AsyncClient(timeout=self.REQUEST_TIMEOUT) as client:
                response = await client.get(self.MARINE_API_URL, params=params)
                response.raise_for_status()
                data = response.json()

            current = data.get("current", {})

            conditions = MarineConditions(
                latitude=latitude,
                longitude=longitude,
                timestamp=datetime.now(timezone.utc),
                wave_height=current.get("wave_height"),
                wave_direction=current.get("wave_direction"),
                wave_period=current.get("wave_period"),
                swell_wave_height=current.get("swell_wave_height"),
                swell_wave_direction=current.get("swell_wave_direction"),
                swell_wave_period=current.get("swell_wave_period"),
                wind_wave_height=current.get("wind_wave_height"),
                wind_wave_direction=current.get("wind_wave_direction"),
                wind_wave_period=current.get("wind_wave_period"),
                ocean_current_velocity=current.get("ocean_current_velocity"),
                ocean_current_direction=current.get("ocean_current_direction"),
            )

            self._save_to_cache(cache_key, conditions)
            logger.info(f"Fetched marine data for {latitude}, {longitude}: wave={conditions.wave_height}m")

            return conditions

        except httpx.HTTPStatusError as e:
            logger.warning(f"Open-Meteo Marine API error for {latitude}, {longitude}: {e.response.status_code}")
            return None
        except Exception as e:
            logger.error(f"Error fetching marine data for {latitude}, {longitude}: {e}")
            return None

    async def get_weather_conditions(
        self,
        latitude: float,
        longitude: float,
        use_cache: bool = True
    ) -> Optional[WeatherConditions]:
        """
        Fetch current weather conditions for a location.

        Args:
            latitude: Location latitude
            longitude: Location longitude
            use_cache: Whether to use cached data

        Returns:
            WeatherConditions object or None if failed
        """
        cache_key = self._get_cache_key(latitude, longitude, "weather")

        if use_cache:
            cached = self._get_from_cache(cache_key)
            if cached:
                logger.debug(f"Cache hit for weather data at {latitude}, {longitude}")
                return cached

        try:
            params = {
                "latitude": latitude,
                "longitude": longitude,
                "current": [
                    "temperature_2m",
                    "wind_speed_10m",
                    "wind_direction_10m",
                    "wind_gusts_10m",
                    "pressure_msl",
                    "visibility",
                    "precipitation"
                ],
                "wind_speed_unit": "ms",  # meters per second
                "timezone": "UTC"
            }

            async with httpx.AsyncClient(timeout=self.REQUEST_TIMEOUT) as client:
                response = await client.get(self.WEATHER_API_URL, params=params)
                response.raise_for_status()
                data = response.json()

            current = data.get("current", {})

            # Convert wind speed from m/s to knots (1 m/s = 1.94384 knots)
            wind_speed_ms = current.get("wind_speed_10m")
            wind_speed_kts = wind_speed_ms * 1.94384 if wind_speed_ms else None

            conditions = WeatherConditions(
                latitude=latitude,
                longitude=longitude,
                timestamp=datetime.now(timezone.utc),
                temperature_2m=current.get("temperature_2m"),
                wind_speed_10m=wind_speed_ms,
                wind_speed_10m_kts=wind_speed_kts,
                wind_direction_10m=current.get("wind_direction_10m"),
                wind_gusts_10m=current.get("wind_gusts_10m"),
                pressure_msl=current.get("pressure_msl"),
                visibility=current.get("visibility"),
                precipitation=current.get("precipitation"),
            )

            self._save_to_cache(cache_key, conditions)
            logger.info(f"Fetched weather data for {latitude}, {longitude}: wind={wind_speed_kts:.1f}kts" if wind_speed_kts else f"Fetched weather data for {latitude}, {longitude}")

            return conditions

        except httpx.HTTPStatusError as e:
            logger.warning(f"Open-Meteo Weather API error for {latitude}, {longitude}: {e.response.status_code}")
            return None
        except Exception as e:
            logger.error(f"Error fetching weather data for {latitude}, {longitude}: {e}")
            return None

    async def get_marine_forecast(
        self,
        latitude: float,
        longitude: float,
        hours: int = 24
    ) -> List[Dict[str, Any]]:
        """
        Fetch marine forecast for next N hours.

        Args:
            latitude: Location latitude
            longitude: Location longitude
            hours: Number of hours to forecast

        Returns:
            List of hourly forecast data
        """
        try:
            params = {
                "latitude": latitude,
                "longitude": longitude,
                "hourly": [
                    "wave_height",
                    "wave_direction",
                    "wave_period",
                    "swell_wave_height",
                    "wind_wave_height"
                ],
                "forecast_hours": hours,
                "timezone": "UTC"
            }

            async with httpx.AsyncClient(timeout=self.REQUEST_TIMEOUT) as client:
                response = await client.get(self.MARINE_API_URL, params=params)
                response.raise_for_status()
                data = response.json()

            hourly = data.get("hourly", {})
            times = hourly.get("time", [])

            forecast = []
            for i, time_str in enumerate(times[:hours]):
                forecast.append({
                    "time": time_str,
                    "wave_height": hourly.get("wave_height", [None] * len(times))[i],
                    "wave_direction": hourly.get("wave_direction", [None] * len(times))[i],
                    "wave_period": hourly.get("wave_period", [None] * len(times))[i],
                    "swell_wave_height": hourly.get("swell_wave_height", [None] * len(times))[i],
                    "wind_wave_height": hourly.get("wind_wave_height", [None] * len(times))[i],
                })

            return forecast

        except Exception as e:
            logger.error(f"Error fetching marine forecast: {e}")
            return []

    async def get_combined_conditions(
        self,
        latitude: float,
        longitude: float
    ) -> Dict[str, Any]:
        """
        Fetch both marine and weather conditions.

        Args:
            latitude: Location latitude
            longitude: Location longitude

        Returns:
            Combined conditions dict
        """
        marine = await self.get_marine_conditions(latitude, longitude)
        weather = await self.get_weather_conditions(latitude, longitude)

        result = {
            "latitude": latitude,
            "longitude": longitude,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "marine": None,
            "weather": None,
        }

        if marine:
            result["marine"] = {
                "wave_height": marine.wave_height,
                "wave_direction": marine.wave_direction,
                "wave_period": marine.wave_period,
                "swell_wave_height": marine.swell_wave_height,
                "ocean_current_velocity": marine.ocean_current_velocity,
            }

        if weather:
            result["weather"] = {
                "temperature_c": weather.temperature_2m,
                "wind_speed_kts": weather.wind_speed_10m_kts,
                "wind_speed_ms": weather.wind_speed_10m,
                "wind_direction": weather.wind_direction_10m,
                "wind_gusts_ms": weather.wind_gusts_10m,
                "pressure_hpa": weather.pressure_msl,
                "visibility_m": weather.visibility,
            }

        return result


# Singleton instance
open_meteo_marine_service = OpenMeteoMarineService()
