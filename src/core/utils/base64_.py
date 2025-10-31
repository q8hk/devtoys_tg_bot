"""Base64 helpers."""

from __future__ import annotations

import base64
from dataclasses import dataclass
from typing import Literal
from urllib.parse import unquote_to_bytes

__all__ = [
    "Base64Error",
    "DataUri",
    "encode_text",
    "decode_text",
    "encode_bytes",
    "decode_bytes",
    "detect_data_uri",
]


class Base64Error(ValueError):
    """Raised when a Base64 decoding operation fails."""


@dataclass(slots=True)
class DataUri:
    """Representation of a ``data:`` URI."""

    media_type: str
    data: bytes


def encode_bytes(value: bytes, *, urlsafe: bool = False) -> str:
    """Encode raw bytes to Base64."""

    encoder: Literal["urlsafe_b64encode", "b64encode"]
    encoder = "urlsafe_b64encode" if urlsafe else "b64encode"
    return getattr(base64, encoder)(value).decode("ascii")


def decode_bytes(value: str, *, urlsafe: bool = False) -> bytes:
    """Decode Base64 encoded text."""

    decoder: Literal["urlsafe_b64decode", "b64decode"]
    decoder = "urlsafe_b64decode" if urlsafe else "b64decode"
    try:
        return getattr(base64, decoder)(value, validate=True)
    except (base64.binascii.Error, ValueError) as exc:  # pragma: no cover - defensive
        raise Base64Error("Invalid Base64 input") from exc


def encode_text(value: str, *, encoding: str = "utf-8", urlsafe: bool = False) -> str:
    """Encode text to Base64 using ``encoding``."""

    return encode_bytes(value.encode(encoding), urlsafe=urlsafe)


def decode_text(value: str, *, encoding: str = "utf-8", urlsafe: bool = False) -> str:
    """Decode Base64 text and return a unicode string."""

    return decode_bytes(value, urlsafe=urlsafe).decode(encoding)


def detect_data_uri(value: str) -> DataUri | None:
    """Parse a ``data:`` URI and return the decoded payload."""

    if not value.startswith("data:"):
        return None
    header, _, payload = value.partition(",")
    if not payload:
        raise Base64Error("Malformed data URI: missing payload")
    media_type = header.removeprefix("data:") or "text/plain;charset=US-ASCII"
    is_base64 = media_type.endswith(";base64")
    if is_base64:
        media_type = media_type[:-7]
        data = decode_bytes(payload, urlsafe=False)
    else:
        data = unquote_to_bytes(payload)
    return DataUri(media_type=media_type, data=data)
