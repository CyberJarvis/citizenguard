"""
RBAC Middleware & Dependencies
Role-based and permission-based access control for FastAPI
"""

import logging
from typing import List, Optional, Callable
from functools import wraps
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.database import get_database
from app.utils.jwt import verify_token
from app.models.user import User
from app.models.rbac import UserRole, Permission, RolePermissions, RoleHierarchy

logger = logging.getLogger(__name__)

# HTTP Bearer security scheme
security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncIOMotorDatabase = Depends(get_database)
) -> User:
    """
    Get current authenticated user from JWT token

    Args:
        credentials: HTTP Bearer credentials
        db: Database connection

    Returns:
        User object

    Raises:
        HTTPException: If token is invalid or user not found
    """
    token = credentials.credentials

    # Verify token
    payload = verify_token(token, expected_type="access")
    user_id = payload.get("sub")

    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token: missing user ID"
        )

    # Get user from database
    user_doc = await db.users.find_one({"user_id": user_id})

    if not user_doc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )

    user = User.from_mongo(user_doc)

    # Check if user is active
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is disabled"
        )

    # Check if user is banned
    if user.is_banned:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Account is banned: {user.ban_reason or 'Policy violation'}"
        )

    return user


# Optional bearer security - won't fail if no token provided
optional_security = HTTPBearer(auto_error=False)


async def get_optional_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(optional_security),
    db: AsyncIOMotorDatabase = Depends(get_database)
) -> Optional[User]:
    """
    Get current authenticated user if token is provided, otherwise return None.
    Useful for endpoints that work for both authenticated and anonymous users.

    Args:
        credentials: HTTP Bearer credentials (optional)
        db: Database connection

    Returns:
        User object if authenticated, None otherwise
    """
    if credentials is None:
        return None

    try:
        token = credentials.credentials

        # Verify token
        payload = verify_token(token, expected_type="access")
        user_id = payload.get("sub")

        if not user_id:
            return None

        # Get user from database
        user_doc = await db.users.find_one({"user_id": user_id})

        if not user_doc:
            return None

        user = User.from_mongo(user_doc)

        # Check if user is active and not banned
        if not user.is_active or user.is_banned:
            return None

        return user
    except Exception:
        # Any error means no valid user
        return None


