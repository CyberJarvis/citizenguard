"""
Audit Logging Utilities
Log security-critical events to MongoDB
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime, timezone
from fastapi import Request
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.models.user import AuditLog
from app.config import settings

logger = logging.getLogger(__name__)


class AuditLogger:
    """Audit logging for security events"""

    @staticmethod
    async def log(
        db: AsyncIOMotorDatabase,
        action: str,
        user_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        request: Optional[Request] = None,
        success: bool = True,
        error_message: Optional[str] = None
    ):
        """
        Log security event to audit log

        Args:
            db: Database connection
            action: Action performed (e.g., "login", "signup", "password_change")
            user_id: User ID (if authenticated)
            details: Additional details dictionary
            request: FastAPI request object
            success: Whether action was successful
            error_message: Error message if failed
        """
        if not settings.AUDIT_LOG_ENABLED:
            return

        # Extract request metadata
        ip_address = None
        user_agent = None

        if request:
            ip_address = request.client.host if request.client else None

            # Check for forwarded IP (behind proxy)
            forwarded_for = request.headers.get("X-Forwarded-For")
            if forwarded_for:
                ip_address = forwarded_for.split(",")[0].strip()

            user_agent = request.headers.get("User-Agent")

        # Create audit log entry
        audit_entry = AuditLog(
            user_id=user_id,
            action=action,
            details=details or {},
            ip_address=ip_address,
            user_agent=user_agent,
            success=success,
            error_message=error_message,
            timestamp=datetime.now(timezone.utc)
        )

        try:
            # Insert into MongoDB
            await db.audit_logs.insert_one(audit_entry.to_mongo())

            # Log to application logger
            log_message = f"Audit: {action} - User: {user_id or 'N/A'} - Success: {success}"
            if error_message:
                log_message += f" - Error: {error_message}"

            if success:
                logger.info(log_message)
            else:
                logger.warning(log_message)

        except Exception as e:
            logger.error(f"Failed to write audit log: {e}")

    @staticmethod
    async def log_login_attempt(
        db: AsyncIOMotorDatabase,
        identifier: str,
        success: bool,
        request: Request,
        user_id: Optional[str] = None,
        error: Optional[str] = None
    ):
        """Log login attempt"""
        await AuditLogger.log(
            db=db,
            action="login_attempt",
            user_id=user_id,
            details={"identifier": identifier},
            request=request,
            success=success,
            error_message=error
        )

    @staticmethod
    async def log_signup(
        db: AsyncIOMotorDatabase,
        user_id: str,
        identifier: str,
        request: Request
    ):
        """Log user signup"""
        await AuditLogger.log(
            db=db,
            action="signup",
            user_id=user_id,
            details={"identifier": identifier},
            request=request,
            success=True
        )

    @staticmethod
    async def log_otp_sent(
        db: AsyncIOMotorDatabase,
        identifier: str,
        channel: str,
        request: Request
    ):
        """Log OTP sent"""
        await AuditLogger.log(
            db=db,
            action="otp_sent",
            details={"identifier": identifier, "channel": channel},
            request=request,
            success=True
        )

    @staticmethod
    async def log_otp_verified(
        db: AsyncIOMotorDatabase,
        user_id: str,
        identifier: str,
        request: Request,
        success: bool
    ):
        """Log OTP verification"""
        await AuditLogger.log(
            db=db,
            action="otp_verified",
            user_id=user_id,
            details={"identifier": identifier},
            request=request,
            success=success
        )

    @staticmethod
    async def log_token_refresh(
        db: AsyncIOMotorDatabase,
        user_id: str,
        request: Request,
        success: bool,
        error: Optional[str] = None
    ):
        """Log token refresh"""
        await AuditLogger.log(
            db=db,
            action="token_refresh",
            user_id=user_id,
            request=request,
            success=success,
            error_message=error
        )

    @staticmethod
    async def log_logout(
        db: AsyncIOMotorDatabase,
        user_id: str,
        request: Request
    ):
        """Log logout"""
        await AuditLogger.log(
            db=db,
            action="logout",
            user_id=user_id,
            request=request,
            success=True
        )

    @staticmethod
    async def log_password_change(
        db: AsyncIOMotorDatabase,
        user_id: str,
        request: Request,
        success: bool,
        error: Optional[str] = None
    ):
        """Log password change"""
        await AuditLogger.log(
            db=db,
            action="password_change",
            user_id=user_id,
            request=request,
            success=success,
            error_message=error
        )

    @staticmethod
    async def log_oauth_login(
        db: AsyncIOMotorDatabase,
        user_id: str,
        provider: str,
        request: Request,
        is_new_user: bool = False
    ):
        """Log OAuth login"""
        await AuditLogger.log(
            db=db,
            action="oauth_login",
            user_id=user_id,
            details={"provider": provider, "is_new_user": is_new_user},
            request=request,
            success=True
        )


# Simplified helper function for direct audit logging
async def log_audit_event(
    db: AsyncIOMotorDatabase,
    user_id: Optional[str],
    action: str,
    details: Dict[str, Any] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
    success: bool = True,
    error_message: Optional[str] = None
) -> None:
    """
    Log an audit event to the database (simplified interface)

    Args:
        db: Database connection
        user_id: User ID performing the action
        action: Action being performed
        details: Additional details
        ip_address: IP address
        user_agent: User agent string
        success: Whether the action succeeded
        error_message: Error message if failed
    """
    await AuditLogger.log(
        db=db,
        action=action,
        user_id=user_id,
        details=details,
        request=None,
        success=success,
        error_message=error_message
    )
