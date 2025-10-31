"""Persistence directory manager and cleanup scheduler."""

from __future__ import annotations

import asyncio
from contextlib import suppress
from datetime import datetime, timezone
import shutil
from pathlib import Path
from typing import Optional

import structlog

from .config import PersistenceConfig


class PersistenceManager:
    """Manage the persistence directory lifecycle and cleanup tasks."""

    def __init__(self, config: PersistenceConfig, logger: Optional[structlog.BoundLogger] = None) -> None:
        self._config = config
        self._logger = (logger or structlog.get_logger(__name__)).bind(component="persistence")
        self._task: asyncio.Task[None] | None = None
        self._stop_event = asyncio.Event()

    @property
    def root(self) -> Path:
        """Return the configured root directory."""

        return self._config.root

    def ensure_base_dir(self) -> None:
        """Ensure that the persistence root directory exists."""

        self._config.root.mkdir(parents=True, exist_ok=True)

    async def start(self) -> None:
        """Start the background cleanup scheduler."""

        self.ensure_base_dir()
        if self._task and not self._task.done():
            return
        self._stop_event = asyncio.Event()
        self._task = asyncio.create_task(self._cleanup_loop(), name="persistence-cleanup")
        self._logger.info("cleanup_scheduler_started", path=str(self._config.root))

    async def shutdown(self) -> None:
        """Stop the cleanup scheduler and wait for completion."""

        if not self._task:
            return
        self._stop_event.set()
        self._task.cancel()
        with suppress(asyncio.CancelledError):
            await self._task
        self._logger.info("cleanup_scheduler_stopped")
        self._task = None

    async def run_cleanup(self) -> None:
        """Execute a single cleanup run removing expired artifacts."""

        await asyncio.to_thread(self._cleanup_once)

    def _cleanup_once(self) -> None:
        cutoff = datetime.now(tz=timezone.utc) - self._config.retention
        for path in self._config.root.iterdir():
            try:
                stat = path.stat()
            except FileNotFoundError:
                continue
            modified = datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc)
            if modified >= cutoff:
                continue
            if path.is_dir():
                shutil.rmtree(path, ignore_errors=True)
            else:
                with suppress(FileNotFoundError):
                    path.unlink()
            self._logger.info("artifact_pruned", target=str(path), modified_at=modified.isoformat())

    async def _cleanup_loop(self) -> None:
        delay = self._config.cleanup_interval.total_seconds()
        try:
            while True:
                try:
                    await self.run_cleanup()
                except Exception:  # pragma: no cover - defensive logging
                    self._logger.exception("cleanup_failed")
                try:
                    await asyncio.wait_for(self._stop_event.wait(), timeout=delay)
                    break
                except asyncio.TimeoutError:
                    continue
        finally:
            await self.run_cleanup()


__all__ = ["PersistenceManager"]
