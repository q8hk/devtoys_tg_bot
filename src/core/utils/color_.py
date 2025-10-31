"""Color conversion utilities and helpers."""

from __future__ import annotations

from io import BytesIO
import random
import re
from typing import Iterable, Sequence

from colorsys import hls_to_rgb as _hls_to_rgb, rgb_to_hls as _rgb_to_hls
from PIL import Image, ImageColor, ImageDraw

__all__ = [
    "normalize_hex",
    "hex_to_rgb",
    "rgb_to_hex",
    "rgb_to_hsl",
    "hsl_to_rgb",
    "rgb_to_cmyk",
    "cmyk_to_rgb",
    "contrast_ratio",
    "meets_wcag_contrast",
    "generate_palette",
    "create_palette_swatch",
]


_HEX_RE = re.compile(r"^[0-9a-fA-F]{6}$")
_HEX_SHORT_RE = re.compile(r"^[0-9a-fA-F]{3}$")


def _clamp(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(maximum, value))


def _validate_rgb(rgb: Iterable[int]) -> tuple[int, int, int]:
    try:
        r, g, b = rgb
    except ValueError as exc:  # pragma: no cover - defensive
        raise ValueError("RGB values must contain exactly three channels") from exc

    for channel in (r, g, b):
        if not isinstance(channel, (int, float)):
            raise ValueError("RGB channels must be numbers")
        if not 0 <= channel <= 255:
            raise ValueError("RGB channels must be between 0 and 255")
    return int(round(r)), int(round(g)), int(round(b))


def _validate_cmyk(cmyk: Iterable[int]) -> tuple[int, int, int, int]:
    try:
        c, m, y, k = cmyk
    except ValueError as exc:  # pragma: no cover - defensive
        raise ValueError("CMYK values must contain four components") from exc

    for component in (c, m, y, k):
        if not isinstance(component, (int, float)):
            raise ValueError("CMYK components must be numbers")
        if not 0 <= component <= 100:
            raise ValueError("CMYK components must be between 0 and 100")
    return (int(round(c)), int(round(m)), int(round(y)), int(round(k)))


def normalize_hex(value: str) -> str:
    """Return ``value`` normalized to the ``#RRGGBB`` format."""

    value = value.strip()
    if not value:
        raise ValueError("HEX color cannot be empty")
    value = value.removeprefix("#")
    if _HEX_SHORT_RE.fullmatch(value):
        value = "".join(ch * 2 for ch in value)
    if not _HEX_RE.fullmatch(value):
        raise ValueError("HEX colors must be three or six hexadecimal characters")
    return f"#{value.upper()}"


def hex_to_rgb(value: str) -> tuple[int, int, int]:
    """Convert a HEX string (``#RRGGBB`` or ``#RGB``) to an RGB tuple."""

    normalized = normalize_hex(value)
    r = int(normalized[1:3], 16)
    g = int(normalized[3:5], 16)
    b = int(normalized[5:7], 16)
    return (r, g, b)


def rgb_to_hex(rgb: Iterable[int]) -> str:
    """Return a HEX representation of ``rgb``."""

    r, g, b = _validate_rgb(rgb)
    return f"#{r:02X}{g:02X}{b:02X}"


def rgb_to_hsl(rgb: Iterable[int]) -> tuple[int, int, int]:
    """Convert an RGB tuple to integer HSL components."""

    r, g, b = _validate_rgb(rgb)
    h, l, s = _rgb_to_hls(r / 255, g / 255, b / 255)
    hue = int(round((h % 1) * 360)) % 360
    sat = int(round(s * 100))
    light = int(round(l * 100))
    return (hue, sat, light)


def hsl_to_rgb(hsl: Iterable[int]) -> tuple[int, int, int]:
    """Convert integer HSL components back to RGB."""

    try:
        h, s, l = hsl
    except ValueError as exc:  # pragma: no cover - defensive
        raise ValueError("HSL values must contain exactly three components") from exc
    if not isinstance(h, (int, float)):
        raise ValueError("Hue must be numeric")
    if not isinstance(s, (int, float)) or not isinstance(l, (int, float)):
        raise ValueError("Saturation and lightness must be numeric")
    if not 0 <= s <= 100 or not 0 <= l <= 100:
        raise ValueError("Saturation and lightness must be between 0 and 100")
    hue = (float(h) % 360) / 360
    sat = float(s) / 100
    light = float(l) / 100
    r, g, b = _hls_to_rgb(hue, light, sat)
    return (int(round(r * 255)), int(round(g * 255)), int(round(b * 255)))


def rgb_to_cmyk(rgb: Iterable[int]) -> tuple[int, int, int, int]:
    """Convert RGB color values to CMYK percentages."""

    r, g, b = _validate_rgb(rgb)
    if (r, g, b) == (0, 0, 0):
        return (0, 0, 0, 100)
    r_p, g_p, b_p = r / 255, g / 255, b / 255
    k = 1 - max(r_p, g_p, b_p)
    c = (1 - r_p - k) / (1 - k)
    m = (1 - g_p - k) / (1 - k)
    y = (1 - b_p - k) / (1 - k)
    return (
        int(round(c * 100)),
        int(round(m * 100)),
        int(round(y * 100)),
        int(round(k * 100)),
    )


