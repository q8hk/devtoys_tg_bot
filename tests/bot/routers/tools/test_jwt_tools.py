"""Tests for the JWT router helpers."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[4] / "src"))

from bot.routers.tools.jwt_tools import JWTRequest, _parse_jwt_command, render_jwt_summary


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("ascii").rstrip("=")


def _make_hmac_token(secret: bytes) -> str:
    header_raw = _b64url(json.dumps({"alg": "HS256"}, separators=(",", ":")).encode("utf-8"))
    payload_raw = _b64url(json.dumps({"scope": "demo"}, separators=(",", ":")).encode("utf-8"))
    signing_input = f"{header_raw}.{payload_raw}".encode("ascii")
    signature = hmac.new(secret, signing_input, hashlib.sha256).digest()
    signature_raw = _b64url(signature)
    return f"{header_raw}.{payload_raw}.{signature_raw}"


def test_parse_jwt_command_extracts_parts() -> None:
    request = _parse_jwt_command("/jwt token-value key=my-secret verify=true")
    assert isinstance(request, JWTRequest)
    assert request.token == "token-value"
    assert request.key == "my-secret"
    assert request.verify is True


def test_render_jwt_summary_verifies_when_key_present() -> None:
    secret = b"shared-secret"
    token = _make_hmac_token(secret)
    summary = render_jwt_summary(token, key=secret.decode("ascii"))
    assert "Signature: ✅ valid" in summary
    assert "Header:" in summary
    assert "Payload:" in summary


def test_render_jwt_summary_handles_errors() -> None:
    summary = render_jwt_summary("invalid-token")
    assert summary.startswith("❌ Failed to process token:")
