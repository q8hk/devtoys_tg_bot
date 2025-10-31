"""UUID and ULID utilities.

This module provides high-level helpers for generating and validating UUID and
ULID identifiers. For UUIDs we support version 1, 4, and 7 identifiers and we
attempt to extract timestamps for versions that encode one (UUIDv1 and
UUIDv7). ULIDs also expose their timestamp component.
"""

from __future__ import annotations

import datetime as _dt
import secrets
import uuid
from dataclasses import dataclass
from typing import Optional

import ulid

UUID_EPOCH = _dt.datetime(1582, 10, 15, tzinfo=_dt.timezone.utc)

__all__ = [
    "UUIDInfo",
    "ULIDInfo",
    "generate_uuid",
    "inspect_uuid",
    "generate_ulid",
    "inspect_ulid",
]


def _ensure_timezone(value: _dt.datetime) -> _dt.datetime:
    """Ensure a :class:`datetime.datetime` is timezone-aware in UTC."""

    if value.tzinfo is None:
        return value.replace(tzinfo=_dt.timezone.utc)
    return value.astimezone(_dt.timezone.utc)


def _generate_uuid7(now: Optional[_dt.datetime] = None) -> uuid.UUID:
    """Generate a UUIDv7 according to the latest draft specification.

    Python does not yet expose :func:`uuid.uuid7` on all supported versions, so
    we construct the identifier manually. The UUIDv7 layout is composed of a
    48-bit millisecond Unix timestamp followed by 12 bits of randomness (the
    ``rand_a`` segment) and 62 bits of randomness (the ``rand_b`` segment).
    """

    moment = _ensure_timezone(now or _dt.datetime.now(tz=_dt.timezone.utc))
    timestamp_ms = int(moment.timestamp() * 1000)
    if timestamp_ms >= 1 << 48:
        raise ValueError("Timestamp exceeds UUIDv7 range")

    rand_a = secrets.randbits(12)
    rand_b = secrets.randbits(62)

    time_low = (timestamp_ms >> 16) & 0xFFFFFFFF
    time_mid = timestamp_ms & 0xFFFF
    time_hi_version = 0x7000 | rand_a

    rand_b_high = rand_b >> 56
    rand_b_low = rand_b & ((1 << 56) - 1)

    clock_seq_hi_variant = 0x80 | rand_b_high
    clock_seq_low = (rand_b_low >> 48) & 0xFF
    node = rand_b_low & ((1 << 48) - 1)

    return uuid.UUID(fields=(
        time_low,
        time_mid,
        time_hi_version,
        clock_seq_hi_variant,
        clock_seq_low,
        node,
    ))


def _uuid1_timestamp(value: uuid.UUID) -> _dt.datetime:
    timestamp_100ns = value.time
    seconds = timestamp_100ns / 10_000_000
    return UUID_EPOCH + _dt.timedelta(seconds=seconds)


def _uuid7_timestamp(value: uuid.UUID) -> _dt.datetime:
    time_low, time_mid, _, _, _, _ = value.fields
    timestamp_ms = (time_low << 16) | time_mid
    return _dt.datetime.fromtimestamp(timestamp_ms / 1000, tz=_dt.timezone.utc)


@dataclass(slots=True)
class UUIDInfo:
    """Information extracted from a UUID string."""

    value: Optional[uuid.UUID]
    version: Optional[int]
    is_valid: bool
    timestamp: Optional[_dt.datetime] = None


@dataclass(slots=True)
class ULIDInfo:
    """Information extracted from a ULID string."""

    value: Optional[ulid.ULID]
    timestamp: Optional[_dt.datetime]
    is_valid: bool


def generate_uuid(version: int = 4) -> uuid.UUID:
    """Generate a UUID for the supplied ``version``.

    Parameters
    ----------
    version:
        UUID version to generate. Supported versions are ``1``, ``4`` and
        ``7``.
    """

    if version == 1:
        return uuid.uuid1()
    if version == 4:
        return uuid.uuid4()
    if version == 7:
        uuid7 = getattr(uuid, "uuid7", None)
        if callable(uuid7):
            return uuid7()
        return _generate_uuid7()
    raise ValueError("Unsupported UUID version")


def inspect_uuid(value: str) -> UUIDInfo:
    """Parse a UUID string and extract metadata."""

    if not isinstance(value, str):
        return UUIDInfo(value=None, version=None, is_valid=False)

    try:
        parsed = uuid.UUID(value)
    except (ValueError, AttributeError, TypeError):
        return UUIDInfo(value=None, version=None, is_valid=False)

    timestamp: Optional[_dt.datetime] = None
    if parsed.version == 1:
        timestamp = _uuid1_timestamp(parsed)
    elif parsed.version == 7:
        timestamp = _uuid7_timestamp(parsed)

    return UUIDInfo(
        value=parsed,
        version=parsed.version,
        is_valid=True,
        timestamp=timestamp,
    )


def generate_ulid() -> ulid.ULID:
    """Return a freshly generated ULID."""

    return ulid.ULID()


def inspect_ulid(value: str) -> ULIDInfo:
    """Return metadata for the supplied ULID string."""

    if not isinstance(value, str):
        return ULIDInfo(value=None, timestamp=None, is_valid=False)

    try:
        parsed = ulid.ULID.from_str(value)
    except (ValueError, AttributeError, TypeError):
        return ULIDInfo(value=None, timestamp=None, is_valid=False)

    timestamp = _dt.datetime.fromtimestamp(parsed.timestamp, tz=_dt.timezone.utc)
    return ULIDInfo(value=parsed, timestamp=timestamp, is_valid=True)
