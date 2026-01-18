"""
Points Service
Handles user points, badges, and leaderboard functionality.
"""

import logging
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any, Tuple

from motor.motor_asyncio import AsyncIOMotorDatabase

from app.models.community import (
    UserPoints,
    BADGE_DEFINITIONS,
    LeaderboardEntry,
)

logger = logging.getLogger(__name__)

# Global service instance
_points_service: Optional["PointsService"] = None


def get_points_service(db: AsyncIOMotorDatabase = None) -> "PointsService":
    """Get or create points service singleton"""
    global _points_service
    if _points_service is None:
        _points_service = PointsService(db)
    elif db is not None:
        _points_service.db = db
    return _points_service


class PointsService:
    """Service for managing user points and badges"""

    def __init__(self, db: AsyncIOMotorDatabase = None):
        self.db = db
        self._initialized = False

    async def initialize(self, db: AsyncIOMotorDatabase = None):
        """Initialize the service with database connection"""
        if db is not None:
            self.db = db

        if self.db is None:
            logger.warning("No database connection provided to PointsService")
            return

        self._initialized = True
        logger.info("PointsService initialized successfully")

    async def get_or_create_user_points(self, user_id: str) -> UserPoints:
        """Get user points or create if not exists"""
        doc = await self.db.user_points.find_one({"user_id": user_id})

        if doc:
            return UserPoints.from_mongo(doc)

        # Create new user points record
        user_points = UserPoints(
            user_id=user_id,
            total_points=0,
            events_attended=0,
            emergency_events_attended=0,
            events_organized=0,
            communities_joined=0,
            badges=[],
            badges_earned_at={},
            updated_at=datetime.now(timezone.utc)
        )

        await self.db.user_points.insert_one(user_points.to_mongo())
        return user_points

    async def add_points(
        self,
        user_id: str,
        points: int,
        is_emergency: bool = False,
        is_organizer: bool = False
    ) -> Tuple[int, List[str]]:
        """
        Add points to a user and check for new badges.

        Args:
            user_id: User ID
            points: Points to add
            is_emergency: Whether this is from an emergency event
            is_organizer: Whether user is the organizer (counts towards events_organized)

        Returns:
            Tuple of (new_total_points, newly_earned_badges)
        """
        user_points = await self.get_or_create_user_points(user_id)
        now = datetime.now(timezone.utc)

        # Update counters
        update = {
            "$inc": {"total_points": points},
            "$set": {"updated_at": now}
        }

        if is_organizer:
            update["$inc"]["events_organized"] = 1
        else:
            update["$inc"]["events_attended"] = 1
            if is_emergency:
                update["$inc"]["emergency_events_attended"] = 1

        await self.db.user_points.update_one(
            {"user_id": user_id},
            update
        )

        # Refresh user points
        user_points = await self.get_or_create_user_points(user_id)

        # Check for new badges
        new_badges = await self._check_and_award_badges(user_id, user_points)

        logger.info(f"Added {points} points to user {user_id}. New total: {user_points.total_points + points}")

        return user_points.total_points + points, new_badges

    async def _check_and_award_badges(
        self,
        user_id: str,
        user_points: UserPoints
    ) -> List[str]:
        """Check and award any new badges the user has earned"""
        new_badges = []
        now = datetime.now(timezone.utc)

        for badge_id, badge_info in BADGE_DEFINITIONS.items():
            # Skip if already has badge
            if badge_id in user_points.badges:
                continue

            requirement = badge_info.get("requirement", {})
            earned = True

            # Check each requirement
            for req_key, req_value in requirement.items():
                user_value = getattr(user_points, req_key, 0)
                if user_value < req_value:
                    earned = False
                    break

            if earned:
                new_badges.append(badge_id)

                # Update user badges
                await self.db.user_points.update_one(
                    {"user_id": user_id},
                    {
                        "$push": {"badges": badge_id},
                        "$set": {f"badges_earned_at.{badge_id}": now}
                    }
                )

                logger.info(f"User {user_id} earned badge: {badge_id}")

        return new_badges

    async def increment_communities_joined(self, user_id: str):
        """Increment communities joined counter"""
        await self.get_or_create_user_points(user_id)
        await self.db.user_points.update_one(
            {"user_id": user_id},
            {
                "$inc": {"communities_joined": 1},
                "$set": {"updated_at": datetime.now(timezone.utc)}
            }
        )

    async def decrement_communities_joined(self, user_id: str):
        """Decrement communities joined counter"""
        await self.db.user_points.update_one(
            {"user_id": user_id},
            {
                "$inc": {"communities_joined": -1},
                "$set": {"updated_at": datetime.now(timezone.utc)}
            }
        )

    async def get_user_points(self, user_id: str) -> Dict[str, Any]:
        """Get user points with badge details"""
        user_points = await self.get_or_create_user_points(user_id)

        # Enrich with badge details
        badge_details = []
        for badge_id in user_points.badges:
            if badge_id in BADGE_DEFINITIONS:
                badge_def = BADGE_DEFINITIONS[badge_id]
                badge_details.append({
                    "badge_id": badge_id,
                    "name": badge_def["name"],
                    "description": badge_def["description"],
                    "icon": badge_def["icon"],
                    "earned_at": user_points.badges_earned_at.get(badge_id, "").isoformat()
                        if isinstance(user_points.badges_earned_at.get(badge_id), datetime)
                        else user_points.badges_earned_at.get(badge_id)
                })

        return {
            "user_id": user_points.user_id,
            "total_points": user_points.total_points,
            "events_attended": user_points.events_attended,
            "emergency_events_attended": user_points.emergency_events_attended,
            "events_organized": user_points.events_organized,
            "communities_joined": user_points.communities_joined,
            "badges": badge_details,
            "badge_count": len(user_points.badges),
            "rank": user_points.rank
        }

    async def get_leaderboard(
        self,
        limit: int = 10,
        skip: int = 0
    ) -> Tuple[List[Dict[str, Any]], int]:
        """Get top users by points"""
        total = await self.db.user_points.count_documents({"total_points": {"$gt": 0}})

        cursor = self.db.user_points.find({"total_points": {"$gt": 0}})
        cursor = cursor.sort("total_points", -1).skip(skip).limit(limit)

        leaderboard = []
        rank = skip + 1

        async for doc in cursor:
            user_points = UserPoints.from_mongo(doc)

            # Get user name from users collection
            user_doc = await self.db.users.find_one({"user_id": user_points.user_id})
            user_name = user_doc.get("name", "Anonymous") if user_doc else "Anonymous"
            profile_picture = user_doc.get("profile_picture") if user_doc else None

            leaderboard.append({
                "rank": rank,
                "user_id": user_points.user_id,
                "user_name": user_name,
                "profile_picture": profile_picture,
                "total_points": user_points.total_points,
                "events_attended": user_points.events_attended,
                "badges": user_points.badges,
                "badge_count": len(user_points.badges)
            })
            rank += 1

        return leaderboard, total

    async def get_user_rank(self, user_id: str) -> Dict[str, Any]:
        """Get a user's rank on the leaderboard"""
        user_points = await self.get_or_create_user_points(user_id)

        if user_points.total_points == 0:
            return {
                "user_id": user_id,
                "rank": None,
                "total_points": 0,
                "message": "Participate in events to get on the leaderboard!"
            }

        # Count users with more points
        users_above = await self.db.user_points.count_documents({
            "total_points": {"$gt": user_points.total_points}
        })

        rank = users_above + 1

        # Update rank in database
        await self.db.user_points.update_one(
            {"user_id": user_id},
            {"$set": {"rank": rank}}
        )

        return {
            "user_id": user_id,
            "rank": rank,
            "total_points": user_points.total_points,
            "events_attended": user_points.events_attended,
            "badges": user_points.badges
        }

    async def update_all_ranks(self):
        """Update ranks for all users (can be run periodically)"""
        cursor = self.db.user_points.find({"total_points": {"$gt": 0}})
        cursor = cursor.sort("total_points", -1)

        rank = 1
        async for doc in cursor:
            await self.db.user_points.update_one(
                {"_id": doc["_id"]},
                {"$set": {"rank": rank}}
            )
            rank += 1

        logger.info(f"Updated ranks for {rank - 1} users")

    async def get_badge_info(self, badge_id: str) -> Optional[Dict[str, Any]]:
        """Get badge information"""
        if badge_id not in BADGE_DEFINITIONS:
            return None

        badge = BADGE_DEFINITIONS[badge_id]
        return {
            "badge_id": badge_id,
            "name": badge["name"],
            "description": badge["description"],
            "icon": badge["icon"],
            "requirement": badge["requirement"]
        }

    async def get_all_badges(self) -> List[Dict[str, Any]]:
        """Get all available badges"""
        return [
            {
                "badge_id": badge_id,
                "name": badge["name"],
                "description": badge["description"],
                "icon": badge["icon"],
                "requirement": badge["requirement"]
            }
            for badge_id, badge in BADGE_DEFINITIONS.items()
        ]
