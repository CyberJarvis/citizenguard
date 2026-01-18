"""
Admin API Endpoints
Super Admin panel for system management, user control, monitoring, and settings
"""

import logging
from datetime import datetime, timezone
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from fastapi.responses import StreamingResponse
from motor.motor_asyncio import AsyncIOMotorDatabase
from pydantic import BaseModel, Field
import csv
import io

from app.database import get_database
from app.models.user import User
from app.models.admin import (
    CreateUserRequest, UpdateUserRequest, BanUserRequest,
    AssignRoleRequest, CreateSettingRequest, UpdateSettingRequest,
    SettingCategory, SettingValueType, AdminActionType
)
from app.models.rbac import UserRole, Permission
from app.middleware.rbac import require_admin, get_current_user
from app.services.admin_service import AdminService, get_admin_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin", tags=["admin"])


# ============================================================================
# Helper Functions
# ============================================================================

def get_client_info(request: Request) -> tuple:
    """Extract IP address and user agent from request."""
    # Handle potential proxy headers
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        ip_address = forwarded_for.split(",")[0].strip()
    else:
        ip_address = request.client.host if request.client else None

    user_agent = request.headers.get("User-Agent")
    return ip_address, user_agent


# ============================================================================
# Dashboard & Statistics
# ============================================================================

