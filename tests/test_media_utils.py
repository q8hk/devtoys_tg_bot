import io

from PIL import Image

from src.core.utils import color_, image_, qr_


def create_png_bytes(color=(255, 0, 0)):
    image = Image.new("RGB", (10, 10), color=color)
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def test_color_conversions_and_contrast():
    rgb = color_.hex_to_rgb("#336699")
    assert rgb == (51, 102, 153)
    assert color_.rgb_to_hex(rgb) == "#336699"
    hsl = color_.rgb_to_hsl(rgb)
    back_rgb = color_.hsl_to_rgb(hsl)
    assert back_rgb == (51, 102, 153)
    contrast = color_.contrast_ratio((0, 0, 0), (255, 255, 255))
    assert contrast == 21.0


def test_qr_generation_returns_png():
    png_bytes = qr_.create_qr_code("https://example.com")
    assert png_bytes.startswith(b"\x89PNG")


def test_image_metadata_resize_and_convert():
    png = create_png_bytes()
    metadata = image_.extract_metadata(png)
    assert metadata["format"] == "PNG"
    resized = image_.resize_image(png, width=5)
    assert Image.open(io.BytesIO(resized)).size == (5, 5)
    converted = image_.convert_format(png, format="JPEG")
    assert converted[6:10] == b"JFIF"
