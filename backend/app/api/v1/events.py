"""
Events API Endpoints
Handles event CRUD, registration, attendance, and leaderboard.
"""

import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.database import get_database
from app.models.user import User
from app.models.community import (
    EventType,
    EventStatus,
    EventCreate,
    EventUpdate,
    AttendanceMarkRequest,
    INDIAN_COASTAL_ZONES,
)
from app.middleware.rbac import get_current_user, get_optional_current_user, require_organizer
from app.services.event_service import get_event_service, event_to_dict
from app.services.points_service import get_points_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/events", tags=["events"])


# ============================================================================
# Public Endpoints
# ============================================================================

@router.get("/filters")
async def get_filter_options():
    """Get available filter options for events."""
    return {
        "success": True,
        "coastal_zones": INDIAN_COASTAL_ZONES,
        "event_types": [
            {"value": t.value, "label": t.value.replace("_", " ").title()}
            for t in EventType
        ],
        "statuses": [
            {"value": s.value, "label": s.value.replace("_", " ").title()}
            for s in EventStatus
        ]
    }


@router.get("")
async def list_events(
    community_id: Optional[str] = Query(None, description="Filter by community"),
    coastal_zone: Optional[str] = Query(None, description="Filter by coastal zone"),
    event_type: Optional[str] = Query(None, description="Filter by event type"),
    status_filter: Optional[str] = Query(None, alias="status", description="Filter by status"),
    is_emergency: Optional[bool] = Query(None, description="Filter emergency events"),
    upcoming_only: bool = Query(False, description="Show only upcoming events"),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    current_user: Optional[User] = Depends(get_optional_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    List all published events with optional filters.
    Public endpoint - authentication optional.
    """
    try:
        service = get_event_service(db)

        # Parse event_type
        et = None
        if event_type:
            try:
                et = EventType(event_type.lower())
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid event_type. Must be one of: {[t.value for t in EventType]}"
                )

        # Parse status
        st = None
        if status_filter:
            try:
                st = EventStatus(status_filter.lower())
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid status. Must be one of: {[s.value for s in EventStatus]}"
                )

        events, total = await service.list_events(
            community_id=community_id,
            coastal_zone=coastal_zone,
            event_type=et,
            status=st,
            is_emergency=is_emergency,
            upcoming_only=upcoming_only,
            skip=skip,
            limit=limit
        )

        user_id = current_user.user_id if current_user else None

        # Enrich with registration status if user is authenticated
        events_data = []
        for event in events:
            event_dict = event_to_dict(event, user_id)
            if current_user:
                reg_status = await service.check_user_registration(event.event_id, current_user.user_id)
                event_dict["registration_status"] = reg_status
            events_data.append(event_dict)

        return {
            "success": True,
            "events": events_data,
            "total": total,
            "skip": skip,
            "limit": limit
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing events: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list events"
        )


@router.get("/{event_id}")
async def get_event(
    event_id: str,
    current_user: Optional[User] = Depends(get_optional_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Get event details by ID.
    Public endpoint.
    """
    try:
        service = get_event_service(db)
        event = await service.get_event_by_id(event_id)

        if not event:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Event not found"
            )

        user_id = current_user.user_id if current_user else None
        event_dict = event_to_dict(event, user_id)

        # Add registration status if authenticated
        if current_user:
            reg_status = await service.check_user_registration(event_id, current_user.user_id)
            event_dict["registration_status"] = reg_status

        # Get community info
        community_doc = await db.communities.find_one({"community_id": event.community_id})
        if community_doc:
            event_dict["community"] = {
                "community_id": community_doc.get("community_id"),
                "name": community_doc.get("name"),
                "logo_url": community_doc.get("logo_url")
            }

        return {
            "success": True,
            "event": event_dict
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting event: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get event"
        )


# ============================================================================
# Authenticated User Endpoints
# ============================================================================

@router.get("/my/events")
async def get_my_events(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Get events the current user is registered for.
    """
    try:
        service = get_event_service(db)
        events, total = await service.get_user_events(
            current_user.user_id,
            skip,
            limit
        )

        return {
            "success": True,
            "events": events,
            "total": total,
            "skip": skip,
            "limit": limit
        }

    except Exception as e:
        logger.error(f"Error getting user events: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get your events"
        )


@router.get("/my/organized")
async def get_my_organized_events(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Get events organized by the current user.
    """
    try:
        service = get_event_service(db)
        events, total = await service.get_organizer_events(
            current_user.user_id,
            skip,
            limit
        )

        return {
            "success": True,
            "events": [event_to_dict(e, current_user.user_id) for e in events],
            "total": total,
            "skip": skip,
            "limit": limit
        }

    except Exception as e:
        logger.error(f"Error getting organized events: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get your organized events"
        )


@router.post("/{event_id}/register")
async def register_for_event(
    event_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Register for an event.
    """
    try:
        service = get_event_service(db)
        success, message, registration = await service.register_for_event(
            event_id,
            current_user
        )

        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=message
            )

        return {
            "success": True,
            "message": message,
            "registration": {
                "registration_id": registration.registration_id,
                "status": registration.registration_status.value
            } if registration else None
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error registering for event: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to register for event"
        )


@router.delete("/{event_id}/register")
async def unregister_from_event(
    event_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Unregister from an event.
    """
    try:
        service = get_event_service(db)
        success, message = await service.unregister_from_event(event_id, current_user)

        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=message
            )

        return {
            "success": True,
            "message": message
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error unregistering from event: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to unregister from event"
        )


@router.get("/{event_id}/registration-status")
async def check_registration_status(
    event_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Check if current user is registered for an event.
    """
    try:
        service = get_event_service(db)
        status_data = await service.check_user_registration(event_id, current_user.user_id)

        return {
            "success": True,
            **status_data
        }

    except Exception as e:
        logger.error(f"Error checking registration: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to check registration status"
        )


# ============================================================================
# Organizer Endpoints
# ============================================================================

@router.post("")
async def create_event(
    event_data: EventCreate,
    current_user: User = Depends(require_organizer),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Create a new event.
    Requires Verified Organizer role.
    """
    try:
        service = get_event_service(db)
        success, message, event = await service.create_event(current_user, event_data)

        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=message
            )

        return {
            "success": True,
            "message": message,
            "event": event_to_dict(event, current_user.user_id)
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating event: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create event"
        )


@router.put("/{event_id}")
async def update_event(
    event_id: str,
    update_data: EventUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Update an event.
    Requires event ownership or admin role.
    """
    try:
        service = get_event_service(db)
        success, message, event = await service.update_event(
            event_id,
            current_user,
            update_data
        )

        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=message
            )

        return {
            "success": True,
            "message": message,
            "event": event_to_dict(event, current_user.user_id) if event else None
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating event: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update event"
        )


@router.post("/{event_id}/cancel")
async def cancel_event(
    event_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Cancel an event.
    Requires event ownership or admin role.
    """
    try:
        service = get_event_service(db)
        success, message = await service.cancel_event(event_id, current_user)

        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=message
            )

        return {
            "success": True,
            "message": message
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error cancelling event: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to cancel event"
        )


@router.get("/{event_id}/registrations")
async def get_event_registrations(
    event_id: str,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    current_user: User = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Get all registrations for an event.
    Requires event ownership.
    """
    try:
        service = get_event_service(db)
        registrations, total = await service.get_event_registrations(
            event_id,
            current_user,
            skip,
            limit
        )

        if not registrations and total == 0:
            # Check if event exists and user has access
            event = await service.get_event_by_id(event_id)
            if not event:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Event not found"
                )

        return {
            "success": True,
            "registrations": registrations,
            "total": total,
            "skip": skip,
            "limit": limit
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting registrations: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get registrations"
        )


@router.post("/{event_id}/mark-attendance")
async def mark_attendance(
    event_id: str,
    attendance_data: AttendanceMarkRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Mark attendance for event participants.
    Requires event ownership.
    """
    try:
        service = get_event_service(db)
        success, message, result = await service.mark_attendance(
            event_id,
            current_user,
            attendance_data
        )

        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=message
            )

        return {
            "success": True,
            "message": message,
            "result": result
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error marking attendance: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to mark attendance"
        )


@router.post("/{event_id}/complete")
async def complete_event(
    event_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Mark an event as completed.
    Requires event ownership.
    """
    try:
        service = get_event_service(db)
        success, message = await service.complete_event(event_id, current_user)

        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=message
            )

        return {
            "success": True,
            "message": message
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error completing event: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to complete event"
        )


# ============================================================================
# Points & Leaderboard Endpoints
# ============================================================================

@router.get("/points/my")
async def get_my_points(
    current_user: User = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Get current user's points and badges.
    """
    try:
        service = get_points_service(db)
        points_data = await service.get_user_points(current_user.user_id)

        return {
            "success": True,
            "points": points_data
        }

    except Exception as e:
        logger.error(f"Error getting points: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get points"
        )


@router.get("/points/leaderboard")
async def get_leaderboard(
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Get points leaderboard.
    Public endpoint.
    """
    try:
        service = get_points_service(db)
        leaderboard, total = await service.get_leaderboard(limit, skip)

        return {
            "success": True,
            "leaderboard": leaderboard,
            "total": total,
            "skip": skip,
            "limit": limit
        }

    except Exception as e:
        logger.error(f"Error getting leaderboard: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get leaderboard"
        )


@router.get("/points/my-rank")
async def get_my_rank(
    current_user: User = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Get current user's rank on the leaderboard.
    """
    try:
        service = get_points_service(db)
        rank_data = await service.get_user_rank(current_user.user_id)

        return {
            "success": True,
            **rank_data
        }

    except Exception as e:
        logger.error(f"Error getting rank: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get rank"
        )


@router.get("/points/badges")
async def get_all_badges(
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Get all available badges.
    Public endpoint.
    """
    try:
        service = get_points_service(db)
        badges = await service.get_all_badges()

        return {
            "success": True,
            "badges": badges
        }

    except Exception as e:
        logger.error(f"Error getting badges: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get badges"
        )
