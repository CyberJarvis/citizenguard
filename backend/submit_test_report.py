"""
Submit a test oil spill hazard report on Mumbai coast.
"""

import asyncio
import httpx
import os
import uuid
from datetime import datetime
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

load_dotenv()

BASE_URL = "http://localhost:8000/api/v1"
MONGODB_URL = os.getenv("MONGODB_URL")

# Test user credentials
TEST_EMAIL = f"test_reporter_{uuid.uuid4().hex[:8]}@test.com"
TEST_PASSWORD = "TestPass123!"

# Mumbai coast coordinates (offshore, within 30km limit for oil spill)
MUMBAI_OFFSHORE = {
    "latitude": 18.9500,  # Offshore Mumbai
    "longitude": 72.7800,
    "address": "Arabian Sea, Mumbai Coast, Maharashtra, India"
}

# Oil spill description
DESCRIPTION = """Urgent: Potential oil spill detected near offshore oil platform approximately 15km from Mumbai coast.

Visible oil sheen spreading on water surface, approximately 500 meters in diameter. The slick appears to be emanating from an offshore drilling platform visible in the background.

Key observations:
- Dark oil sheen visible on water surface
- Strong petroleum odor detected
- No cleanup vessels observed in vicinity
- Weather conditions: Clear skies, moderate waves
- Time of observation: Late afternoon

Immediate response recommended to prevent spread towards Mumbai beaches and marine protected areas. This could impact local fishing communities and marine wildlife in the region.

Reported for testing and verification purposes."""


