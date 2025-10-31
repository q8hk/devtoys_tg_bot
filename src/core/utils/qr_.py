"""QR code utilities."""

from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
from typing import Final

import qrcode
from qrcode.constants import (
    ERROR_CORRECT_H,
    ERROR_CORRECT_L,
    ERROR_CORRECT_M,
    ERROR_CORRECT_Q,
)

__all__ = [
    "create_qr_code",
    "create_qr_png",
    "create_wifi_qr_png",
    "QRCodeOptions",
    "build_wifi_payload",
]

PNG_SIGNATURE: Final = b"\x89PNG\r\n\x1a\n"

_ERROR_CORRECTION_LEVELS: Final = {
    "L": ERROR_CORRECT_L,
    "M": ERROR_CORRECT_M,
    "Q": ERROR_CORRECT_Q,
    "H": ERROR_CORRECT_H,
}


@dataclass(slots=True)
class QRCodeOptions:
    """Configuration for QR code generation."""

    version: int | None = None
    error_correction: str = "M"
    box_size: int = 10
    border: int = 4
    fill_color: str = "black"
    back_color: str = "white"

    def map_error_correction(self) -> int:
        """Return the qrcode constant for the configured error correction level."""

        try:
            return _ERROR_CORRECTION_LEVELS[self.error_correction.upper()]
        except KeyError as exc:  # pragma: no cover - defensive branch
            msg = (
                "Unsupported error correction level. "
                f"Expected one of {sorted(_ERROR_CORRECTION_LEVELS)}, got {self.error_correction!r}."
            )
            raise ValueError(msg) from exc

    def validate(self) -> None:
        """Ensure configuration values are within reasonable bounds."""

        if self.version is not None and not (1 <= self.version <= 40):
            raise ValueError("QR code version must be between 1 and 40 or None.")
        if self.box_size <= 0:
            raise ValueError("box_size must be a positive integer.")
        if self.border < 0:
            raise ValueError("border must be zero or a positive integer.")


def _create_qr(data: str, options: QRCodeOptions) -> bytes:
    options.validate()
    error_correction = options.map_error_correction()
    qr = qrcode.QRCode(
        version=options.version,
        error_correction=error_correction,
        box_size=options.box_size,
        border=options.border,
    )
    qr.add_data(data)
    qr.make(fit=True)
    image = qr.make_image(fill_color=options.fill_color, back_color=options.back_color)
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    result = buffer.getvalue()
    if not result.startswith(PNG_SIGNATURE):  # pragma: no cover - sanity check
        raise RuntimeError("Generated QR code is not a valid PNG file.")
    return result


def create_qr_png(
    data: str,
    *,
    version: int | None = None,
    error_correction: str = "M",
    box_size: int = 10,
    border: int = 4,
    fill_color: str = "black",
    back_color: str = "white",
) -> bytes:
    """Return PNG bytes representing ``data`` encoded as a QR code."""

    options = QRCodeOptions(
        version=version,
        error_correction=error_correction,
        box_size=box_size,
        border=border,
        fill_color=fill_color,
        back_color=back_color,
    )
    return _create_qr(data, options)


def create_qr_code(data: str, *, box_size: int = 10, border: int = 4) -> bytes:
    """Backward compatible wrapper around :func:`create_qr_png`."""

    return create_qr_png(data, box_size=box_size, border=border)


def build_wifi_payload(
    ssid: str,
    *,
    password: str = "",
    auth_type: str = "WPA",
    hidden: bool = False,
) -> str:
    """Return the payload string used to encode Wi-Fi credentials."""

    if not ssid:
        raise ValueError("Wi-Fi SSID must not be empty.")

    normalized_auth = auth_type.upper()
    valid_types = {"WPA", "WPA2", "WEP", "NOPASS"}
    if normalized_auth not in valid_types:
        raise ValueError(f"Unsupported Wi-Fi authentication type: {auth_type!r}.")

    if normalized_auth == "NOPASS":
        password = ""

    def escape(value: str) -> str:
        return (
            value.replace("\\", r"\\\\")
            .replace(";", r"\;")
            .replace(",", r"\,")
            .replace(":", r"\:")
            .replace('"', r"\"")
        )

    components = [
        f"T:{normalized_auth if normalized_auth != 'WPA2' else 'WPA'}",
        f"S:{escape(ssid)}",
    ]
    if password:
        components.append(f"P:{escape(password)}")
    if hidden:
        components.append("H:true")

    return "WIFI:" + ";".join(components) + ";;"


def create_wifi_qr_png(
    ssid: str,
    *,
    password: str = "",
    auth_type: str = "WPA",
    hidden: bool = False,
    **kwargs: object,
) -> bytes:
    """Return PNG bytes encoding Wi-Fi credentials as a QR code."""

    payload = build_wifi_payload(ssid, password=password, auth_type=auth_type, hidden=hidden)
    qr_kwargs = {key: kwargs[key] for key in QRCodeOptions.__annotations__ if key in kwargs}
    options = QRCodeOptions(**qr_kwargs)
    return _create_qr(payload, options)
