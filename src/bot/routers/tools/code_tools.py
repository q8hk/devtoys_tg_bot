"""Code-related handlers for formatting, minifying, and generation commands."""

from __future__ import annotations

from typing import Callable

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from core.utils.code_ import (
    format_css,
    format_js,
    format_json,
    generate_password,
    generate_token,
    minify_css,
    minify_js,
    minify_json,
    text_diff,
)

router = Router(name="code_tools")


async def _transform_text(
    message: Message,
    transformer: Callable[[str], str],
    *,
    usage: str,
) -> None:
    if not message.text:
        await message.answer(usage)
        return

    _, _, payload = message.text.partition(" ")
    if not payload.strip():
        await message.answer(usage)
        return

    try:
        result = transformer(payload)
    except ValueError as exc:
        await message.answer(f"x {exc}")
        return

    await message.answer(result or "Result is empty.")


@router.message(Command("code_json_pretty"))
async def cmd_code_json_pretty(message: Message) -> None:
    """Pretty-print JSON payloads."""

    await _transform_text(message, format_json, usage="Usage: /code_json_pretty <json>")


@router.message(Command("code_json_minify"))
async def cmd_code_json_minify(message: Message) -> None:
    """Minify JSON payloads."""

    await _transform_text(message, minify_json, usage="Usage: /code_json_minify <json>")


@router.message(Command("code_css_pretty"))
async def cmd_code_css_pretty(message: Message) -> None:
    """Pretty-print CSS payloads."""

    await _transform_text(message, format_css, usage="Usage: /code_css_pretty <css>")


@router.message(Command("code_css_minify"))
async def cmd_code_css_minify(message: Message) -> None:
    """Minify CSS payloads."""

    await _transform_text(message, minify_css, usage="Usage: /code_css_minify <css>")


@router.message(Command("code_js_pretty"))
async def cmd_code_js_pretty(message: Message) -> None:
    """Pretty-print JavaScript payloads."""

    await _transform_text(message, format_js, usage="Usage: /code_js_pretty <js>")


@router.message(Command("code_js_minify"))
async def cmd_code_js_minify(message: Message) -> None:
    """Minify JavaScript payloads."""

    await _transform_text(message, minify_js, usage="Usage: /code_js_minify <js>")


def _parse_diff_payload(payload: str) -> tuple[str, str]:
    separator = "\n---\n"
    if separator not in payload:
        raise ValueError("Provide original and updated text separated by a blank line containing '---'.")
    original, updated = payload.split(separator, 1)
    return original, updated


@router.message(Command("code_diff"))
async def cmd_code_diff(message: Message) -> None:
    """Generate a unified diff between two blocks of text."""

    if not message.text:
        await message.answer("Usage: /code_diff <original>\n---\n<updated>")
        return

    _, _, payload = message.text.partition(" ")
    if not payload.strip():
        await message.answer("Usage: /code_diff <original>\n---\n<updated>")
        return

    try:
        original, updated = _parse_diff_payload(payload)
    except ValueError as exc:
        await message.answer(f"x {exc}")
        return

    diff = text_diff(original, updated)
    await message.answer(diff or "No changes detected.")


def _parse_boolean(value: str, *, default: bool) -> bool:
    lowered = value.lower()
    if lowered in {"true", "yes", "on", "1"}:
        return True
    if lowered in {"false", "no", "off", "0"}:
        return False
    return default


@router.message(Command("code_password"))
async def cmd_code_password(message: Message) -> None:
    """Generate a random password."""

    if not message.text:
        await message.answer("Usage: /code_password [length=<n>] [digits=true|false] [symbols=true|false]")
        return

    _, _, payload = message.text.partition(" ")
    tokens = payload.split()

    length = 16
    use_digits = True
    use_symbols = True

    for token in tokens:
        if token.startswith("length="):
            try:
                length = int(token.split("=", 1)[1])
            except ValueError:
                await message.answer("x length must be an integer")
                return
        elif token.startswith("digits="):
            use_digits = _parse_boolean(token.split("=", 1)[1], default=True)
        elif token.startswith("symbols="):
            use_symbols = _parse_boolean(token.split("=", 1)[1], default=True)

    try:
        password = generate_password(length=length, use_digits=use_digits, use_symbols=use_symbols)
    except ValueError as exc:
        await message.answer(f"x {exc}")
        return

    await message.answer(password)


@router.message(Command("code_token"))
async def cmd_code_token(message: Message) -> None:
    """Generate a random token using the provided alphabet and length."""

    if not message.text:
        await message.answer("Usage: /code_token [length=<n>] [alphabet=<chars>]")
        return

    _, _, payload = message.text.partition(" ")
    tokens = payload.split()

    length = 32
    alphabet: str | None = None

    for token in tokens:
        if token.startswith("length="):
            try:
                length = int(token.split("=", 1)[1])
            except ValueError:
                await message.answer("x length must be an integer")
                return
        elif token.startswith("alphabet="):
            alphabet = token.split("=", 1)[1]

    try:
        token_value = generate_token(length=length, alphabet=alphabet)
    except ValueError as exc:
        await message.answer(f"x {exc}")
        return

    await message.answer(token_value)

