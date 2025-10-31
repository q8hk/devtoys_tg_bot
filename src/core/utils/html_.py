"""HTML utilities."""

from __future__ import annotations

import html
from html.parser import HTMLParser

__all__ = [
    "encode_entities",
    "decode_entities",
    "strip_tags",
    "minify_html",
]


def encode_entities(value: str) -> str:
    return html.escape(value)


def decode_entities(value: str) -> str:
    return html.unescape(value)


class _Stripper(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.result: list[str] = []

    def handle_data(self, data: str) -> None:  # pragma: no cover - trivial
        self.result.append(data)


def strip_tags(value: str) -> str:
    parser = _Stripper()
    parser.feed(value)
    parser.close()
    return "".join(parser.result)


def minify_html(value: str) -> str:
    """Naively minify HTML by stripping superfluous whitespace."""

    lines = [line.strip() for line in value.splitlines() if line.strip()]
    return "".join(lines)
