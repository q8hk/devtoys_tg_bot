"""Lightweight image utilities built on top of Pillow."""

from __future__ import annotations

import math
from collections.abc import Iterator
from contextlib import contextmanager
from io import BytesIO
from tempfile import SpooledTemporaryFile
from typing import Any, BinaryIO

from PIL import Image, ImageOps, UnidentifiedImageError

from .base64_ import decode_bytes as _decode_base64
from .base64_ import encode_bytes as _encode_base64

__all__ = [
    "ImageProcessingError",
    "ImageTooLargeError",
    "DEFAULT_MAX_FILE_MB",
    "open_image",
    "extract_metadata",
    "resize_image",
    "convert_format",
    "compress_image",
    "image_to_base64",
    "base64_to_image",
]


DEFAULT_MAX_FILE_MB = 15
_BYTE_LIMIT_MULTIPLIER = 1024 * 1024
_STREAM_CHUNK_SIZE = 256 * 1024


class ImageProcessingError(RuntimeError):
    """Raised when an image operation fails."""


class ImageTooLargeError(ValueError):
    """Raised when the provided image exceeds the allowed size."""


def _to_bytes_limit(max_file_mb: int) -> int:
    if max_file_mb <= 0:
        raise ValueError("max_file_mb must be positive")
    return max_file_mb * _BYTE_LIMIT_MULTIPLIER


def _ensure_seek_start(stream: BinaryIO) -> None:
    if hasattr(stream, "seek") and callable(stream.seek):
        try:
            stream.seek(0)
        except (OSError, ValueError):  # pragma: no cover - best effort reset
            return


@contextmanager
def _spooled(data: bytes | BinaryIO, *, max_bytes: int) -> Iterator[SpooledTemporaryFile]:
    total = 0
    spool = SpooledTemporaryFile(max_size=max_bytes, mode="w+b")
    try:
        if isinstance(data, (bytes, bytearray)):
            total = len(data)
            if total > max_bytes:
                raise ImageTooLargeError("Image exceeds maximum allowed size")
            spool.write(data)
        else:
            _ensure_seek_start(data)
            while chunk := data.read(_STREAM_CHUNK_SIZE):
                total += len(chunk)
                if total > max_bytes:
                    raise ImageTooLargeError("Image exceeds maximum allowed size")
                spool.write(chunk)
        spool.seek(0)
        yield spool
    finally:
        spool.close()


def _ensure_image(data: bytes | BinaryIO | Image.Image, *, max_file_mb: int) -> Image.Image:
    if isinstance(data, Image.Image):
        image = data.copy()
        image.info = dict(data.info)
        image.format = data.format
        return image
    max_bytes = _to_bytes_limit(max_file_mb)
    try:
        with _spooled(data, max_bytes=max_bytes) as stream:
            try:
                with Image.open(stream) as image:
                    format_name = image.format
                    info = dict(image.info)
                    image = ImageOps.exif_transpose(image)
                    image.load()
                    result = image.copy()
                    result.info = info
                    result.format = format_name
                    return result
            except UnidentifiedImageError as exc:  # pragma: no cover - defensive
                raise ImageProcessingError("Unsupported or corrupted image data") from exc
    except ImageTooLargeError:
        raise


def open_image(data: bytes | BinaryIO | Image.Image, *, max_file_mb: int = DEFAULT_MAX_FILE_MB) -> Image.Image:
    """Open ``data`` as a Pillow image while enforcing size limits."""

    return _ensure_image(data, max_file_mb=max_file_mb)


def extract_metadata(data: bytes | BinaryIO | Image.Image, *, max_file_mb: int = DEFAULT_MAX_FILE_MB) -> dict[str, Any]:
    """Return a metadata dictionary for ``data``."""

    image = open_image(data, max_file_mb=max_file_mb)
    metadata: dict[str, Any] = {
        "format": image.format,
        "mode": image.mode,
        "width": image.width,
        "height": image.height,
        "size": image.size,
        "info": dict(image.info),
    }
    exif = image.getexif()
    if exif:
        # Only expose simple EXIF tags to avoid leaking binary data.
        metadata["exif"] = {
            str(tag): value for tag, value in list(exif.items())[:20]
        }
    return metadata


