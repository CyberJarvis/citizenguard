#!/usr/bin/env python3
"""
Test backend OAuth callback to see the actual error
"""

import requests
import json

# Use a dummy code (will fail, but we'll see the error message)
BACKEND_URL = "http://localhost:8000/api/v1"
dummy_code = "4/DUMMY_CODE_FOR_TESTING"
dummy_state = "DUMMY_STATE"

print("Testing backend OAuth callback with dummy code...")
print("This WILL fail, but we'll see the exact error message from backend\n")

try:
    response = requests.get(
        f"{BACKEND_URL}/auth/google/callback",
        params={"code": dummy_code, "state": dummy_state},
        timeout=30
    )

    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")

except requests.exceptions.RequestException as e:
    if hasattr(e, 'response') and e.response is not None:
        print(f"Status: {e.response.status_code}")
        print(f"Response body: {e.response.text}")

        try:
            error_data = e.response.json()
            print(f"\nParsed error: {json.dumps(error_data, indent=2)}")

            if 'detail' in error_data:
                print(f"\n>>> ERROR MESSAGE: {error_data['detail']}")

                if 'redirect_uri_mismatch' in str(error_data['detail']).lower():
                    print("\n🔴 PROBLEM: Google Cloud Console redirect URI mismatch!")
                    print("   You MUST update Google Cloud Console with:")
                    print("   http://localhost:3000/auth/google/callback")
        except:
            pass
    else:
        print(f"Request failed: {e}")

print("\n" + "="*60)
print("Now test with a REAL code from your browser console:")
print("1. Go to http://localhost:3000/login")
print("2. Click 'Sign in with Google'")
print("3. In the callback URL, copy the 'code' parameter")
print("4. Run this script again with that code")
print("="*60)
