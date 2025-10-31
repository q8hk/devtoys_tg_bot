"""High level helpers for manipulating blocks of text.

The real Telegram bot would expose many of these utilities through chat
interactions.  Keeping them in a dedicated module makes the pure business
logic easy to test without having to go through aiogram handlers.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from random import Random
from textwrap import dedent as _dedent
from textwrap import indent as _indent

__all__ = [
    "trim",
    "indent",
    "dedent",
    "normalize_whitespace",
    "ltrim",
    "rtrim",
    "to_upper",
    "to_lower",
    "to_title",
    "to_sentence",
    "slugify",
    "sort_lines",
    "unique_lines",
    "add_line_numbers",
    "strip_line_numbers",
    "LoremConfig",
    "generate_lorem_ipsum",
]


def trim(value: str) -> str:
    """Return ``value`` with leading and trailing whitespace removed."""

    return value.strip()


def ltrim(value: str) -> str:
    """Return ``value`` without the leading whitespace."""

    return value.lstrip()


def rtrim(value: str) -> str:
    """Return ``value`` without the trailing whitespace."""

    return value.rstrip()


def indent(value: str, prefix: str = "    ", indent_empty: bool = False) -> str:
    """Indent every line in *value* using ``prefix``.

    ``textwrap.indent`` does the heavy lifting but toggling ``indent_empty`` is
    a common feature the stdlib helper does not expose directly.
    """

    if indent_empty:
        return _indent(value, prefix, lambda _line: True)
    return _indent(value, prefix, lambda line: bool(line.strip()))


def dedent(value: str) -> str:
    """Dedent *value* using :func:`textwrap.dedent`."""

    return _dedent(value)


def normalize_whitespace(value: str) -> str:
    """Collapse consecutive whitespace characters into a single space.

    All kinds of whitespace (tabs, newlines, carriage returns) are treated as
    separators and the final result is stripped.  This mirrors the behaviour of
    many "minify" style helpers.
    """

    return " ".join(value.split())


def to_upper(value: str) -> str:
    """Return an upper-case representation of ``value``."""

    return value.upper()


def to_lower(value: str) -> str:
    """Return a lower-case representation of ``value``."""

    return value.lower()


def to_title(value: str) -> str:
    """Return ``value`` converted to title case."""

    return value.title()


def to_sentence(value: str) -> str:
    """Return ``value`` converted to sentence case."""

    if not value:
        return ""
    return value.capitalize()


def slugify(value: str, *, separator: str = "-") -> str:
    """Create a filesystem/URL friendly slug.

    The implementation purposely stays lightweight and does not depend on
    ``python-slugify``.  Accented characters are normalized and stripped when
    possible.  Any remaining non alpha-numeric characters are turned into the
    separator.
    """

    import unicodedata

    normalized = unicodedata.normalize("NFKD", value)
    ascii_only = normalized.encode("ascii", "ignore").decode("ascii")
    cleaned: list[str] = []
    previous_was_sep = False
    for char in ascii_only:
        if char.isalnum():
            cleaned.append(char.lower())
            previous_was_sep = False
        else:
            if not previous_was_sep:
                cleaned.append(separator)
            previous_was_sep = True
    slug = "".join(cleaned).strip(separator)
    return slug or separator


def _normalize_newlines(value: str) -> str:
    """Return ``value`` with Windows and old Mac newlines normalised."""

    return value.replace("\r\n", "\n").replace("\r", "\n")


def _split_lines(value: str) -> tuple[list[str], int]:
    """Split ``value`` into lines while tracking trailing newlines.

    The helper normalises newline characters to ``\n`` and returns the list of
    logical lines along with the number of trailing newline characters that need
    to be re-attached once a transformation has been applied.
    """

    normalized = _normalize_newlines(value)
    if not normalized:
        return [], 0
    trailing_newlines = len(normalized) - len(normalized.rstrip("\n"))
    core = normalized[: len(normalized) - trailing_newlines] if trailing_newlines else normalized
    if core:
        lines = core.split("\n")
    else:
        lines = []
    return lines, trailing_newlines


def sort_lines(
    value: str,
    *,
    reverse: bool = False,
    case_sensitive: bool = False,
) -> str:
    """Return a string whose lines are sorted.

    Empty trailing lines are preserved to avoid surprise formatting changes.
    """

    lines, trailing_newlines = _split_lines(value)
    if not lines:
        return "\n" * trailing_newlines
    if not case_sensitive:
        lines.sort(key=lambda item: item.lower(), reverse=reverse)
    else:
        lines.sort(reverse=reverse)
    result = "\n".join(lines)
    if trailing_newlines:
        result += "\n" * trailing_newlines
    return result


def unique_lines(value: str, *, preserve_order: bool = True) -> str:
    """Return ``value`` with duplicate lines removed."""

    lines, trailing_newlines = _split_lines(value)
    if not lines:
        return "\n" * trailing_newlines
    if preserve_order:
        seen: set[str] = set()
        unique: list[str] = []
        for line in lines:
            if line not in seen:
                seen.add(line)
                unique.append(line)
        result_lines = unique
    else:
        result_lines = sorted(set(lines))
    result = "\n".join(result_lines)
    if trailing_newlines:
        result += "\n" * trailing_newlines
    return result


def add_line_numbers(
    value: str,
    *,
    start: int = 1,
    padding: int = 3,
    separator: str = " ",
) -> str:
    """Prefix lines with increasing numbers.

    ``padding`` controls the zero padding applied to the counter so the columns
    stay aligned.
    """

    normalized = _normalize_newlines(value)
    if not normalized:
        return ""

    lines = normalized.split("\n")
    formatted = [
        f"{index:0{padding}d}{separator}{line}"
        for index, line in enumerate(lines, start=start)
    ]
    return "\n".join(formatted)


def strip_line_numbers(value: str, *, separator: str = " ") -> str:
    """Remove the line numbers added by :func:`add_line_numbers`.

    The function is tolerant: if a line does not contain a number it is left as
    is.
    """

    lines, trailing_newlines = _split_lines(value)
    stripped: list[str] = []
    for line in lines:
        parts = line.split(separator, 1)
        if len(parts) == 2 and parts[0].strip().isdigit():
            stripped.append(parts[1])
        else:
            stripped.append(line)
    result = "\n".join(stripped)
    if trailing_newlines:
        result += "\n" * trailing_newlines
    return result


@dataclass(slots=True)
class LoremConfig:
    """Configuration for :func:`generate_lorem_ipsum`."""

    words: int = 30
    seed: int | None = None
    dictionary: Iterable[str] | None = None


DEFAULT_LOREM = (
    "lorem",
    "ipsum",
    "dolor",
    "sit",
    "amet",
    "consectetur",
    "adipiscing",
    "elit",
    "sed",
    "do",
    "eiusmod",
    "tempor",
    "incididunt",
    "ut",
    "labore",
    "et",
    "dolore",
    "magna",
    "aliqua",
)


def generate_lorem_ipsum(config: LoremConfig | None = None) -> str:
    """Generate a deterministic Lorem Ipsum like snippet."""

    if config is None:
        config = LoremConfig()
    words = max(1, config.words)
    dictionary = list(config.dictionary or DEFAULT_LOREM)
    rng = Random(config.seed)
    picked = [rng.choice(dictionary) for _ in range(words)]
    sentence = " ".join(picked)
    return sentence.capitalize() + "."