def _save_image(
    image: Image.Image,
    *,
    format: str | None = None,
    quality: int | None = None,
    optimize: bool | None = None,
    compress_level: int | None = None,
) -> bytes:
    buffer = BytesIO()
    target_format = (format or image.format or "PNG").upper()
    save_kwargs: dict[str, Any] = {"format": target_format}
    if quality is not None:
        save_kwargs["quality"] = quality
    if optimize is not None:
        save_kwargs["optimize"] = optimize
    if compress_level is not None and target_format == "PNG":
        save_kwargs["compress_level"] = compress_level
    if target_format in {"JPEG", "JPG"}:
        save_kwargs.setdefault("progressive", True)
        save_kwargs.setdefault("subsampling", "4:2:0")
    image.save(buffer, **save_kwargs)
    return buffer.getvalue()


def resize_image(
    data: bytes | BinaryIO | Image.Image,
    *,
    width: int | None = None,
    height: int | None = None,
    percent: float | None = None,
    max_file_mb: int = DEFAULT_MAX_FILE_MB,
) -> bytes:
    """Resize ``data`` returning encoded bytes."""

    if percent is not None and (width is not None or height is not None):
        raise ValueError("percent cannot be combined with width or height")
    if percent is None and width is None and height is None:
        raise ValueError("Width, height, or percent must be provided")

    image = open_image(data, max_file_mb=max_file_mb)
    orig_width, orig_height = image.size

    if percent is not None:
        if percent <= 0:
            raise ValueError("percent must be positive")
        scale = percent / 100.0
        width = max(1, int(math.floor(orig_width * scale)))
        height = max(1, int(math.floor(orig_height * scale)))
    else:
        if width is None:
            if height is None:
                raise ValueError("height must be provided when width is None")
            width = max(1, int(round(orig_width * (height / orig_height))))
        if height is None:
            height = max(1, int(round(orig_height * (width / orig_width))))
        if width <= 0 or height <= 0:
            raise ValueError("width and height must be positive")

    resized = image.resize((width, height), Image.Resampling.LANCZOS)
    return _save_image(resized, format=image.format)


def convert_format(
    data: bytes | BinaryIO | Image.Image,
    *,
    format: str,
    max_file_mb: int = DEFAULT_MAX_FILE_MB,
    quality: int | None = None,
    optimize: bool | None = None,
    compress_level: int | None = None,
) -> bytes:
    """Convert ``data`` into ``format`` returning encoded bytes."""

    if not format:
        raise ValueError("format must be provided")
    image = open_image(data, max_file_mb=max_file_mb)
    return _save_image(
        image,
        format=format,
        quality=quality,
        optimize=optimize,
        compress_level=compress_level,
    )


def compress_image(
    data: bytes | BinaryIO | Image.Image,
    *,
    quality: int | None = None,
    optimize: bool = True,
    compress_level: int | None = None,
    format: str | None = None,
    max_file_mb: int = DEFAULT_MAX_FILE_MB,
) -> bytes:
    """Compress an image by adjusting quality/compression parameters."""

    if quality is not None and not (1 <= quality <= 100):
        raise ValueError("quality must be between 1 and 100")
    image = open_image(data, max_file_mb=max_file_mb)
    return _save_image(
        image,
        format=format or image.format,
        quality=quality,
        optimize=optimize,
        compress_level=compress_level,
    )


def image_to_base64(
    data: bytes | BinaryIO | Image.Image,
    *,
    format: str | None = None,
    max_file_mb: int = DEFAULT_MAX_FILE_MB,
) -> str:
    """Encode ``data`` as a Base64 string."""

    if format:
        raw = convert_format(data, format=format, max_file_mb=max_file_mb)
    else:
        max_bytes = _to_bytes_limit(max_file_mb)
        if isinstance(data, (bytes, bytearray)):
            raw = bytes(data)
            if len(raw) > max_bytes:
                raise ImageTooLargeError("Image exceeds maximum allowed size")
        elif isinstance(data, Image.Image):
            raw = _save_image(data, format=data.format)
        else:
            with _spooled(data, max_bytes=max_bytes) as stream:
                raw = stream.read()
    return _encode_base64(raw)


def base64_to_image(value: str, *, max_file_mb: int = DEFAULT_MAX_FILE_MB) -> Image.Image:
    """Decode ``value`` from Base64 and return a Pillow image."""

    raw = _decode_base64(value)
    max_bytes = _to_bytes_limit(max_file_mb)
    if len(raw) > max_bytes:
        raise ImageTooLargeError("Image exceeds maximum allowed size")
    return open_image(raw, max_file_mb=max_file_mb)
