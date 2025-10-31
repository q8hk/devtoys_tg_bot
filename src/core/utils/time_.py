"""Time and date utilities."""

from __future__ import annotations

import datetime as _dt
import re
from dataclasses import dataclass
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import dateparser
from dateutil.relativedelta import relativedelta

__all__ = [
    "ParsedDuration",
    "epoch_to_datetime",
    "datetime_to_epoch",
    "convert_timezone",
    "add_duration",
    "parse_natural_delta",
]

_RELATIVE_SETTINGS = {
    "PREFER_DATES_FROM": "future",
    "RETURN_AS_TIMEZONE_AWARE": True,
}

_DURATION_TOKEN = re.compile(
    r"(?P<sign>[+-])?\s*(?P<amount>\d+(?:\.\d+)?)\s*"
    r"(?P<unit>years?|yrs?|months?|mos?|weeks?|w|days?|d|hours?|hrs?|h|minutes?|mins?|m|seconds?|secs?|s)",
    re.IGNORECASE,
)

_SECONDS_PER_UNIT = {
    "s": 1,
    "sec": 1,
    "secs": 1,
    "second": 1,
    "seconds": 1,
    "m": 60,
    "min": 60,
    "mins": 60,
    "minute": 60,
    "minutes": 60,
    "h": 3600,
    "hr": 3600,
    "hrs": 3600,
    "hour": 3600,
    "hours": 3600,
    "d": 86400,
    "day": 86400,
    "days": 86400,
    "w": 604800,
    "week": 604800,
    "weeks": 604800,
}


@dataclass(slots=True)
class ParsedDuration:
    """Parsed duration expressed as a :class:`datetime.timedelta`."""

    value: _dt.timedelta
    seconds: int


class _NamedZoneInfo(_dt.tzinfo):
    """Wrapper around :class:`zoneinfo.ZoneInfo` that exposes a ``name`` attribute."""

    __slots__ = ("_zone", "name", "key")

    def __init__(self, zone: ZoneInfo):
        self._zone = zone
        self.key = getattr(zone, "key", None)
        self.name = self.key or str(zone)

    def tzname(self, dt: _dt.datetime | None) -> str | None:  # pragma: no cover - trivial
        return self.name

    def utcoffset(self, dt: _dt.datetime | None) -> _dt.timedelta | None:
        if dt is None:
            return None
        zone_dt = dt.replace(tzinfo=self._zone)
        return self._zone.utcoffset(zone_dt)

    def dst(self, dt: _dt.datetime | None) -> _dt.timedelta | None:
        if dt is None:
            return None
        zone_dt = dt.replace(tzinfo=self._zone)
        return self._zone.dst(zone_dt)


def _get_zoneinfo(tz: str | None) -> ZoneInfo:
    try:
        return ZoneInfo(tz or "UTC")
    except ZoneInfoNotFoundError as exc:  # pragma: no cover - defensive branch
        raise ValueError(f"Unknown timezone: {tz}") from exc


def _attach_named_zoneinfo(dt: _dt.datetime, zone: ZoneInfo) -> _dt.datetime:
    named_zone = _NamedZoneInfo(zone)
    return dt.replace(tzinfo=named_zone)


def epoch_to_datetime(epoch: float, tz: str = "UTC") -> _dt.datetime:
    """Convert an epoch timestamp to a timezone aware datetime."""

    zone = _get_zoneinfo(tz)
    utc_dt = _dt.datetime.fromtimestamp(epoch, tz=_dt.timezone.utc)
    converted = utc_dt.astimezone(zone)
    return _attach_named_zoneinfo(converted, zone)


def datetime_to_epoch(dt: _dt.datetime) -> float:
    """Return the epoch for ``dt``."""

    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=_dt.timezone.utc)
    return dt.timestamp()


def convert_timezone(dt: _dt.datetime, tz: str) -> _dt.datetime:
    """Convert ``dt`` to ``tz``."""

    target_tz = _get_zoneinfo(tz)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=_dt.timezone.utc)
    converted = dt.astimezone(target_tz)
    return _attach_named_zoneinfo(converted, target_tz)


def add_duration(dt: _dt.datetime, **kwargs: Any) -> _dt.datetime:
    """Add a duration described by ``kwargs`` to ``dt``."""

    delta = relativedelta(**kwargs)
    return dt + delta


def parse_natural_delta(
    value: str,
    *,
    now: _dt.datetime | None = None,
    tz: str | None = None,
) -> ParsedDuration:
    """Parse simple natural language durations (e.g. ``"in 2h"``).

    Args:
        value: Textual representation of the duration.
        now: Optional base datetime for relative calculations. Defaults to the
            current UTC datetime.
        tz: Optional timezone name to anchor parsing. Defaults to UTC.

    Returns:
        ParsedDuration: The resulting delta.

    Raises:
        ValueError: If ``value`` cannot be parsed.
    """

    text = value.strip()
    if not text:
        raise ValueError("Duration value cannot be empty")

    tzinfo = _NamedZoneInfo(_get_zoneinfo(tz))
    base = now or _dt.datetime.now(tz=_dt.timezone.utc)
    if base.tzinfo is None:
        base = base.replace(tzinfo=tzinfo)
    else:
        base = base.astimezone(tzinfo)

    settings = {
        **_RELATIVE_SETTINGS,
        "RELATIVE_BASE": base,
        "TIMEZONE": tzinfo.key if hasattr(tzinfo, "key") else str(tzinfo),
        "TO_TIMEZONE": tzinfo.key if hasattr(tzinfo, "key") else str(tzinfo),
    }

    parsed = dateparser.parse(text, settings=settings)
    if parsed is not None:
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=tzinfo)
        else:
            parsed = parsed.astimezone(tzinfo)
        delta = parsed - base
        return ParsedDuration(value=delta, seconds=int(delta.total_seconds()))

    # Fallback to compact duration formats like "2h 30m" or "-45m"
    cleaned = text.lower()
    sign = 1
    if cleaned.startswith("in "):
        cleaned = cleaned[3:]
    if cleaned.endswith(" ago"):
        cleaned = cleaned[:-4].strip()
        sign = -1

    total_seconds = 0.0
    matched = False
    for match in _DURATION_TOKEN.finditer(cleaned):
        matched = True
        token_sign = -1 if match.group("sign") == "-" else 1
        amount = float(match.group("amount"))
        unit = match.group("unit").lower()
        unit_key = unit.rstrip("s")
        if unit_key in {"yr", "year", "mo", "month"}:
            # Months/years require calendar awareness; try dateparser again with suffix
            parsed = dateparser.parse(f"{text}", settings=settings)
            if parsed is None:
                raise ValueError(f"Unsupported duration expression: {value}")
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=tzinfo)
            else:
                parsed = parsed.astimezone(tzinfo)
            delta = parsed - base
            return ParsedDuration(value=delta, seconds=int(delta.total_seconds()))
        seconds = _SECONDS_PER_UNIT.get(unit)
        if seconds is None:
            seconds = _SECONDS_PER_UNIT.get(unit_key)
        if seconds is None:
            raise ValueError(f"Unsupported duration unit: {unit}")
        total_seconds += token_sign * amount * seconds

    if not matched:
        raise ValueError(f"Unsupported duration expression: {value}")

    delta_seconds = sign * total_seconds
    delta = _dt.timedelta(seconds=delta_seconds)
    return ParsedDuration(value=delta, seconds=int(delta.total_seconds()))
