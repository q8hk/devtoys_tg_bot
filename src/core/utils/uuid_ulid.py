"""UUID and ULID utilities."""

from __future__ import annotations

import datetime as _dt
import uuid
from dataclasses import dataclass

import ulid

__all__ = [
    "UUIDInfo",
    "ULIDInfo",
    "generate_uuid",
    "inspect_uuid",
    "generate_ulid",
    "inspect_ulid",
]


@dataclass(slots=True)
class UUIDInfo:
    value: uuid.UUID
    version: int
    is_valid: bool


@dataclass(slots=True)
class ULIDInfo:
    value: ulid.ULID
    timestamp: _dt.datetime


def generate_uuid(version: int = 4) -> uuid.UUID:
    """Generate a UUID for the supplied ``version``."""

    if version == 1:
        return uuid.uuid1()
    if version == 4:
        return uuid.uuid4()
    if version == 7:
        return uuid.uuid7()
    raise ValueError("Unsupported UUID version")


def inspect_uuid(value: str) -> UUIDInfo:
    """Parse and return a :class:`UUIDInfo` instance."""

    try:
        parsed = uuid.UUID(value)
    except (ValueError, AttributeError):
        return UUIDInfo(value=uuid.UUID(int=0), version=0, is_valid=False)
    return UUIDInfo(value=parsed, version=parsed.version or 0, is_valid=True)


def generate_ulid() -> ulid.ULID:
    """Return a freshly generated ULID."""

    return ulid.ULID()


def inspect_ulid(value: str) -> ULIDInfo:
    """Return metadata for the supplied ULID string."""

    parsed = ulid.ULID.from_str(value)
    timestamp = _dt.datetime.fromtimestamp(parsed.timestamp, tz=_dt.UTC)
    return ULIDInfo(value=parsed, timestamp=timestamp)
