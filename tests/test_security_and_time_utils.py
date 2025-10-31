import datetime as dt

from src.core.utils import jwt_, regex_, time_, uuid_ulid


def create_sample_jwt(secret: str) -> str:
    header = "{\"alg\":\"HS256\"}"
    payload = "{\"sub\":\"123\",\"name\":\"Alice\"}"
    import base64
    import hmac
    import hashlib

    def encode(segment: str) -> str:
        data = segment.encode()
        return base64.urlsafe_b64encode(data).rstrip(b"=").decode()

    signing_input = f"{encode(header)}.{encode(payload)}"
    signature = hmac.new(secret.encode(), signing_input.encode(), hashlib.sha256).digest()
    signature_b64 = base64.urlsafe_b64encode(signature).rstrip(b"=").decode()
    return f"{signing_input}.{signature_b64}"


def test_jwt_decode_and_verify():
    secret = "topsecret"
    token = create_sample_jwt(secret)
    decoded = jwt_.decode_jwt(token, key=secret, verify=True)
    assert decoded.header["alg"] == "HS256"
    assert decoded.payload["name"] == "Alice"
    assert decoded.signature_valid is True


def test_jwt_rejects_wrong_secret():
    secret = "topsecret"
    token = create_sample_jwt(secret)
    decoded = jwt_.decode_jwt(token, key="wrong", verify=True)
    assert decoded.signature_valid is False


def test_uuid_and_ulid_helpers():
    uid = uuid_ulid.generate_uuid(4)
    info = uuid_ulid.inspect_uuid(str(uid))
    assert info.is_valid and info.version == 4
    ulid_value = uuid_ulid.generate_ulid()
    inspected = uuid_ulid.inspect_ulid(str(ulid_value))
    assert inspected.timestamp.year >= 2000


def test_time_conversions():
    now = dt.datetime.now(tz=dt.timezone.utc)
    epoch = time_.datetime_to_epoch(now)
    restored = time_.epoch_to_datetime(epoch, tz="UTC")
    assert restored.tzinfo is not None
    shifted = time_.add_duration(now, hours=1)
    assert shifted.hour in {(now.hour + 1) % 24, now.hour + 1}
    converted = time_.convert_timezone(now, "Europe/Paris")
    assert getattr(converted.tzinfo, "name", converted.tzinfo.tzname(converted)) == "Europe/Paris"


def test_regex_matches_and_timeout():
    result = regex_.run_regex(r"a.+?c", "abc abc", limit=1)
    assert result.matches[0].value == "abc"

    result = regex_.run_regex(r"(a+)+$", "a" * 2000, timeout=0.0001)
    assert result.timed_out is True


def test_parse_natural_delta():
    parsed = time_.parse_natural_delta("in 2 hours")
    assert parsed.seconds > 0
