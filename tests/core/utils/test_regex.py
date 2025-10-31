import regex as regex_module
import pytest

from src.core.utils import regex_ as regex_utils


def test_run_regex_basic_matches_and_groups():
    text = "Invoice 42 due 2024"
    result = regex_utils.run_regex(r"(?P<num>\d+)", text, limit=5)

    assert not result.timed_out
    assert len(result.matches) == 2

    first = result.matches[0]
    assert first.value == "42"
    assert first.groups == ("42",)
    assert first.named_groups == {"num": "42"}
    assert first.span == (8, 10)


def test_run_regex_respects_limit():
    result = regex_utils.run_regex(r"\w+", "alpha beta gamma", limit=2)

    assert [match.value for match in result.matches] == ["alpha", "beta"]


def test_run_regex_handles_invalid_pattern():
    with pytest.raises(ValueError):
        regex_utils.run_regex(r"(unbalanced", "text")


def test_run_regex_marks_timeout(monkeypatch):
    class DummyPattern:
        def finditer(self, text: str, **kwargs):
            raise TimeoutError

    monkeypatch.setattr(regex_utils.regex, "compile", lambda pattern, flags: DummyPattern())

    result = regex_utils.run_regex(r".+", "payload")

    assert result.timed_out is True
    assert result.matches == []


def test_parse_flag_tokens_supports_multiple_sources():
    combined = regex_utils.parse_flag_tokens("im")
    assert combined == regex_module.IGNORECASE | regex_module.MULTILINE

    combined_iterable = regex_utils.parse_flag_tokens(["s", "x"])
    assert combined_iterable == regex_module.DOTALL | regex_module.VERBOSE

    with pytest.raises(ValueError):
        regex_utils.parse_flag_tokens("q")
