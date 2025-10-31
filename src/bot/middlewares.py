"""Custom middlewares for the bot."""

from __future__ import annotations

import asyncio
from collections import defaultdict, deque
import time
from typing import Any, Callable, Awaitable

from aiogram.dispatcher.middlewares.base import BaseMiddleware
import structlog


EventHandler = Callable[[Any, dict[str, Any]], Awaitable[Any]]


class LoggingMiddleware(BaseMiddleware):
    """Log incoming updates and errors in a structured manner."""

    def __init__(self, logger: structlog.BoundLogger | None = None) -> None:
        self._logger = (logger or structlog.get_logger(__name__)).bind(middleware="logging")

    async def __call__(self, handler: EventHandler, event: Any, data: dict[str, Any]) -> Any:
        bound_logger = self._logger.bind(event_type=type(event).__name__)
        bound_logger.info("update_received")
        try:
            result = await handler(event, data)
            bound_logger.info("update_processed")
            return result
        except Exception:
            bound_logger.exception("update_failed")
            raise


class LocalizationMiddleware(BaseMiddleware):
    """Populate the locale for downstream handlers."""

    def __init__(self, default_locale: str = "en") -> None:
        self._default_locale = default_locale

    async def __call__(self, handler: EventHandler, event: Any, data: dict[str, Any]) -> Any:
        locale = getattr(getattr(event, "from_user", None), "language_code", None) or self._default_locale
        data.setdefault("locale", locale)
        return await handler(event, data)


class RateLimitMiddleware(BaseMiddleware):
    """A lightweight in-memory rate limiter per user."""

    def __init__(self, limit_per_minute: int, logger: structlog.BoundLogger | None = None) -> None:
        if limit_per_minute < 1:
            raise ValueError("limit_per_minute must be >= 1")
        self._limit = limit_per_minute
        self._window = 60.0
        self._hits: defaultdict[int, deque[float]] = defaultdict(deque)
        self._lock = asyncio.Lock()
        self._logger = (logger or structlog.get_logger(__name__)).bind(middleware="rate_limit")

    async def __call__(self, handler: EventHandler, event: Any, data: dict[str, Any]) -> Any:
        user = getattr(event, "from_user", None)
        user_id = getattr(user, "id", None)
        if user_id is None:
            return await handler(event, data)

        async with self._lock:
            bucket = self._hits[user_id]
            now = time.monotonic()
            while bucket and now - bucket[0] >= self._window:
                bucket.popleft()
            if len(bucket) >= self._limit:
                allow = False
            else:
                bucket.append(now)
                allow = True

        if not allow:
            self._logger.warning("rate_limit_exceeded", user_id=user_id)
            responder = getattr(event, "answer", None)
            if callable(responder):
                await responder("Too many requests. Please slow down and try again shortly.")
            return None

        try:
            result = await handler(event, data)
            return result
        finally:
            async with self._lock:
                bucket = self._hits.get(user_id)
                if not bucket:
                    return
                now = time.monotonic()
                while bucket and now - bucket[0] >= self._window:
                    bucket.popleft()
                if not bucket:
                    self._hits.pop(user_id, None)


__all__ = ["LoggingMiddleware", "LocalizationMiddleware", "RateLimitMiddleware"]
