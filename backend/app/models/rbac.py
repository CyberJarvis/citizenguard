"""
RBAC (Role-Based Access Control) Models
Defines roles, permissions, and access control logic
"""

from enum import Enum
from typing import List, Set
from pydantic import BaseModel


class UserRole(str, Enum):
    """Enhanced user role enumeration with 5 distinct roles"""

    # Basic user - citizens reporting hazards
    CITIZEN = "citizen"

    # Verified organizers - citizens with credibility >= 80 who can create communities/events
    VERIFIED_ORGANIZER = "verified_organizer"

    # Authorities - INCOIS officers, disaster managers, coast guards, etc.
    AUTHORITY = "authority"

    # Analysts - data science & monitoring teams (no PII access)
    ANALYST = "analyst"

    # Super admins - INCOIS leadership, platform administrators
    AUTHORITY_ADMIN = "authority_admin"


class Permission(str, Enum):
    """System permissions - granular access control"""

    # Report Permissions
    SUBMIT_REPORT = "submit_report"
    VIEW_PUBLIC_REPORTS = "view_public_reports"
    VIEW_DETAILED_REPORTS = "view_detailed_reports"
    VIEW_REPORT_HISTORY = "view_report_history"
    VERIFY_REPORT = "verify_report"
    DELETE_REPORT = "delete_report"

    # User Data Permissions
    VIEW_USER_PII = "view_user_pii"  # Personal Identifiable Information
    VIEW_USER_CONTACT = "view_user_contact"
    VIEW_REPORTER_DETAILS = "view_reporter_details"
    MANAGE_USERS = "manage_users"
    BAN_USERS = "ban_users"
    ASSIGN_ROLES = "assign_roles"

    # Alert Permissions
    VIEW_ALERTS = "view_alerts"
    CREATE_ALERTS = "create_alerts"
    EDIT_ALERTS = "edit_alerts"
    DELETE_ALERTS = "delete_alerts"

    # Analytics Permissions
    VIEW_ANALYTICS = "view_analytics"
    VIEW_FULL_ANALYTICS = "view_full_analytics"
    VIEW_NLP_INSIGHTS = "view_nlp_insights"
    VIEW_SOCIAL_FEEDS = "view_social_feeds"

    # System Permissions
    VIEW_AUDIT_LOGS = "view_audit_logs"
    SYSTEM_CONFIG = "system_config"
    ACCESS_VERIFICATION_PANEL = "access_verification_panel"
    ACCESS_ALERT_CONSOLE = "access_alert_console"

    # Geographic/Remote Sensing Data
    VIEW_GEO_DATA = "view_geo_data"
    VIEW_REMOTE_SENSING_DATA = "view_remote_sensing_data"

    # Admin-specific Permissions
    VIEW_ADMIN_DASHBOARD = "view_admin_dashboard"
    MANAGE_ALL_USERS = "manage_all_users"
    CREATE_USERS = "create_users"
    DELETE_USERS = "delete_users"
    VIEW_SYSTEM_HEALTH = "view_system_health"
    MANAGE_SYSTEM_SETTINGS = "manage_system_settings"
    EXPORT_AUDIT_LOGS = "export_audit_logs"
    MODERATE_CONTENT = "moderate_content"
    DELETE_ANY_CONTENT = "delete_any_content"
    VIEW_ERROR_LOGS = "view_error_logs"
    VIEW_API_STATS = "view_api_stats"

    # Community & Event Permissions (Verified Organizers)
    CREATE_COMMUNITY = "create_community"
    MANAGE_OWN_COMMUNITY = "manage_own_community"
    CREATE_EVENT = "create_event"
    MANAGE_OWN_EVENT = "manage_own_event"
    MARK_ATTENDANCE = "mark_attendance"
    VIEW_COMMUNITY_MEMBERS = "view_community_members"
    VIEW_EVENT_REGISTRATIONS = "view_event_registrations"
    RECEIVE_HAZARD_NOTIFICATIONS = "receive_hazard_notifications"

    # Community Admin Permissions
    REVIEW_ORGANIZER_APPLICATIONS = "review_organizer_applications"
    APPROVE_ORGANIZER = "approve_organizer"
    REJECT_ORGANIZER = "reject_organizer"
    VIEW_AADHAAR_DOCUMENTS = "view_aadhaar_documents"
    MANAGE_ALL_COMMUNITIES = "manage_all_communities"
    MANAGE_ALL_EVENTS = "manage_all_events"


