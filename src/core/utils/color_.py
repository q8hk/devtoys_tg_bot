"""Color conversion utilities."""

from __future__ import annotations

from colorsys import hls_to_rgb, rgb_to_hls

__all__ = [
    "hex_to_rgb",
    "rgb_to_hex",
    "rgb_to_hsl",
    "hsl_to_rgb",
    "contrast_ratio",
]


def hex_to_rgb(value: str) -> tuple[int, int, int]:
    """Convert a HEX string (``#RRGGBB`` or ``RRGGBB``) to an RGB tuple."""

    value = value.strip().removeprefix("#")
    if len(value) != 6:
        raise ValueError("HEX colors must be 6 characters long")
    r = int(value[0:2], 16)
    g = int(value[2:4], 16)
    b = int(value[4:6], 16)
    return (r, g, b)


def rgb_to_hex(rgb: tuple[int, int, int]) -> str:
    """Return a HEX representation of ``rgb``."""

    r, g, b = rgb
    if not all(0 <= channel <= 255 for channel in (r, g, b)):
        raise ValueError("RGB channels must be between 0 and 255")
    return f"#{r:02X}{g:02X}{b:02X}"


def rgb_to_hsl(rgb: tuple[int, int, int]) -> tuple[int, int, int]:
    """Convert an RGB tuple to HSL components."""

    r, g, b = (channel / 255 for channel in rgb)
    hue, lightness, saturation = rgb_to_hls(r, g, b)
    return (
        round(hue * 360),
        round(saturation * 100),
        round(lightness * 100),
    )


def hsl_to_rgb(hsl: tuple[int, int, int]) -> tuple[int, int, int]:
    """Convert an HSL triple back to RGB."""

    hue, saturation, lightness = hsl
    r, g, b = hls_to_rgb(hue / 360, lightness / 100, saturation / 100)
    return (round(r * 255), round(g * 255), round(b * 255))


def contrast_ratio(color_a: tuple[int, int, int], color_b: tuple[int, int, int]) -> float:
    """Return the WCAG contrast ratio between two colors."""

    def luminance(rgb: tuple[int, int, int]) -> float:
        def transform(channel: int) -> float:
            c = channel / 255
            return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4

        r, g, b = (transform(channel) for channel in rgb)
        return 0.2126 * r + 0.7152 * g + 0.0722 * b

    lum_a = luminance(color_a)
    lum_b = luminance(color_b)
    lighter, darker = max(lum_a, lum_b), min(lum_a, lum_b)
    return round((lighter + 0.05) / (darker + 0.05), 2)
