import io
import pytest
from PIL import Image

from src.core.utils.image_ import (
    ImageTooLargeError,
    base64_to_image,
    compress_image,
    convert_format,
    extract_metadata,
    image_to_base64,
    open_image,
    resize_image,
)


@pytest.fixture()
def sample_png() -> bytes:
    image = Image.new("RGB", (24, 12), color=(10, 20, 30))
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def test_extract_metadata_reports_basic_fields(sample_png: bytes) -> None:
    metadata = extract_metadata(sample_png)
    assert metadata["format"] == "PNG"
    assert metadata["mode"] == "RGB"
    assert metadata["width"] == 24
    assert metadata["height"] == 12
    assert "info" in metadata


@pytest.mark.parametrize(
    ("width", "height", "percent", "expected"),
    [
        (12, None, None, (12, 6)),
        (None, 6, None, (12, 6)),
        (None, None, 50, (12, 6)),
    ],
)
def test_resize_image_supports_multiple_strategies(
    sample_png: bytes, width: int | None, height: int | None, percent: float | None, expected: tuple[int, int]
) -> None:
    resized_bytes = resize_image(sample_png, width=width, height=height, percent=percent)
    resized = open_image(resized_bytes)
    assert resized.size == expected


def test_convert_format_accepts_quality_arguments(sample_png: bytes) -> None:
    jpeg_bytes = convert_format(sample_png, format="JPEG", quality=80)
    assert jpeg_bytes[6:10] == b"JFIF"


def test_compress_image_reduces_jpeg_size(sample_png: bytes) -> None:
    high_quality = convert_format(sample_png, format="JPEG", quality=95)
    compressed = compress_image(high_quality, quality=40, format="JPEG")
    assert len(compressed) < len(high_quality)


def test_image_to_base64_and_back_roundtrip(sample_png: bytes) -> None:
    encoded = image_to_base64(sample_png)
    decoded = base64_to_image(encoded)
    assert decoded.size == (24, 12)


def test_percent_resize_requires_positive_percent(sample_png: bytes) -> None:
    with pytest.raises(ValueError):
        resize_image(sample_png, percent=0)


def test_convert_requires_format(sample_png: bytes) -> None:
    with pytest.raises(ValueError):
        convert_format(sample_png, format="")


def test_size_limit_enforced(sample_png: bytes) -> None:
    large_image = Image.new("RGB", (1500, 1500), color=(1, 2, 3))
    buffer = io.BytesIO()
    large_image.save(buffer, format="BMP")
    payload = buffer.getvalue()
    assert len(payload) > 1 * 1024 * 1024
    with pytest.raises(ImageTooLargeError):
        open_image(payload, max_file_mb=1)


def test_open_image_preserves_format(sample_png: bytes) -> None:
    image = open_image(sample_png)
    assert image.format == "PNG"
    assert image.info == {}
