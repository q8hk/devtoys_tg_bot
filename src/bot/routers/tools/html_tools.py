"""Handlers exposing HTML utilities via Telegram commands."""

from __future__ import annotations

import html
from typing import Final

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from src.core.utils import html_ as html_utils

router = Router(name="html_tools")

_NO_PAYLOAD_MESSAGE: Final[str] = (
    "Send or reply with the HTML/text you want to process, e.g. /html_minify <html>."
)


def _extract_payload(message: Message) -> str | None:
    if message.reply_to_message:
        reply = message.reply_to_message
        if reply.text:
            text = reply.text.strip()
            if text:
                return text
        if reply.caption:
            text = reply.caption.strip()
            if text:
                return text
    if message.text:
        parts = message.text.split(maxsplit=1)
        if len(parts) == 2:
            payload = parts[1].strip()
            if payload:
                return payload
    if message.caption:
        parts = message.caption.split(maxsplit=1)
        if len(parts) == 2:
            payload = parts[1].strip()
            if payload:
                return payload
    return None


async def _reply_with_block(message: Message, title: str, content: str) -> None:
    escaped = html.escape(content)
    text = f"<b>{title}</b>\n<pre><code>{escaped}</code></pre>"
    await message.answer(text, parse_mode="HTML")


async def _reply_with_error(message: Message) -> None:
    await message.answer(_NO_PAYLOAD_MESSAGE)


@router.message(Command("html_minify"))
async def handle_html_minify(message: Message) -> None:
    payload = _extract_payload(message)
    if payload is None:
        await _reply_with_error(message)
        return
    result = html_utils.minify_html(payload)
    await _reply_with_block(message, "Minified HTML", result)


@router.message(Command("html_prettify"))
async def handle_html_prettify(message: Message) -> None:
    payload = _extract_payload(message)
    if payload is None:
        await _reply_with_error(message)
        return
    result = html_utils.prettify_html(payload)
    await _reply_with_block(message, "Prettified HTML", result)


@router.message(Command("html_encode"))
async def handle_html_encode(message: Message) -> None:
    payload = _extract_payload(message)
    if payload is None:
        await _reply_with_error(message)
        return
    result = html_utils.encode_entities(payload)
    await _reply_with_block(message, "HTML Entities Encoded", result)


@router.message(Command("html_decode"))
async def handle_html_decode(message: Message) -> None:
    payload = _extract_payload(message)
    if payload is None:
        await _reply_with_error(message)
        return
    result = html_utils.decode_entities(payload)
    await _reply_with_block(message, "HTML Entities Decoded", result)


@router.message(Command("html_strip"))
async def handle_html_strip(message: Message) -> None:
    payload = _extract_payload(message)
    if payload is None:
        await _reply_with_error(message)
        return
    result = html_utils.strip_tags(payload)
    await _reply_with_block(message, "HTML Tags Removed", result)
