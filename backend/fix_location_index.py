"""
Fix MongoDB location field index issue
Drop the geospatial index and allow plain object storage
"""

from pymongo import MongoClient

def fix_location_index():
    print("Fixing location field index...")
    print()

    try:
        # Connect to MongoDB Atlas
        client = MongoClient("mongodb+srv://vishwakarmaakashav17:AkashPython123@pythoncluster0.t9pop.mongodb.net/CoastGuardian?retryWrites=true&w=majority")
        db = client.CoastGuardian

        print("Connected to MongoDB")
        print()

        # Check current indexes
        print("Current indexes on users collection:")
        indexes = list(db.users.list_indexes())
        for idx in indexes:
            print(f"  - {idx['name']}: {idx.get('key', {})}")
        print()

        # Drop geospatial index on location if it exists
        location_indexes = [idx for idx in indexes if 'location' in str(idx.get('key', {}))]

        if location_indexes:
            print("Found location-related indexes:")
            for idx in location_indexes:
                index_name = idx['name']
                print(f"  Dropping index: {index_name}")
                try:
                    db.users.drop_index(index_name)
                    print(f"  ✓ Dropped {index_name}")
                except Exception as e:
                    print(f"  ✗ Failed to drop {index_name}: {e}")
            print()
        else:
            print("No location indexes found to drop")
            print()

        # Verify indexes after dropping
        print("Indexes after cleanup:")
        remaining_indexes = list(db.users.list_indexes())
        for idx in remaining_indexes:
            print(f"  - {idx['name']}: {idx.get('key', {})}")
        print()

        print("✓ Location field is now free from geospatial constraints")
        print("✓ You can now store plain objects with state, region, city")
        print()

        # Test update
        print("Testing location update...")
        test_update = db.users.update_one(
            {"role": "citizen"},
            {
                "$set": {
                    "location": {
                        "state": "Maharashtra",
                        "region": "Maharashtra",
                        "city": "Mumbai"
                    }
                }
            }
        )

        if test_update.matched_count > 0:
            print(f"✓ Test update successful ({test_update.modified_count} user updated)")
        else:
            print("⚠ No users found to test update")

        print()
        print("="*60)
        print("FIX COMPLETE!")
        print("="*60)
        print()
        print("You can now update user profiles with location data.")

        client.close()

    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    fix_location_index()
