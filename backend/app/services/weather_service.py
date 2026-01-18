"""
Production-ready Weather Service with caching, error handling, and retry logic.
"""
import httpx
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict
from functools import lru_cache
import asyncio

logger = logging.getLogger(__name__)


class WeatherService:
    """
    Professional weather data service with:
    - API rate limiting
    - Automatic retries
    - Response caching
    - Error handling
    - Multiple provider fallback
    """

    def __init__(self):
        import os

        # Load API keys from environment
        self.weather_api_key = os.getenv("WEATHERAPI_KEY")
        self.openweather_api_key = os.getenv("OPENWEATHER_API_KEY")

        self.weather_base_url = "https://api.weatherapi.com/v1"
        self.openweather_base_url = "https://api.openweathermap.org/data/2.5"

        # Cache configuration
        self.cache = {}
        self.cache_ttl = int(os.getenv("WEATHER_CACHE_TTL_SECONDS", "300"))

        # Rate limiting
        self.last_request_time = {}
        self.min_request_interval = 1.0  # 1 second between requests

        # Log configuration status
        if not self.weather_api_key:
            logger.warning("⚠️ WEATHERAPI_KEY not configured - weather data will be unavailable")
        if not self.openweather_api_key:
            logger.warning("⚠️ OPENWEATHER_API_KEY not configured - fallback provider unavailable")

    def _get_cache_key(self, lat: float, lon: float, data_type: str) -> str:
        """Generate cache key for location and data type."""
        return f"{data_type}:{lat:.4f}:{lon:.4f}"

    def _is_cache_valid(self, cache_key: str) -> bool:
        """Check if cached data is still valid."""
        if cache_key not in self.cache:
            return False

        cached_data, timestamp = self.cache[cache_key]
        age = (datetime.now(timezone.utc) - timestamp).total_seconds()

        return age < self.cache_ttl

    def _get_from_cache(self, cache_key: str) -> Optional[Dict]:
        """Get data from cache if valid."""
        if self._is_cache_valid(cache_key):
            data, _ = self.cache[cache_key]
            logger.debug(f"Cache hit: {cache_key}")
            return data
        return None

    def _save_to_cache(self, cache_key: str, data: Dict):
        """Save data to cache with timestamp."""
        self.cache[cache_key] = (data, datetime.now(timezone.utc))
        logger.debug(f"Cached: {cache_key}")

    async def _rate_limit(self, provider: str):
        """Implement rate limiting per provider."""
        if provider in self.last_request_time:
            elapsed = (datetime.now(timezone.utc) - self.last_request_time[provider]).total_seconds()
            if elapsed < self.min_request_interval:
                await asyncio.sleep(self.min_request_interval - elapsed)

        self.last_request_time[provider] = datetime.now(timezone.utc)

    async def fetch_current_weather(
        self,
        lat: float,
        lon: float,
        retry_count: int = 3
    ) -> Optional[Dict]:
        """
        Fetch current weather data with retry logic.

        Args:
            lat: Latitude
            lon: Longitude
            retry_count: Number of retry attempts

        Returns:
            Weather data dict or None if all attempts fail
        """
        # Check if API keys are configured
        if not self.weather_api_key and not self.openweather_api_key:
            logger.debug("Weather API keys not configured, skipping weather fetch")
            return None

        cache_key = self._get_cache_key(lat, lon, "weather")

        # Check cache first
        cached_data = self._get_from_cache(cache_key)
        if cached_data:
            return cached_data

        # Try primary provider (WeatherAPI) if key is available
        if self.weather_api_key:
            for attempt in range(retry_count):
                try:
                    await self._rate_limit("weatherapi")

                    url = f"{self.weather_base_url}/current.json"
                    params = {
                        "key": self.weather_api_key,
                        "q": f"{lat},{lon}",
                        "aqi": "yes"  # Include air quality
                    }

                    async with httpx.AsyncClient(timeout=10.0) as client:
                        response = await client.get(url, params=params)

                        if response.status_code == 200:
                            data = response.json()

                            # Format data
                            weather_data = {
                                "temperature_c": data["current"]["temp_c"],
                                "feels_like_c": data["current"]["feelslike_c"],
                                "condition": data["current"]["condition"]["text"],
                                "condition_code": data["current"]["condition"]["code"],
                                "wind_kph": data["current"]["wind_kph"],
                                "wind_degree": data["current"]["wind_degree"],
                                "wind_dir": data["current"]["wind_dir"],
                                "pressure_mb": data["current"]["pressure_mb"],
                                "humidity": data["current"]["humidity"],
                                "cloud": data["current"]["cloud"],
                                "visibility_km": data["current"]["vis_km"],
                                "uv": data["current"]["uv"],
                                "gust_kph": data["current"].get("gust_kph", 0),
                                "timestamp": datetime.now(timezone.utc).isoformat()
                            }

                            # Cache successful response
                            self._save_to_cache(cache_key, weather_data)

                            logger.info(f"✓ Fetched weather for ({lat}, {lon})")
                            return weather_data

                        elif response.status_code == 429:
                            logger.warning("Rate limit exceeded, waiting...")
                            await asyncio.sleep(2 ** attempt)  # Exponential backoff
                            continue

                        else:
                            logger.warning(f"Weather API returned {response.status_code}")

                except httpx.TimeoutException:
                    logger.warning(f"Weather API timeout (attempt {attempt + 1}/{retry_count})")
                    await asyncio.sleep(1)

                except Exception as e:
                    logger.error(f"Weather fetch error: {e}")
                    if attempt == retry_count - 1:
                        break
                    await asyncio.sleep(1)

        # Fallback to OpenWeatherMap if primary fails
        logger.info("Trying fallback weather provider...")
        return await self._fetch_openweather_fallback(lat, lon)

    async def _fetch_openweather_fallback(
        self,
        lat: float,
        lon: float
    ) -> Optional[Dict]:
        """Fallback to OpenWeatherMap API."""
        try:
            await self._rate_limit("openweather")

            url = f"{self.openweather_base_url}/weather"
            params = {
                "lat": lat,
                "lon": lon,
                "appid": self.openweather_api_key,
                "units": "metric"
            }

            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(url, params=params)

                if response.status_code == 200:
                    data = response.json()

                    weather_data = {
                        "temperature_c": data["main"]["temp"],
                        "feels_like_c": data["main"]["feels_like"],
                        "condition": data["weather"][0]["description"],
                        "condition_code": data["weather"][0]["id"],
                        "wind_kph": data["wind"]["speed"] * 3.6,  # m/s to km/h
                        "wind_degree": data["wind"].get("deg", 0),
                        "wind_dir": self._degrees_to_direction(data["wind"].get("deg", 0)),
                        "pressure_mb": data["main"]["pressure"],
                        "humidity": data["main"]["humidity"],
                        "cloud": data["clouds"]["all"],
                        "visibility_km": data.get("visibility", 10000) / 1000,
                        "uv": 0,  # Not available in free tier
                        "gust_kph": data["wind"].get("gust", 0) * 3.6,
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "source": "openweather"
                    }

                    logger.info(f"✓ Fetched weather from fallback provider")
                    return weather_data

        except Exception as e:
            logger.error(f"Fallback weather fetch failed: {e}")

        return None

    async def fetch_marine_data(
        self,
        lat: float,
        lon: float
    ) -> Optional[Dict]:
        """
        Fetch marine/tide data for coastal locations.

        Args:
            lat: Latitude
            lon: Longitude

        Returns:
            Marine data dict or None
        """
        # Check if API key is configured
        if not self.weather_api_key:
            logger.debug("Weather API key not configured, skipping marine data fetch")
            return None

        cache_key = self._get_cache_key(lat, lon, "marine")

        # Check cache
        cached_data = self._get_from_cache(cache_key)
        if cached_data:
            return cached_data

        try:
            await self._rate_limit("weatherapi")

            url = f"{self.weather_base_url}/marine.json"
            params = {
                "key": self.weather_api_key,
                "q": f"{lat},{lon}",
                "days": 1
            }

            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(url, params=params)

                if response.status_code == 200:
                    data = response.json()
                    forecast = data.get("forecast", {}).get("forecastday", [])

                    if forecast:
                        day_data = forecast[0]
                        hourly = day_data.get("hour", [])

                        # Get current hour data
                        current_hour = datetime.now(timezone.utc).hour
                        current_marine = None

                        for hour_data in hourly:
                            hour_time = datetime.fromisoformat(hour_data["time"].replace(" ", "T"))
                            if hour_time.hour == current_hour:
                                current_marine = hour_data
                                break

                        if not current_marine and hourly:
                            current_marine = hourly[0]

                        # Extract tide data
                        tide_data = day_data.get("day", {}).get("tides", {})
                        astro = day_data.get("astro", {})

                        marine_data = {
                            "wave_height_m": current_marine.get("wave_height_m", 0) if current_marine else 0,
                            "wave_direction_degree": current_marine.get("wave_dir_degree", 0) if current_marine else 0,
                            "swell_height_m": current_marine.get("swell_height_m", 0) if current_marine else 0,
                            "swell_direction_degree": current_marine.get("swell_dir_degree", 0) if current_marine else 0,
                            "swell_period_secs": current_marine.get("swell_period_secs", 0) if current_marine else 0,
                            "water_temp_c": current_marine.get("water_temp_c", 0) if current_marine else 0,
                            "tide_data": tide_data,
                            "moonrise": astro.get("moonrise", ""),
                            "moonset": astro.get("moonset", ""),
                            "moon_phase": astro.get("moon_phase", ""),
                            "moon_illumination": astro.get("moon_illumination", 0),
                            "timestamp": datetime.now(timezone.utc).isoformat()
                        }

                        # Cache successful response
                        self._save_to_cache(cache_key, marine_data)

                        logger.info(f"✓ Fetched marine data for ({lat}, {lon})")
                        return marine_data

        except Exception as e:
            logger.error(f"Marine data fetch error: {e}")

        return None

    def _degrees_to_direction(self, degrees: float) -> str:
        """Convert wind degrees to compass direction."""
        directions = ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE",
                     "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"]
        index = int((degrees + 11.25) / 22.5) % 16
        return directions[index]

    def clear_cache(self):
        """Clear all cached data."""
        self.cache = {}
        logger.info("Weather cache cleared")

    def get_cache_stats(self) -> Dict:
        """Get cache statistics."""
        valid_entries = sum(1 for key in self.cache.keys() if self._is_cache_valid(key))
        return {
            "total_entries": len(self.cache),
            "valid_entries": valid_entries,
            "expired_entries": len(self.cache) - valid_entries,
            "cache_ttl_seconds": self.cache_ttl
        }


# Create singleton instance
weather_service = WeatherService()
