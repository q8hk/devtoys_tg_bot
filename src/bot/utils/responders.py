"""Helpers for preparing tool responses based on payload size and type."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence

from aiogram.types import (
    BufferedInputFile,
    FSInputFile,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)

TELEGRAM_TEXT_LIMIT = 4096
DEFAULT_TEXT_THRESHOLD = 3500
DEFAULT_FILE_NAME = "result.txt"


@dataclass(slots=True)
class ToolResponse:
    """Normalized payload returned by tool handlers."""

    text: str | None = None
    document: BufferedInputFile | FSInputFile | None = None
    parse_mode: str | None = None
    keyboard: InlineKeyboardMarkup | None = None
    file_name: str | None = None

    @property
    def is_document(self) -> bool:
        """Return ``True`` when the payload should be sent as a file."""

        return self.document is not None

    def as_message_kwargs(self) -> dict:
        """Return keyword arguments usable with ``message.answer``."""

        payload: dict = {}
        if self.keyboard is not None:
            payload["reply_markup"] = self.keyboard

        if self.document is not None:
            payload["document"] = self.document
            if self.text:
                payload["caption"] = self.text
            if self.parse_mode:
                payload["parse_mode"] = self.parse_mode
            return payload

        payload["text"] = self.text or ""
        if self.parse_mode:
            payload["parse_mode"] = self.parse_mode
        return payload


def chunk_text(text: str, limit: int = TELEGRAM_TEXT_LIMIT) -> list[str]:
    """Split ``text`` into chunks that comply with Telegram limits."""

    if limit <= 0:
        msg = "limit must be greater than zero"
        raise ValueError(msg)

    if not text:
        return [""]

    chunks: list[str] = []
    for start in range(0, len(text), limit):
        chunks.append(text[start : start + limit])
    return chunks


def build_text_response(
    text: str,
    *,
    threshold: int = DEFAULT_TEXT_THRESHOLD,
    file_name: str = DEFAULT_FILE_NAME,
    persist_path: Path | None = None,
    encoding: str = "utf-8",
    parse_mode: str | None = None,
    keyboard: InlineKeyboardMarkup | None = None,
) -> ToolResponse:
    """Return a ``ToolResponse`` deciding between text and document modes."""

    if threshold < 1:
        msg = "threshold must be at least 1"
        raise ValueError(msg)

    if len(text) <= threshold:
        return ToolResponse(text=text, parse_mode=parse_mode, keyboard=keyboard)

    data = text.encode(encoding)
    if persist_path is not None:
        persist_path.mkdir(parents=True, exist_ok=True)
        file_path = persist_path / file_name
        file_path.write_bytes(data)
        document: BufferedInputFile | FSInputFile = FSInputFile(file_path)
    else:
        document = BufferedInputFile(data=data, filename=file_name)

    return ToolResponse(
        document=document,
        text=None,
        parse_mode=parse_mode,
        keyboard=keyboard,
        file_name=file_name,
    )


def build_document_response(
    data: bytes,
    *,
    file_name: str,
    caption: str | None = None,
    parse_mode: str | None = None,
    keyboard: InlineKeyboardMarkup | None = None,
    persist_path: Path | None = None,
) -> ToolResponse:
    """Return a file-based ``ToolResponse`` for binary payloads."""

    if not file_name:
        msg = "file_name must be provided"
        raise ValueError(msg)

    if persist_path is not None:
        persist_path.mkdir(parents=True, exist_ok=True)
        file_path = persist_path / file_name
        file_path.write_bytes(data)
        document: BufferedInputFile | FSInputFile = FSInputFile(file_path)
    else:
        document = BufferedInputFile(data=data, filename=file_name)

    return ToolResponse(
        document=document,
        text=caption,
        parse_mode=parse_mode,
        keyboard=keyboard,
        file_name=file_name,
    )


def merge_keyboards(
    *keyboards: InlineKeyboardMarkup | None,
) -> InlineKeyboardMarkup | None:
    """Combine multiple inline keyboards into one for convenience."""

    rows: list[list[InlineKeyboardButton]] = []
    for keyboard in keyboards:
        if not keyboard:
            continue
        rows.extend(keyboard.inline_keyboard)
    if not rows:
        return None
    return InlineKeyboardMarkup(inline_keyboard=rows)


def ensure_keyboard(
    keyboard: InlineKeyboardMarkup | None,
    extra_rows: Iterable[Sequence[InlineKeyboardButton]],
) -> InlineKeyboardMarkup | None:
    """Add ``extra_rows`` to ``keyboard`` returning a new markup."""

    if not extra_rows:
        return keyboard
    rows = [list(row) for row in extra_rows]
    if keyboard:
        rows = [*keyboard.inline_keyboard, *rows]
    return InlineKeyboardMarkup(inline_keyboard=rows)
