"""
Simple database check using synchronous pymongo
This should work even with dependency issues
"""

from pymongo import MongoClient
from datetime import datetime

def check_database():
    print("="*60)
    print("DATABASE CHECK - NOTIFICATION SYSTEM")
    print("="*60)
    print()

    try:
        # Connect to MongoDB (synchronous)
        client = MongoClient("mongodb://localhost:27017/")
        db = client.coastguardian
        print("✓ Connected to MongoDB\n")

        # 1. Check alerts
        alerts = list(db.alerts.find({}).sort("created_at", -1).limit(5))
        print(f"1. ALERTS: Found {db.alerts.count_documents({})} total")
        if alerts:
            recent = alerts[0]
            print(f"   Most recent: {recent.get('title')}")
            print(f"   Regions: {recent.get('regions')}")
            print(f"   Notifications sent: {recent.get('notifications_sent', 0)}")
        print()

        # 2. Check users
        total_users = db.users.count_documents({})
        citizens = list(db.users.find({"role": "citizen"}).limit(10))
        print(f"2. USERS: Found {total_users} total, {len(citizens)} citizens")

        if citizens:
            with_region = 0
            without_region = 0
            regions_found = set()

            for citizen in citizens:
                location = citizen.get('location', {})
                region = location.get('region') or location.get('state')

                if region:
                    with_region += 1
                    regions_found.add(region)
                    print(f"   ✓ {citizen.get('name')}: {region}")
                else:
                    without_region += 1
                    print(f"   ✗ {citizen.get('name')}: NO REGION")

            print(f"\n   Citizens WITH region: {with_region}")
            print(f"   Citizens WITHOUT region: {without_region}")
            print(f"   User regions: {sorted(regions_found)}")
        print()

        # 3. Check notifications
        notifications = list(db.notifications.find({}).sort("created_at", -1).limit(5))
        print(f"3. NOTIFICATIONS: Found {db.notifications.count_documents({})}")

        if notifications:
            for notif in notifications[:3]:
                print(f"   - {notif.get('title')} (User: {notif.get('user_id')})")
        else:
            print("   ✗ NO NOTIFICATIONS IN DATABASE!")
            print("   This means the notification creation code is NOT working")
        print()

        # 4. Check region matching
        if alerts and citizens:
            alert_regions = set()
            for alert in alerts:
                alert_regions.update(alert.get('regions', []))

            user_regions = set()
            for citizen in citizens:
                location = citizen.get('location', {})
                region = location.get('region') or location.get('state')
                if region:
                    user_regions.add(region)

            print("4. REGION MATCHING:")
            print(f"   Alert regions: {sorted(alert_regions)}")
            print(f"   User regions: {sorted(user_regions)}")

            matching = alert_regions.intersection(user_regions)
            if matching:
                print(f"   ✓ MATCHING: {sorted(matching)}")
            else:
                print(f"   ✗ NO MATCH - This is the problem!")

        print()
        print("="*60)
        print("DIAGNOSIS:")
        print("="*60)

        if db.notifications.count_documents({}) == 0:
            if without_region == len(citizens):
                print("❌ USERS HAVE NO LOCATION DATA")
                print("   Fix: Update user profiles with region")
            elif not matching:
                print("❌ REGION MISMATCH")
                print("   Alert regions don't match user regions")
            else:
                print("❌ NOTIFICATION CODE NOT EXECUTING")
                print("   Backend notification hook is failing")
        else:
            print("✓ Notifications exist in database")
            print("  Check frontend API calls")

        client.close()

    except Exception as e:
        print(f"ERROR: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    check_database()
