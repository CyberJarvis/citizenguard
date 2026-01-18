"""
OTP Service
Generate, store, and verify OTPs using Redis
"""

import logging
from typing import Optional
from redis.asyncio import Redis

from app.config import settings
from app.utils.security import generate_otp, constant_time_compare

logger = logging.getLogger(__name__)


class OTPService:
    """OTP management service using Redis"""

    @staticmethod
    async def generate_and_store(
        redis: Redis,
        identifier: str,
        otp_type: str = "login"
    ) -> str:
        """
        Generate and store OTP in Redis

        Args:
            redis: Redis client
            identifier: Email or phone number
            otp_type: Type of OTP (login, signup, reset, etc.)

        Returns:
            Generated OTP
        """
        # Generate OTP
        otp = generate_otp(settings.OTP_LENGTH)

        # Store in Redis with expiry
        key = f"otp:{otp_type}:{identifier}"
        await redis.setex(
            key,
            settings.OTP_EXPIRE_MINUTES * 60,
            otp
        )

        # Initialize attempt counter
        attempts_key = f"otp_attempts:{otp_type}:{identifier}"
        await redis.setex(
            attempts_key,
            settings.OTP_EXPIRE_MINUTES * 60,
            0
        )

        logger.info(f"OTP generated for {identifier} (type: {otp_type})")
        return otp

    @staticmethod
    async def verify(
        redis: Redis,
        identifier: str,
        otp: str,
        otp_type: str = "login"
    ) -> bool:
        """
        Verify OTP

        Args:
            redis: Redis client
            identifier: Email or phone number
            otp: OTP to verify
            otp_type: Type of OTP

        Returns:
            True if OTP is valid, False otherwise
        """
        key = f"otp:{otp_type}:{identifier}"
        attempts_key = f"otp_attempts:{otp_type}:{identifier}"

        # Check attempts
        attempts = await redis.get(attempts_key)
        if attempts and int(attempts) >= settings.OTP_MAX_ATTEMPTS:
            logger.warning(f"OTP max attempts exceeded for {identifier}")
            return False

        # Increment attempts
        await redis.incr(attempts_key)

        # Get stored OTP
        stored_otp = await redis.get(key)

        if not stored_otp:
            logger.warning(f"OTP not found or expired for {identifier}")
            return False

        # Constant-time comparison to prevent timing attacks
        is_valid = constant_time_compare(otp, stored_otp)

        if is_valid:
            # Delete OTP after successful verification
            await redis.delete(key)
            await redis.delete(attempts_key)
            logger.info(f"OTP verified successfully for {identifier}")
        else:
            logger.warning(f"Invalid OTP for {identifier}")

        return is_valid

    @staticmethod
    async def get_remaining_attempts(
        redis: Redis,
        identifier: str,
        otp_type: str = "login"
    ) -> int:
        """
        Get remaining OTP verification attempts

        Args:
            redis: Redis client
            identifier: Email or phone number
            otp_type: Type of OTP

        Returns:
            Number of remaining attempts
        """
        attempts_key = f"otp_attempts:{otp_type}:{identifier}"
        attempts = await redis.get(attempts_key)

        if not attempts:
            return settings.OTP_MAX_ATTEMPTS

        used_attempts = int(attempts)
        return max(0, settings.OTP_MAX_ATTEMPTS - used_attempts)

    @staticmethod
    async def delete_otp(
        redis: Redis,
        identifier: str,
        otp_type: str = "login"
    ):
        """
        Delete OTP from Redis

        Args:
            redis: Redis client
            identifier: Email or phone number
            otp_type: Type of OTP
        """
        key = f"otp:{otp_type}:{identifier}"
        attempts_key = f"otp_attempts:{otp_type}:{identifier}"

        await redis.delete(key)
        await redis.delete(attempts_key)

        logger.info(f"OTP deleted for {identifier}")

    @staticmethod
    async def check_rate_limit(
        redis: Redis,
        identifier: str,
        otp_type: str = "login",
        max_requests: int = 3,
        window_seconds: int = 300
    ) -> tuple[bool, int]:
        """
        Check if OTP generation is rate-limited

        Args:
            redis: Redis client
            identifier: Email or phone number
            otp_type: Type of OTP
            max_requests: Maximum OTP requests in window
            window_seconds: Time window in seconds

        Returns:
            Tuple of (is_allowed, remaining_time_seconds)
        """
        key = f"otp_rate_limit:{otp_type}:{identifier}"

        # Get current count
        count = await redis.get(key)

        if count and int(count) >= max_requests:
            # Get TTL
            ttl = await redis.ttl(key)
            logger.warning(f"OTP rate limit exceeded for {identifier}")
            return False, ttl

        # Increment counter
        pipe = redis.pipeline()
        pipe.incr(key)
        pipe.expire(key, window_seconds)
        await pipe.execute()

        return True, 0
