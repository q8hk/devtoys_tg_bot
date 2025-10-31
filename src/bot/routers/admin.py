"""Admin panel handlers and metrics aggregation."""

from __future__ import annotations

import asyncio
import dataclasses
import html
import inspect
import logging
import math
import os
from collections import OrderedDict
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

logger = logging.getLogger(__name__)


def _parse_admin_ids(raw: str | None) -> set[int]:
    """Parse a comma separated list of administrator identifiers."""

    if not raw:
        return set()
    candidates: list[str] = [piece.strip() for piece in raw.split(",")]
    admin_ids: set[int] = set()
    for piece in candidates:
        if not piece:
            continue
        try:
            admin_ids.add(int(piece))
        except ValueError:
            logger.warning("Ignoring invalid admin id", extra={"value": piece})
    return admin_ids


ADMIN_USER_IDS: set[int] = _parse_admin_ids(os.getenv("ADMINS"))
PERSIST_DIR = Path(os.getenv("PERSIST_DIR", "/data"))


@dataclass(slots=True, frozen=True)
class StorageMetrics:
    """Aggregated persistence statistics."""

    total_users: int
    total_jobs: int
    total_size_bytes: int
    last_job_at: datetime | None
    daily_activity: Mapping[str, int]


@dataclass(slots=True, frozen=True)
class RateLimiterMetrics:
    """Snapshot of the rate limiter health indicators."""

    backend: str = "n/a"
    total_requests: int = 0
    throttled_requests: int = 0
    active_keys: int = 0
    detail: str | None = None


@dataclass(slots=True, frozen=True)
class QueueMetrics:
    """Current job queue insights."""

    backend: str = "n/a"
    pending_jobs: int = 0
    in_progress_jobs: int = 0
    completed_last_hour: int = 0
    workers: int | None = None
    detail: str | None = None


@dataclass(slots=True, frozen=True)
class AdminMetricsSnapshot:
    """Aggregate view used by the /admin dashboard."""

    generated_at: datetime
    storage: StorageMetrics
    rate_limiter: RateLimiterMetrics
    queue: QueueMetrics


class PersistenceMetricsCollector:
    """Collect metrics from the filesystem persistence backend."""

    def __init__(self, root: Path) -> None:
        self._root = root

    async def collect(self) -> StorageMetrics:
        return await asyncio.to_thread(self._collect_sync)

    def _collect_sync(self) -> StorageMetrics:
        users_dir = self._root / "users"
        total_users = 0
        total_jobs = 0
        total_size_bytes = 0
        last_job_at: datetime | None = None
        today = datetime.now(tz=UTC).date()
        day_labels = [today - timedelta(days=offset) for offset in range(6, -1, -1)]
        daily_activity: OrderedDict[str, int] = OrderedDict(
            (day.isoformat(), 0) for day in day_labels
        )

        if not users_dir.exists():
            return StorageMetrics(
                total_users=0,
                total_jobs=0,
                total_size_bytes=0,
                last_job_at=None,
                daily_activity=daily_activity,
            )

        for user_entry in users_dir.iterdir():
            if not user_entry.is_dir():
                continue
            total_users += 1
            jobs_dir = user_entry / "jobs"
            if not jobs_dir.exists():
                continue
            for job_entry in jobs_dir.iterdir():
                if job_entry.is_dir():
                    total_size_bytes += _directory_size(job_entry)
                else:
                    try:
                        total_size_bytes += job_entry.stat().st_size
                    except OSError:
                        continue
                total_jobs += 1
                try:
                    stat = job_entry.stat()
                except OSError:
                    continue
                job_dt = datetime.fromtimestamp(stat.st_mtime, tz=UTC)
                if last_job_at is None or job_dt > last_job_at:
                    last_job_at = job_dt
                job_day = job_dt.date().isoformat()
                if job_day in daily_activity:
                    daily_activity[job_day] += 1

        return StorageMetrics(
            total_users=total_users,
            total_jobs=total_jobs,
            total_size_bytes=total_size_bytes,
            last_job_at=last_job_at,
            daily_activity=daily_activity,
        )


