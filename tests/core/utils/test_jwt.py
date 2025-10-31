"""Tests for :mod:`core.utils.jwt_`."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import sys
from pathlib import Path

import pytest
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding, rsa

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "src"))

from core.utils.jwt_ import DecodedJWT, JWTDecodeError, decode_jwt


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("ascii").rstrip("=")


def _make_token(header: dict[str, object], payload: dict[str, object], signer) -> str:
    header_raw = _b64url(json.dumps(header, separators=(",", ":")).encode("utf-8"))
    payload_raw = _b64url(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
    signing_input = f"{header_raw}.{payload_raw}".encode("ascii")
    signature = signer(signing_input)
    signature_raw = _b64url(signature)
    return f"{header_raw}.{payload_raw}.{signature_raw}"


def test_decode_without_verification() -> None:
    token = _make_token({"alg": "HS256", "typ": "JWT"}, {"sub": "123"}, lambda _: b"sig")
    decoded = decode_jwt(token, verify=False)
    assert isinstance(decoded, DecodedJWT)
    assert decoded.signature_valid is None
    assert decoded.algorithm == "HS256"
    assert decoded.key_id is None


def test_verify_hmac_signature_success() -> None:
    secret = b"super-secret"

    def signer(data: bytes) -> bytes:
        return hmac.new(secret, data, hashlib.sha256).digest()

    token = _make_token({"alg": "HS256"}, {"role": "admin"}, signer)
    decoded = decode_jwt(token, key=secret, verify=True)
    assert decoded.signature_valid is True


def test_verify_hmac_signature_failure() -> None:
    secret = b"correct"

    def signer(data: bytes) -> bytes:
        return hmac.new(secret, data, hashlib.sha256).digest()

    token = _make_token({"alg": "HS256"}, {"role": "admin"}, signer)
    decoded = decode_jwt(token, key=b"wrong", verify=True)
    assert decoded.signature_valid is False


def test_verify_requires_key() -> None:
    token = _make_token({"alg": "HS256"}, {"test": True}, lambda _: b"sig")
    with pytest.raises(JWTDecodeError):
        decode_jwt(token, verify=True)


def test_verify_with_jwks_rs256() -> None:
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    public_numbers = private_key.public_key().public_numbers()
    jwk = {
        "kty": "RSA",
        "kid": "kid-1",
        "n": _b64url(public_numbers.n.to_bytes((public_numbers.n.bit_length() + 7) // 8, "big")),
        "e": _b64url(public_numbers.e.to_bytes((public_numbers.e.bit_length() + 7) // 8, "big")),
        "alg": "RS256",
        "use": "sig",
    }

    def signer(data: bytes) -> bytes:
        return private_key.sign(data, padding.PKCS1v15(), hashes.SHA256())

    token = _make_token({"alg": "RS256", "kid": "kid-1"}, {"exp": 1}, signer)
    decoded = decode_jwt(token, key=json.dumps({"keys": [jwk]}), verify=True)
    assert decoded.signature_valid is True
    assert decoded.key_id == "kid-1"


def test_verify_with_jwks_missing_kid() -> None:
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    public_numbers = private_key.public_key().public_numbers()
    jwk1 = {
        "kty": "RSA",
        "kid": "kid-1",
        "n": _b64url(public_numbers.n.to_bytes((public_numbers.n.bit_length() + 7) // 8, "big")),
        "e": _b64url(public_numbers.e.to_bytes((public_numbers.e.bit_length() + 7) // 8, "big")),
        "alg": "RS256",
    }

    other_key = {
        "kty": "RSA",
        "kid": "kid-2",
        "n": _b64url((public_numbers.n + 1).to_bytes((public_numbers.n.bit_length() + 7) // 8, "big")),
        "e": jwk1["e"],
    }

    def signer(data: bytes) -> bytes:
        return private_key.sign(data, padding.PKCS1v15(), hashes.SHA256())

    token = _make_token({"alg": "RS256", "kid": "kid-1"}, {"exp": 1}, signer)
    jwks = json.dumps({"keys": [other_key, jwk1]})
    decoded = decode_jwt(token, key=jwks, verify=True)
    assert decoded.signature_valid is True


def test_warns_on_none_algorithm() -> None:
    header = {"alg": "none"}
    payload = {"ok": True}
    token = _make_token(header, payload, lambda _: b"")
    decoded = decode_jwt(token)
    assert decoded.warnings
    assert decoded.signature_valid is None
    with pytest.raises(JWTDecodeError):
        decode_jwt(token, verify=True)
