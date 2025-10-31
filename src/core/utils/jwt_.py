"""JWT utilities."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
from dataclasses import dataclass
from typing import Any, Iterable

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec, padding as asym_padding, rsa

__all__ = [
    "JWTDecodeError",
    "DecodedJWT",
    "decode_jwt",
]


class JWTDecodeError(ValueError):
    """Raised when a token cannot be decoded."""


def _b64url_decode(segment: str) -> bytes:
    padding = "=" * (-len(segment) % 4)
    return base64.urlsafe_b64decode(segment + padding)


@dataclass(slots=True)
class DecodedJWT:
    """Container returned by :func:`decode_jwt`."""

    header: dict[str, Any]
    payload: dict[str, Any]
    signature_valid: bool | None
    algorithm: str | None
    key_id: str | None
    warnings: list[str]


SUPPORTED_HMAC = {
    "HS256": hashlib.sha256,
    "HS384": hashlib.sha384,
    "HS512": hashlib.sha512,
}

RSA_HASHES = {
    "RS256": hashes.SHA256(),
    "RS384": hashes.SHA384(),
    "RS512": hashes.SHA512(),
}

RSA_PSS_HASHES = {
    "PS256": hashes.SHA256(),
    "PS384": hashes.SHA384(),
    "PS512": hashes.SHA512(),
}

ECDSA_HASHES = {
    "ES256": (ec.SECP256R1(), hashes.SHA256()),
    "ES384": (ec.SECP384R1(), hashes.SHA384()),
    "ES512": (ec.SECP521R1(), hashes.SHA512()),
}

INSECURE_ALGORITHMS = {"none", "NONE"}


def _load_shared_secret(value: str | bytes) -> bytes:
    if isinstance(value, bytes):
        return value
    return value.encode("utf-8")


def _jwk_to_key(jwk: dict[str, Any]) -> Any:
    kty = jwk.get("kty")
    if kty == "oct":
        key = jwk.get("k")
        if not isinstance(key, str):  # pragma: no cover - defensive
            raise JWTDecodeError("Octet JWK is missing the 'k' parameter")
        return _b64url_decode(key)
    if kty == "RSA":
        n_raw = jwk.get("n")
        e_raw = jwk.get("e")
        if not isinstance(n_raw, str) or not isinstance(e_raw, str):  # pragma: no cover - defensive
            raise JWTDecodeError("RSA JWK is missing modulus or exponent")
        n = int.from_bytes(_b64url_decode(n_raw), "big")
        e = int.from_bytes(_b64url_decode(e_raw), "big")
        public_numbers = rsa.RSAPublicNumbers(e=e, n=n)
        return public_numbers.public_key()
    if kty == "EC":
        x_raw = jwk.get("x")
        y_raw = jwk.get("y")
        curve_name = jwk.get("crv")
        if not all(isinstance(v, str) for v in (x_raw, y_raw, curve_name)):
            raise JWTDecodeError("EC JWK is missing parameters")
        curve, _ = ECDSA_HASHES.get(jwk.get("alg", "ES256"), (None, None))
        if curve is None:
            curve = {
                "P-256": ec.SECP256R1(),
                "P-384": ec.SECP384R1(),
                "P-521": ec.SECP521R1(),
            }.get(curve_name)
        if curve is None:
            raise JWTDecodeError(f"Unsupported EC curve: {curve_name}")
        x = int.from_bytes(_b64url_decode(x_raw), "big")
        y = int.from_bytes(_b64url_decode(y_raw), "big")
        public_numbers = ec.EllipticCurvePublicNumbers(x=x, y=y, curve=curve)
        return public_numbers.public_key()
    raise JWTDecodeError(f"Unsupported JWK key type: {kty}")


def _load_keys_from_json(data: Any) -> Iterable[Any]:
    if isinstance(data, dict):
        if "keys" in data:
            items = data["keys"]
            if not isinstance(items, list):
                raise JWTDecodeError("JWKS 'keys' must be a list")
            for jwk in items:
                if not isinstance(jwk, dict):
                    continue
                yield jwk
        else:
            yield data
    elif isinstance(data, list):
        for jwk in data:
            if isinstance(jwk, dict):
                yield jwk


def _load_key_material(
    key: str | bytes | dict[str, Any] | list[dict[str, Any]] | None,
    *,
    header: dict[str, Any],
) -> Any:
    if key is None:
        raise JWTDecodeError("A key is required for verification")
    if isinstance(key, (bytes, bytearray)):
        return bytes(key)
    if isinstance(key, str):
        text = key.strip()
        if text.startswith("-----BEGIN"):
            return serialization.load_pem_public_key(text.encode("utf-8"))
        if text.startswith("{") or text.startswith("["):
            try:
                parsed = json.loads(text)
            except json.JSONDecodeError as exc:  # pragma: no cover - defensive
                raise JWTDecodeError("Invalid JSON key material") from exc
            return _select_key_from_jwks(parsed, header=header)
        return _load_shared_secret(text)
    if isinstance(key, (dict, list)):
        return _select_key_from_jwks(key, header=header)
    raise JWTDecodeError("Unsupported key type")


def _select_key_from_jwks(
    data: dict[str, Any] | list[dict[str, Any]],
    *,
    header: dict[str, Any],
) -> Any:
    kid = header.get("kid")
    candidates = list(_load_keys_from_json(data))
    if not candidates:
        raise JWTDecodeError("JWKS does not contain any keys")
    selected: dict[str, Any] | None = None
    if kid is not None:
        for jwk in candidates:
            if jwk.get("kid") == kid:
                selected = jwk
                break
        if selected is None:
            raise JWTDecodeError(f"Key with kid={kid!r} not found in JWKS")
    else:
        if len(candidates) > 1:
            raise JWTDecodeError("JWKS contains multiple keys; specify 'kid'")
        selected = candidates[0]
    return _jwk_to_key(selected)


def _verify_signature(
    *,
    algorithm: str,
    signing_input: bytes,
    signature_raw: str,
    key_material: Any,
) -> bool:
    if algorithm in SUPPORTED_HMAC:
        secret = _load_shared_secret(key_material)
        expected = hmac.new(secret, signing_input, SUPPORTED_HMAC[algorithm]).digest()
        actual = _b64url_decode(signature_raw or "")
        return hmac.compare_digest(expected, actual)
    if algorithm in RSA_HASHES:
        if not hasattr(key_material, "verify"):
            raise JWTDecodeError("RSA verification requires a public key")
        signature = _b64url_decode(signature_raw or "")
        try:
            key_material.verify(signature, signing_input, asym_padding.PKCS1v15(), RSA_HASHES[algorithm])
        except InvalidSignature:
            return False
        return True
    if algorithm in RSA_PSS_HASHES:
        if not hasattr(key_material, "verify"):
            raise JWTDecodeError("RSA-PSS verification requires a public key")
        signature = _b64url_decode(signature_raw or "")
        try:
            key_material.verify(
                signature,
                signing_input,
                asym_padding.PSS(mgf=asym_padding.MGF1(RSA_PSS_HASHES[algorithm]), salt_length=asym_padding.PSS.MAX_LENGTH),
                RSA_PSS_HASHES[algorithm],
            )
        except InvalidSignature:
            return False
        return True
    if algorithm in ECDSA_HASHES:
        if not hasattr(key_material, "verify"):
            raise JWTDecodeError("ECDSA verification requires a public key")
        curve, digest = ECDSA_HASHES[algorithm]
        # Ensure provided key matches expected curve.
        if hasattr(key_material, "curve") and key_material.curve.name != curve.name:
            raise JWTDecodeError("ECDSA key does not match algorithm curve")
        signature = _b64url_decode(signature_raw or "")
        try:
            key_material.verify(signature, signing_input, ec.ECDSA(digest))
        except InvalidSignature:
            return False
        return True
    raise JWTDecodeError(f"Unsupported algorithm for verification: {algorithm}")


def decode_jwt(
    token: str,
    *,
    key: str | bytes | dict[str, Any] | list[dict[str, Any]] | None = None,
    verify: bool = False,
) -> DecodedJWT:
    """Decode a JWT token and optionally verify its signature.

    ``key`` can be a shared secret, PEM encoded public key, or JWKS/JWK data.
    When ``verify`` is false the signature is not checked and
    ``signature_valid`` is set to ``None``.
    """

    try:
        header_raw, payload_raw, signature_raw = token.split(".")
    except ValueError as exc:  # pragma: no cover - defensive
        raise JWTDecodeError("Token must have exactly 3 parts") from exc

    try:
        header = json.loads(_b64url_decode(header_raw))
        payload = json.loads(_b64url_decode(payload_raw))
    except (json.JSONDecodeError, ValueError) as exc:
        raise JWTDecodeError("Invalid JSON content") from exc

    algorithm = header.get("alg")
    key_id = header.get("kid")
    warnings: list[str] = []
    if algorithm is None:
        warnings.append("Token header does not declare an 'alg' value")
    elif algorithm in INSECURE_ALGORITHMS:
        warnings.append("Token uses the insecure 'alg: none' algorithm")

    signature_valid: bool | None = None
    if verify or key is not None:
        if algorithm is None:
            raise JWTDecodeError("Cannot verify token without 'alg' header")
        if algorithm in INSECURE_ALGORITHMS:
            raise JWTDecodeError("Tokens signed with 'none' cannot be verified")
        signing_input = f"{header_raw}.{payload_raw}".encode("ascii")
        key_material = _load_key_material(key, header=header)
        signature_valid = _verify_signature(
            algorithm=algorithm,
            signing_input=signing_input,
            signature_raw=signature_raw,
            key_material=key_material,
        )
    return DecodedJWT(
        header=header,
        payload=payload,
        signature_valid=signature_valid,
        algorithm=algorithm,
        key_id=key_id,
        warnings=warnings,
    )