class RateLimiterMetricsCollector:
    """Collect statistics from a rate limiter implementation."""

    @staticmethod
    async def collect(limiter: Any) -> RateLimiterMetrics:
        if limiter is None:
            return RateLimiterMetrics()

        if hasattr(limiter, "get_metrics"):
            raw = limiter.get_metrics()  # type: ignore[call-arg]
        elif hasattr(limiter, "metrics"):
            metrics_attr = limiter.metrics
            raw = metrics_attr() if callable(metrics_attr) else metrics_attr
        else:
            return RateLimiterMetrics(detail=repr(limiter))

        data = await _maybe_await(raw)
        if isinstance(data, Mapping):
            backend = str(data.get("backend", "custom"))
            total_requests = int(data.get("total_requests", 0))
            throttled = int(data.get("throttled_requests", data.get("throttled", 0)))
            active_keys = int(data.get("active_keys", data.get("buckets", 0)))
            detail = None
        else:
            backend = "custom"
            total_requests = 0
            throttled = 0
            active_keys = 0
            detail = repr(data)

        return RateLimiterMetrics(
            backend=backend,
            total_requests=total_requests,
            throttled_requests=throttled,
            active_keys=active_keys,
            detail=detail,
        )


class QueueMetricsCollector:
    """Collect statistics from a background job queue."""

    @staticmethod
    async def collect(queue: Any) -> QueueMetrics:
        if queue is None:
            return QueueMetrics()

        data: Any
        if hasattr(queue, "get_metrics"):
            data = await _maybe_await(queue.get_metrics())
        elif hasattr(queue, "metrics"):
            metrics_attr = queue.metrics
            value = metrics_attr() if callable(metrics_attr) else metrics_attr
            data = await _maybe_await(value)
        else:
            return QueueMetrics(detail=repr(queue))

        if isinstance(data, Mapping):
            backend = str(data.get("backend", "custom"))
            pending = int(data.get("pending_jobs", data.get("pending", 0)))
            in_progress = int(data.get("in_progress_jobs", data.get("in_progress", 0)))
            completed = int(data.get("completed_last_hour", data.get("completed", 0)))
            workers = data.get("workers")
            try:
                workers_value = int(workers) if workers is not None else None
            except (TypeError, ValueError):
                workers_value = None
            detail = None
        else:
            backend = "custom"
            pending = 0
            in_progress = 0
            completed = 0
            workers_value = None
            detail = repr(data)

        return QueueMetrics(
            backend=backend,
            pending_jobs=pending,
            in_progress_jobs=in_progress,
            completed_last_hour=completed,
            workers=workers_value,
            detail=detail,
        )


class AdminMetricsService:
    """Orchestrates metric collectors to build the dashboard snapshot."""

    def __init__(self, persistence_root: Path | None = None) -> None:
        root = persistence_root or PERSIST_DIR
        self._persistence = PersistenceMetricsCollector(root)

    async def snapshot(self, *, rate_limiter: Any, queue: Any) -> AdminMetricsSnapshot:
        storage_task = asyncio.create_task(self._persistence.collect())
        rate_task = asyncio.create_task(RateLimiterMetricsCollector.collect(rate_limiter))
        queue_task = asyncio.create_task(QueueMetricsCollector.collect(queue))
        storage, rate, queue_metrics = await asyncio.gather(storage_task, rate_task, queue_task)
        snapshot = AdminMetricsSnapshot(
            generated_at=datetime.now(tz=UTC),
            storage=storage,
            rate_limiter=rate,
            queue=queue_metrics,
        )
        _log_metrics(snapshot)
        return snapshot


METRICS_SERVICE = AdminMetricsService()


router = Router(name="admin")


