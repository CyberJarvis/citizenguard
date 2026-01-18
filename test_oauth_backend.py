#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OAuth Backend Diagnostic Script
Tests the Google OAuth endpoints directly
"""

import sys
import io
import requests
import json
from urllib.parse import urlparse, parse_qs

# Fix encoding for Windows console
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Configuration
BACKEND_URL = "http://localhost:8000/api/v1"
GOOGLE_REDIRECT_URI_EXPECTED = "http://localhost:3000/auth/google/callback"

def test_google_login_endpoint():
    """Test the /auth/google/login endpoint"""
    print("\n" + "="*60)
    print("TEST 1: Google Login Endpoint")
    print("="*60)

    try:
        url = f"{BACKEND_URL}/auth/google/login"
        print(f"Calling: {url}")

        response = requests.get(url)

        print(f"Status Code: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")

        if response.status_code == 200:
            data = response.json()
            if 'authorization_url' in data:
                print("✅ SUCCESS: authorization_url present")

                # Parse the URL to check redirect_uri
                auth_url = data['authorization_url']
                parsed = urlparse(auth_url)
                params = parse_qs(parsed.query)

                redirect_uri = params.get('redirect_uri', [None])[0]
                print(f"Redirect URI in auth URL: {redirect_uri}")

                if redirect_uri == GOOGLE_REDIRECT_URI_EXPECTED:
                    print(f"✅ Redirect URI matches expected: {GOOGLE_REDIRECT_URI_EXPECTED}")
                else:
                    print(f"❌ Redirect URI MISMATCH!")
                    print(f"   Expected: {GOOGLE_REDIRECT_URI_EXPECTED}")
                    print(f"   Got: {redirect_uri}")
                    print(f"\n   FIX: Update backend/.env with:")
                    print(f"   GOOGLE_REDIRECT_URI={GOOGLE_REDIRECT_URI_EXPECTED}")

                if 'state' in data:
                    print(f"✅ State parameter generated: {data['state'][:20]}...")
                else:
                    print("⚠️  No state parameter (CSRF protection missing)")
            else:
                print("❌ FAIL: authorization_url not in response")
        else:
            print(f"❌ FAIL: Expected 200, got {response.status_code}")

    except requests.exceptions.ConnectionError:
        print("❌ ERROR: Cannot connect to backend!")
        print("   Make sure backend is running on http://localhost:8000")
    except Exception as e:
        print(f"❌ ERROR: {e}")

def test_backend_config():
    """Check if backend is configured correctly"""
    print("\n" + "="*60)
    print("TEST 2: Backend Configuration Check")
    print("="*60)

    try:
        # Read .env file
        env_file = "backend/.env"
        print(f"Reading {env_file}...")

        with open(env_file, 'r') as f:
            lines = f.readlines()

        config = {}
        for line in lines:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                config[key] = value

        print("\nGoogle OAuth Configuration:")
        print(f"GOOGLE_CLIENT_ID: {config.get('GOOGLE_CLIENT_ID', 'NOT SET')[:50]}...")
        print(f"GOOGLE_CLIENT_SECRET: {'***' + config.get('GOOGLE_CLIENT_SECRET', 'NOT SET')[-10:] if config.get('GOOGLE_CLIENT_SECRET') else 'NOT SET'}")
        print(f"GOOGLE_REDIRECT_URI: {config.get('GOOGLE_REDIRECT_URI', 'NOT SET')}")
        print(f"FRONTEND_URL: {config.get('FRONTEND_URL', 'NOT SET')}")

        # Check redirect URI
        redirect_uri = config.get('GOOGLE_REDIRECT_URI', '')
        if redirect_uri == GOOGLE_REDIRECT_URI_EXPECTED:
            print(f"\n✅ GOOGLE_REDIRECT_URI is correct")
        else:
            print(f"\n❌ GOOGLE_REDIRECT_URI is WRONG!")
            print(f"   Current: {redirect_uri}")
            print(f"   Expected: {GOOGLE_REDIRECT_URI_EXPECTED}")
            print(f"\n   FIX: Update backend/.env line:")
            print(f"   GOOGLE_REDIRECT_URI={GOOGLE_REDIRECT_URI_EXPECTED}")

    except FileNotFoundError:
        print(f"❌ ERROR: {env_file} not found")
    except Exception as e:
        print(f"❌ ERROR: {e}")

def test_health_endpoint():
    """Test if backend is running"""
    print("\n" + "="*60)
    print("TEST 0: Backend Health Check")
    print("="*60)

    try:
        url = f"{BACKEND_URL.replace('/api/v1', '')}/health"
        print(f"Calling: {url}")

        response = requests.get(url, timeout=5)
        print(f"Status Code: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            print(f"Response: {json.dumps(data, indent=2)}")

            if data.get('status') == 'healthy':
                print("✅ Backend is healthy")
            else:
                print(f"⚠️  Backend status: {data.get('status')}")
        else:
            print(f"❌ Unexpected status code: {response.status_code}")

    except requests.exceptions.ConnectionError:
        print("❌ ERROR: Cannot connect to backend!")
        print("   Make sure backend is running:")
        print("   cd backend")
        print("   python main.py")
    except Exception as e:
        print(f"❌ ERROR: {e}")

def print_next_steps():
    """Print next steps based on tests"""
    print("\n" + "="*60)
    print("NEXT STEPS")
    print("="*60)

    print("\n1. If backend is not running:")
    print("   cd backend")
    print("   python main.py")

    print("\n2. If GOOGLE_REDIRECT_URI is wrong:")
    print("   - Open backend/.env")
    print(f"   - Change GOOGLE_REDIRECT_URI to: {GOOGLE_REDIRECT_URI_EXPECTED}")
    print("   - Restart backend server")

    print("\n3. Update Google Cloud Console:")
    print("   - Go to: https://console.cloud.google.com/apis/credentials")
    print("   - Find your OAuth 2.0 Client ID")
    print("   - Add to 'Authorized redirect URIs':")
    print(f"     {GOOGLE_REDIRECT_URI_EXPECTED}")
    print("   - Click 'Save'")
    print("   - Wait 5-10 minutes for changes to propagate")

    print("\n4. Test OAuth flow:")
    print("   - Clear browser cache")
    print("   - Go to http://localhost:3000/login")
    print("   - Click 'Sign in with Google'")
    print("   - Check browser console for detailed logs")

    print("\n5. If still getting 400 error:")
    print("   - Check browser console for 'API: Error response data'")
    print("   - Look for 'redirect_uri_mismatch' error")
    print("   - Verify Google Cloud Console was updated")
    print("   - Wait longer (changes can take 10+ minutes)")

def main():
    """Run all tests"""
    print("\n" + "="*60)
    print("GOOGLE OAUTH DIAGNOSTIC TOOL")
    print("="*60)
    print("\nThis script will test your OAuth backend configuration")

    # Run tests
    test_health_endpoint()
    test_backend_config()
    test_google_login_endpoint()
    print_next_steps()

    print("\n" + "="*60)
    print("Tests Complete!")
    print("="*60 + "\n")

if __name__ == "__main__":
    main()
