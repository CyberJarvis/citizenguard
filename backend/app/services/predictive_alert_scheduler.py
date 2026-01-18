"""
Predictive Alert Scheduler
Background service that periodically fetches weather/marine data
and dispatches alerts based on IMD thresholds
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Set
from dataclasses import dataclass

from app.config import settings
from app.database import MongoDB
from app.services.open_meteo_marine_service import open_meteo_marine_service
from app.services.predictive_alert_service import (
    PredictiveAlertService,
    PredictiveAlert,
    AlertSeverity,
    get_predictive_alert_service,
)
from app.services.fast2sms_service import fast2sms_service

logger = logging.getLogger(__name__)


@dataclass
class MonitoringLocation:
    """A location being monitored for alerts"""
    location_id: str
    name: str
    latitude: float
    longitude: float
    user_ids: List[str]  # Users subscribed to this location
    phone_numbers: List[str]  # Phone numbers for SMS alerts


class PredictiveAlertScheduler:
    """
    Background scheduler for predictive weather alerts.

    Features:
    - Fetches data from Open-Meteo Marine API (free)
    - Evaluates conditions against IMD thresholds
    - Sends push notifications via web push
    - Sends SMS alerts via Fast2SMS for critical alerts
    - Caches recent alerts to avoid duplicates
    """

    def __init__(self):
        self._running = False
        self._task: Optional[asyncio.Task] = None
        self._check_interval = settings.PREDICTIVE_ALERT_CHECK_INTERVAL  # seconds
        self._recent_alerts: Dict[str, datetime] = {}  # Alert deduplication
        self._alert_cooldown = 3600  # 1 hour cooldown for same alert type/location

        # Default monitoring locations (Indian coast)
        self._default_locations = [
            {"name": "Chennai", "lat": 13.0827, "lon": 80.2707},
            {"name": "Mumbai", "lat": 19.0760, "lon": 72.8777},
            {"name": "Kolkata", "lat": 22.5726, "lon": 88.3639},
            {"name": "Visakhapatnam", "lat": 17.6868, "lon": 83.2185},
            {"name": "Kochi", "lat": 9.9312, "lon": 76.2673},
            {"name": "Goa", "lat": 15.2993, "lon": 73.9130},
            {"name": "Mangalore", "lat": 12.9141, "lon": 74.8560},
            {"name": "Paradip", "lat": 20.3164, "lon": 86.6085},
            {"name": "Tuticorin", "lat": 8.7642, "lon": 78.1348},
            {"name": "Andaman", "lat": 11.6234, "lon": 92.7265},
        ]

    async def start(self):
        """Start the scheduler"""
        if self._running:
            logger.warning("Scheduler already running")
            return

        self._running = True
        self._task = asyncio.create_task(self._run_loop())
        logger.info(f"[OK] Predictive Alert Scheduler started (interval: {self._check_interval}s)")

    async def stop(self):
        """Stop the scheduler"""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("[OK] Predictive Alert Scheduler stopped")

    async def _run_loop(self):
        """Main scheduler loop"""
        while self._running:
            try:
                await self._check_conditions()
            except Exception as e:
                logger.error(f"Error in scheduler loop: {e}", exc_info=True)

            # Wait for next check
            await asyncio.sleep(self._check_interval)

    async def _check_conditions(self):
        """Check conditions for all monitored locations"""
        logger.info("Starting predictive alert check...")

        try:
            # Get user subscriptions from database
            locations = await self._get_monitoring_locations()

            if not locations:
                # Use default locations if no subscriptions
                locations = [
                    MonitoringLocation(
                        location_id=f"default_{loc['name'].lower()}",
                        name=loc["name"],
                        latitude=loc["lat"],
                        longitude=loc["lon"],
                        user_ids=[],
                        phone_numbers=[]
                    )
                    for loc in self._default_locations
                ]

            logger.info(f"Checking {len(locations)} locations...")

            alerts_generated = 0
            alerts_sent = 0

            for location in locations:
                try:
                    # Fetch current conditions from Open-Meteo
                    conditions = await open_meteo_marine_service.get_combined_conditions(
                        location.latitude,
                        location.longitude
                    )

                    if not conditions:
                        continue

                    # Evaluate conditions and generate alerts
                    alerts = await self._evaluate_location(location, conditions)

                    for alert in alerts:
                        alerts_generated += 1

                        # Check if we should send this alert (deduplication)
                        if self._should_send_alert(alert, location):
                            sent = await self._dispatch_alert(alert, location)
                            if sent:
                                alerts_sent += 1
                                self._record_alert_sent(alert, location)

                except Exception as e:
                    logger.error(f"Error checking location {location.name}: {e}")
                    continue

            logger.info(f"Alert check complete: {alerts_generated} alerts generated, {alerts_sent} sent")

        except Exception as e:
            logger.error(f"Error in condition check: {e}", exc_info=True)

    async def _get_monitoring_locations(self) -> List[MonitoringLocation]:
        """Get all locations that need monitoring from subscriptions"""
        try:
            db = MongoDB.get_database()

            # Get all active subscriptions
            cursor = db.alert_subscriptions.find({"enabled": True})
            subscriptions = await cursor.to_list(length=1000)

            # Group by location (round to 0.1 degree for grouping)
            location_map: Dict[str, MonitoringLocation] = {}

            for sub in subscriptions:
                coords = sub.get("location", {}).get("coordinates", [])
                if len(coords) < 2:
                    continue

                lon, lat = coords
                # Round to group nearby locations
                key = f"{round(lat, 1)}:{round(lon, 1)}"

                if key not in location_map:
                    location_map[key] = MonitoringLocation(
                        location_id=key,
                        name=f"Location {lat:.2f}, {lon:.2f}",
                        latitude=lat,
                        longitude=lon,
                        user_ids=[],
                        phone_numbers=[]
                    )

                location_map[key].user_ids.append(sub["user_id"])

                # Get user phone for SMS alerts
                user = await db.users.find_one({"user_id": sub["user_id"]})
                if user and user.get("phone") and "sms" in sub.get("channels", []):
                    location_map[key].phone_numbers.append(user["phone"])

            return list(location_map.values())

        except Exception as e:
            logger.error(f"Error getting monitoring locations: {e}")
            return []

    async def _evaluate_location(
        self,
        location: MonitoringLocation,
        conditions: Dict
    ) -> List[PredictiveAlert]:
        """Evaluate conditions for a location and return any alerts"""
        alerts = []

        try:
            alert_service = get_predictive_alert_service()

            marine = conditions.get("marine", {})
            weather = conditions.get("weather", {})

            # Check wave conditions
            if marine and marine.get("wave_height"):
                wave_alert = await alert_service.evaluate_wave_conditions(
                    latitude=location.latitude,
                    longitude=location.longitude,
                    wave_height=marine["wave_height"],
                    location_name=location.name
                )
                if wave_alert:
                    alerts.append(wave_alert)

            # Check wind conditions
            if weather and weather.get("wind_speed_kts"):
                wind_alert = await alert_service.evaluate_wind_conditions(
                    latitude=location.latitude,
                    longitude=location.longitude,
                    wind_speed=weather["wind_speed_kts"],
                    location_name=location.name
                )
                if wind_alert:
                    alerts.append(wind_alert)

            # Check for active cyclones (from multi-hazard service if available)
            cyclone_alert = await self._check_cyclone_proximity(location)
            if cyclone_alert:
                alerts.append(cyclone_alert)

        except Exception as e:
            logger.error(f"Error evaluating location {location.name}: {e}")

        return alerts

    async def _check_cyclone_proximity(
        self,
        location: MonitoringLocation
    ) -> Optional[PredictiveAlert]:
        """Check if there's an active cyclone near the location"""
        try:
            # Try to get cyclone data from multi-hazard service
            from app.services.multi_hazard_service import get_multi_hazard_service

            mh_service = get_multi_hazard_service()
            cyclone_data = await mh_service.get_active_cyclone()

            if cyclone_data and cyclone_data.get("active"):
                alert_service = get_predictive_alert_service()

                return await alert_service.evaluate_cyclone_proximity(
                    user_latitude=location.latitude,
                    user_longitude=location.longitude,
                    cyclone_latitude=cyclone_data["latitude"],
                    cyclone_longitude=cyclone_data["longitude"],
                    cyclone_name=cyclone_data.get("name", "Unknown"),
                    cyclone_category=cyclone_data.get("category", "Unknown")
                )
        except Exception as e:
            # Multi-hazard service may not be available
            logger.debug(f"Cyclone check skipped: {e}")

        return None

    def _should_send_alert(
        self,
        alert: PredictiveAlert,
        location: MonitoringLocation
    ) -> bool:
        """Check if we should send this alert (deduplication)"""
        key = f"{alert.alert_type.value}:{location.location_id}"

        if key in self._recent_alerts:
            last_sent = self._recent_alerts[key]
            age = (datetime.now(timezone.utc) - last_sent).total_seconds()

            if age < self._alert_cooldown:
                logger.debug(f"Skipping duplicate alert {key} (sent {age:.0f}s ago)")
                return False

        return True

    def _record_alert_sent(
        self,
        alert: PredictiveAlert,
        location: MonitoringLocation
    ):
        """Record that an alert was sent"""
        key = f"{alert.alert_type.value}:{location.location_id}"
        self._recent_alerts[key] = datetime.now(timezone.utc)

        # Cleanup old entries
        cutoff = datetime.now(timezone.utc)
        self._recent_alerts = {
            k: v for k, v in self._recent_alerts.items()
            if (cutoff - v).total_seconds() < self._alert_cooldown * 2
        }

    async def _dispatch_alert(
        self,
        alert: PredictiveAlert,
        location: MonitoringLocation
    ) -> bool:
        """Dispatch alert via push notifications and SMS"""
        try:
            alert_service = get_predictive_alert_service()

            # Save alert to database
            await alert_service.save_alert(alert)

            # Send push notifications to subscribed users
            if location.user_ids and settings.PUSH_NOTIFICATIONS_ENABLED:
                try:
                    from app.services.push_notification_service import get_push_service
                    push_service = get_push_service()

                    await push_service.send_alert_notification(
                        user_ids=location.user_ids,
                        alert=alert.model_dump()
                    )
                    logger.info(f"Push notification sent for {alert.alert_type.value} at {location.name}")
                except Exception as e:
                    logger.warning(f"Failed to send push notification: {e}")

            # Send SMS for WARNING and CRITICAL alerts
            if (
                location.phone_numbers and
                settings.FAST2SMS_ENABLED and
                alert.severity in [AlertSeverity.WARNING, AlertSeverity.CRITICAL]
            ):
                try:
                    # Compose SMS message
                    sms_message = self._compose_sms_message(alert, location)

                    result = await fast2sms_service.send_sms(
                        phone_numbers=location.phone_numbers,
                        message=sms_message,
                        flash=alert.severity == AlertSeverity.CRITICAL
                    )

                    if result.get("success"):
                        logger.info(f"SMS alert sent to {len(location.phone_numbers)} numbers for {alert.alert_type.value}")
                    else:
                        logger.warning(f"SMS alert failed: {result.get('error')}")

                except Exception as e:
                    logger.warning(f"Failed to send SMS alert: {e}")

            # Also create a notification in the system
            await self._create_system_notification(alert, location)

            return True

        except Exception as e:
            logger.error(f"Error dispatching alert: {e}")
            return False

    def _compose_sms_message(
        self,
        alert: PredictiveAlert,
        location: MonitoringLocation
    ) -> str:
        """Compose SMS message for an alert"""
        severity_emoji = {
            AlertSeverity.CRITICAL: "!!!",
            AlertSeverity.WARNING: "!!",
            AlertSeverity.WATCH: "!",
            AlertSeverity.ADVISORY: "",
            AlertSeverity.INFO: "",
        }

        prefix = severity_emoji.get(alert.severity, "")

        # Keep message under 160 chars
        if alert.alert_type.value == "high_wave":
            msg = f"{prefix}WAVE ALERT{prefix} {location.name}: {alert.current_value}m waves. {alert.recommendations[0] if alert.recommendations else 'Stay safe.'}"
        elif alert.alert_type.value == "high_wind":
            msg = f"{prefix}WIND ALERT{prefix} {location.name}: {alert.current_value:.0f}kt winds. {alert.recommendations[0] if alert.recommendations else 'Stay safe.'}"
        elif alert.alert_type.value == "cyclone_watch":
            msg = f"{prefix}CYCLONE{prefix} {location.name}: {alert.message[:80]}"
        elif alert.alert_type.value == "storm_surge":
            msg = f"{prefix}SURGE ALERT{prefix} {location.name}: {alert.current_value}m surge expected. Move to higher ground."
        else:
            msg = f"{prefix}ALERT{prefix} {location.name}: {alert.title[:100]}"

        # Truncate if too long
        if len(msg) > 160:
            msg = msg[:157] + "..."

        return msg

    async def _create_system_notification(
        self,
        alert: PredictiveAlert,
        location: MonitoringLocation
    ):
        """Create a notification in the system for each user"""
        try:
            db = MongoDB.get_database()
            from uuid import uuid4

            for user_id in location.user_ids:
                notification = {
                    "notification_id": f"PA-{uuid4().hex[:8]}",
                    "user_id": user_id,
                    "type": "predictive_alert",
                    "title": alert.title,
                    "message": alert.message,
                    "data": {
                        "alert_id": alert.alert_id,
                        "alert_type": alert.alert_type.value,
                        "severity": alert.severity.value,
                        "latitude": alert.latitude,
                        "longitude": alert.longitude,
                        "location_name": location.name,
                    },
                    "is_read": False,
                    "is_dismissed": False,
                    "created_at": datetime.now(timezone.utc),
                    "expires_at": alert.valid_until,
                }

                await db.notifications.insert_one(notification)

        except Exception as e:
            logger.error(f"Error creating system notification: {e}")

    async def check_now(self) -> Dict:
        """
        Manually trigger an immediate check.
        Returns summary of alerts generated.
        """
        logger.info("Manual alert check triggered")
        await self._check_conditions()

        return {
            "success": True,
            "message": "Alert check completed",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

    async def get_status(self) -> Dict:
        """Get scheduler status"""
        return {
            "running": self._running,
            "check_interval_seconds": self._check_interval,
            "recent_alerts_count": len(self._recent_alerts),
            "alert_cooldown_seconds": self._alert_cooldown,
        }


# Global scheduler instance
_scheduler: Optional[PredictiveAlertScheduler] = None


async def initialize_alert_scheduler() -> PredictiveAlertScheduler:
    """Initialize and start the alert scheduler"""
    global _scheduler

    if _scheduler is None:
        _scheduler = PredictiveAlertScheduler()

    if not _scheduler._running:
        await _scheduler.start()

    return _scheduler


async def shutdown_alert_scheduler():
    """Stop the alert scheduler"""
    global _scheduler

    if _scheduler and _scheduler._running:
        await _scheduler.stop()


def get_alert_scheduler() -> PredictiveAlertScheduler:
    """Get the scheduler instance"""
    global _scheduler

    if _scheduler is None:
        raise RuntimeError("Alert scheduler not initialized")

    return _scheduler
