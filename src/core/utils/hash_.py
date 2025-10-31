"""Hashing helpers."""

from __future__ import annotations

import hashlib
import hmac

__all__ = [
    "available_algorithms",
    "calculate_hash",
    "calculate_hmac",
]


def available_algorithms() -> list[str]:
    """Return the list of supported hash algorithms."""

    return sorted(hashlib.algorithms_available)


def _normalise_data(data: bytes | str) -> bytes:
    return data if isinstance(data, bytes) else data.encode("utf-8")


def calculate_hash(data: bytes | str, algorithm: str = "sha256") -> str:
    """Calculate the hash digest for *data*."""

    algo = algorithm.lower()
    try:
        digest = hashlib.new(algo)
    except ValueError as exc:  # pragma: no cover - defensive
        raise ValueError(f"Unsupported algorithm: {algorithm}") from exc
    digest.update(_normalise_data(data))
    return digest.hexdigest()


def calculate_hmac(data: bytes | str, secret: bytes | str, algorithm: str = "sha256") -> str:
    """Return the HMAC digest of *data* using *secret*."""

    key = _normalise_data(secret)
    message = _normalise_data(data)
    try:
        digest = hmac.new(key, message, algorithm)
    except ValueError as exc:  # pragma: no cover - defensive
        raise ValueError(f"Unsupported algorithm: {algorithm}") from exc
    return digest.hexdigest()
