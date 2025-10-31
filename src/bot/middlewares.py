"""Custom middlewares for the bot."""

from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import Awaitable, Callable, MutableMapping
from dataclasses import dataclass
from typing import Any, Protocol

from aiogram import BaseMiddleware
from aiogram.exceptions import CancelHandler, TelegramAPIError
from aiogram.types import TelegramObject

try:  # pragma: no cover - optional dependency guard
    from redis.asyncio import Redis
except Exception:  # pragma: no cover - redis may be unavailable
    Redis = None  # type: ignore[assignment]

from ..core.i18n import I18n, I18nContext
from .rate_limit import RateLimitExceeded, RateLimiter

logger = logging.getLogger(__name__)


class SessionStorage(Protocol):
    """Protocol implemented by storage backends."""

    async def read(self, key: str) -> dict[str, Any]:  # pragma: no cover - protocol signature
        ...

    async def write(self, key: str, data: dict[str, Any]) -> None:  # pragma: no cover
        ...


class MemorySessionStorage:
    """Stores session payloads in memory."""

    def __init__(self) -> None:
        self._data: dict[str, dict[str, Any]] = {}
        self._lock = asyncio.Lock()

    async def read(self, key: str) -> dict[str, Any]:
        async with self._lock:
            return json.loads(json.dumps(self._data.get(key, {})))

    async def write(self, key: str, data: dict[str, Any]) -> None:
        async with self._lock:
            self._data[key] = json.loads(json.dumps(data))


class RedisSessionStorage:
    """Redis-backed session storage."""

    def __init__(self, redis: Redis, *, prefix: str = "session") -> None:
        if Redis is None:
            raise RuntimeError("redis package is required for RedisSessionStorage")
        self._redis = redis
        self._prefix = prefix

    def _key(self, key: str) -> str:
        return f"{self._prefix}:{key}"

    async def read(self, key: str) -> dict[str, Any]:
        raw = await self._redis.get(self._key(key))
        if not raw:
            return {}
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            logger.warning("Failed to decode session JSON", extra={"key": key})
            return {}

    async def write(self, key: str, data: dict[str, Any]) -> None:
        await self._redis.set(self._key(key), json.dumps(data))


@dataclass(slots=True)
class SessionData(MutableMapping[str, Any]):
    """Mutable mapping that tracks modifications and persists on commit."""

    storage: SessionStorage
    key: str
    _data: dict[str, Any]
    _dirty: bool = False

    # MutableMapping implementation -------------------------------------------------
    def __getitem__(self, item: str) -> Any:
        return self._data[item]

    def __setitem__(self, key: str, value: Any) -> None:
        self._data[key] = value
        self._dirty = True

    def __delitem__(self, key: str) -> None:
        del self._data[key]
        self._dirty = True

    def __iter__(self):  # type: ignore[override]
        return iter(self._data)

    def __len__(self) -> int:
        return len(self._data)

    def clear(self) -> None:  # type: ignore[override]
        self._data.clear()
        self._dirty = True

    # Helpers -----------------------------------------------------------------------
    @property
    def dirty(self) -> bool:
        return self._dirty

    async def commit(self) -> None:
        if self._dirty:
            await self.storage.write(self.key, self._data)
            self._dirty = False

    def copy(self) -> dict[str, Any]:  # pragma: no cover - provided for convenience
        return dict(self._data)


class SessionMiddleware(BaseMiddleware):
    """Attach per-user session data to handler context."""

    def __init__(self, storage: SessionStorage) -> None:
        super().__init__()
        self._storage = storage

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        user = data.get("event_from_user")
        if not user or not user.id:
            return await handler(event, data)
        key = str(user.id)
        payload = await self._storage.read(key)
        session = SessionData(storage=self._storage, key=key, _data=payload)
        data["session"] = session
        try:
            return await handler(event, data)
        finally:
            await session.commit()


