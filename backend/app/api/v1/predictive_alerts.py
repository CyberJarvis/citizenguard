"""
Predictive Alerts API Routes
Handles alert subscriptions, push notifications, and predictive alert management
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from pydantic import BaseModel, Field

from app.config import settings
from app.database import MongoDB
from app.middleware.security import get_current_user
from app.services.predictive_alert_service import (
    PredictiveAlertService,
    AlertSeverity,
    AlertType,
    get_predictive_alert_service,
)
from app.services.push_notification_service import (
    PushNotificationService,
    get_push_service,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/predictive-alerts", tags=["Predictive Alerts"])


# ============ Request/Response Models ============

class AlertSubscriptionRequest(BaseModel):
    """Request to subscribe to predictive alerts"""
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)
    radius_km: float = Field(default=100, ge=10, le=500)
    alert_types: Optional[List[str]] = None  # Filter by specific alert types
    min_severity: Optional[str] = Field(default="advisory")  # Minimum severity
    channels: List[str] = Field(default=["push"])  # push, sms, email
    enabled: bool = True


class AlertSubscriptionResponse(BaseModel):
    """Response for subscription operations"""
    success: bool
    message: str
    subscription_id: Optional[str] = None
    data: Optional[Dict[str, Any]] = None


class PushSubscriptionRequest(BaseModel):
    """Browser push subscription request"""
    endpoint: str
    keys: Dict[str, str]  # p256dh and auth keys
    expiration_time: Optional[int] = None
    device_info: Optional[Dict[str, str]] = None


class EvaluateConditionsRequest(BaseModel):
    """Request to manually evaluate conditions"""
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)
    weather_data: Optional[Dict[str, Any]] = None
    marine_data: Optional[Dict[str, Any]] = None
    cyclone_data: Optional[Dict[str, Any]] = None


class AlertsResponse(BaseModel):
    """Response containing alerts"""
    success: bool
    count: int
    alerts: List[Dict[str, Any]]


# ============ Subscription Endpoints ============

@router.post("/subscribe", response_model=AlertSubscriptionResponse)
async def subscribe_to_alerts(
    request: AlertSubscriptionRequest,
    current_user: dict = Depends(get_current_user),
):
    """
    Subscribe to predictive alerts for a location

    Creates or updates an alert subscription for the authenticated user.
    Alerts will be sent via specified channels when conditions meet thresholds.
    """
    try:
        db = MongoDB.get_database()

        subscription_doc = {
            "user_id": current_user["user_id"],
            "location": {
                "type": "Point",
                "coordinates": [request.longitude, request.latitude]
            },
            "latitude": request.latitude,
            "longitude": request.longitude,
            "radius_km": request.radius_km,
            "alert_types": request.alert_types,
            "min_severity": request.min_severity,
            "channels": request.channels,
            "enabled": request.enabled,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
        }

        # Upsert subscription
        result = await db.alert_subscriptions.update_one(
            {"user_id": current_user["user_id"]},
            {"$set": subscription_doc},
            upsert=True
        )

        return AlertSubscriptionResponse(
            success=True,
            message="Successfully subscribed to alerts",
            subscription_id=current_user["user_id"],
            data={
                "latitude": request.latitude,
                "longitude": request.longitude,
                "radius_km": request.radius_km,
            }
        )

    except Exception as e:
        logger.error(f"Failed to create subscription: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create alert subscription"
        )


@router.get("/subscriptions", response_model=AlertSubscriptionResponse)
async def get_subscription(
    current_user: dict = Depends(get_current_user),
):
    """
    Get current user's alert subscription
    """
    try:
        db = MongoDB.get_database()

        subscription = await db.alert_subscriptions.find_one({
            "user_id": current_user["user_id"]
        })

        if not subscription:
            return AlertSubscriptionResponse(
                success=True,
                message="No subscription found",
                data=None
            )

        # Clean up MongoDB fields
        subscription.pop("_id", None)
        subscription.pop("location", None)

        return AlertSubscriptionResponse(
            success=True,
            message="Subscription retrieved",
            subscription_id=current_user["user_id"],
            data=subscription
        )

    except Exception as e:
        logger.error(f"Failed to get subscription: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve subscription"
        )


@router.delete("/subscribe")
async def unsubscribe_from_alerts(
    current_user: dict = Depends(get_current_user),
):
    """
    Unsubscribe from predictive alerts
    """
    try:
        db = MongoDB.get_database()

        result = await db.alert_subscriptions.delete_one({
            "user_id": current_user["user_id"]
        })

        if result.deleted_count == 0:
            return {"success": True, "message": "No subscription to remove"}

        return {"success": True, "message": "Successfully unsubscribed from alerts"}

    except Exception as e:
        logger.error(f"Failed to unsubscribe: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to unsubscribe from alerts"
        )


@router.patch("/subscribe/toggle")
async def toggle_subscription(
    enabled: bool,
    current_user: dict = Depends(get_current_user),
):
    """
    Enable or disable alert subscription
    """
    try:
        db = MongoDB.get_database()

        result = await db.alert_subscriptions.update_one(
            {"user_id": current_user["user_id"]},
            {"$set": {"enabled": enabled, "updated_at": datetime.utcnow()}}
        )

        if result.matched_count == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No subscription found"
            )

        return {
            "success": True,
            "message": f"Alerts {'enabled' if enabled else 'disabled'}",
            "enabled": enabled
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to toggle subscription: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to toggle subscription"
        )


# ============ Push Notification Endpoints ============

@router.post("/push-subscription")
async def register_push_subscription(
    request: PushSubscriptionRequest,
    current_user: dict = Depends(get_current_user),
):
    """
    Register browser push notification subscription

    Call this after obtaining a PushSubscription from the browser's
    Push API to enable push notifications for alerts.
    """
    if not settings.PUSH_NOTIFICATIONS_ENABLED:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Push notifications are not configured"
        )

    try:
        push_service = get_push_service()

        subscription_info = {
            "endpoint": request.endpoint,
            "keys": request.keys,
            "expirationTime": request.expiration_time,
        }

        success = await push_service.subscribe_user(
            user_id=current_user["user_id"],
            subscription_info=subscription_info,
            device_info=request.device_info,
        )

        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to register push subscription"
            )

        return {"success": True, "message": "Push subscription registered"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to register push subscription: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to register push subscription"
        )


@router.delete("/push-subscription")
async def unregister_push_subscription(
    endpoint: Optional[str] = None,
    current_user: dict = Depends(get_current_user),
):
    """
    Unregister push notification subscription

    If endpoint is provided, removes only that subscription.
    Otherwise, removes all push subscriptions for the user.
    """
    try:
        push_service = get_push_service()

        success = await push_service.unsubscribe_user(
            user_id=current_user["user_id"],
            endpoint=endpoint,
        )

        return {
            "success": True,
            "message": "Push subscription(s) removed" if success else "No subscriptions to remove"
        }

    except Exception as e:
        logger.error(f"Failed to unregister push subscription: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to unregister push subscription"
        )


@router.get("/push-vapid-key")
async def get_vapid_public_key():
    """
    Get VAPID public key for browser push subscription

    Use this key when calling pushManager.subscribe() in the browser.
    """
    if not settings.VAPID_PUBLIC_KEY:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Push notifications are not configured"
        )

    return {
        "success": True,
        "vapid_public_key": settings.VAPID_PUBLIC_KEY,
    }


# ============ Alert Endpoints ============

@router.get("/active", response_model=AlertsResponse)
async def get_active_alerts(
    latitude: Optional[float] = None,
    longitude: Optional[float] = None,
    radius_km: float = 100,
    alert_type: Optional[str] = None,
    min_severity: Optional[str] = None,
    current_user: dict = Depends(get_current_user),
):
    """
    Get active predictive alerts

    Optionally filter by location, type, and severity.
    If no location is provided, uses user's subscription location.
    """
    try:
        alert_service = get_predictive_alert_service()

        # If no location provided, use subscription location
        if latitude is None or longitude is None:
            db = MongoDB.get_database()
            subscription = await db.alert_subscriptions.find_one({
                "user_id": current_user["user_id"]
            })

            if subscription:
                coords = subscription.get("location", {}).get("coordinates", [])
                if len(coords) >= 2:
                    longitude, latitude = coords
                    radius_km = subscription.get("radius_km", radius_km)

        # Parse filter parameters
        alert_types = None
        if alert_type:
            try:
                alert_types = [AlertType(alert_type)]
            except ValueError:
                pass

        severity = None
        if min_severity:
            try:
                severity = AlertSeverity(min_severity)
            except ValueError:
                pass

        alerts = await alert_service.get_active_alerts(
            latitude=latitude,
            longitude=longitude,
            radius_km=radius_km,
            alert_types=alert_types,
            min_severity=severity,
        )

        return AlertsResponse(
            success=True,
            count=len(alerts),
            alerts=alerts
        )

    except Exception as e:
        logger.error(f"Failed to get active alerts: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve alerts"
        )


@router.get("/my-alerts", response_model=AlertsResponse)
async def get_my_alerts(
    current_user: dict = Depends(get_current_user),
):
    """
    Get alerts relevant to the current user based on their subscription
    """
    try:
        alert_service = get_predictive_alert_service()

        alerts = await alert_service.get_alerts_for_user(current_user["user_id"])

        return AlertsResponse(
            success=True,
            count=len(alerts),
            alerts=alerts
        )

    except Exception as e:
        logger.error(f"Failed to get user alerts: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve alerts"
        )


@router.post("/evaluate")
async def evaluate_conditions(
    request: EvaluateConditionsRequest,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user),
):
    """
    Manually evaluate conditions for a location

    Returns any alerts that would be triggered based on provided data.
    Useful for testing or on-demand evaluation.
    """
    try:
        alert_service = get_predictive_alert_service()

        alerts = await alert_service.evaluate_all_conditions(
            latitude=request.latitude,
            longitude=request.longitude,
            weather_data=request.weather_data or {},
            marine_data=request.marine_data,
            cyclone_data=request.cyclone_data,
        )

        # Save alerts and dispatch notifications in background
        if alerts:
            background_tasks.add_task(
                _save_and_dispatch_alerts,
                alerts,
                request.latitude,
                request.longitude,
            )

        return {
            "success": True,
            "count": len(alerts),
            "alerts": [alert.model_dump() for alert in alerts],
        }

    except Exception as e:
        logger.error(f"Failed to evaluate conditions: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to evaluate conditions"
        )


@router.get("/thresholds")
async def get_alert_thresholds():
    """
    Get IMD standard thresholds used for alert generation

    Returns all threshold values for wave height, wind speed,
    cyclone distance, and storm surge.
    """
    from app.services.predictive_alert_service import IMDThresholds

    return {
        "success": True,
        "thresholds": {
            "wave_height_meters": IMDThresholds.WAVE_HEIGHT,
            "wind_speed_knots": IMDThresholds.WIND_SPEED,
            "cyclone_distance_km": IMDThresholds.CYCLONE_DISTANCE,
            "storm_surge_meters": IMDThresholds.STORM_SURGE,
            "visibility_km": IMDThresholds.VISIBILITY,
        },
        "source": "India Meteorological Department (IMD) Standards"
    }


# ============ Scheduler Control Endpoints ============

@router.get("/scheduler/status")
async def get_scheduler_status(
    current_user: dict = Depends(get_current_user),
):
    """
    Get the status of the predictive alert scheduler

    Returns whether the scheduler is running and its configuration.
    """
    try:
        from app.services.predictive_alert_scheduler import get_alert_scheduler
        scheduler = get_alert_scheduler()
        status = await scheduler.get_status()

        return {
            "success": True,
            **status
        }
    except RuntimeError:
        return {
            "success": True,
            "running": False,
            "message": "Scheduler not initialized"
        }
    except Exception as e:
        logger.error(f"Failed to get scheduler status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get scheduler status"
        )


@router.post("/scheduler/check-now")
async def trigger_manual_check(
    current_user: dict = Depends(get_current_user),
):
    """
    Manually trigger an immediate alert check

    This runs the scheduler check immediately instead of waiting
    for the next scheduled interval.
    """
    # Only allow authority users to trigger manual checks
    if current_user.get("role") not in ["authority", "authority_admin", "analyst"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only authority users can trigger manual checks"
        )

    try:
        from app.services.predictive_alert_scheduler import get_alert_scheduler
        scheduler = get_alert_scheduler()
        result = await scheduler.check_now()

        return result

    except RuntimeError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Alert scheduler not running"
        )
    except Exception as e:
        logger.error(f"Failed to trigger manual check: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to trigger alert check"
        )


@router.get("/marine-conditions")
async def get_marine_conditions(
    latitude: float,
    longitude: float,
    current_user: dict = Depends(get_current_user),
):
    """
    Get current marine conditions from Open-Meteo Marine API

    Returns wave height, swell data, and ocean currents for the location.
    """
    try:
        from app.services.open_meteo_marine_service import open_meteo_marine_service

        conditions = await open_meteo_marine_service.get_combined_conditions(
            latitude=latitude,
            longitude=longitude
        )

        return {
            "success": True,
            "data": conditions,
            "source": "Open-Meteo Marine API (free)"
        }

    except Exception as e:
        logger.error(f"Failed to get marine conditions: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch marine conditions"
        )


@router.get("/marine-forecast")
async def get_marine_forecast(
    latitude: float,
    longitude: float,
    hours: int = 24,
    current_user: dict = Depends(get_current_user),
):
    """
    Get marine forecast for the next N hours

    Returns hourly wave height predictions.
    """
    try:
        from app.services.open_meteo_marine_service import open_meteo_marine_service

        forecast = await open_meteo_marine_service.get_marine_forecast(
            latitude=latitude,
            longitude=longitude,
            hours=min(hours, 168)  # Max 7 days
        )

        return {
            "success": True,
            "count": len(forecast),
            "forecast": forecast,
            "source": "Open-Meteo Marine API"
        }

    except Exception as e:
        logger.error(f"Failed to get marine forecast: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch marine forecast"
        )


# ============ Helper Functions ============

async def _save_and_dispatch_alerts(alerts: list, latitude: float, longitude: float):
    """Background task to save alerts and dispatch notifications"""
    try:
        alert_service = get_predictive_alert_service()
        push_service = get_push_service()

        for alert in alerts:
            # Save alert to database
            await alert_service.save_alert(alert)

            # Dispatch push notifications to affected users
            if settings.PUSH_NOTIFICATIONS_ENABLED:
                await push_service.dispatch_alert_to_area(alert.model_dump())

    except Exception as e:
        logger.error(f"Failed to save/dispatch alerts: {e}")
