"""
Rate Limiting Middleware
Redis-based rate limiting
"""

import logging
from typing import Callable
from fastapi import Request, HTTPException, status, Depends
from starlette.middleware.base import BaseHTTPMiddleware
from redis.asyncio import Redis

from app.config import settings
from app.database import get_redis

logger = logging.getLogger(__name__)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Rate limiting middleware using Redis
    Implements sliding window rate limiting
    """

    async def dispatch(self, request: Request, call_next: Callable):
        """Process request with rate limiting"""

        # Skip rate limiting if disabled
        if not settings.RATE_LIMIT_ENABLED:
            return await call_next(request)

        # Skip for certain paths (health checks, docs)
        skip_paths = ["/docs", "/redoc", "/openapi.json", "/health"]
        if request.url.path in skip_paths:
            return await call_next(request)

        try:
            # Get identifier (IP address or user ID from token)
            identifier = self._get_identifier(request)

            # Get Redis client - skip rate limiting if Redis not available
            redis = await get_redis()

            # Check rate limit
            is_allowed, remaining = await self._check_rate_limit(
                redis,
                identifier,
                request.url.path
            )

            if not is_allowed:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Rate limit exceeded. Please try again later.",
                    headers={"Retry-After": str(remaining)}
                )

            # Process request
            response = await call_next(request)

            # Add rate limit headers
            response.headers["X-RateLimit-Limit"] = str(
                settings.RATE_LIMIT_MAX_REQUESTS_PER_WINDOW
            )

            return response

        except RuntimeError as e:
            # Redis not connected - skip rate limiting
            if "not connected" in str(e).lower():
                logger.debug("Rate limiting skipped - Redis not connected")
                return await call_next(request)
            raise

    def _get_identifier(self, request: Request) -> str:
        """Get identifier for rate limiting (IP or user ID)"""

        # Try to get user ID from token if authenticated
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            try:
                from app.utils.jwt import decode_token
                token = auth_header.split(" ")[1]
                payload = decode_token(token)
                user_id = payload.get("sub")
                if user_id:
                    return f"user:{user_id}"
            except (IndexError, KeyError, Exception):
                # Fall back to IP if token is invalid
                pass

        # Fall back to IP address
        client_ip = request.client.host if request.client else "unknown"

        # Check for forwarded IP (behind proxy)
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            client_ip = forwarded_for.split(",")[0].strip()

        return f"ip:{client_ip}"

    async def _check_rate_limit(
        self,
        redis: Redis,
        identifier: str,
        path: str
    ) -> tuple[bool, int]:
        """
        Check rate limit using sliding window

        Returns:
            Tuple of (is_allowed, remaining_time_seconds)
        """
        key = f"rate_limit:{identifier}:{path}"

        # Get current count
        count = await redis.get(key)

        if count and int(count) >= settings.RATE_LIMIT_MAX_REQUESTS_PER_WINDOW:
            # Get remaining TTL
            ttl = await redis.ttl(key)
            return False, ttl

        # Increment counter
        pipe = redis.pipeline()
        pipe.incr(key)
        pipe.expire(key, settings.RATE_LIMIT_WINDOW_SECONDS)
        await pipe.execute()

        return True, 0


async def rate_limit_dependency(
    request: Request,
    max_requests: int = 10,
    window_seconds: int = 60
) -> None:
    """
    Dependency for endpoint-specific rate limiting

    Args:
        request: FastAPI request
        max_requests: Maximum requests allowed
        window_seconds: Time window in seconds

    Raises:
        HTTPException: If rate limit exceeded
    """

    if not settings.RATE_LIMIT_ENABLED:
        return

    try:
        # Get Redis client
        redis = await get_redis()

        # Get identifier
        client_ip = request.client.host if request.client else "unknown"
        identifier = f"ip:{client_ip}"

        # Check auth token for user ID
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            try:
                from app.utils.jwt import decode_token
                token = auth_header.split(" ")[1]
                payload = decode_token(token)
                user_id = payload.get("sub")
                if user_id:
                    identifier = f"user:{user_id}"
            except (IndexError, KeyError, Exception):
                # Fall back to IP if token is invalid
                pass

        # Rate limit key
        endpoint = request.url.path
        key = f"rate_limit:custom:{identifier}:{endpoint}"

        # Check limit
        count = await redis.get(key)

        if count and int(count) >= max_requests:
            ttl = await redis.ttl(key)
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Rate limit exceeded. Try again in {ttl} seconds.",
                headers={"Retry-After": str(ttl)}
            )

        # Increment
        pipe = redis.pipeline()
        pipe.incr(key)
        pipe.expire(key, window_seconds)
        await pipe.execute()

    except RuntimeError as e:
        # Redis not connected - skip rate limiting
        if "not connected" in str(e).lower():
            logger.debug("Rate limiting skipped - Redis not connected")
            return
        raise
