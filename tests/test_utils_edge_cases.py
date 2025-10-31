import base64
import io

import pytest
from PIL import Image
from src.core.utils import base64_, color_, image_, jwt_, regex_, time_, url


def _make_png(color: tuple[int, int, int] = (0, 0, 0)) -> bytes:
    image = Image.new("RGB", (4, 4), color=color)
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def test_base64_errors_and_data_uri_variants():
    with pytest.raises(base64_.Base64Error):
        base64_.decode_bytes("not-base64!!")

    with pytest.raises(base64_.Base64Error):
        base64_.detect_data_uri("data:text/plain;base64,")

    uri = "data:,Hello%20World"
    parsed = base64_.detect_data_uri(uri)
    assert parsed is not None
    assert parsed.media_type == "text/plain;charset=US-ASCII"
    assert parsed.data == b"Hello World"


def test_color_validation_errors():
    with pytest.raises(ValueError):
        color_.hex_to_rgb("12345")

    with pytest.raises(ValueError):
        color_.rgb_to_hex((300, 0, 0))


def test_image_resize_requires_dimension():
    png = _make_png()
    with pytest.raises(ValueError):
        image_.resize_image(png)


def _sample_jwt(alg: str = "none", signature: bytes = b"") -> str:
    header_json = f'{{"alg":"{alg}"}}'.encode()
    payload_json = b'{"sub":"1"}'
    header = base64.urlsafe_b64encode(header_json).rstrip(b"=")
    payload = base64.urlsafe_b64encode(payload_json).rstrip(b"=")
    signature_segment = base64.urlsafe_b64encode(signature).rstrip(b"=")
    return f"{header.decode()}.{payload.decode()}.{signature_segment.decode()}"


def test_jwt_verification_requirements():
    token = _sample_jwt()
    with pytest.raises(jwt_.JWTDecodeError):
        jwt_.decode_jwt(token, verify=True)

    token = _sample_jwt("RS256", b"sig")
    with pytest.raises(jwt_.JWTDecodeError):
        jwt_.decode_jwt(token, key="secret", verify=True)


def test_regex_groups_and_limits():
    result = regex_.run_regex(r"(ab)", "ab ab", limit=1)
    assert len(result.matches) == 1
    assert result.matches[0].groups == ("ab",)


def test_parse_natural_delta_invalid_expression():
    with pytest.raises(ValueError):
        time_.parse_natural_delta("not a real duration")


def test_query_parsing_and_rebuild_round_trip():
    assert url.parse_query_string("path/without/query") == {}

    mapping = {"foo": ["1", "2"], "bar": "baz"}
    query = url.rebuild_query_string(mapping)
    parsed = url.parse_query_string(f"https://example.com?{query}")
    assert parsed["foo"] == ["1", "2"]
    assert parsed["bar"] == ["baz"]
