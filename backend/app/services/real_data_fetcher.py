"""
Real-time data fetcher for hazard monitoring.
Fetches actual data from external APIs instead of generating mock data.
"""
import httpx
import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional
from uuid import uuid4

from app.models.monitoring import EarthquakeData, Coordinates

logger = logging.getLogger(__name__)


class RealDataFetcher:
    """Fetches real-time data from external sources."""

    def __init__(self):
        self.usgs_base_url = "https://earthquake.usgs.gov/fdsnws/event/1/query"
        self.weather_api_key = None  # Add your WeatherAPI key here
        self.weather_base_url = "https://api.weatherapi.com/v1"

    async def fetch_earthquakes(
        self,
        hours: int = 24,
        min_magnitude: float = 4.0,
        min_lat: float = 0,
        max_lat: float = 25,
        min_lon: float = 65,
        max_lon: float = 95
    ) -> List[EarthquakeData]:
        """
        Fetch real earthquake data from USGS.

        Args:
            hours: Look back this many hours
            min_magnitude: Minimum magnitude to include
            min_lat, max_lat, min_lon, max_lon: Geographic bounds

        Returns:
            List of EarthquakeData objects
        """
        try:
            start_time = (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()

            params = {
                "format": "geojson",
                "starttime": start_time,
                "minmagnitude": min_magnitude,
                "minlatitude": min_lat,
                "maxlatitude": max_lat,
                "minlongitude": min_lon,
                "maxlongitude": max_lon,
                "orderby": "time"
            }

            async with httpx.AsyncClient(timeout=30.0) as client:
                logger.info(f"Fetching earthquakes from USGS...")
                response = await client.get(self.usgs_base_url, params=params)
                response.raise_for_status()
                data = response.json()

            earthquakes = []

            for feature in data.get("features", []):
                try:
                    props = feature["properties"]
                    coords = feature["geometry"]["coordinates"]

                    earthquakes.append(
                        EarthquakeData(
                            earthquake_id=feature["id"],
                            magnitude=props["mag"],
                            depth_km=coords[2],
                            coordinates=Coordinates(lat=coords[1], lon=coords[0]),
                            location_description=props.get("place", "Unknown location"),
                            timestamp=datetime.fromtimestamp(props["time"] / 1000),
                            distance_from_coast_km=None  # Calculate if needed
                        )
                    )
                except (KeyError, ValueError) as e:
                    logger.warning(f"Error parsing earthquake feature: {e}")
                    continue

            logger.info(f"✓ Fetched {len(earthquakes)} earthquakes from USGS")
            return earthquakes

        except httpx.HTTPError as e:
            logger.error(f"✗ Failed to fetch earthquakes from USGS: {e}")
            return []
        except Exception as e:
            logger.error(f"✗ Unexpected error fetching earthquakes: {e}")
            return []

    async def fetch_weather_data(self, lat: float, lon: float) -> Optional[Dict]:
        """
        Fetch current weather data for a location.

        Args:
            lat: Latitude
            lon: Longitude

        Returns:
            Weather data dict or None if failed
        """
        if not self.weather_api_key:
            logger.warning("Weather API key not configured, skipping weather fetch")
            return None

        try:
            url = f"{self.weather_base_url}/current.json"
            params = {
                "key": self.weather_api_key,
                "q": f"{lat},{lon}",
                "aqi": "no"
            }

            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
                data = response.json()

            return {
                "temperature_c": data["current"]["temp_c"],
                "condition": data["current"]["condition"]["text"],
                "wind_kph": data["current"]["wind_kph"],
                "wind_dir": data["current"]["wind_dir"],
                "humidity": data["current"]["humidity"],
                "pressure_mb": data["current"]["pressure_mb"],
                "visibility_km": data["current"]["vis_km"]
            }

        except Exception as e:
            logger.error(f"Error fetching weather for {lat},{lon}: {e}")
            return None

    async def fetch_marine_data(self, lat: float, lon: float) -> Optional[Dict]:
        """
        Fetch marine/tide data for coastal location.

        Args:
            lat: Latitude
            lon: Longitude

        Returns:
            Marine data dict or None if failed
        """
        if not self.weather_api_key:
            return None

        try:
            url = f"{self.weather_base_url}/marine.json"
            params = {
                "key": self.weather_api_key,
                "q": f"{lat},{lon}",
                "days": 1
            }

            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
                data = response.json()

            # Extract tide and wave data
            forecast = data.get("forecast", {}).get("forecastday", [])
            if forecast:
                day_data = forecast[0]
                marine = day_data.get("day", {})

                return {
                    "max_wave_height_m": marine.get("maxwave_height_m"),
                    "avg_vis_km": marine.get("avgvis_km"),
                    "max_wind_kph": marine.get("maxwind_kph")
                }

        except Exception as e:
            logger.error(f"Error fetching marine data for {lat},{lon}: {e}")
            return None

        return None


# Create singleton instance
real_data_fetcher = RealDataFetcher()
