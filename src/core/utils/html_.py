"""HTML utilities."""

from __future__ import annotations

import html
import re
from html.parser import HTMLParser

__all__ = [
    "encode_entities",
    "decode_entities",
    "strip_tags",
    "minify_html",
    "prettify_html",
]

_VOID_TAGS = {
    "area",
    "base",
    "br",
    "col",
    "embed",
    "hr",
    "img",
    "input",
    "link",
    "meta",
    "param",
    "source",
    "track",
    "wbr",
}

_PRESERVE_WHITESPACE_TAGS = {"pre", "code", "textarea", "script", "style"}
_BLOCK_ELEMENTS = {
    "address",
    "article",
    "aside",
    "blockquote",
    "div",
    "dl",
    "fieldset",
    "figcaption",
    "figure",
    "footer",
    "form",
    "h1",
    "h2",
    "h3",
    "h4",
    "h5",
    "h6",
    "header",
    "hr",
    "li",
    "main",
    "nav",
    "ol",
    "p",
    "pre",
    "section",
    "table",
    "ul",
}


def _format_attributes(attrs: list[tuple[str, str | None]]) -> str:
    if not attrs:
        return ""
    formatted: list[str] = []
    for key, value in attrs:
        if value is None:
            formatted.append(key)
        else:
            escaped = html.escape(value, quote=True)
            formatted.append(f"{key}=\"{escaped}\"")
    return " " + " ".join(formatted)


def encode_entities(value: str) -> str:
    """HTML-escape a string, encoding quotes by default."""

    return html.escape(value, quote=True)


def decode_entities(value: str) -> str:
    """Decode HTML entities into their corresponding characters."""

    return html.unescape(value)


