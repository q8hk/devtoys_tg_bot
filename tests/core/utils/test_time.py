import datetime as dt

import pytest

from src.core.utils.time_ import (
    ParsedDuration,
    add_duration,
    convert_timezone,
    datetime_to_epoch,
    epoch_to_datetime,
    parse_natural_delta,
)


def test_epoch_to_datetime_converts_timezone():
    epoch = 0
    result = epoch_to_datetime(epoch, tz="Europe/Berlin")
    assert result.year == 1970
    assert result.hour == 1  # CET is UTC+1 on 1970-01-01
    assert result.tzinfo is not None
    assert getattr(result.tzinfo, "key", "") == "Europe/Berlin"


def test_datetime_to_epoch_handles_naive():
    dt_obj = dt.datetime(2024, 1, 1, 0, 0, 0)
    expected = dt.datetime(2024, 1, 1, 0, 0, 0, tzinfo=dt.timezone.utc).timestamp()
    assert datetime_to_epoch(dt_obj) == expected


def test_convert_timezone_from_utc_to_tokyo():
    utc_dt = dt.datetime(2024, 3, 10, 12, 0, tzinfo=dt.timezone.utc)
    converted = convert_timezone(utc_dt, "Asia/Tokyo")
    assert converted.hour == 21
    assert getattr(converted.tzinfo, "key", "") == "Asia/Tokyo"


def test_add_duration_with_calendar_month():
    base = dt.datetime(2024, 1, 31, 12, 0, tzinfo=dt.timezone.utc)
    result = add_duration(base, months=1)
    assert result.year == 2024
    assert result.month == 2
    assert result.day == 29  # 2024 is a leap year
    assert result.hour == 12


@pytest.mark.parametrize(
    "expression,expected_seconds",
    [
        ("in 2 hours", 2 * 3600),
        ("45m", 45 * 60),
        ("3 hours ago", -3 * 3600),
    ],
)
def test_parse_natural_delta_seconds(expression: str, expected_seconds: int):
    base = dt.datetime(2024, 1, 1, 12, 0, tzinfo=dt.timezone.utc)
    parsed = parse_natural_delta(expression, now=base)
    assert isinstance(parsed, ParsedDuration)
    assert parsed.seconds == expected_seconds
    assert parsed.value.total_seconds() == pytest.approx(expected_seconds)


def test_parse_natural_delta_with_timezone_context():
    base = dt.datetime(2024, 1, 1, 9, 0, tzinfo=dt.timezone.utc)
    parsed = parse_natural_delta("tomorrow at 10:00", now=base, tz="Europe/Berlin")
    target = base.astimezone(dt.timezone.utc)
    resulting_dt = target + parsed.value
    expected = dt.datetime(2024, 1, 2, 9, 0, tzinfo=dt.timezone.utc)
    assert resulting_dt == expected


def test_parse_natural_delta_invalid_expression():
    base = dt.datetime(2024, 1, 1, 12, 0, tzinfo=dt.timezone.utc)
    with pytest.raises(ValueError):
        parse_natural_delta("nonsense", now=base)
