"""Image utility handlers for metadata, conversion, and transformations."""

from __future__ import annotations

import html
import json
import os
from pathlib import Path
from tempfile import SpooledTemporaryFile
from typing import Any

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import BufferedInputFile, Message
from aiogram.filters.command import CommandObject

from src.core.utils.image_ import (
    ImageProcessingError,
    ImageTooLargeError,
    base64_to_image,
    compress_image,
    convert_format,
    extract_metadata,
    image_to_base64,
    resize_image,
)

router = Router(name="image_tools")

_FALLBACK_MAX_MB = 15


def _max_file_mb() -> int:
    value = os.getenv("MAX_FILE_MB", str(_FALLBACK_MAX_MB))
    try:
        parsed = int(value)
    except ValueError:  # pragma: no cover - defensive
        return _FALLBACK_MAX_MB
    return max(1, parsed)


def _max_file_bytes() -> int:
    return _max_file_mb() * 1024 * 1024


def _resolve_image_source(message: Message) -> Message | None:
    if message.document or message.photo:
        return message
    if message.reply_to_message and (
        message.reply_to_message.document or message.reply_to_message.photo
    ):
        return message.reply_to_message
    return None


async def _download_image_payload(message: Message) -> tuple[SpooledTemporaryFile, str]:
    source = _resolve_image_source(message)
    if source is None:
        raise ImageProcessingError("No image attached or replied to the command")

    if source.document:
        file_id = source.document.file_id
        file_name = source.document.file_name or "image"
        file_size = source.document.file_size or 0
    elif source.photo:
        photo = source.photo[-1]
        file_id = photo.file_id
        file_size = photo.file_size or 0
        file_name = f"photo_{photo.file_unique_id}.jpg"
    else:  # pragma: no cover - safety
        raise ImageProcessingError("Unsupported message payload")

    if file_size and file_size > _max_file_bytes():
        raise ImageTooLargeError(
            f"Image exceeds maximum allowed size of {_max_file_mb()} MB"
        )

    bot_file = await message.bot.get_file(file_id)
    spool = SpooledTemporaryFile(max_size=_max_file_bytes(), mode="w+b")
    await message.bot.download(bot_file, destination=spool)
    spool.seek(0)
    return spool, file_name


def _json_block(payload: dict[str, Any]) -> str:
    text = json.dumps(payload, indent=2, default=str)
    return f"<pre>{html.escape(text)}</pre>"


def _usage_message(command: str) -> str:
    usages = {
        "image_convert": "Usage: /image_convert <format>. Example: /image_convert webp",
        "image_resize": (
            "Usage: /image_resize <width>x<height> or <percent>%. "
            "Examples: /image_resize 200x, /image_resize x200, /image_resize 50%"
        ),
        "image_compress": "Usage: /image_compress <quality 1-100>. Example: /image_compress 70",
        "image_base64": "Reply to an image with /image_base64 to receive encoded data.",
        "image_from_base64": "Send /image_from_base64 <data> or reply to Base64 text.",
    }
    return usages.get(command, "Send or reply to an image to use this command.")


def _parse_resize_args(argument: str) -> dict[str, Any]:
    arg = argument.strip().lower()
    if not arg:
        raise ValueError
    if arg.endswith("%"):
        percent = float(arg[:-1])
        return {"percent": percent}
    if "x" in arg:
        left, _, right = arg.partition("x")
        width = int(left) if left else None
        height = int(right) if right else None
        if width is None and height is None:
            raise ValueError
        return {"width": width, "height": height}
    parts = arg.split()
    if len(parts) == 1:
        return {"width": int(parts[0])}
    if len(parts) == 2:
        width = int(parts[0]) if parts[0] != "-" else None
        height = int(parts[1]) if parts[1] != "-" else None
        if width is None and height is None:
            raise ValueError
        return {"width": width, "height": height}
    raise ValueError


async def _ensure_image_reply(message: Message, command: str) -> SpooledTemporaryFile | None:
    try:
        spool, _ = await _download_image_payload(message)
        return spool
    except ImageTooLargeError as exc:
        await message.answer(str(exc))
    except ImageProcessingError:
        await message.answer(_usage_message(command))
    return None


@router.message(Command("image_info"))
async def handle_image_info(message: Message) -> None:
    try:
        spool, _ = await _download_image_payload(message)
    except ImageTooLargeError as exc:
        await message.answer(str(exc))
        return
    except ImageProcessingError as exc:
        await message.answer(str(exc))
        return
    try:
        metadata = extract_metadata(spool, max_file_mb=_max_file_mb())
    finally:
        spool.close()
    await message.answer(_json_block(metadata))


