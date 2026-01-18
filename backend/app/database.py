"""
Database Connection Handlers
MongoDB (Motor) and Redis async clients
"""

import logging
from typing import Optional
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
import redis.asyncio as aioredis
from redis.asyncio import Redis

from app.config import settings

logger = logging.getLogger(__name__)


class MongoDB:
    """MongoDB async connection handler"""

    client: Optional[AsyncIOMotorClient] = None
    database: Optional[AsyncIOMotorDatabase] = None

    @classmethod
    async def connect(cls):
        """Establish MongoDB connection"""
        try:
            cls.client = AsyncIOMotorClient(
                settings.MONGODB_URL,
                minPoolSize=settings.MONGODB_MIN_POOL_SIZE,
                maxPoolSize=settings.MONGODB_MAX_POOL_SIZE,
                serverSelectionTimeoutMS=5000,
            )

            cls.database = cls.client[settings.MONGODB_DB_NAME]

            # Test connection
            await cls.client.admin.command("ping")
            logger.info(f"✓ Connected to MongoDB: {settings.MONGODB_DB_NAME}")

            # Create indexes
            await cls._create_indexes()

        except Exception as e:
            logger.error(f"✗ Failed to connect to MongoDB: {e}")
            raise

    @classmethod
    async def disconnect(cls):
        """Close MongoDB connection"""
        if cls.client:
            cls.client.close()
            logger.info("✓ Disconnected from MongoDB")

    @classmethod
    async def _create_indexes(cls):
        """Create database indexes for optimal performance"""
        if cls.database is None:
            return

        from pymongo.errors import DuplicateKeyError, OperationFailure

        try:
            # Users collection indexes
            users_collection = cls.database.users

            # Create indexes with error handling
            try:
                await users_collection.create_index("user_id", unique=True)
            except (DuplicateKeyError, OperationFailure) as e:
                if "E11000" in str(e) or "duplicate key" in str(e).lower():
                    logger.warning(f"⚠ user_id index already exists or has duplicate values. Cleaning up...")
                    # Drop the problematic index and recreate
                    try:
                        await users_collection.drop_index("user_id_1")
                        logger.info("✓ Dropped existing user_id index")
                    except (OperationFailure, Exception) as drop_error:
                        logger.debug(f"Failed to drop index (may not exist): {drop_error}")
                        pass
                else:
                    raise

            try:
                await users_collection.create_index("email", unique=True, sparse=True)
            except (DuplicateKeyError, OperationFailure):
                logger.warning("⚠ email index already exists")

            try:
                await users_collection.create_index("phone", unique=True, sparse=True)
            except (DuplicateKeyError, OperationFailure):
                logger.warning("⚠ phone index already exists")

            try:
                await users_collection.create_index("role")
            except (DuplicateKeyError, OperationFailure):
                logger.warning("⚠ role index already exists")

            # NOTE: Removed geospatial index on location field
            # The location field now stores plain objects with state/region/city
            # for notification matching, not GeoJSON coordinates
            # If you need geospatial queries in the future, use a separate field

            # Audit logs collection indexes
            audit_collection = cls.database.audit_logs
            try:
                await audit_collection.create_index("user_id")
                await audit_collection.create_index("action")
                await audit_collection.create_index("timestamp")
                await audit_collection.create_index([("timestamp", -1)])
            except (DuplicateKeyError, OperationFailure):
                logger.warning("⚠ audit_logs indexes already exist")

            # Refresh tokens collection indexes
            tokens_collection = cls.database.refresh_tokens
            try:
                await tokens_collection.create_index("token_id", unique=True)
                await tokens_collection.create_index("user_id")
                await tokens_collection.create_index("expires_at", expireAfterSeconds=0)  # TTL index
            except (DuplicateKeyError, OperationFailure):
                logger.warning("⚠ refresh_tokens indexes already exist")

            # ============================================================
            # ANALYST MODULE INDEXES
            # ============================================================

            # Analyst notes collection indexes
            analyst_notes = cls.database.analyst_notes
            try:
                await analyst_notes.create_index("note_id", unique=True)
                await analyst_notes.create_index("user_id")
                await analyst_notes.create_index([("user_id", 1), ("created_at", -1)])
                await analyst_notes.create_index([("user_id", 1), ("is_pinned", -1)])
                await analyst_notes.create_index([("user_id", 1), ("tags", 1)])
                await analyst_notes.create_index("reference_id")
            except (DuplicateKeyError, OperationFailure):
                logger.warning("⚠ analyst_notes indexes already exist")

            # Saved queries collection indexes
            saved_queries = cls.database.saved_queries
            try:
                await saved_queries.create_index("query_id", unique=True)
                await saved_queries.create_index("user_id")
                await saved_queries.create_index([("user_id", 1), ("created_at", -1)])
            except (DuplicateKeyError, OperationFailure):
                logger.warning("⚠ saved_queries indexes already exist")

            # Scheduled reports collection indexes
            scheduled_reports = cls.database.scheduled_reports
            try:
                await scheduled_reports.create_index("schedule_id", unique=True)
                await scheduled_reports.create_index("user_id")
                await scheduled_reports.create_index([("is_active", 1), ("next_run", 1)])
            except (DuplicateKeyError, OperationFailure):
                logger.warning("⚠ scheduled_reports indexes already exist")

            # Export jobs collection indexes
            export_jobs = cls.database.export_jobs
            try:
                await export_jobs.create_index("job_id", unique=True)
                await export_jobs.create_index("user_id")
                await export_jobs.create_index([("user_id", 1), ("created_at", -1)])
                await export_jobs.create_index("expires_at", expireAfterSeconds=0)  # TTL index
            except (DuplicateKeyError, OperationFailure):
                logger.warning("⚠ export_jobs indexes already exist")

            # Analyst API keys collection indexes
            analyst_api_keys = cls.database.analyst_api_keys
            try:
                await analyst_api_keys.create_index("key_id", unique=True)
                await analyst_api_keys.create_index("user_id")
                await analyst_api_keys.create_index("key_hash", unique=True)
            except (DuplicateKeyError, OperationFailure):
                logger.warning("⚠ analyst_api_keys indexes already exist")

            # ============================================================
            # ADMIN MODULE INDEXES
            # ============================================================

            # System settings collection indexes
            system_settings = cls.database.system_settings
            try:
                await system_settings.create_index("setting_id", unique=True)
                await system_settings.create_index([("category", 1), ("key", 1)], unique=True)
                await system_settings.create_index("key", unique=True)
            except (DuplicateKeyError, OperationFailure):
                logger.warning("⚠ system_settings indexes already exist")

            # Admin activity logs collection indexes
            admin_activity_logs = cls.database.admin_activity_logs
            try:
                await admin_activity_logs.create_index("log_id", unique=True)
                await admin_activity_logs.create_index("admin_id")
                await admin_activity_logs.create_index("action")
                await admin_activity_logs.create_index([("admin_id", 1), ("timestamp", -1)])
                await admin_activity_logs.create_index([("action", 1), ("timestamp", -1)])
                await admin_activity_logs.create_index([("target_type", 1), ("target_id", 1)])
                await admin_activity_logs.create_index([("timestamp", -1)])
            except (DuplicateKeyError, OperationFailure):
                logger.warning("⚠ admin_activity_logs indexes already exist")

            # Error logs collection indexes
            error_logs = cls.database.error_logs
            try:
                await error_logs.create_index("error_id", unique=True)
                await error_logs.create_index("level")
                await error_logs.create_index("resolved")
                await error_logs.create_index([("timestamp", -1)])
                await error_logs.create_index([("level", 1), ("timestamp", -1)])
            except (DuplicateKeyError, OperationFailure):
                logger.warning("⚠ error_logs indexes already exist")

            # API request logs collection indexes (for monitoring)
            api_request_logs = cls.database.api_request_logs
            try:
                await api_request_logs.create_index("request_id", unique=True)
                await api_request_logs.create_index("endpoint")
                await api_request_logs.create_index("user_id")
                await api_request_logs.create_index([("timestamp", -1)])
                await api_request_logs.create_index([("endpoint", 1), ("timestamp", -1)])
                await api_request_logs.create_index([("status_code", 1), ("timestamp", -1)])
            except (DuplicateKeyError, OperationFailure):
                logger.warning("⚠ api_request_logs indexes already exist")

            # ============================================================
            # COMMUNITY RESPONSE MODULE INDEXES
            # ============================================================

            # Organizer applications collection indexes
            organizer_applications = cls.database.organizer_applications
            try:
                await organizer_applications.create_index("application_id", unique=True)
                await organizer_applications.create_index("user_id", unique=True)
                await organizer_applications.create_index("status")
                await organizer_applications.create_index([("status", 1), ("applied_at", -1)])
                await organizer_applications.create_index("state")
                await organizer_applications.create_index("coastal_zone")
            except (DuplicateKeyError, OperationFailure):
                logger.warning("⚠ organizer_applications indexes already exist")

            # Communities collection indexes
            communities = cls.database.communities
            try:
                await communities.create_index("community_id", unique=True)
                await communities.create_index("organizer_id")
                await communities.create_index("coastal_zone")
                await communities.create_index("state")
                await communities.create_index("category")
                await communities.create_index("member_ids")
                await communities.create_index([("is_active", 1), ("member_count", -1)])
                await communities.create_index([("created_at", -1)])
            except (DuplicateKeyError, OperationFailure):
                logger.warning("⚠ communities indexes already exist")

            # Events collection indexes
            events = cls.database.events
            try:
                await events.create_index("event_id", unique=True)
                await events.create_index("community_id")
                await events.create_index("organizer_id")
                await events.create_index("coastal_zone")
                await events.create_index("status")
                await events.create_index([("event_date", 1), ("status", 1)])
                await events.create_index([("status", 1), ("event_date", 1)])
                await events.create_index("related_hazard_id")
                await events.create_index("related_alert_id")
                await events.create_index([("is_emergency", 1), ("event_date", 1)])
            except (DuplicateKeyError, OperationFailure):
                logger.warning("⚠ events indexes already exist")

            # Event registrations collection indexes
            event_registrations = cls.database.event_registrations
            try:
                await event_registrations.create_index("registration_id", unique=True)
                await event_registrations.create_index([("event_id", 1), ("user_id", 1)], unique=True)
                await event_registrations.create_index("user_id")
                await event_registrations.create_index("event_id")
                await event_registrations.create_index([("user_id", 1), ("registered_at", -1)])
                await event_registrations.create_index("registration_status")
            except (DuplicateKeyError, OperationFailure):
                logger.warning("⚠ event_registrations indexes already exist")

            # Organizer notifications collection indexes
            organizer_notifications = cls.database.organizer_notifications
            try:
                await organizer_notifications.create_index("notification_id", unique=True)
                await organizer_notifications.create_index([("organizer_id", 1), ("is_read", 1)])
                await organizer_notifications.create_index([("organizer_id", 1), ("created_at", -1)])
                await organizer_notifications.create_index("expires_at", expireAfterSeconds=0)  # TTL index
            except (DuplicateKeyError, OperationFailure):
                logger.warning("⚠ organizer_notifications indexes already exist")

            # User points collection indexes
            user_points = cls.database.user_points
            try:
                await user_points.create_index("user_id", unique=True)
                await user_points.create_index([("total_points", -1)])  # For leaderboard
                await user_points.create_index([("events_attended", -1)])
            except (DuplicateKeyError, OperationFailure):
                logger.warning("⚠ user_points indexes already exist")

            logger.info("✓ Database indexes created successfully")

        except Exception as e:
            logger.error(f"✗ Failed to create indexes: {e}")
            # Don't raise - allow app to continue even if indexes fail
            logger.warning("⚠ Continuing without some indexes - app functionality may be limited")

    @classmethod
    def get_database(cls) -> AsyncIOMotorDatabase:
        """Get database instance"""
        if cls.database is None:
            raise RuntimeError("Database not connected. Call connect() first.")
        return cls.database


