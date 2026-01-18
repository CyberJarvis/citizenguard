"""
Check existing users and their password hash format
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
    
    # Find demo users
    demo_emails = [
        "citizen@coastguardian.com",
        "authority@coastguardian.com",
        "analyst@coastguardian.com",
        "admin@coastguardian.com",
        "organizer@coastguardian.com"
    ]
    
    for email in demo_emails:
        user = users.find_one({"email": email})
        if user:
            print(f"Email: {email}")
            print(f"  user_id: {user.get('user_id', 'N/A')}")
            print(f"  role: {user.get('role', 'N/A')}")
            print(f"  is_active: {user.get('is_active', 'N/A')}")
            print(f"  is_verified: {user.get('is_verified', 'N/A')}")
            print(f"  email_verified: {user.get('email_verified', 'N/A')}")
            
            # Check password field
            pwd_hash = user.get('password_hash') or user.get('hashed_password')
            if pwd_hash:
                print(f"  password_hash: {pwd_hash[:50]}...")
            else:
                print(f"  password_hash: NOT SET!")
                print(f"  Available fields: {list(user.keys())}")
            print()
        else:
            print(f"Email: {email} - NOT FOUND\n")
    
    client.close()

if __name__ == "__main__":
    main()
