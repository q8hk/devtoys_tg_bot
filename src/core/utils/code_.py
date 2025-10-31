"""Code tooling utilities."""

from __future__ import annotations

import secrets
import string
from difflib import unified_diff

__all__ = ["generate_password", "text_diff"]


def generate_password(
    *,
    length: int = 16,
    use_digits: bool = True,
    use_symbols: bool = True,
) -> str:
    """Generate a random password satisfying basic policy requirements."""

    if length < 4:
        raise ValueError("Password length must be at least 4 characters")
    alphabet = string.ascii_letters
    if use_digits:
        alphabet += string.digits
    if use_symbols:
        alphabet += string.punctuation
    return "".join(secrets.choice(alphabet) for _ in range(length))


def text_diff(original: str, updated: str, *, fromfile: str = "original", tofile: str = "updated") -> str:
    """Return a unified diff between two pieces of text."""

    diff = unified_diff(
        original.splitlines(keepends=True),
        updated.splitlines(keepends=True),
        fromfile=fromfile,
        tofile=tofile,
    )
    return "".join(diff)
