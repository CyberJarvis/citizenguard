"""
Standalone Location Index Migration Script

Run this script to fix the MongoDB geospatial index issue immediately.
This uses synchronous pymongo to avoid dependency issues.

Usage: python run_location_migration.py
"""

import logging
from pymongo import MongoClient

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def run_migration():
    """Run the location index migration"""
    logger.info("=" * 60)
    logger.info("LOCATION INDEX MIGRATION")
    logger.info("=" * 60)
    logger.info("")

    try:
        # Connect to MongoDB
        logger.info("Connecting to MongoDB...")
        client = MongoClient("mongodb://localhost:27017/")
        db = client.coastguardian
        logger.info("✓ Connected to MongoDB")
        logger.info("")

        # Get current indexes on users collection
        logger.info("Checking indexes on users collection...")
        indexes = list(db.users.list_indexes())

        logger.info(f"Found {len(indexes)} total indexes:")
        for idx in indexes:
            logger.info(f"  - {idx['name']}: {idx.get('key', {})}")
        logger.info("")

        # Find location-related geospatial indexes
        location_geo_indexes = []
        for idx in indexes:
            index_key = idx.get('key', {})
            # Check if this is a geospatial index on location field
            if 'location' in index_key:
                index_type = index_key.get('location')
                # 2dsphere indexes have value '2dsphere'
                if index_type == '2dsphere':
                    location_geo_indexes.append(idx['name'])
                    logger.info(f"  Found geospatial index on location: {idx['name']}")

        # Drop geospatial indexes on location
        if location_geo_indexes:
            logger.info("")
            logger.info("Dropping geospatial indexes...")
            for index_name in location_geo_indexes:
                try:
                    db.users.drop_index(index_name)
                    logger.info(f"  ✓ Dropped: {index_name}")
                except Exception as e:
                    logger.error(f"  ✗ Failed to drop {index_name}: {e}")

            logger.info("")
            logger.info("✓ Migration completed successfully!")
            logger.info("")
            logger.info("RESULT:")
            logger.info("  The location field can now store plain objects")
            logger.info("  with state, region, and city data.")
            logger.info("")
            logger.info("You can now update user profiles with location data!")
        else:
            logger.info("")
            logger.info("✓ No geospatial indexes found on location field")
            logger.info("  Migration already applied or not needed")
            logger.info("")

        # Verify final state
        logger.info("")
        logger.info("Final indexes on users collection:")
        final_indexes = list(db.users.list_indexes())
        for idx in final_indexes:
            logger.info(f"  - {idx['name']}: {idx.get('key', {})}")

        logger.info("")
        logger.info("=" * 60)
        logger.info("MIGRATION COMPLETE")
        logger.info("=" * 60)
        logger.info("")
        logger.info("Next steps:")
        logger.info("  1. Try updating your profile with location data")
        logger.info("  2. The error should be resolved")
        logger.info("  3. Future backend restarts will auto-apply this migration")
        logger.info("")

        client.close()

    except Exception as e:
        logger.error("")
        logger.error("=" * 60)
        logger.error("ERROR")
        logger.error("=" * 60)
        logger.error(f"Migration failed: {e}")
        logger.error("")
        import traceback
        traceback.print_exc()
        logger.error("")
        logger.error("Please ensure:")
        logger.error("  1. MongoDB is running (mongodb://localhost:27017/)")
        logger.error("  2. Database name is 'coastguardian'")
        logger.error("  3. You have permissions to modify indexes")
        logger.error("")


if __name__ == "__main__":
    run_migration()
