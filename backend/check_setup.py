#!/usr/bin/env python3
"""
BlueRadar 2.0 Setup Diagnostic Tool
Checks system requirements and dependency compatibility
"""

import sys
import subprocess
import importlib.metadata


def check_python_version():
    """Check Python version compatibility"""
    print("\n=== Python Version Check ===")
    version = sys.version_info
    print(f"Python Version: {version.major}.{version.minor}.{version.micro}")

    if version.major == 3 and version.minor in [11, 12]:
        print("✓ Python version is compatible")
        return True
    elif version.major == 3 and version.minor == 13:
        print("❌ Python 3.13 is NOT supported due to bcrypt compatibility issues")
        print("   Please downgrade to Python 3.11 or 3.12")
        return False
    else:
        print(f"⚠️  Python {version.major}.{version.minor} may have compatibility issues")
        print("   Recommended: Python 3.11 or 3.12")
        return False


def check_package(package_name, min_version=None, max_version=None):
    """Check if a package is installed with correct version"""
    try:
        version = importlib.metadata.version(package_name)

        if min_version and version < min_version:
            print(f"❌ {package_name} version {version} is too old (need >= {min_version})")
            return False
        if max_version and version > max_version:
            print(f"❌ {package_name} version {version} is too new (need <= {max_version})")
            return False

        print(f"✓ {package_name}: {version}")
        return True
    except importlib.metadata.PackageNotFoundError:
        print(f"❌ {package_name}: NOT INSTALLED")
        return False


def check_critical_packages():
    """Check all critical packages"""
    print("\n=== Critical Packages ===")

    packages = {
        "fastapi": {"min": "0.109.0"},
        "uvicorn": {"min": "0.27.0"},
        "passlib": {"min": "1.7.4"},
        "bcrypt": {"exact": "4.0.1"},
        "motor": {"min": "3.3.2"},
        "redis": {"min": "7.1.0"},
        "pydantic": {"min": "2.5.3"},
        "python-jose": {"min": "3.3.0"},
    }

    all_ok = True
    for package, requirements in packages.items():
        try:
            version = importlib.metadata.version(package)

            if "exact" in requirements:
                if version == requirements["exact"]:
                    print(f"✓ {package}: {version}")
                else:
                    print(f"❌ {package}: {version} (need exactly {requirements['exact']})")
                    all_ok = False
            else:
                print(f"✓ {package}: {version}")
        except importlib.metadata.PackageNotFoundError:
            print(f"❌ {package}: NOT INSTALLED")
            all_ok = False

    return all_ok


def check_bcrypt_compatibility():
    """Check bcrypt compatibility with passlib"""
    print("\n=== Bcrypt Compatibility Test ===")

    try:
        from passlib.context import CryptContext

        pwd_context = CryptContext(
            schemes=["bcrypt"],
            deprecated="auto",
            bcrypt__rounds=12
        )

        # Test password hashing
        test_password = "test_password_123"
        hashed = pwd_context.hash(test_password)

        # Test password verification
        is_valid = pwd_context.verify(test_password, hashed)

        if is_valid:
            print("✓ Bcrypt hashing and verification working correctly")

            # Test with long password (72+ bytes)
            long_password = "a" * 100
            hashed_long = pwd_context.hash(long_password)
            is_valid_long = pwd_context.verify(long_password, hashed_long)

            if is_valid_long:
                print("✓ Long password handling working correctly")
                return True
            else:
                print("❌ Long password verification failed")
                return False
        else:
            print("❌ Password verification failed")
            return False

    except Exception as e:
        print(f"❌ Bcrypt test failed: {str(e)}")
        if "attribute '__about__'" in str(e):
            print("   This is the Python 3.13 compatibility issue!")
            print("   Solution: Downgrade to Python 3.11 or 3.12")
        return False


def check_services():
    """Check if MongoDB and Redis are accessible"""
    print("\n=== External Services Check ===")

    # Check MongoDB
    try:
        from motor.motor_asyncio import AsyncIOMotorClient
        import asyncio

        async def test_mongo():
            client = AsyncIOMotorClient("mongodb://localhost:27017", serverSelectionTimeoutMS=2000)
            try:
                await client.admin.command('ping')
                return True
            except Exception:
                return False
            finally:
                client.close()

        mongo_ok = asyncio.run(test_mongo())
        if mongo_ok:
            print("✓ MongoDB: Connected")
        else:
            print("❌ MongoDB: Not accessible (is it running?)")
    except Exception as e:
        print(f"❌ MongoDB: Connection test failed - {str(e)}")
        mongo_ok = False

    # Check Redis
    try:
        import redis
        r = redis.Redis(host='localhost', port=6379, socket_connect_timeout=2)
        r.ping()
        print("✓ Redis: Connected")
        redis_ok = True
    except Exception:
        print("❌ Redis: Not accessible (is it running?)")
        redis_ok = False

    return mongo_ok and redis_ok


def check_environment():
    """Check environment variables"""
    print("\n=== Environment Configuration ===")

    import os
    from pathlib import Path

    env_file = Path(".env")
    if env_file.exists():
        print("✓ .env file found")

        # Check critical env vars
        from dotenv import load_dotenv
        load_dotenv()

        required_vars = [
            "MONGODB_URL",
            "REDIS_HOST",
            "JWT_SECRET_KEY",
            "SECRET_KEY"
        ]

        all_ok = True
        for var in required_vars:
            if os.getenv(var):
                print(f"✓ {var}: Set")
            else:
                print(f"❌ {var}: Not set")
                all_ok = False

        return all_ok
    else:
        print("❌ .env file not found")
        print("   Copy .env.example to .env and configure it")
        return False


def main():
    """Run all checks"""
    print("=" * 60)
    print("BlueRadar 2.0 Setup Diagnostic Tool")
    print("=" * 60)

    results = {
        "Python Version": check_python_version(),
        "Critical Packages": check_critical_packages(),
        "Bcrypt Compatibility": check_bcrypt_compatibility(),
        "External Services": check_services(),
        "Environment Config": check_environment()
    }

    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)

    for check, passed in results.items():
        status = "✓ PASS" if passed else "❌ FAIL"
        print(f"{check}: {status}")

    all_passed = all(results.values())

    print("\n" + "=" * 60)
    if all_passed:
        print("✓ ALL CHECKS PASSED - Ready to run!")
        print("\nStart the server with:")
        print("  uvicorn app.main:app --reload")
    else:
        print("❌ SOME CHECKS FAILED - Please fix the issues above")
        print("\nCommon fixes:")
        print("  1. Downgrade Python to 3.11 or 3.12")
        print("  2. Install dependencies: pip install -r requirements.txt")
        print("  3. Start MongoDB and Redis services")
        print("  4. Configure .env file")
    print("=" * 60)

    sys.exit(0 if all_passed else 1)


if __name__ == "__main__":
    main()
