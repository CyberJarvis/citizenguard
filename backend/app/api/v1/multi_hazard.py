"""
MultiHazard Detection API Routes
Real-time coastal hazard monitoring endpoints for Indian coastal cities.
"""

import logging
from datetime import datetime, timezone
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, status, Query
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.database import get_database
from app.models.user import User
from app.middleware.rbac import get_current_user, require_analyst, require_admin
from app.services.multi_hazard_service import (
    get_multi_hazard_service, MultiHazardService
)
from app.models.multi_hazard import (
    AlertLevel, HazardType,
    HazardAlert, LocationStatus, MultiHazardResponse,
    MultiHazardSummary, MultiHazardHealthResponse,
    PublicAlertResponse, PublicStatusResponse,
    RefreshRequest, MonitoringControlRequest, DetectionCycleResult
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/multi-hazard", tags=["MultiHazard Detection"])


# Dependency to get service
def get_service() -> MultiHazardService:
    """Get initialized MultiHazard service."""
    service = get_multi_hazard_service()
    if not service._initialized:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="MultiHazard service not initialized"
        )
    return service


# =============================================================================
# PUBLIC ENDPOINTS (No Authentication)
# =============================================================================

@router.get("/health", response_model=MultiHazardHealthResponse)
async def health_check():
    """
    Health check for MultiHazard detection service.
    Public endpoint - no authentication required.
    """
    try:
        service = get_multi_hazard_service()

        all_alerts = []
        for alerts in service.active_alerts.values():
            all_alerts.extend(alerts)

        return MultiHazardHealthResponse(
            status="healthy" if service._initialized else "not_initialized",
            is_monitoring=service.is_monitoring,
            locations_count=len(service.MONITORED_LOCATIONS),
            last_cycle=service.last_detection_cycle,
            active_alerts=len(all_alerts),
            timestamp=datetime.now(timezone.utc)
        )
    except Exception as e:
        logger.error(f"MultiHazard health check failed: {e}")
        return MultiHazardHealthResponse(
            status="error",
            is_monitoring=False,
            locations_count=0,
            last_cycle=None,
            active_alerts=0,
            timestamp=datetime.now(timezone.utc)
        )


@router.get("/public/status", response_model=PublicStatusResponse)
async def get_public_status():
    """
    Get public status summary.
    Simplified view for public dashboards - no authentication required.
    """
    try:
        service = get_multi_hazard_service()

        if not service._initialized:
            return PublicStatusResponse(
                total_locations=0,
                locations_at_risk=0,
                active_alerts=[],
                highest_alert_level=1,
                highest_alert_level_name="NORMAL",
                last_updated=datetime.now(timezone.utc),
                message="Service initializing..."
            )

        # Collect all alerts
        all_alerts = []
        locations_at_risk = 0

        for loc_id, alerts in service.active_alerts.items():
            if alerts:
                locations_at_risk += 1
                for alert in alerts:
                    all_alerts.append(PublicAlertResponse(
                        location_id=alert.location_id,
                        location_name=alert.location_name,
                        hazard_type=alert.hazard_type.value,
                        alert_level=alert.alert_level,
                        alert_level_name=AlertLevel(alert.alert_level).name,
                        message=alert.reasoning if hasattr(alert, 'reasoning') else f"{alert.hazard_type.value.upper()} detected",
                        recommendations=alert.recommendations[:3],
                        detected_at=alert.detected_at,
                        is_active=alert.is_active
                    ))

        # Sort by alert level (highest first)
        all_alerts.sort(key=lambda a: -a.alert_level)

        highest_level = max((a.alert_level for a in all_alerts), default=1)

        # Generate message
        if highest_level >= AlertLevel.CRITICAL:
            message = "CRITICAL: Immediate action required for one or more locations"
        elif highest_level >= AlertLevel.WARNING:
            message = "WARNING: Hazardous conditions detected at some locations"
        elif highest_level >= AlertLevel.WATCH:
            message = "WATCH: Potentially dangerous conditions developing"
        elif highest_level >= AlertLevel.ADVISORY:
            message = "ADVISORY: Exercise caution in coastal areas"
        else:
            message = "All monitored locations are currently safe"

        return PublicStatusResponse(
            total_locations=len(service.MONITORED_LOCATIONS),
            locations_at_risk=locations_at_risk,
            active_alerts=all_alerts[:10],  # Limit to 10
            highest_alert_level=highest_level,
            highest_alert_level_name=AlertLevel(highest_level).name,
            last_updated=service.last_detection_cycle or datetime.now(timezone.utc),
            message=message
        )

    except Exception as e:
        logger.error(f"Public status error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get status"
        )