@router.message(Command("image_convert"))
async def handle_image_convert(message: Message, command: CommandObject) -> None:
    argument = (command.args or "").strip()
    if not argument:
        await message.answer(_usage_message("image_convert"))
        return
    format_name = argument.split()[0].upper()
    try:
        spool, file_name = await _download_image_payload(message)
    except ImageTooLargeError as exc:
        await message.answer(str(exc))
        return
    except ImageProcessingError:
        await message.answer(_usage_message("image_convert"))
        return
    try:
        converted = convert_format(spool, format=format_name, max_file_mb=_max_file_mb())
    except ValueError as exc:
        await message.answer(str(exc))
        return
    finally:
        spool.close()
    stem = Path(file_name).stem or "image"
    filename = f"{stem}.{format_name.lower()}"
    await message.answer_document(BufferedInputFile(converted, filename=filename))


@router.message(Command("image_resize"))
async def handle_image_resize(message: Message, command: CommandObject) -> None:
    argument = command.args or ""
    try:
        kwargs = _parse_resize_args(argument)
    except ValueError:
        await message.answer(_usage_message("image_resize"))
        return
    try:
        spool, file_name = await _download_image_payload(message)
    except ImageTooLargeError as exc:
        await message.answer(str(exc))
        return
    except ImageProcessingError:
        await message.answer(_usage_message("image_resize"))
        return
    try:
        resized = resize_image(spool, max_file_mb=_max_file_mb(), **kwargs)
    except ValueError as exc:
        await message.answer(str(exc))
        return
    finally:
        spool.close()
    stem = Path(file_name).stem or "image"
    await message.answer_document(BufferedInputFile(resized, filename=f"{stem}.png"))


@router.message(Command("image_compress"))
async def handle_image_compress(message: Message, command: CommandObject) -> None:
    argument = (command.args or "").strip()
    if not argument:
        await message.answer(_usage_message("image_compress"))
        return
    try:
        quality = int(argument)
    except ValueError:
        await message.answer(_usage_message("image_compress"))
        return
    try:
        spool, file_name = await _download_image_payload(message)
    except ImageTooLargeError as exc:
        await message.answer(str(exc))
        return
    except ImageProcessingError:
        await message.answer(_usage_message("image_compress"))
        return
    try:
        compressed = compress_image(
            spool,
            quality=quality,
            max_file_mb=_max_file_mb(),
        )
    except ValueError as exc:
        await message.answer(str(exc))
        return
    finally:
        spool.close()
    stem = Path(file_name).stem or "image"
    await message.answer_document(BufferedInputFile(compressed, filename=f"{stem}.jpg"))


@router.message(Command("image_base64"))
async def handle_image_base64(message: Message) -> None:
    spool = await _ensure_image_reply(message, "image_base64")
    if spool is None:
        return
    try:
        encoded = image_to_base64(spool, max_file_mb=_max_file_mb())
    finally:
        spool.close()
    if len(encoded) <= 3500:
        await message.answer(f"<pre>{html.escape(encoded)}</pre>")
    else:
        await message.answer_document(
            BufferedInputFile(encoded.encode("ascii"), filename="image_base64.txt")
        )


@router.message(Command("image_from_base64"))
async def handle_image_from_base64(message: Message, command: CommandObject) -> None:
    payload = (command.args or "").strip()
    if not payload and message.reply_to_message and message.reply_to_message.text:
        payload = message.reply_to_message.text.strip()
    if not payload:
        await message.answer(_usage_message("image_from_base64"))
        return
    try:
        image = base64_to_image(payload, max_file_mb=_max_file_mb())
    except (ImageTooLargeError, ImageProcessingError) as exc:
        await message.answer(str(exc))
        return
    except Exception:  # pragma: no cover - invalid base64 propagated from decoder
        await message.answer("Unable to decode Base64 payload.")
        return
    try:
        image_bytes = convert_format(image, format=image.format or "PNG")
    except ValueError:
        image_bytes = convert_format(image, format="PNG")
    filename = "decoded_image.png" if image.format is None else f"decoded_image.{image.format.lower()}"
    await message.answer_document(BufferedInputFile(image_bytes, filename=filename))


@router.message(Command("image_tools"))
async def handle_image_tools_menu(message: Message) -> None:
    await message.answer(
        "<b>Image tools</b>\n"
        "• Reply with /image_info to inspect metadata\n"
        "• Reply with /image_convert &lt;format&gt; to change format\n"
        "• Reply with /image_resize &lt;width&gt;x&lt;height&gt; or &lt;percent&gt;%\n"
        "• Reply with /image_compress &lt;quality&gt; to reduce size\n"
        "• Reply with /image_base64 to get encoded data\n"
        "• Use /image_from_base64 &lt;data&gt; to decode back into an image"
    )
