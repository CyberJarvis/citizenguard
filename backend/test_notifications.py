"""
Test script to verify notification system is working
Run this to check if notifications are being created
"""

import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime, timezone

async def test_notifications():
    try:
        # Connect to MongoDB
        client = AsyncIOMotorClient("mongodb://localhost:27017/")
        db = client.coastguardian

        print("✓ Connected to MongoDB\n")

        # Check if there are any users
        users_count = await db.users.count_documents({})
        print(f"Total users in database: {users_count}")

        # Check citizen users
        citizens = await db.users.find({"role": "citizen"}).to_list(length=10)
        print(f"Citizens found: {len(citizens)}\n")

        if citizens:
            print("Sample citizen data:")
            for citizen in citizens[:3]:
                print(f"  - {citizen.get('name')} ({citizen.get('user_id')})")
                print(f"    Email: {citizen.get('email')}")
                print(f"    Location: {citizen.get('location', {})}")
                print()

        # Check if there are any alerts
        alerts_count = await db.alerts.count_documents({})
        print(f"Total alerts in database: {alerts_count}")

        alerts = await db.alerts.find({}).sort("created_at", -1).to_list(length=5)
        if alerts:
            print("\nRecent alerts:")
            for alert in alerts:
                print(f"  - {alert.get('title')} (ID: {alert.get('alert_id')})")
                print(f"    Severity: {alert.get('severity')}")
                print(f"    Regions: {alert.get('regions')}")
                print(f"    Notifications sent: {alert.get('notifications_sent', 0)}")
                print()

        # Check if there are any notifications
        notifications_count = await db.notifications.count_documents({})
        print(f"Total notifications in database: {notifications_count}")

        notifications = await db.notifications.find({}).sort("created_at", -1).to_list(length=10)
        if notifications:
            print("\nRecent notifications:")
            for notif in notifications:
                print(f"  - {notif.get('title')}")
                print(f"    User ID: {notif.get('user_id')}")
                print(f"    Type: {notif.get('type')}")
                print(f"    Severity: {notif.get('severity')}")
                print(f"    Is Read: {notif.get('is_read')}")
                print(f"    Created: {notif.get('created_at')}")
                print()
        else:
            print("\n⚠️  No notifications found in database!")
            print("This means notifications are not being created when alerts are made.\n")

        # Close connection
        client.close()

    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_notifications())
