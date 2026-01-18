"""
Password Hashing Utilities
Secure password hashing with bcrypt
"""

import hashlib
from passlib.context import CryptContext

# Password context with bcrypt (12 rounds for security)
pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
    bcrypt__rounds=12
)


def _process_password(password: str) -> bytes:
    """
    Process password to handle bcrypt's 72-byte limitation.
    Uses SHA256 to ensure any length password can be safely hashed.

    Args:
        password: Plain text password

    Returns:
        Processed password as bytes (always <= 72 bytes)
    """
    # Convert password to UTF-8 bytes
    password_bytes = password.encode('utf-8')

    # If password is within bcrypt's limit, use it directly
    if len(password_bytes) <= 72:
        return password_bytes

    # For longer passwords, use SHA256 hash (always 64 hex chars = 64 bytes)
    # This ensures consistent hashing regardless of password length
    password_hash = hashlib.sha256(password_bytes).hexdigest()
    return password_hash.encode('utf-8')


def hash_password(password: str) -> str:
    """
    Hash a password using bcrypt

    Args:
        password: Plain text password

    Returns:
        Hashed password string
    """
    processed = _process_password(password)
    return pwd_context.hash(processed.decode('utf-8'))


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a password against its hash

    Args:
        plain_password: Plain text password to verify
        hashed_password: Hashed password from database

    Returns:
        True if password matches, False otherwise
    """
    try:
        processed = _process_password(plain_password)
        return pwd_context.verify(processed.decode('utf-8'), hashed_password)
    except Exception as e:
        # Log error but don't expose details
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Password verification error: {str(e)}")
        return False


def needs_rehash(hashed_password: str) -> bool:
    """
    Check if password hash needs to be updated

    Args:
        hashed_password: Hashed password from database

    Returns:
        True if hash needs update (algorithm/rounds changed)
    """
    return pwd_context.needs_update(hashed_password)
