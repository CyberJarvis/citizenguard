"""
Alert Management API Endpoints
For authorities to create, manage, and publish hazard alerts
"""

import logging
import uuid
from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.database import get_database
from app.models.user import User
from app.models.alert import (
    Alert, AlertCreate, AlertUpdate, AlertResponse,
    AlertSeverity, AlertType, AlertStatus
)
from app.models.notification import NotificationType, NotificationSeverity
from app.middleware.rbac import require_authority, require_admin
from app.utils.audit import log_audit_event

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/alerts", tags=["alerts"])


# ============================================================================
# Alert CRUD Endpoints
# ============================================================================

@router.post("", response_model=AlertResponse, status_code=status.HTTP_201_CREATED)
async def create_alert(
    alert_data: AlertCreate,
    current_user: User = Depends(require_authority),  # Authority or Admin
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Create a new hazard alert

    Authority & Admin only
    """
    try:
        # Generate alert ID
        alert_id = f"ALT-{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:8].upper()}"

        # Create alert document
        alert = Alert(
            alert_id=alert_id,
            title=alert_data.title,
            description=alert_data.description,
            alert_type=alert_data.alert_type,
            severity=alert_data.severity,
            regions=alert_data.regions,
            coordinates=alert_data.coordinates,
            expires_at=alert_data.expires_at,
            instructions=alert_data.instructions,
            contact_info=alert_data.contact_info,
            tags=alert_data.tags,
            priority=alert_data.priority,
            created_by=current_user.user_id,
            creator_name=current_user.name,
            creator_organization=current_user.authority_organization,
            status=AlertStatus.ACTIVE,
            created_at=datetime.now(timezone.utc),
            issued_at=datetime.now(timezone.utc)
        )

        # Insert into database
        await db.alerts.insert_one(alert.to_mongo())

        # Log audit event
        await log_audit_event(
            db=db,
            user_id=current_user.user_id,
            action="ALERT_CREATED",
            details={
                "alert_id": alert_id,
                "severity": alert_data.severity.value,
                "regions": alert_data.regions
            }
        )

        logger.info(f"Alert created: {alert_id} by {current_user.user_id}")

        # Create notifications for affected users
        try:
            from app.api.v1.notifications import create_notifications_for_region

            # Map alert severity to notification severity
            notif_severity = NotificationSeverity(alert_data.severity.value)

            # Create notification message
            severity_emoji = {
                "critical": "🚨",
                "high": "⚠️",
                "medium": "⚡",
                "low": "ℹ️",
                "info": "📢"
            }
            emoji = severity_emoji.get(alert_data.severity.value, "📢")

            notification_title = f"{emoji} {alert_data.severity.value.upper()}: {alert_data.title}"
            notification_message = alert_data.description

            # Add instructions to message if provided
            if alert_data.instructions:
                notification_message += f"\n\n⚠️ Safety Instructions: {alert_data.instructions}"

            # Create notifications for all affected regions
            notifications_count = await create_notifications_for_region(
                db=db,
                regions=alert_data.regions,
                notification_type=NotificationType.ALERT,
                severity=notif_severity,
                title=notification_title,
                message=notification_message,
                alert_id=alert_id,
                action_url=None,  # Show details in notifications page itself
                action_label=None,
                expires_at=alert_data.expires_at,
                metadata={
                    "alert_type": alert_data.alert_type.value,
                    "creator_name": current_user.name,
                    "creator_org": current_user.authority_organization,
                    "priority": alert_data.priority,
                    "instructions": alert_data.instructions,
                    "contact_info": alert_data.contact_info,
                    "tags": alert_data.tags or []
                }
            )

            # Update alert with notification count
            await db.alerts.update_one(
                {"alert_id": alert_id},
                {
                    "$set": {
                        "notifications_sent": notifications_count
                    }
                }
            )

            logger.info(f"Created {notifications_count} notifications for alert {alert_id}")

        except Exception as e:
            # Don't fail the alert creation if notification fails
            logger.error(f"Failed to create notifications for alert {alert_id}: {str(e)}")

        return AlertResponse(
            alert_id=alert.alert_id,
            title=alert.title,
            description=alert.description,
            alert_type=alert.alert_type,
            severity=alert.severity,
            status=alert.status,
            regions=alert.regions,
            issued_at=alert.issued_at,
            expires_at=alert.expires_at,
            created_by=alert.created_by,
            creator_name=alert.creator_name,
            creator_organization=alert.creator_organization,
            instructions=alert.instructions,
            tags=alert.tags,
            priority=alert.priority
        )

    except Exception as e:
        logger.error(f"Error creating alert: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create alert"
        )


@router.get("")
async def list_alerts(
    status_filter: Optional[str] = Query(default="active", description="active, expired, cancelled, all"),
    severity: Optional[str] = Query(default=None, description="Filter by severity"),
    region: Optional[str] = Query(default=None, description="Filter by region"),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Get list of alerts with filters

    Public endpoint - anyone can view alerts
    """
    try:
        # Build query
        query = {}

        # Status filter
        if status_filter != "all":
            if status_filter == "active":
                query["status"] = AlertStatus.ACTIVE
                # Also check if not expired
                query["$or"] = [
                    {"expires_at": None},
                    {"expires_at": {"$gte": datetime.now(timezone.utc)}}
                ]
            else:
                query["status"] = status_filter

        # Severity filter
        if severity:
            query["severity"] = severity

        # Region filter
        if region:
            query["regions"] = region

        # Get alerts
        cursor = db.alerts.find(query).sort("issued_at", -1).skip(skip).limit(limit)
        alerts_docs = await cursor.to_list(length=limit)

        # Format response
        alerts = []
        for alert_doc in alerts_docs:
            alert = Alert.from_mongo(alert_doc)
            alerts.append(alert.dict())

        # Get total count
        total_count = await db.alerts.count_documents(query)

        return {
            "alerts": alerts,
            "total": total_count,
            "skip": skip,
            "limit": limit
        }

    except Exception as e:
        logger.error(f"Error listing alerts: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch alerts"
        )


@router.get("/{alert_id}")
async def get_alert(
    alert_id: str,
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Get specific alert details

    Public endpoint
    """
    try:
        alert_doc = await db.alerts.find_one({"alert_id": alert_id})

        if not alert_doc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Alert not found"
            )

        alert = Alert.from_mongo(alert_doc)
        return alert.dict()

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching alert: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch alert"
        )


@router.put("/{alert_id}")
async def update_alert(
    alert_id: str,
    update_data: AlertUpdate,
    current_user: User = Depends(require_authority),  # Authority or Admin
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Update an existing alert

    Authority & Admin only
    """
    try:
        # Check if alert exists
        alert_doc = await db.alerts.find_one({"alert_id": alert_id})

        if not alert_doc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Alert not found"
            )

        # Prepare update data
        update_dict = update_data.dict(exclude_none=True)

        if update_dict:
            update_dict["updated_by"] = current_user.user_id
            update_dict["updated_at"] = datetime.now(timezone.utc)

            # Update alert
            result = await db.alerts.update_one(
                {"alert_id": alert_id},
                {"$set": update_dict}
            )

            if result.modified_count == 0:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to update alert"
                )

            # Log audit event
            await log_audit_event(
                db=db,
                user_id=current_user.user_id,
                action="ALERT_UPDATED",
                details={"alert_id": alert_id, "changes": list(update_dict.keys())}
            )

        # Get updated alert
        updated_alert_doc = await db.alerts.find_one({"alert_id": alert_id})
        alert = Alert.from_mongo(updated_alert_doc)

        return {
            "success": True,
            "message": "Alert updated successfully",
            "alert": alert.dict()
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating alert: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update alert"
        )


