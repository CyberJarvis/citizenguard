"""
Diagnostic script to find why notifications aren't being created
Run this to see exactly what's happening
"""

import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime

async def diagnose():
    print("="*60)
    print("NOTIFICATION SYSTEM DIAGNOSTIC")
    print("="*60)
    print()

    try:
        # Connect to MongoDB
        client = AsyncIOMotorClient("mongodb://localhost:27017/")
        db = client.coastguardian
        print("✓ Connected to MongoDB")
        print()

        # 1. Check Alerts
        print("="*60)
        print("1. CHECKING ALERTS")
        print("="*60)

        alerts = await db.alerts.find({}).sort("created_at", -1).to_list(length=10)
        print(f"Total alerts in database: {len(alerts)}")
        print()

        if alerts:
            print("Recent alerts:")
            for i, alert in enumerate(alerts[:5], 1):
                print(f"\n  Alert {i}:")
                print(f"  - ID: {alert.get('alert_id')}")
                print(f"  - Title: {alert.get('title')}")
                print(f"  - Severity: {alert.get('severity')}")
                print(f"  - Regions: {alert.get('regions')}")
                print(f"  - Status: {alert.get('status')}")
                print(f"  - Notifications sent: {alert.get('notifications_sent', 0)}")
                print(f"  - Created: {alert.get('created_at')}")
        else:
            print("⚠️  No alerts found!")

        print()

        # 2. Check Users
        print("="*60)
        print("2. CHECKING USERS")
        print("="*60)

        total_users = await db.users.count_documents({})
        citizens = await db.users.find({"role": "citizen"}).to_list(length=100)
        active_citizens = [u for u in citizens if u.get('is_active', True) and not u.get('is_banned', False)]

        print(f"Total users: {total_users}")
        print(f"Total citizens: {len(citizens)}")
        print(f"Active citizens: {len(active_citizens)}")
        print()

        if citizens:
            print("Citizen location data:")
            citizens_with_location = 0
            citizens_without_location = 0
            location_regions = set()

            for citizen in citizens[:10]:
                location = citizen.get('location', {})
                user_id = citizen.get('user_id', 'unknown')
                name = citizen.get('name', 'unknown')

                if location:
                    region = location.get('region') or location.get('state')
                    if region:
                        citizens_with_location += 1
                        location_regions.add(region)
                        print(f"  ✓ {name} ({user_id})")
                        print(f"    Region: {region}")
                        print(f"    Location: {location}")
                    else:
                        citizens_without_location += 1
                        print(f"  ✗ {name} ({user_id})")
                        print(f"    Location data exists but NO REGION: {location}")
                else:
                    citizens_without_location += 1
                    print(f"  ✗ {name} ({user_id})")
                    print(f"    NO location data")
                print()

            print(f"Summary:")
            print(f"  - Citizens WITH region: {citizens_with_location}")
            print(f"  - Citizens WITHOUT region: {citizens_without_location}")
            print(f"  - Unique regions: {location_regions}")
        else:
            print("⚠️  No citizen users found!")

        print()

        # 3. Check Notifications
        print("="*60)
        print("3. CHECKING NOTIFICATIONS")
        print("="*60)

        notifications = await db.notifications.find({}).sort("created_at", -1).to_list(length=10)
        print(f"Total notifications: {len(notifications)}")
        print()

        if notifications:
            print("Recent notifications:")
            for i, notif in enumerate(notifications[:5], 1):
                print(f"\n  Notification {i}:")
                print(f"  - ID: {notif.get('notification_id')}")
                print(f"  - User ID: {notif.get('user_id')}")
                print(f"  - Type: {notif.get('type')}")
                print(f"  - Severity: {notif.get('severity')}")
                print(f"  - Title: {notif.get('title')}")
                print(f"  - Alert ID: {notif.get('alert_id')}")
                print(f"  - Region: {notif.get('region')}")
                print(f"  - Is Read: {notif.get('is_read')}")
                print(f"  - Created: {notif.get('created_at')}")
        else:
            print("⚠️  NO NOTIFICATIONS FOUND!")
            print("This means notifications are NOT being created when alerts are made.")

        print()

        # 4. Region Matching Analysis
        print("="*60)
        print("4. REGION MATCHING ANALYSIS")
        print("="*60)

        if alerts and citizens:
            print("\nChecking if alert regions match user regions...")
            print()

            # Get all alert regions
            alert_regions = set()
            for alert in alerts:
                regions = alert.get('regions', [])
                alert_regions.update(regions)

            # Get all user regions
            user_regions = set()
            for citizen in citizens:
                location = citizen.get('location', {})
                region = location.get('region') or location.get('state')
                if region:
                    user_regions.add(region)

            print(f"Alert regions: {sorted(alert_regions)}")
            print(f"User regions: {sorted(user_regions)}")
            print()

            matching = alert_regions.intersection(user_regions)
            not_matching = alert_regions - user_regions

            if matching:
                print(f"✓ MATCHING regions: {sorted(matching)}")
                print(f"  These regions should trigger notifications!")
            else:
                print("✗ NO MATCHING REGIONS!")
                print("  This is why no notifications are created.")

            if not_matching:
                print(f"\n⚠️  Alerts for these regions won't create notifications: {sorted(not_matching)}")
                print("  No users are located in these regions.")

            # Check specific alert
            if alerts:
                print()
                print("Detailed check for most recent alert:")
                recent_alert = alerts[0]
                alert_regions = recent_alert.get('regions', [])
                print(f"  Alert: {recent_alert.get('title')}")
                print(f"  Alert regions: {alert_regions}")
                print()

                # Find matching users
                matching_users = []
                for citizen in active_citizens:
                    location = citizen.get('location', {})
                    user_region = location.get('region') or location.get('state')

                    if user_region in alert_regions:
                        matching_users.append({
                            'name': citizen.get('name'),
                            'user_id': citizen.get('user_id'),
                            'region': user_region
                        })

                if matching_users:
                    print(f"  ✓ Found {len(matching_users)} users who SHOULD receive notifications:")
                    for user in matching_users[:10]:
                        print(f"    - {user['name']} ({user['user_id']}) in {user['region']}")

                    # Check if notifications exist for these users
                    print()
                    print("  Checking if notifications were actually created...")
                    alert_id = recent_alert.get('alert_id')
                    alert_notifications = await db.notifications.find({
                        'alert_id': alert_id
                    }).to_list(length=100)

                    if alert_notifications:
                        print(f"  ✓ Found {len(alert_notifications)} notifications for this alert!")
                    else:
                        print(f"  ✗ NO notifications found for this alert!")
                        print(f"  This means the notification creation code is NOT executing.")
                else:
                    print(f"  ✗ NO users found in regions: {alert_regions}")
                    print(f"  This is why no notifications were created.")

        print()
        print("="*60)
        print("DIAGNOSIS COMPLETE")
        print("="*60)
        print()

        # Summary and recommendations
        print("SUMMARY & RECOMMENDATIONS:")
        print()

        if not citizens:
            print("❌ ISSUE: No citizen users in database")
            print("   FIX: Create citizen user accounts")
        elif citizens_without_location == len(citizens):
            print("❌ ISSUE: Users have NO location data")
            print("   FIX: Update user profiles with location (region/state)")
        elif not matching:
            print("❌ ISSUE: Alert regions don't match any user regions")
            print("   FIX: Either:")
            print("   1. Create alerts for regions where users are located")
            print("   2. Update user locations to match alert regions")
        elif len(notifications) == 0:
            print("❌ ISSUE: Notification creation code is NOT executing")
            print("   FIX: Check backend logs when creating alert")
            print("   The notification hook in alerts.py might be failing silently")
        else:
            print("✓ Everything looks good! Notifications should be working.")

        client.close()

    except Exception as e:
        print(f"❌ ERROR: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(diagnose())
