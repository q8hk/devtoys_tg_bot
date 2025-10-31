"""URL processing utilities."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from urllib.parse import ParseResult, parse_qsl, urlencode, urlparse, urlunparse, quote, unquote

__all__ = [
    "ParsedUrl",
    "parse_url",
    "build_url",
    "encode_component",
    "decode_component",
    "parse_query_string",
    "rebuild_query_string",
]


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
    """Percent encode a string for use in URLs."""

    return quote(value, safe=safe)


def decode_component(value: str) -> str:
    """Decode a percent encoded string."""

    return unquote(value)


def parse_query_string(value: str) -> dict[str, list[str]]:
    """Parse a query string or raw URL and return a mapping."""

    if "=" not in value and "&" not in value and "?" not in value:
        # treat it as part of an URL without query.
        return {}
    query = urlparse(value).query if "?" in value else value.lstrip("?")
    result: dict[str, list[str]] = {}
    for key, val in parse_qsl(query, keep_blank_values=True):
        result.setdefault(key, []).append(val)
    return result


def rebuild_query_string(data: dict[str, Any]) -> str:
    """Build a query string from a mapping.

    Values that are list/tuple like result in repeated keys.
    """

    encoded: list[tuple[str, str]] = []
    for key, value in data.items():
        if isinstance(value, (list, tuple)):
            encoded.extend((key, str(item)) for item in value)
        else:
            encoded.append((key, str(value)))
    return urlencode(encoded)
