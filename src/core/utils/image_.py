"""Lightweight image utilities."""

from __future__ import annotations

from io import BytesIO
from typing import Any

from PIL import Image

__all__ = [
    "open_image",
    "extract_metadata",
    "resize_image",
    "convert_format",
]


def open_image(data: bytes) -> Image.Image:
    """Open image bytes and return a Pillow image object."""

    return Image.open(BytesIO(data))


def extract_metadata(data: bytes) -> dict[str, Any]:
    """Return basic metadata for ``data``."""

    with open_image(data) as image:
        return {
            "format": image.format,
            "mode": image.mode,
            "size": image.size,
            "info": dict(image.info),
        }


def resize_image(data: bytes, *, width: int | None = None, height: int | None = None) -> bytes:
    """Resize an image preserving aspect ratio when only one dimension is provided."""

    if width is None and height is None:
        raise ValueError("Width or height must be provided")
    with open_image(data) as image:
        orig_width, orig_height = image.size
        if width is None:
            ratio = height / orig_height
            width = int(orig_width * ratio)
        elif height is None:
            ratio = width / orig_width
            height = int(orig_height * ratio)
        resized = image.resize((width, height), Image.LANCZOS)
        buffer = BytesIO()
        resized.save(buffer, format=image.format or "PNG")
        return buffer.getvalue()


def convert_format(data: bytes, *, format: str) -> bytes:
    """Convert an image to ``format`` returning bytes."""

    with open_image(data) as image:
        buffer = BytesIO()
        image.save(buffer, format=format)
        return buffer.getvalue()