@router.get("/public/locations")
async def get_public_locations():
    """
    Get list of monitored locations (public).
    Returns basic info about all 30 Indian coastal cities with active hazards.
    """
    service = get_multi_hazard_service()

    locations = []
    for loc_id, location in service.MONITORED_LOCATIONS.items():
        status = service.location_status.get(loc_id)
        alert_level = status.max_alert_level if status else AlertLevel.NORMAL
        active_hazards = status.active_hazards if status else []

        # Get active alerts for this location
        location_alerts = service.active_alerts.get(loc_id, [])
        active_hazards_data = []
        for alert in location_alerts:
            active_hazards_data.append({
                "alert_id": alert.alert_id,
                "hazard_type": alert.hazard_type.value,
                "alert_level": alert.alert_level,
                "detected_at": alert.detected_at.isoformat(),
                "confidence": alert.confidence,
                "recommendations": alert.recommendations
            })

        locations.append({
            "location_id": loc_id,
            "name": location.name,
            "location_name": location.name,  # Alias for frontend compatibility
            "country": location.country,
            "region": location.region,
            "coordinates": {
                "lat": location.coordinates.lat,
                "lon": location.coordinates.lon
            },
            "alert_level": alert_level,
            "max_alert_level": alert_level,  # Alias for frontend compatibility
            "alert_level_name": AlertLevel(alert_level).name,
            "risk_profile": location.risk_profile,
            "active_hazards": active_hazards_data
        })

    return {
        "locations": locations,
        "total": len(locations),
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


@router.get("/public/alerts")
async def get_public_alerts(
    min_level: int = Query(default=2, ge=1, le=5, description="Minimum alert level"),
    limit: int = Query(default=20, ge=1, le=100, description="Maximum alerts to return")
):
    """
    Get active alerts (public view).
    Filtered by minimum alert level.
    """
    service = get_multi_hazard_service()

    alerts = service.get_active_alerts(min_level=AlertLevel(min_level))

    public_alerts = []
    for alert in alerts[:limit]:
        public_alerts.append({
            "alert_id": alert.alert_id,
            "location_id": alert.location_id,
            "location_name": alert.location_name,
            "hazard_type": alert.hazard_type.value,
            "alert_level": alert.alert_level,
            "alert_level_name": AlertLevel(alert.alert_level).name,
            "detected_at": alert.detected_at.isoformat(),
            "recommendations": alert.recommendations,
            "is_active": alert.is_active
        })

    return {
        "alerts": public_alerts,
        "total": len(public_alerts),
        "min_level": min_level,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


# =============================================================================
# ANALYST ENDPOINTS (Requires Authentication)
# =============================================================================

@router.get("/status", response_model=MultiHazardResponse)
async def get_full_status(
    current_user: User = Depends(require_analyst),
    service: MultiHazardService = Depends(get_service)
):
    """
    Get complete monitoring status.
    Returns all locations, alerts, earthquakes, and summary.
    Requires Analyst role or higher.
    """
    return service.get_all_status()


@router.get("/summary", response_model=MultiHazardSummary)
async def get_summary(
    current_user: User = Depends(require_analyst),
    service: MultiHazardService = Depends(get_service)
):
    """
    Get monitoring summary only.
    Lightweight endpoint for dashboard widgets.
    Requires Analyst role or higher.
    """
    full_status = service.get_all_status()
    return full_status.summary


@router.get("/locations/{location_id}", response_model=LocationStatus)
async def get_location_detail(
    location_id: str,
    current_user: User = Depends(require_analyst),
    service: MultiHazardService = Depends(get_service)
):
    """
    Get detailed status for a specific location.
    Requires Analyst role or higher.
    """
    status = service.get_location_status(location_id)
    if not status:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Location '{location_id}' not found"
        )
    return status


@router.get("/alerts", response_model=List[HazardAlert])
async def get_alerts(
    location_id: Optional[str] = Query(default=None, description="Filter by location"),
    hazard_type: Optional[str] = Query(default=None, description="Filter by hazard type"),
    min_level: int = Query(default=1, ge=1, le=5, description="Minimum alert level"),
    current_user: User = Depends(require_analyst),
    service: MultiHazardService = Depends(get_service)
):
    """
    Get filtered active alerts.
    Requires Analyst role or higher.
    """
    hazard = None
    if hazard_type:
        try:
            hazard = HazardType(hazard_type)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid hazard type: {hazard_type}"
            )

    return service.get_active_alerts(
        location_id=location_id,
        hazard_type=hazard,
        min_level=AlertLevel(min_level)
    )


