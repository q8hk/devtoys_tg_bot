"""Tests for :mod:`src.core.utils.url`."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.core.utils import url


def test_encode_decode_component_roundtrip() -> None:
    raw = "Hello world/привет"
    encoded = url.encode_component(raw)
    assert encoded == "Hello%20world%2F%D0%BF%D1%80%D0%B8%D0%B2%D0%B5%D1%82"
    assert url.decode_component(encoded) == raw


def test_decode_component_invalid_escape() -> None:
    with pytest.raises(url.UrlError) as exc:
        url.decode_component("%E0%A4%")
    assert "Invalid" in str(exc.value)


def test_parse_query_string_from_url_and_raw_query() -> None:
    source = "https://example.com/api?foo=bar&foo=baz&empty=&space=hello+world"
    parsed_from_url = url.parse_query_string(source)
    parsed_from_query = url.parse_query_string("foo=bar&foo=baz&empty=&space=hello+world")
    assert parsed_from_url == parsed_from_query
    assert parsed_from_url["foo"] == ["bar", "baz"]
    assert parsed_from_url["empty"] == [""]
    assert parsed_from_url["space"] == ["hello world"]


def test_parse_query_string_invalid() -> None:
    with pytest.raises(url.UrlError):
        url.parse_query_string("q=%E0%A4%")


def test_rebuild_query_string_from_mapping_and_sequence() -> None:
    mapping = {"foo": [1, 2], "bar": "baz qux", "empty": None}
    rebuilt_from_mapping = url.rebuild_query_string(mapping)
    rebuilt_from_sequence = url.rebuild_query_string([("foo", 1), ("foo", 2), ("bar", "baz qux"), ("empty", None)])
    assert rebuilt_from_mapping == rebuilt_from_sequence
    assert "foo=1" in rebuilt_from_mapping and "foo=2" in rebuilt_from_mapping
    assert "bar=baz+qux" in rebuilt_from_mapping
    assert "empty=" in rebuilt_from_mapping
