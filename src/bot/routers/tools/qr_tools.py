"""QR code and barcode handlers."""

from __future__ import annotations

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import BufferedInputFile, Message

from src.core.utils.qr_ import create_qr_png, create_wifi_qr_png

__all__ = ["router"]

router = Router(name="qr-tools")

_USAGE_MESSAGE = (
    "Send the text after /qr to generate a QR code, e.g. `/qr https://example.com`."
)

_WIFI_USAGE_MESSAGE = (
    "Use /wifi_qr <ssid>;<password> to generate Wi-Fi QR codes. "
    "Set password to `nopass` for open networks."
)


@router.message(Command("qr"))
async def handle_qr_command(message: Message) -> None:
    """Generate a QR code for arbitrary text supplied with the command."""

    text = (message.text or "").split(maxsplit=1)
    if len(text) < 2:
        await message.answer(_USAGE_MESSAGE)
        return
    payload = text[1]
    png_bytes = create_qr_png(payload)
    await message.answer_document(
        BufferedInputFile(png_bytes, filename="qr.png"),
        caption="Here is your QR code!",
    )


@router.message(Command("wifi_qr"))
async def handle_wifi_qr_command(message: Message) -> None:
    """Generate a Wi-Fi QR code using ``/wifi_qr SSID;password`` syntax."""

    text = (message.text or "").split(maxsplit=1)
    if len(text) < 2:
        await message.answer(_WIFI_USAGE_MESSAGE)
        return

    credentials = text[1].split(";", 1)
    ssid = credentials[0].strip()
    password = credentials[1].strip() if len(credentials) > 1 else ""

    if password.lower() == "nopass":
        password = ""
        auth_type = "nopass"
    else:
        auth_type = "wpa"

    try:
        png_bytes = create_wifi_qr_png(ssid, password=password, auth_type=auth_type)
    except ValueError as exc:
        await message.answer(f"Could not generate Wi-Fi QR code: {exc}")
        return

    await message.answer_document(
        BufferedInputFile(png_bytes, filename="wifi-qr.png"),
        caption="Share this QR to let others join your Wi-Fi network.",
    )
