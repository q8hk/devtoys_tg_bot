"""Hashing helpers."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import hmac
from pathlib import Path

__all__ = [
    "HmacDigest",
    "available_algorithms",
    "calculate_hash",
    "calculate_file_hash",
    "calculate_hmac",
]

_COMMON_ALGORITHMS = (
    "md5",
    "sha1",
    "sha224",
    "sha256",
    "sha384",
    "sha512",
)

_DEFAULT_CHUNK_SIZE = 1024 * 64


@dataclass(slots=True)
class HmacDigest:
    """Represents the result of an HMAC operation."""

    algorithm: str
    hexdigest: str
    secret_masked: str


def available_algorithms() -> list[str]:
    """Return the sorted list of supported hash algorithms."""

    available = {name.lower() for name in hashlib.algorithms_available}
    return sorted(name for name in _COMMON_ALGORITHMS if name in available)


def _normalise_data(data: bytes | str) -> bytes:
    return data if isinstance(data, bytes) else data.encode("utf-8")


def _create_digest(algorithm: str) -> "hashlib._Hash":  # type: ignore[attr-defined]
    algo = algorithm.lower()
    try:
        return hashlib.new(algo)
    except ValueError as exc:  # pragma: no cover - defensive
        raise ValueError(f"Unsupported algorithm: {algorithm}") from exc


def _mask_secret(secret: bytes | str, *, visible: int = 4) -> str:
    if isinstance(secret, bytes):
        try:
            text = secret.decode("utf-8")
        except UnicodeDecodeError:
            text = secret.hex()
    else:
        text = secret

    if not text:
        return ""

    length = len(text)
    if length == 1:
        return "*"
    if visible <= 0:
        return "*" * length
    if length <= visible:
        masked_length = max(length - 1, 1)
        return "*" * masked_length + text[-1]
    return "*" * (length - visible) + text[-visible:]


def calculate_hash(data: bytes | str, algorithm: str = "sha256") -> str:
    """Calculate the hash digest for *data*."""

    digest = _create_digest(algorithm)
    digest.update(_normalise_data(data))
    return digest.hexdigest()


def calculate_file_hash(
    path: str | Path,
    algorithm: str = "sha256",
    *,
    chunk_size: int = _DEFAULT_CHUNK_SIZE,
) -> str:
    """Calculate the hash digest for a file using streamed reads."""

    if chunk_size <= 0:
        raise ValueError("chunk_size must be a positive integer")

    digest = _create_digest(algorithm)
    file_path = Path(path)
    with file_path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(chunk_size), b""):
            digest.update(chunk)
    return digest.hexdigest()


def calculate_hmac(
    data: bytes | str,
    secret: bytes | str,
    algorithm: str = "sha256",
    *,
    visible_secret_chars: int = 4,
) -> HmacDigest:
    """Return the HMAC digest of *data* using *secret* with masked secret handling."""

    key = _normalise_data(secret)
    message = _normalise_data(data)
    try:
        digest = hmac.new(key, message, algorithm)
    except ValueError as exc:  # pragma: no cover - defensive
        raise ValueError(f"Unsupported algorithm: {algorithm}") from exc

    return HmacDigest(
        algorithm=algorithm.lower(),
        hexdigest=digest.hexdigest(),
        secret_masked=_mask_secret(secret, visible=visible_secret_chars),
    )
