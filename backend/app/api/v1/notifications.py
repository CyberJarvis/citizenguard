"""
Notification Management API Endpoints
For delivering alerts and updates to citizens
"""

import logging
import uuid
from datetime import datetime, timezone, timedelta
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.database import get_database
from app.models.user import User
from app.models.notification import (
    Notification, NotificationResponse, NotificationStats,
    NotificationType, NotificationSeverity
)
from app.middleware.rbac import get_current_user
from app.utils.audit import log_audit_event

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/notifications", tags=["notifications"])


# ============================================================================
# Helper Functions
# ============================================================================

async def create_notification(
    db: AsyncIOMotorDatabase,
    user_id: str,
    notification_type: NotificationType,
    severity: NotificationSeverity,
    title: str,
    message: str,
    alert_id: Optional[str] = None,
    report_id: Optional[str] = None,
    region: Optional[str] = None,
    regions: List[str] = None,
    action_url: Optional[str] = None,
    action_label: Optional[str] = None,
    expires_at: Optional[datetime] = None,
    metadata: dict = None
) -> Notification:
    """
    Helper function to create a notification

    Args:
        db: Database connection
        user_id: User ID to send notification to
        notification_type: Type of notification
        severity: Severity level
        title: Notification title
        message: Notification message
        alert_id: Related alert ID (optional)
        report_id: Related report ID (optional)
        region: Region this notification applies to (optional)
        regions: Multiple regions (optional)
        action_url: URL to navigate when clicked (optional)
        action_label: Label for action button (optional)
        expires_at: Expiration time (optional)
        metadata: Additional metadata (optional)

    Returns:
        Created Notification object
    """
    # Generate notification ID
    notification_id = f"NTF-{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:8].upper()}"

    # Create notification document
    notification = Notification(
        notification_id=notification_id,
        user_id=user_id,
        type=notification_type,
        severity=severity,
        title=title,
        message=message,
        alert_id=alert_id,
        report_id=report_id,
        region=region,
        regions=regions or [],
        action_url=action_url,
        action_label=action_label,
        expires_at=expires_at,
        metadata=metadata or {},
        created_at=datetime.now(timezone.utc)
    )

    # Insert into database
    await db.notifications.insert_one(notification.to_mongo())

    logger.info(f"Notification created: {notification_id} for user {user_id}")

    return notification


async def create_notifications_for_region(
    db: AsyncIOMotorDatabase,
    regions: List[str],
    notification_type: NotificationType,
    severity: NotificationSeverity,
    title: str,
    message: str,
    alert_id: Optional[str] = None,
    action_url: Optional[str] = None,
    action_label: Optional[str] = None,
    expires_at: Optional[datetime] = None,
    metadata: dict = None
) -> int:
    """
    Create notifications for all users in specified regions

    Returns:
        Number of notifications created
    """
    # Find all active citizens in these regions
    users_cursor = db.users.find({
        "role": "citizen",
        "is_active": True,
        "is_banned": False,
        "$or": [
            {"location.region": {"$in": regions}},
            {"location.state": {"$in": regions}}
        ]
    })

    notifications_created = 0

    async for user_doc in users_cursor:
        try:
            user_id = user_doc.get("user_id")
            user_region = user_doc.get("location", {}).get("region") or user_doc.get("location", {}).get("state")

            await create_notification(
                db=db,
                user_id=user_id,
                notification_type=notification_type,
                severity=severity,
                title=title,
                message=message,
                alert_id=alert_id,
                region=user_region,
                regions=regions,
                action_url=action_url,
                action_label=action_label,
                expires_at=expires_at,
                metadata=metadata
            )

            notifications_created += 1

        except Exception as e:
            logger.error(f"Failed to create notification for user {user_id}: {str(e)}")
            continue

    logger.info(f"Created {notifications_created} notifications for regions: {regions}")

    return notifications_created


# ============================================================================
# Notification Endpoints
# ============================================================================

