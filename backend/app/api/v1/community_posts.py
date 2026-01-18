"""
Community Posts API Router
Endpoints for creating, viewing, and managing community posts
"""

import logging
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from motor.motor_asyncio import AsyncIOMotorDatabase
from pydantic import BaseModel
from typing import Optional, List

from app.database import get_database
from app.middleware.rbac import get_current_user
from app.services.community_post_service import CommunityPostService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/communities", tags=["Community Posts"])


# ============================================================================
# REQUEST/RESPONSE MODELS
# ============================================================================

class PostResponse(BaseModel):
    success: bool
    message: str
    post_id: Optional[str] = None


class PostListResponse(BaseModel):
    success: bool
    posts: List[dict]
    total: int
    skip: int
    limit: int


class UpdatePostRequest(BaseModel):
    content: str


class PinRequest(BaseModel):
    pin: bool = True


class VisibilityRequest(BaseModel):
    hide: bool = True


class LikeResponse(BaseModel):
    success: bool
    message: str
    is_liked: bool
    likes_count: int


# ============================================================================
# POST ENDPOINTS
# ============================================================================

@router.post("/{community_id}/posts", response_model=PostResponse)
async def create_post(
    community_id: str,
    content: str = Form(...),
    post_type: str = Form("general"),
    related_event_id: Optional[str] = Form(None),
    photos: List[UploadFile] = File(None),
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Create a new community post

    - Only community members can post
    - Only organizers can post announcements
    - Max 5 photos per post
    """
    user_id = current_user.user_id
    user_name = current_user.name or "Anonymous"

    success, message, post_data = await CommunityPostService.create_post(
        db=db,
        community_id=community_id,
        author_id=user_id,
        author_name=user_name,
        content=content,
        post_type=post_type,
        related_event_id=related_event_id,
        photos=photos if photos and photos[0].filename else None
    )

    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=message
        )

    return PostResponse(
        success=True,
        message=message,
        post_id=post_data.get("post_id") if post_data else None
    )


@router.get("/{community_id}/posts", response_model=PostListResponse)
async def get_community_posts(
    community_id: str,
    skip: int = 0,
    limit: int = 20,
    include_hidden: bool = False,
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Get posts for a community

    - Returns all visible posts
    - Organizers can see hidden posts with include_hidden=true
    """
    user_id = current_user.user_id

    # Check if user is organizer for hidden posts
    if include_hidden:
        community = await db.communities.find_one({"community_id": community_id})
        if community and community.get("organizer_id") != user_id:
            include_hidden = False

    success, message, posts, total = await CommunityPostService.get_community_posts(
        db=db,
        community_id=community_id,
        skip=skip,
        limit=limit,
        include_hidden=include_hidden
    )

    # Check if current user liked each post
    for post in posts:
        post["is_liked"] = await CommunityPostService.check_if_user_liked(
            db, post["post_id"], user_id
        )

    return PostListResponse(
        success=success,
        posts=posts,
        total=total,
        skip=skip,
        limit=limit
    )


@router.put("/{community_id}/posts/{post_id}", response_model=PostResponse)
async def update_post(
    community_id: str,
    post_id: str,
    request: UpdatePostRequest,
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Update a post (author only)
    """
    user_id = current_user.user_id

    success, message = await CommunityPostService.update_post(
        db=db,
        post_id=post_id,
        user_id=user_id,
        content=request.content
    )

    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=message
        )

    return PostResponse(
        success=True,
        message=message
    )


@router.delete("/{community_id}/posts/{post_id}", response_model=PostResponse)
async def delete_post(
    community_id: str,
    post_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Delete a post

    - Users can delete their own posts
    - Organizers can delete any post in their community
    """
    user_id = current_user.user_id

    # Check if user is organizer
    community = await db.communities.find_one({"community_id": community_id})
    is_organizer = community and community.get("organizer_id") == user_id

    success, message = await CommunityPostService.delete_post(
        db=db,
        post_id=post_id,
        user_id=user_id,
        is_organizer=is_organizer
    )

    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=message
        )

    return PostResponse(
        success=True,
        message=message
    )


@router.post("/{community_id}/posts/{post_id}/like", response_model=LikeResponse)
async def toggle_post_like(
    community_id: str,
    post_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Toggle like on a post
    """
    user_id = current_user.user_id

    success, message, is_liked = await CommunityPostService.toggle_like(
        db=db,
        post_id=post_id,
        user_id=user_id
    )

    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=message
        )

    # Get updated likes count
    post = await db.community_posts.find_one({"post_id": post_id})
    likes_count = post.get("likes_count", 0) if post else 0

    return LikeResponse(
        success=True,
        message=message,
        is_liked=is_liked,
        likes_count=likes_count
    )


@router.post("/{community_id}/posts/{post_id}/pin", response_model=PostResponse)
async def toggle_post_pin(
    community_id: str,
    post_id: str,
    request: PinRequest,
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Pin or unpin a post (organizer only)
    """
    user_id = current_user.user_id

    # Check if user is organizer
    community = await db.communities.find_one({"community_id": community_id})
    if not community:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Community not found"
        )

    if community.get("organizer_id") != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only organizers can pin posts"
        )

    success, message = await CommunityPostService.toggle_pin(
        db=db,
        post_id=post_id,
        organizer_id=user_id,
        pin=request.pin
    )

    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=message
        )

    return PostResponse(
        success=True,
        message=message
    )


@router.post("/{community_id}/posts/{post_id}/visibility", response_model=PostResponse)
async def toggle_post_visibility(
    community_id: str,
    post_id: str,
    request: VisibilityRequest,
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Hide or show a post (organizer moderation)
    """
    user_id = current_user.user_id

    # Check if user is organizer
    community = await db.communities.find_one({"community_id": community_id})
    if not community:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Community not found"
        )

    if community.get("organizer_id") != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only organizers can moderate posts"
        )

    success, message = await CommunityPostService.toggle_visibility(
        db=db,
        post_id=post_id,
        organizer_id=user_id,
        hide=request.hide
    )

    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=message
        )

    return PostResponse(
        success=True,
        message=message
    )
