"""
Event Photos API Router
Endpoints for photo upload, retrieval, and moderation
"""

import logging
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from motor.motor_asyncio import AsyncIOMotorDatabase
from pydantic import BaseModel
from typing import Optional, List

from app.database import get_database
from app.middleware.rbac import get_current_user
from app.services.event_photo_service import EventPhotoService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/events", tags=["Event Photos"])


# ============================================================================
# RESPONSE MODELS
# ============================================================================

class PhotoResponse(BaseModel):
    success: bool
    message: str
    photo_id: Optional[str] = None
    photo_url: Optional[str] = None


class PhotoListResponse(BaseModel):
    success: bool
    photos: List[dict]
    total: int
    skip: int
    limit: int


class VisibilityRequest(BaseModel):
    hide: bool = True


# ============================================================================
# PHOTO ENDPOINTS
# ============================================================================

@router.post("/{event_id}/photos", response_model=PhotoResponse)
async def upload_event_photo(
    event_id: str,
    file: UploadFile = File(...),
    caption: Optional[str] = Form(None),
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Upload a photo to an event

    - Only attendees can upload photos
    - Max file size: 5MB
    - Allowed formats: JPEG, PNG, WebP
    """
    user_id = current_user.get("user_id") or current_user.get("sub")
    user_name = current_user.get("name", "Anonymous")

    success, message, photo_data = await EventPhotoService.upload_photo(
        db=db,
        event_id=event_id,
        user_id=user_id,
        user_name=user_name,
        file=file,
        caption=caption
    )

    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=message
        )

    return PhotoResponse(
        success=True,
        message=message,
        photo_id=photo_data.get("photo_id"),
        photo_url=photo_data.get("photo_url")
    )


@router.get("/{event_id}/photos", response_model=PhotoListResponse)
async def get_event_photos(
    event_id: str,
    skip: int = 0,
    limit: int = 20,
    include_hidden: bool = False,
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Get photos for an event

    - Returns all visible photos
    - Organizers can see hidden photos with include_hidden=true
    """
    user_id = current_user.get("user_id") or current_user.get("sub")

    # Check if user is organizer for hidden photos
    if include_hidden:
        event = await db.events.find_one({"event_id": event_id})
        if event and event.get("organizer_id") != user_id:
            include_hidden = False

    success, message, photos, total = await EventPhotoService.get_event_photos(
        db=db,
        event_id=event_id,
        skip=skip,
        limit=limit,
        include_hidden=include_hidden
    )

    return PhotoListResponse(
        success=success,
        photos=photos,
        total=total,
        skip=skip,
        limit=limit
    )


@router.delete("/{event_id}/photos/{photo_id}", response_model=PhotoResponse)
async def delete_event_photo(
    event_id: str,
    photo_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Delete a photo

    - Users can delete their own photos
    - Organizers can delete any photo in their event
    """
    user_id = current_user.get("user_id") or current_user.get("sub")

    # Check if user is organizer
    event = await db.events.find_one({"event_id": event_id})
    is_organizer = event and event.get("organizer_id") == user_id

    success, message = await EventPhotoService.delete_photo(
        db=db,
        photo_id=photo_id,
        user_id=user_id,
        is_organizer=is_organizer
    )

    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=message
        )

    return PhotoResponse(
        success=True,
        message=message
    )


@router.post("/{event_id}/photos/{photo_id}/visibility", response_model=PhotoResponse)
async def toggle_photo_visibility(
    event_id: str,
    photo_id: str,
    request: VisibilityRequest,
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Hide or show a photo (organizer moderation)

    - Only event organizers can use this endpoint
    """
    user_id = current_user.get("user_id") or current_user.get("sub")

    # Check if user is organizer
    event = await db.events.find_one({"event_id": event_id})
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event not found"
        )

    if event.get("organizer_id") != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only event organizers can moderate photos"
        )

    success, message = await EventPhotoService.toggle_photo_visibility(
        db=db,
        photo_id=photo_id,
        organizer_id=user_id,
        hide=request.hide
    )

    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=message
        )

    return PhotoResponse(
        success=True,
        message=message
    )


@router.get("/photos/my", response_model=PhotoListResponse)
async def get_my_photos(
    skip: int = 0,
    limit: int = 20,
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Get all photos uploaded by current user
    """
    user_id = current_user.get("user_id") or current_user.get("sub")

    success, message, photos, total = await EventPhotoService.get_user_photos(
        db=db,
        user_id=user_id,
        skip=skip,
        limit=limit
    )

    return PhotoListResponse(
        success=success,
        photos=photos,
        total=total,
        skip=skip,
        limit=limit
    )
