"""Base64 encode/decode handlers."""

from __future__ import annotations

from dataclasses import dataclass
from os import PathLike
from typing import BinaryIO, TextIO

from core.utils import base64_

__all__ = ["Base64CodecService"]


@dataclass(slots=True)
class Base64CodecService:
    """High-level helpers that wrap :mod:`src.core.utils.base64_` for the bot layer."""

    chunk_size: int = 1024 * 64

    def encode_text(self, value: str, *, encoding: str = "utf-8", urlsafe: bool = False) -> str:
        """Encode ``value`` to Base64."""

        return base64_.encode_text(value, encoding=encoding, urlsafe=urlsafe)

    def decode_text(self, value: str, *, encoding: str = "utf-8", urlsafe: bool = False) -> str:
        """Decode Base64 text into a unicode string."""

        return base64_.decode_text(value, encoding=encoding, urlsafe=urlsafe)

    def encode_stream(
        self,
        source: BinaryIO,
        destination: BinaryIO | TextIO,
        *,
        urlsafe: bool = False,
    ) -> int:
        """Stream Base64 encoding using the configured chunk size."""

        return base64_.encode_stream(
            source,
            destination,
            urlsafe=urlsafe,
            chunk_size=self.chunk_size,
        )

    def decode_stream(
        self,
        source: BinaryIO | TextIO,
        destination: BinaryIO,
        *,
        urlsafe: bool = False,
    ) -> int:
        """Stream Base64 decoding using the configured chunk size."""

        return base64_.decode_stream(
            source,
            destination,
            urlsafe=urlsafe,
            chunk_size=self.chunk_size,
        )

    def encode_file(
        self,
        source_path: str | PathLike[str],
        destination_path: str | PathLike[str],
        *,
        urlsafe: bool = False,
    ) -> int:
        """Encode a file and return the number of characters written."""

        return base64_.encode_file(
            source_path,
            destination_path,
            urlsafe=urlsafe,
            chunk_size=self.chunk_size,
        )

    def decode_file(
        self,
        source_path: str | PathLike[str],
        destination_path: str | PathLike[str],
        *,
        urlsafe: bool = False,
    ) -> int:
        """Decode a Base64 file and return the number of bytes written."""

        return base64_.decode_file(
            source_path,
            destination_path,
            urlsafe=urlsafe,
            chunk_size=self.chunk_size,
        )

    def build_data_uri(
        self,
        data: bytes,
        *,
        media_type: str = "application/octet-stream",
        urlsafe: bool = False,
        base64_encoded: bool = True,
    ) -> str:
        """Build a ``data:`` URI for ``data``."""

        return base64_.build_data_uri(
            data,
            media_type=media_type,
            urlsafe=urlsafe,
            base64_encoded=base64_encoded,
        )

    @staticmethod
    def detect_data_uri(value: str) -> base64_.DataUri | None:
        """Expose the utility detector for convenience."""

        return base64_.detect_data_uri(value)