@router.get("/earthquakes")
async def get_recent_earthquakes(
    current_user: User = Depends(require_analyst),
    service: MultiHazardService = Depends(get_service)
):
    """
    Get recent significant earthquakes.
    Requires Analyst role or higher.
    """
    return {
        "earthquakes": [eq.model_dump() for eq in service.recent_earthquakes],
        "total": len(service.recent_earthquakes),
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


@router.post("/refresh", response_model=DetectionCycleResult)
async def force_detection_cycle(
    request: Optional[RefreshRequest] = None,
    current_user: User = Depends(require_analyst),
    service: MultiHazardService = Depends(get_service)
):
    """
    Force an immediate detection cycle.
    Can specify specific locations or run for all.
    Requires Analyst role or higher.
    """
    location_ids = request.location_ids if request else None

    logger.info(f"Manual detection cycle triggered by {current_user.user_id}")

    result = await service.run_detection_cycle(location_ids)
    return result


# =============================================================================
# ADMIN ENDPOINTS (Requires Admin Role)
# =============================================================================

@router.post("/monitoring/start")
async def start_monitoring(
    request: Optional[MonitoringControlRequest] = None,
    current_user: User = Depends(require_admin)
):
    """
    Start background monitoring.
    Requires Admin role.
    """
    service = get_multi_hazard_service()

    if service.is_monitoring:
        return {
            "success": False,
            "message": "Monitoring already active",
            "is_monitoring": True
        }

    interval = request.interval_seconds if request else None
    await service.start_monitoring(interval)

    logger.info(f"Monitoring started by {current_user.user_id}")

    return {
        "success": True,
        "message": "Monitoring started",
        "is_monitoring": True,
        "interval_seconds": interval or 300
    }


@router.post("/monitoring/stop")
async def stop_monitoring(
    current_user: User = Depends(require_admin)
):
    """
    Stop background monitoring.
    Requires Admin role.
    """
    service = get_multi_hazard_service()

    if not service.is_monitoring:
        return {
            "success": False,
            "message": "Monitoring not active",
            "is_monitoring": False
        }

    await service.stop_monitoring()

    logger.info(f"Monitoring stopped by {current_user.user_id}")

    return {
        "success": True,
        "message": "Monitoring stopped",
        "is_monitoring": False
    }


@router.get("/monitoring/status")
async def get_monitoring_status(
    current_user: User = Depends(require_analyst)
):
    """
    Get monitoring task status.
    Requires Analyst role or higher.
    """
    service = get_multi_hazard_service()

    return {
        "is_initialized": service._initialized,
        "is_monitoring": service.is_monitoring,
        "last_detection_cycle": service.last_detection_cycle.isoformat() if service.last_detection_cycle else None,
        "next_detection_cycle": service.next_detection_cycle.isoformat() if service.next_detection_cycle else None,
        "monitored_locations": len(service.MONITORED_LOCATIONS),
        "total_active_alerts": sum(len(alerts) for alerts in service.active_alerts.values())
    }


# =============================================================================
# DEMO/TEST ENDPOINTS (Public for testing)
# =============================================================================

@router.post("/demo/inject-alerts")
async def inject_demo_alerts():
    """
    Inject demo alerts for testing/demonstration purposes.
    Creates realistic hazard alerts for Chennai, Mumbai, Kolkata, Goa, and Visakhapatnam.
    Public endpoint for easy testing.
    """
    service = get_multi_hazard_service()
    if not service._initialized:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="MultiHazard service not initialized"
        )

    alerts = service.inject_demo_alerts()

    return {
        "success": True,
        "message": f"Injected {len(alerts)} demo alerts",
        "alerts_created": [
            {
                "alert_id": a.alert_id,
                "location": a.location_name,
                "hazard_type": a.hazard_type.value,
                "alert_level": a.alert_level,
                "alert_level_name": AlertLevel(a.alert_level).name
            }
            for a in alerts
        ],
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


@router.post("/demo/clear-alerts")
async def clear_demo_alerts():
    """
    Clear all demo alerts.
    Returns system to normal state.
    Public endpoint for easy testing.
    """
    service = get_multi_hazard_service()
    if not service._initialized:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="MultiHazard service not initialized"
        )

    service.clear_demo_alerts()

    return {
        "success": True,
        "message": "All demo alerts cleared",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


@router.get("/thresholds")
async def get_detection_thresholds(
    current_user: User = Depends(require_analyst)
):
    """
    Get current hazard detection thresholds.
    Requires Analyst role or higher.
    """
    service = get_multi_hazard_service()
    return service.THRESHOLDS.model_dump()


# =============================================================================
# WEBSOCKET ENDPOINT (For Real-time Updates)
# =============================================================================

# Note: WebSocket implementation would go here for real-time alert updates
# This is a placeholder for future implementation

@router.get("/ws-info")
async def get_websocket_info():
    """
    Get WebSocket connection info (placeholder).
    WebSocket endpoint for real-time updates is planned for future release.
    """
    return {
        "status": "planned",
        "message": "WebSocket real-time updates coming in next release",
        "planned_endpoint": "/api/v1/multi-hazard/ws"
    }


# =============================================================================
# CYCLONE & STORM SURGE ENDPOINTS
# =============================================================================

@router.get("/public/cyclone-data")
async def get_cyclone_data(
    include_forecast: bool = Query(default=True, description="Include forecast track"),
    include_surge: bool = Query(default=True, description="Include storm surge data"),
    include_demo: bool = Query(default=False, description="Include demo cyclone if no active cyclones"),
):
    """
    Get active cyclone and storm surge data for map visualization.
    Returns INCOIS-style cyclone tracking data including:
    - Current cyclone position and intensity
    - Historical track
    - Forecast track and uncertainty cone
    - Wind radii
    - Storm surge contours

    Public endpoint - no authentication required.
    """
    import random
    from datetime import timedelta

    try:
        service = get_multi_hazard_service()

        # Check for real cyclone alerts
        cyclone_alerts = []
        for location_id, alerts in service.active_alerts.items():
            for alert in alerts:
                if alert.hazard_type.value == "cyclone":
                    cyclone_alerts.append(alert)

        # If we have real cyclone data, format and return it
        if cyclone_alerts:
            # Get the most severe cyclone
            cyclone_alert = max(cyclone_alerts, key=lambda a: a.alert_level)
            location = service.MONITORED_LOCATIONS.get(cyclone_alert.location_id)

            # Get parameters from the alert (not metadata)
            params = cyclone_alert.parameters or {}

            # Build cyclone data from alert
            cyclone_data = {
                "name": params.get("imd_category", "ACTIVE CYCLONE"),
                "currentPosition": {
                    "lat": location.coordinates.lat if location else params.get("lat", 15.0),
                    "lon": location.coordinates.lon if location else params.get("lon", 85.0),
                    "time": cyclone_alert.detected_at.isoformat(),
                },
                "maxWindSpeed": params.get("wind_kph", 80),
                "centralPressure": params.get("pressure_mb", 980),
                "movementSpeed": params.get("movement_speed", 15),
                "movementDirection": params.get("wind_direction", "N"),
                "condition": params.get("condition", "Unknown"),
                "track": [],
                "forecast": [],
                "windRadii": {
                    "gale": 150,
                    "storm": 80,
                    "hurricane": 40,
                },
            }

            return {
                "success": True,
                "hasActiveCyclone": True,
                "isDemo": False,
                "cyclone": cyclone_data,
                "surge": None,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

        # Return demo cyclone if requested and no real data
        if include_demo:
            now = datetime.now(timezone.utc)

            # Demo cyclone in Bay of Bengal (INCOIS-style)
            demo_cyclone = {
                "name": "CYCLONE DEMO",
                "id": "BOB-DEMO-2024",
                "basin": "Bay of Bengal",
                "currentPosition": {
                    "lat": 14.5,
                    "lon": 86.8,
                    "time": now.isoformat(),
                },
                "maxWindSpeed": 95,  # km/h - Very Severe Cyclonic Storm
                "centralPressure": 972,  # hPa
                "movementSpeed": 18,  # km/h
                "movementDirection": 315,  # NW
                "category": "very_severe",
                "track": [
                    {"lat": 11.2, "lon": 89.5, "time": (now - timedelta(hours=72)).isoformat(), "windSpeed": 45, "pressure": 1002},
                    {"lat": 11.8, "lon": 89.0, "time": (now - timedelta(hours=60)).isoformat(), "windSpeed": 55, "pressure": 998},
                    {"lat": 12.3, "lon": 88.5, "time": (now - timedelta(hours=48)).isoformat(), "windSpeed": 65, "pressure": 992},
                    {"lat": 12.9, "lon": 88.0, "time": (now - timedelta(hours=36)).isoformat(), "windSpeed": 75, "pressure": 985},
                    {"lat": 13.5, "lon": 87.5, "time": (now - timedelta(hours=24)).isoformat(), "windSpeed": 85, "pressure": 978},
                    {"lat": 14.0, "lon": 87.2, "time": (now - timedelta(hours=12)).isoformat(), "windSpeed": 90, "pressure": 974},
                    {"lat": 14.5, "lon": 86.8, "time": now.isoformat(), "windSpeed": 95, "pressure": 972},
                ],
                "forecast": [
                    {"lat": 15.0, "lon": 86.2, "time": (now + timedelta(hours=12)).isoformat(), "windSpeed": 100, "pressure": 968},
                    {"lat": 15.6, "lon": 85.5, "time": (now + timedelta(hours=24)).isoformat(), "windSpeed": 105, "pressure": 964},
                    {"lat": 16.3, "lon": 84.8, "time": (now + timedelta(hours=36)).isoformat(), "windSpeed": 95, "pressure": 970},
                    {"lat": 17.0, "lon": 84.0, "time": (now + timedelta(hours=48)).isoformat(), "windSpeed": 80, "pressure": 980},
                    {"lat": 17.8, "lon": 83.2, "time": (now + timedelta(hours=72)).isoformat(), "windSpeed": 60, "pressure": 992},
                ],
                "windRadii": {
                    "gale": {"ne": 180, "se": 150, "sw": 120, "nw": 160},
                    "storm": {"ne": 100, "se": 80, "sw": 60, "nw": 90},
                    "hurricane": {"ne": 50, "se": 40, "sw": 30, "nw": 45},
                },
            }

            # Demo storm surge contours (around Andhra Pradesh coast)
            demo_surge = None
            if include_surge:
                demo_surge = {
                    "maxHeight": 3.5,
                    "affectedCoastline": 250,  # km
                    "contours": [
                        {
                            "height": 0.5,
                            "coordinates": [
                                [16.5, 82.0], [16.8, 82.3], [17.0, 82.5], [17.2, 82.8],
                                [17.4, 83.0], [17.6, 82.8], [17.4, 82.5], [17.2, 82.2],
                                [17.0, 82.0], [16.8, 81.8], [16.5, 82.0]
                            ],
                        },
                        {
                            "height": 1.0,
                            "coordinates": [
                                [16.6, 82.1], [16.9, 82.4], [17.1, 82.6], [17.3, 82.7],
                                [17.5, 82.6], [17.3, 82.4], [17.1, 82.2], [16.9, 82.0],
                                [16.6, 82.1]
                            ],
                        },
                        {
                            "height": 1.5,
                            "coordinates": [
                                [16.8, 82.3], [17.0, 82.5], [17.2, 82.6], [17.3, 82.5],
                                [17.2, 82.4], [17.0, 82.3], [16.8, 82.3]
                            ],
                        },
                        {
                            "height": 2.0,
                            "coordinates": [
                                [16.9, 82.4], [17.1, 82.5], [17.2, 82.5], [17.1, 82.4],
                                [16.9, 82.4]
                            ],
                        },
                        {
                            "height": 3.0,
                            "coordinates": [
                                [17.0, 82.45], [17.1, 82.48], [17.05, 82.45], [17.0, 82.45]
                            ],
                        },
                    ],
                    "predictions": [
                        {"location": "Visakhapatnam", "expectedSurge": 2.5, "time": (now + timedelta(hours=36)).isoformat()},
                        {"location": "Kakinada", "expectedSurge": 3.2, "time": (now + timedelta(hours=42)).isoformat()},
                        {"location": "Machilipatnam", "expectedSurge": 2.8, "time": (now + timedelta(hours=48)).isoformat()},
                    ],
                }

            return {
                "success": True,
                "hasActiveCyclone": True,
                "isDemo": True,
                "message": "Demo cyclone data - No active cyclones in the region",
                "cyclone": demo_cyclone,
                "surge": demo_surge,
                "timestamp": now.isoformat(),
            }

        # No cyclone data
        return {
            "success": True,
            "hasActiveCyclone": False,
            "isDemo": False,
            "cyclone": None,
            "surge": None,
            "message": "No active cyclones in the Bay of Bengal or Arabian Sea",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    except Exception as e:
        logger.error(f"Error fetching cyclone data: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch cyclone data: {str(e)}"
        )


@router.get("/public/surge-legend")
async def get_surge_legend():
    """
    Get storm surge color legend configuration.
    Returns the color scale used for storm surge visualization.
    """
    return {
        "success": True,
        "legend": [
            {"height": "0-0.5m", "color": "#00ffff", "label": "Minor", "risk": "Low"},
            {"height": "0.5-1m", "color": "#00ff00", "label": "Moderate", "risk": "Moderate"},
            {"height": "1-1.5m", "color": "#ffff00", "label": "Significant", "risk": "Moderate-High"},
            {"height": "1.5-2m", "color": "#ffa500", "label": "Severe", "risk": "High"},
            {"height": "2-3m", "color": "#ff0000", "label": "Very Severe", "risk": "Very High"},
            {"height": "3-5m", "color": "#8b0000", "label": "Extreme", "risk": "Extreme"},
            {"height": ">5m", "color": "#4b0082", "label": "Catastrophic", "risk": "Catastrophic"},
        ],
        "cycloneCategories": [
            {"category": "Depression", "windSpeed": "0-33 km/h", "color": "#3b82f6"},
            {"category": "Deep Depression", "windSpeed": "34-47 km/h", "color": "#06b6d4"},
            {"category": "Cyclonic Storm", "windSpeed": "48-63 km/h", "color": "#22c55e"},
            {"category": "Severe Cyclonic", "windSpeed": "64-89 km/h", "color": "#eab308"},
            {"category": "Very Severe", "windSpeed": "90-119 km/h", "color": "#f97316"},
            {"category": "Extremely Severe", "windSpeed": "120-166 km/h", "color": "#ef4444"},
            {"category": "Super Cyclone", "windSpeed": ">167 km/h", "color": "#dc2626"},
        ],
    }
