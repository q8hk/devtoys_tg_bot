"""Persistence helpers for per-user task history."""

from __future__ import annotations

import asyncio
import json
from collections import defaultdict
from pathlib import Path
from typing import Iterable, Sequence

try:
    import redis.asyncio as redis
except ModuleNotFoundError:  # pragma: no cover - optional dependency
    redis = None


class RecentHistoryStorage:
    """Store and retrieve recent tasks per user.

    The storage prefers Redis when a URL is provided and the dependency is
    available; otherwise it falls back to filesystem persistence under the
    configured directory.
    """

    def __init__(
        self,
        base_dir: Path,
        redis_url: str | None = None,
        *,
        max_items: int = 10,
    ) -> None:
        self._base_dir = base_dir
        self._base_dir.mkdir(parents=True, exist_ok=True)
        self._max_items = max_items
        self._locks: dict[int, asyncio.Lock] = defaultdict(asyncio.Lock)
        self._redis_client = self._create_redis_client(redis_url)

    def _create_redis_client(self, redis_url: str | None):
        if not redis_url or redis is None:
            return None
        return redis.from_url(redis_url, encoding="utf-8", decode_responses=True)

    async def close(self) -> None:
        """Close the underlying Redis connection (if any)."""

        if self._redis_client is not None:
            await self._redis_client.close()

    async def add_task(self, user_id: int, description: str) -> None:
        """Record a task description for ``user_id`` keeping the history bounded."""

        if self._redis_client is not None:
            key = self._redis_key(user_id)
            await self._redis_client.lrem(key, 0, description)
            await self._redis_client.lpush(key, description)
            await self._redis_client.ltrim(key, 0, self._max_items - 1)
            return

        async with self._lock_for(user_id):
            history = await self._read_file(user_id)
            if description in history:
                history.remove(description)
            history.insert(0, description)
            del history[self._max_items :]
            await self._write_file(user_id, history)

    async def get_tasks(self, user_id: int) -> list[str]:
        """Return the stored tasks for ``user_id`` in most-recent-first order."""

        if self._redis_client is not None:
            key = self._redis_key(user_id)
            return list(await self._redis_client.lrange(key, 0, self._max_items - 1))

        async with self._lock_for(user_id):
            return await self._read_file(user_id)

    async def replace(self, user_id: int, descriptions: Iterable[str]) -> None:
        """Overwrite ``user_id`` history with ``descriptions`` (bounded)."""

        bounded = list(descriptions)[: self._max_items]
        if self._redis_client is not None:
            key = self._redis_key(user_id)
            if bounded:
                await self._redis_client.delete(key)
                await self._redis_client.lpush(key, *reversed(bounded))
            else:
                await self._redis_client.delete(key)
            return

        async with self._lock_for(user_id):
            if bounded:
                await self._write_file(user_id, bounded)
            else:
                await self._delete_file(user_id)

    async def clear(self, user_id: int) -> None:
        """Remove the stored history for ``user_id``."""

        await self.replace(user_id, [])

    def _redis_key(self, user_id: int) -> str:
        return f"history:{user_id}"

    def _lock_for(self, user_id: int) -> asyncio.Lock:
        return self._locks[user_id]

    async def _read_file(self, user_id: int) -> list[str]:
        path = self._file_path(user_id)
        if not path.exists():
            return []
        return await asyncio.to_thread(self._read_json, path)

    async def _write_file(self, user_id: int, history: Sequence[str]) -> None:
        path = self._file_path(user_id)
        await asyncio.to_thread(self._write_json, path, list(history))

    async def _delete_file(self, user_id: int) -> None:
        path = self._file_path(user_id)
        if path.exists():
            await asyncio.to_thread(path.unlink)

    def _file_path(self, user_id: int) -> Path:
        return self._base_dir / f"{user_id}.json"

    def _read_json(self, path: Path) -> list[str]:
        with path.open(encoding="utf-8") as fp:
            data = json.load(fp)
        if isinstance(data, list):
            return [str(item) for item in data]
        return []

    def _write_json(self, path: Path, data: Sequence[str]) -> None:
        with path.open("w", encoding="utf-8") as fp:
            json.dump(list(data), fp, ensure_ascii=False, indent=2)


__all__ = ["RecentHistoryStorage"]
