"""
Environmental Data Service
Fetches weather, marine, astronomy, and seismic data from external APIs.
Data sources: WeatherAPI (weather/marine/astronomy), USGS (earthquakes)
"""

import logging
import asyncio
import httpx
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict, Any, Tuple
from math import radians, cos, sin, asin, sqrt

from app.config import settings
from app.models.hazard import (
    ExtendedWeatherData, MarineData, AstronomyData, SeismicData,
    EnvironmentalSnapshot
)

logger = logging.getLogger(__name__)


class EnvironmentalDataService:
    """
    Service for fetching environmental data at report submission time.
    Integrates with WeatherAPI and USGS Earthquake API.
    """

    # API endpoints
    WEATHERAPI_BASE = "https://api.weatherapi.com/v1"
    USGS_EARTHQUAKE_API = "https://earthquake.usgs.gov/fdsnws/event/1/query"

    # Search parameters
    EARTHQUAKE_SEARCH_RADIUS_KM = 500  # Search within 500km
    EARTHQUAKE_LOOKBACK_DAYS = 7  # Look at past 7 days
    EARTHQUAKE_MIN_MAGNITUDE = 3.0  # Minimum magnitude to consider

    def __init__(self):
        self.api_key = settings.WEATHERAPI_KEY
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=30.0)
        return self._client

    async def close(self):
        """Close HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    @staticmethod
    def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """
        Calculate the great circle distance between two points in km.
        """
        R = 6371  # Earth's radius in km

        lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
        dlat = lat2 - lat1
        dlon = lon2 - lon1

        a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
        c = 2 * asin(sqrt(a))

        return R * c

    async def fetch_weather_data(
        self,
        latitude: float,
        longitude: float
    ) -> Tuple[Optional[ExtendedWeatherData], Optional[str]]:
        """
        Fetch current weather data from WeatherAPI.

        Returns:
            Tuple of (weather_data, error_message)
        """
        try:
            client = await self._get_client()

            url = f"{self.WEATHERAPI_BASE}/forecast.json"
            params = {
                "key": self.api_key,
                "q": f"{latitude},{longitude}",
                "days": 1,
                "aqi": "no",
                "alerts": "no"
            }

            response = await client.get(url, params=params)
            response.raise_for_status()

            data = response.json()
            current = data.get("current", {})
            condition = current.get("condition", {})

            # Get forecast hour for will_it_rain
            forecast_day = data.get("forecast", {}).get("forecastday", [{}])[0]
            current_hour = datetime.now().hour
            forecast_hours = forecast_day.get("hour", [])
            will_it_rain = 0

            for hour_data in forecast_hours:
                hour_time = hour_data.get("time", "")
                if hour_time:
                    hour_num = int(hour_time.split(" ")[1].split(":")[0])
                    if hour_num == current_hour:
                        will_it_rain = hour_data.get("will_it_rain", 0)
                        break

            weather = ExtendedWeatherData(
                temp_c=current.get("temp_c"),
                feelslike_c=current.get("feelslike_c"),
                wind_mph=current.get("wind_mph"),
                wind_kph=current.get("wind_kph"),
                wind_degree=current.get("wind_degree"),
                wind_dir=current.get("wind_dir"),
                gust_mph=current.get("gust_mph"),
                gust_kph=current.get("gust_kph"),
                pressure_mb=current.get("pressure_mb"),
                precip_mm=current.get("precip_mm"),
                will_it_rain=will_it_rain,
                vis_km=current.get("vis_km"),
                humidity=current.get("humidity"),
                cloud=current.get("cloud"),
                uv=current.get("uv"),
                condition=condition.get("text"),
                condition_code=condition.get("code"),
                time=data.get("location", {}).get("localtime"),
                last_updated=current.get("last_updated"),
                last_updated_epoch=current.get("last_updated_epoch")
            )

            logger.info(f"Weather data fetched for ({latitude}, {longitude})")
            return weather, None

        except httpx.HTTPStatusError as e:
            error_msg = f"WeatherAPI HTTP error: {e.response.status_code}"
            logger.error(error_msg)
            return None, error_msg
        except Exception as e:
            error_msg = f"Weather fetch error: {str(e)}"
            logger.error(error_msg)
            return None, error_msg

    async def fetch_marine_data(
        self,
        latitude: float,
        longitude: float
    ) -> Tuple[Optional[MarineData], Optional[str]]:
        """
        Fetch marine/ocean data from WeatherAPI Marine API.

        Returns:
            Tuple of (marine_data, error_message)
        """
        try:
            client = await self._get_client()

            url = f"{self.WEATHERAPI_BASE}/marine.json"
            params = {
                "key": self.api_key,
                "q": f"{latitude},{longitude}",
                "days": 1
            }

            response = await client.get(url, params=params)
            response.raise_for_status()

            data = response.json()

            # Get current hour's marine data
            forecast_day = data.get("forecast", {}).get("forecastday", [{}])[0]
            current_hour = datetime.now().hour
            marine_hours = forecast_day.get("hour", [])

            marine_data = None
            for hour_data in marine_hours:
                hour_time = hour_data.get("time", "")
                if hour_time:
                    hour_num = int(hour_time.split(" ")[1].split(":")[0])
                    if hour_num == current_hour:
                        marine_data = hour_data
                        break

            # Fall back to first hour if current not found
            if not marine_data and marine_hours:
                marine_data = marine_hours[0]

            if not marine_data:
                return None, "No marine data available"

            # Get tide data
            tides = forecast_day.get("day", {}).get("tides", [{}])
            tide_data = {}
            if tides and tides[0].get("tide"):
                # Get next tide event
                tide_events = tides[0]["tide"]
                now = datetime.now()
                for tide in tide_events:
                    tide_time_str = tide.get("tide_time", "")
                    if tide_time_str:
                        tide_data = {
                            "tide_time": tide_time_str,
                            "tide_height_mt": tide.get("tide_height_mt"),
                            "tide_type": tide.get("tide_type")
                        }
                        break

            marine = MarineData(
                sig_ht_mt=marine_data.get("sig_ht_mt"),
                swell_ht_mt=marine_data.get("swell_ht_mt"),
                swell_period_secs=marine_data.get("swell_period_secs"),
                swell_dir=marine_data.get("swell_dir"),
                swell_dir_16_point=marine_data.get("swell_dir_16_point"),
                water_temp_c=marine_data.get("water_temp_c"),
                water_temp_f=marine_data.get("water_temp_f"),
                tide_time=tide_data.get("tide_time"),
                tide_height_mt=float(tide_data.get("tide_height_mt", 0)) if tide_data.get("tide_height_mt") else None,
                tide_type=tide_data.get("tide_type")
            )

            logger.info(f"Marine data fetched for ({latitude}, {longitude})")
            return marine, None

        except httpx.HTTPStatusError as e:
            error_msg = f"Marine API HTTP error: {e.response.status_code}"
            logger.error(error_msg)
            return None, error_msg
        except Exception as e:
            error_msg = f"Marine fetch error: {str(e)}"
            logger.error(error_msg)
            return None, error_msg

    async def fetch_astronomy_data(
        self,
        latitude: float,
        longitude: float
    ) -> Tuple[Optional[AstronomyData], Optional[str]]:
        """
        Fetch astronomy data from WeatherAPI.

        Returns:
            Tuple of (astronomy_data, error_message)
        """
        try:
            client = await self._get_client()

            url = f"{self.WEATHERAPI_BASE}/astronomy.json"
            params = {
                "key": self.api_key,
                "q": f"{latitude},{longitude}"
            }

            response = await client.get(url, params=params)
            response.raise_for_status()

            data = response.json()
            astro = data.get("astronomy", {}).get("astro", {})
            current = data.get("current", {}) if "current" in data else {}

            astronomy = AstronomyData(
                sunrise=astro.get("sunrise"),
                sunset=astro.get("sunset"),
                moonrise=astro.get("moonrise"),
                moonset=astro.get("moonset"),
                moon_phase=astro.get("moon_phase"),
                moon_illumination=int(astro.get("moon_illumination", 0)) if astro.get("moon_illumination") else None,
                is_day=current.get("is_day")
            )

            logger.info(f"Astronomy data fetched for ({latitude}, {longitude})")
            return astronomy, None

        except httpx.HTTPStatusError as e:
            error_msg = f"Astronomy API HTTP error: {e.response.status_code}"
            logger.error(error_msg)
            return None, error_msg
        except Exception as e:
            error_msg = f"Astronomy fetch error: {str(e)}"
            logger.error(error_msg)
            return None, error_msg

    async def fetch_seismic_data(
        self,
        latitude: float,
        longitude: float,
        radius_km: Optional[float] = None,
        lookback_days: Optional[int] = None,
        min_magnitude: Optional[float] = None
    ) -> Tuple[Optional[SeismicData], Optional[str]]:
        """
        Fetch recent earthquake data from USGS API.

        Returns:
            Tuple of (seismic_data, error_message) - returns most significant nearby earthquake
        """
        try:
            client = await self._get_client()

            radius = radius_km or self.EARTHQUAKE_SEARCH_RADIUS_KM
            days = lookback_days or self.EARTHQUAKE_LOOKBACK_DAYS
            min_mag = min_magnitude or self.EARTHQUAKE_MIN_MAGNITUDE

            # Calculate date range
            end_time = datetime.now(timezone.utc)
            start_time = end_time - timedelta(days=days)

            params = {
                "format": "geojson",
                "latitude": latitude,
                "longitude": longitude,
                "maxradiuskm": radius,
                "starttime": start_time.strftime("%Y-%m-%d"),
                "endtime": end_time.strftime("%Y-%m-%d"),
                "minmagnitude": min_mag,
                "orderby": "magnitude"  # Get largest first
            }

            response = await client.get(self.USGS_EARTHQUAKE_API, params=params)
            response.raise_for_status()

            data = response.json()
            features = data.get("features", [])

            if not features:
                logger.info(f"No significant earthquakes near ({latitude}, {longitude})")
                return None, None  # No error, just no data

            # Get the most significant earthquake (already sorted by magnitude)
            eq = features[0]
            props = eq.get("properties", {})
            geometry = eq.get("geometry", {})
            coords = geometry.get("coordinates", [0, 0, 0])

            # Calculate distance from report location
            eq_lon, eq_lat, eq_depth = coords[0], coords[1], coords[2] if len(coords) > 2 else 0
            distance = self.haversine_distance(latitude, longitude, eq_lat, eq_lon)

            # Convert epoch ms to datetime
            eq_time_ms = props.get("time")
            eq_time = datetime.fromtimestamp(eq_time_ms / 1000, tz=timezone.utc) if eq_time_ms else None

            seismic = SeismicData(
                magnitude=props.get("mag"),
                depth_km=eq_depth,
                place=props.get("place"),
                time=eq_time,
                time_epoch=eq_time_ms,
                tsunami=props.get("tsunami"),
                alert=props.get("alert"),
                earthquake_id=eq.get("id"),
                distance_km=round(distance, 2),
                felt=props.get("felt"),
                significance=props.get("sig")
            )

            logger.info(f"Seismic data fetched: M{seismic.magnitude} earthquake {distance:.1f}km from ({latitude}, {longitude})")
            return seismic, None

        except httpx.HTTPStatusError as e:
            error_msg = f"USGS API HTTP error: {e.response.status_code}"
            logger.error(error_msg)
            return None, error_msg
        except Exception as e:
            error_msg = f"Seismic fetch error: {str(e)}"
            logger.error(error_msg)
            return None, error_msg

    async def fetch_all_environmental_data(
        self,
        latitude: float,
        longitude: float
    ) -> EnvironmentalSnapshot:
        """
        Fetch all environmental data concurrently and return a complete snapshot.

        This is the main method to be called at report submission time.
        """
        errors = []

        # Fetch all data concurrently
        weather_task = self.fetch_weather_data(latitude, longitude)
        marine_task = self.fetch_marine_data(latitude, longitude)
        astronomy_task = self.fetch_astronomy_data(latitude, longitude)
        seismic_task = self.fetch_seismic_data(latitude, longitude)

        results = await asyncio.gather(
            weather_task,
            marine_task,
            astronomy_task,
            seismic_task,
            return_exceptions=True
        )

        # Process results
        weather, weather_error = (None, None)
        marine, marine_error = (None, None)
        astronomy, astronomy_error = (None, None)
        seismic, seismic_error = (None, None)

        if isinstance(results[0], Exception):
            errors.append(f"Weather: {str(results[0])}")
        else:
            weather, weather_error = results[0]
            if weather_error:
                errors.append(f"Weather: {weather_error}")

        if isinstance(results[1], Exception):
            errors.append(f"Marine: {str(results[1])}")
        else:
            marine, marine_error = results[1]
            if marine_error:
                errors.append(f"Marine: {marine_error}")

        if isinstance(results[2], Exception):
            errors.append(f"Astronomy: {str(results[2])}")
        else:
            astronomy, astronomy_error = results[2]
            if astronomy_error:
                errors.append(f"Astronomy: {astronomy_error}")

        if isinstance(results[3], Exception):
            errors.append(f"Seismic: {str(results[3])}")
        else:
            seismic, seismic_error = results[3]
            if seismic_error:
                errors.append(f"Seismic: {seismic_error}")

        # Determine overall success
        fetch_success = (weather is not None or marine is not None or
                        astronomy is not None or seismic is not None)

        snapshot = EnvironmentalSnapshot(
            weather=weather,
            marine=marine,
            astronomy=astronomy,
            seismic=seismic,
            fetched_at=datetime.now(timezone.utc),
            fetch_success=fetch_success,
            fetch_errors=errors if errors else None
        )

        logger.info(
            f"Environmental snapshot created for ({latitude}, {longitude}): "
            f"weather={'OK' if weather else 'FAIL'}, "
            f"marine={'OK' if marine else 'FAIL'}, "
            f"astronomy={'OK' if astronomy else 'FAIL'}, "
            f"seismic={'OK' if seismic else 'N/A'}"
        )

        return snapshot


# Singleton instance
_environmental_service: Optional[EnvironmentalDataService] = None


def get_environmental_service() -> EnvironmentalDataService:
    """Get singleton instance of EnvironmentalDataService."""
    global _environmental_service
    if _environmental_service is None:
        _environmental_service = EnvironmentalDataService()
    return _environmental_service


async def fetch_environmental_snapshot(
    latitude: float,
    longitude: float
) -> EnvironmentalSnapshot:
    """
    Convenience function to fetch environmental data snapshot.
    Use this at report submission time.
    """
    service = get_environmental_service()
    return await service.fetch_all_environmental_data(latitude, longitude)
