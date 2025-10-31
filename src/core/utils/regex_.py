"""Regex helpers with safety controls."""

from __future__ import annotations

from dataclasses import dataclass

import regex

__all__ = [
    "RegexMatch",
    "RegexResult",
    "run_regex",
]


@dataclass(slots=True)
class RegexMatch:
    value: str
    groups: tuple[str, ...]
    span: tuple[int, int]


@dataclass(slots=True)
class RegexResult:
    pattern: str
    matches: list[RegexMatch]
    timed_out: bool


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
    library's ``timeout`` argument which provides useful ReDoS protection.
    """

    compiled = regex.compile(pattern, flags)
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
                    span=match.span(),
                )
            )
            if len(matches) >= limit:
                break
    except TimeoutError:
        timed_out = True
    return RegexResult(pattern=pattern, matches=matches, timed_out=timed_out)
