"""Rate limiting utilities."""

from __future__ import annotations

import asyncio
from collections import deque
from dataclasses import dataclass
from time import monotonic
from typing import Deque, Dict


class RateLimitExceededError(RuntimeError):
    """Error raised when a user exceeds the configured rate limit."""


@dataclass(slots=True)
class RateLimiter:
    """In-memory, per-user rate limiter.

    The limiter keeps track of timestamps for each user in the last minute. It is intentionally
    lightweight so it can be swapped with a Redis-backed implementation without changing the
    call sites.
    """

    limit_per_minute: int
    _timestamps: Dict[int, Deque[float]] = None  # type: ignore[assignment]
    _lock: asyncio.Lock = None  # type: ignore[assignment]

    def __post_init__(self) -> None:
        if self.limit_per_minute < 1:
            msg = "Rate limit must be at least 1 request per minute"
            raise ValueError(msg)
        self._timestamps = {}
        self._lock = asyncio.Lock()

    async def check(self, user_id: int) -> None:
        """Ensure the user is within the allowed rate."""

        async with self._lock:
            now = monotonic()
            window = self._timestamps.setdefault(user_id, deque())
            self._prune(window, now)
            if len(window) >= self.limit_per_minute:
                raise RateLimitExceededError(f"Rate limit exceeded for user {user_id}")
            window.append(now)

    def remaining(self, user_id: int) -> int:
        """Return remaining requests for the user in the current minute."""

        now = monotonic()
        window = self._timestamps.get(user_id)
        if window is None:
            return self.limit_per_minute
        self._prune(window, now)
        return max(self.limit_per_minute - len(window), 0)

    def _prune(self, window: Deque[float], now: float) -> None:
        """Remove entries older than 60 seconds from ``window``."""

        cutoff = now - 60
        while window and window[0] < cutoff:
            window.popleft()
