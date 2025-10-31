"""Base64 helpers."""

from __future__ import annotations

import base64
import io
from os import PathLike
from dataclasses import dataclass
from typing import BinaryIO, TextIO, Literal
from urllib.parse import quote_from_bytes, unquote_to_bytes

__all__ = [
    "Base64Error",
    "DataUri",
    "encode_text",
    "decode_text",
    "encode_bytes",
    "decode_bytes",
    "encode_stream",
    "decode_stream",
    "encode_file",
    "decode_file",
    "build_data_uri",
    "detect_data_uri",
]


class Base64Error(ValueError):
    """Raised when a Base64 encoding or decoding operation fails."""


@dataclass(slots=True)
class DataUri:
    """Representation of a ``data:`` URI."""

    media_type: str
    data: bytes


_WHITESPACE = frozenset({
    " ",
    "\n",
    "\r",
    "\t",
    "\f",
    "\v",
})


def _encoder(urlsafe: bool) -> Literal["urlsafe_b64encode", "b64encode"]:
    return "urlsafe_b64encode" if urlsafe else "b64encode"


def _decoder(urlsafe: bool) -> Literal["urlsafe_b64decode", "b64decode"]:
    return "urlsafe_b64decode" if urlsafe else "b64decode"


def _strip_whitespace(value: str | bytes) -> str:
    if isinstance(value, bytes):
        value = value.decode("ascii")
    return "".join(ch for ch in value if ch not in _WHITESPACE)


def encode_bytes(value: bytes, *, urlsafe: bool = False) -> str:
    """Encode raw bytes to Base64."""

    encoded = getattr(base64, _encoder(urlsafe))(value)
    return encoded.decode("ascii")


def decode_bytes(value: str | bytes, *, urlsafe: bool = False) -> bytes:
    """Decode Base64 encoded text."""

    cleaned = _strip_whitespace(value)
    try:
        return getattr(base64, _decoder(urlsafe))(cleaned, validate=True)
    except (base64.binascii.Error, ValueError) as exc:  # pragma: no cover - defensive
        raise Base64Error("Invalid Base64 input") from exc


def encode_text(value: str, *, encoding: str = "utf-8", urlsafe: bool = False) -> str:
    """Encode text to Base64 using ``encoding``."""

    return encode_bytes(value.encode(encoding), urlsafe=urlsafe)


def decode_text(value: str, *, encoding: str = "utf-8", urlsafe: bool = False) -> str:
    """Decode Base64 text and return a unicode string."""

    return decode_bytes(value, urlsafe=urlsafe).decode(encoding)


def _write_chunk(destination: BinaryIO | TextIO, chunk: bytes) -> int:
    """Write Base64 encoded bytes to the destination preserving type."""

    if isinstance(destination, io.TextIOBase):
        destination.write(chunk.decode("ascii"))
        return len(chunk)
    written = destination.write(chunk)
    # Some file-like objects (e.g. io.BufferedWriter) return the number of bytes written,
    # while ``io.BytesIO`` returns the length implicitly via ``None``.
    return written if written is not None else len(chunk)


def encode_stream(
    source: BinaryIO,
    destination: BinaryIO | TextIO,
    *,
    urlsafe: bool = False,
    chunk_size: int = 1024 * 64,
) -> int:
    """Stream Base64 encoding from ``source`` into ``destination``.

    The function reads ``chunk_size`` blocks and ensures data is emitted in multiples of
    three bytes to produce correct Base64 output. Returns the number of encoded
    characters written.
    """

    if chunk_size <= 0:
        raise ValueError("chunk_size must be a positive integer")

    encoder = getattr(base64, _encoder(urlsafe))
    leftover = b""
    total_written = 0
    while True:
        chunk = source.read(chunk_size)
        if chunk is None:
            raise ValueError("source.read() returned None")
        if not chunk:
            break
        buffer = leftover + chunk
        consume = len(buffer) - (len(buffer) % 3)
        if consume:
            to_encode = buffer[:consume]
            leftover = buffer[consume:]
        else:
            to_encode = b""
            leftover = buffer
        if to_encode:
            encoded = encoder(to_encode)
            total_written += _write_chunk(destination, encoded)
    if leftover:
        encoded = encoder(leftover)
        total_written += _write_chunk(destination, encoded)
    return total_written


def decode_stream(
    source: BinaryIO | TextIO,
    destination: BinaryIO,
    *,
    urlsafe: bool = False,
    chunk_size: int = 1024 * 64,
) -> int:
    """Stream Base64 decoding from ``source`` into ``destination``.

    Whitespace in the input is ignored. Returns the number of decoded bytes written.
    """

    if chunk_size <= 0:
        raise ValueError("chunk_size must be a positive integer")

    decoder = getattr(base64, _decoder(urlsafe))
    leftover = ""
    total_written = 0
    while True:
        chunk = source.read(chunk_size)
        if chunk is None:
            raise ValueError("source.read() returned None")
        if not chunk:
            break
        text = chunk.decode("ascii") if isinstance(chunk, bytes) else str(chunk)
        buffer = leftover + _strip_whitespace(text)
        consume = len(buffer) - (len(buffer) % 4)
        to_decode = buffer[:consume]
        leftover = buffer[consume:]
        if to_decode:
            try:
                decoded = decoder(to_decode, validate=True)
            except (base64.binascii.Error, ValueError) as exc:  # pragma: no cover - defensive
                raise Base64Error("Invalid Base64 input") from exc
            written = destination.write(decoded)
            total_written += written if written is not None else len(decoded)
    if leftover:
        padding = (4 - (len(leftover) % 4)) % 4
        padded = leftover + ("=" * padding)
        try:
            decoded = decoder(padded, validate=True)
        except (base64.binascii.Error, ValueError) as exc:  # pragma: no cover - defensive
            raise Base64Error("Invalid Base64 input") from exc
        written = destination.write(decoded)
        total_written += written if written is not None else len(decoded)
    return total_written


def encode_file(
    source_path: str | PathLike[str],
    destination_path: str | PathLike[str],
    *,
    urlsafe: bool = False,
    chunk_size: int = 1024 * 64,
) -> int:
    """Encode a binary file to Base64 writing the result as ASCII text."""

    with open(source_path, "rb") as source, open(
        destination_path, "w", encoding="ascii", newline=""
    ) as destination:
        return encode_stream(source, destination, urlsafe=urlsafe, chunk_size=chunk_size)


def decode_file(
    source_path: str | PathLike[str],
    destination_path: str | PathLike[str],
    *,
    urlsafe: bool = False,
    chunk_size: int = 1024 * 64,
) -> int:
    """Decode a Base64 text file back to binary data."""

    with open(source_path, "r", encoding="ascii") as source, open(
        destination_path, "wb"
    ) as destination:
        return decode_stream(source, destination, urlsafe=urlsafe, chunk_size=chunk_size)


def build_data_uri(
    data: bytes,
    *,
    media_type: str = "application/octet-stream",
    urlsafe: bool = False,
    base64_encoded: bool = True,
) -> str:
    """Return a ``data:`` URI representing ``data``.

    When ``base64_encoded`` is ``True`` (the default) the payload is Base64 encoded,
    otherwise it is percent-encoded.
    """

    if base64_encoded:
        payload = encode_bytes(data, urlsafe=urlsafe)
        suffix = ";base64"
    else:
        payload = quote_from_bytes(data)
        suffix = ""
    return f"data:{media_type}{suffix},{payload}"


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
