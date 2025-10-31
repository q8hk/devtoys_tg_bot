"""Handlers and helper utilities for working with JWTs."""

from __future__ import annotations

import json
import shlex
from dataclasses import dataclass

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from core.utils.jwt_ import JWTDecodeError, decode_jwt

router = Router(name="jwt_tools")


@dataclass(slots=True)
class JWTRequest:
    """Parsed command arguments for the JWT tool."""

    token: str | None
    key: str | None
    verify: bool


def _parse_jwt_command(text: str) -> JWTRequest:
    args = text.split(maxsplit=1)
    if len(args) == 1:
        return JWTRequest(token=None, key=None, verify=False)
    arg_line = args[1].strip()
    if not arg_line:
        return JWTRequest(token=None, key=None, verify=False)
    try:
        tokens = shlex.split(arg_line)
    except ValueError:
        tokens = arg_line.split()

    token: str | None = None
    key: str | None = None
    verify = False
    for part in tokens:
        if part.startswith("key="):
            key = part.split("=", 1)[1]
        elif part.startswith("verify="):
            value = part.split("=", 1)[1].lower()
            verify = value in {"1", "true", "yes", "on"}
        elif token is None:
            token = part
    return JWTRequest(token=token, key=key, verify=verify)


def _format_json(data: dict[str, object]) -> str:
    return json.dumps(data, indent=2, sort_keys=True)


def render_jwt_summary(token: str, *, key: str | None = None, verify: bool = False) -> str:
    """Return a formatted summary for the provided token."""

    try:
        decode_kwargs: dict[str, object] = {}
        if key is not None:
            decode_kwargs["key"] = key
            decode_kwargs["verify"] = True
        elif verify:
            decode_kwargs["verify"] = True
        decoded = decode_jwt(token, **decode_kwargs)
    except JWTDecodeError as exc:
        return f"❌ Failed to process token: {exc}"

    status = "Signature: not verified"
    if decoded.signature_valid is True:
        status = "Signature: ✅ valid"
    elif decoded.signature_valid is False:
        status = "Signature: ❌ invalid"

    warnings_block = ""
    if decoded.warnings:
        warnings = "\n".join(f"• {message}" for message in decoded.warnings)
        warnings_block = f"\nWarnings:\n{warnings}"

    parts: tuple[str, ...] = (
        "JWT decoded successfully:",
        f"Algorithm: {decoded.algorithm or 'unknown'}",
        f"Key ID: {decoded.key_id or 'n/a'}",
        status,
        f"Header:\n{_format_json(decoded.header)}",
        f"Payload:\n{_format_json(decoded.payload)}",
    )
    return "\n\n".join(parts) + warnings_block


@router.message(Command("jwt"))
async def handle_jwt_command(message: Message) -> None:
    """Decode and optionally verify JWT tokens."""

    request = _parse_jwt_command(message.text or "")
    token = request.token
    key = request.key
    verify = request.verify

    if token is None and message.reply_to_message and message.reply_to_message.text:
        token = message.reply_to_message.text.strip()

    if token is None:
        await message.answer(
            "Send `/jwt <token> [key=<secret|jwks>] [verify=true]` to inspect a JWT.\n"
            "You can also reply to a message containing the token.",
        )
        return

    if key is None and message.reply_to_message and message.reply_to_message.text:
        # Allow replying to a token message with `/jwt key=...`.
        if token != message.reply_to_message.text.strip():
            key = message.reply_to_message.text.strip()

    should_verify = verify or bool(key)
    summary = render_jwt_summary(token, key=key, verify=should_verify)
    await message.answer(summary)
