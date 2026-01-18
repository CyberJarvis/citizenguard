"""Check MongoDB databases and collections"""
from pymongo import MongoClient

client = MongoClient("mongodb://localhost:27017/")

print("=" * 60)
print("MONGODB DATABASES AND COLLECTIONS")
print("=" * 60)
print()

# List all databases
print("Available databases:")
for db_name in client.list_database_names():
    print(f"  - {db_name}")
print()

# Check coastguardian database
if "coastguardian" in client.list_database_names():
    db = client.coastguardian
    print("Collections in 'coastguardian' database:")
    for coll_name in db.list_collection_names():
        print(f"  - {coll_name}")
        count = db[coll_name].count_documents({})
        print(f"    Documents: {count}")
    print()

    # Check users collection indexes
    if "users" in db.list_collection_names():
        print("Indexes on 'users' collection:")
        for idx in db.users.list_indexes():
            print(f"  - {idx['name']}: {idx.get('key', {})}")
            if 'location' in idx.get('key', {}):
                print(f"    ** LOCATION INDEX FOUND **")
                print(f"    Type: {idx.get('key', {}).get('location')}")
    else:
        print("⚠ 'users' collection does not exist")
else:
    print("⚠ 'coastguardian' database does not exist")

print()
print("=" * 60)

client.close()