@router.get("", response_model=List[NotificationResponse])
async def get_notifications(
    type_filter: Optional[str] = Query(default=None, description="Filter by type"),
    severity_filter: Optional[str] = Query(default=None, description="Filter by severity"),
    unread_only: bool = Query(default=False, description="Show only unread notifications"),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Get user's notifications with filters

    - Returns notifications for the authenticated user
    - Supports filtering by type, severity, and read status
    - Automatically excludes expired notifications
    """
    try:
        # Build query
        query = {
            "user_id": current_user.user_id,
            "is_dismissed": False,  # Don't show dismissed notifications
            "$or": [
                {"expires_at": None},
                {"expires_at": {"$gte": datetime.now(timezone.utc)}}
            ]
        }

        # Type filter
        if type_filter:
            query["type"] = type_filter

        # Severity filter
        if severity_filter:
            query["severity"] = severity_filter

        # Unread filter
        if unread_only:
            query["is_read"] = False

        # Get notifications
        cursor = db.notifications.find(query).sort("created_at", -1).skip(skip).limit(limit)
        notifications_docs = await cursor.to_list(length=limit)

        # Format response
        notifications = []
        for notif_doc in notifications_docs:
            notif = Notification.from_mongo(notif_doc)
            notifications.append(NotificationResponse(
                notification_id=notif.notification_id,
                type=notif.type,
                severity=notif.severity,
                title=notif.title,
                message=notif.message,
                alert_id=notif.alert_id,
                report_id=notif.report_id,
                region=notif.region,
                is_read=notif.is_read,
                read_at=notif.read_at,
                created_at=notif.created_at,
                expires_at=notif.expires_at,
                action_url=notif.action_url,
                action_label=notif.action_label,
                metadata=notif.metadata
            ))

        return notifications

    except Exception as e:
        logger.error(f"Error fetching notifications: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch notifications"
        )


@router.get("/stats", response_model=NotificationStats)
async def get_notification_stats(
    current_user: User = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Get notification statistics for current user

    Returns:
    - Total notifications
    - Unread count
    - Counts by severity and type
    - Latest unread notification
    """
    try:
        # Base query (exclude dismissed and expired)
        base_query = {
            "user_id": current_user.user_id,
            "is_dismissed": False,
            "$or": [
                {"expires_at": None},
                {"expires_at": {"$gte": datetime.now(timezone.utc)}}
            ]
        }

        # Total count
        total = await db.notifications.count_documents(base_query)

        # Unread count
        unread_query = {**base_query, "is_read": False}
        unread = await db.notifications.count_documents(unread_query)

        # Count by severity
        severity_pipeline = [
            {"$match": base_query},
            {"$group": {"_id": "$severity", "count": {"$sum": 1}}}
        ]

        by_severity = {}
        async for doc in db.notifications.aggregate(severity_pipeline):
            by_severity[doc["_id"]] = doc["count"]

        # Count by type
        type_pipeline = [
            {"$match": base_query},
            {"$group": {"_id": "$type", "count": {"$sum": 1}}}
        ]

        by_type = {}
        async for doc in db.notifications.aggregate(type_pipeline):
            by_type[doc["_id"]] = doc["count"]

        # Get latest unread notification
        latest_unread = None
        latest_doc = await db.notifications.find_one(
            unread_query,
            sort=[("created_at", -1)]
        )

        if latest_doc:
            notif = Notification.from_mongo(latest_doc)
            latest_unread = NotificationResponse(
                notification_id=notif.notification_id,
                type=notif.type,
                severity=notif.severity,
                title=notif.title,
                message=notif.message,
                alert_id=notif.alert_id,
                report_id=notif.report_id,
                region=notif.region,
                is_read=notif.is_read,
                read_at=notif.read_at,
                created_at=notif.created_at,
                expires_at=notif.expires_at,
                action_url=notif.action_url,
                action_label=notif.action_label,
                metadata=notif.metadata
            )

        return NotificationStats(
            total=total,
            unread=unread,
            by_severity=by_severity,
            by_type=by_type,
            latest_unread=latest_unread
        )

    except Exception as e:
        logger.error(f"Error fetching notification stats: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch notification statistics"
        )


@router.put("/{notification_id}/read")
async def mark_notification_read(
    notification_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Mark a notification as read
    """
    try:
        result = await db.notifications.update_one(
            {
                "notification_id": notification_id,
                "user_id": current_user.user_id  # Ensure user owns this notification
            },
            {
                "$set": {
                    "is_read": True,
                    "read_at": datetime.now(timezone.utc)
                }
            }
        )

        if result.matched_count == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Notification not found"
            )

        return {
            "success": True,
            "message": "Notification marked as read",
            "notification_id": notification_id
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error marking notification as read: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to mark notification as read"
        )


@router.put("/read-all")
async def mark_all_notifications_read(
    current_user: User = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Mark all unread notifications as read for current user
    """
    try:
        result = await db.notifications.update_many(
            {
                "user_id": current_user.user_id,
                "is_read": False
            },
            {
                "$set": {
                    "is_read": True,
                    "read_at": datetime.now(timezone.utc)
                }
            }
        )

        return {
            "success": True,
            "message": f"Marked {result.modified_count} notifications as read",
            "count": result.modified_count
        }

    except Exception as e:
        logger.error(f"Error marking all notifications as read: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to mark all notifications as read"
        )


@router.put("/{notification_id}/dismiss")
async def dismiss_notification(
    notification_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Dismiss a notification (removes from user's view but keeps in database)
    """
    try:
        result = await db.notifications.update_one(
            {
                "notification_id": notification_id,
                "user_id": current_user.user_id
            },
            {
                "$set": {
                    "is_dismissed": True,
                    "dismissed_at": datetime.now(timezone.utc)
                }
            }
        )

        if result.matched_count == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Notification not found"
            )

        return {
            "success": True,
            "message": "Notification dismissed",
            "notification_id": notification_id
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error dismissing notification: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to dismiss notification"
        )


@router.delete("/clear")
async def clear_read_notifications(
    current_user: User = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Delete all read notifications for current user
    """
    try:
        result = await db.notifications.delete_many({
            "user_id": current_user.user_id,
            "is_read": True
        })

        return {
            "success": True,
            "message": f"Cleared {result.deleted_count} read notifications",
            "count": result.deleted_count
        }

    except Exception as e:
        logger.error(f"Error clearing notifications: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to clear notifications"
        )


@router.delete("/{notification_id}")
async def delete_notification(
    notification_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Delete a specific notification
    """
    try:
        result = await db.notifications.delete_one({
            "notification_id": notification_id,
            "user_id": current_user.user_id
        })

        if result.deleted_count == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Notification not found"
            )

        return {
            "success": True,
            "message": "Notification deleted",
            "notification_id": notification_id
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting notification: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete notification"
        )


# Export router and helper functions
__all__ = ["router", "create_notification", "create_notifications_for_region"]
