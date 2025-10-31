"""Persistent storage helpers for user-provided files."""

from __future__ import annotations

import asyncio
import logging
import hashlib
import mimetypes
import re
import shutil
from contextlib import suppress
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from itertools import count
from pathlib import Path
from collections.abc import AsyncIterable, AsyncIterator, Iterable

import aiofiles

logger = logging.getLogger(__name__)


_SAFE_COMPONENT = re.compile(r"[^A-Za-z0-9._-]")
_SNIFF_BYTES = 1024
_DEFAULT_CHUNK_SIZE = 64 * 1024


@dataclass(slots=True, frozen=True)
class StoredFile:
    """Metadata about a file saved in the persistent storage."""

    user_id: str
    job_id: str
    filename: str
    path: Path
    size: int
    mime_type: str
    created_at: datetime


class StorageManager:
    """Manage persistent storage for user uploads."""

    def __init__(
        self,
        base_dir: Path,
        *,
        max_age: timedelta | None = timedelta(hours=24),
        cleanup_interval: timedelta | None = timedelta(hours=1),
    ) -> None:
        self.base_dir = base_dir
        self.users_dir = self.base_dir / "users"
        self.max_age = max_age
        self.cleanup_interval = cleanup_interval
        self._cleanup_task: asyncio.Task[None] | None = None

    async def startup(self) -> None:
        """Ensure base directories exist and bootstrap cleanup."""

        await asyncio.to_thread(self.users_dir.mkdir, parents=True, exist_ok=True)
        if self.max_age is not None:
            await self.cleanup()
        if self.cleanup_interval is not None and self.max_age is not None:
            self._cleanup_task = asyncio.create_task(self._run_periodic_cleanup())

    async def shutdown(self) -> None:
        """Stop background tasks and flush any pending operations."""

        if self._cleanup_task is None:
            return
        self._cleanup_task.cancel()
        with suppress(asyncio.CancelledError):
            await self._cleanup_task
        self._cleanup_task = None

    async def save_upload(
        self,
        user_id: int | str,
        job_id: str,
        filename: str,
        data_stream: AsyncIterable[bytes] | Iterable[bytes] | bytes,
    ) -> StoredFile:
        """Persist an uploaded file using async streaming."""

        normalized_user = self._normalize_component(str(user_id), fallback="user")
        normalized_job = self._normalize_component(job_id, fallback="job")
        job_dir = await self._ensure_job_dir(normalized_user, normalized_job)
        safe_name = self._sanitize_filename(filename)
        target_name = await asyncio.to_thread(self._unique_filename, job_dir, safe_name)
        path = job_dir / target_name

        total = 0
        first_chunk: bytes = b""
        created_at = datetime.now(timezone.utc)
        async with aiofiles.open(path, "wb") as handle:
            async for chunk in self._iterate_stream(data_stream):
                if not chunk:
                    continue
                if not first_chunk:
                    first_chunk = bytes(chunk[:_SNIFF_BYTES])
                await handle.write(chunk)
                total += len(chunk)

        mime_type = self._detect_mime(path, first_chunk)
        return StoredFile(
            user_id=normalized_user,
            job_id=normalized_job,
            filename=target_name,
            path=path,
            size=total,
            mime_type=mime_type,
            created_at=created_at,
        )

    async def stream_download(
        self, stored_file: StoredFile, *, chunk_size: int = _DEFAULT_CHUNK_SIZE
    ) -> AsyncIterator[bytes]:
        """Yield file bytes using an async iterator suitable for streaming."""

        resolved_base = self.base_dir.resolve()
        resolved_path = stored_file.path.resolve()
        resolved_path.relative_to(resolved_base)

        async with aiofiles.open(resolved_path, "rb") as handle:
            while True:
                chunk = await handle.read(chunk_size)
                if not chunk:
                    break
                yield chunk

    async def remove_job(self, user_id: int | str, job_id: str) -> None:
        """Delete the entire job directory for a user, if it exists."""

        normalized_user = self._normalize_component(str(user_id), fallback="user")
        normalized_job = self._normalize_component(job_id, fallback="job")
        job_dir = self.users_dir / normalized_user / "jobs" / normalized_job
        await asyncio.to_thread(shutil.rmtree, job_dir, True)

    async def cleanup(
        self,
        *,
        now: datetime | None = None,
        max_age: timedelta | None = None,
    ) -> int:
        """Remove job directories older than the configured retention."""

        if max_age is None:
            max_age = self.max_age
        if max_age is None:
            return 0
        if now is None:
            now = datetime.now(timezone.utc)
        threshold = now - max_age
        return await asyncio.to_thread(self._cleanup_sync, threshold)

    async def _ensure_job_dir(self, normalized_user: str, normalized_job: str) -> Path:
        job_dir = self.users_dir / normalized_user / "jobs" / normalized_job
        await asyncio.to_thread(job_dir.mkdir, parents=True, exist_ok=True)
        return job_dir

    async def _run_periodic_cleanup(self) -> None:
        assert self.cleanup_interval is not None
        assert self.max_age is not None
        delay = self.cleanup_interval.total_seconds()
        try:
            while True:
                await asyncio.sleep(delay)
                try:
                    removed = await self.cleanup()
                    if removed:
                        logger.info("Removed expired storage jobs", extra={"removed": removed})
                except Exception:  # pragma: no cover - log unexpected errors
                    logger.exception("Storage cleanup failed")
        except asyncio.CancelledError:  # pragma: no cover - cooperative cancellation
            raise

    def _cleanup_sync(self, threshold: datetime) -> int:
        removed = 0
        if not self.users_dir.exists():
            return removed
        for user_dir in list(self.users_dir.iterdir()):
            if not user_dir.is_dir():
                continue
            jobs_root = user_dir / "jobs"
            if not jobs_root.exists():
                self._prune_if_empty(user_dir)
                continue
            for job_dir in list(jobs_root.iterdir()):
                if not job_dir.is_dir():
                    continue
                if self._job_is_expired(job_dir, threshold):
                    shutil.rmtree(job_dir, ignore_errors=True)
                    removed += 1
            if jobs_root.exists() and not any(jobs_root.iterdir()):
                shutil.rmtree(jobs_root, ignore_errors=True)
            self._prune_if_empty(user_dir)
        return removed

    def _job_is_expired(self, job_dir: Path, threshold: datetime) -> bool:
        latest_mtime = job_dir.stat().st_mtime
        for entry in job_dir.rglob("*"):
            try:
                mtime = entry.stat().st_mtime
            except FileNotFoundError:
                continue
            if mtime > latest_mtime:
                latest_mtime = mtime
        job_time = datetime.fromtimestamp(latest_mtime, tz=timezone.utc)
        return job_time <= threshold

    def _prune_if_empty(self, directory: Path) -> None:
        try:
            next(directory.iterdir())
        except StopIteration:
            shutil.rmtree(directory, ignore_errors=True)
        except FileNotFoundError:
            pass

    def _unique_filename(self, directory: Path, filename: str) -> str:
        candidate = filename
        if not (directory / candidate).exists():
            return candidate
        stem = Path(filename).stem or "file"
        suffix = Path(filename).suffix
        for index in count(1):
            candidate = f"{stem}_{index}{suffix}"
            if not (directory / candidate).exists():
                return candidate

    def _normalize_component(self, component: str, *, fallback: str) -> str:
        trimmed = component.strip()
        cleaned = _SAFE_COMPONENT.sub("_", trimmed)
        if cleaned and not cleaned.startswith("."):
            return cleaned[:255]
        digest = hashlib.sha1(component.encode("utf-8", "ignore")).hexdigest()[:12]
        return f"{fallback}_{digest}"

    def _sanitize_filename(self, filename: str) -> str:
        name = Path(filename).name
        cleaned = _SAFE_COMPONENT.sub("_", name)
        if not cleaned or cleaned.startswith("."):
            cleaned = "file"
        return cleaned[:255]

    async def _iterate_stream(
        self, stream: AsyncIterable[bytes] | Iterable[bytes] | bytes
    ) -> AsyncIterator[bytes]:
        if isinstance(stream, (bytes, bytearray, memoryview)):
            yield bytes(stream)
            return
        if isinstance(stream, AsyncIterable):
            async for chunk in stream:
                yield self._ensure_bytes(chunk)
            return
        for chunk in stream:
            yield self._ensure_bytes(chunk)

    def _ensure_bytes(self, chunk: object) -> bytes:
        if isinstance(chunk, (bytes, bytearray, memoryview)):
            data = bytes(chunk)
            if data:
                return data
            return b""
        msg = f"Stream yielded unsupported type: {type(chunk)!r}"
        raise TypeError(msg)

    def _detect_mime(self, path: Path, first_chunk: bytes) -> str:
        guess = mimetypes.guess_type(path.name)[0]
        sniff = self._guess_mime_from_bytes(first_chunk)
        if sniff and sniff != "application/octet-stream":
            return sniff
        if guess:
            return guess
        if sniff:
            return sniff
        return "application/octet-stream"

    def _guess_mime_from_bytes(self, chunk: bytes) -> str:
        if not chunk:
            return "application/octet-stream"
        signatures = (
            (b"\x89PNG\r\n\x1a\n", "image/png"),
            (b"GIF87a", "image/gif"),
            (b"GIF89a", "image/gif"),
            (b"%PDF-", "application/pdf"),
            (b"PK\x03\x04", "application/zip"),
            (b"\x1f\x8b\x08", "application/gzip"),
            (b"RIFF", "audio/wav"),
            (b"OggS", "application/ogg"),
            (b"ID3", "audio/mpeg"),
            (b"\xff\xd8\xff", "image/jpeg"),
            (b"BM", "image/bmp"),
        )
        for signature, mime in signatures:
            if chunk.startswith(signature):
                return mime
        trimmed = chunk.lstrip()
        if trimmed.startswith((b"{", b"[")):
            return "application/json"
        if trimmed.startswith(b"<?xml") or trimmed.startswith(b"<"):
            return "application/xml"
        if b"\x00" in chunk:
            return "application/octet-stream"
        if self._looks_textual(chunk):
            return "text/plain"
        return "application/octet-stream"

    def _looks_textual(self, chunk: bytes) -> bool:
        text_bytes = set(range(0x20, 0x7F)) | {0x09, 0x0A, 0x0D}
        sample = chunk[:_SNIFF_BYTES]
        return all(byte in text_bytes for byte in sample)
