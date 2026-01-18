"""
API endpoints for ML-powered hazard monitoring system.
"""
from fastapi import APIRouter, HTTPException, Depends
from typing import List, Dict, Optional
from datetime import datetime, timedelta, timezone
import logging

from app.models.monitoring import (
    MonitoringResponse,
    MonitoringLocation,
    EarthquakeData,
    MonitoringSummary,
    AlertLevel,
    AlertStatus
)
from app.services.ml_monitor import ml_service
from app.middleware.security import get_current_user
from app.models.user import User

router = APIRouter(prefix="/monitoring", tags=["Hazard Monitoring"])
logger = logging.getLogger(__name__)


@router.get("/locations", response_model=List[Dict])
async def get_monitoring_locations():
    """
    Get list of all monitored locations.

    Returns basic information about each location being monitored by the ML system.
    Public endpoint - no authentication required.
    """
    try:
        locations = ml_service.get_locations()
        return locations
    except Exception as e:
        logger.error(f"Error fetching monitoring locations: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch monitoring locations")


@router.get("/current", response_model=MonitoringResponse)
async def get_current_monitoring_data(
    min_alert_level: Optional[int] = None
):
    """
    Get current hazard monitoring data for all locations.

    This is the main endpoint that returns:
    - All monitored locations with current hazard data
    - Summary statistics (critical/high/warning counts)
    - Recent earthquakes

    Query Parameters:
    - min_alert_level: Filter locations with alert level >= this value (1-5)

    Public endpoint - no authentication required for transparency.
    """
    try:
        # Get latest monitoring data
        monitoring_data = ml_service.get_current_data()

        # Filter by alert level if specified
        if min_alert_level is not None:
            if min_alert_level < 1 or min_alert_level > 5:
                raise HTTPException(status_code=400, detail="min_alert_level must be between 1 and 5")

            filtered_locations = {
                loc_id: loc_data
                for loc_id, loc_data in monitoring_data["locations"].items()
                if loc_data.max_alert >= min_alert_level
            }
            monitoring_data["locations"] = filtered_locations

            # Recalculate summary
            monitoring_data["summary"] = ml_service._calculate_summary(
                list(filtered_locations.values())
            )

        return monitoring_data
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching current monitoring data: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch monitoring data")


@router.get("/location/{location_id}", response_model=MonitoringLocation)
async def get_location_details(location_id: str):
    """
    Get detailed monitoring data for a specific location.

    Path Parameters:
    - location_id: Unique identifier for the location (e.g., "mumbai", "chennai")

    Returns detailed hazard information, recommendations, and current status.
    """
    try:
        location_data = ml_service.get_location_by_id(location_id)

        if not location_data:
            raise HTTPException(status_code=404, detail=f"Location '{location_id}' not found")

        return location_data
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching location {location_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch location details")


@router.get("/earthquakes/recent", response_model=List[EarthquakeData])
async def get_recent_earthquakes(
    hours: int = 24,
    min_magnitude: float = 4.0
):
    """
    Get recent earthquake data.

    Query Parameters:
    - hours: Look back this many hours (default: 24)
    - min_magnitude: Minimum magnitude to include (default: 4.0)

    Returns list of recent earthquakes that could trigger tsunamis or affect coastal areas.
    """
    try:
        if hours < 1 or hours > 168:  # Max 1 week
            raise HTTPException(status_code=400, detail="hours must be between 1 and 168")

        if min_magnitude < 0 or min_magnitude > 10:
            raise HTTPException(status_code=400, detail="min_magnitude must be between 0 and 10")

        earthquakes = ml_service.get_recent_earthquakes(hours=hours, min_magnitude=min_magnitude)
        return earthquakes
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching earthquake data: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch earthquake data")


@router.get("/alerts/active", response_model=List[MonitoringLocation])
async def get_active_alerts(min_level: int = 3):
    """
    Get all locations with active alerts (warning or higher).

    Query Parameters:
    - min_level: Minimum alert level (default: 3 = WARNING)

    Useful for dashboard views showing only critical/high-priority alerts.
    """
    try:
        if min_level < 1 or min_level > 5:
            raise HTTPException(status_code=400, detail="min_level must be between 1 and 5")

        all_data = ml_service.get_current_data()
        active_alerts = [
            loc_data
            for loc_data in all_data["locations"].values()
            if loc_data.max_alert >= min_level
        ]

        # Sort by alert level (highest first)
        active_alerts.sort(key=lambda x: x.max_alert, reverse=True)

        return active_alerts
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching active alerts: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch active alerts")


@router.get("/summary", response_model=MonitoringSummary)
async def get_monitoring_summary():
    """
    Get summary statistics for all monitoring locations.

    Returns counts of alerts by level and hazard type.
    Useful for dashboard overview and statistics.
    """
    try:
        monitoring_data = ml_service.get_current_data()
        return monitoring_data["summary"]
    except Exception as e:
        logger.error(f"Error fetching monitoring summary: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch summary")


@router.post("/refresh")
async def trigger_manual_refresh(current_user: User = Depends(get_current_user)):
    """
    Manually trigger ML model refresh (admin only).

    Normally, the ML model runs every 5 minutes automatically.
    This endpoint allows admins to force an immediate refresh.

    Requires: admin role
    """
    try:
        # Check if user is admin
        if current_user.role.value != "admin":
            raise HTTPException(
                status_code=403,
                detail="Only administrators can trigger manual refresh"
            )

        # Trigger refresh
        success = await ml_service.run_detection_cycle()

        if success:
            return {
                "status": "success",
                "message": "Monitoring data refreshed successfully",
                "timestamp": datetime.now(timezone.utc)
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to refresh monitoring data")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error triggering manual refresh: {e}")
        raise HTTPException(status_code=500, detail="Failed to refresh data")


@router.get("/health")
async def monitoring_health_check():
    """
    Health check endpoint for monitoring system.

    Returns status of ML service, last update time, and system health.
    """
    try:
        health_status = ml_service.get_health_status()
        return health_status
    except Exception as e:
        logger.error(f"Error checking monitoring health: {e}")
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.now(timezone.utc)
        }
