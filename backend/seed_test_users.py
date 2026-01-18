"""
Seed Test Users Script
Creates test users for each role (Citizen, Authority, Analyst, Admin)
Run: python seed_test_users.py
"""

import asyncio
from datetime import datetime, timezone
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
import os
import sys

# Load environment variables from .env
load_dotenv()

# Add the backend directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.utils.password import hash_password
from app.models.rbac import UserRole

# MongoDB connection from .env
MONGODB_URL = os.getenv("MONGODB_URL")
DATABASE_NAME = os.getenv("MONGODB_DB_NAME", "CoastGuardian")

# Test users configuration (matching frontend login page)
TEST_USERS = [
    {
        "user_id": "USR-TEST-CITIZEN",
        "email": "citizen@coastguardian.com",
        "password": "Citizen@123",
        "name": "Test Citizen",
        "role": UserRole.CITIZEN,
        "phone": "+919876543210",
        "credibility_score": 75,
    },
    {
        "user_id": "USR-TEST-AUTHORITY",
        "email": "authority@coastguardian.com",
        "password": "Authority@123",
        "name": "Test Authority",
        "role": UserRole.AUTHORITY,
        "phone": "+919876543211",
        "credibility_score": 90,
        "authority_organization": "INCOIS",
        "authority_designation": "Marine Safety Officer",
        "authority_jurisdiction": ["Maharashtra", "Gujarat", "Goa"],
    },
    {
        "user_id": "USR-TEST-ANALYST",
        "email": "analyst@coastguardian.com",
        "password": "Analyst@123",
        "name": "Test Analyst",
        "role": UserRole.ANALYST,
        "phone": "+919876543212",
        "credibility_score": 85,
    },
    {
        "user_id": "USR-TEST-ADMIN",
        "email": "admin@coastguardian.com",
        "password": "Admin@123",
        "name": "Test Admin",
        "role": UserRole.AUTHORITY_ADMIN,
        "phone": "+919876543213",
        "credibility_score": 100,
    },
    {
        "user_id": "USR-TEST-ORGANIZER",
        "email": "organizer@coastguardian.com",
        "password": "Organizer@123",
        "name": "Test Organizer",
        "role": UserRole.VERIFIED_ORGANIZER,
        "phone": "+919876543214",
        "credibility_score": 85,
    },
]


async def seed_users():
    """Create test users in the database"""
    print("=" * 60)
    print("CoastGuardians - Test Users Seeder")
    print("=" * 60)

    if not MONGODB_URL:
        print("\nERROR: MONGODB_URL not found in .env file!")
        return

    # Connect to MongoDB
    print(f"\nConnecting to MongoDB Atlas...")
    print(f"Database: {DATABASE_NAME}")

    client = AsyncIOMotorClient(MONGODB_URL)
    db = client[DATABASE_NAME]
    users_collection = db["users"]

    created_count = 0
    updated_count = 0

    print("\nProcessing users...")
    print("-" * 60)

    for user_data in TEST_USERS:
        email = user_data["email"]
        password = user_data.pop("password")
        role_value = user_data["role"].value

        # Check if user already exists
        existing_user = await users_collection.find_one({"email": email})

        # Prepare user document
        user_doc = {
            **user_data,
            "role": role_value,
            "hashed_password": hash_password(password),
            "auth_provider": "local",
            "email_verified": True,
            "phone_verified": True,
            "is_active": True,
            "is_banned": False,
            "total_reports": 0,
            "verified_reports": 0,
            "notification_preferences": {
                "alerts_enabled": True,
                "channels": ["push", "email"],
                "email_notifications": True,
                "sms_notifications": True
            },
            "updated_at": datetime.now(timezone.utc),
        }

        if existing_user:
            await users_collection.update_one(
                {"email": email},
                {"$set": user_doc}
            )
            print(f"  [UPDATED] {role_value.upper():10} | {email}")
            updated_count += 1
        else:
            user_doc["created_at"] = datetime.now(timezone.utc)
            await users_collection.insert_one(user_doc)
            print(f"  [CREATED] {role_value.upper():10} | {email}")
            created_count += 1

    client.close()

    print("-" * 60)
    print(f"\nSummary: {created_count} created, {updated_count} updated")

    # Print credentials table
    print("\n" + "=" * 60)
    print("TEST CREDENTIALS (use on login page)")
    print("=" * 60)
    print(f"{'Role':<12} | {'Email':<32} | {'Password':<15}")
    print("-" * 60)

    creds = [
        ("CITIZEN", "citizen@coastguardian.com", "Citizen@123"),
        ("AUTHORITY", "authority@coastguardian.com", "Authority@123"),
        ("ANALYST", "analyst@coastguardian.com", "Analyst@123"),
        ("ADMIN", "admin@coastguardian.com", "Admin@123"),
        ("ORGANIZER", "organizer@coastguardian.com", "Organizer@123"),
    ]
    for role, email, pwd in creds:
        print(f"{role:<12} | {email:<32} | {pwd:<15}")

    print("=" * 60)
    print("\nDone! You can now use the Quick Login dropdown on the login page.")


if __name__ == "__main__":
    asyncio.run(seed_users())
