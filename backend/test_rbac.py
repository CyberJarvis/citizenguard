"""
RBAC System Test Script
Tests role-based access control with all 4 roles
"""

import asyncio
import sys
from datetime import datetime, timezone
from motor.motor_asyncio import AsyncIOMotorClient
from app.config import settings
from app.models.user import User
from app.models.rbac import UserRole
from app.models.hazard import HazardReport, HazardType, HazardCategory, VerificationStatus, Location
from app.utils.password import hash_password
from app.utils.jwt import create_access_token

# ANSI Colors for terminal output
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    MAGENTA = '\033[95m'
    CYAN = '\033[96m'
    WHITE = '\033[97m'
    BOLD = '\033[1m'
    END = '\033[0m'


def print_header(text):
    """Print colored header"""
    print(f"\n{Colors.BOLD}{Colors.CYAN}{'='*70}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.CYAN}{text.center(70)}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.CYAN}{'='*70}{Colors.END}\n")


def print_success(text):
    """Print success message"""
    print(f"{Colors.GREEN}✓ {text}{Colors.END}")


def print_error(text):
    """Print error message"""
    print(f"{Colors.RED}✗ {text}{Colors.END}")


def print_info(text):
    """Print info message"""
    print(f"{Colors.BLUE}ℹ {text}{Colors.END}")


def print_warning(text):
    """Print warning message"""
    print(f"{Colors.YELLOW}⚠ {text}{Colors.END}")


