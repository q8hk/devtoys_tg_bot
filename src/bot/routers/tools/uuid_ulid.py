"""UUID and ULID handlers."""

from __future__ import annotations

from aiogram import Router
from aiogram.filters import Command
from aiogram.filters.command import CommandObject
from aiogram.types import Message

from core.utils.uuid_ulid import (
    ULIDInfo,
    UUIDInfo,
    generate_ulid,
    generate_uuid,
    inspect_ulid,
    inspect_uuid,
)

router = Router(name="tools.uuid_ulid")


def _format_uuid_info(info: UUIDInfo) -> str:
    if not info.is_valid or info.value is None:
        return "❌ Invalid UUID provided."

    parts = [
        "<b>UUID</b>:\n<code>{}</code>".format(info.value),
        f"<b>Version:</b> {info.version}",
    ]
    if info.timestamp is not None:
        parts.append(f"<b>Timestamp:</b> {info.timestamp.isoformat()}")
    else:
        parts.append("<b>Timestamp:</b> —")
    return "\n".join(parts)


def _format_ulid_info(info: ULIDInfo) -> str:
    if not info.is_valid or info.value is None:
        return "❌ Invalid ULID provided."

    parts = [
        "<b>ULID</b>:\n<code>{}</code>".format(info.value),
    ]
    if info.timestamp is not None:
        parts.append(f"<b>Timestamp:</b> {info.timestamp.isoformat()}")
    else:
        parts.append("<b>Timestamp:</b> —")
    return "\n".join(parts)


@router.message(Command("uuid"))
async def handle_generate_uuid(message: Message, command: CommandObject) -> None:
    """Generate a UUID (defaults to v4)."""

    version = 4
    if command.args:
        arg = command.args.strip()
        if arg:
            try:
                version = int(arg.split()[0])
            except ValueError:
                await message.answer("❌ Version must be one of 1, 4, or 7.")
                return

    try:
        identifier = generate_uuid(version)
    except ValueError:
        await message.answer("❌ Unsupported UUID version. Use 1, 4, or 7.")
        return

    info = inspect_uuid(str(identifier))
    await message.answer(_format_uuid_info(info))


@router.message(Command("uuid_inspect"))
async def handle_inspect_uuid(message: Message, command: CommandObject) -> None:
    """Inspect an incoming UUID string."""

    if not command.args:
        await message.answer("❌ Provide a UUID after the command.")
        return

    info = inspect_uuid(command.args.strip())
    await message.answer(_format_uuid_info(info))


@router.message(Command("ulid"))
async def handle_generate_ulid(message: Message, command: CommandObject) -> None:  # noqa: ARG001
    """Generate a ULID."""

    identifier = generate_ulid()
    info = inspect_ulid(str(identifier))
    await message.answer(_format_ulid_info(info))


@router.message(Command("ulid_inspect"))
async def handle_inspect_ulid(message: Message, command: CommandObject) -> None:
    """Inspect an incoming ULID string."""

    if not command.args:
        await message.answer("❌ Provide a ULID after the command.")
        return

    info = inspect_ulid(command.args.strip())
    await message.answer(_format_ulid_info(info))
