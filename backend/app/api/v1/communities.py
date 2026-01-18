"""
Communities API Endpoints
Handles community CRUD, membership, and browsing.
"""

import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query, File, UploadFile
from motor.motor_asyncio import AsyncIOMotorDatabase
from pydantic import BaseModel

from app.database import get_database
from app.models.user import User
from app.models.community import (
    Community,
    CommunityCategory,
    CommunityCreate,
    CommunityUpdate,
    INDIAN_COASTAL_ZONES,
    INDIAN_COASTAL_STATES,
)
from app.middleware.rbac import get_current_user, get_optional_current_user, require_organizer
from app.services.community_service import get_community_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/communities", tags=["communities"])


# ============================================================================
# Helper function to convert Community to response dict
# ============================================================================

def community_to_dict(community: Community, user_id: Optional[str] = None) -> dict:
    """Convert Community object to response dictionary"""
    return {
        "community_id": community.community_id,
        "name": community.name,
        "description": community.description,
        "category": community.category.value if hasattr(community.category, 'value') else community.category,
        "organizer_id": community.organizer_id,
        "organizer_name": community.organizer_name,
        "coastal_zone": community.coastal_zone,
        "state": community.state,
        "member_count": community.member_count,
        "cover_image_url": community.cover_image_url,
        "logo_url": community.logo_url,
        "total_events": community.total_events,
        "total_volunteers": community.total_volunteers,
        "is_active": community.is_active,
        "is_public": community.is_public,
        "is_member": user_id in community.member_ids if user_id else False,
        "is_organizer": community.organizer_id == user_id if user_id else False,
        "created_at": community.created_at.isoformat(),
        "updated_at": community.updated_at.isoformat()
    }


# ============================================================================
# Public Endpoints
# ============================================================================

@router.get("")
async def list_communities(
    coastal_zone: Optional[str] = Query(None, description="Filter by coastal zone"),
    state: Optional[str] = Query(None, description="Filter by state"),
    category: Optional[str] = Query(None, description="Filter by category"),
    search: Optional[str] = Query(None, description="Search by name or description"),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    current_user: Optional[User] = Depends(get_optional_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    List all public communities with optional filters.
    Public endpoint - authentication optional but improves is_member accuracy.
    """
    try:
        service = get_community_service(db)

        # Parse category
        cat = None
        if category:
            try:
                cat = CommunityCategory(category.lower())
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid category. Must be one of: {[c.value for c in CommunityCategory]}"
                )

        communities, total = await service.list_communities(
            coastal_zone=coastal_zone,
            state=state,
            category=cat,
            search=search,
            skip=skip,
            limit=limit
        )

        # Pass user_id for is_member/is_organizer calculation
        user_id = current_user.user_id if current_user else None

        return {
            "success": True,
            "communities": [community_to_dict(c, user_id) for c in communities],
            "total": total,
            "skip": skip,
            "limit": limit
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing communities: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list communities"
        )


@router.get("/filters")
async def get_filter_options():
    """Get available filter options for communities."""
    return {
        "success": True,
        "coastal_zones": INDIAN_COASTAL_ZONES,
        "states": INDIAN_COASTAL_STATES,
        "categories": [
            {"value": c.value, "label": c.value.replace("_", " ").title()}
            for c in CommunityCategory
        ]
    }


@router.get("/{community_id}")
async def get_community(
    community_id: str,
    current_user: Optional[User] = Depends(get_optional_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Get community details by ID.
    Public endpoint - authentication optional but improves is_member accuracy.
    """
    try:
        service = get_community_service(db)
        community = await service.get_community_by_id(community_id)

        if not community:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Community not found"
            )

        # Get statistics
        stats = await service.get_community_statistics(community_id)

        # Pass user_id for is_member/is_organizer calculation
        user_id = current_user.user_id if current_user else None

        return {
            "success": True,
            "community": community_to_dict(community, user_id),
            "statistics": stats
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting community: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get community"
        )


@router.get("/{community_id}/members")
async def get_community_members(
    community_id: str,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Get members of a community.
    """
    try:
        service = get_community_service(db)
        members, total = await service.get_community_members(community_id, skip, limit)

        return {
            "success": True,
            "members": members,
            "total": total,
            "skip": skip,
            "limit": limit
        }

    except Exception as e:
        logger.error(f"Error getting members: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get members"
        )


# ============================================================================
# Authenticated User Endpoints
# ============================================================================

@router.get("/my/communities")
async def get_my_communities(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Get communities the current user is a member of.
    """
    try:
        service = get_community_service(db)
        communities, total = await service.get_user_communities(
            current_user.user_id,
            skip,
            limit
        )

        return {
            "success": True,
            "communities": [community_to_dict(c, current_user.user_id) for c in communities],
            "total": total,
            "skip": skip,
            "limit": limit
        }

    except Exception as e:
        logger.error(f"Error getting user communities: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get your communities"
        )


@router.get("/my/organized")
async def get_my_organized_communities(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Get communities organized by the current user.
    """
    try:
        service = get_community_service(db)
        communities, total = await service.get_organizer_communities(
            current_user.user_id,
            skip,
            limit
        )

        return {
            "success": True,
            "communities": [community_to_dict(c, current_user.user_id) for c in communities],
            "total": total,
            "skip": skip,
            "limit": limit
        }

    except Exception as e:
        logger.error(f"Error getting organized communities: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get your organized communities"
        )


@router.post("/{community_id}/join")
async def join_community(
    community_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Join a community.
    """
    try:
        service = get_community_service(db)
        success, message = await service.join_community(community_id, current_user)

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
        logger.error(f"Error joining community: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to join community"
        )


@router.post("/{community_id}/leave")
async def leave_community(
    community_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Leave a community.
    """
    try:
        service = get_community_service(db)
        success, message = await service.leave_community(community_id, current_user)

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
        logger.error(f"Error leaving community: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to leave community"
        )


# ============================================================================
# Organizer Endpoints
# ============================================================================

@router.post("")
async def create_community(
    community_data: CommunityCreate,
    current_user: User = Depends(require_organizer),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Create a new community.
    Requires Verified Organizer role.
    """
    try:
        service = get_community_service(db)
        success, message, community = await service.create_community(
            current_user,
            community_data
        )

        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=message
            )

        return {
            "success": True,
            "message": message,
            "community": community_to_dict(community, current_user.user_id)
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating community: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create community"
        )


@router.put("/{community_id}")
async def update_community(
    community_id: str,
    update_data: CommunityUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Update a community.
    Requires community ownership or admin role.
    """
    try:
        service = get_community_service(db)
        success, message, community = await service.update_community(
            community_id,
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
            "community": community_to_dict(community, current_user.user_id)
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating community: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update community"
        )


@router.delete("/{community_id}")
async def delete_community(
    community_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Delete a community (soft delete).
    Requires community ownership or admin role.
    """
    try:
        service = get_community_service(db)
        success, message = await service.delete_community(community_id, current_user)

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
        logger.error(f"Error deleting community: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete community"
        )


@router.post("/{community_id}/upload-image")
async def upload_community_image(
    community_id: str,
    image_type: str = Query("cover", regex="^(cover|logo)$"),
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Upload a community cover image or logo.
    Requires community ownership.
    """
    try:
        service = get_community_service(db)
        success, message, image_url = await service.upload_community_image(
            community_id,
            current_user,
            file,
            image_type
        )

        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=message
            )

        return {
            "success": True,
            "message": message,
            "image_url": image_url
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uploading image: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to upload image"
        )
