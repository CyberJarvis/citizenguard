"""
Security Utilities
ID generation, masking, and other security helpers
"""

import secrets
import hashlib
from datetime import datetime, timezone
from typing import Optional


def generate_user_id() -> str:
    """
    Generate unique user ID

    Returns:
        User ID in format: USR-XXXXXXXXXX
    """
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    random_part = secrets.token_hex(4).upper()
    return f"USR-{timestamp}{random_part}"


def generate_token_id() -> str:
    """
    Generate unique token ID (JTI)

    Returns:
        Token ID (UUID-like)
    """
    return secrets.token_urlsafe(32)


def generate_otp(length: int = 6) -> str:
    """
    Generate numeric OTP

    Args:
        length: OTP length (default: 6)

    Returns:
        Numeric OTP string
    """
    # Generate cryptographically secure random number
    return "".join([str(secrets.randbelow(10)) for _ in range(length)])


def hash_token(token: str) -> str:
    """
    Hash a token for secure storage

    Args:
        token: Token to hash

    Returns:
        SHA256 hash of token
    """
    return hashlib.sha256(token.encode()).hexdigest()


def mask_email(email: str) -> str:
    """
    Mask email address for privacy

    Args:
        email: Email address

    Returns:
        Masked email (e.g., u***@example.com)
    """
    if not email or "@" not in email:
        return email

    local, domain = email.split("@", 1)

    if len(local) <= 2:
        masked_local = local[0] + "*"
    else:
        masked_local = local[0] + "*" * (len(local) - 2) + local[-1]

    return f"{masked_local}@{domain}"


def mask_phone(phone: str) -> str:
    """
    Mask phone number for privacy

    Args:
        phone: Phone number

    Returns:
        Masked phone (e.g., +91******3210)
    """
    if not phone:
        return phone

    if len(phone) <= 6:
        return "*" * len(phone)

    # Show country code and last 4 digits
    if phone.startswith("+"):
        country_code_end = min(3, len(phone) - 4)
        return phone[:country_code_end] + "*" * (len(phone) - country_code_end - 4) + phone[-4:]
    else:
        return "*" * (len(phone) - 4) + phone[-4:]


def generate_session_id() -> str:
    """
    Generate secure session ID

    Returns:
        Session ID
    """
    return secrets.token_urlsafe(32)


def constant_time_compare(a: str, b: str) -> bool:
    """
    Constant-time string comparison to prevent timing attacks

    Args:
        a: First string
        b: Second string

    Returns:
        True if strings match, False otherwise
    """
    return secrets.compare_digest(a.encode(), b.encode())
