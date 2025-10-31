from __future__ import annotations

import os
from collections.abc import AsyncIterator
from datetime import datetime, timedelta, timezone

import pytest

from src.bot.storage import StorageManager


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.mark.anyio
async def test_stream_upload_and_download(tmp_path) -> None:
    manager = StorageManager(tmp_path, cleanup_interval=None)
    await manager.startup()
    try:
        async def generator() -> AsyncIterator[bytes]:
            yield b"hello world"

        stored = await manager.save_upload(123, "job-1", "greeting.txt", generator())
        assert stored.size == len(b"hello world")
        assert stored.mime_type == "text/plain"
        chunks: list[bytes] = []
        async for part in manager.stream_download(stored, chunk_size=4):
            chunks.append(part)
        assert b"".join(chunks) == b"hello world"
    finally:
        await manager.shutdown()


@pytest.mark.anyio
async def test_cleanup_removes_old_jobs(tmp_path) -> None:
    manager = StorageManager(tmp_path, cleanup_interval=None)
    await manager.startup()
    try:
        stored = await manager.save_upload(1, "ancient", "data.bin", [b"data"])
        old_time = (datetime.now(timezone.utc) - timedelta(days=2)).timestamp()
        os.utime(stored.path, (old_time, old_time))
        os.utime(stored.path.parent, (old_time, old_time))

        removed = await manager.cleanup(now=datetime.now(timezone.utc))
        assert removed == 1
        assert not stored.path.exists()
    finally:
        await manager.shutdown()


@pytest.mark.anyio
async def test_sanitises_components(tmp_path) -> None:
    manager = StorageManager(tmp_path, cleanup_interval=None)
    await manager.startup()
    try:
        stored = await manager.save_upload(" user  ", "../strange", "../payload.dat", [b"42"])

        base_users = tmp_path / "users"
        assert stored.path.is_file()
        assert stored.path.parent == base_users / stored.user_id / "jobs" / stored.job_id
        assert not stored.filename.startswith(".")
    finally:
        await manager.shutdown()
