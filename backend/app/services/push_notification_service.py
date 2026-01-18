"""
Push Notification Service
Web Push notifications using VAPID protocol
"""

import json
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
from pywebpush import webpush, WebPushException

from app.config import settings
from app.database import MongoDB

logger = logging.getLogger(__name__)


class PushNotificationService:
    """
    Service for sending web push notifications using VAPID
    """

    def __init__(self):
        self.vapid_private_key = settings.VAPID_PRIVATE_KEY
        self.vapid_public_key = settings.VAPID_PUBLIC_KEY
        self.vapid_claims = {
            "sub": f"mailto:{settings.VAPID_CONTACT_EMAIL or 'admin@coastguardian.in'}"
        }
        self._initialized = False

    async def initialize(self):
        """Initialize the service and create database indexes"""
        logger.info("Initializing Push Notification Service...")

        try:
            db = MongoDB.get_database()

            # Create indexes for push subscriptions
            await db.push_subscriptions.create_index([("user_id", 1)])
            await db.push_subscriptions.create_index([("endpoint", 1)], unique=True)
            await db.push_subscriptions.create_index([("created_at", -1)])

            # Create indexes for notification history
            await db.push_notification_history.create_index([("user_id", 1)])
            await db.push_notification_history.create_index([("sent_at", -1)])
            await db.push_notification_history.create_index([("alert_id", 1)])

            self._initialized = True
            logger.info("[OK] Push Notification Service initialized")

        except Exception as e:
            logger.error(f"[ERROR] Failed to initialize Push Notification Service: {e}")
            raise

    def is_configured(self) -> bool:
        """Check if VAPID keys are configured"""
        return bool(self.vapid_private_key and self.vapid_public_key)

    async def subscribe_user(
        self,
        user_id: str,
        subscription_info: Dict[str, Any],
        device_info: Optional[Dict[str, str]] = None,
    ) -> bool:
        """
        Save a user's push subscription

        Args:
            user_id: User ID
            subscription_info: Browser push subscription object
            device_info: Optional device information
        """
        try:
            db = MongoDB.get_database()

            subscription_doc = {
                "user_id": user_id,
                "endpoint": subscription_info["endpoint"],
                "keys": subscription_info.get("keys", {}),
                "expiration_time": subscription_info.get("expirationTime"),
                "device_info": device_info or {},
                "created_at": datetime.utcnow(),
                "last_used_at": datetime.utcnow(),
                "active": True,
            }

            # Upsert - update if endpoint exists, insert if not
            result = await db.push_subscriptions.update_one(
                {"endpoint": subscription_info["endpoint"]},
                {"$set": subscription_doc},
                upsert=True
            )

            logger.info(f"Push subscription saved for user {user_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to save push subscription: {e}")
            return False

    async def unsubscribe_user(self, user_id: str, endpoint: Optional[str] = None) -> bool:
        """
        Remove a user's push subscription

        Args:
            user_id: User ID
            endpoint: Optional specific endpoint to remove
        """
        try:
            db = MongoDB.get_database()

            if endpoint:
                # Remove specific subscription
                result = await db.push_subscriptions.delete_one({
                    "user_id": user_id,
                    "endpoint": endpoint
                })
            else:
                # Remove all subscriptions for user
                result = await db.push_subscriptions.delete_many({"user_id": user_id})

            logger.info(f"Push subscription(s) removed for user {user_id}")
            return result.deleted_count > 0

        except Exception as e:
            logger.error(f"Failed to remove push subscription: {e}")
            return False

    async def get_user_subscriptions(self, user_id: str) -> List[Dict]:
        """Get all push subscriptions for a user"""
        try:
            db = MongoDB.get_database()

            cursor = db.push_subscriptions.find({
                "user_id": user_id,
                "active": True
            })

            subscriptions = await cursor.to_list(length=10)

            # Clean up MongoDB fields
            for sub in subscriptions:
                sub.pop("_id", None)

            return subscriptions

        except Exception as e:
            logger.error(f"Failed to get subscriptions for user {user_id}: {e}")
            return []

    async def send_push(
        self,
        user_id: str,
        title: str,
        body: str,
        data: Optional[Dict[str, Any]] = None,
        icon: Optional[str] = None,
        badge: Optional[str] = None,
        tag: Optional[str] = None,
        actions: Optional[List[Dict[str, str]]] = None,
        url: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Send push notification to a specific user

        Args:
            user_id: User ID
            title: Notification title
            body: Notification body text
            data: Optional data payload
            icon: Optional icon URL
            badge: Optional badge icon URL
            tag: Optional tag for notification grouping
            actions: Optional action buttons
            url: Optional URL to open on click
        """
        if not self.is_configured():
            logger.warning("VAPID keys not configured, skipping push notification")
            return {"success": False, "reason": "not_configured"}

        try:
            db = MongoDB.get_database()

            # Get user's subscriptions
            subscriptions = await self.get_user_subscriptions(user_id)

            if not subscriptions:
                return {"success": False, "reason": "no_subscriptions"}

            # Prepare notification payload
            payload = {
                "title": title,
                "body": body,
                "icon": icon or "/icons/icon-192x192.png",
                "badge": badge or "/icons/badge-72x72.png",
                "data": data or {},
                "url": url or "/map",
            }

            if tag:
                payload["tag"] = tag

            if actions:
                payload["actions"] = actions

            # Send to all subscriptions
            success_count = 0
            fail_count = 0
            failed_endpoints = []

            for subscription in subscriptions:
                try:
                    subscription_info = {
                        "endpoint": subscription["endpoint"],
                        "keys": subscription.get("keys", {}),
                    }

                    webpush(
                        subscription_info=subscription_info,
                        data=json.dumps(payload),
                        vapid_private_key=self.vapid_private_key,
                        vapid_claims=self.vapid_claims,
                    )

                    success_count += 1

                    # Update last used timestamp
                    await db.push_subscriptions.update_one(
                        {"endpoint": subscription["endpoint"]},
                        {"$set": {"last_used_at": datetime.utcnow()}}
                    )

                except WebPushException as e:
                    fail_count += 1
                    failed_endpoints.append(subscription["endpoint"])

                    # If subscription is invalid (410 Gone), mark as inactive
                    if e.response and e.response.status_code == 410:
                        await db.push_subscriptions.update_one(
                            {"endpoint": subscription["endpoint"]},
                            {"$set": {"active": False}}
                        )
                        logger.info(f"Marking expired subscription as inactive: {subscription['endpoint'][:50]}...")
                    else:
                        logger.warning(f"Push notification failed: {e}")

            # Log notification in history
            await db.push_notification_history.insert_one({
                "user_id": user_id,
                "title": title,
                "body": body,
                "data": data,
                "sent_at": datetime.utcnow(),
                "success_count": success_count,
                "fail_count": fail_count,
            })

            return {
                "success": success_count > 0,
                "sent": success_count,
                "failed": fail_count,
            }

        except Exception as e:
            logger.error(f"Failed to send push notification: {e}")
            return {"success": False, "reason": str(e)}

    async def send_bulk_push(
        self,
        user_ids: List[str],
        title: str,
        body: str,
        data: Optional[Dict[str, Any]] = None,
        alert_id: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Send push notification to multiple users

        Args:
            user_ids: List of user IDs
            title: Notification title
            body: Notification body
            data: Optional data payload
            alert_id: Optional alert ID for tracking
        """
        results = {
            "total_users": len(user_ids),
            "success": 0,
            "failed": 0,
            "no_subscription": 0,
        }

        for user_id in user_ids:
            result = await self.send_push(
                user_id=user_id,
                title=title,
                body=body,
                data=data,
                **kwargs
            )

            if result.get("success"):
                results["success"] += 1
            elif result.get("reason") == "no_subscriptions":
                results["no_subscription"] += 1
            else:
                results["failed"] += 1

        # Log bulk notification
        try:
            db = MongoDB.get_database()
            await db.push_notification_history.insert_one({
                "bulk": True,
                "user_ids": user_ids,
                "title": title,
                "body": body,
                "alert_id": alert_id,
                "sent_at": datetime.utcnow(),
                "results": results,
            })
        except Exception as e:
            logger.error(f"Failed to log bulk notification: {e}")

        return results

    async def send_alert_notification(
        self,
        user_ids: List[str],
        alert: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Send notification for a predictive alert

        Args:
            user_ids: List of user IDs to notify
            alert: Alert data
        """
        severity = alert.get("severity", "info")
        alert_type = alert.get("alert_type", "alert")

        # Customize notification based on severity
        icon = "/icons/icon-192x192.png"
        if severity == "critical":
            icon = "/icons/alert-critical.png"
        elif severity == "warning":
            icon = "/icons/alert-warning.png"

        # Add relevant actions
        actions = [
            {"action": "view", "title": "View Details"},
            {"action": "dismiss", "title": "Dismiss"},
        ]

        return await self.send_bulk_push(
            user_ids=user_ids,
            title=alert.get("title", "Weather Alert"),
            body=alert.get("message", "A weather alert has been issued for your area"),
            data={
                "type": "predictive_alert",
                "alert_id": alert.get("alert_id"),
                "alert_type": alert_type,
                "severity": severity,
            },
            icon=icon,
            tag=f"alert-{alert.get('alert_id', 'unknown')}",
            actions=actions,
            url=f"/map?alert={alert.get('alert_id')}",
            alert_id=alert.get("alert_id"),
        )

    async def get_users_in_area(
        self,
        latitude: float,
        longitude: float,
        radius_km: float,
    ) -> List[str]:
        """
        Get user IDs who have subscribed to alerts in a specific area

        Args:
            latitude: Center latitude
            longitude: Center longitude
            radius_km: Radius in km
        """
        try:
            db = MongoDB.get_database()

            # Query alert subscriptions with location
            cursor = db.alert_subscriptions.find({
                "enabled": True,
                "location": {
                    "$geoWithin": {
                        "$centerSphere": [
                            [longitude, latitude],
                            radius_km / 6371  # Convert to radians
                        ]
                    }
                }
            })

            subscriptions = await cursor.to_list(length=1000)
            user_ids = [sub["user_id"] for sub in subscriptions]

            return user_ids

        except Exception as e:
            logger.error(f"Failed to get users in area: {e}")
            return []

    async def dispatch_alert_to_area(
        self,
        alert: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Dispatch alert notifications to all subscribed users in affected area

        Args:
            alert: Alert data with location info
        """
        latitude = alert.get("latitude")
        longitude = alert.get("longitude")
        radius_km = alert.get("radius_km", 100)

        if latitude is None or longitude is None:
            return {"success": False, "reason": "missing_location"}

        # Get users in affected area
        user_ids = await self.get_users_in_area(latitude, longitude, radius_km)

        if not user_ids:
            logger.info(f"No users subscribed in alert area ({latitude}, {longitude})")
            return {"success": True, "users_notified": 0}

        # Send notifications
        result = await self.send_alert_notification(user_ids, alert)
        result["users_in_area"] = len(user_ids)

        logger.info(f"Alert dispatched to {len(user_ids)} users, {result.get('success', 0)} succeeded")

        return result


# Global service instance
_push_service: Optional[PushNotificationService] = None


async def initialize_push_service():
    """Initialize the push notification service"""
    global _push_service

    if _push_service is None:
        _push_service = PushNotificationService()
        await _push_service.initialize()

    return _push_service


def get_push_service() -> PushNotificationService:
    """Get the push notification service instance"""
    global _push_service

    if _push_service is None:
        raise RuntimeError("Push Notification Service not initialized")

    return _push_service
