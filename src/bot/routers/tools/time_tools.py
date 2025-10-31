"""Time and date handlers."""

from __future__ import annotations

import datetime as _dt
from html import escape
from typing import Optional
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import dateparser
from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from src.core.utils.time_ import (
    convert_timezone,
    datetime_to_epoch,
    epoch_to_datetime,
    parse_natural_delta,
)

__all__ = ["router"]

router = Router(name="time_tools")


def _format_timedelta(delta: _dt.timedelta) -> str:
    total_seconds = int(delta.total_seconds())
    sign = "-" if total_seconds < 0 else ""
    remaining = abs(total_seconds)
    days, remaining = divmod(remaining, 86400)
    hours, remaining = divmod(remaining, 3600)
    minutes, seconds = divmod(remaining, 60)
    parts: list[str] = []
    if days:
        parts.append(f"{days}d")
    if hours:
        parts.append(f"{hours}h")
    if minutes:
        parts.append(f"{minutes}m")
    if seconds or not parts:
        parts.append(f"{seconds}s")
    return sign + " ".join(parts)


def _parse_datetime(value: str, tz: Optional[str] = None) -> _dt.datetime:
    settings = {"RETURN_AS_TIMEZONE_AWARE": True}
    if tz:
        settings["TIMEZONE"] = tz
        settings["TO_TIMEZONE"] = tz
    parsed = dateparser.parse(value, settings=settings)
    if parsed is None:
        raise ValueError("Unable to parse datetime expression")
    if parsed.tzinfo is None:
        try:
            tzinfo = ZoneInfo(tz) if tz else _dt.timezone.utc
        except ZoneInfoNotFoundError as exc:  # pragma: no cover - defensive
            raise ValueError(f"Unknown timezone: {tz}") from exc
        parsed = parsed.replace(tzinfo=tzinfo)
    return parsed


def _split_payload(message: Message) -> str:
    if not message.text:
        return ""
    parts = message.text.split(maxsplit=1)
    if len(parts) == 1:
        return ""
    return parts[1].strip()


@router.message(Command("epoch_to_datetime"))
async def handle_epoch_to_datetime(message: Message) -> None:
    """Convert an epoch timestamp to a human-readable datetime."""

    payload = _split_payload(message)
    if not payload:
        await message.answer(
            "Usage: /epoch_to_datetime <epoch> [timezone] "
            "(e.g. `/epoch_to_datetime 1700000000 Europe/Berlin`)",
        )
        return
    parts = payload.split()
    try:
        epoch = float(parts[0])
    except (IndexError, ValueError):
        await message.answer("Please provide a valid numeric epoch value.")
        return

    tz = parts[1] if len(parts) > 1 else "UTC"
    try:
        converted = epoch_to_datetime(epoch, tz=tz)
    except ValueError as exc:
        await message.answer(str(exc))
        return

    await message.answer(
        "\n".join(
            [
                "🕒 <b>Epoch to datetime</b>",
                f"Epoch: <code>{epoch}</code>",
                f"Timezone: <code>{escape(tz)}</code>",
                f"Result: <code>{converted.isoformat()}</code>",
            ]
        )
    )


@router.message(Command("datetime_to_epoch"))
async def handle_datetime_to_epoch(message: Message) -> None:
    """Convert a datetime expression into an epoch timestamp."""

    payload = _split_payload(message)
    if not payload:
        await message.answer(
            "Usage: /datetime_to_epoch <datetime>[|timezone] "
            "(e.g. `/datetime_to_epoch 2024-01-01T12:00:00Z`)",
        )
        return

    expression, tz = _parse_expression_with_timezone(payload)
    try:
        dt_value = _parse_datetime(expression, tz)
    except ValueError as exc:
        await message.answer(str(exc))
        return

    epoch = datetime_to_epoch(dt_value)
    await message.answer(
        "\n".join(
            [
                "🕒 <b>Datetime to epoch</b>",
                f"Input: <code>{escape(expression)}</code>",
                f"Timezone: <code>{escape(tz or dt_value.tzname() or 'UTC')}</code>",
                f"Epoch: <code>{epoch:.6f}</code>",
            ]
        )
    )


@router.message(Command("convert_time"))
async def handle_convert_time(message: Message) -> None:
    """Convert a datetime between timezones."""

    payload = _split_payload(message)
    if not payload:
        await message.answer(
            "Usage: /convert_time <datetime>|<target tz>[|<source tz>] "
            "(e.g. `/convert_time 2024-01-01T12:00:00Z|Asia/Tokyo`)",
        )
        return

    try:
        expression, target_tz, source_tz = _parse_convert_payload(payload)
        dt_value = _parse_datetime(expression, source_tz)
        converted = convert_timezone(dt_value, target_tz)
    except ValueError as exc:
        await message.answer(str(exc))
        return

    await message.answer(
        "\n".join(
            [
                "🌍 <b>Timezone conversion</b>",
                f"Input: <code>{escape(expression)}</code>",
                f"From: <code>{escape(source_tz or dt_value.tzname() or 'UTC')}</code>",
                f"To: <code>{escape(target_tz)}</code>",
                f"Result: <code>{converted.isoformat()}</code>",
            ]
        )
    )


@router.message(Command("time_delta"))
async def handle_time_delta(message: Message) -> None:
    """Parse natural language expressions into durations."""

    payload = _split_payload(message)
    if not payload:
        await message.answer(
            "Usage: /time_delta <expression> (e.g. `/time_delta in 90 minutes`)",
        )
        return

    try:
        parsed = parse_natural_delta(payload)
    except ValueError as exc:
        await message.answer(str(exc))
        return

    now = _dt.datetime.now(tz=_dt.timezone.utc)
    future = now + parsed.value
    await message.answer(
        "\n".join(
            [
                "⏱ <b>Parsed duration</b>",
                f"Expression: <code>{escape(payload)}</code>",
                f"Total seconds: <code>{parsed.seconds}</code>",
                f"Normalized: <code>{_format_timedelta(parsed.value)}</code>",
                f"Relative UTC target: <code>{future.isoformat()}</code>",
            ]
        )
    )


def _parse_expression_with_timezone(payload: str) -> tuple[str, Optional[str]]:
    parts = [part.strip() for part in payload.split("|", maxsplit=1)]
    expression = parts[0]
    tz = parts[1] if len(parts) > 1 and parts[1] else None
    return expression, tz


def _parse_convert_payload(payload: str) -> tuple[str, str, Optional[str]]:
    parts = [part.strip() for part in payload.split("|")]
    if len(parts) < 2:
        raise ValueError("Expected datetime and target timezone separated by `|`.")
    expression = parts[0]
    target_tz = parts[1]
    if not target_tz:
        raise ValueError("Target timezone cannot be empty.")
    source_tz = parts[2] if len(parts) > 2 and parts[2] else None
    return expression, target_tz, source_tz