class RolePermissions:
    """
    Role-based permission mapping
    Defines which permissions each role has
    """

    # Citizen Permissions
    CITIZEN_PERMISSIONS: Set[Permission] = {
        Permission.SUBMIT_REPORT,
        Permission.VIEW_PUBLIC_REPORTS,
        Permission.VIEW_ALERTS,
    }

    # Verified Organizer Permissions (Citizens with credibility >= 80)
    VERIFIED_ORGANIZER_PERMISSIONS: Set[Permission] = {
        # Citizen base permissions
        Permission.SUBMIT_REPORT,
        Permission.VIEW_PUBLIC_REPORTS,
        Permission.VIEW_ALERTS,

        # Community management
        Permission.CREATE_COMMUNITY,
        Permission.MANAGE_OWN_COMMUNITY,
        Permission.VIEW_COMMUNITY_MEMBERS,

        # Event management
        Permission.CREATE_EVENT,
        Permission.MANAGE_OWN_EVENT,
        Permission.MARK_ATTENDANCE,
        Permission.VIEW_EVENT_REGISTRATIONS,

        # Hazard notifications for emergency response
        Permission.RECEIVE_HAZARD_NOTIFICATIONS,
    }

    # Authority Permissions (INCOIS, Disaster Managers, Coast Guards, etc.)
    AUTHORITY_PERMISSIONS: Set[Permission] = {
        # View permissions
        Permission.VIEW_PUBLIC_REPORTS,
        Permission.VIEW_DETAILED_REPORTS,
        Permission.VIEW_REPORTER_DETAILS,
        Permission.VIEW_USER_PII,
        Permission.VIEW_USER_CONTACT,
        Permission.VIEW_ALERTS,
        Permission.VIEW_ANALYTICS,
        Permission.VIEW_NLP_INSIGHTS,
        Permission.VIEW_SOCIAL_FEEDS,

        # Action permissions
        Permission.VERIFY_REPORT,
        Permission.ACCESS_VERIFICATION_PANEL,
        Permission.ACCESS_ALERT_CONSOLE,
        Permission.MANAGE_USERS,
    }

    # Analyst Permissions (Data Science & Monitoring - NO PII)
    ANALYST_PERMISSIONS: Set[Permission] = {
        # View permissions (NO PII ACCESS)
        Permission.VIEW_PUBLIC_REPORTS,
        Permission.VIEW_REPORT_HISTORY,
        Permission.VIEW_ANALYTICS,
        Permission.VIEW_FULL_ANALYTICS,
        Permission.VIEW_NLP_INSIGHTS,
        Permission.VIEW_SOCIAL_FEEDS,
        Permission.VIEW_GEO_DATA,
        Permission.VIEW_REMOTE_SENSING_DATA,
        Permission.VIEW_ALERTS,

        # Note: Explicitly NO access to:
        # - VIEW_USER_PII
        # - VIEW_USER_CONTACT
        # - VIEW_REPORTER_DETAILS
    }

    # Authority Admin Permissions (Super Admin - Full Access)
    AUTHORITY_ADMIN_PERMISSIONS: Set[Permission] = {
        # All permissions - super admin has everything
        Permission.SUBMIT_REPORT,
        Permission.VIEW_PUBLIC_REPORTS,
        Permission.VIEW_DETAILED_REPORTS,
        Permission.VIEW_REPORT_HISTORY,
        Permission.VERIFY_REPORT,
        Permission.DELETE_REPORT,

        Permission.VIEW_USER_PII,
        Permission.VIEW_USER_CONTACT,
        Permission.VIEW_REPORTER_DETAILS,
        Permission.MANAGE_USERS,
        Permission.BAN_USERS,
        Permission.ASSIGN_ROLES,

        Permission.VIEW_ALERTS,
        Permission.CREATE_ALERTS,
        Permission.EDIT_ALERTS,
        Permission.DELETE_ALERTS,

        Permission.VIEW_ANALYTICS,
        Permission.VIEW_FULL_ANALYTICS,
        Permission.VIEW_NLP_INSIGHTS,
        Permission.VIEW_SOCIAL_FEEDS,

        Permission.VIEW_AUDIT_LOGS,
        Permission.SYSTEM_CONFIG,
        Permission.ACCESS_VERIFICATION_PANEL,
        Permission.ACCESS_ALERT_CONSOLE,

        Permission.VIEW_GEO_DATA,
        Permission.VIEW_REMOTE_SENSING_DATA,

        # Admin-specific permissions
        Permission.VIEW_ADMIN_DASHBOARD,
        Permission.MANAGE_ALL_USERS,
        Permission.CREATE_USERS,
        Permission.DELETE_USERS,
        Permission.VIEW_SYSTEM_HEALTH,
        Permission.MANAGE_SYSTEM_SETTINGS,
        Permission.EXPORT_AUDIT_LOGS,
        Permission.MODERATE_CONTENT,
        Permission.DELETE_ANY_CONTENT,
        Permission.VIEW_ERROR_LOGS,
        Permission.VIEW_API_STATS,

        # Community & Organizer Admin permissions
        Permission.CREATE_COMMUNITY,
        Permission.MANAGE_OWN_COMMUNITY,
        Permission.CREATE_EVENT,
        Permission.MANAGE_OWN_EVENT,
        Permission.MARK_ATTENDANCE,
        Permission.VIEW_COMMUNITY_MEMBERS,
        Permission.VIEW_EVENT_REGISTRATIONS,
        Permission.RECEIVE_HAZARD_NOTIFICATIONS,
        Permission.REVIEW_ORGANIZER_APPLICATIONS,
        Permission.APPROVE_ORGANIZER,
        Permission.REJECT_ORGANIZER,
        Permission.VIEW_AADHAAR_DOCUMENTS,
        Permission.MANAGE_ALL_COMMUNITIES,
        Permission.MANAGE_ALL_EVENTS,
    }

    @classmethod
    def get_permissions(cls, role: UserRole) -> Set[Permission]:
        """
        Get all permissions for a given role

        Args:
            role: User role

        Returns:
            Set of permissions for the role
        """
        role_permission_map = {
            UserRole.CITIZEN: cls.CITIZEN_PERMISSIONS,
            UserRole.VERIFIED_ORGANIZER: cls.VERIFIED_ORGANIZER_PERMISSIONS,
            UserRole.AUTHORITY: cls.AUTHORITY_PERMISSIONS,
            UserRole.ANALYST: cls.ANALYST_PERMISSIONS,
            UserRole.AUTHORITY_ADMIN: cls.AUTHORITY_ADMIN_PERMISSIONS,
        }

        return role_permission_map.get(role, set())

    @classmethod
    def has_permission(cls, role: UserRole, permission: Permission) -> bool:
        """
        Check if a role has a specific permission

        Args:
            role: User role
            permission: Permission to check

        Returns:
            True if role has permission, False otherwise
        """
        role_permissions = cls.get_permissions(role)
        return permission in role_permissions

    @classmethod
    def has_any_permission(cls, role: UserRole, permissions: List[Permission]) -> bool:
        """
        Check if role has any of the specified permissions

        Args:
            role: User role
            permissions: List of permissions to check

        Returns:
            True if role has at least one permission
        """
        role_permissions = cls.get_permissions(role)
        return any(p in role_permissions for p in permissions)

    @classmethod
    def has_all_permissions(cls, role: UserRole, permissions: List[Permission]) -> bool:
        """
        Check if role has all of the specified permissions

        Args:
            role: User role
            permissions: List of permissions to check

        Returns:
            True if role has all permissions
        """
        role_permissions = cls.get_permissions(role)
        return all(p in role_permissions for p in permissions)


class RoleHierarchy:
    """
    Role hierarchy and precedence
    Used for role comparison and access level checks
    """

    # Role levels (higher = more privileged)
    ROLE_LEVELS = {
        UserRole.CITIZEN: 1,
        UserRole.VERIFIED_ORGANIZER: 2,
        UserRole.ANALYST: 3,
        UserRole.AUTHORITY: 4,
        UserRole.AUTHORITY_ADMIN: 5,
    }

    @classmethod
    def get_level(cls, role: UserRole) -> int:
        """Get numeric level for a role"""
        return cls.ROLE_LEVELS.get(role, 0)

    @classmethod
    def is_higher_or_equal(cls, role1: UserRole, role2: UserRole) -> bool:
        """Check if role1 is higher or equal to role2 in hierarchy"""
        return cls.get_level(role1) >= cls.get_level(role2)

    @classmethod
    def is_higher(cls, role1: UserRole, role2: UserRole) -> bool:
        """Check if role1 is strictly higher than role2"""
        return cls.get_level(role1) > cls.get_level(role2)


# Export for easy imports
__all__ = [
    'UserRole',
    'Permission',
    'RolePermissions',
    'RoleHierarchy',
]
