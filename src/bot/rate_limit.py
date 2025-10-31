"""Rate limiting utilities."""

from __future__ import annotations

import asyncio
import logging
import math
import time
from collections import defaultdict, deque
from dataclasses import dataclass
from typing import Protocol

try:  # pragma: no cover - optional dependency guard
    from redis.asyncio import Redis
except Exception:  # pragma: no cover - redis might be unavailable at runtime
    Redis = None  # type: ignore[assignment]

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class RateLimitStatus:
    """Represents the outcome of a rate limit check."""

    allowed: bool
    remaining: int
    retry_after: int
    limit: int


class RateLimitExceeded(RuntimeError):
    """Raised when a rate limit is exceeded."""

    def __init__(self, status: RateLimitStatus) -> None:
        self.status = status
        super().__init__(f"Rate limit exceeded. Retry in {status.retry_after} seconds")


class RateLimiter(Protocol):
    """Protocol implemented by rate limiter backends."""

    async def hit(self, key: str, limit: int, window: int) -> RateLimitStatus:
        """Register a hit and return the rate limit status."""


class MemoryRateLimiter:
    """A simple in-memory sliding window rate limiter."""

    def __init__(self) -> None:
        self._hits: defaultdict[str, deque[float]] = defaultdict(deque)
        self._lock = asyncio.Lock()

    async def hit(self, key: str, limit: int, window: int) -> RateLimitStatus:
        now = time.monotonic()
        threshold = now - window
        async with self._lock:
            bucket = self._hits[key]
            while bucket and bucket[0] <= threshold:
                bucket.popleft()
            if len(bucket) >= limit:
                retry_after = max(math.ceil(window - (now - bucket[0])), 1)
                status = RateLimitStatus(
                    allowed=False,
                    remaining=0,
                    retry_after=retry_after,
                    limit=limit,
                )
                logger.debug("Rate limit exceeded (memory)", extra={"key": key, "status": status})
                return status
            bucket.append(now)
            remaining = max(limit - len(bucket), 0)
            status = RateLimitStatus(
                allowed=True,
                remaining=remaining,
                retry_after=0,
                limit=limit,
            )
            logger.debug("Rate limit allowed (memory)", extra={"key": key, "status": status})
            return status


class RedisRateLimiter:
    """Redis-based rate limiter using discrete time windows."""

    def __init__(self, redis: Redis, *, prefix: str = "rate-limit") -> None:
        if Redis is None:
            raise RuntimeError("redis package is required for RedisRateLimiter")
        self._redis = redis
        self._prefix = prefix

    def _key(self, key: str, window: int) -> str:
        window_bucket = int(time.time() // window)
        return f"{self._prefix}:{key}:{window_bucket}"

    async def hit(self, key: str, limit: int, window: int) -> RateLimitStatus:
        redis_key = self._key(key, window)
        current = await self._redis.incr(redis_key)
        if current == 1:
            await self._redis.expire(redis_key, window)
        if current > limit:
            ttl = await self._redis.ttl(redis_key)
            retry_after = max(int(ttl), 1) if ttl > 0 else window
            status = RateLimitStatus(
                allowed=False,
                remaining=0,
                retry_after=retry_after,
                limit=limit,
            )
            logger.debug("Rate limit exceeded (redis)", extra={"key": key, "status": status})
            return status
        ttl = await self._redis.ttl(redis_key)
        remaining = max(limit - int(current), 0)
        status = RateLimitStatus(
            allowed=True,
            remaining=remaining,
            retry_after=int(ttl) if ttl > 0 else 0,
            limit=limit,
        )
        logger.debug("Rate limit allowed (redis)", extra={"key": key, "status": status})
        return status


def create_rate_limiter(redis_url: str | None) -> RateLimiter:
    """Create a rate limiter using Redis if available, otherwise memory."""

    if redis_url:
        if Redis is None:
            logger.warning("redis package missing, falling back to memory rate limiter")
        else:
            redis = Redis.from_url(redis_url, encoding="utf-8", decode_responses=False)
            logger.info("Using Redis rate limiter", extra={"redis_url": redis_url})
            return RedisRateLimiter(redis)
    logger.info("Using in-memory rate limiter")
    return MemoryRateLimiter()


__all__ = [
    "RateLimitStatus",
    "RateLimitExceeded",
    "RateLimiter",
    "MemoryRateLimiter",
    "RedisRateLimiter",
    "create_rate_limiter",
]