@router.get("/dashboard")
async def get_admin_dashboard(
    current_user: User = Depends(require_admin),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Get comprehensive admin dashboard statistics.

    Admin Only - Returns user stats, report stats, alerts, and system health.
    """
    try:
        admin_service = get_admin_service(db)
        dashboard_data = await admin_service.get_dashboard_stats()

        return {
            "success": True,
            "data": dashboard_data
        }
    except Exception as e:
        logger.error(f"Error getting admin dashboard: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch dashboard data"
        )


@router.get("/stats")
async def get_system_stats(
    current_user: User = Depends(require_admin),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Get quick system statistics summary.

    Admin Only
    """
    try:
        admin_service = get_admin_service(db)
        stats = await admin_service.get_dashboard_stats()

        return {
            "success": True,
            "data": {
                "total_users": stats["users"]["total"],
                "active_users": stats["users"]["active"],
                "total_reports": stats["reports"]["total"],
                "pending_reports": stats["reports"]["pending"],
                "active_alerts": stats["alerts"]["active"],
                "system_health": "healthy"
            }
        }
    except Exception as e:
        logger.error(f"Error getting system stats: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch system stats"
        )


# ============================================================================
# User Management
# ============================================================================

@router.get("/users")
async def list_users(
    page: int = Query(default=1, ge=1, description="Page number"),
    limit: int = Query(default=20, ge=1, le=100, description="Items per page"),
    search: Optional[str] = Query(default=None, description="Search by name, email, phone, or ID"),
    role: Optional[str] = Query(default=None, description="Filter by role"),
    status: Optional[str] = Query(default=None, description="Filter: active, inactive, banned"),
    sort_by: str = Query(default="created_at", description="Sort field"),
    sort_order: str = Query(default="desc", description="Sort order: asc or desc"),
    current_user: User = Depends(require_admin),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Get paginated list of all users with filters.

    Admin Only
    """
    try:
        admin_service = get_admin_service(db)
        result = await admin_service.get_users_paginated(
            page=page,
            limit=limit,
            search=search,
            role=role,
            status=status,
            sort_by=sort_by,
            sort_order=sort_order
        )

        return {
            "success": True,
            "data": result
        }
    except Exception as e:
        logger.error(f"Error listing users: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch users"
        )


@router.get("/users/{user_id}")
async def get_user_details(
    user_id: str,
    current_user: User = Depends(require_admin),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Get detailed user information including activity history.

    Admin Only
    """
    try:
        admin_service = get_admin_service(db)
        user_details = await admin_service.get_user_details(user_id)

        if not user_details:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        return {
            "success": True,
            "data": user_details
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting user details: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch user details"
        )


@router.post("/users")
async def create_user(
    user_data: CreateUserRequest,
    request: Request,
    current_user: User = Depends(require_admin),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Create a new user with specified role.

    Admin Only
    """
    try:
        ip_address, user_agent = get_client_info(request)
        admin_service = get_admin_service(db)

        result = await admin_service.create_user(
            user_data=user_data.model_dump(),
            admin_id=current_user.user_id,
            admin_name=current_user.name or current_user.email,
            ip_address=ip_address,
            user_agent=user_agent
        )

        return {
            "success": True,
            "message": "User created successfully",
            "data": result
        }
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error creating user: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create user"
        )


@router.put("/users/{user_id}")
async def update_user(
    user_id: str,
    update_data: UpdateUserRequest,
    request: Request,
    current_user: User = Depends(require_admin),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Update user details.

    Admin Only
    """
    try:
        ip_address, user_agent = get_client_info(request)
        admin_service = get_admin_service(db)

        result = await admin_service.update_user(
            user_id=user_id,
            update_data=update_data.model_dump(exclude_none=True),
            admin_id=current_user.user_id,
            admin_name=current_user.name or current_user.email,
            ip_address=ip_address,
            user_agent=user_agent
        )

        return {
            "success": True,
            "message": "User updated successfully",
            "data": result
        }
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error updating user: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update user"
        )


@router.post("/users/{user_id}/ban")
async def ban_user(
    user_id: str,
    ban_request: BanUserRequest,
    request: Request,
    current_user: User = Depends(require_admin),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Ban a user with reason.

    Admin Only - Cannot ban yourself.
    """
    try:
        ip_address, user_agent = get_client_info(request)
        admin_service = get_admin_service(db)

        result = await admin_service.ban_user(
            user_id=user_id,
            reason=ban_request.reason,
            admin_id=current_user.user_id,
            admin_name=current_user.name or current_user.email,
            ip_address=ip_address,
            user_agent=user_agent
        )

        return {
            "success": True,
            "message": f"User {user_id} has been banned",
            "data": result
        }
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error banning user: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to ban user"
        )


@router.post("/users/{user_id}/unban")
async def unban_user(
    user_id: str,
    request: Request,
    current_user: User = Depends(require_admin),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Unban a previously banned user.

    Admin Only
    """
    try:
        ip_address, user_agent = get_client_info(request)
        admin_service = get_admin_service(db)

        result = await admin_service.unban_user(
            user_id=user_id,
            admin_id=current_user.user_id,
            admin_name=current_user.name or current_user.email,
            ip_address=ip_address,
            user_agent=user_agent
        )

        return {
            "success": True,
            "message": f"User {user_id} has been unbanned",
            "data": result
        }
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error unbanning user: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to unban user"
        )


@router.post("/users/{user_id}/role")
async def assign_user_role(
    user_id: str,
    role_request: AssignRoleRequest,
    request: Request,
    current_user: User = Depends(require_admin),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Assign a new role to a user.

    Admin Only
    """
    try:
        ip_address, user_agent = get_client_info(request)
        admin_service = get_admin_service(db)

        result = await admin_service.assign_role(
            user_id=user_id,
            new_role=role_request.role,
            reason=role_request.reason,
            admin_id=current_user.user_id,
            admin_name=current_user.name or current_user.email,
            ip_address=ip_address,
            user_agent=user_agent
        )

        return {
            "success": True,
            "message": f"Role changed from {result['previous_role']} to {result['new_role']}",
            "data": result
        }
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error assigning role: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to assign role"
        )


@router.delete("/users/{user_id}")
async def delete_user(
    user_id: str,
    request: Request,
    current_user: User = Depends(require_admin),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Soft delete a user (mark as inactive).

    Admin Only - Cannot delete yourself.
    """
    try:
        ip_address, user_agent = get_client_info(request)
        admin_service = get_admin_service(db)

        result = await admin_service.delete_user(
            user_id=user_id,
            admin_id=current_user.user_id,
            admin_name=current_user.name or current_user.email,
            ip_address=ip_address,
            user_agent=user_agent
        )

        return {
            "success": True,
            "message": f"User {user_id} has been deleted",
            "data": result
        }
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error deleting user: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete user"
        )


@router.get("/users/{user_id}/activity")
async def get_user_activity(
    user_id: str,
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    current_user: User = Depends(require_admin),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Get user's activity history from audit logs.

    Admin Only
    """
    try:
        skip = (page - 1) * limit

        cursor = db.audit_logs.find(
            {"user_id": user_id}
        ).sort("timestamp", -1).skip(skip).limit(limit)

        logs = await cursor.to_list(limit)
        total = await db.audit_logs.count_documents({"user_id": user_id})

        activity = []
        for log in logs:
            activity.append({
                "action": log.get("action"),
                "details": log.get("details", {}),
                "ip_address": log.get("ip_address"),
                "success": log.get("success", True),
                "timestamp": log.get("timestamp").isoformat() if log.get("timestamp") else None
            })

        return {
            "success": True,
            "data": {
                "activity": activity,
                "pagination": {
                    "page": page,
                    "limit": limit,
                    "total_count": total,
                    "total_pages": (total + limit - 1) // limit
                }
            }
        }
    except Exception as e:
        logger.error(f"Error getting user activity: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch user activity"
        )


# ============================================================================
# Content Moderation
# ============================================================================

@router.get("/reports")
async def list_reports(
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    status: Optional[str] = Query(default=None, description="Filter by status"),
    hazard_type: Optional[str] = Query(default=None, description="Filter by hazard type"),
    search: Optional[str] = Query(default=None, description="Search in description"),
    date_range: str = Query(default="all", description="Date range filter"),
    current_user: User = Depends(require_admin),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Get paginated list of all hazard reports for moderation.

    Admin Only
    """
    try:
        admin_service = get_admin_service(db)
        result = await admin_service.get_reports_paginated(
            page=page,
            limit=limit,
            status=status,
            hazard_type=hazard_type,
            search=search,
            date_range=date_range
        )

        return {
            "success": True,
            "data": result
        }
    except Exception as e:
        logger.error(f"Error listing reports: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch reports"
        )


@router.delete("/reports/{report_id}")
async def delete_report(
    report_id: str,
    reason: Optional[str] = Query(default=None, description="Deletion reason"),
    request: Request = None,
    current_user: User = Depends(require_admin),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Delete a hazard report.

    Admin Only
    """
    try:
        ip_address, user_agent = get_client_info(request) if request else (None, None)
        admin_service = get_admin_service(db)

        result = await admin_service.delete_report(
            report_id=report_id,
            admin_id=current_user.user_id,
            admin_name=current_user.name or current_user.email,
            reason=reason,
            ip_address=ip_address,
            user_agent=user_agent
        )

        return {
            "success": True,
            "message": f"Report {report_id} has been deleted",
            "data": result
        }
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error deleting report: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete report"
        )


@router.get("/alerts")
async def list_alerts(
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    status: Optional[str] = Query(default=None, description="Filter by status"),
    severity: Optional[str] = Query(default=None, description="Filter by severity"),
    current_user: User = Depends(require_admin),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Get paginated list of all system alerts.

    Admin Only
    """
    try:
        admin_service = get_admin_service(db)
        result = await admin_service.get_alerts_paginated(
            page=page,
            limit=limit,
            status=status,
            severity=severity
        )

        return {
            "success": True,
            "data": result
        }
    except Exception as e:
        logger.error(f"Error listing alerts: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch alerts"
        )


@router.delete("/alerts/{alert_id}")
async def delete_alert(
    alert_id: str,
    request: Request,
    current_user: User = Depends(require_admin),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Delete a system alert.

    Admin Only
    """
    try:
        ip_address, user_agent = get_client_info(request)
        admin_service = get_admin_service(db)

        result = await admin_service.delete_alert(
            alert_id=alert_id,
            admin_id=current_user.user_id,
            admin_name=current_user.name or current_user.email,
            ip_address=ip_address,
            user_agent=user_agent
        )

        return {
            "success": True,
            "message": f"Alert {alert_id} has been deleted",
            "data": result
        }
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error deleting alert: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete alert"
        )


@router.get("/chat/messages")
async def list_chat_messages(
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=50, ge=1, le=100),
    room_id: Optional[str] = Query(default=None, description="Filter by room"),
    user_id: Optional[str] = Query(default=None, description="Filter by user"),
    current_user: User = Depends(require_admin),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Get chat messages for moderation.

    Admin Only
    """
    try:
        query = {"deleted": {"$ne": True}}

        if room_id:
            query["room_id"] = room_id
        if user_id:
            query["user_id"] = user_id

        skip = (page - 1) * limit
        total = await db.chat_messages.count_documents(query)

        cursor = db.chat_messages.find(query).sort("timestamp", -1).skip(skip).limit(limit)
        messages = await cursor.to_list(limit)

        formatted_messages = []
        for msg in messages:
            formatted_messages.append({
                "message_id": msg.get("message_id"),
                "room_id": msg.get("room_id"),
                "user_id": msg.get("user_id"),
                "user_name": msg.get("user_name"),
                "content": msg.get("content"),
                "message_type": msg.get("message_type"),
                "timestamp": msg.get("timestamp").isoformat() if msg.get("timestamp") else None
            })

        return {
            "success": True,
            "data": {
                "messages": formatted_messages,
                "pagination": {
                    "page": page,
                    "limit": limit,
                    "total_count": total,
                    "total_pages": (total + limit - 1) // limit
                }
            }
        }
    except Exception as e:
        logger.error(f"Error listing chat messages: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch chat messages"
        )


@router.delete("/chat/messages/{message_id}")
async def delete_chat_message(
    message_id: str,
    request: Request,
    current_user: User = Depends(require_admin),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Delete a chat message.

    Admin Only
    """
    try:
        result = await db.chat_messages.update_one(
            {"message_id": message_id},
            {"$set": {
                "deleted": True,
                "deleted_at": datetime.now(timezone.utc),
                "deleted_by": current_user.user_id
            }}
        )

        if result.matched_count == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Message not found"
            )

        # Log admin action
        ip_address, user_agent = get_client_info(request)
        admin_service = get_admin_service(db)
        await admin_service._log_admin_action(
            admin_id=current_user.user_id,
            admin_name=current_user.name or current_user.email,
            action=AdminActionType.MESSAGE_DELETED,
            target_type="chat_message",
            target_id=message_id,
            ip_address=ip_address,
            user_agent=user_agent
        )

        return {
            "success": True,
            "message": "Chat message deleted"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting chat message: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete chat message"
        )


# ============================================================================
# System Monitoring
# ============================================================================

@router.get("/monitoring/health")
async def get_system_health(
    current_user: User = Depends(require_admin),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Get comprehensive system health status.

    Admin Only
    """
    try:
        admin_service = get_admin_service(db)
        health_data = await admin_service.get_system_health()

        return {
            "success": True,
            "data": health_data
        }
    except Exception as e:
        logger.error(f"Error getting system health: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch system health"
        )


@router.get("/monitoring/api-stats")
async def get_api_statistics(
    date_range: str = Query(default="7days", description="Date range: today, 7days, 30days, 90days"),
    current_user: User = Depends(require_admin),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Get API usage statistics.

    Admin Only
    """
    try:
        admin_service = get_admin_service(db)
        stats = await admin_service.get_api_statistics(date_range)

        return {
            "success": True,
            "data": stats
        }
    except Exception as e:
        logger.error(f"Error getting API stats: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch API statistics"
        )


@router.get("/monitoring/errors")
async def get_error_logs(
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    level: Optional[str] = Query(default=None, description="Filter by level: error, warning, critical"),
    resolved: Optional[bool] = Query(default=None, description="Filter by resolved status"),
    current_user: User = Depends(require_admin),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Get recent error logs.

    Admin Only
    """
    try:
        admin_service = get_admin_service(db)
        result = await admin_service.get_error_logs(
            page=page,
            limit=limit,
            level=level,
            resolved=resolved
        )

        return {
            "success": True,
            "data": result
        }
    except Exception as e:
        logger.error(f"Error getting error logs: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch error logs"
        )


@router.get("/monitoring/database")
async def get_database_stats(
    current_user: User = Depends(require_admin),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Get database statistics.

    Admin Only
    """
    try:
        # Get database stats
        db_stats = await db.command("dbStats")

        # Get collection stats
        collections = await db.list_collection_names()
        collection_stats = []

        for coll_name in collections[:20]:  # Limit to first 20 collections
            try:
                stats = await db.command("collStats", coll_name)
                collection_stats.append({
                    "name": coll_name,
                    "count": stats.get("count", 0),
                    "size_mb": round(stats.get("size", 0) / (1024 * 1024), 2),
                    "avg_doc_size_kb": round(stats.get("avgObjSize", 0) / 1024, 2),
                    "indexes": stats.get("nindexes", 0)
                })
            except Exception:
                pass

        return {
            "success": True,
            "data": {
                "database": {
                    "name": db_stats.get("db"),
                    "collections": db_stats.get("collections", 0),
                    "data_size_mb": round(db_stats.get("dataSize", 0) / (1024 * 1024), 2),
                    "storage_size_mb": round(db_stats.get("storageSize", 0) / (1024 * 1024), 2),
                    "index_size_mb": round(db_stats.get("indexSize", 0) / (1024 * 1024), 2),
                    "total_indexes": db_stats.get("indexes", 0)
                },
                "collections": sorted(collection_stats, key=lambda x: x["count"], reverse=True)
            }
        }
    except Exception as e:
        logger.error(f"Error getting database stats: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch database statistics"
        )


# ============================================================================
# System Settings
# ============================================================================

@router.get("/settings")
async def get_all_settings(
    current_user: User = Depends(require_admin),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Get all system settings grouped by category.

    Admin Only - Sensitive values are masked.
    """
    try:
        admin_service = get_admin_service(db)
        settings = await admin_service.get_all_settings()

        return {
            "success": True,
            "data": settings
        }
    except Exception as e:
        logger.error(f"Error getting settings: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch settings"
        )


@router.get("/settings/{category}")
async def get_settings_by_category(
    category: str,
    current_user: User = Depends(require_admin),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Get settings for a specific category.

    Admin Only
    """
    try:
        admin_service = get_admin_service(db)
        settings = await admin_service.get_settings_by_category(category)

        return {
            "success": True,
            "data": settings
        }
    except Exception as e:
        logger.error(f"Error getting settings: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch settings"
        )


@router.put("/settings/{key}")
async def update_setting(
    key: str,
    update_request: UpdateSettingRequest,
    request: Request,
    current_user: User = Depends(require_admin),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Update a system setting.

    Admin Only
    """
    try:
        ip_address, user_agent = get_client_info(request)
        admin_service = get_admin_service(db)

        result = await admin_service.update_setting(
            key=key,
            value=update_request.value,
            admin_id=current_user.user_id,
            admin_name=current_user.name or current_user.email,
            ip_address=ip_address,
            user_agent=user_agent
        )

        return {
            "success": True,
            "message": f"Setting '{key}' updated successfully",
            "data": result
        }
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error updating setting: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update setting"
        )


@router.post("/settings")
async def create_setting(
    setting_data: CreateSettingRequest,
    request: Request,
    current_user: User = Depends(require_admin),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Create a new system setting.

    Admin Only
    """
    try:
        ip_address, user_agent = get_client_info(request)
        admin_service = get_admin_service(db)

        result = await admin_service.create_setting(
            setting_data=setting_data.model_dump(),
            admin_id=current_user.user_id,
            admin_name=current_user.name or current_user.email,
            ip_address=ip_address,
            user_agent=user_agent
        )

        return {
            "success": True,
            "message": "Setting created successfully",
            "data": result
        }
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error creating setting: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create setting"
        )


@router.delete("/settings/{key}")
async def delete_setting(
    key: str,
    request: Request,
    current_user: User = Depends(require_admin),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Delete a system setting.

    Admin Only
    """
    try:
        result = await db.system_settings.delete_one({"key": key})

        if result.deleted_count == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Setting not found"
            )

        # Log admin action
        ip_address, user_agent = get_client_info(request)
        admin_service = get_admin_service(db)
        await admin_service._log_admin_action(
            admin_id=current_user.user_id,
            admin_name=current_user.name or current_user.email,
            action=AdminActionType.SETTING_DELETED,
            target_type="setting",
            target_name=key,
            ip_address=ip_address,
            user_agent=user_agent
        )

        return {
            "success": True,
            "message": f"Setting '{key}' deleted successfully"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting setting: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete setting"
        )


# ============================================================================
# Audit Logs
# ============================================================================

@router.get("/audit-logs")
async def get_audit_logs(
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=50, ge=1, le=100),
    action: Optional[str] = Query(default=None, description="Filter by action type"),
    user_id: Optional[str] = Query(default=None, description="Filter by user"),
    date_range: str = Query(default="7days", description="Date range filter"),
    search: Optional[str] = Query(default=None, description="Search in action or details"),
    current_user: User = Depends(require_admin),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Get searchable audit logs.

    Admin Only
    """
    try:
        admin_service = get_admin_service(db)
        result = await admin_service.get_audit_logs(
            page=page,
            limit=limit,
            action=action,
            user_id=user_id,
            date_range=date_range,
            search=search
        )

        return {
            "success": True,
            "data": result
        }
    except Exception as e:
        logger.error(f"Error getting audit logs: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch audit logs"
        )


@router.get("/audit-logs/admin-activity")
async def get_admin_activity_logs(
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=50, ge=1, le=100),
    action: Optional[str] = Query(default=None, description="Filter by action type"),
    admin_id: Optional[str] = Query(default=None, description="Filter by admin"),
    date_range: str = Query(default="7days", description="Date range filter"),
    current_user: User = Depends(require_admin),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Get admin-specific activity logs.

    Admin Only
    """
    try:
        admin_service = get_admin_service(db)
        result = await admin_service.get_admin_activity_logs(
            page=page,
            limit=limit,
            action=action,
            admin_id=admin_id,
            date_range=date_range
        )

        return {
            "success": True,
            "data": result
        }
    except Exception as e:
        logger.error(f"Error getting admin activity logs: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch admin activity logs"
        )


@router.get("/audit-logs/stats")
async def get_audit_stats(
    date_range: str = Query(default="7days", description="Date range filter"),
    current_user: User = Depends(require_admin),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Get audit log statistics.

    Admin Only
    """
    try:
        admin_service = get_admin_service(db)
        stats = await admin_service.get_audit_stats(date_range)

        return {
            "success": True,
            "data": stats
        }
    except Exception as e:
        logger.error(f"Error getting audit stats: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch audit statistics"
        )


@router.get("/audit-logs/export")
async def export_audit_logs(
    format: str = Query(default="csv", description="Export format: csv or xlsx"),
    date_range: str = Query(default="7days", description="Date range filter"),
    action: Optional[str] = Query(default=None, description="Filter by action type"),
    current_user: User = Depends(require_admin),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Export audit logs as CSV or Excel.

    Admin Only
    """
    try:
        admin_service = get_admin_service(db)
        result = await admin_service.get_audit_logs(
            page=1,
            limit=10000,  # Get all logs for export
            action=action,
            date_range=date_range
        )

        logs = result["logs"]

        if format == "csv":
            # Generate CSV
            output = io.StringIO()
            writer = csv.DictWriter(output, fieldnames=[
                "timestamp", "user_id", "action", "details", "ip_address", "success"
            ])
            writer.writeheader()

            for log in logs:
                writer.writerow({
                    "timestamp": log.get("timestamp"),
                    "user_id": log.get("user_id"),
                    "action": log.get("action"),
                    "details": str(log.get("details", {})),
                    "ip_address": log.get("ip_address"),
                    "success": log.get("success")
                })

            output.seek(0)

            return StreamingResponse(
                iter([output.getvalue()]),
                media_type="text/csv",
                headers={
                    "Content-Disposition": f"attachment; filename=audit_logs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
                }
            )
        else:
            # For Excel, return JSON with download link (would need openpyxl)
            return {
                "success": True,
                "message": "Excel export not implemented yet. Please use CSV format.",
                "data": {"logs_count": len(logs)}
            }

    except Exception as e:
        logger.error(f"Error exporting audit logs: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to export audit logs"
        )


# ============================================================================
# Utility Endpoints
# ============================================================================

@router.get("/roles")
async def get_available_roles(
    current_user: User = Depends(require_admin)
):
    """
    Get list of available user roles.

    Admin Only
    """
    return {
        "success": True,
        "data": {
            "roles": [
                {"value": "citizen", "label": "Citizen", "level": 1, "description": "Basic user who can report hazards"},
                {"value": "analyst", "label": "Analyst", "level": 2, "description": "Data analyst without PII access"},
                {"value": "authority", "label": "Authority", "level": 3, "description": "Can verify reports and manage alerts"},
                {"value": "authority_admin", "label": "Authority Admin", "level": 4, "description": "Full system access"}
            ]
        }
    }


@router.get("/action-types")
async def get_action_types(
    current_user: User = Depends(require_admin)
):
    """
    Get list of admin action types for filtering.

    Admin Only
    """
    return {
        "success": True,
        "data": {
            "action_types": [action.value for action in AdminActionType]
        }
    }
