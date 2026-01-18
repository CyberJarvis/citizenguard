"""Find the correct database with users collection"""
from pymongo import MongoClient

client = MongoClient("mongodb://localhost:27017/")

print("=" * 60)
print("FINDING USERS COLLECTION")
print("=" * 60)
print()

# Check blueradar database
for db_name in ["blueradar", "ocean_hazard"]:
    if db_name in client.list_database_names():
        db = client[db_name]
        print(f"Database: {db_name}")
        print(f"Collections: {db.list_collection_names()}")

        if "users" in db.list_collection_names():
            users_count = db.users.count_documents({})
            print(f"  - users collection found: {users_count} documents")

            print(f"  - Indexes on users collection:")
            for idx in db.users.list_indexes():
                print(f"    * {idx['name']}: {idx.get('key', {})}")
                if 'location' in idx.get('key', {}):
                    print(f"      >> LOCATION INDEX: {idx.get('key', {}).get('location')}")
        print()

client.close()