async def main():
    client = httpx.AsyncClient(base_url=BASE_URL, follow_redirects=True, timeout=60.0)
    mongo_client = AsyncIOMotorClient(MONGODB_URL)
    db = mongo_client["CoastGuardian"]

    try:
        # Step 1: Register user
        print("=" * 60)
        print("STEP 1: Registering test user...")
        print("=" * 60)

        register_data = {
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD,
            "confirm_password": TEST_PASSWORD,
            "first_name": "Test",
            "last_name": "Reporter",
            "phone_number": "+919876543210"
        }

        response = await client.post("/auth/signup", json=register_data)
        print(f"Registration response: {response.status_code}")

        if response.status_code not in [200, 201]:
            print(f"Registration failed: {response.text}")
            return

        # Step 2: Activate user directly in database
        print("\n" + "=" * 60)
        print("STEP 2: Activating user in database...")
        print("=" * 60)

        result = await db.users.update_one(
            {"email": TEST_EMAIL},
            {"$set": {"is_active": True, "is_verified": True, "email_verified": True}}
        )
        print(f"User activated: {result.modified_count} document(s) updated")

        # Step 3: Login
        print("\n" + "=" * 60)
        print("STEP 3: Logging in...")
        print("=" * 60)

        login_data = {
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD,
            "login_type": "password"
        }

        response = await client.post("/auth/login", json=login_data)
        print(f"Login response: {response.status_code}")

        if response.status_code != 200:
            print(f"Login failed: {response.text}")
            return

        login_result = response.json()
        access_token = login_result.get("access_token")
        print(f"Access token obtained: {access_token[:30]}...")

        # Step 4: Get the image file
        print("\n" + "=" * 60)
        print("STEP 4: Loading test image...")
        print("=" * 60)

        # The image was shared in the conversation - we need to use it
        # For now, let's use an existing image from uploads or create a test image
        image_path = "/Users/patu/Desktop/coastGuardians/backend/uploads/hazards/907103e4-5c04-4c86-8f69-e6fd4ac85d54.jpg"

        if os.path.exists(image_path):
            with open(image_path, "rb") as f:
                image_data = f.read()
            print(f"Using existing image: {image_path}")
            print(f"Image size: {len(image_data)} bytes")
        else:
            print(f"Image not found at {image_path}")
            print("Creating a synthetic test image...")
            # Create a simple PNG image
            import struct
            import zlib

            width, height = 400, 300

            def create_png(width, height):
                def png_chunk(chunk_type, data):
                    chunk_len = struct.pack('>I', len(data))
                    chunk_data = chunk_type + data
                    checksum = struct.pack('>I', zlib.crc32(chunk_data) & 0xffffffff)
                    return chunk_len + chunk_data + checksum

                signature = b'\x89PNG\r\n\x1a\n'
                ihdr_data = struct.pack('>IIBBBBB', width, height, 8, 2, 0, 0, 0)
                ihdr = png_chunk(b'IHDR', ihdr_data)

                raw_data = b''
                for y in range(height):
                    raw_data += b'\x00'
                    for x in range(width):
                        r = int(20 + (y / height) * 30)
                        g = int(40 + (y / height) * 60)
                        b = int(80 + (y / height) * 100)
                        raw_data += bytes([r, g, b])

                compressed = zlib.compress(raw_data, 9)
                idat = png_chunk(b'IDAT', compressed)
                iend = png_chunk(b'IEND', b'')

                return signature + ihdr + idat + iend

            image_data = create_png(width, height)
            print(f"Created synthetic image: {len(image_data)} bytes")

        # Step 5: Submit hazard report
        print("\n" + "=" * 60)
        print("STEP 5: Submitting hazard report...")
        print("=" * 60)

        headers = {"Authorization": f"Bearer {access_token}"}

        form_data = {
            "hazard_type": "Oil Spill",
            "category": "humanMade",
            "latitude": str(MUMBAI_OFFSHORE["latitude"]),
            "longitude": str(MUMBAI_OFFSHORE["longitude"]),
            "address": MUMBAI_OFFSHORE["address"],
            "description": DESCRIPTION
        }

        # Determine file extension and content type
        if image_path.endswith('.jpg') or image_path.endswith('.jpeg'):
            content_type = "image/jpeg"
            filename = "oil_spill_mumbai.jpg"
        else:
            content_type = "image/png"
            filename = "oil_spill_mumbai.png"

        files = {"image": (filename, image_data, content_type)}

        print(f"Form data: {form_data}")
        print(f"Image: {filename} ({content_type})")

        response = await client.post(
            "/hazards",
            data=form_data,
            files=files,
            headers=headers
        )

        print(f"\nSubmission response: {response.status_code}")

        if response.status_code in [200, 201]:
            result = response.json()
            print("\n" + "=" * 60)
            print("HAZARD REPORT SUBMITTED SUCCESSFULLY!")
            print("=" * 60)
            print(f"Report ID: {result.get('report_id')}")
            print(f"Hazard Type: {result.get('hazard_type')}")
            print(f"Location: {result.get('location')}")
            print(f"Verification Status: {result.get('verification_status')}")
            print(f"Verification Score: {result.get('verification_score')}")
            print(f"Verification ID: {result.get('verification_id')}")
            print(f"Image URL: {result.get('image_url')}")

            # Print verification details if available
            if result.get('verification_result'):
                print("\n--- Verification Result ---")
                vr = result.get('verification_result')
                print(f"Decision: {vr.get('decision')}")
                print(f"Composite Score: {vr.get('composite_score')}%")
                if vr.get('layer_results'):
                    print("\nLayer Results:")
                    for layer in vr.get('layer_results', []):
                        print(f"  - {layer.get('layer_name')}: {layer.get('status')} (score: {layer.get('score'):.2f})")
        else:
            print(f"Submission failed: {response.text}")

        # Step 6: Wait and check final status
        print("\n" + "=" * 60)
        print("STEP 6: Checking report status after 5 seconds...")
        print("=" * 60)

        await asyncio.sleep(5)

        if response.status_code in [200, 201]:
            report_id = response.json().get('report_id')
            if report_id:
                # Query database for final status
                report = await db.hazard_reports.find_one({"report_id": report_id})
                if report:
                    print(f"\nFinal Status: {report.get('verification_status')}")
                    print(f"Final Score: {report.get('verification_score')}")
                    if report.get('verification_result'):
                        print(f"Decision: {report['verification_result'].get('decision')}")

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

    finally:
        await client.aclose()
        mongo_client.close()

        # Cleanup: Remove test user
        print("\n" + "=" * 60)
        print("Cleanup: Test user will remain in database for verification")
        print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
