"""JWT utilities."""

from __future__ import annotations

import base64
import json
import hmac
import hashlib
from dataclasses import dataclass
from typing import Any

__all__ = [
    "JWTDecodeError",
    "DecodedJWT",
    "decode_jwt",
]


class JWTDecodeError(ValueError):
    """Raised when a token cannot be decoded."""


def _b64url_decode(segment: str) -> bytes:
    padding = '=' * (-len(segment) % 4)
    return base64.urlsafe_b64decode(segment + padding)


@dataclass(slots=True)
class DecodedJWT:
    header: dict[str, Any]
    payload: dict[str, Any]
    signature_valid: bool | None


SUPPORTED_HMAC = {
    "HS256": hashlib.sha256,
    "HS384": hashlib.sha384,
    "HS512": hashlib.sha512,
}


def decode_jwt(token: str, *, key: str | bytes | None = None, verify: bool = False) -> DecodedJWT:
    """Decode a JWT token.

    ``verify`` only supports symmetric HMAC algorithms.  When ``verify`` is
    false the signature is not checked and ``signature_valid`` is set to ``None``.
    """

    try:
        header_raw, payload_raw, signature_raw = token.split(".")
    except ValueError as exc:  # pragma: no cover - defensive
        raise JWTDecodeError("Token must have exactly 3 parts") from exc
    try:
        header = json.loads(_b64url_decode(header_raw))
        payload = json.loads(_b64url_decode(payload_raw))
    except (json.JSONDecodeError, ValueError) as exc:  # pragma: no cover - defensive
        raise JWTDecodeError("Invalid JSON content") from exc
    signature_valid: bool | None = None
    if verify:
        if key is None:
            raise JWTDecodeError("A key is required for verification")
        algorithm = header.get("alg", "")
        if algorithm not in SUPPORTED_HMAC:
            raise JWTDecodeError(f"Unsupported algorithm for verification: {algorithm}")
        signing_input = f"{header_raw}.{payload_raw}".encode("ascii")
        expected = hmac.new(
            key.encode("utf-8") if isinstance(key, str) else key,
            signing_input,
            SUPPORTED_HMAC[algorithm],
        ).digest()
        actual = _b64url_decode(signature_raw or "")
        signature_valid = hmac.compare_digest(expected, actual)
    return DecodedJWT(header=header, payload=payload, signature_valid=signature_valid)
