from __future__ import annotations

import sys
from pathlib import Path

import pytest

# Ensure the src/ directory is on sys.path for src-layout imports.
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "src"))

from core.utils.qr_ import (  # type: ignore  # noqa: E402
    PNG_SIGNATURE,
    QRCodeOptions,
    build_wifi_payload,
    create_qr_png,
    create_wifi_qr_png,
)


def test_create_qr_png_returns_png_bytes():
    result = create_qr_png("Hello QR", box_size=4, border=2)
    assert isinstance(result, bytes)
    assert result.startswith(PNG_SIGNATURE)


@pytest.mark.parametrize("level", ["L", "M", "Q", "H", "l"])
def test_create_qr_png_supports_error_correction(level: str):
    result = create_qr_png("payload", error_correction=level)
    assert result.startswith(PNG_SIGNATURE)


def test_create_qr_png_rejects_invalid_configuration():
    with pytest.raises(ValueError):
        create_qr_png("test", version=41)
    with pytest.raises(ValueError):
        create_qr_png("test", box_size=0)
    with pytest.raises(ValueError):
        QRCodeOptions(error_correction="X").map_error_correction()


def test_build_wifi_payload_formats_credentials():
    payload = build_wifi_payload("My Wi-Fi", password="p@ss;word", auth_type="wpa2", hidden=True)
    assert payload == r"WIFI:T:WPA;S:My Wi-Fi;P:p@ss\;word;H:true;;"


def test_create_wifi_qr_png_inherits_options():
    result = create_wifi_qr_png(
        "CafeNet",
        password="beans",
        auth_type="WPA",
        error_correction="H",
        box_size=6,
    )
    assert result.startswith(PNG_SIGNATURE)


def test_create_wifi_qr_png_rejects_invalid_auth():
    with pytest.raises(ValueError):
        build_wifi_payload("ssid", auth_type="INVALID")
