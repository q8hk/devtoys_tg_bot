"""Code tooling utilities."""

from __future__ import annotations

import json
import secrets
import string
from difflib import unified_diff

__all__ = [
    "format_json",
    "minify_json",
    "format_css",
    "minify_css",
    "format_js",
    "minify_js",
    "generate_password",
    "generate_token",
    "text_diff",
]

_INDENT = "    "


def format_json(value: str) -> str:
    """Return a pretty printed JSON string."""

    parsed = json.loads(value)
    return json.dumps(parsed, indent=2, ensure_ascii=False, sort_keys=True)


def minify_json(value: str) -> str:
    """Return a compact JSON string."""

    parsed = json.loads(value)
    return json.dumps(parsed, separators=(",", ":"), ensure_ascii=False, sort_keys=True)


def _strip_css_comments(value: str) -> str:
    result: list[str] = []
    i = 0
    length = len(value)
    string_delimiter: str | None = None

    while i < length:
        char = value[i]
        if string_delimiter is not None:
            result.append(char)
            if char == string_delimiter and (i == 0 or value[i - 1] != "\\"):
                string_delimiter = None
            i += 1
            continue

        if char in {'"', "'"}:
            string_delimiter = char
            result.append(char)
            i += 1
            continue

        if char == "/" and i + 1 < length and value[i + 1] == "*":
            i += 2
            while i + 1 < length and not (value[i] == "*" and value[i + 1] == "/"):
                if value[i] in {'"', "'"}:
                    quote = value[i]
                    i += 1
                    while i < length and not (value[i] == quote and value[i - 1] != "\\"):
                        i += 1
                else:
                    i += 1
            i += 2
            continue

        result.append(char)
        i += 1

    return "".join(result)


def format_css(value: str) -> str:
    """Return formatted CSS with deterministic indentation."""

    css = _strip_css_comments(value).strip()
    if not css:
        return ""

    lines: list[str] = []
    buffer: list[str] = []
    indent = 0
    string_delimiter: str | None = None

    def flush_buffer(*, suffix: str = "") -> None:
        nonlocal buffer
        if buffer or suffix:
            content = "".join(buffer).strip()
            if suffix:
                content = f"{content}{suffix}" if content else suffix
            if content:
                lines.append(f"{_INDENT * indent}{content}")
        buffer = []

    for char in css:
        if string_delimiter is not None:
            buffer.append(char)
            if char == string_delimiter and (len(buffer) < 2 or buffer[-2] != "\\"):
                string_delimiter = None
            continue

        if char in {'"', "'"}:
            buffer.append(char)
            string_delimiter = char
            continue

        if char == "{":
            flush_buffer(suffix=" {")
            indent += 1
            continue

        if char == "}":
            flush_buffer()
            indent = max(indent - 1, 0)
            lines.append(f"{_INDENT * indent}}}")
            continue

        if char == ";":
            flush_buffer(suffix=";")
            continue

        if char == ",":
            buffer.append(",")
            flush_buffer()
            continue

        if char.isspace():
            if buffer and not buffer[-1].isspace():
                buffer.append(" ")
            continue

        buffer.append(char)

    flush_buffer()
    return "\n".join(lines)


def minify_css(value: str) -> str:
    """Return a compact CSS string preserving string literals."""

    css = _strip_css_comments(value)
    result: list[str] = []
    string_delimiter: str | None = None

    for char in css:
        if string_delimiter is not None:
            result.append(char)
            if char == string_delimiter and (len(result) < 2 or result[-2] != "\\"):
                string_delimiter = None
            continue

        if char in {'"', "'"}:
            string_delimiter = char
            result.append(char)
            continue

        if char.isspace():
            if result and result[-1] not in " \n\t\r\f{}:;>,()" and not (len(result) >= 2 and result[-2] in "\r\n"):
                result.append(" ")
            continue

        if char in "{}:;>,()":
            while result and result[-1] == " ":
                result.pop()
            result.append(char)
            continue

        result.append(char)

    return "".join(result).strip()


def _strip_js_comments(value: str) -> str:
    result: list[str] = []
    i = 0
    length = len(value)
    string_delimiter: str | None = None
    in_single_line_comment = False
    in_multi_line_comment = False

    while i < length:
        char = value[i]

        if string_delimiter is not None:
            result.append(char)
            if char == string_delimiter and (i == 0 or value[i - 1] != "\\"):
                string_delimiter = None
            i += 1
            continue

        if in_single_line_comment:
            if char in "\r\n":
                in_single_line_comment = False
                result.append(char)
            i += 1
            continue

        if in_multi_line_comment:
            if char == "*" and i + 1 < length and value[i + 1] == "/":
                in_multi_line_comment = False
                i += 2
            else:
                i += 1
            continue

        if char in {'"', "'", "`"}:
            string_delimiter = char
            result.append(char)
            i += 1
            continue

        if char == "/" and i + 1 < length:
            nxt = value[i + 1]
            if nxt == "/":
                in_single_line_comment = True
                i += 2
                continue
            if nxt == "*":
                in_multi_line_comment = True
                i += 2
                continue

        result.append(char)
        i += 1

    return "".join(result)


