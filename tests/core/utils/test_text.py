"""Unit tests for :mod:`src.core.utils.text`."""
from __future__ import annotations

import pytest
from src.core.utils import text


@pytest.mark.parametrize(
    "raw, expected",
    [
        ("  Hello\nWorld  ", "Hello\nWorld"),
        ("\ttrim\n", "trim"),
    ],
)
def test_trim(raw: str, expected: str) -> None:
    assert text.trim(raw) == expected


@pytest.mark.parametrize(
    "raw, expected",
    [
        ("  leading", "leading"),
        ("\n\nvalue", "value"),
    ],
)
def test_ltrim(raw: str, expected: str) -> None:
    assert text.ltrim(raw) == expected


@pytest.mark.parametrize(
    "raw, expected",
    [
        ("trailing   ", "trailing"),
        ("value\n\t  ", "value"),
    ],
)
def test_rtrim(raw: str, expected: str) -> None:
    assert text.rtrim(raw) == expected


@pytest.mark.parametrize(
    "content, prefix, indent_empty, expected",
    [
        ("line1\n\nline2", "--", False, "--line1\n\n--line2"),
        ("line1\n\nline2", "--", True, "--line1\n--\n--line2"),
    ],
)
def test_indent(content: str, prefix: str, indent_empty: bool, expected: str) -> None:
    assert text.indent(content, prefix=prefix, indent_empty=indent_empty) == expected


def test_dedent() -> None:
    content = "    foo\n        bar"
    assert text.dedent(content) == "foo\n    bar"


def test_normalize_whitespace() -> None:
    raw = "  Hello\tworld\nthis   is\r\n  neat  "
    assert text.normalize_whitespace(raw) == "Hello world this is neat"


@pytest.mark.parametrize(
    "value, upper, lower, title, sentence",
    [
        ("hello world", "HELLO WORLD", "hello world", "Hello World", "Hello world"),
        ("hELLO wORLD", "HELLO WORLD", "hello world", "Hello World", "Hello world"),
        ("", "", "", "", ""),
    ],
)
def test_case_conversions(value: str, upper: str, lower: str, title: str, sentence: str) -> None:
    assert text.to_upper(value) == upper
    assert text.to_lower(value) == lower
    assert text.to_title(value) == title
    assert text.to_sentence(value) == sentence


def test_slugify_basic_and_custom_separator() -> None:
    assert text.slugify("Héllo, World!") == "hello-world"
    assert text.slugify("Hello     world??", separator="_") == "hello_world"
    assert text.slugify("###") == "-"


def test_sort_lines_preserves_trailing_newlines() -> None:
    content = "b\na\n"
    assert text.sort_lines(content) == "a\nb\n"
    assert text.sort_lines("b\nA", case_sensitive=False) == "A\nb"
    assert text.sort_lines("b\nA", case_sensitive=True, reverse=True) == "b\nA"


def test_unique_lines_behaviour() -> None:
    content = "alpha\nBeta\nalpha\n"
    assert text.unique_lines(content) == "alpha\nBeta\n"
    assert text.unique_lines(content, preserve_order=False) == "Beta\nalpha\n"
    assert text.unique_lines("\n") == "\n"


def test_line_numbering_round_trip() -> None:
    source = "alpha\n\nbeta\n"
    numbered = text.add_line_numbers(source, start=5, padding=2, separator=" : ")
    assert numbered == "05 : alpha\n06 : \n07 : beta\n08 : "
    assert text.strip_line_numbers(numbered, separator=" : ") == source


def test_strip_line_numbers_tolerant() -> None:
    assert text.strip_line_numbers("no numbers here") == "no numbers here"


def test_generate_lorem_ipsum_deterministic() -> None:
    config = text.LoremConfig(words=5, seed=42)
    first = text.generate_lorem_ipsum(config)
    second = text.generate_lorem_ipsum(config)
    assert first == second
    assert first[0].isupper()
    assert first.endswith(".")


def test_generate_lorem_ipsum_minimum_length() -> None:
    config = text.LoremConfig(words=0, seed=1)
    result = text.generate_lorem_ipsum(config)
    assert len(result.split()) == 1
