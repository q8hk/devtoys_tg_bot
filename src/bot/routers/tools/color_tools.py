"""Handlers for color conversions and palette previews."""

from __future__ import annotations

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import BufferedInputFile, Message

from src.core.utils import color_

router = Router(name="color-tools")


def build_color_summary(hex_color: str) -> tuple[str, list[str], bytes]:
    """Return a textual summary, palette, and swatch for ``hex_color``."""

    rgb = color_.hex_to_rgb(hex_color)
    normalized_hex = color_.rgb_to_hex(rgb)
    hsl = color_.rgb_to_hsl(rgb)
    cmyk = color_.rgb_to_cmyk(rgb)
    contrast_on_white = color_.contrast_ratio(rgb, (255, 255, 255))
    contrast_on_black = color_.contrast_ratio(rgb, (0, 0, 0))
    palette = color_.generate_palette(base_hex=normalized_hex, count=5)
    swatch = color_.create_palette_swatch(palette)
    summary_lines = [
        f"🎨 {normalized_hex}",
        f"RGB: {rgb[0]}, {rgb[1]}, {rgb[2]}",
        f"HSL: {hsl[0]}°, {hsl[1]}%, {hsl[2]}%",
        f"CMYK: {cmyk[0]}%, {cmyk[1]}%, {cmyk[2]}%, {cmyk[3]}%",
        (
            "Contrast vs white: "
            f"{contrast_on_white:.2f}:1 (AA: {'yes' if color_.meets_wcag_contrast(contrast_on_white) else 'no'})"
        ),
        (
            "Contrast vs black: "
            f"{contrast_on_black:.2f}:1 (AA: {'yes' if color_.meets_wcag_contrast(contrast_on_black) else 'no'})"
        ),
        "Palette: " + ", ".join(palette),
    ]
    return "\n".join(summary_lines), palette, swatch


@router.message(Command("color"))
async def handle_color_lookup(message: Message) -> None:
    """Parse a HEX value from ``message`` and reply with conversions."""

    text = message.text or ""
    parts = text.split(maxsplit=1)
    if len(parts) < 2:
        await message.answer("Send /color followed by a HEX value, e.g. /color #336699")
        return
    candidate = parts[1].strip().split()[0]
    try:
        summary, palette, swatch = build_color_summary(candidate)
    except ValueError as exc:
        await message.answer(f"⚠️ {exc}")
        return
    await message.answer(summary)
    file = BufferedInputFile(swatch, filename="palette.png")
    caption = "Palette preview: " + ", ".join(palette)
    await message.answer_document(file, caption=caption)