async def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    Get current active user (not banned, not disabled)
    Alias for get_current_user for clarity
    """
    return current_user


def require_role(allowed_roles: List[UserRole]):
    """
    Dependency to require specific roles

    Usage:
        @app.get("/admin/dashboard", dependencies=[Depends(require_role([UserRole.AUTHORITY_ADMIN]))])
        async def admin_dashboard():
            ...

    Args:
        allowed_roles: List of roles that are allowed

    Returns:
        Dependency function
    """
    async def role_checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient privileges. Required roles: {[r.value for r in allowed_roles]}"
            )
        return current_user

    return Depends(role_checker)


def require_permission(required_permissions: List[Permission]):
    """
    Dependency to require specific permissions

    Usage:
        @app.get("/reports/verify", dependencies=[Depends(require_permission([Permission.VERIFY_REPORT]))])
        async def verify_report():
            ...

    Args:
        required_permissions: List of permissions that are required

    Returns:
        Dependency function
    """
    async def permission_checker(current_user: User = Depends(get_current_user)) -> User:
        # Check if user has all required permissions
        if not RolePermissions.has_all_permissions(current_user.role, required_permissions):
            missing_perms = [
                p.value for p in required_permissions
                if not RolePermissions.has_permission(current_user.role, p)
            ]
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Missing required permissions: {missing_perms}"
            )
        return current_user

    return Depends(permission_checker)


def require_any_permission(permissions: List[Permission]):
    """
    Dependency to require at least one of the specified permissions

    Args:
        permissions: List of permissions (user needs at least one)

    Returns:
        Dependency function
    """
    async def permission_checker(current_user: User = Depends(get_current_user)) -> User:
        if not RolePermissions.has_any_permission(current_user.role, permissions):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient privileges. Need one of: {[p.value for p in permissions]}"
            )
        return current_user

    return Depends(permission_checker)


def require_role_or_higher(minimum_role: UserRole):
    """
    Dependency to require a minimum role level in hierarchy

    Args:
        minimum_role: Minimum required role

    Returns:
        Dependency function
    """
    async def role_hierarchy_checker(current_user: User = Depends(get_current_user)) -> User:
        if not RoleHierarchy.is_higher_or_equal(current_user.role, minimum_role):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient privileges. Minimum role required: {minimum_role.value}"
            )
        return current_user

    return Depends(role_hierarchy_checker)


# Convenience dependencies for common role checks

async def require_citizen(current_user: User = Depends(get_current_user)) -> User:
    """Require citizen role or higher"""
    return current_user  # All authenticated users are at least citizens


def _normalize_role(role) -> str:
    """Normalize role to lowercase string for comparison"""
    if isinstance(role, UserRole):
        return role.value.lower()
    elif isinstance(role, str):
        return role.lower()
    return str(role).lower()


async def require_analyst(current_user: User = Depends(get_current_user)) -> User:
    """Require analyst role or higher (analyst, authority, authority_admin)"""
    allowed_roles = ['analyst', 'authority', 'authority_admin']
    user_role = _normalize_role(current_user.role)

    if user_role not in allowed_roles:
        logger.warning(f"Access denied for user {current_user.user_id}: role '{current_user.role}' not in {allowed_roles}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Analyst, Authority, or Admin role required. Your role: {current_user.role}"
        )
    return current_user


async def require_authority(current_user: User = Depends(get_current_user)) -> User:
    """Require authority role or higher (authority, authority_admin)"""
    allowed_roles = ['authority', 'authority_admin']
    user_role = _normalize_role(current_user.role)

    if user_role not in allowed_roles:
        logger.warning(f"Access denied for user {current_user.user_id}: role '{current_user.role}' not in {allowed_roles}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Authority or Admin role required. Your role: {current_user.role}"
        )
    return current_user


async def require_analyst_or_authority(current_user: User = Depends(get_current_user)) -> User:
    """
    Require analyst or authority role.
    Used for V2 hybrid verification endpoints where both analysts and
    authorities have full verification privileges.
    """
    allowed_roles = ['analyst', 'authority', 'authority_admin']
    user_role = _normalize_role(current_user.role)

    if user_role not in allowed_roles:
        logger.warning(f"Access denied for user {current_user.user_id}: role '{current_user.role}' not in {allowed_roles}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Analyst, Authority, or Admin role required. Your role: {current_user.role}"
        )
    return current_user


async def require_admin(current_user: User = Depends(get_current_user)) -> User:
    """Require authority admin role"""
    user_role = _normalize_role(current_user.role)

    if user_role != 'authority_admin':
        logger.warning(f"Access denied for user {current_user.user_id}: role '{current_user.role}' != authority_admin")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Authority Admin role required. Your role: {current_user.role}"
        )
    return current_user


async def require_organizer(current_user: User = Depends(get_current_user)) -> User:
    """Require verified organizer role or higher"""
    allowed_roles = [
        UserRole.VERIFIED_ORGANIZER,
        UserRole.AUTHORITY,
        UserRole.AUTHORITY_ADMIN
    ]
    if current_user.role not in allowed_roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Verified Organizer, Authority, or Admin role required. Apply to become an organizer if eligible."
        )
    return current_user


def has_permission(user: User, permission: Permission) -> bool:
    """
    Check if user has a specific permission
    Utility function for use in route handlers

    Args:
        user: User object
        permission: Permission to check

    Returns:
        True if user has permission
    """
    return RolePermissions.has_permission(user.role, permission)


def check_permission(user: User, permission: Permission) -> None:
    """
    Check if user has permission, raise exception if not

    Args:
        user: User object
        permission: Permission to check

    Raises:
        HTTPException: If user lacks permission
    """
    if not has_permission(user, permission):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Missing required permission: {permission.value}"
        )


def filter_pii_fields(data: dict, user: User) -> dict:
    """
    Filter out PII fields based on user permissions
    Used for Analysts who should not see personal information

    Args:
        data: Data dictionary (e.g., user profile, report)
        user: Current user

    Returns:
        Filtered data dictionary
    """
    # If user has permission to view PII, return all data
    if has_permission(user, Permission.VIEW_USER_PII):
        return data

    # PII fields to remove for users without permission
    pii_fields = [
        'name',
        'email',
        'phone',
        'address',
        'full_name',
        'user_name',
        'contact',
        'personal_info',
        'profile_picture',
    ]

    # Create a copy and remove PII fields
    filtered_data = data.copy()
    for field in pii_fields:
        filtered_data.pop(field, None)

    # Replace with anonymized values
    filtered_data['reporter_id'] = data.get('user_id', 'ANONYMOUS')
    filtered_data['reporter_type'] = 'VERIFIED_CITIZEN'  # Generic label

    return filtered_data


# Export commonly used dependencies
__all__ = [
    'get_current_user',
    'get_current_active_user',
    'get_optional_current_user',
    'require_role',
    'require_permission',
    'require_any_permission',
    'require_role_or_higher',
    'require_citizen',
    'require_analyst',
    'require_analyst_or_authority',
    'require_authority',
    'require_admin',
    'require_organizer',
    'has_permission',
    'check_permission',
    'filter_pii_fields',
]
