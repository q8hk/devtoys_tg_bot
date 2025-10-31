"""Regex helpers with safety controls."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

import regex

__all__ = [
    "FLAG_ALIASES",
    "RegexMatch",
    "RegexResult",
    "parse_flag_tokens",
    "run_regex",
]


FLAG_ALIASES: dict[str, int] = {
    "i": regex.IGNORECASE,
    "m": regex.MULTILINE,
    "s": regex.DOTALL,
    "x": regex.VERBOSE,
    "a": regex.ASCII,
    "l": regex.LOCALE,
    "u": regex.UNICODE,
}


@dataclass(slots=True)
class RegexMatch:
    """Single regex match result."""

    value: str
    groups: tuple[str | None, ...]
    named_groups: dict[str, str | None]
    span: tuple[int, int]


@dataclass(slots=True)
class RegexResult:
    """Aggregate information returned by :func:`run_regex`."""

    pattern: str
    matches: list[RegexMatch]
    timed_out: bool


def parse_flag_tokens(tokens: str | Iterable[str]) -> int:
    """Translate textual flag tokens to a combined flag integer.

    ``tokens`` may either be a string (e.g. ``"imx"``) or an iterable of strings
    such as ``["i", "m"]``. Unknown tokens raise :class:`ValueError` to signal
    invalid user input.
    """

    if isinstance(tokens, str):
        cleaned = tokens.replace(",", "").replace("|", "").replace(" ", "")
        parts: list[str] = list(cleaned)
    else:
        parts = []
        for part in tokens:
            stripped = part.strip()
            if not stripped:
                continue
            parts.extend(list(stripped))

    flag_value = 0
    for part in parts:
        key = part.lower()
        try:
            flag_value |= FLAG_ALIASES[key]
        except KeyError as exc:
            raise ValueError(f"Unsupported regex flag: {part}") from exc
    return flag_value


def run_regex(
    pattern: str,
    text: str,
    *,
    flags: int = 0,
    limit: int = 20,
    timeout: float = 100,
) -> RegexResult:
    """Execute ``pattern`` against ``text``.

    ``timeout`` is expressed in milliseconds and translated to the ``regex``
    library's ``timeout`` argument which provides useful ReDoS protection. If
    ``limit`` is negative a :class:`ValueError` is raised.
    """

    if limit < 0:
        raise ValueError("limit must be greater than or equal to 0")
    if timeout < 0:
        raise ValueError("timeout must be greater than or equal to 0")

    try:
        compiled = regex.compile(pattern, flags)
    except regex.error as exc:
        raise ValueError(str(exc)) from exc

    if limit == 0:
        return RegexResult(pattern=pattern, matches=[], timed_out=False)

    matches: list[RegexMatch] = []
    timed_out = False
    try:
        timeout_seconds = timeout / 1000 if timeout else None
        iterator_kwargs = {"timeout": timeout_seconds} if timeout_seconds is not None else {}
        for match in compiled.finditer(text, **iterator_kwargs):
            matches.append(
                RegexMatch(
                    value=match.group(0),
                    groups=match.groups(),
                    named_groups=match.groupdict(),
                    span=match.span(),
                )
            )
            if limit and len(matches) >= limit:
                break
    except TimeoutError:
        timed_out = True
    return RegexResult(pattern=pattern, matches=matches, timed_out=timed_out)
