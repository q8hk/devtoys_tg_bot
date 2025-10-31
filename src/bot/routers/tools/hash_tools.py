"""Hashing and HMAC handlers."""

from __future__ import annotations

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from src.core.utils import hash_

router = Router(name="hash_tools")

_HASH_USAGE = "Usage: /hash <algorithm> <text>"
_HMAC_USAGE = "Usage: /hmac <algorithm> <secret> -- <text>"


def _format_algorithms() -> str:
    algorithms = hash_.available_algorithms()
    return ", ".join(algorithms) if algorithms else "(none)"


@router.message(Command("hash_algorithms"))
async def list_algorithms(message: Message) -> None:
    """Send the list of supported hash algorithms to the user."""

    await message.answer(f"Supported algorithms: {_format_algorithms()}")


@router.message(Command("hash"))
async def handle_hash_command(message: Message) -> None:
    """Calculate a hash digest for user-provided text."""

    text = message.text or ""
    parts = text.split(maxsplit=2)
    if len(parts) < 3:
        await message.answer(_HASH_USAGE)
        return

    _, algorithm, payload = parts
    if not payload.strip():
        await message.answer(_HASH_USAGE)
        return

    try:
        digest = hash_.calculate_hash(payload, algorithm)
    except ValueError as exc:
        await message.answer(str(exc))
        return

    await message.answer(f"{algorithm.lower()} digest:\n{digest}")


@router.message(Command("hmac"))
async def handle_hmac_command(message: Message) -> None:
    """Calculate an HMAC digest for user-provided text."""

    text = message.text or ""
    parts = text.split(maxsplit=2)
    if len(parts) < 3:
        await message.answer(_HMAC_USAGE)
        return

    _, algorithm, remainder = parts
    secret, separator, payload = remainder.partition(" -- ")
    if not separator or not secret or not payload.strip():
        await message.answer(_HMAC_USAGE)
        return

    try:
        result = hash_.calculate_hmac(payload, secret, algorithm)
    except ValueError as exc:
        await message.answer(str(exc))
        return

    await message.answer(
        "\n".join(
            (
                f"{result.algorithm} HMAC:",
                result.hexdigest,
                f"Secret: {result.secret_masked}",
            )
        )
    )


__all__ = ["router"]
