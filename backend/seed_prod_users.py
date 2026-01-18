"""
Quick seed script for production - uses pymongo directly
Run: python seed_prod_users.py
"""

import os
from datetime import datetime, timezone
import uuid
import hashlib
import secrets

# Simple password hashing (matching your app's hash_password)
def hash_password(password: str) -> str:
    """Simple password hash using hashlib"""
    salt = secrets.token_hex(16)
    pwdhash = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt.encode('utf-8'), 100000)
    return f"{salt}${pwdhash.hex()}"

# Actually let's use bcrypt like the app does
try:
    from passlib.context import CryptContext
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    def hash_password(password: str) -> str:
        return pwd_context.hash(password)
    print("Using bcrypt for password hashing")
except:
    print("Using simple hash (bcrypt not available)")

# MongoDB connection
MONGODB_URL = os.environ.get("MONGODB_URL", "mongodb+srv://vishwakarmaakashav17:AkashPython123@pythoncluster0.t9pop.mongodb.net/CoastGuardian?retryWrites=true&w=majority")

# Test users
TEST_USERS = [
    {
        "user_id": f"USR-{uuid.uuid4().hex[:8].upper()}",
        "email": "citizen@coastguardian.com",
        "password": "Citizen@123",
        "name": "Test Citizen",
        "role": "citizen",
        "phone": "+919876543210",
        "credibility_score": 75,
    },
    {
        "user_id": f"USR-{uuid.uuid4().hex[:8].upper()}",
        "email": "authority@coastguardian.com",
        "password": "Authority@123",
        "name": "Test Authority",
        "role": "authority",
        "phone": "+919876543211",
        "credibility_score": 90,
        "authority_organization": "INCOIS",
        "authority_designation": "Marine Safety Officer",
        "authority_jurisdiction": ["Maharashtra", "Gujarat", "Goa"],
    },
    {
        "user_id": f"USR-{uuid.uuid4().hex[:8].upper()}",
        "email": "analyst@coastguardian.com",
        "password": "Analyst@123",
        "name": "Test Analyst",
        "role": "analyst",
        "phone": "+919876543212",
        "credibility_score": 85,
    },
    {
        "user_id": f"USR-{uuid.uuid4().hex[:8].upper()}",
        "email": "admin@coastguardian.com",
        "password": "Admin@123",
        "name": "Test Admin",
        "role": "authority_admin",
        "phone": "+919876543213",
        "credibility_score": 100,
    },
    {
        "user_id": f"USR-{uuid.uuid4().hex[:8].upper()}",
        "email": "organizer@coastguardian.com",
        "password": "Organizer@123",
        "name": "Test Organizer",
        "role": "verified_organizer",
        "phone": "+919876543214",
        "credibility_score": 85,
    },
]

def main():
    # Use pymongo directly (sync)
    from pymongo import MongoClient
    
    print(f"Connecting to MongoDB...")
    client = MongoClient(MONGODB_URL, serverSelectionTimeoutMS=5000)
    
    # Test connection
    client.admin.command('ping')
    print("✓ Connected to MongoDB")
    
    db = client["CoastGuardian"]
    users_collection = db["users"]
    
    for user_data in TEST_USERS:
        email = user_data["email"]
        
        # Check if user exists
        existing = users_collection.find_one({"email": email})
        if existing:
            print(f"⚠ User {email} already exists, skipping...")
            continue
        
        # Hash password
        plain_password = user_data.pop("password")
        hashed_password = hash_password(plain_password)
        
        # Create user document
        user_doc = {
            **user_data,
            "password_hash": hashed_password,
            "is_verified": True,
            "is_active": True,
            "email_verified": True,
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
            "last_login": None,
            "profile_picture": None,
            "notification_preferences": {
                "push": True,
                "email": True,
                "sms": False,
                "radius_km": 50
            },
            "preferred_language": "en",
            "emergency_contacts": [],
            "saved_locations": [],
        }
        
        users_collection.insert_one(user_doc)
        print(f"✓ Created user: {email} (password: {plain_password})")
    
    print("\n" + "="*50)
    print("Demo users created successfully!")
    print("="*50)
    print("\nYou can now login with:")
    print("  Email: citizen@coastguardian.com")
    print("  Password: Citizen@123")
    print("\nOr any of the other test users.")
    
    client.close()

if __name__ == "__main__":
    main()
