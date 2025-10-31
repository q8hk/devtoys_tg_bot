"""QR code utilities."""

from __future__ import annotations

from io import BytesIO

import qrcode

__all__ = ["create_qr_code"]


def create_qr_code(data: str, *, box_size: int = 10, border: int = 4) -> bytes:
    """Return PNG bytes representing ``data`` encoded as a QR code."""

    qr = qrcode.QRCode(box_size=box_size, border=border)
    qr.add_data(data)
    qr.make(fit=True)
    image = qr.make_image(fill_color="black", back_color="white")
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()
