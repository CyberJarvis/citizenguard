"""
Simplified RBAC Test - No Database Required
Tests core RBAC logic: roles, permissions, hierarchy
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.models.rbac import UserRole, Permission, RolePermissions, RoleHierarchy

# ANSI Colors
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    BOLD = '\033[1m'
    END = '\033[0m'


def print_header(text):
    print(f"\n{Colors.BOLD}{Colors.CYAN}{'='*70}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.CYAN}{text.center(70)}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.CYAN}{'='*70}{Colors.END}\n")


def print_success(text):
    print(f"{Colors.GREEN}[PASS] {text}{Colors.END}")


def print_error(text):
    print(f"{Colors.RED}[FAIL] {text}{Colors.END}")


def print_info(text):
    print(f"{Colors.BLUE}[INFO] {text}{Colors.END}")


def test_role_permissions():
    """Test RBAC permissions for all roles"""
    print_header("TEST 1: ROLE PERMISSIONS")

    test_cases = [
        # ===== CITIZEN PERMISSIONS =====
        ("CITIZEN", UserRole.CITIZEN, Permission.SUBMIT_REPORT, True),
        ("CITIZEN", UserRole.CITIZEN, Permission.VIEW_PUBLIC_REPORTS, True),
        ("CITIZEN", UserRole.CITIZEN, Permission.VIEW_ALERTS, True),
        ("CITIZEN", UserRole.CITIZEN, Permission.VERIFY_REPORT, False),
        ("CITIZEN", UserRole.CITIZEN, Permission.VIEW_USER_PII, False),
        ("CITIZEN", UserRole.CITIZEN, Permission.MANAGE_USERS, False),
        ("CITIZEN", UserRole.CITIZEN, Permission.DELETE_REPORT, False),

        # ===== ANALYST PERMISSIONS =====
        ("ANALYST", UserRole.ANALYST, Permission.VIEW_NLP_INSIGHTS, True),
        ("ANALYST", UserRole.ANALYST, Permission.VIEW_ANALYTICS, True),
        ("ANALYST", UserRole.ANALYST, Permission.VIEW_FULL_ANALYTICS, True),
        ("ANALYST", UserRole.ANALYST, Permission.VIEW_GEO_DATA, True),
        ("ANALYST", UserRole.ANALYST, Permission.VIEW_REMOTE_SENSING_DATA, True),
        ("ANALYST", UserRole.ANALYST, Permission.VIEW_USER_PII, False),  # ❌ NO PII!
        ("ANALYST", UserRole.ANALYST, Permission.VIEW_USER_CONTACT, False),  # ❌ NO contact!
        ("ANALYST", UserRole.ANALYST, Permission.VIEW_REPORTER_DETAILS, False),  # ❌ NO reporter details!
        ("ANALYST", UserRole.ANALYST, Permission.VERIFY_REPORT, False),
        ("ANALYST", UserRole.ANALYST, Permission.MANAGE_USERS, False),

        # ===== AUTHORITY PERMISSIONS =====
        ("AUTHORITY", UserRole.AUTHORITY, Permission.VERIFY_REPORT, True),
        ("AUTHORITY", UserRole.AUTHORITY, Permission.VIEW_USER_PII, True),
        ("AUTHORITY", UserRole.AUTHORITY, Permission.VIEW_USER_CONTACT, True),
        ("AUTHORITY", UserRole.AUTHORITY, Permission.VIEW_REPORTER_DETAILS, True),
        ("AUTHORITY", UserRole.AUTHORITY, Permission.MANAGE_USERS, True),
        ("AUTHORITY", UserRole.AUTHORITY, Permission.ACCESS_VERIFICATION_PANEL, True),
        ("AUTHORITY", UserRole.AUTHORITY, Permission.VIEW_NLP_INSIGHTS, True),
        ("AUTHORITY", UserRole.AUTHORITY, Permission.DELETE_REPORT, False),  # ❌ Only admin
        ("AUTHORITY", UserRole.AUTHORITY, Permission.BAN_USERS, False),  # ❌ Only admin
        ("AUTHORITY", UserRole.AUTHORITY, Permission.ASSIGN_ROLES, False),  # ❌ Only admin

        # ===== AUTHORITY ADMIN PERMISSIONS =====
        ("ADMIN", UserRole.AUTHORITY_ADMIN, Permission.DELETE_REPORT, True),
        ("ADMIN", UserRole.AUTHORITY_ADMIN, Permission.BAN_USERS, True),
        ("ADMIN", UserRole.AUTHORITY_ADMIN, Permission.ASSIGN_ROLES, True),
        ("ADMIN", UserRole.AUTHORITY_ADMIN, Permission.SYSTEM_CONFIG, True),
        ("ADMIN", UserRole.AUTHORITY_ADMIN, Permission.VIEW_AUDIT_LOGS, True),
        ("ADMIN", UserRole.AUTHORITY_ADMIN, Permission.VIEW_USER_PII, True),
        ("ADMIN", UserRole.AUTHORITY_ADMIN, Permission.VERIFY_REPORT, True),
    ]

    passed = 0
    failed = 0
    failed_tests = []

    for test_name, role, permission, expected in test_cases:
        actual = RolePermissions.has_permission(role, permission)

        status = "[OK]" if actual == expected else "[FAIL]"
        color = Colors.GREEN if actual == expected else Colors.RED

        if actual == expected:
            print(f"{color}{status} {test_name:8s}: {permission.value:30s} = {actual}{Colors.END}")
            passed += 1
        else:
            print(f"{color}{status} {test_name:8s}: {permission.value:30s} = {actual} (expected {expected}){Colors.END}")
            failed += 1
            failed_tests.append((test_name, permission.value, actual, expected))

    print(f"\n{Colors.BOLD}Results: {Colors.GREEN}{passed} passed{Colors.END}, {Colors.RED}{failed} failed{Colors.END}")

    if failed_tests:
        print(f"\n{Colors.RED}Failed tests:{Colors.END}")
        for test_name, perm, actual, expected in failed_tests:
            print(f"  - {test_name}: {perm} (got {actual}, expected {expected})")

    return failed == 0


def test_role_hierarchy():
    """Test role hierarchy and precedence"""
    print_header("TEST 2: ROLE HIERARCHY")

    test_cases = [
        ("ADMIN > AUTHORITY", UserRole.AUTHORITY_ADMIN, UserRole.AUTHORITY, True),
        ("ADMIN > ANALYST", UserRole.AUTHORITY_ADMIN, UserRole.ANALYST, True),
        ("ADMIN > CITIZEN", UserRole.AUTHORITY_ADMIN, UserRole.CITIZEN, True),
        ("AUTHORITY > ANALYST", UserRole.AUTHORITY, UserRole.ANALYST, True),
        ("AUTHORITY > CITIZEN", UserRole.AUTHORITY, UserRole.CITIZEN, True),
        ("ANALYST > CITIZEN", UserRole.ANALYST, UserRole.CITIZEN, True),
        ("CITIZEN < AUTHORITY", UserRole.CITIZEN, UserRole.AUTHORITY, False),
        ("CITIZEN < ANALYST", UserRole.CITIZEN, UserRole.ANALYST, False),
        ("AUTHORITY < ADMIN", UserRole.AUTHORITY, UserRole.AUTHORITY_ADMIN, False),
        ("ADMIN = ADMIN", UserRole.AUTHORITY_ADMIN, UserRole.AUTHORITY_ADMIN, True),
    ]

    passed = 0
    failed = 0

    for test_name, role1, role2, expected in test_cases:
        actual = RoleHierarchy.is_higher_or_equal(role1, role2)

        status = "[OK]" if actual == expected else "[FAIL]"
        color = Colors.GREEN if actual == expected else Colors.RED

        print(f"{color}{status} {test_name:20s}: {actual}{Colors.END}")

        if actual == expected:
            passed += 1
        else:
            failed += 1

    print(f"\n{Colors.BOLD}Results: {Colors.GREEN}{passed} passed{Colors.END}, {Colors.RED}{failed} failed{Colors.END}")

    return failed == 0


def test_permission_summary():
    """Display permission summary for each role"""
    print_header("TEST 3: PERMISSION SUMMARY")

    roles = [
        (UserRole.CITIZEN, "CITIZEN"),
        (UserRole.ANALYST, "ANALYST"),
        (UserRole.AUTHORITY, "AUTHORITY"),
        (UserRole.AUTHORITY_ADMIN, "AUTHORITY ADMIN")
    ]

    for role, name in roles:
        permissions = RolePermissions.get_permissions(role)
        print(f"\n{Colors.BOLD}{Colors.CYAN}{name} ({len(permissions)} permissions):{Colors.END}")

        # Group permissions by category
        report_perms = [p for p in permissions if 'REPORT' in p.value]
        user_perms = [p for p in permissions if 'USER' in p.value or 'PII' in p.value]
        alert_perms = [p for p in permissions if 'ALERT' in p.value]
        analytics_perms = [p for p in permissions if 'ANALYTIC' in p.value or 'NLP' in p.value]
        system_perms = [p for p in permissions if any(x in p.value for x in ['SYSTEM', 'AUDIT', 'CONFIG', 'VERIFICATION', 'CONSOLE'])]

        if report_perms:
            print(f"  {Colors.YELLOW}Reports:{Colors.END} {', '.join([p.value for p in report_perms])}")
        if user_perms:
            print(f"  {Colors.YELLOW}Users:{Colors.END} {', '.join([p.value for p in user_perms])}")
        if alert_perms:
            print(f"  {Colors.YELLOW}Alerts:{Colors.END} {', '.join([p.value for p in alert_perms])}")
        if analytics_perms:
            print(f"  {Colors.YELLOW}Analytics:{Colors.END} {', '.join([p.value for p in analytics_perms])}")
        if system_perms:
            print(f"  {Colors.YELLOW}System:{Colors.END} {', '.join([p.value for p in system_perms])}")

    return True


def main():
    """Main test runner"""
    print(f"{Colors.BOLD}{Colors.CYAN}")
    print("="*70)
    print("           RBAC CORE LOGIC TEST SUITE".center(70))
    print("           CoastGuardian Platform".center(70))
    print("="*70)
    print(f"{Colors.END}\n")

    # Run tests
    test1_passed = test_role_permissions()
    test2_passed = test3_passed = test_role_hierarchy()
    test3_passed = test_permission_summary()

    # Summary
    print_header("FINAL SUMMARY")

    all_passed = test1_passed and test2_passed and test3_passed

    if all_passed:
        print_success("ALL RBAC CORE TESTS PASSED!")
        print_info("\nRole definitions are correct")
        print_info("Permissions are properly assigned")
        print_info("Role hierarchy works correctly")
        print_success("\nRBAC System Core is READY!")

        print(f"\n{Colors.BOLD}Next Steps:{Colors.END}")
        print_info("1. Start the backend server to test API endpoints")
        print_info("2. Test Authority verification panel")
        print_info("3. Verify PII filtering for Analysts")
        print_info("4. Test role-based access control on endpoints")

    else:
        print_error("✗ Some tests failed. Review the errors above.")
        sys.exit(1)

    print(f"\n{Colors.CYAN}{'='*70}{Colors.END}\n")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print_error(f"Test suite failed with error: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
