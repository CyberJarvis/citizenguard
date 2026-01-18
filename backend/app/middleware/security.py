"""
Security Middleware
Security headers, CORS, and authentication dependencies
"""

import logging
from typing import Callable, List
from fastapi import Request, HTTPException, status, Depends, Header
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from starlette.middleware.base import BaseHTTPMiddleware
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.config import settings
from app.database import get_database
from app.utils.jwt import verify_token
from app.models.user import User
from app.models.rbac import UserRole

logger = logging.getLogger(__name__)

# HTTP Bearer security scheme
security = HTTPBearer()


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add security headers to all responses"""

    async def dispatch(self, request: Request, call_next: Callable):
        """Add security headers"""
        response = await call_next(request)

        # Skip CSP for documentation endpoints (Swagger UI, ReDoc)
        skip_csp_paths = ["/docs", "/redoc", "/openapi.json"]
        if request.url.path in skip_csp_paths:
            # Only add basic security headers for docs
            response.headers["X-Content-Type-Options"] = "nosniff"
            return response

        # Security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # HSTS (only in production)
        if settings.is_production:
            response.headers["Strict-Transport-Security"] = (
                "max-age=31536000; includeSubDomains; preload"
            )

        # Content Security Policy (relaxed for development)
        if settings.DEBUG:
            # Development - relaxed CSP for easier debugging
            csp_directives = [
                "default-src 'self'",
                "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://cdn.jsdelivr.net",
                "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net",
                "img-src 'self' data: https:",
                "font-src 'self' data: https:",
                "connect-src 'self' https:",
            ]
        else:
            # Production - strict CSP
            csp_directives = [
                "default-src 'self'",
                "script-src 'self'",
                "style-src 'self'",
                "img-src 'self' data: https:",
                "font-src 'self' data:",
                "connect-src 'self'",
                "frame-ancestors 'none'",
            ]

        response.headers["Content-Security-Policy"] = "; ".join(csp_directives)

        return response


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
            detail="Invalid token: missing user ID",
            headers={"WWW-Authenticate": "Bearer"}
        )

    # Get user from database
    user_data = await db.users.find_one({"user_id": user_id})

    if not user_data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"}
        )

    user = User.from_mongo(user_data)

    # Check if user is active
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive"
        )

    # Check if user is banned
    if user.is_banned:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"User account is banned: {user.ban_reason or 'No reason provided'}"
        )

    return user


def require_role(allowed_roles: List[UserRole]):
    """
    Dependency to require specific user roles

    Args:
        allowed_roles: List of allowed roles

    Returns:
        Dependency function
    """

    async def role_checker(current_user: User = Depends(get_current_user)) -> User:
        """Check if user has required role"""

        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions. Required roles: {[r.value for r in allowed_roles]}"
            )

        return current_user

    return role_checker


# Role-specific dependencies (using new RBAC roles)
require_admin = require_role([UserRole.AUTHORITY_ADMIN])
require_analyst = require_role([UserRole.ANALYST, UserRole.AUTHORITY_ADMIN])
require_authority = require_role([UserRole.AUTHORITY, UserRole.AUTHORITY_ADMIN])
require_any_role = require_role([UserRole.CITIZEN, UserRole.ANALYST, UserRole.AUTHORITY, UserRole.AUTHORITY_ADMIN])


async def get_optional_user(
    authorization: str = Header(None),
    db: AsyncIOMotorDatabase = Depends(get_database)
) -> User | None:
    """
    Get user if authenticated, otherwise return None

    Args:
        authorization: Authorization header
        db: Database connection

    Returns:
        User object if authenticated, None otherwise
    """
    if not authorization or not authorization.startswith("Bearer "):
        return None

    try:
        token = authorization.split(" ")[1]
        payload = verify_token(token, expected_type="access")
        user_id = payload.get("sub")

        if user_id:
            user_data = await db.users.find_one({"user_id": user_id})
            if user_data:
                return User.from_mongo(user_data)

    except (HTTPException, IndexError, KeyError, Exception) as e:
        logger.debug(f"Optional authentication failed: {e}")
        return None

    return None