class RedisCache:
    """Redis async connection handler"""

    client: Optional[Redis] = None

    @classmethod
    async def connect(cls):
        """Establish Redis connection"""
        try:
            cls.client = await aioredis.from_url(
                settings.redis_url,
                encoding="utf-8",
                decode_responses=True,
                max_connections=50,
            )

            # Test connection
            await cls.client.ping()
            logger.info(f"✓ Connected to Redis: {settings.REDIS_HOST}:{settings.REDIS_PORT}")

        except Exception as e:
            logger.error(f"✗ Failed to connect to Redis: {e}")
            raise

    @classmethod
    async def disconnect(cls):
        """Close Redis connection"""
        if cls.client:
            await cls.client.close()
            logger.info("✓ Disconnected from Redis")

    @classmethod
    def get_client(cls) -> Redis:
        """Get Redis client instance"""
        if cls.client is None:
            raise RuntimeError("Redis not connected. Call connect() first.")
        return cls.client


# Convenience functions
async def get_database() -> AsyncIOMotorDatabase:
    """Dependency injection for database"""
    return MongoDB.get_database()


async def get_redis() -> Optional[Redis]:
    """
    Dependency injection for Redis (optional)
    Returns None if Redis is not connected
    """
    try:
        return RedisCache.get_client()
    except RuntimeError:
        # Redis not connected - return None for graceful degradation
        logger.debug("Redis not available - returning None")
        return None