@router.post("/{alert_id}/cancel")
async def cancel_alert(
    alert_id: str,
    reason: str = Query(..., min_length=10, description="Cancellation reason"),
    current_user: User = Depends(require_authority),  # Authority or Admin
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Cancel an active alert

    Authority & Admin only
    """
    try:
        # Update alert status
        result = await db.alerts.update_one(
            {"alert_id": alert_id},
            {
                "$set": {
                    "status": AlertStatus.CANCELLED,
                    "cancelled_by": current_user.user_id,
                    "cancelled_at": datetime.now(timezone.utc),
                    "cancellation_reason": reason,
                    "updated_at": datetime.now(timezone.utc)
                }
            }
        )

        if result.matched_count == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Alert not found"
            )

        # Log audit event
        await log_audit_event(
            db=db,
            user_id=current_user.user_id,
            action="ALERT_CANCELLED",
            details={"alert_id": alert_id, "reason": reason}
        )

        return {
            "success": True,
            "message": "Alert cancelled successfully",
            "alert_id": alert_id
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error cancelling alert: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to cancel alert"
        )


@router.delete("/{alert_id}")
async def delete_alert(
    alert_id: str,
    current_user: User = Depends(require_admin),  # Admin only
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Delete an alert (hard delete)

    Admin only
    """
    try:
        result = await db.alerts.delete_one({"alert_id": alert_id})

        if result.deleted_count == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Alert not found"
            )

        # Log audit event
        await log_audit_event(
            db=db,
            user_id=current_user.user_id,
            action="ALERT_DELETED",
            details={"alert_id": alert_id}
        )

        return {
            "success": True,
            "message": f"Alert {alert_id} deleted successfully"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting alert: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete alert"
        )


@router.get("/active/summary")
async def get_active_alerts_summary(
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Get summary of active alerts

    Public endpoint
    """
    try:
        # Get active alerts count by severity
        pipeline = [
            {
                "$match": {
                    "status": "active",
                    "$or": [
                        {"expires_at": None},
                        {"expires_at": {"$gte": datetime.now(timezone.utc)}}
                    ]
                }
            },
            {
                "$group": {
                    "_id": "$severity",
                    "count": {"$sum": 1}
                }
            }
        ]

        severity_counts = {}
        async for doc in db.alerts.aggregate(pipeline):
            severity_counts[doc["_id"]] = doc["count"]

        # Get total active alerts
        total_active = await db.alerts.count_documents({
            "status": "active",
            "$or": [
                {"expires_at": None},
                {"expires_at": {"$gte": datetime.now(timezone.utc)}}
            ]
        })

        return {
            "total_active": total_active,
            "by_severity": {
                "critical": severity_counts.get("critical", 0),
                "high": severity_counts.get("high", 0),
                "medium": severity_counts.get("medium", 0),
                "low": severity_counts.get("low", 0),
                "info": severity_counts.get("info", 0)
            }
        }

    except Exception as e:
        logger.error(f"Error getting alert summary: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch alert summary"
        )


# Export router
__all__ = ["router"]