@router.message(Command("ping"))
async def handle_ping(message: Message) -> None:
    """Respond to ping health checks."""

    if not _is_authorized(message):
        await message.answer("🚫 Access denied.")
        return

    now = datetime.now(tz=UTC)
    uptime_detail = f"Pong! <code>{now.isoformat()}</code>"
    await message.answer(uptime_detail)


@router.message(Command("admin"))
async def handle_admin_dashboard(message: Message) -> None:
    """Send a formatted admin dashboard overview."""

    if not _is_authorized(message):
        await message.answer("🚫 Access denied.")
        return

    bot = message.bot
    rate_limiter = getattr(bot, "rate_limiter", None)
    queue = getattr(bot, "job_queue", None)
    snapshot = await METRICS_SERVICE.snapshot(rate_limiter=rate_limiter, queue=queue)
    dashboard = _render_dashboard(snapshot)
    await message.answer(dashboard)


def _is_authorized(message: Message) -> bool:
    if not ADMIN_USER_IDS:
        # When no admin IDs are configured, allow access to the command to simplify local testing.
        return True
    user = message.from_user
    return bool(user and user.id in ADMIN_USER_IDS)


def _directory_size(path: Path) -> int:
    total = 0
    try:
        for entry in os.scandir(path):
            try:
                if entry.is_symlink():
                    continue
                if entry.is_dir(follow_symlinks=False):
                    total += _directory_size(Path(entry.path))
                else:
                    total += entry.stat(follow_symlinks=False).st_size
            except OSError:
                continue
    except FileNotFoundError:
        return 0
    return total


async def _maybe_await(value: Any) -> Any:
    if inspect.isawaitable(value):
        return await value
    return value


def _render_dashboard(snapshot: AdminMetricsSnapshot) -> str:
    sections: list[str] = ["<b>Admin dashboard</b>"]
    sections.append(f"Generated at <code>{snapshot.generated_at.isoformat()}</code>")

    storage = snapshot.storage
    storage_lines = ["<b>Storage</b>"]
    storage_lines.append(f"• Users: <b>{storage.total_users}</b>")
    storage_lines.append(f"• Jobs: <b>{storage.total_jobs}</b>")
    storage_lines.append(f"• Size: <b>{_format_bytes(storage.total_size_bytes)}</b>")
    if storage.last_job_at is not None:
        storage_lines.append(f"• Last job: <code>{storage.last_job_at.isoformat()}</code>")
    sections.append("\n".join(storage_lines))

    chart = _render_usage_chart(storage.daily_activity)
    sections.append("<b>Usage (7d)</b>\n<pre>" + chart + "</pre>")

    rate = snapshot.rate_limiter
    rate_lines = ["<b>Rate limiter</b>"]
    rate_lines.append(f"• Backend: <b>{html.escape(rate.backend)}</b>")
    rate_lines.append(f"• Active keys: <b>{rate.active_keys}</b>")
    rate_lines.append(f"• Total requests: <b>{rate.total_requests}</b>")
    rate_lines.append(f"• Throttled: <b>{rate.throttled_requests}</b>")
    if rate.detail:
        rate_lines.append(f"• Detail: <code>{html.escape(rate.detail)}</code>")
    sections.append("\n".join(rate_lines))

    queue = snapshot.queue
    queue_lines = ["<b>Job queue</b>"]
    queue_lines.append(f"• Backend: <b>{html.escape(queue.backend)}</b>")
    queue_lines.append(f"• Pending: <b>{queue.pending_jobs}</b>")
    queue_lines.append(f"• In progress: <b>{queue.in_progress_jobs}</b>")
    queue_lines.append(f"• Completed (1h): <b>{queue.completed_last_hour}</b>")
    if queue.workers is not None:
        queue_lines.append(f"• Workers: <b>{queue.workers}</b>")
    if queue.detail:
        queue_lines.append(f"• Detail: <code>{html.escape(queue.detail)}</code>")
    sections.append("\n".join(queue_lines))

    sections.append("<b>Prometheus</b>\n<pre>" + _render_prometheus_metrics(snapshot) + "</pre>")

    return "\n\n".join(sections)