class I18nMiddleware(BaseMiddleware):
    """Bind a translation context to the handler pipeline."""

    def __init__(self, i18n: I18n, *, session_key: str = "locale") -> None:
        super().__init__()
        self._i18n = i18n
        self._session_key = session_key

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        session_obj = data.get("session")
        session = session_obj if isinstance(session_obj, SessionData) else None
        stored_locale = session.get(self._session_key) if session else None
        user = data.get("event_from_user")
        candidate_locale = stored_locale
        if not candidate_locale and user and user.language_code:
            candidate_locale = user.language_code
        resolved_locale = self._i18n.resolve_locale(candidate_locale)
        if session is not None and session.get(self._session_key) != resolved_locale:
            session[self._session_key] = resolved_locale
        context = self._i18n.get_context(resolved_locale)
        data["i18n"] = context
        data["gettext"] = context.gettext
        return await handler(event, data)


class RateLimitMiddleware(BaseMiddleware):
    """Enforce per-user rate limits."""

    def __init__(
        self,
        limiter: RateLimiter,
        *,
        limit: int,
        window: int,
        key_builder: Callable[[TelegramObject, dict[str, Any]], str] | None = None,
    ) -> None:
        super().__init__()
        self._limiter = limiter
        self._limit = limit
        self._window = window
        self._key_builder = key_builder

    def _default_key(self, data: dict[str, Any]) -> str | None:
        user = data.get("event_from_user")
        if user and user.id:
            return str(user.id)
        chat = data.get("event_chat")
        if chat and chat.id:
            return str(chat.id)
        return None

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        key = self._key_builder(event, data) if self._key_builder else self._default_key(data)
        if not key:
            return await handler(event, data)
        status = await self._limiter.hit(key, self._limit, self._window)
        data["rate_limit_status"] = status
        if not status.allowed:
            raise RateLimitExceeded(status)
        return await handler(event, data)


class ErrorHandlingMiddleware(BaseMiddleware):
    """Catch exceptions, log them, and notify the user."""

    def __init__(self, *, logger_: logging.Logger | None = None) -> None:
        super().__init__()
        self._logger = logger_ or logging.getLogger("bot.errors")

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        try:
            return await handler(event, data)
        except RateLimitExceeded as exc:
            await self._handle_rate_limit(exc, data)
            raise CancelHandler() from exc
        except CancelHandler:
            raise
        except Exception as exc:  # pragma: no cover - defensive logging
            await self._handle_exception(exc, data)
            raise CancelHandler() from exc

    async def _handle_rate_limit(self, exc: RateLimitExceeded, data: dict[str, Any]) -> None:
        status = exc.status
        self._logger.info(
            "Rate limit exceeded",
            extra={"retry_after": status.retry_after, "limit": status.limit},
        )
        await self._safe_notify(
            data,
            "errors.rate_limited",
            default=f"Too many requests. Please retry in {status.retry_after} seconds.",
            retry_after=status.retry_after,
        )

    async def _handle_exception(self, exc: Exception, data: dict[str, Any]) -> None:
        self._logger.exception("Unhandled error in handler", exc_info=exc)
        await self._safe_notify(
            data,
            "errors.internal",
            default="Sorry, something went wrong. Please try again later.",
        )

    async def _safe_notify(
        self,
        data: dict[str, Any],
        message_key: str,
        *,
        default: str,
        **kwargs: Any,
    ) -> None:
        bot = data.get("bot")
        user = data.get("event_from_user")
        if not bot or not user or not user.id:
            return
        i18n: I18nContext | None = data.get("i18n")
        if i18n is not None:
            text = i18n.gettext(message_key, **kwargs)
        else:
            text = default.format(**kwargs) if kwargs else default
        try:
            await bot.send_message(user.id, text)
        except TelegramAPIError:
            self._logger.warning("Failed to deliver error message", exc_info=True)


def create_session_storage(redis_url: str | None) -> SessionStorage:
    """Create session storage with Redis fallback."""

    if redis_url and Redis is not None:
        redis = Redis.from_url(redis_url, encoding="utf-8", decode_responses=False)
        logger.info("Using Redis session storage", extra={"redis_url": redis_url})
        return RedisSessionStorage(redis)
    logger.info("Using in-memory session storage")
    return MemorySessionStorage()


__all__ = [
    "SessionData",
    "SessionMiddleware",
    "I18nMiddleware",
    "RateLimitMiddleware",
    "ErrorHandlingMiddleware",
    "create_session_storage",
]
