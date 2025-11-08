from fastapi import HTTPException, Request
from typing import Dict, Tuple
from datetime import datetime, timedelta, timezone
import asyncio
import logging

logger = logging.getLogger(__name__)


class InMemoryRateLimiter:
    """
    Simple in-memory rate limiter for API endpoints.
    In production, this should be replaced with Redis-based rate limiting.
    """

    def __init__(self):
        # Storage: {key: (request_count, window_start_time)}
        self._storage: Dict[str, Tuple[int, datetime]] = {}
        self._lock = asyncio.Lock()

    async def is_allowed(self, key: str, limit: int, window_seconds: int) -> bool:
        """
        Check if request is allowed based on rate limit.

        Args:
            key: Unique identifier for the rate limit (e.g., API key)
            limit: Maximum number of requests allowed
            window_seconds: Time window in seconds

        Returns:
            True if request is allowed, False otherwise
        """
        async with self._lock:
            now = datetime.now(timezone.utc)

            # Get current count and window start
            if key in self._storage:
                count, window_start = self._storage[key]

                # Check if we need to reset the window
                if now - window_start >= timedelta(seconds=window_seconds):
                    # Reset window
                    self._storage[key] = (1, now)
                    return True
                else:
                    # Within current window
                    if count >= limit:
                        return False
                    else:
                        # Increment count
                        self._storage[key] = (count + 1, window_start)
                        return True
            else:
                # First request for this key
                self._storage[key] = (1, now)
                return True

    async def get_current_usage(self, key: str) -> Tuple[int, datetime]:
        """Get current usage for a key."""
        async with self._lock:
            if key in self._storage:
                return self._storage[key]
            return 0, datetime.now(timezone.utc)

    async def cleanup_expired(self, window_seconds: int):
        """Clean up expired entries to prevent memory leaks."""
        async with self._lock:
            now = datetime.now(timezone.utc)
            expired_keys = [
                key
                for key, (_, window_start) in self._storage.items()
                if now - window_start >= timedelta(seconds=window_seconds)
            ]
            for key in expired_keys:
                del self._storage[key]


# Global rate limiter instance
rate_limiter = InMemoryRateLimiter()


async def check_rate_limit(
    request: Request,
    api_key: str,
    limit: int = 1000,  # requests per window
    window_seconds: int = 3600,  # 1 hour window
):
    """
    Check rate limit for an API key.

    Args:
        request: FastAPI request object
        api_key: API key string
        limit: Maximum requests per window (default: 1000/hour)
        window_seconds: Window duration in seconds (default: 3600 = 1 hour)

    Raises:
        HTTPException: If rate limit is exceeded
    """
    # Use API key as the rate limit key
    rate_limit_key = f"api_key:{api_key}"

    is_allowed = await rate_limiter.is_allowed(
        key=rate_limit_key, limit=limit, window_seconds=window_seconds
    )

    if not is_allowed:
        count, window_start = await rate_limiter.get_current_usage(rate_limit_key)
        reset_time = window_start + timedelta(seconds=window_seconds)

        logger.warning(
            f"Rate limit exceeded for API key {api_key[:20]}... "
            f"({count}/{limit} requests)"
        )

        raise HTTPException(
            status_code=429,
            detail={
                "error": "Rate limit exceeded",
                "limit": limit,
                "window_seconds": window_seconds,
                "reset_time": reset_time.isoformat(),
                "current_usage": count,
            },
            headers={
                "Retry-After": str(
                    int((reset_time - datetime.now(timezone.utc)).total_seconds())
                ),
                "X-RateLimit-Limit": str(limit),
                "X-RateLimit-Remaining": str(max(0, limit - count)),
                "X-RateLimit-Reset": str(int(reset_time.timestamp())),
            },
        )

    # Add rate limit headers to successful responses
    count, window_start = await rate_limiter.get_current_usage(rate_limit_key)
    reset_time = window_start + timedelta(seconds=window_seconds)

    # Store rate limit info in request state for response headers
    request.state.rate_limit_info = {
        "limit": limit,
        "remaining": max(0, limit - count),
        "reset": int(reset_time.timestamp()),
    }


# Background task to clean up expired rate limit entries
async def cleanup_rate_limiter():
    """Background task to clean up expired rate limiter entries."""
    while True:
        try:
            await rate_limiter.cleanup_expired(window_seconds=3600)
            await asyncio.sleep(300)  # Clean up every 5 minutes
        except Exception as e:
            logger.error(f"Error in rate limiter cleanup: {e}")
            await asyncio.sleep(60)  # Wait 1 minute before retrying
