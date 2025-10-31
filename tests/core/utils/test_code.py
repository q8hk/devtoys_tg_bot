"""Tests for :mod:`src.core.utils.code_`."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

import pytest

from src.core.utils.code_ import (
    format_css,
    format_js,
    format_json,
    generate_password,
    generate_token,
    minify_css,
    minify_js,
    minify_json,
    text_diff,
)


def test_format_json_and_minify_json_roundtrip() -> None:
    raw = '{"b":1,"a":{"c":2}}'
    formatted = format_json(raw)
    assert formatted == '{\n  "a": {\n    "c": 2\n  },\n  "b": 1\n}'
    assert minify_json(formatted) == '{"a":{"c":2},"b":1}'


def test_format_css_and_minify_css() -> None:
    css = """
    /* comment */
    body { color: red; margin: 0 auto; content: "a b"; }
    """
    formatted = format_css(css)
    assert formatted == """body {\n    color: red;\n    margin: 0 auto;\n    content: "a b";\n}"""

    compact = minify_css(css)
    assert compact == 'body{color:red;margin:0 auto;content:"a b";}'


def test_format_js_and_minify_js() -> None:
    js = """
    // say hello
    function greet(name){console.log("Hello, " + name);if(name){return name.toUpperCase();}}
    """
    formatted = format_js(js)
    assert formatted == (
        "function greet(name)\n"
        "{\n"
        "    console.log(\"Hello, \" + name);\n"
        "    if(name)\n"
        "    {\n"
        "        return name.toUpperCase();\n"
        "    }\n"
        "}"
    )

    compact = minify_js(js)
    assert compact == 'function greet(name){console.log("Hello, "+name);if(name){return name.toUpperCase();}}'


def test_generate_password_policy() -> None:
    password = generate_password(length=12)
    assert len(password) == 12
    assert any(ch.islower() for ch in password)
    assert any(ch.isupper() for ch in password)
    assert any(ch.isdigit() for ch in password)
    assert any(ch in "!@#$%^&*()-_=+[]{};:'\"|,.<>/?`~" for ch in password)


def test_generate_password_policy_validation() -> None:
    with pytest.raises(ValueError):
        generate_password(length=2)


def test_generate_token_custom_alphabet() -> None:
    token = generate_token(length=24, alphabet="ABC")
    assert len(token) == 24
    assert set(token) <= {"A", "B", "C"}


def test_generate_token_invalid_length() -> None:
    with pytest.raises(ValueError):
        generate_token(length=0)


def test_text_diff() -> None:
    diff = text_diff("hello\nworld\n", "hello\nworld!\n")
    assert diff.startswith("--- original\n+++")
    assert "-world" in diff
    assert "+world!" in diff