async def setup_test_database():
    """Setup test users and data"""
    print_header("SETTING UP TEST DATABASE")

    try:
        # Connect to MongoDB
        client = AsyncIOMotorClient(settings.MONGODB_URL)
        db = client[settings.MONGODB_DB_NAME]

        print_info("Connected to MongoDB")

        # Clear existing test users
        await db.users.delete_many({"email": {"$regex": "^test"}})
        print_info("Cleared existing test users")

        # Create test users for each role
        test_users = [
            {
                "user_id": "TST-CITIZEN-001",
                "email": "test.citizen@coastguardian.com",
                "name": "Test Citizen",
                "role": UserRole.CITIZEN,
                "hashed_password": hash_password("TestPass123!"),
                "is_active": True,
                "is_banned": False,
                "email_verified": True,
                "credibility_score": 75,
                "total_reports": 10,
                "verified_reports": 7
            },
            {
                "user_id": "TST-ANALYST-001",
                "email": "test.analyst@coastguardian.com",
                "name": "Test Analyst",
                "role": UserRole.ANALYST,
                "hashed_password": hash_password("TestPass123!"),
                "is_active": True,
                "is_banned": False,
                "email_verified": True
            },
            {
                "user_id": "TST-AUTHORITY-001",
                "email": "test.authority@coastguardian.com",
                "name": "Test Authority",
                "role": UserRole.AUTHORITY,
                "hashed_password": hash_password("TestPass123!"),
                "is_active": True,
                "is_banned": False,
                "email_verified": True,
                "authority_organization": "INCOIS",
                "authority_designation": "Senior Officer",
                "authority_jurisdiction": ["Mumbai", "Chennai", "Visakhapatnam"]
            },
            {
                "user_id": "TST-ADMIN-001",
                "email": "test.admin@coastguardian.com",
                "name": "Test Admin",
                "role": UserRole.AUTHORITY_ADMIN,
                "hashed_password": hash_password("TestPass123!"),
                "is_active": True,
                "is_banned": False,
                "email_verified": True,
                "authority_organization": "INCOIS",
                "authority_designation": "Platform Administrator"
            }
        ]

        # Insert test users
        for user_data in test_users:
            user = User(**user_data, created_at=datetime.now(timezone.utc), updated_at=datetime.now(timezone.utc))
            await db.users.insert_one(user.to_mongo())
            print_success(f"Created {user.role.value.upper()} user: {user.email}")

        # Create test hazard reports
        print_info("\nCreating test hazard reports...")

        test_reports = [
            {
                "report_id": "TST-RPT-001",
                "user_id": "TST-CITIZEN-001",
                "user_name": "Test Citizen",
                "hazard_type": HazardType.HIGH_WAVES,
                "category": HazardCategory.NATURAL,
                "description": "High waves observed at Juhu Beach. Wave height approximately 4-5 meters.",
                "image_url": "/uploads/test/high_waves.jpg",
                "location": Location(
                    latitude=19.0760,
                    longitude=72.8777,
                    address="Juhu Beach, Mumbai"
                ).dict(),
                "verification_status": VerificationStatus.PENDING,
                "nlp_sentiment": "concerned",
                "nlp_keywords": ["high waves", "dangerous", "beach"],
                "nlp_risk_score": 0.75,
                "risk_level": "high",
                "urgency": "urgent",
                "requires_immediate_action": True,
                "created_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc),
                "is_active": True,
                "is_deleted": False
            },
            {
                "report_id": "TST-RPT-002",
                "user_id": "TST-CITIZEN-001",
                "user_name": "Test Citizen",
                "hazard_type": HazardType.OIL_SPILL,
                "category": HazardCategory.HUMAN_MADE,
                "description": "Oil spill detected near fishing harbor.",
                "image_url": "/uploads/test/oil_spill.jpg",
                "location": Location(
                    latitude=13.0827,
                    longitude=80.2707,
                    address="Chennai Fishing Harbor"
                ).dict(),
                "verification_status": VerificationStatus.PENDING,
                "nlp_sentiment": "alarmed",
                "nlp_keywords": ["oil spill", "pollution", "harbor"],
                "nlp_risk_score": 0.68,
                "risk_level": "medium",
                "urgency": "normal",
                "requires_immediate_action": False,
                "created_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc),
                "is_active": True,
                "is_deleted": False
            }
        ]

        for report_data in test_reports:
            report = HazardReport(**report_data)
            await db.hazard_reports.insert_one(report.to_mongo())
            print_success(f"Created test report: {report.report_id}")

        print_success("\n✓ Test database setup complete!")

        await client.close()
        return True

    except Exception as e:
        print_error(f"Failed to setup test database: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


async def test_role_permissions():
    """Test RBAC permissions"""
    print_header("TESTING RBAC PERMISSIONS")

    from app.models.rbac import Permission, RolePermissions

    test_cases = [
        # Citizen permissions
        (UserRole.CITIZEN, Permission.SUBMIT_REPORT, True),
        (UserRole.CITIZEN, Permission.VIEW_PUBLIC_REPORTS, True),
        (UserRole.CITIZEN, Permission.VERIFY_REPORT, False),
        (UserRole.CITIZEN, Permission.VIEW_USER_PII, False),
        (UserRole.CITIZEN, Permission.MANAGE_USERS, False),

        # Analyst permissions
        (UserRole.ANALYST, Permission.VIEW_NLP_INSIGHTS, True),
        (UserRole.ANALYST, Permission.VIEW_ANALYTICS, True),
        (UserRole.ANALYST, Permission.VIEW_USER_PII, False),  # NO PII!
        (UserRole.ANALYST, Permission.VIEW_USER_CONTACT, False),  # NO contact!
        (UserRole.ANALYST, Permission.VERIFY_REPORT, False),

        # Authority permissions
        (UserRole.AUTHORITY, Permission.VERIFY_REPORT, True),
        (UserRole.AUTHORITY, Permission.VIEW_USER_PII, True),
        (UserRole.AUTHORITY, Permission.VIEW_REPORTER_DETAILS, True),
        (UserRole.AUTHORITY, Permission.MANAGE_USERS, True),
        (UserRole.AUTHORITY, Permission.DELETE_REPORT, False),  # Only admin

        # Authority Admin permissions
        (UserRole.AUTHORITY_ADMIN, Permission.DELETE_REPORT, True),
        (UserRole.AUTHORITY_ADMIN, Permission.BAN_USERS, True),
        (UserRole.AUTHORITY_ADMIN, Permission.ASSIGN_ROLES, True),
        (UserRole.AUTHORITY_ADMIN, Permission.SYSTEM_CONFIG, True),
    ]

    passed = 0
    failed = 0

    for role, permission, expected in test_cases:
        actual = RolePermissions.has_permission(role, permission)

        if actual == expected:
            print_success(f"{role.value.upper()}: {permission.value} = {actual} ✓")
            passed += 1
        else:
            print_error(f"{role.value.upper()}: {permission.value} = {actual} (expected {expected}) ✗")
            failed += 1

    print(f"\n{Colors.BOLD}Results: {passed} passed, {failed} failed{Colors.END}")
    return failed == 0


async def test_role_hierarchy():
    """Test role hierarchy"""
    print_header("TESTING ROLE HIERARCHY")

    from app.models.rbac import RoleHierarchy

    test_cases = [
        (UserRole.AUTHORITY_ADMIN, UserRole.AUTHORITY, True),  # Admin > Authority
        (UserRole.AUTHORITY_ADMIN, UserRole.ANALYST, True),  # Admin > Analyst
        (UserRole.AUTHORITY_ADMIN, UserRole.CITIZEN, True),  # Admin > Citizen
        (UserRole.AUTHORITY, UserRole.ANALYST, True),  # Authority > Analyst
        (UserRole.AUTHORITY, UserRole.CITIZEN, True),  # Authority > Citizen
        (UserRole.ANALYST, UserRole.CITIZEN, True),  # Analyst > Citizen
        (UserRole.CITIZEN, UserRole.AUTHORITY, False),  # Citizen < Authority
    ]

    passed = 0
    failed = 0

    for role1, role2, expected in test_cases:
        actual = RoleHierarchy.is_higher_or_equal(role1, role2)

        if actual == expected:
            print_success(f"{role1.value} ≥ {role2.value} = {actual} ✓")
            passed += 1
        else:
            print_error(f"{role1.value} ≥ {role2.value} = {actual} (expected {expected}) ✗")
            failed += 1

    print(f"\n{Colors.BOLD}Results: {passed} passed, {failed} failed{Colors.END}")
    return failed == 0


async def generate_test_tokens():
    """Generate JWT tokens for testing"""
    print_header("GENERATING TEST TOKENS")

    tokens = {}

    users = [
        ("TST-CITIZEN-001", "citizen"),
        ("TST-ANALYST-001", "analyst"),
        ("TST-AUTHORITY-001", "authority"),
        ("TST-ADMIN-001", "admin")
    ]

    for user_id, role in users:
        token = create_access_token(user_id=user_id)
        tokens[role] = token
        print_success(f"{role.upper()} token generated")
        print(f"   {Colors.MAGENTA}{token[:50]}...{Colors.END}\n")

    return tokens


async def main():
    """Main test runner"""
    print(f"{Colors.BOLD}{Colors.MAGENTA}")
    print("╔═══════════════════════════════════════════════════════════════════╗")
    print("║                  RBAC SYSTEM TEST SUITE                          ║")
    print("║                  CoastGuardian Platform                          ║")
    print("╚═══════════════════════════════════════════════════════════════════╝")
    print(f"{Colors.END}\n")

    # Test 1: Setup Database
    if not await setup_test_database():
        print_error("\nDatabase setup failed. Exiting...")
        sys.exit(1)

    # Test 2: Role Permissions
    test1_passed = await test_role_permissions()

    # Test 3: Role Hierarchy
    test2_passed = await test_role_hierarchy()

    # Test 4: Generate Tokens
    tokens = await generate_test_tokens()

    # Summary
    print_header("TEST SUMMARY")

    if test1_passed and test2_passed:
        print_success("All core RBAC tests passed! ✓")
        print_info("\nNext steps:")
        print_info("1. Start the backend server: python main.py")
        print_info("2. Test the Authority endpoints using the tokens above")
        print_info("3. Test endpoints:")
        print_info("   - GET /api/v1/authority/verification-panel/summary")
        print_info("   - GET /api/v1/authority/verification-panel/reports")
        print_info("   - POST /api/v1/authority/verification-panel/reports/TST-RPT-001/verify")
        print_success("\nRBAC System is ready for integration testing!")
    else:
        print_error("Some tests failed. Please review the errors above.")
        sys.exit(1)

    print(f"\n{Colors.BOLD}{Colors.MAGENTA}{'='*70}{Colors.END}")
    print(f"{Colors.BOLD}Test credentials:{Colors.END}")
    print(f"{Colors.YELLOW}Email: test.<role>@coastguardian.com{Colors.END}")
    print(f"{Colors.YELLOW}Password: TestPass123!{Colors.END}")
    print(f"{Colors.YELLOW}Roles: citizen, analyst, authority, admin{Colors.END}")
    print(f"{Colors.BOLD}{Colors.MAGENTA}{'='*70}{Colors.END}\n")


if __name__ == "__main__":
    asyncio.run(main())
