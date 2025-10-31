import hashlib

from src.core.utils import base64_, hash_, url


def test_base64_encode_decode_text():
    encoded = base64_.encode_text("hello")
    assert encoded == "aGVsbG8="
    assert base64_.decode_text(encoded) == "hello"


def test_data_uri_detection():
    uri = "data:text/plain;base64," + base64_.encode_text("payload")
    parsed = base64_.detect_data_uri(uri)
    assert parsed and parsed.media_type == "text/plain"
    assert parsed.data == b"payload"


def test_hash_and_hmac():
    digest = hash_.calculate_hash("devtoys", algorithm="sha256")
    assert digest == hashlib.sha256(b"devtoys").hexdigest()
    signature = hash_.calculate_hmac("message", "secret", algorithm="sha1")
    assert len(signature) == 40


def test_url_helpers():
    parsed = url.parse_url("https://example.com/path?foo=bar&foo=baz")
    mapping = url.parse_query_string(parsed.query)
    assert mapping["foo"] == ["bar", "baz"]
    rebuilt = url.build_url(parsed, query={"foo": ["one", "two"], "q": "search"})
    assert "q=search" in rebuilt
    assert "foo=one" in rebuilt
