"""
Fix password field name in MongoDB
Changes 'password_hash' to 'hashed_password' to match the User model
"""

import os
from pymongo import MongoClient

MONGODB_URL = os.environ.get("MONGODB_URL", "mongodb+srv://vishwakarmaakashav17:AkashPython123@pythoncluster0.t9pop.mongodb.net/CoastGuardian?retryWrites=true&w=majority")

def main():
    print("Connecting to MongoDB...")
    client = MongoClient(MONGODB_URL, serverSelectionTimeoutMS=5000)
    client.admin.command('ping')
    print("✓ Connected\n")
    
    db = client["CoastGuardian"]
    users = db["users"]
    
    # Find all users with 'password_hash' field (wrong name)
    users_with_wrong_field = users.find({"password_hash": {"$exists": True}})
    
    count = 0
    for user in users_with_wrong_field:
        email = user.get("email", "unknown")
        password_hash = user.get("password_hash")
        
        if password_hash:
            # Rename field from password_hash to hashed_password
            result = users.update_one(
                {"_id": user["_id"]},
                {
                    "$set": {"hashed_password": password_hash},
                    "$unset": {"password_hash": ""}
                }
            )
            if result.modified_count > 0:
                print(f"✓ Fixed user: {email}")
                count += 1
    
    print(f"\n{'='*50}")
    print(f"Fixed {count} users")
    print(f"{'='*50}")
    
    # Verify the fix
    print("\nVerifying fix...")
    demo_user = users.find_one({"email": "citizen@coastguardian.com"})
    if demo_user:
        has_old = "password_hash" in demo_user
        has_new = "hashed_password" in demo_user
        print(f"citizen@coastguardian.com:")
        print(f"  has 'password_hash': {has_old}")
        print(f"  has 'hashed_password': {has_new}")
        if has_new:
            print(f"  hashed_password value: {demo_user['hashed_password'][:40]}...")
    
    client.close()

if __name__ == "__main__":
    main()
