"""
JWT Token Utilities
Token generation and validation with refresh token support
"""

from datetime import datetime, timedelta, timezone
from typing import Dict, Any, Optional
from jose import jwt, JWTError
from fastapi import HTTPException, status

from app.config import settings
from app.utils.security import generate_token_id


def create_access_token(
    user_id: str,
    role: str,
    additional_claims: Optional[Dict[str, Any]] = None
) -> str:
    """
    Create JWT access token

    Args:
        user_id: User ID
        role: User role
        additional_claims: Additional claims to include

    Returns:
        JWT token string
    """
    now = datetime.now(timezone.utc)
    expires_delta = timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)

    claims = {
        "sub": user_id,
        "role": role,
        "type": "access",
        "iat": now,
        "exp": now + expires_delta,
        "jti": generate_token_id()
    }

    if additional_claims:
        claims.update(additional_claims)

    encoded_jwt = jwt.encode(
        claims,
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM
    )

    return encoded_jwt


def create_refresh_token(user_id: str) -> tuple[str, str, datetime]:
    """
    Create JWT refresh token

    Args:
        user_id: User ID

    Returns:
        Tuple of (token, token_id, expiry_datetime)
    """
    now = datetime.now(timezone.utc)
    expires_delta = timedelta(days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS)
    expiry = now + expires_delta

    token_id = generate_token_id()

    claims = {
        "sub": user_id,
        "type": "refresh",
        "iat": now,
        "exp": expiry,
        "jti": token_id
    }

    encoded_jwt = jwt.encode(
        claims,
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM
    )

    return encoded_jwt, token_id, expiry


def decode_token(token: str) -> Dict[str, Any]:
    """
    Decode JWT token without verification

    Args:
        token: JWT token string

    Returns:
        Token payload dictionary

    Raises:
        HTTPException: If token is invalid
    """
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
            options={"verify_exp": False}  # Don't verify expiry
        )
        return payload
    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"}
        )


def verify_token(token: str, expected_type: str = "access") -> Dict[str, Any]:
    """
    Verify and decode JWT token

    Args:
        token: JWT token string
        expected_type: Expected token type ('access' or 'refresh')

    Returns:
        Token payload dictionary

    Raises:
        HTTPException: If token is invalid or expired
    """
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM]
        )

        # Check token type
        token_type = payload.get("type")
        if token_type != expected_type:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Invalid token type. Expected {expected_type}, got {token_type}",
                headers={"WWW-Authenticate": "Bearer"}
            )

        return payload

    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"}
        )
    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"}
        )


def get_token_expiry(token: str) -> Optional[datetime]:
    """
    Get token expiration time

    Args:
        token: JWT token string

    Returns:
        Expiration datetime or None if invalid
    """
    try:
        payload = decode_token(token)
        exp = payload.get("exp")
        if exp:
            return datetime.fromtimestamp(exp, tz=timezone.utc)
        return None
    except (JWTError, Exception) as e:
        logger.debug(f"Failed to get token expiration: {e}")
        return None


def is_token_expired(token: str) -> bool:
    """
    Check if token is expired

    Args:
        token: JWT token string

    Returns:
        True if expired, False otherwise
    """
    expiry = get_token_expiry(token)
    if expiry:
        return datetime.now(timezone.utc) > expiry
    return True
