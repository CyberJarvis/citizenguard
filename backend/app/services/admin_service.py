"""
Admin Service
Provides comprehensive admin functionality for the Super Admin panel.
Handles user management, system monitoring, settings, and audit logs.
"""

import logging
import os
import uuid
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Any
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.models.admin import (
    AdminActivityLog, AdminActionType, SystemSettings,
    SettingCategory, SettingValueType, HealthStatus
)
from app.models.rbac import UserRole
from app.utils.password import hash_password

logger = logging.getLogger(__name__)


class AdminService:
    """
    Service for admin operations.

    Provides:
    - User management (CRUD, ban/unban, role assignment)
    - System monitoring (health, API stats, errors)
    - System settings management
    - Audit log retrieval and export
    - Dashboard statistics
    """

    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db

    # =========================================================================
    # HELPER METHODS
    # =========================================================================

    def _generate_id(self, prefix: str = "ID") -> str:
        """Generate a unique ID with prefix."""
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
        unique = uuid.uuid4().hex[:8].upper()
        return f"{prefix}-{timestamp}{unique}"

    async def _log_admin_action(
        self,
        admin_id: str,
        admin_name: str,
        action: AdminActionType,
        target_type: str,
        target_id: Optional[str] = None,
        target_name: Optional[str] = None,
        details: Optional[Dict] = None,
        previous_value: Any = None,
        new_value: Any = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        success: bool = True,
        error_message: Optional[str] = None
    ) -> None:
        """Log an admin action to the admin activity logs."""
        try:
            log_entry = AdminActivityLog(
                log_id=self._generate_id("ALOG"),
                admin_id=admin_id,
                admin_name=admin_name,
                action=action,
                target_type=target_type,
                target_id=target_id,
                target_name=target_name,
                details=details or {},
                previous_value=previous_value,
                new_value=new_value,
                ip_address=ip_address,
                user_agent=user_agent,
                success=success,
                error_message=error_message
            )
            await self.db.admin_activity_logs.insert_one(log_entry.to_mongo())
        except Exception as e:
            logger.error(f"Failed to log admin action: {e}")

    def _get_date_range(self, range_type: str) -> Dict[str, datetime]:
        """Convert a range type to start/end dates."""
        now = datetime.now(timezone.utc)
        end = now

        if range_type == "today":
            start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        elif range_type == "7days":
            start = now - timedelta(days=7)
        elif range_type == "30days":
            start = now - timedelta(days=30)
        elif range_type == "90days":
            start = now - timedelta(days=90)
        elif range_type == "year":
            start = now - timedelta(days=365)
        elif range_type == "all":
            start = datetime(2020, 1, 1, tzinfo=timezone.utc)
        else:
            start = now - timedelta(days=7)

        return {"start": start, "end": end}

    # =========================================================================
    # DASHBOARD & STATISTICS
    # =========================================================================

    async def get_dashboard_stats(self) -> Dict[str, Any]:
        """Get comprehensive dashboard statistics for admin panel."""
        now = datetime.now(timezone.utc)
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        seven_days_ago = now - timedelta(days=7)
        thirty_days_ago = now - timedelta(days=30)

        # User statistics
        total_users = await self.db.users.count_documents({})
        active_users = await self.db.users.count_documents({"is_active": True, "is_banned": False})
        banned_users = await self.db.users.count_documents({"is_banned": True})
        new_users_today = await self.db.users.count_documents({
            "created_at": {"$gte": today_start}
        })
        new_users_week = await self.db.users.count_documents({
            "created_at": {"$gte": seven_days_ago}
        })

        # User role distribution
        role_pipeline = [
            {"$group": {"_id": "$role", "count": {"$sum": 1}}},
            {"$sort": {"count": -1}}
        ]
        role_results = await self.db.users.aggregate(role_pipeline).to_list(10)
        users_by_role = {item["_id"]: item["count"] for item in role_results if item["_id"]}

        # Report statistics
        total_reports = await self.db.hazard_reports.count_documents({})
        pending_reports = await self.db.hazard_reports.count_documents({
            "$or": [
                {"verification_status": "pending"},
                {"status": "pending"}
            ]
        })
        verified_reports = await self.db.hazard_reports.count_documents({
            "$or": [
                {"verification_status": "verified"},
                {"status": "verified"}
            ]
        })
        reports_today = await self.db.hazard_reports.count_documents({
            "created_at": {"$gte": today_start}
        })

        # Alert statistics
        total_alerts = await self.db.alerts.count_documents({})
        active_alerts = await self.db.alerts.count_documents({"status": "active"})
        critical_alerts = await self.db.alerts.count_documents({
            "status": "active",
            "severity": {"$in": ["critical", "high"]}
        })

        # System activity (last 24 hours)
        yesterday = now - timedelta(days=1)
        logins_24h = await self.db.audit_logs.count_documents({
            "action": "login",
            "success": True,
            "timestamp": {"$gte": yesterday}
        })

        # Error counts (if error_logs collection exists)
        try:
            errors_24h = await self.db.error_logs.count_documents({
                "timestamp": {"$gte": yesterday}
            })
            unresolved_errors = await self.db.error_logs.count_documents({
                "resolved": False
            })
        except Exception:
            errors_24h = 0
            unresolved_errors = 0

        # Recent admin actions
        recent_admin_actions = await self.db.admin_activity_logs.count_documents({
            "timestamp": {"$gte": seven_days_ago}
        })

        return {
            "users": {
                "total": total_users,
                "active": active_users,
                "banned": banned_users,
                "new_today": new_users_today,
                "new_this_week": new_users_week,
                "by_role": users_by_role
            },
            "reports": {
                "total": total_reports,
                "pending": pending_reports,
                "verified": verified_reports,
                "today": reports_today,
                "verification_rate": round((verified_reports / max(total_reports, 1)) * 100, 1)
            },
            "alerts": {
                "total": total_alerts,
                "active": active_alerts,
                "critical": critical_alerts
            },
            "system": {
                "logins_24h": logins_24h,
                "errors_24h": errors_24h,
                "unresolved_errors": unresolved_errors,
                "admin_actions_week": recent_admin_actions
            },
            "last_updated": now.isoformat()
        }

    # =========================================================================
    # USER MANAGEMENT
    # =========================================================================

    async def get_users_paginated(
        self,
        page: int = 1,
        limit: int = 20,
        search: Optional[str] = None,
        role: Optional[str] = None,
        status: Optional[str] = None,
        sort_by: str = "created_at",
        sort_order: str = "desc"
    ) -> Dict[str, Any]:
        """Get paginated list of users with filters."""
        query = {}

        # Search filter
        if search:
            query["$or"] = [
                {"name": {"$regex": search, "$options": "i"}},
                {"email": {"$regex": search, "$options": "i"}},
                {"phone": {"$regex": search, "$options": "i"}},
                {"user_id": {"$regex": search, "$options": "i"}}
            ]

        # Role filter
        if role and role != "all":
            query["role"] = role

        # Status filter
        if status == "active":
            query["is_active"] = True
            query["is_banned"] = False
        elif status == "inactive":
            query["is_active"] = False
        elif status == "banned":
            query["is_banned"] = True

        # Pagination
        skip = (page - 1) * limit
        total = await self.db.users.count_documents(query)
        total_pages = (total + limit - 1) // limit

        # Sorting
        sort_direction = -1 if sort_order == "desc" else 1
        sort_field = sort_by if sort_by in ["created_at", "name", "email", "role", "credibility_score"] else "created_at"

        # Fetch users
        cursor = self.db.users.find(query).sort(sort_field, sort_direction).skip(skip).limit(limit)
        users = await cursor.to_list(limit)

        # Format users (exclude sensitive fields)
        formatted_users = []
        for user in users:
            formatted_users.append({
                "user_id": user.get("user_id"),
                "email": user.get("email"),
                "phone": user.get("phone"),
                "name": user.get("name"),
                "role": user.get("role"),
                "is_active": user.get("is_active", True),
                "is_banned": user.get("is_banned", False),
                "ban_reason": user.get("ban_reason"),
                "credibility_score": user.get("credibility_score", 50),
                "total_reports": user.get("total_reports", 0),
                "verified_reports": user.get("verified_reports", 0),
                "email_verified": user.get("email_verified", False),
                "phone_verified": user.get("phone_verified", False),
                "auth_provider": user.get("auth_provider", "local"),
                "authority_organization": user.get("authority_organization"),
                "authority_designation": user.get("authority_designation"),
                "created_at": user.get("created_at").isoformat() if user.get("created_at") else None,
                "last_login": user.get("last_login").isoformat() if user.get("last_login") else None
            })

        return {
            "users": formatted_users,
            "pagination": {
                "page": page,
                "limit": limit,
                "total_count": total,
                "total_pages": total_pages,
                "has_next": page < total_pages,
                "has_prev": page > 1
            }
        }

    async def get_user_details(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed user information including activity history."""
        user = await self.db.users.find_one({"user_id": user_id})
        if not user:
            return None

        # Get user's report statistics
        report_stats = await self.db.hazard_reports.aggregate([
            {"$match": {"user_id": user_id}},
            {"$group": {
                "_id": None,
                "total": {"$sum": 1},
                "verified": {"$sum": {"$cond": [{"$eq": ["$verification_status", "verified"]}, 1, 0]}},
                "pending": {"$sum": {"$cond": [{"$eq": ["$verification_status", "pending"]}, 1, 0]}},
                "rejected": {"$sum": {"$cond": [{"$eq": ["$verification_status", "rejected"]}, 1, 0]}}
            }}
        ]).to_list(1)
        report_stats = report_stats[0] if report_stats else {"total": 0, "verified": 0, "pending": 0, "rejected": 0}

        # Get recent activity (audit logs)
        recent_activity = await self.db.audit_logs.find(
            {"user_id": user_id}
        ).sort("timestamp", -1).limit(20).to_list(20)

        activity_list = []
        for log in recent_activity:
            activity_list.append({
                "action": log.get("action"),
                "details": log.get("details", {}),
                "ip_address": log.get("ip_address"),
                "success": log.get("success", True),
                "timestamp": log.get("timestamp").isoformat() if log.get("timestamp") else None
            })

        # Get role change history
        role_history = await self.db.admin_activity_logs.find({
            "target_id": user_id,
            "action": AdminActionType.ROLE_CHANGED.value
        }).sort("timestamp", -1).limit(10).to_list(10)

        role_changes = []
        for change in role_history:
            role_changes.append({
                "changed_by": change.get("admin_name"),
                "previous_role": change.get("previous_value"),
                "new_role": change.get("new_value"),
                "reason": change.get("details", {}).get("reason"),
                "timestamp": change.get("timestamp").isoformat() if change.get("timestamp") else None
            })

        return {
            "user_id": user.get("user_id"),
            "email": user.get("email"),
            "phone": user.get("phone"),
            "name": user.get("name"),
            "profile_picture": user.get("profile_picture"),
            "role": user.get("role"),
            "is_active": user.get("is_active", True),
            "is_banned": user.get("is_banned", False),
            "ban_reason": user.get("ban_reason"),
            "banned_at": user.get("banned_at").isoformat() if user.get("banned_at") else None,
            "banned_by": user.get("banned_by"),
            "credibility_score": user.get("credibility_score", 50),
            "email_verified": user.get("email_verified", False),
            "phone_verified": user.get("phone_verified", False),
            "two_factor_enabled": user.get("two_factor_enabled", False),
            "auth_provider": user.get("auth_provider", "local"),
            "authority_organization": user.get("authority_organization"),
            "authority_designation": user.get("authority_designation"),
            "authority_jurisdiction": user.get("authority_jurisdiction"),
            "notification_preferences": user.get("notification_preferences", {}),
            "location": user.get("location"),
            "created_at": user.get("created_at").isoformat() if user.get("created_at") else None,
            "updated_at": user.get("updated_at").isoformat() if user.get("updated_at") else None,
            "last_login": user.get("last_login").isoformat() if user.get("last_login") else None,
            "role_assigned_by": user.get("role_assigned_by"),
            "role_assigned_at": user.get("role_assigned_at").isoformat() if user.get("role_assigned_at") else None,
            "report_statistics": report_stats,
            "recent_activity": activity_list,
            "role_history": role_changes
        }

    async def create_user(
        self,
        user_data: Dict[str, Any],
        admin_id: str,
        admin_name: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create a new user."""
        now = datetime.now(timezone.utc)

        # Check for existing user
        existing = await self.db.users.find_one({
            "$or": [
                {"email": user_data.get("email")} if user_data.get("email") else {"_id": None},
                {"phone": user_data.get("phone")} if user_data.get("phone") else {"_id": None}
            ]
        })
        if existing:
            raise ValueError("User with this email or phone already exists")

        # Validate role
        role = user_data.get("role", "citizen")
        valid_roles = [r.value for r in UserRole]
        if role not in valid_roles:
            raise ValueError(f"Invalid role. Must be one of: {valid_roles}")

        # Create user document
        user_id = self._generate_id("USR")
        hashed_password = hash_password(user_data["password"])

        new_user = {
            "user_id": user_id,
            "email": user_data.get("email"),
            "phone": user_data.get("phone"),
            "name": user_data["name"],
            "hashed_password": hashed_password,
            "role": role,
            "auth_provider": "local",
            "is_active": True,
            "is_banned": False,
            "email_verified": False,
            "phone_verified": False,
            "credibility_score": 50,
            "total_reports": 0,
            "verified_reports": 0,
            "notification_preferences": {
                "alerts_enabled": True,
                "channels": ["push"],
                "email_notifications": True,
                "sms_notifications": False
            },
            "role_assigned_by": admin_id,
            "role_assigned_at": now,
            "authority_organization": user_data.get("authority_organization"),
            "authority_designation": user_data.get("authority_designation"),
            "authority_jurisdiction": user_data.get("authority_jurisdiction"),
            "created_at": now,
            "updated_at": now
        }

        await self.db.users.insert_one(new_user)

        # Log admin action
        await self._log_admin_action(
            admin_id=admin_id,
            admin_name=admin_name,
            action=AdminActionType.USER_CREATED,
            target_type="user",
            target_id=user_id,
            target_name=user_data["name"],
            details={"role": role, "email": user_data.get("email")},
            ip_address=ip_address,
            user_agent=user_agent
        )

        return {"user_id": user_id, "name": user_data["name"], "role": role}

    async def update_user(
        self,
        user_id: str,
        update_data: Dict[str, Any],
        admin_id: str,
        admin_name: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> Dict[str, Any]:
        """Update user details."""
        user = await self.db.users.find_one({"user_id": user_id})
        if not user:
            raise ValueError("User not found")

        # Build update document
        update_fields = {}
        changes = {}

        allowed_fields = [
            "name", "email", "phone", "is_active", "credibility_score",
            "authority_organization", "authority_designation", "authority_jurisdiction"
        ]

        for field in allowed_fields:
            if field in update_data and update_data[field] is not None:
                old_value = user.get(field)
                new_value = update_data[field]
                if old_value != new_value:
                    update_fields[field] = new_value
                    changes[field] = {"old": old_value, "new": new_value}

        if not update_fields:
            return {"message": "No changes to update"}

        update_fields["updated_at"] = datetime.now(timezone.utc)

        await self.db.users.update_one(
            {"user_id": user_id},
            {"$set": update_fields}
        )

        # Log admin action
        await self._log_admin_action(
            admin_id=admin_id,
            admin_name=admin_name,
            action=AdminActionType.USER_UPDATED,
            target_type="user",
            target_id=user_id,
            target_name=user.get("name"),
            details={"changes": changes},
            ip_address=ip_address,
            user_agent=user_agent
        )

        return {"user_id": user_id, "updated_fields": list(update_fields.keys())}

    async def ban_user(
        self,
        user_id: str,
        reason: str,
        admin_id: str,
        admin_name: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> Dict[str, Any]:
        """Ban a user."""
        user = await self.db.users.find_one({"user_id": user_id})
        if not user:
            raise ValueError("User not found")

        if user_id == admin_id:
            raise ValueError("Cannot ban yourself")

        if user.get("is_banned"):
            raise ValueError("User is already banned")

        now = datetime.now(timezone.utc)
        await self.db.users.update_one(
            {"user_id": user_id},
            {"$set": {
                "is_banned": True,
                "ban_reason": reason,
                "banned_at": now,
                "banned_by": admin_id,
                "updated_at": now
            }}
        )

        # Log admin action
        await self._log_admin_action(
            admin_id=admin_id,
            admin_name=admin_name,
            action=AdminActionType.USER_BANNED,
            target_type="user",
            target_id=user_id,
            target_name=user.get("name"),
            details={"reason": reason},
            ip_address=ip_address,
            user_agent=user_agent
        )

        return {"user_id": user_id, "banned": True, "reason": reason}

    async def unban_user(
        self,
        user_id: str,
        admin_id: str,
        admin_name: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> Dict[str, Any]:
        """Unban a user."""
        user = await self.db.users.find_one({"user_id": user_id})
        if not user:
            raise ValueError("User not found")

        if not user.get("is_banned"):
            raise ValueError("User is not banned")

        previous_reason = user.get("ban_reason")

        await self.db.users.update_one(
            {"user_id": user_id},
            {"$set": {
                "is_banned": False,
                "ban_reason": None,
                "banned_at": None,
                "banned_by": None,
                "updated_at": datetime.now(timezone.utc)
            }}
        )

        # Log admin action
        await self._log_admin_action(
            admin_id=admin_id,
            admin_name=admin_name,
            action=AdminActionType.USER_UNBANNED,
            target_type="user",
            target_id=user_id,
            target_name=user.get("name"),
            details={"previous_ban_reason": previous_reason},
            ip_address=ip_address,
            user_agent=user_agent
        )

        return {"user_id": user_id, "banned": False}

    async def assign_role(
        self,
        user_id: str,
        new_role: str,
        reason: Optional[str],
        admin_id: str,
        admin_name: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> Dict[str, Any]:
        """Assign a new role to a user."""
        user = await self.db.users.find_one({"user_id": user_id})
        if not user:
            raise ValueError("User not found")

        # Validate role
        valid_roles = [r.value for r in UserRole]
        if new_role not in valid_roles:
            raise ValueError(f"Invalid role. Must be one of: {valid_roles}")

        previous_role = user.get("role")
        if previous_role == new_role:
            raise ValueError("User already has this role")

        now = datetime.now(timezone.utc)
        await self.db.users.update_one(
            {"user_id": user_id},
            {"$set": {
                "role": new_role,
                "previous_role": previous_role,
                "role_assigned_by": admin_id,
                "role_assigned_at": now,
                "updated_at": now
            }}
        )

        # Log admin action
        await self._log_admin_action(
            admin_id=admin_id,
            admin_name=admin_name,
            action=AdminActionType.ROLE_CHANGED,
            target_type="user",
            target_id=user_id,
            target_name=user.get("name"),
            details={"reason": reason},
            previous_value=previous_role,
            new_value=new_role,
            ip_address=ip_address,
            user_agent=user_agent
        )

        return {
            "user_id": user_id,
            "previous_role": previous_role,
            "new_role": new_role
        }

    async def delete_user(
        self,
        user_id: str,
        admin_id: str,
        admin_name: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> Dict[str, Any]:
        """Soft delete a user (mark as inactive)."""
        user = await self.db.users.find_one({"user_id": user_id})
        if not user:
            raise ValueError("User not found")

        if user_id == admin_id:
            raise ValueError("Cannot delete yourself")

        await self.db.users.update_one(
            {"user_id": user_id},
            {"$set": {
                "is_active": False,
                "deleted_at": datetime.now(timezone.utc),
                "deleted_by": admin_id,
                "updated_at": datetime.now(timezone.utc)
            }}
        )

        # Log admin action
        await self._log_admin_action(
            admin_id=admin_id,
            admin_name=admin_name,
            action=AdminActionType.USER_DELETED,
            target_type="user",
            target_id=user_id,
            target_name=user.get("name"),
            ip_address=ip_address,
            user_agent=user_agent
        )

        return {"user_id": user_id, "deleted": True}

    # =========================================================================
    # CONTENT MODERATION
    # =========================================================================

    async def get_reports_paginated(
        self,
        page: int = 1,
        limit: int = 20,
        status: Optional[str] = None,
        hazard_type: Optional[str] = None,
        search: Optional[str] = None,
        date_range: str = "all"
    ) -> Dict[str, Any]:
        """Get paginated list of hazard reports for moderation."""
        query = {}

        if status and status != "all":
            query["$or"] = [
                {"verification_status": status},
                {"status": status}
            ]

        if hazard_type and hazard_type != "all":
            query["hazard_type"] = hazard_type

        if search:
            query["$or"] = [
                {"description": {"$regex": search, "$options": "i"}},
                {"report_id": {"$regex": search, "$options": "i"}},
                {"user_id": {"$regex": search, "$options": "i"}}
            ]

        if date_range != "all":
            dates = self._get_date_range(date_range)
            query["created_at"] = {"$gte": dates["start"], "$lte": dates["end"]}

        skip = (page - 1) * limit
        total = await self.db.hazard_reports.count_documents(query)
        total_pages = (total + limit - 1) // limit

        cursor = self.db.hazard_reports.find(query).sort("created_at", -1).skip(skip).limit(limit)
        reports = await cursor.to_list(limit)

        formatted_reports = []
        for report in reports:
            formatted_reports.append({
                "report_id": report.get("report_id"),
                "user_id": report.get("user_id"),
                "hazard_type": report.get("hazard_type"),
                "description": report.get("description"),
                "location": report.get("location"),
                "image_url": report.get("image_url"),
                "verification_status": report.get("verification_status", report.get("status")),
                "risk_level": report.get("risk_level"),
                "verified_by": report.get("verified_by"),
                "created_at": report.get("created_at").isoformat() if report.get("created_at") else None
            })

        return {
            "reports": formatted_reports,
            "pagination": {
                "page": page,
                "limit": limit,
                "total_count": total,
                "total_pages": total_pages,
                "has_next": page < total_pages,
                "has_prev": page > 1
            }
        }

    async def delete_report(
        self,
        report_id: str,
        admin_id: str,
        admin_name: str,
        reason: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> Dict[str, Any]:
        """Delete a hazard report."""
        report = await self.db.hazard_reports.find_one({"report_id": report_id})
        if not report:
            raise ValueError("Report not found")

        # Soft delete
        await self.db.hazard_reports.update_one(
            {"report_id": report_id},
            {"$set": {
                "deleted": True,
                "deleted_at": datetime.now(timezone.utc),
                "deleted_by": admin_id,
                "deletion_reason": reason
            }}
        )

        # Log admin action
        await self._log_admin_action(
            admin_id=admin_id,
            admin_name=admin_name,
            action=AdminActionType.REPORT_DELETED,
            target_type="report",
            target_id=report_id,
            details={"reason": reason, "hazard_type": report.get("hazard_type")},
            ip_address=ip_address,
            user_agent=user_agent
        )

        return {"report_id": report_id, "deleted": True}

    async def get_alerts_paginated(
        self,
        page: int = 1,
        limit: int = 20,
        status: Optional[str] = None,
        severity: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get paginated list of alerts."""
        query = {}

        if status and status != "all":
            query["status"] = status

        if severity and severity != "all":
            query["severity"] = severity

        skip = (page - 1) * limit
        total = await self.db.alerts.count_documents(query)
        total_pages = (total + limit - 1) // limit

        cursor = self.db.alerts.find(query).sort("created_at", -1).skip(skip).limit(limit)
        alerts = await cursor.to_list(limit)

        formatted_alerts = []
        for alert in alerts:
            formatted_alerts.append({
                "alert_id": alert.get("alert_id"),
                "title": alert.get("title"),
                "description": alert.get("description"),
                "alert_type": alert.get("alert_type"),
                "severity": alert.get("severity"),
                "status": alert.get("status"),
                "regions": alert.get("regions", []),
                "created_by": alert.get("created_by"),
                "created_at": alert.get("created_at").isoformat() if alert.get("created_at") else None,
                "expires_at": alert.get("expires_at").isoformat() if alert.get("expires_at") else None
            })

        return {
            "alerts": formatted_alerts,
            "pagination": {
                "page": page,
                "limit": limit,
                "total_count": total,
                "total_pages": total_pages,
                "has_next": page < total_pages,
                "has_prev": page > 1
            }
        }

    async def delete_alert(
        self,
        alert_id: str,
        admin_id: str,
        admin_name: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> Dict[str, Any]:
        """Delete an alert."""
        alert = await self.db.alerts.find_one({"alert_id": alert_id})
        if not alert:
            raise ValueError("Alert not found")

        await self.db.alerts.delete_one({"alert_id": alert_id})

        # Log admin action
        await self._log_admin_action(
            admin_id=admin_id,
            admin_name=admin_name,
            action=AdminActionType.ALERT_DELETED,
            target_type="alert",
            target_id=alert_id,
            target_name=alert.get("title"),
            ip_address=ip_address,
            user_agent=user_agent
        )

        return {"alert_id": alert_id, "deleted": True}

    # =========================================================================
    # SYSTEM MONITORING
    # =========================================================================

    async def get_system_health(self) -> Dict[str, Any]:
        """Get comprehensive system health status."""
        health_data = {
            "overall_status": HealthStatus.HEALTHY.value,
            "components": {},
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

        # Database health
        try:
            await self.db.command("ping")
            db_stats = await self.db.command("dbStats")
            health_data["components"]["database"] = {
                "status": HealthStatus.HEALTHY.value,
                "details": {
                    "collections": db_stats.get("collections", 0),
                    "data_size_mb": round(db_stats.get("dataSize", 0) / (1024 * 1024), 2),
                    "storage_size_mb": round(db_stats.get("storageSize", 0) / (1024 * 1024), 2),
                    "indexes": db_stats.get("indexes", 0)
                }
            }
        except Exception as e:
            health_data["components"]["database"] = {
                "status": HealthStatus.CRITICAL.value,
                "error": str(e)
            }
            health_data["overall_status"] = HealthStatus.CRITICAL.value

        # Storage health (check uploads directory)
        try:
            uploads_path = "uploads"
            if os.path.exists(uploads_path):
                total_size = 0
                file_count = 0
                for dirpath, dirnames, filenames in os.walk(uploads_path):
                    for f in filenames:
                        fp = os.path.join(dirpath, f)
                        total_size += os.path.getsize(fp)
                        file_count += 1

                health_data["components"]["storage"] = {
                    "status": HealthStatus.HEALTHY.value,
                    "details": {
                        "total_files": file_count,
                        "total_size_mb": round(total_size / (1024 * 1024), 2)
                    }
                }
            else:
                health_data["components"]["storage"] = {
                    "status": HealthStatus.WARNING.value,
                    "message": "Uploads directory not found"
                }
        except Exception as e:
            health_data["components"]["storage"] = {
                "status": HealthStatus.WARNING.value,
                "error": str(e)
            }

        # API health (check recent response times from logs if available)
        try:
            one_hour_ago = datetime.now(timezone.utc) - timedelta(hours=1)
            api_stats = await self.db.api_request_logs.aggregate([
                {"$match": {"timestamp": {"$gte": one_hour_ago}}},
                {"$group": {
                    "_id": None,
                    "total_requests": {"$sum": 1},
                    "avg_response_time": {"$avg": "$response_time_ms"},
                    "error_count": {"$sum": {"$cond": [{"$gte": ["$status_code", 500]}, 1, 0]}}
                }}
            ]).to_list(1)

            if api_stats:
                stats = api_stats[0]
                error_rate = (stats["error_count"] / max(stats["total_requests"], 1)) * 100

                status = HealthStatus.HEALTHY.value
                if error_rate > 5:
                    status = HealthStatus.WARNING.value
                if error_rate > 10:
                    status = HealthStatus.CRITICAL.value

                health_data["components"]["api"] = {
                    "status": status,
                    "details": {
                        "requests_last_hour": stats["total_requests"],
                        "avg_response_time_ms": round(stats["avg_response_time"] or 0, 2),
                        "error_rate": round(error_rate, 2)
                    }
                }
            else:
                health_data["components"]["api"] = {
                    "status": HealthStatus.HEALTHY.value,
                    "message": "No recent request data"
                }
        except Exception:
            health_data["components"]["api"] = {
                "status": HealthStatus.UNKNOWN.value,
                "message": "API logging not available"
            }

        return health_data

    async def get_api_statistics(self, date_range: str = "7days") -> Dict[str, Any]:
        """Get API usage statistics."""
        dates = self._get_date_range(date_range)

        try:
            # Total requests
            total_requests = await self.db.api_request_logs.count_documents({
                "timestamp": {"$gte": dates["start"], "$lte": dates["end"]}
            })

            # Requests by endpoint
            endpoint_stats = await self.db.api_request_logs.aggregate([
                {"$match": {"timestamp": {"$gte": dates["start"], "$lte": dates["end"]}}},
                {"$group": {
                    "_id": "$endpoint",
                    "count": {"$sum": 1},
                    "avg_response_time": {"$avg": "$response_time_ms"}
                }},
                {"$sort": {"count": -1}},
                {"$limit": 20}
            ]).to_list(20)

            # Requests by status code
            status_stats = await self.db.api_request_logs.aggregate([
                {"$match": {"timestamp": {"$gte": dates["start"], "$lte": dates["end"]}}},
                {"$group": {
                    "_id": "$status_code",
                    "count": {"$sum": 1}
                }},
                {"$sort": {"_id": 1}}
            ]).to_list(100)

            # Daily request counts
            daily_stats = await self.db.api_request_logs.aggregate([
                {"$match": {"timestamp": {"$gte": dates["start"], "$lte": dates["end"]}}},
                {"$group": {
                    "_id": {
                        "year": {"$year": "$timestamp"},
                        "month": {"$month": "$timestamp"},
                        "day": {"$dayOfMonth": "$timestamp"}
                    },
                    "count": {"$sum": 1},
                    "avg_response_time": {"$avg": "$response_time_ms"}
                }},
                {"$sort": {"_id.year": 1, "_id.month": 1, "_id.day": 1}}
            ]).to_list(100)

            return {
                "total_requests": total_requests,
                "by_endpoint": [{"endpoint": e["_id"], "count": e["count"], "avg_ms": round(e["avg_response_time"] or 0, 2)} for e in endpoint_stats],
                "by_status_code": {str(s["_id"]): s["count"] for s in status_stats},
                "daily_trend": [
                    {
                        "date": f"{d['_id']['year']}-{d['_id']['month']:02d}-{d['_id']['day']:02d}",
                        "count": d["count"],
                        "avg_response_time_ms": round(d["avg_response_time"] or 0, 2)
                    }
                    for d in daily_stats
                ],
                "date_range": {"start": dates["start"].isoformat(), "end": dates["end"].isoformat()}
            }
        except Exception as e:
            logger.warning(f"API statistics not available: {e}")
            return {
                "message": "API request logging not enabled",
                "total_requests": 0,
                "by_endpoint": [],
                "by_status_code": {},
                "daily_trend": []
            }

    async def get_error_logs(
        self,
        page: int = 1,
        limit: int = 20,
        level: Optional[str] = None,
        resolved: Optional[bool] = None
    ) -> Dict[str, Any]:
        """Get paginated error logs."""
        query = {}

        if level:
            query["level"] = level

        if resolved is not None:
            query["resolved"] = resolved

        try:
            skip = (page - 1) * limit
            total = await self.db.error_logs.count_documents(query)
            total_pages = (total + limit - 1) // limit

            cursor = self.db.error_logs.find(query).sort("timestamp", -1).skip(skip).limit(limit)
            errors = await cursor.to_list(limit)

            formatted_errors = []
            for error in errors:
                formatted_errors.append({
                    "error_id": error.get("error_id"),
                    "level": error.get("level"),
                    "message": error.get("message"),
                    "source": error.get("source"),
                    "request_path": error.get("request_path"),
                    "resolved": error.get("resolved", False),
                    "timestamp": error.get("timestamp").isoformat() if error.get("timestamp") else None
                })

            return {
                "errors": formatted_errors,
                "pagination": {
                    "page": page,
                    "limit": limit,
                    "total_count": total,
                    "total_pages": total_pages
                }
            }
        except Exception:
            return {
                "errors": [],
                "message": "Error logging not enabled",
                "pagination": {"page": 1, "limit": limit, "total_count": 0, "total_pages": 0}
            }

    # =========================================================================
    # SYSTEM SETTINGS
    # =========================================================================

    async def get_all_settings(self) -> Dict[str, Any]:
        """Get all system settings grouped by category."""
        settings = await self.db.system_settings.find({}).to_list(1000)

        grouped = {}
        for setting in settings:
            category = setting.get("category", "general")
            if category not in grouped:
                grouped[category] = []

            setting_data = {
                "setting_id": setting.get("setting_id"),
                "key": setting.get("key"),
                "value": "********" if setting.get("is_sensitive") else setting.get("value"),
                "value_type": setting.get("value_type"),
                "label": setting.get("label"),
                "description": setting.get("description"),
                "is_sensitive": setting.get("is_sensitive", False),
                "is_editable": setting.get("is_editable", True),
                "updated_at": setting.get("updated_at").isoformat() if setting.get("updated_at") else None
            }
            grouped[category].append(setting_data)

        return {"settings": grouped}

    async def get_settings_by_category(self, category: str) -> Dict[str, Any]:
        """Get settings for a specific category."""
        settings = await self.db.system_settings.find({"category": category}).to_list(100)

        formatted = []
        for setting in settings:
            formatted.append({
                "setting_id": setting.get("setting_id"),
                "key": setting.get("key"),
                "value": "********" if setting.get("is_sensitive") else setting.get("value"),
                "value_type": setting.get("value_type"),
                "label": setting.get("label"),
                "description": setting.get("description"),
                "is_sensitive": setting.get("is_sensitive", False),
                "is_editable": setting.get("is_editable", True)
            })

        return {"category": category, "settings": formatted}

    async def update_setting(
        self,
        key: str,
        value: Any,
        admin_id: str,
        admin_name: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> Dict[str, Any]:
        """Update a system setting."""
        setting = await self.db.system_settings.find_one({"key": key})
        if not setting:
            raise ValueError("Setting not found")

        if not setting.get("is_editable", True):
            raise ValueError("This setting cannot be edited")

        previous_value = setting.get("value")

        await self.db.system_settings.update_one(
            {"key": key},
            {"$set": {
                "value": value,
                "updated_by": admin_id,
                "updated_at": datetime.now(timezone.utc)
            }}
        )

        # Log admin action
        await self._log_admin_action(
            admin_id=admin_id,
            admin_name=admin_name,
            action=AdminActionType.SETTING_UPDATED,
            target_type="setting",
            target_id=setting.get("setting_id"),
            target_name=key,
            previous_value="[hidden]" if setting.get("is_sensitive") else previous_value,
            new_value="[hidden]" if setting.get("is_sensitive") else value,
            ip_address=ip_address,
            user_agent=user_agent
        )

        return {"key": key, "updated": True}

    async def create_setting(
        self,
        setting_data: Dict[str, Any],
        admin_id: str,
        admin_name: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create a new system setting."""
        existing = await self.db.system_settings.find_one({"key": setting_data["key"]})
        if existing:
            raise ValueError("Setting with this key already exists")

        setting_id = self._generate_id("SET")
        now = datetime.now(timezone.utc)

        new_setting = {
            "setting_id": setting_id,
            "category": setting_data["category"],
            "key": setting_data["key"],
            "value": setting_data["value"],
            "value_type": setting_data["value_type"],
            "label": setting_data["label"],
            "description": setting_data["description"],
            "is_sensitive": setting_data.get("is_sensitive", False),
            "is_editable": setting_data.get("is_editable", True),
            "validation_rules": setting_data.get("validation_rules"),
            "updated_by": admin_id,
            "created_at": now,
            "updated_at": now
        }

        await self.db.system_settings.insert_one(new_setting)

        # Log admin action
        await self._log_admin_action(
            admin_id=admin_id,
            admin_name=admin_name,
            action=AdminActionType.SETTING_CREATED,
            target_type="setting",
            target_id=setting_id,
            target_name=setting_data["key"],
            ip_address=ip_address,
            user_agent=user_agent
        )

        return {"setting_id": setting_id, "key": setting_data["key"]}

    # =========================================================================
    # AUDIT LOGS
    # =========================================================================

    async def get_audit_logs(
        self,
        page: int = 1,
        limit: int = 50,
        action: Optional[str] = None,
        user_id: Optional[str] = None,
        date_range: str = "7days",
        search: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get paginated audit logs with filters."""
        query = {}

        if action and action != "all":
            query["action"] = action

        if user_id:
            query["user_id"] = user_id

        if date_range != "all":
            dates = self._get_date_range(date_range)
            query["timestamp"] = {"$gte": dates["start"], "$lte": dates["end"]}

        if search:
            query["$or"] = [
                {"action": {"$regex": search, "$options": "i"}},
                {"user_id": {"$regex": search, "$options": "i"}},
                {"details": {"$regex": search, "$options": "i"}}
            ]

        skip = (page - 1) * limit
        total = await self.db.audit_logs.count_documents(query)
        total_pages = (total + limit - 1) // limit

        cursor = self.db.audit_logs.find(query).sort("timestamp", -1).skip(skip).limit(limit)
        logs = await cursor.to_list(limit)

        formatted_logs = []
        for log in logs:
            formatted_logs.append({
                "user_id": log.get("user_id"),
                "action": log.get("action"),
                "details": log.get("details", {}),
                "ip_address": log.get("ip_address"),
                "user_agent": log.get("user_agent"),
                "success": log.get("success", True),
                "error_message": log.get("error_message"),
                "timestamp": log.get("timestamp").isoformat() if log.get("timestamp") else None
            })

        return {
            "logs": formatted_logs,
            "pagination": {
                "page": page,
                "limit": limit,
                "total_count": total,
                "total_pages": total_pages,
                "has_next": page < total_pages,
                "has_prev": page > 1
            }
        }

    async def get_admin_activity_logs(
        self,
        page: int = 1,
        limit: int = 50,
        action: Optional[str] = None,
        admin_id: Optional[str] = None,
        date_range: str = "7days"
    ) -> Dict[str, Any]:
        """Get admin-specific activity logs."""
        query = {}

        if action and action != "all":
            query["action"] = action

        if admin_id:
            query["admin_id"] = admin_id

        if date_range != "all":
            dates = self._get_date_range(date_range)
            query["timestamp"] = {"$gte": dates["start"], "$lte": dates["end"]}

        skip = (page - 1) * limit
        total = await self.db.admin_activity_logs.count_documents(query)
        total_pages = (total + limit - 1) // limit

        cursor = self.db.admin_activity_logs.find(query).sort("timestamp", -1).skip(skip).limit(limit)
        logs = await cursor.to_list(limit)

        formatted_logs = []
        for log in logs:
            formatted_logs.append({
                "log_id": log.get("log_id"),
                "admin_id": log.get("admin_id"),
                "admin_name": log.get("admin_name"),
                "action": log.get("action"),
                "target_type": log.get("target_type"),
                "target_id": log.get("target_id"),
                "target_name": log.get("target_name"),
                "details": log.get("details", {}),
                "previous_value": log.get("previous_value"),
                "new_value": log.get("new_value"),
                "success": log.get("success", True),
                "timestamp": log.get("timestamp").isoformat() if log.get("timestamp") else None
            })

        return {
            "logs": formatted_logs,
            "pagination": {
                "page": page,
                "limit": limit,
                "total_count": total,
                "total_pages": total_pages,
                "has_next": page < total_pages,
                "has_prev": page > 1
            }
        }

    async def get_audit_stats(self, date_range: str = "7days") -> Dict[str, Any]:
        """Get audit log statistics."""
        dates = self._get_date_range(date_range)

        # Actions distribution
        action_stats = await self.db.audit_logs.aggregate([
            {"$match": {"timestamp": {"$gte": dates["start"], "$lte": dates["end"]}}},
            {"$group": {"_id": "$action", "count": {"$sum": 1}}},
            {"$sort": {"count": -1}},
            {"$limit": 20}
        ]).to_list(20)

        # Success rate
        total_logs = await self.db.audit_logs.count_documents({
            "timestamp": {"$gte": dates["start"], "$lte": dates["end"]}
        })
        failed_logs = await self.db.audit_logs.count_documents({
            "timestamp": {"$gte": dates["start"], "$lte": dates["end"]},
            "success": False
        })

        # Most active users
        user_stats = await self.db.audit_logs.aggregate([
            {"$match": {"timestamp": {"$gte": dates["start"], "$lte": dates["end"]}}},
            {"$group": {"_id": "$user_id", "count": {"$sum": 1}}},
            {"$sort": {"count": -1}},
            {"$limit": 10}
        ]).to_list(10)

        return {
            "total_logs": total_logs,
            "failed_actions": failed_logs,
            "success_rate": round(((total_logs - failed_logs) / max(total_logs, 1)) * 100, 1),
            "by_action": {a["_id"]: a["count"] for a in action_stats if a["_id"]},
            "most_active_users": [{"user_id": u["_id"], "count": u["count"]} for u in user_stats if u["_id"]],
            "date_range": {"start": dates["start"].isoformat(), "end": dates["end"].isoformat()}
        }


# Singleton instance helper
_admin_service: Optional[AdminService] = None


def get_admin_service(db: AsyncIOMotorDatabase) -> AdminService:
    """Get or create admin service instance."""
    global _admin_service
    if _admin_service is None or _admin_service.db != db:
        _admin_service = AdminService(db)
    return _admin_service


__all__ = [
    'AdminService',
    'get_admin_service'
]
