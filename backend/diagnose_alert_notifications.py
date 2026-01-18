"""
Diagnostic script to check alert notification system
Checks: user locations, region matching, and notification creation
"""

import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime, timezone
import os
from dotenv import load_dotenv

load_dotenv()

MONGODB_URL = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
DATABASE_NAME = os.getenv("MONGODB_DB_NAME", "CoastGuardian")


async def main():
    print("=" * 80)
    print("ALERT NOTIFICATION SYSTEM DIAGNOSTICS")
    print("=" * 80)

    # Connect to MongoDB
    client = AsyncIOMotorClient(MONGODB_URL)
    db = client[DATABASE_NAME]

    print(f"\n[OK] Connected to MongoDB: {DATABASE_NAME}")

    # 1. Check users with location data
    print("\n" + "=" * 80)
    print("1. CHECKING USER LOCATION DATA")
    print("=" * 80)

    total_users = await db.users.count_documents({})
    print(f"Total users: {total_users}")

    users_with_location = await db.users.count_documents({"location": {"$ne": None}})
    print(f"Users with location data: {users_with_location}")

    users_with_region = await db.users.count_documents({"location.region": {"$exists": True, "$ne": None}})
    print(f"Users with location.region: {users_with_region}")

    users_with_state = await db.users.count_documents({"location.state": {"$exists": True, "$ne": None}})
    print(f"Users with location.state: {users_with_state}")

    # Sample user locations
    print("\n[LOCATIONS] Sample user location structures:")
    sample_users = await db.users.find(
        {"location": {"$ne": None}},
        {"user_id": 1, "name": 1, "role": 1, "location": 1}
    ).limit(3).to_list(length=3)

    for user in sample_users:
        print(f"\nUser: {user.get('name')} ({user.get('user_id')})")
        print(f"  Role: {user.get('role')}")
        print(f"  Location: {user.get('location')}")

    # 2. Check citizens specifically
    print("\n" + "=" * 80)
    print("2. CHECKING CITIZEN USERS (who should receive notifications)")
    print("=" * 80)

    total_citizens = await db.users.count_documents({"role": "citizen"})
    print(f"Total citizens: {total_citizens}")

    active_citizens = await db.users.count_documents({
        "role": "citizen",
        "is_active": True,
        "is_banned": False
    })
    print(f"Active citizens: {active_citizens}")

    citizens_with_location = await db.users.count_documents({
        "role": "citizen",
        "is_active": True,
        "is_banned": False,
        "location": {"$ne": None}
    })
    print(f"Active citizens with location: {citizens_with_location}")

    # Check by specific regions
    print("\n[STATS] Citizens by region:")
    regions = ["West Bengal", "Odisha", "Andhra Pradesh", "Tamil Nadu", "Kerala",
               "Karnataka", "Goa", "Maharashtra", "Gujarat"]

    for region in regions:
        count = await db.users.count_documents({
            "role": "citizen",
            "is_active": True,
            "is_banned": False,
            "$or": [
                {"location.region": region},
                {"location.state": region}
            ]
        })
        if count > 0:
            print(f"  {region}: {count} citizens")

    # 3. Check recent alerts
    print("\n" + "=" * 80)
    print("3. CHECKING RECENT ALERTS")
    print("=" * 80)

    total_alerts = await db.alerts.count_documents({})
    print(f"Total alerts: {total_alerts}")

    recent_alerts = await db.alerts.find().sort("created_at", -1).limit(5).to_list(length=5)

    if recent_alerts:
        print(f"\n[ALERTS] {len(recent_alerts)} most recent alerts:")
        for alert in recent_alerts:
            print(f"\n  Alert ID: {alert.get('alert_id')}")
            print(f"    Title: {alert.get('title')}")
            print(f"    Type: {alert.get('alert_type')}")
            print(f"    Severity: {alert.get('severity')}")
            print(f"    Regions: {alert.get('regions', [])}")
            print(f"    Notifications sent: {alert.get('notifications_sent', 0)}")
            print(f"    Created: {alert.get('created_at')}")
    else:
        print("  [WARNING] No alerts found")

    # 4. Check notifications created
    print("\n" + "=" * 80)
    print("4. CHECKING NOTIFICATIONS")
    print("=" * 80)

    total_notifications = await db.notifications.count_documents({})
    print(f"Total notifications: {total_notifications}")

    alert_notifications = await db.notifications.count_documents({"type": "alert"})
    print(f"Alert-type notifications: {alert_notifications}")

    recent_notifications = await db.notifications.find().sort("created_at", -1).limit(5).to_list(length=5)

    if recent_notifications:
        print(f"\n[NOTIFICATIONS] {len(recent_notifications)} most recent notifications:")
        for notif in recent_notifications:
            print(f"\n  Notification ID: {notif.get('notification_id')}")
            print(f"    User ID: {notif.get('user_id')}")
            print(f"    Type: {notif.get('type')}")
            print(f"    Severity: {notif.get('severity')}")
            title = notif.get('title', '')[:50]
            print(f"    Title: {title.encode('ascii', 'ignore').decode('ascii')}...")
            print(f"    Alert ID: {notif.get('alert_id')}")
            print(f"    Region: {notif.get('region')}")
            print(f"    Regions: {notif.get('regions', [])}")
            print(f"    Is Read: {notif.get('is_read')}")
            print(f"    Created: {notif.get('created_at')}")
    else:
        print("  [WARNING] No notifications found")

    # 5. Cross-check: Alerts vs Notifications
    if recent_alerts and alert_notifications == 0:
        print("\n" + "=" * 80)
        print("[WARNING] ISSUE DETECTED!")
        print("=" * 80)
        print("Alerts exist but no alert-type notifications were created.")
        print("This means notifications are NOT being created when alerts are published.")
        print("\nPossible causes:")
        print("  1. Users don't have location data (region/state)")
        print("  2. Region names don't match between alerts and user locations")
        print("  3. Notification creation function is failing silently")
        print("  4. Users are all banned or inactive")

    # 6. Test region matching
    if recent_alerts:
        print("\n" + "=" * 80)
        print("5. TESTING REGION MATCHING FOR LATEST ALERT")
        print("=" * 80)

        latest_alert = recent_alerts[0]
        alert_regions = latest_alert.get('regions', [])

        print(f"\nLatest Alert: {latest_alert.get('alert_id')}")
        print(f"  Regions: {alert_regions}")

        if alert_regions:
            # Try exact match
            for region in alert_regions:
                count = await db.users.count_documents({
                    "role": "citizen",
                    "is_active": True,
                    "is_banned": False,
                    "location.region": region
                })
                print(f"  Citizens with location.region = '{region}': {count}")

                count_state = await db.users.count_documents({
                    "role": "citizen",
                    "is_active": True,
                    "is_banned": False,
                    "location.state": region
                })
                print(f"  Citizens with location.state = '{region}': {count_state}")

                # Try $in query (what the code uses)
                count_or = await db.users.count_documents({
                    "role": "citizen",
                    "is_active": True,
                    "is_banned": False,
                    "$or": [
                        {"location.region": {"$in": alert_regions}},
                        {"location.state": {"$in": alert_regions}}
                    ]
                })
                print(f"  Citizens matching with $or query: {count_or}")

    print("\n" + "=" * 80)
    print("DIAGNOSIS COMPLETE")
    print("=" * 80)

    client.close()


if __name__ == "__main__":
    asyncio.run(main())
