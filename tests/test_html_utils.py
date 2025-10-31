"""Tests for HTML utility helpers."""

from __future__ import annotations

from src.core.utils import html_


def test_entity_encoding_and_decoding() -> None:
    raw = '<div class="title">Tom & "Jerry"</div>'
    encoded = html_.encode_entities(raw)
    assert encoded == "&lt;div class=&quot;title&quot;&gt;Tom &amp; &quot;Jerry&quot;&lt;/div&gt;"
    assert html_.decode_entities(encoded) == raw


def test_strip_tags_preserves_textual_structure() -> None:
    html_text = "<div><p>Hello<br>world &amp; friends</p><p>Line 2</p></div>"
    stripped = html_.strip_tags(html_text)
    assert stripped.splitlines() == ["Hello", "world & friends", "Line 2"]


def test_minify_preserves_preformatted_blocks() -> None:
    html_text = """
    <!DOCTYPE html>
    <html>
      <body>
        <p>Hello <strong>world</strong>!</p>
        <pre>  code
line2
</pre>
      </body>
    </html>
    """

    minified = html_.minify_html(html_text)
    assert minified.startswith("<!DOCTYPE html><html><body>")
    assert "<p>Hello <strong>world</strong>!</p>" in minified
    assert "<pre>  code\nline2\n</pre>" in minified


def test_prettify_adds_consistent_indentation() -> None:
    html_text = "<div><p>Hello<strong>world</strong></p><pre>  code\n</pre></div>"
    pretty = html_.prettify_html(html_text)
    lines = pretty.splitlines()
    assert lines[0] == "<div>"
    assert lines[1].startswith("  <p>")
    assert "Hello" in lines[2]
    assert lines[3].strip() == "<strong>"
    assert "  code" in lines[-3]
