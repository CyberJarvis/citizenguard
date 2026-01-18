"""
MongoDB Database Cleanup Script
Removes documents with null user_id values
"""

import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from app.config import settings


async def cleanup_database():
    """Clean up invalid documents from MongoDB"""
    
    print("🔧 Connecting to MongoDB...")
    client = AsyncIOMotorClient(settings.MONGODB_URL)
    database = client[settings.MONGODB_DB_NAME]
    
    try:
        # Test connection
        await client.admin.command("ping")
        print(f"✓ Connected to MongoDB: {settings.MONGODB_DB_NAME}")
        
        # Find documents with null user_id
        users_collection = database.users
        null_count = await users_collection.count_documents({"user_id": None})
        
        print(f"\n📊 Found {null_count} documents with null user_id")
        
        if null_count > 0:
            print("\n⚠️  These documents will be DELETED:")
            async for doc in users_collection.find({"user_id": None}):
                print(f"  - Document ID: {doc.get('_id')}")
            
            response = input("\n❓ Do you want to delete these documents? (yes/no): ")
            
            if response.lower() == "yes":
                result = await users_collection.delete_many({"user_id": None})
                print(f"✓ Deleted {result.deleted_count} documents")
                print("\n✅ Database cleanup completed!")
            else:
                print("❌ Cleanup cancelled")
        else:
            print("✓ No cleanup needed - all documents are valid")
        
        # Try to drop the problematic index
        print("\n🔧 Checking indexes...")
        try:
            await users_collection.drop_index("user_id_1")
            print("✓ Dropped user_id index - will be recreated on next app startup")
        except Exception as e:
            print(f"ℹ️  Index doesn't exist or already dropped: {e}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        client.close()
        print("\n✓ Disconnected from MongoDB")


if __name__ == "__main__":
    print("=" * 60)
    print("MongoDB Database Cleanup Script")
    print("=" * 60)
    asyncio.run(cleanup_database())
