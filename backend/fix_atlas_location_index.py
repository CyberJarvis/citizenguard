"""
Fix Location Index on MongoDB Atlas

This script connects to your MongoDB Atlas database and removes
the geospatial index that's preventing location updates.

It reads credentials from your .env file automatically.
"""

import logging
import os
from pymongo import MongoClient
from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

def run_migration():
    """Run the location index migration on MongoDB Atlas"""
    logger.info("=" * 70)
    logger.info("MONGODB ATLAS - LOCATION INDEX MIGRATION")
    logger.info("=" * 70)
    logger.info("")

    # Get MongoDB connection from environment
    mongodb_url = os.getenv("MONGODB_URL")
    db_name = os.getenv("MONGODB_DB_NAME", "CoastGuardian")

    if not mongodb_url:
        logger.error("ERROR: MONGODB_URL not found in .env file")
        return

    logger.info(f"Database: {db_name}")
    logger.info(f"Connecting to MongoDB Atlas...")

    try:
        # Connect to MongoDB Atlas
        client = MongoClient(mongodb_url)
        db = client[db_name]

        # Test connection
        client.server_info()
        logger.info("✓ Connected successfully")
        logger.info("")

        # Get current indexes on users collection
        logger.info("Checking indexes on 'users' collection...")
        indexes = list(db.users.list_indexes())

        logger.info(f"Found {len(indexes)} total indexes:")
        for idx in indexes:
            logger.info(f"  - {idx['name']}")
            logger.info(f"    Fields: {idx.get('key', {})}")
        logger.info("")

        # Find location-related geospatial indexes
        location_geo_indexes = []
        for idx in indexes:
            index_key = idx.get('key', {})
            index_name = idx['name']

            # Check if this is a geospatial index on location field or subfields
            is_location_geo = False
            for field_name, field_type in index_key.items():
                if field_type == '2dsphere' and 'location' in field_name:
                    is_location_geo = True
                    break

            if is_location_geo:
                location_geo_indexes.append(index_name)
                logger.info(f"  >> Found geospatial index: {index_name}")
                logger.info(f"     This is blocking location updates!")

        # Drop geospatial indexes on location
        if location_geo_indexes:
            logger.info("")
            logger.info("Dropping geospatial indexes...")
            logger.info("")

            for index_name in location_geo_indexes:
                try:
                    db.users.drop_index(index_name)
                    logger.info(f"  ✓ Dropped: {index_name}")
                except Exception as e:
                    logger.error(f"  ✗ Failed to drop {index_name}: {e}")

            logger.info("")
            logger.info("=" * 70)
            logger.info("MIGRATION COMPLETED SUCCESSFULLY!")
            logger.info("=" * 70)
            logger.info("")
            logger.info("RESULT:")
            logger.info("  ✓ Geospatial indexes removed from location field")
            logger.info("  ✓ You can now store state/region/city data in location")
            logger.info("")
            logger.info("NEXT STEPS:")
            logger.info("  1. Try updating your profile with location data")
            logger.info("  2. The 'unknown GeoJSON type' error should be resolved")
            logger.info("  3. Notifications will work once users have location data")
            logger.info("")

        else:
            logger.info("")
            logger.info("=" * 70)
            logger.info("NO GEOSPATIAL INDEXES FOUND")
            logger.info("=" * 70)
            logger.info("")
            logger.info("  ✓ No geospatial indexes on location field")
            logger.info("  ✓ Migration already applied or not needed")
            logger.info("")
            logger.info("If you're still getting errors, please:")
            logger.info("  1. Restart your backend server")
            logger.info("  2. Clear browser cache")
            logger.info("  3. Try the profile update again")
            logger.info("")

        # Verify final state
        logger.info("")
        logger.info("Final indexes on 'users' collection:")
        final_indexes = list(db.users.list_indexes())
        for idx in final_indexes:
            logger.info(f"  - {idx['name']}: {idx.get('key', {})}")

        logger.info("")
        logger.info("=" * 70)

        client.close()

    except Exception as e:
        logger.error("")
        logger.error("=" * 70)
        logger.error("ERROR")
        logger.error("=" * 70)
        logger.error(f"Migration failed: {e}")
        logger.error("")
        import traceback
        traceback.print_exc()
        logger.error("")
        logger.error("Please check:")
        logger.error("  1. MONGODB_URL in .env file is correct")
        logger.error("  2. Internet connection is working (MongoDB Atlas is cloud-based)")
        logger.error("  3. MongoDB Atlas credentials are valid")
        logger.error("  4. You have permissions to modify indexes")
        logger.error("")


if __name__ == "__main__":
    run_migration()
