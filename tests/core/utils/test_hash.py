"""Tests for :mod:`src.core.utils.hash_`."""

from __future__ import annotations

import hashlib
import hmac
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.core.utils import hash_


def test_available_algorithms_include_common_digests():
    algorithms = hash_.available_algorithms()
    assert algorithms == sorted(algorithms)
    for algo in ("md5", "sha1", "sha224", "sha256", "sha384", "sha512"):
        assert algo in algorithms


def test_calculate_hash_matches_hashlib():
    payload = "Hello, hashing!"
    expected = hashlib.sha256(payload.encode()).hexdigest()
    assert hash_.calculate_hash(payload, "SHA256") == expected


def test_calculate_hash_rejects_unknown_algorithm():
    with pytest.raises(ValueError):
        hash_.calculate_hash("data", "made-up")


def test_calculate_file_hash_streams(tmp_path):
    content = b"abc123" * 2048
    target = tmp_path / "sample.bin"
    target.write_bytes(content)

    expected = hashlib.sha1(content).hexdigest()
    digest = hash_.calculate_file_hash(target, "sha1", chunk_size=8192)

    assert digest == expected


def test_calculate_file_hash_validates_chunk_size(tmp_path):
    target = tmp_path / "empty.txt"
    target.write_text("")

    with pytest.raises(ValueError):
        hash_.calculate_file_hash(target, chunk_size=0)


def test_calculate_hmac_masks_secret():
    result = hash_.calculate_hmac("message", "supersecret", "sha256")

    expected = hmac.new(b"supersecret", b"message", "sha256").hexdigest()
    assert result.algorithm == "sha256"
    assert result.hexdigest == expected
    assert result.secret_masked.endswith("cret")
    assert "supersecret" not in result.secret_masked


def test_calculate_hmac_with_bytes_secret_and_custom_visibility():
    secret = b"\xff\x01key"
    result = hash_.calculate_hmac("payload", secret, "sha1", visible_secret_chars=0)

    expected = hmac.new(secret, b"payload", "sha1").hexdigest()
    assert result.hexdigest == expected
    assert set(result.secret_masked) == {"*"}


def test_calculate_hmac_rejects_unknown_algorithm():
    with pytest.raises(ValueError):
        hash_.calculate_hmac("data", "secret", "sha999")
