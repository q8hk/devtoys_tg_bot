"""Tests for UUID and ULID utilities."""

from __future__ import annotations

import datetime as dt
import sys
from pathlib import Path

import pytest

ROOT_DIR = Path(__file__).resolve().parents[3]
if str(ROOT_DIR) not in sys.path:
    sys.path.append(str(ROOT_DIR))

from src.core.utils.uuid_ulid import (  # noqa: E402
    ULIDInfo,
    UUIDInfo,
    generate_ulid,
    generate_uuid,
    inspect_ulid,
    inspect_uuid,
)


def _now_utc() -> dt.datetime:
    return dt.datetime.now(tz=dt.timezone.utc)


def test_generate_uuid_versions() -> None:
    v1 = generate_uuid(1)
    v4 = generate_uuid(4)
    v7 = generate_uuid(7)

    assert v1.version == 1
    assert v4.version == 4
    assert v7.version == 7


def test_generate_uuid_invalid_version() -> None:
    with pytest.raises(ValueError):
        generate_uuid(2)


def test_inspect_uuid_v1_timestamp() -> None:
    generated = str(generate_uuid(1))
    info = inspect_uuid(generated)

    assert isinstance(info, UUIDInfo)
    assert info.is_valid is True
    assert info.version == 1
    assert info.timestamp is not None
    delta = abs(info.timestamp - _now_utc())
    assert delta < dt.timedelta(seconds=10)


def test_inspect_uuid_v7_timestamp() -> None:
    generated = str(generate_uuid(7))
    info = inspect_uuid(generated)

    assert info.is_valid is True
    assert info.version == 7
    assert info.timestamp is not None
    assert abs(info.timestamp - _now_utc()) < dt.timedelta(seconds=10)


def test_inspect_uuid_invalid_value() -> None:
    info = inspect_uuid("not-a-uuid")
    assert info.is_valid is False
    assert info.value is None
    assert info.timestamp is None


def test_generate_and_inspect_ulid() -> None:
    generated = generate_ulid()
    info = inspect_ulid(str(generated))

    assert isinstance(info, ULIDInfo)
    assert info.is_valid is True
    assert info.timestamp is not None
    assert abs(info.timestamp - _now_utc()) < dt.timedelta(seconds=10)


def test_inspect_ulid_invalid() -> None:
    info = inspect_ulid("invalid-ulid")
    assert info.is_valid is False
    assert info.value is None
    assert info.timestamp is None