class _Stripper(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.result: list[str] = []

    def handle_data(self, data: str) -> None:  # pragma: no cover - trivial
        if data:
            self.result.append(data)

    def handle_entityref(self, name: str) -> None:  # pragma: no cover - trivial
        self.result.append(html.unescape(f"&{name};"))

    def handle_charref(self, name: str) -> None:  # pragma: no cover - trivial
        self.result.append(html.unescape(f"&#{name};"))

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:  # pragma: no cover - trivial
        if tag == "br":
            self.result.append("\n")
        elif tag in _BLOCK_ELEMENTS and (not self.result or not self.result[-1].endswith("\n")):
            self.result.append("\n")

    def handle_endtag(self, tag: str) -> None:  # pragma: no cover - trivial
        if tag in _BLOCK_ELEMENTS:
            if not self.result or not self.result[-1].endswith("\n"):
                self.result.append("\n")


def strip_tags(value: str) -> str:
    """Remove all HTML tags while keeping textual content."""

    parser = _Stripper()
    parser.feed(value)
    parser.close()
    text = "".join(parser.result)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


class _HTMLMinifier(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=False)
        self._result: list[str] = []
        self._stack: list[tuple[str, bool]] = []
        self._preserve_depth = 0
        self._pending_space = False
        self._last_was_text = False

    def getvalue(self) -> str:
        return "".join(self._result)

    def _append(self, text: str, *, raw: bool = False) -> None:
        if not text:
            return
        if not raw:
            text = re.sub(r"\s+", " ", text)
        if not self._result:
            text = text.lstrip()
        elif self._result[-1].endswith(" ") and text.startswith(" "):
            text = text.lstrip()
        if text:
            self._result.append(text)

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if self._pending_space and self._result and not self._result[-1][-1].isspace():
            self._append(" ", raw=True)
        self._pending_space = False
        self._append(f"<{tag}{_format_attributes(attrs)}>")
        self._last_was_text = False
        if tag not in _VOID_TAGS:
            is_preserve = tag in _PRESERVE_WHITESPACE_TAGS
            self._stack.append((tag, is_preserve))
            if is_preserve:
                self._preserve_depth += 1

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if self._pending_space and self._result and not self._result[-1][-1].isspace():
            self._append(" ", raw=True)
        self._pending_space = False
        self._append(f"<{tag}{_format_attributes(attrs)}/>")
        self._last_was_text = False

    def handle_endtag(self, tag: str) -> None:
        self._pending_space = False
        if self._stack:
            for index in range(len(self._stack) - 1, -1, -1):
                name, is_preserve = self._stack.pop()
                if is_preserve:
                    self._preserve_depth = max(0, self._preserve_depth - 1)
                if name == tag:
                    break
        self._append(f"</{tag}>")
        self._last_was_text = False

    def handle_data(self, data: str) -> None:
        if not data:
            return
        had_text_before = self._last_was_text
        if self._preserve_depth > 0:
            self._append(data, raw=True)
            if data.strip():
                self._last_was_text = True
            return
        has_leading = data[0].isspace()
        has_trailing = data[-1].isspace()
        collapsed = " ".join(data.split())
        if collapsed:
            if (self._pending_space or has_leading) and self._result and not self._result[-1][-1].isspace():
                self._append(" ", raw=True)
            self._append(collapsed)
            self._last_was_text = True
        else:
            self._last_was_text = False
        if collapsed and has_trailing:
            self._pending_space = True
        elif not collapsed and (has_leading or has_trailing) and had_text_before:
            self._pending_space = True
        else:
            self._pending_space = False

    def handle_entityref(self, name: str) -> None:
        self.handle_data(f"&{name};")

    def handle_charref(self, name: str) -> None:
        self.handle_data(f"&#{name};")

    def handle_comment(self, data: str) -> None:
        cleaned = data.strip()
        if cleaned:
            self._append(f"<!--{cleaned}-->")
        self._last_was_text = False

    def handle_decl(self, decl: str) -> None:
        self._append(f"<!{decl}>")
        self._last_was_text = False


def minify_html(value: str) -> str:
    """Minify HTML while preserving significant whitespace in certain tags."""

    parser = _HTMLMinifier()
    parser.feed(value)
    parser.close()
    return parser.getvalue().strip()


class _HTMLPrettifier(HTMLParser):
    def __init__(self, indent: str = "  ") -> None:
        super().__init__(convert_charrefs=False)
        self._indent = indent
        self._result: list[str] = []
        self._pending_data: list[str] = []
        self._stack: list[tuple[str, bool]] = []
        self._indent_level = 0
        self._preserve_depth = 0

    def _current_indent(self) -> str:
        return self._indent * self._indent_level

    def _emit_data(self) -> None:
        if not self._pending_data:
            return
        data = "".join(self._pending_data)
        self._pending_data.clear()
        if self._preserve_depth > 0:
            if data:
                self._result.append(data)
            return
        collapsed = " ".join(data.split())
        if collapsed:
            self._result.append(f"{self._current_indent()}{collapsed}")

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self._emit_data()
        self._result.append(f"{self._current_indent()}<{tag}{_format_attributes(attrs)}>")
        if tag not in _VOID_TAGS:
            is_preserve = tag in _PRESERVE_WHITESPACE_TAGS
            self._stack.append((tag, is_preserve))
            if is_preserve:
                self._preserve_depth += 1
            else:
                self._indent_level += 1

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self._emit_data()
        self._result.append(f"{self._current_indent()}<{tag}{_format_attributes(attrs)}/>")

    def handle_endtag(self, tag: str) -> None:
        self._emit_data()
        if self._stack:
            for index in range(len(self._stack) - 1, -1, -1):
                name, is_preserve = self._stack.pop()
                if is_preserve:
                    self._preserve_depth = max(0, self._preserve_depth - 1)
                else:
                    self._indent_level = max(0, self._indent_level - 1)
                if name == tag:
                    break
        self._result.append(f"{self._current_indent()}</{tag}>")

    def handle_data(self, data: str) -> None:
        if data:
            self._pending_data.append(data)

    def handle_entityref(self, name: str) -> None:
        self._pending_data.append(f"&{name};")

    def handle_charref(self, name: str) -> None:
        self._pending_data.append(f"&#{name};")

    def handle_comment(self, data: str) -> None:
        self._emit_data()
        cleaned = data.strip()
        if cleaned:
            self._result.append(f"{self._current_indent()}<!-- {cleaned} -->")

    def handle_decl(self, decl: str) -> None:
        self._emit_data()
        self._result.append(f"{self._current_indent()}<!{decl}>")

    def close(self) -> None:
        super().close()
        self._emit_data()

    def getvalue(self) -> str:
        lines = [line.rstrip() for line in self._result]
        return "\n".join(line for line in lines if line or line == "")


def prettify_html(value: str, *, indent: str = "  ") -> str:
    """Pretty format an HTML string using a simple indentation strategy."""

    parser = _HTMLPrettifier(indent=indent)
    parser.feed(value)
    parser.close()
    return parser.getvalue().strip()
