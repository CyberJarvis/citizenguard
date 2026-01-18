"""
Community Service
Handles community CRUD operations, membership management.
"""

import logging
import os
import uuid
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any, Tuple

from motor.motor_asyncio import AsyncIOMotorDatabase
from fastapi import UploadFile

from app.models.community import (
    Community,
    CommunityCategory,
    CommunityCreate,
    CommunityUpdate,
    INDIAN_COASTAL_ZONES,
    INDIAN_COASTAL_STATES,
)
from app.models.user import User
from app.models.rbac import UserRole

logger = logging.getLogger(__name__)

# Constants
UPLOAD_DIR = "uploads/community_images"

# Global service instance
_community_service: Optional["CommunityService"] = None


def get_community_service(db: AsyncIOMotorDatabase = None) -> "CommunityService":
    """Get or create community service singleton"""
    global _community_service
    if _community_service is None:
        _community_service = CommunityService(db)
    elif db is not None:
        _community_service.db = db
    return _community_service


class CommunityService:
    """Service for managing communities"""

    def __init__(self, db: AsyncIOMotorDatabase = None):
        self.db = db
        self._initialized = False

    async def initialize(self, db: AsyncIOMotorDatabase = None):
        """Initialize the service with database connection"""
        if db is not None:
            self.db = db

        if self.db is None:
            logger.warning("No database connection provided to CommunityService")
            return

        # Ensure upload directory exists
        os.makedirs(UPLOAD_DIR, exist_ok=True)

        self._initialized = True
        logger.info("CommunityService initialized successfully")

    def _generate_community_id(self) -> str:
        """Generate unique community ID (COM-YYYYMMDD-XXXXX)"""
        date_part = datetime.now(timezone.utc).strftime("%Y%m%d")
        random_part = uuid.uuid4().hex[:5].upper()
        return f"COM-{date_part}-{random_part}"

    async def create_community(
        self,
        user: User,
        community_data: CommunityCreate
    ) -> Tuple[bool, str, Optional[Community]]:
        """
        Create a new community.

        Args:
            user: Current user (must be verified organizer)
            community_data: Community creation data

        Returns:
            Tuple of (success, message, community)
        """
        # Validate user role
        if user.role not in [UserRole.VERIFIED_ORGANIZER, UserRole.AUTHORITY, UserRole.AUTHORITY_ADMIN]:
            return False, "Only verified organizers can create communities", None

        # Validate coastal zone and state
        if community_data.coastal_zone not in INDIAN_COASTAL_ZONES:
            return False, f"Invalid coastal zone. Must be one of: {', '.join(INDIAN_COASTAL_ZONES)}", None

        if community_data.state not in INDIAN_COASTAL_STATES:
            return False, f"Invalid state. Must be one of: {', '.join(INDIAN_COASTAL_STATES)}", None

        try:
            now = datetime.now(timezone.utc)

            # Create community
            community = Community(
                community_id=self._generate_community_id(),
                name=community_data.name,
                description=community_data.description,
                category=community_data.category,
                organizer_id=user.user_id,
                organizer_name=user.name or user.email,
                coastal_zone=community_data.coastal_zone,
                state=community_data.state,
                member_ids=[user.user_id],  # Organizer is first member
                member_count=1,
                is_active=True,
                is_public=community_data.is_public,
                created_at=now,
                updated_at=now
            )

            # Insert into database
            await self.db.communities.insert_one(community.to_mongo())

            logger.info(f"Community created: {community.community_id} by {user.user_id}")

            return True, "Community created successfully!", community

        except Exception as e:
            logger.error(f"Failed to create community: {e}")
            return False, "Failed to create community. Please try again.", None

    async def get_community_by_id(self, community_id: str) -> Optional[Community]:
        """Get a community by ID."""
        doc = await self.db.communities.find_one({"community_id": community_id})
        if doc:
            return Community.from_mongo(doc)
        return None

    async def update_community(
        self,
        community_id: str,
        user: User,
        update_data: CommunityUpdate
    ) -> Tuple[bool, str, Optional[Community]]:
        """
        Update a community.

        Args:
            community_id: Community ID to update
            user: Current user (must be organizer or admin)
            update_data: Update data

        Returns:
            Tuple of (success, message, updated community)
        """
        community = await self.get_community_by_id(community_id)
        if not community:
            return False, "Community not found", None

        # Check ownership
        if community.organizer_id != user.user_id and user.role != UserRole.AUTHORITY_ADMIN:
            return False, "You don't have permission to update this community", None

        try:
            # Build update dict
            update_dict = {"updated_at": datetime.now(timezone.utc)}

            if update_data.name is not None:
                update_dict["name"] = update_data.name
            if update_data.description is not None:
                update_dict["description"] = update_data.description
            if update_data.category is not None:
                update_dict["category"] = update_data.category.value
            if update_data.is_public is not None:
                update_dict["is_public"] = update_data.is_public

            await self.db.communities.update_one(
                {"community_id": community_id},
                {"$set": update_dict}
            )

            # Get updated community
            updated = await self.get_community_by_id(community_id)
            return True, "Community updated successfully", updated

        except Exception as e:
            logger.error(f"Failed to update community: {e}")
            return False, "Failed to update community", None

    async def delete_community(
        self,
        community_id: str,
        user: User
    ) -> Tuple[bool, str]:
        """
        Delete a community (soft delete by setting is_active=False).

        Args:
            community_id: Community ID to delete
            user: Current user (must be organizer or admin)

        Returns:
            Tuple of (success, message)
        """
        community = await self.get_community_by_id(community_id)
        if not community:
            return False, "Community not found"

        # Check ownership
        if community.organizer_id != user.user_id and user.role != UserRole.AUTHORITY_ADMIN:
            return False, "You don't have permission to delete this community"

        try:
            await self.db.communities.update_one(
                {"community_id": community_id},
                {"$set": {"is_active": False, "updated_at": datetime.now(timezone.utc)}}
            )

            logger.info(f"Community {community_id} deleted by {user.user_id}")
            return True, "Community deleted successfully"

        except Exception as e:
            logger.error(f"Failed to delete community: {e}")
            return False, "Failed to delete community"

    async def list_communities(
        self,
        coastal_zone: Optional[str] = None,
        state: Optional[str] = None,
        category: Optional[CommunityCategory] = None,
        search: Optional[str] = None,
        skip: int = 0,
        limit: int = 20,
        include_inactive: bool = False
    ) -> Tuple[List[Community], int]:
        """
        List communities with filters.

        Returns:
            Tuple of (communities list, total count)
        """
        query = {}

        if not include_inactive:
            query["is_active"] = True

        if coastal_zone:
            query["coastal_zone"] = coastal_zone
        if state:
            query["state"] = state
        if category:
            query["category"] = category.value
        if search:
            query["$or"] = [
                {"name": {"$regex": search, "$options": "i"}},
                {"description": {"$regex": search, "$options": "i"}}
            ]

        total = await self.db.communities.count_documents(query)

        cursor = self.db.communities.find(query)
        cursor = cursor.sort([("member_count", -1), ("created_at", -1)]).skip(skip).limit(limit)

        communities = []
        async for doc in cursor:
            communities.append(Community.from_mongo(doc))

        return communities, total

    async def join_community(
        self,
        community_id: str,
        user: User
    ) -> Tuple[bool, str]:
        """
        Join a community.

        Args:
            community_id: Community to join
            user: User joining

        Returns:
            Tuple of (success, message)
        """
        community = await self.get_community_by_id(community_id)
        if not community:
            return False, "Community not found"

        if not community.is_active:
            return False, "This community is no longer active"

        if user.user_id in community.member_ids:
            return False, "You are already a member of this community"

        try:
            await self.db.communities.update_one(
                {"community_id": community_id},
                {
                    "$addToSet": {"member_ids": user.user_id},
                    "$inc": {"member_count": 1},
                    "$set": {"updated_at": datetime.now(timezone.utc)}
                }
            )

            logger.info(f"User {user.user_id} joined community {community_id}")
            return True, "Successfully joined the community!"

        except Exception as e:
            logger.error(f"Failed to join community: {e}")
            return False, "Failed to join community"

    async def leave_community(
        self,
        community_id: str,
        user: User
    ) -> Tuple[bool, str]:
        """
        Leave a community.

        Args:
            community_id: Community to leave
            user: User leaving

        Returns:
            Tuple of (success, message)
        """
        community = await self.get_community_by_id(community_id)
        if not community:
            return False, "Community not found"

        if user.user_id not in community.member_ids:
            return False, "You are not a member of this community"

        if user.user_id == community.organizer_id:
            return False, "Organizers cannot leave their own community. Transfer ownership first or delete the community."

        try:
            await self.db.communities.update_one(
                {"community_id": community_id},
                {
                    "$pull": {"member_ids": user.user_id},
                    "$inc": {"member_count": -1},
                    "$set": {"updated_at": datetime.now(timezone.utc)}
                }
            )

            logger.info(f"User {user.user_id} left community {community_id}")
            return True, "Successfully left the community"

        except Exception as e:
            logger.error(f"Failed to leave community: {e}")
            return False, "Failed to leave community"

    async def get_user_communities(
        self,
        user_id: str,
        skip: int = 0,
        limit: int = 20
    ) -> Tuple[List[Community], int]:
        """
        Get communities a user is a member of.

        Returns:
            Tuple of (communities list, total count)
        """
        query = {
            "member_ids": user_id,
            "is_active": True
        }

        total = await self.db.communities.count_documents(query)

        cursor = self.db.communities.find(query)
        cursor = cursor.sort("created_at", -1).skip(skip).limit(limit)

        communities = []
        async for doc in cursor:
            communities.append(Community.from_mongo(doc))

        return communities, total

    async def get_organizer_communities(
        self,
        organizer_id: str,
        skip: int = 0,
        limit: int = 20
    ) -> Tuple[List[Community], int]:
        """
        Get communities organized by a user.

        Returns:
            Tuple of (communities list, total count)
        """
        query = {
            "organizer_id": organizer_id,
            "is_active": True
        }

        total = await self.db.communities.count_documents(query)

        cursor = self.db.communities.find(query)
        cursor = cursor.sort("created_at", -1).skip(skip).limit(limit)

        communities = []
        async for doc in cursor:
            communities.append(Community.from_mongo(doc))

        return communities, total

    async def get_community_members(
        self,
        community_id: str,
        skip: int = 0,
        limit: int = 50
    ) -> Tuple[List[Dict[str, Any]], int]:
        """
        Get members of a community with their basic info.

        Returns:
            Tuple of (members list, total count)
        """
        community = await self.get_community_by_id(community_id)
        if not community:
            return [], 0

        total = len(community.member_ids)
        member_ids = community.member_ids[skip:skip + limit]

        # Get user details
        members = []
        async for user_doc in self.db.users.find(
            {"user_id": {"$in": member_ids}},
            {"user_id": 1, "name": 1, "email": 1, "profile_picture": 1, "credibility_score": 1}
        ):
            members.append({
                "user_id": user_doc.get("user_id"),
                "name": user_doc.get("name") or user_doc.get("email"),
                "profile_picture": user_doc.get("profile_picture"),
                "credibility_score": user_doc.get("credibility_score", 50),
                "is_organizer": user_doc.get("user_id") == community.organizer_id
            })

        return members, total

    async def upload_community_image(
        self,
        community_id: str,
        user: User,
        file: UploadFile,
        image_type: str = "cover"  # "cover" or "logo"
    ) -> Tuple[bool, str, Optional[str]]:
        """
        Upload a community image (cover or logo).

        Returns:
            Tuple of (success, message, image_url)
        """
        logger.info(f"Uploading image for community {community_id} by user {user.user_id}")

        community = await self.get_community_by_id(community_id)
        if not community:
            logger.error(f"Community not found: {community_id}")
            return False, "Community not found", None

        # Check ownership
        logger.info(f"Checking ownership: community.organizer_id={community.organizer_id}, user.user_id={user.user_id}, user.role={user.role}")
        if community.organizer_id != user.user_id and user.role != UserRole.AUTHORITY_ADMIN:
            logger.warning(f"Permission denied for user {user.user_id} to update community {community_id}")
            return False, "You don't have permission to update this community", None

        # Validate file type
        allowed_types = ["image/jpeg", "image/png", "image/jpg", "image/webp"]
        logger.info(f"File content_type: {file.content_type}, filename: {file.filename}")
        if file.content_type not in allowed_types:
            logger.warning(f"Invalid file type: {file.content_type}")
            return False, "Invalid file type. Please upload JPEG, PNG, or WebP images.", None

        try:
            # Read file
            content = await file.read()

            # Validate size (2MB max)
            if len(content) > 2 * 1024 * 1024:
                return False, "File too large. Maximum size: 2MB", None

            # Generate filename
            extension = file.filename.split(".")[-1] if "." in file.filename else "jpg"
            filename = f"{community_id}_{image_type}_{uuid.uuid4().hex[:8]}.{extension}"
            file_path = os.path.join(UPLOAD_DIR, filename)

            # Save file
            with open(file_path, "wb") as f:
                f.write(content)

            # Update community
            field = "cover_image_url" if image_type == "cover" else "logo_url"
            image_url = f"/uploads/community_images/{filename}"

            await self.db.communities.update_one(
                {"community_id": community_id},
                {"$set": {field: image_url, "updated_at": datetime.now(timezone.utc)}}
            )

            return True, "Image uploaded successfully", image_url

        except Exception as e:
            logger.error(f"Failed to upload community image: {e}")
            return False, "Failed to upload image", None

    async def get_community_statistics(self, community_id: str) -> Dict[str, Any]:
        """Get statistics for a community."""
        community = await self.get_community_by_id(community_id)
        if not community:
            return {}

        # Count events
        event_count = await self.db.events.count_documents({
            "community_id": community_id
        })

        # Count completed events
        completed_events = await self.db.events.count_documents({
            "community_id": community_id,
            "status": "completed"
        })

        return {
            "member_count": community.member_count,
            "total_events": event_count,
            "completed_events": completed_events,
            "total_volunteers": community.total_volunteers
        }
