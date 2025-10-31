"""URL processing utilities."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable
from collections.abc import Mapping, Sequence
import re
from urllib.parse import (
    ParseResult,
    parse_qsl,
    urlencode,
    urlparse,
    urlunparse,
    quote,
    unquote_to_bytes,
)

INVALID_PERCENT_PATTERN = re.compile(r"%(?![0-9A-Fa-f]{2})")

__all__ = [
    "UrlError",
    "ParsedUrl",
    "parse_url",
    "build_url",
    "encode_component",
    "decode_component",
    "parse_query_string",
    "rebuild_query_string",
]


class UrlError(ValueError):
    """Raised when URL specific processing fails."""


@dataclass(slots=True)
class ParsedUrl:
    """A small dataclass that mirrors :class:`urllib.parse.ParseResult`."""

    scheme: str
    netloc: str
    path: str
    params: str
    query: str
    fragment: str

    @classmethod
    def from_parse_result(cls, result: ParseResult) -> "ParsedUrl":
        return cls(
            scheme=result.scheme,
            netloc=result.netloc,
            path=result.path,
            params=result.params,
            query=result.query,
            fragment=result.fragment,
        )

    def to_parse_result(self) -> ParseResult:
        return ParseResult(self.scheme, self.netloc, self.path, self.params, self.query, self.fragment)


def parse_url(value: str) -> ParsedUrl:
    """Parse ``value`` into a :class:`ParsedUrl`."""

    return ParsedUrl.from_parse_result(urlparse(value))


def build_url(parsed: ParsedUrl, *, query: dict[str, Any] | None = None) -> str:
    """Return a URL string from ``parsed`` replacing the query if provided."""

    query_string = parsed.query if query is None else rebuild_query_string(query)
    return urlunparse(
        ParsedUrl(
            scheme=parsed.scheme,
            netloc=parsed.netloc,
            path=parsed.path,
            params=parsed.params,
            query=query_string,
            fragment=parsed.fragment,
        ).to_parse_result()
    )


def encode_component(value: str, *, safe: str = "") -> str:
    """Percent encode ``value`` for use in URLs.

    Parameters
    ----------
    value:
        The component to encode. The function expects a unicode string and
        returns an ASCII safe representation.
    safe:
        Additional characters that should not be percent encoded. By default
        ``safe`` is empty, resulting in strict encoding even for ``/``.
    """

    if not isinstance(value, str):  # pragma: no cover - defensive
        raise TypeError("value must be a string")
    return quote(value, safe=safe)


def decode_component(value: str, *, encoding: str = "utf-8", errors: str = "strict") -> str:
    """Decode a percent encoded string.

    ``urllib.parse.unquote`` silently ignores malformed percent escapes. The
    bot should instead surface helpful error messages, therefore the function
    leverages :func:`urllib.parse.unquote_to_bytes` which raises ``ValueError``
    when encountering invalid sequences.
    """

    _ensure_valid_percent_encoding(value)
    try:
        raw = unquote_to_bytes(value)
    except ValueError as exc:  # pragma: no cover - delegated to caller
        raise UrlError("Invalid percent-encoded sequence") from exc
    try:
        return raw.decode(encoding, errors=errors)
    except UnicodeDecodeError as exc:  # pragma: no cover - delegated to caller
        raise UrlError("Decoded data is not valid UTF-8") from exc


def parse_query_string(value: str) -> dict[str, list[str]]:
    """Parse a query string or raw URL and return a mapping."""

    if "=" not in value and "&" not in value and "?" not in value:
        # treat it as part of an URL without query.
        return {}
    query = urlparse(value).query if "?" in value else value.lstrip("?")
    result: dict[str, list[str]] = {}
    _ensure_valid_percent_encoding(query)
    try:
        pairs = parse_qsl(
            query,
            keep_blank_values=True,
            strict_parsing=False,
            encoding="utf-8",
            errors="strict",
        )
    except ValueError as exc:  # pragma: no cover - delegated to caller
        raise UrlError("Invalid query string") from exc
    for key, val in pairs:
        result.setdefault(key, []).append(val)
    return result


def rebuild_query_string(data: Mapping[str, Any] | Sequence[tuple[str, Any]]) -> str:
    """Build a query string from ``data``.

    The function accepts either a mapping or a sequence of ``(key, value)``
    tuples. Values that are list/tuple like produce repeated keys. ``None``
    values are converted to the empty string for convenience.
    """

    def as_iterable() -> Iterable[tuple[str, Any]]:
        if isinstance(data, Mapping):
            return data.items()
        return data

    encoded: list[tuple[str, str]] = []
    for key, value in as_iterable():
        if isinstance(value, (list, tuple)):
            if not value:
                encoded.append((key, ""))
            else:
                for item in value:
                    encoded.append((key, "" if item is None else str(item)))
        else:
            encoded.append((key, "" if value is None else str(value)))
    return urlencode(encoded)


def _ensure_valid_percent_encoding(value: str) -> None:
    if INVALID_PERCENT_PATTERN.search(value):
        raise UrlError("Invalid percent-encoded sequence")
