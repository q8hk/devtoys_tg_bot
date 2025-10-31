import io
import os

import pytest

from src.core.utils import base64_


def test_encode_decode_text_roundtrip():
    encoded = base64_.encode_text("hello world")
    assert encoded == "aGVsbG8gd29ybGQ="
    decoded = base64_.decode_text(encoded)
    assert decoded == "hello world"


def test_decode_bytes_invalid_input():
    with pytest.raises(base64_.Base64Error):
        base64_.decode_bytes("@@ not valid @@")


def test_stream_encoding_and_decoding_roundtrip():
    payload = b"abc" * 20000 + b"tail"
    source = io.BytesIO(payload)
    encoded_stream = io.StringIO()

    base64_.encode_stream(source, encoded_stream, chunk_size=4096)
    encoded_value = encoded_stream.getvalue()

    # Introduce whitespace to ensure decoder tolerates it.
    formatted = "\n".join(encoded_value[i : i + 60] for i in range(0, len(encoded_value), 60))
    decoded_stream = io.BytesIO()
    base64_.decode_stream(io.StringIO(formatted), decoded_stream, chunk_size=500)
    assert decoded_stream.getvalue() == payload


def test_file_roundtrip(tmp_path):
    binary_path = tmp_path / "input.bin"
    encoded_path = tmp_path / "encoded.txt"
    decoded_path = tmp_path / "decoded.bin"

    data = os.urandom(8192 + 17)
    binary_path.write_bytes(data)

    written_chars = base64_.encode_file(binary_path, encoded_path, chunk_size=2048)
    assert written_chars == len(encoded_path.read_text("ascii"))

    written_bytes = base64_.decode_file(encoded_path, decoded_path, chunk_size=1024)
    assert written_bytes == len(data)
    assert decoded_path.read_bytes() == data


def test_data_uri_helpers():
    payload = b"\xffPNG" + b"\x00" * 4
    uri = base64_.build_data_uri(payload, media_type="image/png")
    parsed = base64_.detect_data_uri(uri)
    assert parsed is not None
    assert parsed.media_type == "image/png"
    assert parsed.data == payload

    # Percent encoded (non-base64) payloads are also supported by the detector.
    plain_uri = "data:text/plain,Hello%20World"
    parsed_plain = base64_.detect_data_uri(plain_uri)
    assert parsed_plain is not None
    assert parsed_plain.media_type == "text/plain"
    assert parsed_plain.data == b"Hello World"
