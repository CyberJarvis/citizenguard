"""
Location Index Migration

Fixes the MongoDB geospatial index issue on the location field.
Previously, the location field had a 2dsphere geospatial index expecting GeoJSON format.
This migration removes that index to allow storing plain objects with state/region/city.

This migration is safe to run multiple times (idempotent).
"""

import logging
from motor.motor_asyncio import AsyncIOMotorDatabase

logger = logging.getLogger(__name__)


async def fix_location_index(db: AsyncIOMotorDatabase) -> None:
    """
    Fix location field index issue

    Removes any geospatial indexes on the location field that would
    prevent storing plain objects with state, region, and city data.

    Args:
        db: AsyncIOMotorDatabase instance
    """
    try:
        logger.info("Running location index migration...")

        # Get current indexes on users collection
        indexes = await db.users.list_indexes().to_list(length=None)

        # Find location-related geospatial indexes
        location_geo_indexes = []
        for idx in indexes:
            index_key = idx.get('key', {})
            index_name = idx['name']

            # Check if this is a geospatial index on location field or location.coordinates
            # Look for: 'location' or 'location.coordinates' with '2dsphere' type
            is_location_geo = False

            for field_name, field_type in index_key.items():
                if field_type == '2dsphere' and ('location' in field_name):
                    is_location_geo = True
                    break

            if is_location_geo:
                location_geo_indexes.append(index_name)
                logger.info(f"  Found geospatial index: {index_name} -> {index_key}")

        # Drop geospatial indexes on location
        if location_geo_indexes:
            for index_name in location_geo_indexes:
                try:
                    await db.users.drop_index(index_name)
                    logger.info(f"  ✓ Dropped geospatial index: {index_name}")
                except Exception as e:
                    logger.warning(f"  Failed to drop index {index_name}: {e}")

            logger.info("✓ Location index migration completed successfully")
            logger.info("  Location field can now store state/region/city objects")
        else:
            logger.info("  No geospatial indexes found on location field (already migrated)")

    except Exception as e:
        logger.error(f"Error during location index migration: {e}")
        # Don't raise - we want the app to start even if migration fails
        logger.warning("  Application will continue, but profile updates may fail")
