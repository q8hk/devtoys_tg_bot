"""Time and date utilities."""

from __future__ import annotations

import datetime as _dt
import re
from dataclasses import dataclass
from typing import Any

import pendulum

__all__ = [
    "ParsedDuration",
    "epoch_to_datetime",
    "datetime_to_epoch",
    "convert_timezone",
    "add_duration",
    "parse_natural_delta",
]


@dataclass(slots=True)
class ParsedDuration:
    value: pendulum.Duration
    seconds: int


def epoch_to_datetime(epoch: float, tz: str = "UTC") -> _dt.datetime:
    """Convert an epoch timestamp to a timezone aware datetime."""

    return pendulum.from_timestamp(epoch, tz=tz)


def datetime_to_epoch(dt: _dt.datetime) -> float:
    """Return the epoch for ``dt``."""

    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=_dt.UTC)
    return dt.timestamp()


def convert_timezone(dt: _dt.datetime, tz: str) -> _dt.datetime:
    """Convert ``dt`` to ``tz``."""

    pendulum_dt = pendulum.instance(dt)
    return pendulum_dt.in_timezone(tz)


def add_duration(dt: _dt.datetime, **kwargs: Any) -> _dt.datetime:
    """Add a duration described by ``kwargs`` to ``dt``."""

    pendulum_dt = pendulum.instance(dt)
    return pendulum_dt.add(**kwargs)


def parse_natural_delta(value: str) -> ParsedDuration:
    """Parse simple natural language durations (e.g. ``"in 2h"``)."""

    text = value.strip()
    try:
        parsed = pendulum.parse(text, strict=False)
    except pendulum.parsing.exceptions.ParserError:
        pattern = re.compile(
            r"(?:in\s+)?([+-]?\d+(?:\.\d+)?)\s*(second|minute|hour|day|week|month|year)s?",
            re.I,
        )
        match = pattern.fullmatch(text)
        if not match:
            raise ValueError(f"Unsupported duration expression: {value}") from None
        amount = float(match.group(1))
        unit = match.group(2).lower() + "s"
        duration = pendulum.duration(**{unit: amount})
    else:
        if isinstance(parsed, pendulum.DateTime):
            now = pendulum.now(parsed.tzinfo)
            duration = parsed - now
        else:
            duration = parsed
    return ParsedDuration(value=duration, seconds=int(duration.total_seconds()))
