"""
Community Post Service
Handle posts within communities, including event recaps
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
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB per image
MAX_PHOTOS_PER_POST = 5


class CommunityPostService:
    """Service for managing community posts"""

    @staticmethod
    def generate_post_id() -> str:
        """Generate unique post ID"""
        timestamp = datetime.utcnow().strftime('%Y%m%d')
        unique_id = uuid.uuid4().hex[:8].upper()
        return f"PST-{timestamp}-{unique_id}"

    @staticmethod
    async def check_membership(
        db: AsyncIOMotorDatabase,
        community_id: str,
        user_id: str
    ) -> Tuple[bool, bool, str]:
        """
        Check if user is a member/organizer of community

        Returns:
            Tuple of (is_member, is_organizer, message)
        """
        community = await db.communities.find_one({"community_id": community_id})
        if not community:
            return False, False, "Community not found"

        # Check if organizer
        if community.get("organizer_id") == user_id:
            return True, True, "Organizer"

        # Check if member (membership is stored in member_ids array)
        member_ids = community.get("member_ids", [])
        if user_id in member_ids:
            return True, False, "Member"

        return False, False, "Not a member"

    @staticmethod
    async def create_post(
        db: AsyncIOMotorDatabase,
        community_id: str,
        author_id: str,
        author_name: str,
        content: str,
        post_type: str = "general",
        related_event_id: Optional[str] = None,
        photos: Optional[List[UploadFile]] = None
    ) -> Tuple[bool, str, Optional[dict]]:
        """
        Create a new community post

        Args:
            db: Database connection
            community_id: Community ID
            author_id: Author user ID
            author_name: Author display name
            content: Post content
            post_type: "general", "announcement", or "event_recap"
            related_event_id: Event ID if this is an event recap
            photos: List of uploaded photos (max 5)

        Returns:
            Tuple of (success, message, post_data)
        """
        try:
            # Validate membership
            is_member, is_organizer, msg = await CommunityPostService.check_membership(
                db, community_id, author_id
            )

            if not is_member:
                return False, msg, None

            # Only organizers can post announcements
            if post_type == "announcement" and not is_organizer:
                return False, "Only organizers can post announcements", None

            # Validate content
            if not content or len(content.strip()) < 10:
                return False, "Post content must be at least 10 characters", None

            if len(content) > 5000:
                return False, "Post content cannot exceed 5000 characters", None

            # Validate event recap
            if post_type == "event_recap" and related_event_id:
                event = await db.events.find_one({"event_id": related_event_id})
                if not event:
                    return False, "Related event not found", None

            # Handle photo uploads
            photo_urls = []
            if photos:
                if len(photos) > MAX_PHOTOS_PER_POST:
                    return False, f"Maximum {MAX_PHOTOS_PER_POST} photos allowed", None

                upload_dir = f"uploads/posts/{community_id}"
                os.makedirs(upload_dir, exist_ok=True)

                for photo in photos:
                    if photo.content_type not in ALLOWED_IMAGE_TYPES:
                        continue

                    photo_content = await photo.read()
                    if len(photo_content) > MAX_FILE_SIZE:
                        continue

                    file_extension = photo.filename.split('.')[-1] if '.' in photo.filename else 'jpg'
                    filename = f"{uuid.uuid4().hex}.{file_extension}"
                    file_path = f"{upload_dir}/{filename}"

                    with open(file_path, 'wb') as f:
                        f.write(photo_content)

                    photo_urls.append(f"/{file_path}")

            # Create post document
            post_id = CommunityPostService.generate_post_id()
            post_doc = {
                "post_id": post_id,
                "community_id": community_id,
                "author_id": author_id,
                "author_name": author_name,
                "content": content.strip(),
                "photos": photo_urls,
                "post_type": post_type,
                "related_event_id": related_event_id,
                "likes_count": 0,
                "likes": [],
                "is_pinned": False,
                "is_hidden": False,
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            }

            await db.community_posts.insert_one(post_doc)

            logger.info(f"Post created: {post_id} in community {community_id}")

            return True, "Post created successfully", {
                "post_id": post_id,
                "photos": photo_urls
            }

        except Exception as e:
            logger.error(f"Error creating post: {e}")
            return False, f"Failed to create post: {str(e)}", None

    @staticmethod
    async def get_community_posts(
        db: AsyncIOMotorDatabase,
        community_id: str,
        skip: int = 0,
        limit: int = 20,
        include_hidden: bool = False
    ) -> Tuple[bool, str, List[dict], int]:
        """
        Get posts for a community

        Args:
            db: Database connection
            community_id: Community ID
            skip: Pagination offset
            limit: Max posts to return
            include_hidden: Include hidden posts (for organizers)

        Returns:
            Tuple of (success, message, posts, total)
        """
        try:
            query = {"community_id": community_id}
            if not include_hidden:
                query["is_hidden"] = False

            # Get total count
            total = await db.community_posts.count_documents(query)

            # Get posts sorted by pinned first, then by date
            cursor = db.community_posts.find(query).sort([
                ("is_pinned", -1),
                ("created_at", -1)
            ]).skip(skip).limit(limit)

            posts = []
            async for post in cursor:
                # Get author profile picture
                author = await db.users.find_one({"user_id": post["author_id"]})
                author_picture = author.get("profile_picture") if author else None

                # Get related event details if event recap
                event_details = None
                if post.get("related_event_id"):
                    event = await db.events.find_one({"event_id": post["related_event_id"]})
                    if event:
                        event_details = {
                            "event_id": event["event_id"],
                            "title": event.get("title"),
                            "event_date": event.get("event_date").isoformat() if event.get("event_date") else None
                        }

                posts.append({
                    "post_id": post["post_id"],
                    "community_id": post["community_id"],
                    "author_id": post["author_id"],
                    "author_name": post["author_name"],
                    "author_picture": author_picture,
                    "content": post["content"],
                    "photos": post.get("photos", []),
                    "post_type": post.get("post_type", "general"),
                    "related_event": event_details,
                    "likes_count": post.get("likes_count", 0),
                    "is_pinned": post.get("is_pinned", False),
                    "is_hidden": post.get("is_hidden", False),
                    "created_at": post["created_at"].isoformat() if post.get("created_at") else None,
                    "updated_at": post["updated_at"].isoformat() if post.get("updated_at") else None
                })

            return True, "Posts retrieved", posts, total

        except Exception as e:
            logger.error(f"Error getting community posts: {e}")
            return False, f"Failed to get posts: {str(e)}", [], 0

    @staticmethod
    async def update_post(
        db: AsyncIOMotorDatabase,
        post_id: str,
        user_id: str,
        content: Optional[str] = None
    ) -> Tuple[bool, str]:
        """
        Update a post (author only)

        Args:
            db: Database connection
            post_id: Post ID
            user_id: Requesting user ID
            content: New content

        Returns:
            Tuple of (success, message)
        """
        try:
            post = await db.community_posts.find_one({"post_id": post_id})
            if not post:
                return False, "Post not found"

            if post["author_id"] != user_id:
                return False, "You can only edit your own posts"

            update_data = {"updated_at": datetime.utcnow()}

            if content:
                if len(content.strip()) < 10:
                    return False, "Post content must be at least 10 characters"
                if len(content) > 5000:
                    return False, "Post content cannot exceed 5000 characters"
                update_data["content"] = content.strip()

            await db.community_posts.update_one(
                {"post_id": post_id},
                {"$set": update_data}
            )

            return True, "Post updated successfully"

        except Exception as e:
            logger.error(f"Error updating post: {e}")
            return False, f"Failed to update post: {str(e)}"

    @staticmethod
    async def delete_post(
        db: AsyncIOMotorDatabase,
        post_id: str,
        user_id: str,
        is_organizer: bool = False
    ) -> Tuple[bool, str]:
        """
        Delete a post

        Args:
            db: Database connection
            post_id: Post ID
            user_id: Requesting user ID
            is_organizer: Whether user is community organizer

        Returns:
            Tuple of (success, message)
        """
        try:
            post = await db.community_posts.find_one({"post_id": post_id})
            if not post:
                return False, "Post not found"

            # Check permission
            if not is_organizer and post["author_id"] != user_id:
                return False, "You can only delete your own posts"

            # Delete photos
            for photo_url in post.get("photos", []):
                file_path = photo_url.lstrip("/")
                if os.path.exists(file_path):
                    os.remove(file_path)

            # Delete from database
            await db.community_posts.delete_one({"post_id": post_id})

            logger.info(f"Post deleted: {post_id}")

            return True, "Post deleted successfully"

        except Exception as e:
            logger.error(f"Error deleting post: {e}")
            return False, f"Failed to delete post: {str(e)}"

    @staticmethod
    async def toggle_like(
        db: AsyncIOMotorDatabase,
        post_id: str,
        user_id: str
    ) -> Tuple[bool, str, bool]:
        """
        Toggle like on a post

        Args:
            db: Database connection
            post_id: Post ID
            user_id: User ID

        Returns:
            Tuple of (success, message, is_liked)
        """
        try:
            post = await db.community_posts.find_one({"post_id": post_id})
            if not post:
                return False, "Post not found", False

            likes = post.get("likes", [])
            is_liked = user_id in likes

            if is_liked:
                # Unlike
                await db.community_posts.update_one(
                    {"post_id": post_id},
                    {
                        "$pull": {"likes": user_id},
                        "$inc": {"likes_count": -1}
                    }
                )
                return True, "Post unliked", False
            else:
                # Like
                await db.community_posts.update_one(
                    {"post_id": post_id},
                    {
                        "$addToSet": {"likes": user_id},
                        "$inc": {"likes_count": 1}
                    }
                )
                return True, "Post liked", True

        except Exception as e:
            logger.error(f"Error toggling like: {e}")
            return False, f"Failed to toggle like: {str(e)}", False

    @staticmethod
    async def toggle_pin(
        db: AsyncIOMotorDatabase,
        post_id: str,
        organizer_id: str,
        pin: bool = True
    ) -> Tuple[bool, str]:
        """
        Pin or unpin a post (organizer only)

        Args:
            db: Database connection
            post_id: Post ID
            organizer_id: Organizer user ID
            pin: True to pin, False to unpin

        Returns:
            Tuple of (success, message)
        """
        try:
            post = await db.community_posts.find_one({"post_id": post_id})
            if not post:
                return False, "Post not found"

            await db.community_posts.update_one(
                {"post_id": post_id},
                {"$set": {"is_pinned": pin, "updated_at": datetime.utcnow()}}
            )

            action = "pinned" if pin else "unpinned"
            return True, f"Post {action} successfully"

        except Exception as e:
            logger.error(f"Error toggling pin: {e}")
            return False, f"Failed to toggle pin: {str(e)}"

    @staticmethod
    async def toggle_visibility(
        db: AsyncIOMotorDatabase,
        post_id: str,
        organizer_id: str,
        hide: bool = True
    ) -> Tuple[bool, str]:
        """
        Hide or show a post (organizer moderation)

        Args:
            db: Database connection
            post_id: Post ID
            organizer_id: Organizer user ID
            hide: True to hide, False to show

        Returns:
            Tuple of (success, message)
        """
        try:
            post = await db.community_posts.find_one({"post_id": post_id})
            if not post:
                return False, "Post not found"

            await db.community_posts.update_one(
                {"post_id": post_id},
                {"$set": {"is_hidden": hide, "updated_at": datetime.utcnow()}}
            )

            action = "hidden" if hide else "shown"
            return True, f"Post {action} successfully"

        except Exception as e:
            logger.error(f"Error toggling visibility: {e}")
            return False, f"Failed to update post: {str(e)}"

    @staticmethod
    async def check_if_user_liked(
        db: AsyncIOMotorDatabase,
        post_id: str,
        user_id: str
    ) -> bool:
        """Check if user has liked a post"""
        post = await db.community_posts.find_one({"post_id": post_id})
        if not post:
            return False
        return user_id in post.get("likes", [])