def _render_usage_chart(activity: Mapping[str, int]) -> str:
    if not activity:
        return "no data"
    max_value = max(activity.values(), default=0)
    if max_value == 0:
        return "no activity"
    bar_width = 30
    lines: list[str] = []
    for day, value in activity.items():
        if value:
            scaled = max(1, math.ceil((value / max_value) * bar_width))
            bar = "█" * scaled
        else:
            bar = ""
        lines.append(f"{day} {bar} {value}")
    return "\n".join(lines)


def _format_bytes(num: int) -> str:
    if num <= 0:
        return "0 B"
    units = ["B", "KiB", "MiB", "GiB", "TiB"]
    power = min(int(math.log(num, 1024)), len(units) - 1)
    value = num / (1024**power)
    return f"{value:.2f} {units[power]}"


def _render_prometheus_metrics(snapshot: AdminMetricsSnapshot) -> str:
    storage = snapshot.storage
    lines = [
        "# HELP devtoys_storage_bytes Total size of persisted jobs in bytes",
        "# TYPE devtoys_storage_bytes gauge",
        f"devtoys_storage_bytes {storage.total_size_bytes}",
        "# HELP devtoys_storage_jobs Total jobs persisted",
        "# TYPE devtoys_storage_jobs gauge",
        f"devtoys_storage_jobs {storage.total_jobs}",
        "# HELP devtoys_storage_users Total users with persisted data",
        "# TYPE devtoys_storage_users gauge",
        f"devtoys_storage_users {storage.total_users}",
    ]
    for day, value in storage.daily_activity.items():
        lines.append(
            f"devtoys_jobs_daily{{day=\"{day}\"}} {value}"
        )

    rate = snapshot.rate_limiter
    lines.extend(
        [
            "# HELP devtoys_rate_limit_requests Total requests observed by the rate limiter",
            "# TYPE devtoys_rate_limit_requests counter",
            f"devtoys_rate_limit_requests{{backend=\"{rate.backend}\"}} {rate.total_requests}",
            "# HELP devtoys_rate_limit_throttled Requests throttled by the rate limiter",
            "# TYPE devtoys_rate_limit_throttled counter",
            f"devtoys_rate_limit_throttled{{backend=\"{rate.backend}\"}} {rate.throttled_requests}",
            "# HELP devtoys_rate_limit_active_keys Active rate limit buckets",
            "# TYPE devtoys_rate_limit_active_keys gauge",
            f"devtoys_rate_limit_active_keys{{backend=\"{rate.backend}\"}} {rate.active_keys}",
        ]
    )

    queue = snapshot.queue
    lines.extend(
        [
            "# HELP devtoys_queue_pending Pending jobs in the queue",
            "# TYPE devtoys_queue_pending gauge",
            f"devtoys_queue_pending{{backend=\"{queue.backend}\"}} {queue.pending_jobs}",
            "# HELP devtoys_queue_in_progress Jobs currently being processed",
            "# TYPE devtoys_queue_in_progress gauge",
            f"devtoys_queue_in_progress{{backend=\"{queue.backend}\"}} {queue.in_progress_jobs}",
            "# HELP devtoys_queue_completed_hour Jobs completed within the last hour",
            "# TYPE devtoys_queue_completed_hour counter",
            (
                "devtoys_queue_completed_hour{backend=\""
                f"{queue.backend}\"}} {queue.completed_last_hour}"
            ),
        ]
    )

    return "\n".join(lines)


def _log_metrics(snapshot: AdminMetricsSnapshot) -> None:
    data = {
        "generated_at": snapshot.generated_at.isoformat(),
        "storage": dataclasses.asdict(snapshot.storage),
        "rate_limiter": dataclasses.asdict(snapshot.rate_limiter),
        "queue": dataclasses.asdict(snapshot.queue),
    }
    logger.info("admin_snapshot", extra={"metrics": data})

