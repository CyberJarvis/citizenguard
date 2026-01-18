"""
Event Photo Service
Handle photo uploads and management for events
"""

import os
import uuid
import logging
from datetime import datetime
from typing import Tuple, Optional, List
from motor.motor_asyncio import AsyncIOMotorDatabase
from fastapi import UploadFile

logger = logging.getLogger(__name__)

# Allowed image types
ALLOWED_IMAGE_TYPES = ['image/jpeg', 'image/png', 'image/jpg', 'image/webp']
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB


class EventPhotoService:
    """Service for managing event photos"""

    @staticmethod
    def generate_photo_id() -> str:
        """Generate unique photo ID"""
        timestamp = datetime.utcnow().strftime('%Y%m%d')
        unique_id = uuid.uuid4().hex[:8].upper()
        return f"PHT-{timestamp}-{unique_id}"

    @staticmethod
    async def validate_attendance(
        db: AsyncIOMotorDatabase,
        event_id: str,
        user_id: str
    ) -> Tuple[bool, str]:
        """Check if user attended the event"""
        registration = await db.event_registrations.find_one({
            "event_id": event_id,
            "user_id": user_id
        })

        if not registration:
            return False, "You are not registered for this event"

        status = registration.get("registration_status", "").lower()
        if status != "attended":
            return False, "You can only upload photos for events you have attended"

        return True, "Validated"

    @staticmethod
    async def upload_photo(
        db: AsyncIOMotorDatabase,
        event_id: str,
        user_id: str,
        user_name: str,
        file: UploadFile,
        caption: Optional[str] = None
    ) -> Tuple[bool, str, Optional[dict]]:
        """
        Upload a photo to an event

        Args:
            db: Database connection
            event_id: Event ID
            user_id: User ID
            user_name: User display name
            file: Uploaded file
            caption: Optional caption

        Returns:
            Tuple of (success, message, photo_data)
        """
        try:
            # Validate event exists
            event = await db.events.find_one({"event_id": event_id})
            if not event:
                return False, "Event not found", None

            # Validate attendance
            is_valid, message = await EventPhotoService.validate_attendance(db, event_id, user_id)
            if not is_valid:
                return False, message, None

            # Validate file type
            if file.content_type not in ALLOWED_IMAGE_TYPES:
                return False, f"Invalid file type. Allowed: JPEG, PNG, WebP", None

            # Read file content
            content = await file.read()

            # Validate file size
            if len(content) > MAX_FILE_SIZE:
                return False, f"File too large. Maximum size: 5MB", None

            # Generate photo ID and filename
            photo_id = EventPhotoService.generate_photo_id()
            file_extension = file.filename.split('.')[-1] if '.' in file.filename else 'jpg'
            filename = f"{uuid.uuid4().hex}.{file_extension}"

            # Create uploads directory
            upload_dir = f"uploads/event_photos/{event_id}"
            os.makedirs(upload_dir, exist_ok=True)

            # Save file
            file_path = f"{upload_dir}/{filename}"
            with open(file_path, 'wb') as f:
                f.write(content)

            photo_url = f"/{file_path}"

            # Create photo document
            photo_doc = {
                "photo_id": photo_id,
                "event_id": event_id,
                "user_id": user_id,
                "user_name": user_name,
                "photo_url": photo_url,
                "caption": caption[:500] if caption else None,
                "uploaded_at": datetime.utcnow(),
                "is_hidden": False,
                "hidden_by": None,
                "hidden_at": None
            }

            await db.event_photos.insert_one(photo_doc)

            logger.info(f"Photo uploaded: {photo_id} for event {event_id} by user {user_id}")

            return True, "Photo uploaded successfully", {
                "photo_id": photo_id,
                "photo_url": photo_url
            }

        except Exception as e:
            logger.error(f"Error uploading photo: {e}")
            return False, f"Failed to upload photo: {str(e)}", None

    @staticmethod
    async def get_event_photos(
        db: AsyncIOMotorDatabase,
        event_id: str,
        skip: int = 0,
        limit: int = 20,
        include_hidden: bool = False
    ) -> Tuple[bool, str, List[dict], int]:
        """
        Get photos for an event

        Args:
            db: Database connection
            event_id: Event ID
            skip: Pagination offset
            limit: Max photos to return
            include_hidden: Include hidden photos (for organizers)

        Returns:
            Tuple of (success, message, photos, total)
        """
        try:
            query = {"event_id": event_id}
            if not include_hidden:
                query["is_hidden"] = False

            # Get total count
            total = await db.event_photos.count_documents(query)

            # Get photos sorted by upload date (newest first)
            cursor = db.event_photos.find(query).sort(
                "uploaded_at", -1
            ).skip(skip).limit(limit)

            photos = []
            async for photo in cursor:
                photos.append({
                    "photo_id": photo["photo_id"],
                    "event_id": photo["event_id"],
                    "user_id": photo["user_id"],
                    "user_name": photo["user_name"],
                    "photo_url": photo["photo_url"],
                    "caption": photo.get("caption"),
                    "uploaded_at": photo["uploaded_at"].isoformat() if photo.get("uploaded_at") else None,
                    "is_hidden": photo.get("is_hidden", False)
                })

            return True, "Photos retrieved", photos, total

        except Exception as e:
            logger.error(f"Error getting event photos: {e}")
            return False, f"Failed to get photos: {str(e)}", [], 0

    @staticmethod
    async def delete_photo(
        db: AsyncIOMotorDatabase,
        photo_id: str,
        user_id: str,
        is_organizer: bool = False
    ) -> Tuple[bool, str]:
        """
        Delete a photo

        Args:
            db: Database connection
            photo_id: Photo ID
            user_id: Requesting user ID
            is_organizer: Whether user is event organizer

        Returns:
            Tuple of (success, message)
        """
        try:
            photo = await db.event_photos.find_one({"photo_id": photo_id})
            if not photo:
                return False, "Photo not found"

            # Check permission
            if not is_organizer and photo["user_id"] != user_id:
                return False, "You can only delete your own photos"

            # Delete file
            file_path = photo["photo_url"].lstrip("/")
            if os.path.exists(file_path):
                os.remove(file_path)

            # Delete from database
            await db.event_photos.delete_one({"photo_id": photo_id})

            logger.info(f"Photo deleted: {photo_id} by user {user_id}")

            return True, "Photo deleted successfully"

        except Exception as e:
            logger.error(f"Error deleting photo: {e}")
            return False, f"Failed to delete photo: {str(e)}"

    @staticmethod
    async def toggle_photo_visibility(
        db: AsyncIOMotorDatabase,
        photo_id: str,
        organizer_id: str,
        hide: bool = True
    ) -> Tuple[bool, str]:
        """
        Hide or show a photo (organizer moderation)

        Args:
            db: Database connection
            photo_id: Photo ID
            organizer_id: Organizer user ID
            hide: True to hide, False to show

        Returns:
            Tuple of (success, message)
        """
        try:
            photo = await db.event_photos.find_one({"photo_id": photo_id})
            if not photo:
                return False, "Photo not found"

            # Update visibility
            update_data = {
                "is_hidden": hide,
                "hidden_by": organizer_id if hide else None,
                "hidden_at": datetime.utcnow() if hide else None
            }

            await db.event_photos.update_one(
                {"photo_id": photo_id},
                {"$set": update_data}
            )

            action = "hidden" if hide else "shown"
            logger.info(f"Photo {photo_id} {action} by organizer {organizer_id}")

            return True, f"Photo {action} successfully"

        except Exception as e:
            logger.error(f"Error toggling photo visibility: {e}")
            return False, f"Failed to update photo: {str(e)}"

    @staticmethod
    async def get_user_photos(
        db: AsyncIOMotorDatabase,
        user_id: str,
        skip: int = 0,
        limit: int = 20
    ) -> Tuple[bool, str, List[dict], int]:
        """
        Get all photos uploaded by a user

        Args:
            db: Database connection
            user_id: User ID
            skip: Pagination offset
            limit: Max photos to return

        Returns:
            Tuple of (success, message, photos, total)
        """
        try:
            query = {"user_id": user_id, "is_hidden": False}

            # Get total count
            total = await db.event_photos.count_documents(query)

            # Get photos with event info
            pipeline = [
                {"$match": query},
                {"$sort": {"uploaded_at": -1}},
                {"$skip": skip},
                {"$limit": limit},
                {
                    "$lookup": {
                        "from": "events",
                        "localField": "event_id",
                        "foreignField": "event_id",
                        "as": "event"
                    }
                },
                {"$unwind": {"path": "$event", "preserveNullAndEmptyArrays": True}}
            ]

            photos = []
            async for photo in db.event_photos.aggregate(pipeline):
                event = photo.get("event", {})
                photos.append({
                    "photo_id": photo["photo_id"],
                    "event_id": photo["event_id"],
                    "event_title": event.get("title", "Unknown Event"),
                    "photo_url": photo["photo_url"],
                    "caption": photo.get("caption"),
                    "uploaded_at": photo["uploaded_at"].isoformat() if photo.get("uploaded_at") else None
                })

            return True, "Photos retrieved", photos, total

        except Exception as e:
            logger.error(f"Error getting user photos: {e}")
            return False, f"Failed to get photos: {str(e)}", [], 0
