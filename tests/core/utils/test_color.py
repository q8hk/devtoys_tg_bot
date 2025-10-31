import io
import sys
from pathlib import Path

import pytest
from PIL import Image

ROOT_DIR = Path(__file__).resolve().parents[3]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src.core.utils import color_


def test_hex_rgb_roundtrip() -> None:
    assert color_.normalize_hex("abc") == "#AABBCC"
    rgb = color_.hex_to_rgb("#1A2B3C")
    assert rgb == (26, 43, 60)
    assert color_.rgb_to_hex(rgb) == "#1A2B3C"
    with pytest.raises(ValueError):
        color_.hex_to_rgb("zzzzzz")


def test_hsl_and_cmyk_conversions() -> None:
    rgb = (51, 102, 153)
    hsl = color_.rgb_to_hsl(rgb)
    assert hsl == (210, 50, 40)
    assert color_.hsl_to_rgb(hsl) == rgb
    cmyk = color_.rgb_to_cmyk(rgb)
    assert cmyk == (67, 33, 0, 40)
    back_rgb = color_.cmyk_to_rgb(cmyk)
    for original, reconstructed in zip(rgb, back_rgb):
        assert abs(original - reconstructed) <= 1
    with pytest.raises(ValueError):
        color_.rgb_to_cmyk((300, 0, 0))
    with pytest.raises(ValueError):
        color_.cmyk_to_rgb((0, 0, 0))


def test_contrast_helpers() -> None:
    ratio = color_.contrast_ratio((0, 0, 0), (255, 255, 255))
    assert ratio == 21.0
    assert color_.meets_wcag_contrast(ratio)
    assert color_.meets_wcag_contrast(3.0, large_text=True)
    assert not color_.meets_wcag_contrast(4.0, level="AAA")
    with pytest.raises(ValueError):
        color_.meets_wcag_contrast(-1)


def test_generate_palette_and_swatch() -> None:
    palette = color_.generate_palette(count=5, seed=42)
    assert palette == [
        "#5F1C41",
        "#524224",
        "#4A8740",
        "#3D7C7F",
        "#5132AE",
    ]
    swatch_bytes = color_.create_palette_swatch(palette, width=200, height=40)
    assert swatch_bytes.startswith(b"\x89PNG")
    image = Image.open(io.BytesIO(swatch_bytes))
    assert image.size == (200, 40)
    assert image.getpixel((10, 20)) == color_.hex_to_rgb(palette[0])
    with pytest.raises(ValueError):
        color_.generate_palette(count=0)
    with pytest.raises(ValueError):
        color_.create_palette_swatch([], width=100)
    with pytest.raises(ValueError):
        color_.create_palette_swatch(["#000"], width=4, padding=4)
