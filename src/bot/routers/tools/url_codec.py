"""URL encoding/decoding handlers."""

from __future__ import annotations

import json
import re
from enum import Enum
from html import escape
from typing import Iterable
from urllib.parse import urlparse

from aiogram import Router
from aiogram.filters import Command, CommandObject
from aiogram.types import Message

from core.errors import ToolValidationError
from core.utils import url

router = Router(name="tools-url-codec")


class UrlCodecMode(str, Enum):
    """Supported actions for the URL codec tool."""

    ENCODE = "encode"
    DECODE = "decode"
    PARSE = "parse"


PERCENT_PATTERN = re.compile(r"%[0-9A-Fa-f]{2}")


def _format_section(title: str, content: str) -> str:
    formatted = content if content else "empty"
    return f"<b>{escape(title)}</b>\n<pre>{escape(formatted)}</pre>"


def _format_response(header: str, sections: Iterable[tuple[str, str]], *, footer: str | None = None) -> str:
    blocks = [f"<b>{escape(header)}</b>"]
    blocks.extend(_format_section(title, content) for title, content in sections)
    if footer:
        blocks.append(f"<i>{escape(footer)}</i>")
    return "\n\n".join(blocks)


def _extract_input(message: Message, command: CommandObject | None) -> str:
    candidates: list[str] = []
    if command and command.args:
        candidates.append(command.args)
    if message.reply_to_message:
        reply = message.reply_to_message
        if reply.text:
            candidates.append(reply.text)
        elif reply.caption:
            candidates.append(reply.caption)
    if message.text:
        parts = message.text.split(maxsplit=1)
        if len(parts) == 2:
            candidates.append(parts[1])
    if message.caption:
        parts = message.caption.split(maxsplit=1)
        if len(parts) == 2:
            candidates.append(parts[1])
    for candidate in candidates:
        stripped = candidate.strip()
        if stripped:
            return stripped
    raise ToolValidationError("Send text after the command or reply to a message with content to process.")


def _looks_like_query(value: str) -> bool:
    if value.startswith("?"):
        return True
    if "\n" in value:
        lines = [line.strip() for line in value.splitlines() if line.strip()]
        if lines and all("=" in line for line in lines):
            return True
    parsed = urlparse(value)
    if parsed.query:
        return True
    if "=" in value and ("&" in value or value.count("=") > 1):
        return True
    return False


def _detect_mode(value: str) -> UrlCodecMode:
    if _looks_like_query(value):
        return UrlCodecMode.PARSE
    if PERCENT_PATTERN.search(value):
        return UrlCodecMode.DECODE
    return UrlCodecMode.ENCODE


def _handle_encode(value: str) -> str:
    encoded = url.encode_component(value)
    return _format_response(
        "URL Encode",
        [
            ("Input", value),
            ("Encoded", encoded),
        ],
    )


def _handle_decode(value: str) -> str:
    decoded = url.decode_component(value)
    return _format_response(
        "URL Decode",
        [
            ("Input", value),
            ("Decoded", decoded),
        ],
    )


def _handle_parse(value: str) -> str:
    params = url.parse_query_string(value)
    if not params:
        raise ToolValidationError("No query parameters detected in the provided input.")
    pretty = json.dumps(params, indent=2, ensure_ascii=False)
    rebuilt = url.rebuild_query_string(params)
    sections = [
        ("Input", value),
        ("Parameters", pretty),
        ("Rebuilt query", rebuilt),
    ]
    parsed_url = url.parse_url(value)
    if parsed_url.query:
        normalized = url.build_url(parsed_url, query=params)
        sections.append(("Normalized URL", normalized))
    return _format_response("URL Query Parser", sections)


async def _answer(message: Message, response: str) -> None:
    await message.answer(response, disable_web_page_preview=True)


async def _answer_error(message: Message, error: Exception) -> None:
    await message.answer(f"!  <b>{escape(str(error))}</b>")


@router.message(Command("urlencode"))
async def url_encode_handler(message: Message, command: CommandObject) -> None:
    try:
        user_input = _extract_input(message, command)
        response = _handle_encode(user_input)
    except ToolValidationError as exc:
        await _answer_error(message, exc)
        return
    await _answer(message, response)


@router.message(Command("urldecode"))
async def url_decode_handler(message: Message, command: CommandObject) -> None:
    try:
        user_input = _extract_input(message, command)
        response = _handle_decode(user_input)
    except (ToolValidationError, url.UrlError) as exc:
        await _answer_error(message, exc)
        return
    await _answer(message, response)


@router.message(Command("urlparse"))
async def url_parse_handler(message: Message, command: CommandObject) -> None:
    try:
        user_input = _extract_input(message, command)
        response = _handle_parse(user_input)
    except (ToolValidationError, url.UrlError) as exc:
        await _answer_error(message, exc)
        return
    await _answer(message, response)


@router.message(Command("url"))
async def url_auto_handler(message: Message, command: CommandObject) -> None:
    try:
        user_input = _extract_input(message, command)
        mode = _detect_mode(user_input)
        if mode is UrlCodecMode.ENCODE:
            response = _handle_encode(user_input)
            footer = "Detected encode operation based on the input."
        elif mode is UrlCodecMode.DECODE:
            response = _handle_decode(user_input)
            footer = "Detected percent-encoded content; performed decode."
        else:
            response = _handle_parse(user_input)
            footer = "Detected query parameters; parsed the input."
    except (ToolValidationError, url.UrlError) as exc:
        await _answer_error(message, exc)
        return
    annotated = f"{response}\n\n<i>{escape(footer)}</i>"
    await _answer(message, annotated)



