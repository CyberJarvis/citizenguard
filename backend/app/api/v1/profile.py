import logging
import os
import secrets
from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from motor.motor_asyncio import AsyncIOMotorDatabase
from PIL import Image
import io

from pydantic import BaseModel, Field

from app.database import get_database
from app.models.profile import (
    ProfileUpdate,
    ProfileResponse,
    PublicProfileResponse,
    UserStats
)
from app.models.user import User
from app.middleware.security import get_current_user
from app.services.s3_service import s3_service
from app.config import settings

logger = logging.getLogger(__name__)


class ProfilePictureS3Request(BaseModel):
    """Request model for S3-based profile picture update"""
    picture_url: str = Field(..., description="S3 public URL of the uploaded profile picture")

router = APIRouter(prefix="/profile", tags=["Profile"])

# Constants
MAX_IMAGE_SIZE = 5 * 1024 * 1024  # 5MB
ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/jpg", "image/webp"}
PROFILE_UPLOAD_DIR = "uploads/profiles"


@router.get("/me", response_model=ProfileResponse)
async def get_my_profile(
    current_user: User = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Get current user's profile

    Returns complete profile information including private data
    """
    try:
        user_doc = await db.users.find_one({"user_id": current_user.user_id})

        if not user_doc:
            raise HTTPException(status_code=404, detail="Profile not found")

        return ProfileResponse(
            user_id=user_doc["user_id"],
            email=user_doc.get("email"),
            phone=user_doc.get("phone"),
            name=user_doc.get("name", "User"),
            role=user_doc.get("role", "CITIZEN"),
            profile_picture=user_doc.get("profile_picture"),
            bio=user_doc.get("bio"),
            location=user_doc.get("location"),
            credibility_score=user_doc.get("credibility_score", 0),
            total_reports=user_doc.get("total_reports", 0),
            verified_reports=user_doc.get("verified_reports", 0),
            email_verified=user_doc.get("email_verified", False),
            phone_verified=user_doc.get("phone_verified", False),
            created_at=user_doc.get("created_at", datetime.now(timezone.utc)).isoformat(),
            emergency_contacts=user_doc.get("emergency_contacts", [])
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching profile: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch profile")


@router.put("/me", response_model=ProfileResponse)
async def update_my_profile(
    profile_data: ProfileUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Update current user's profile

    Updates allowed fields: name, phone, bio, location
    """
    try:
        # Build update document (only include provided fields)
        update_doc = {
            "updated_at": datetime.now(timezone.utc)
        }

        if profile_data.name is not None:
            update_doc["name"] = profile_data.name.strip()

        if profile_data.phone is not None:
            # Check if phone is already used by another user
            if profile_data.phone.strip():
                existing = await db.users.find_one({
                    "phone": profile_data.phone,
                    "user_id": {"$ne": current_user.user_id}
                })
                if existing:
                    raise HTTPException(
                        status_code=400,
                        detail="Phone number already in use"
                    )
                update_doc["phone"] = profile_data.phone.strip()

        if profile_data.bio is not None:
            update_doc["bio"] = profile_data.bio.strip()

        if profile_data.location is not None:
            update_doc["location"] = profile_data.location

        if profile_data.emergency_contacts is not None:
            # Convert to list of dicts for MongoDB
            update_doc["emergency_contacts"] = [
                contact.model_dump() for contact in profile_data.emergency_contacts
            ]

        # Update user document
        result = await db.users.update_one(
            {"user_id": current_user.user_id},
            {"$set": update_doc}
        )

        if result.modified_count == 0 and result.matched_count == 0:
            raise HTTPException(status_code=404, detail="Profile not found")

        # Fetch updated profile
        user_doc = await db.users.find_one({"user_id": current_user.user_id})

        return ProfileResponse(
            user_id=user_doc["user_id"],
            email=user_doc.get("email"),
            phone=user_doc.get("phone"),
            name=user_doc.get("name", "User"),
            role=user_doc.get("role", "CITIZEN"),
            profile_picture=user_doc.get("profile_picture"),
            bio=user_doc.get("bio"),
            location=user_doc.get("location"),
            credibility_score=user_doc.get("credibility_score", 0),
            total_reports=user_doc.get("total_reports", 0),
            verified_reports=user_doc.get("verified_reports", 0),
            email_verified=user_doc.get("email_verified", False),
            phone_verified=user_doc.get("phone_verified", False),
            created_at=user_doc.get("created_at", datetime.now(timezone.utc)).isoformat(),
            emergency_contacts=user_doc.get("emergency_contacts", [])
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating profile: {e}")
        raise HTTPException(status_code=500, detail="Failed to update profile")


@router.post("/picture")
async def upload_profile_picture(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Upload profile picture

    - Max size: 5MB
    - Allowed types: JPEG, PNG, WebP
    - Auto-resizes to 400x400px
    """
    try:
        # Validate file type
        if file.content_type not in ALLOWED_IMAGE_TYPES:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid file type. Allowed: {', '.join(ALLOWED_IMAGE_TYPES)}"
            )

        # Read file content
        content = await file.read()

        # Validate file size
        if len(content) > MAX_IMAGE_SIZE:
            raise HTTPException(
                status_code=400,
                detail=f"File too large. Max size: {MAX_IMAGE_SIZE / 1024 / 1024}MB"
            )

        # Open and validate image
        try:
            image = Image.open(io.BytesIO(content))
            image.verify()  # Verify it's a valid image
            image = Image.open(io.BytesIO(content))  # Re-open after verify
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid image file")

        # Resize image to 400x400 (square)
        image = image.convert("RGB")  # Convert to RGB
        image.thumbnail((400, 400), Image.Resampling.LANCZOS)

        # Create square image (crop to center)
        width, height = image.size
        if width != height:
            min_dim = min(width, height)
            left = (width - min_dim) / 2
            top = (height - min_dim) / 2
            right = (width + min_dim) / 2
            bottom = (height + min_dim) / 2
            image = image.crop((left, top, right, bottom))

        # Generate unique filename
        file_extension = "jpg"
        filename = f"{current_user.user_id}_{secrets.token_urlsafe(8)}.{file_extension}"

        # Ensure upload directory exists
        os.makedirs(PROFILE_UPLOAD_DIR, exist_ok=True)

        # Save file
        file_path = os.path.join(PROFILE_UPLOAD_DIR, filename)
        image.save(file_path, "JPEG", quality=85, optimize=True)

        # Update user document with new profile picture URL
        picture_url = f"/{file_path.replace(os.sep, '/')}"

        # Delete old profile picture if exists
        user_doc = await db.users.find_one({"user_id": current_user.user_id})
        if user_doc.get("profile_picture"):
            old_path = user_doc["profile_picture"].lstrip("/")
            if os.path.exists(old_path):
                try:
                    os.remove(old_path)
                except Exception as e:
                    logger.warning(f"Failed to delete old profile picture: {e}")

        # Update database
        await db.users.update_one(
            {"user_id": current_user.user_id},
            {"$set": {
                "profile_picture": picture_url,
                "updated_at": datetime.now(timezone.utc)
            }}
        )

        return {
            "success": True,
            "message": "Profile picture uploaded successfully",
            "picture_url": picture_url
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uploading profile picture: {e}")
        raise HTTPException(status_code=500, detail="Failed to upload profile picture")


@router.delete("/picture")
async def delete_profile_picture(
    current_user: User = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Remove profile picture"""
    try:
        user_doc = await db.users.find_one({"user_id": current_user.user_id})

        if user_doc.get("profile_picture"):
            # Delete file
            old_path = user_doc["profile_picture"].lstrip("/")
            if os.path.exists(old_path):
                try:
                    os.remove(old_path)
                except Exception as e:
                    logger.warning(f"Failed to delete profile picture file: {e}")

            # Update database
            await db.users.update_one(
                {"user_id": current_user.user_id},
                {
                    "$unset": {"profile_picture": ""},
                    "$set": {"updated_at": datetime.now(timezone.utc)}
                }
            )

        return {
            "success": True,
            "message": "Profile picture removed successfully"
        }

    except Exception as e:
        logger.error(f"Error deleting profile picture: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete profile picture")


@router.post("/picture/s3")
async def update_profile_picture_s3(
    request: ProfilePictureS3Request,
    current_user: User = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Update profile picture using S3 URL (presigned upload)

    Use this endpoint after uploading the image directly to S3 via presigned URL.

    **Flow:**
    1. Frontend calls `/api/v1/uploads/presigned-url` with upload_type='profile'
    2. Frontend uploads image directly to S3
    3. Frontend calls this endpoint with the S3 public URL
    """
    try:
        # Validate S3 is enabled
        if not s3_service.is_enabled:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="S3 storage is not enabled"
            )

        # Validate URL is from our S3 bucket
        if not request.picture_url.startswith(settings.s3_base_url):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid picture URL. Must be uploaded to CoastGuardian S3 bucket."
            )

        # Get current user profile to delete old picture
        user_doc = await db.users.find_one({"user_id": current_user.user_id})

        if user_doc.get("profile_picture"):
            old_url = user_doc["profile_picture"]
            # If old picture is on S3, delete it
            if old_url.startswith(settings.s3_base_url):
                old_key = s3_service.extract_key_from_url(old_url)
                if old_key:
                    s3_service.delete_file(old_key)
            # If old picture is local, delete local file
            elif old_url.startswith("/"):
                old_path = old_url.lstrip("/")
                if os.path.exists(old_path):
                    try:
                        os.remove(old_path)
                    except Exception as e:
                        logger.warning(f"Failed to delete old profile picture: {e}")

        # Update database with new S3 URL
        await db.users.update_one(
            {"user_id": current_user.user_id},
            {"$set": {
                "profile_picture": request.picture_url,
                "updated_at": datetime.now(timezone.utc)
            }}
        )

        return {
            "success": True,
            "message": "Profile picture updated successfully",
            "picture_url": request.picture_url
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating profile picture (S3): {e}")
        raise HTTPException(status_code=500, detail="Failed to update profile picture")


@router.get("/stats", response_model=UserStats)
async def get_user_stats(
    current_user: User = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Get user statistics

    Returns detailed statistics about user's activity
    """
    try:
        # Get user reports
        reports = await db.hazard_reports.find({
            "user_id": current_user.user_id,
            "deleted": {"$ne": True}
        }).to_list(length=1000)

        # Calculate statistics
        total_reports = len(reports)
        verified_reports = len([r for r in reports if r.get("verification_status") == "verified"])
        pending_reports = len([r for r in reports if r.get("verification_status") == "pending"])
        rejected_reports = len([r for r in reports if r.get("verification_status") == "rejected"])

        # Count reports by type
        reports_by_type = {}
        for report in reports:
            hazard_type = report.get("hazard_type", "UNKNOWN")
            reports_by_type[hazard_type] = reports_by_type.get(hazard_type, 0) + 1

        # Calculate total likes
        total_likes = sum(r.get("likes", 0) for r in reports)

        # Get recent activity (last 5 reports)
        recent_activity = []
        for report in sorted(reports, key=lambda x: x.get("timestamp", datetime.min), reverse=True)[:5]:
            recent_activity.append({
                "type": "report_submitted",
                "date": report.get("timestamp", datetime.now(timezone.utc)).isoformat(),
                "description": f"Reported {report.get('hazard_type', 'hazard')}",
                "status": report.get("verification_status", "pending")
            })

        # Get credibility score from user document
        user_doc = await db.users.find_one({"user_id": current_user.user_id})
        credibility_score = user_doc.get("credibility_score", 0) if user_doc else 0

        return UserStats(
            total_reports=total_reports,
            verified_reports=verified_reports,
            pending_reports=pending_reports,
            rejected_reports=rejected_reports,
            credibility_score=credibility_score,
            total_likes=total_likes,
            reports_by_type=reports_by_type,
            recent_activity=recent_activity
        )

    except Exception as e:
        logger.error(f"Error fetching user stats: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch statistics")


@router.get("/{user_id}", response_model=PublicProfileResponse)
async def get_public_profile(
    user_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Get public profile of another user

    Returns limited public information (no private data like email/phone)
    """
    try:
        user_doc = await db.users.find_one({"user_id": user_id})

        if not user_doc:
            raise HTTPException(status_code=404, detail="User not found")

        return PublicProfileResponse(
            user_id=user_doc["user_id"],
            name=user_doc.get("name", "User"),
            role=user_doc.get("role", "CITIZEN"),
            profile_picture=user_doc.get("profile_picture"),
            bio=user_doc.get("bio"),
            credibility_score=user_doc.get("credibility_score", 0),
            total_reports=user_doc.get("total_reports", 0),
            verified_reports=user_doc.get("verified_reports", 0),
            created_at=user_doc.get("created_at", datetime.now(timezone.utc)).isoformat()
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching public profile: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch profile")