def format_js(value: str) -> str:
    """Return a formatted JavaScript string using a lightweight formatter."""

    js = _strip_js_comments(value)
    if not js.strip():
        return ""

    lines: list[str] = []
    buffer: list[str] = []
    indent = 0
    string_delimiter: str | None = None

    def flush_buffer(*, suffix: str | None = None) -> None:
        nonlocal buffer
        if not buffer and suffix is None:
            return
        content = "".join(buffer).strip()
        if suffix:
            content = f"{content}{suffix}" if content else suffix
        if content:
            lines.append(f"{_INDENT * indent}{content}")
        buffer = []

    i = 0
    while i < len(js):
        char = js[i]

        if string_delimiter is not None:
            buffer.append(char)
            if char == string_delimiter and (len(buffer) < 2 or buffer[-2] != "\\"):
                string_delimiter = None
            i += 1
            continue

        if char in {'"', "'", "`"}:
            string_delimiter = char
            buffer.append(char)
            i += 1
            continue

        if char == "{":
            flush_buffer()
            lines.append(f"{_INDENT * indent}{{")
            indent += 1
            i += 1
            continue

        if char == "}":
            flush_buffer()
            indent = max(indent - 1, 0)
            lines.append(f"{_INDENT * indent}}}")
            i += 1
            continue

        if char == ";":
            flush_buffer(suffix=";")
            i += 1
            continue

        if char == ",":
            buffer.append(",")
            flush_buffer()
            i += 1
            continue

        if char in "\r\n":
            flush_buffer()
            i += 1
            continue

        if char.isspace():
            if buffer and not buffer[-1].isspace():
                buffer.append(" ")
            i += 1
            continue

        buffer.append(char)
        i += 1

    flush_buffer()
    return "\n".join(lines)


def minify_js(value: str) -> str:
    """Return a compact JavaScript string preserving string literals."""

    js = _strip_js_comments(value)
    result: list[str] = []
    string_delimiter: str | None = None

    for char in js:
        if string_delimiter is not None:
            result.append(char)
            if char == string_delimiter and (len(result) < 2 or result[-2] != "\\"):
                string_delimiter = None
            continue

        if char in {'"', "'", "`"}:
            string_delimiter = char
            result.append(char)
            continue

        if char.isspace():
            if result and result[-1] not in " \n\t\r\f{}[]():;,.+-*/%&|^!?<>=":
                result.append(" ")
            continue

        if char in "{}[]():;,.+-*/%&|^!?<>=":
            while result and result[-1] == " ":
                result.pop()
            result.append(char)
            continue

        result.append(char)

    return "".join(result).strip()


def generate_password(
    *,
    length: int = 16,
    use_digits: bool = True,
    use_symbols: bool = True,
) -> str:
    """Generate a random password satisfying basic policy requirements."""

    lower = string.ascii_lowercase
    upper = string.ascii_uppercase
    digits = string.digits if use_digits else ""
    symbols = string.punctuation if use_symbols else ""

    categories = [lower, upper]
    if digits:
        categories.append(digits)
    if symbols:
        categories.append(symbols)

    if length < len(categories):
        raise ValueError("Password length is too short for the selected policy")

    password_chars = [secrets.choice(category) for category in categories]
    alphabet = "".join(categories)
    password_chars.extend(secrets.choice(alphabet) for _ in range(length - len(categories)))
    secrets.SystemRandom().shuffle(password_chars)
    return "".join(password_chars)


def generate_token(*, length: int = 32, alphabet: str | None = None) -> str:
    """Generate a cryptographically secure random token."""

    if length <= 0:
        raise ValueError("Token length must be positive")

    chars = alphabet or (string.ascii_letters + string.digits)
    if not chars:
        raise ValueError("Alphabet must not be empty")

    return "".join(secrets.choice(chars) for _ in range(length))


def text_diff(original: str, updated: str, *, fromfile: str = "original", tofile: str = "updated") -> str:
    """Return a unified diff between two pieces of text."""

    diff = unified_diff(
        original.splitlines(keepends=True),
        updated.splitlines(keepends=True),
        fromfile=fromfile,
        tofile=tofile,
    )
    return "".join(diff)