def cmyk_to_rgb(cmyk: Iterable[int]) -> tuple[int, int, int]:
    """Convert CMYK percentages back to RGB values."""

    c, m, y, k = _validate_cmyk(cmyk)
    c_p, m_p, y_p, k_p = c / 100, m / 100, y / 100, k / 100
    r = 255 * (1 - c_p) * (1 - k_p)
    g = 255 * (1 - m_p) * (1 - k_p)
    b = 255 * (1 - y_p) * (1 - k_p)
    return (int(round(r)), int(round(g)), int(round(b)))


def _relative_luminance(rgb: Iterable[int]) -> float:
    r, g, b = _validate_rgb(rgb)
    channels = []
    for channel in (r, g, b):
        channel /= 255
        if channel <= 0.03928:
            channels.append(channel / 12.92)
        else:
            channels.append(((channel + 0.055) / 1.055) ** 2.4)
    r_l, g_l, b_l = channels
    return 0.2126 * r_l + 0.7152 * g_l + 0.0722 * b_l


def contrast_ratio(color_a: Iterable[int], color_b: Iterable[int]) -> float:
    """Return the WCAG contrast ratio between two colors rounded to two decimals."""

    lum_a = _relative_luminance(color_a)
    lum_b = _relative_luminance(color_b)
    lighter, darker = max(lum_a, lum_b), min(lum_a, lum_b)
    ratio = (lighter + 0.05) / (darker + 0.05)
    return round(ratio, 2)


def meets_wcag_contrast(
    ratio: float,
    *,
    level: str = "AA",
    large_text: bool = False,
) -> bool:
    """Return ``True`` when ``ratio`` satisfies the requested WCAG threshold."""

    if ratio < 0:
        raise ValueError("Contrast ratio cannot be negative")
    normalized_level = level.upper()
    if normalized_level not in {"AA", "AAA"}:
        raise ValueError("Level must be either 'AA' or 'AAA'")
    if normalized_level == "AA":
        threshold = 3.0 if large_text else 4.5
    else:  # AAA
        threshold = 4.5 if large_text else 7.0
    return ratio >= threshold


def generate_palette(
    *,
    count: int = 5,
    base_hex: str | None = None,
    seed: int | None = None,
) -> list[str]:
    """Return a deterministic palette of HEX colors."""

    if count <= 0:
        raise ValueError("Palette size must be positive")
    rng = random.Random(seed)
    if base_hex is None:
        base_h = rng.randrange(0, 360)
        base_s = rng.randint(40, 90)
        base_l = rng.randint(30, 70)
    else:
        base_rgb = hex_to_rgb(base_hex)
        base_h, base_s, base_l = rgb_to_hsl(base_rgb)
    step = 360 / count
    palette: list[str] = []
    for index in range(count):
        hue = (base_h + step * index) % 360
        sat = _clamp(base_s + rng.randint(-15, 15), 25, 95)
        light = _clamp(base_l + rng.randint(-15, 15), 20, 85)
        palette.append(
            rgb_to_hex(
                hsl_to_rgb(
                    (
                        int(round(hue)) % 360,
                        int(round(sat)),
                        int(round(light)),
                    )
                )
            )
        )
    return palette


def create_palette_swatch(
    palette: Sequence[str],
    *,
    width: int = 320,
    height: int = 64,
    padding: int = 4,
    background: str = "#FFFFFF",
) -> bytes:
    """Return a PNG image representing the provided ``palette``."""

    if not palette:
        raise ValueError("Palette cannot be empty")
    if width <= 0 or height <= 0:
        raise ValueError("Width and height must be positive")
    if padding < 0:
        raise ValueError("Padding cannot be negative")

    normalized_colors = [rgb_to_hex(hex_to_rgb(color)) for color in palette]
    segments_space = width - padding * (len(normalized_colors) + 1)
    if segments_space <= 0:
        raise ValueError("Width too small for the requested padding and colors")
    segment_width, remainder = divmod(segments_space, len(normalized_colors))

    try:
        background_rgb = ImageColor.getrgb(background)
    except ValueError:  # pragma: no cover - defensive
        background_rgb = ImageColor.getrgb(normalize_hex(background))
    image = Image.new("RGB", (width, height), background_rgb)
    draw = ImageDraw.Draw(image)

    x0 = padding
    for index, color in enumerate(normalized_colors):
        extra = 1 if index < remainder else 0
        w = segment_width + extra
        x1 = x0 + w
        draw.rectangle([x0, padding, x1, height - padding], fill=color)
        x0 = x1 + padding

    buffer = BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()
