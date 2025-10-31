"""Utilities for working with XML payloads."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any, Iterable

from xml.etree import ElementTree

__all__ = [
    "pretty_xml",
    "minify_xml",
    "xml_to_json",
    "json_to_xml",
    "xpath_query",
]


def pretty_xml(value: str, *, indent: str = "  ") -> str:
    """Return a formatted XML string."""

    element = ElementTree.fromstring(value)
    ElementTree.indent(element, space=indent)  # type: ignore[attr-defined]
    return ElementTree.tostring(element, encoding="unicode", method="xml")


def minify_xml(value: str) -> str:
    """Return a compact XML string with insignificant whitespace removed."""

    element = ElementTree.fromstring(value)

    def _strip_whitespace(node: ElementTree.Element) -> None:
        if node.text is not None and not node.text.strip():
            node.text = None
        for child in list(node):
            _strip_whitespace(child)
            if child.tail is not None and not child.tail.strip():
                child.tail = None

    _strip_whitespace(element)
    return ElementTree.tostring(element, encoding="unicode", method="xml")


def xml_to_json(value: str, *, pretty: bool = True) -> str:
    """Convert an XML document to JSON text."""

    root = ElementTree.fromstring(value)
    payload = {root.tag: _element_to_data(root)}
    if pretty:
        return json.dumps(payload, indent=2, ensure_ascii=False)
    return json.dumps(payload, separators=(",", ":"), ensure_ascii=False)


def json_to_xml(value: str, *, pretty: bool = False, indent: str = "  ") -> str:
    """Convert JSON text produced by :func:`xml_to_json` back to XML."""

    parsed = json.loads(value)
    if not isinstance(parsed, dict) or len(parsed) != 1:
        raise ValueError("JSON must describe a single XML root element")

    root_tag, root_value = next(iter(parsed.items()))
    if not isinstance(root_tag, str):  # pragma: no cover - defensive
        raise ValueError("Root element name must be a string")

    root = _build_element(root_tag, root_value)
    xml_text = ElementTree.tostring(root, encoding="unicode", method="xml")
    if pretty:
        return pretty_xml(xml_text, indent=indent)
    return xml_text


def xpath_query(value: str, expression: str) -> list[str]:
    """Evaluate a safe subset of XPath ``expression`` against ``value``.

    The supported subset understands child (``/``) and descendant (``//``)
    navigation with optional single attribute equality predicates as well as
    ``text()`` and attribute selection as the final operation.
    """

    expression = expression.strip()
    if not expression:
        raise ValueError("XPath expression cannot be empty")

    attr_selection = None
    text_selection = False

    if expression.endswith("/text()"):
        expression = expression[: -len("/text()")]
        text_selection = True
    elif "/@" in expression:
        base, attr = expression.rsplit("/@", 1)
        if not _NAME_RE.fullmatch(attr):
            raise ValueError("Invalid attribute selector in XPath expression")
        expression = base
        attr_selection = attr

    expression = expression.strip()
    expression = _normalise_root_prefix(expression)
    tokens, absolute = _parse_xpath(expression)

    root = ElementTree.fromstring(value)
    nodes = _evaluate_xpath(root, tokens, absolute)

    if text_selection:
        return [(node.text or "").strip() for node in nodes]

    if attr_selection:
        return [node.attrib[attr_selection] for node in nodes if attr_selection in node.attrib]

    return [ElementTree.tostring(node, encoding="unicode", method="xml") for node in nodes]


def _element_to_data(element: ElementTree.Element) -> Any:
    children = list(element)
    text = (element.text or "").strip()
    if not children and not element.attrib:
        return text

    result: dict[str, Any] = {}
    if element.attrib:
        result["@attributes"] = dict(element.attrib)
    if text:
        result["@text"] = text

    if children:
        for child in children:
            child_value = _element_to_data(child)
            if child.tag in result:
                existing = result[child.tag]
                if isinstance(existing, list):
                    existing.append(child_value)
                else:
                    result[child.tag] = [existing, child_value]
            else:
                result[child.tag] = child_value

    return result


def _build_element(tag: str, value: Any) -> ElementTree.Element:
    element = ElementTree.Element(tag)

    if isinstance(value, dict):
        attributes = value.get("@attributes")
        if attributes is not None:
            if not isinstance(attributes, dict):
                raise ValueError("@attributes must be an object of name/value pairs")
            for name, attr_value in attributes.items():
                if not isinstance(name, str):
                    raise ValueError("Attribute names must be strings")
                element.set(name, str(attr_value))

        if "@text" in value:
            element.text = "" if value["@text"] is None else str(value["@text"])

        child_items = [(key, value[key]) for key in value if not key.startswith("@")]
        for child_tag, child_value in child_items:
            if isinstance(child_value, list):
                for item in child_value:
                    element.append(_build_element(child_tag, item))
            else:
                element.append(_build_element(child_tag, child_value))
        return element

    if isinstance(value, list):
        raise ValueError("Lists must be associated with element names")

    if value is None:
        element.text = ""
    else:
        element.text = str(value)
    return element


def _normalise_root_prefix(expression: str) -> str:
    if expression.startswith(".//"):
        return expression[1:]
    if expression.startswith("./"):
        return expression[2:]
    return expression


@dataclass(slots=True)
class _XPathToken:
    axis: str
    tag: str
    predicate: tuple[str, str] | None


_NAME_RE = re.compile(r"^[A-Za-z_][\w\-.]*$")
_SEGMENT_RE = re.compile(
    r"^(?P<tag>\*|[A-Za-z_][\w\-.]*)"
    r"(?:\[@(?P<attr>[A-Za-z_][\w\-.]*)=(?P<quote>['\"])(?P<value>[^'\"]*)(?P=quote)\])?$"
)


def _parse_xpath(expression: str) -> tuple[list[_XPathToken], bool]:
    absolute = False
    axis = "child"
    index = 0

    if expression.startswith("//"):
        axis = "descendant"
        index = 2
    elif expression.startswith("/"):
        absolute = True
        index = 1

    length = len(expression)
    tokens: list[_XPathToken] = []

    while index < length:
        if expression.startswith("//", index):
            axis = "descendant"
            index += 2
            continue
        if expression.startswith("/", index):
            axis = "child"
            index += 1
            continue

        next_sep = expression.find("/", index)
        if next_sep == -1:
            segment = expression[index:]
            index = length
        else:
            segment = expression[index:next_sep]
            index = next_sep

        segment = segment.strip()
        if not segment:
            raise ValueError("Malformed XPath expression")

        match = _SEGMENT_RE.fullmatch(segment)
        if not match:
            raise ValueError("Unsupported XPath segment: %s" % segment)

        tag = match.group("tag")
        attr = match.group("attr")
        if attr and not _NAME_RE.fullmatch(attr):
            raise ValueError("Invalid attribute name in predicate")
        predicate = (attr, match.group("value")) if attr else None
        tokens.append(_XPathToken(axis=axis, tag=tag, predicate=predicate))
        axis = "child"

    return tokens, absolute


def _evaluate_xpath(root: ElementTree.Element, tokens: list[_XPathToken], absolute: bool) -> list[ElementTree.Element]:
    if not tokens:
        return [root]

    nodes: Iterable[ElementTree.Element] = [root]

    if absolute:
        first, *rest = tokens
        if first.axis != "child":
            raise ValueError("Absolute XPath must start with a direct child segment")
        if not _matches(root, first):
            return []
        nodes = [root]
        tokens = rest
    else:
        nodes = [root]

    for token in tokens:
        next_nodes: list[ElementTree.Element] = []
        if token.axis == "child":
            for node in nodes:
                for child in list(node):
                    if _matches(child, token):
                        next_nodes.append(child)
        else:  # descendant
            for node in nodes:
                iterator = node.iter()
                next(iterator)  # skip self
                for descendant in iterator:
                    if _matches(descendant, token):
                        next_nodes.append(descendant)
        nodes = next_nodes

    return list(nodes)


def _matches(node: ElementTree.Element, token: _XPathToken) -> bool:
    if token.tag != "*" and node.tag != token.tag:
        return False
    if token.predicate:
        attr, value = token.predicate
        return node.attrib.get(attr) == value
    return True
