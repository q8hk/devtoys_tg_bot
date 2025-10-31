"""XML utilities."""

from __future__ import annotations

import json
from xml.dom import minidom
from xml.etree import ElementTree

__all__ = [
    "pretty_xml",
    "minify_xml",
    "xml_to_json",
]


def pretty_xml(value: str) -> str:
    """Pretty format XML."""

    parsed = minidom.parseString(value)
    pretty = parsed.toprettyxml(indent="  ")
    lines = [line for line in pretty.splitlines() if line.strip()]
    if lines and lines[0].startswith("<?xml"):
        lines = lines[1:]
    return "\n".join(lines)


def minify_xml(value: str) -> str:
    """Remove whitespace from XML."""

    element = ElementTree.fromstring(value)

    def _strip_whitespace(node: ElementTree.Element) -> None:
        if node.text:
            node.text = node.text.strip()
        if node.tail:
            node.tail = node.tail.strip()
        for child in list(node):
            _strip_whitespace(child)

    _strip_whitespace(element)
    return ElementTree.tostring(element, encoding="unicode", method="xml")


def xml_to_json(value: str) -> str:
    """Convert an XML document to a JSON string."""

    def recurse(element: ElementTree.Element) -> dict[str, object]:
        children = list(element)
        node: dict[str, object] = {"@text": element.text.strip() if element.text else ""}
        if element.attrib:
            node["@attributes"] = dict(element.attrib)
        if children:
            node["children"] = [{child.tag: recurse(child)} for child in children]
        return node

    root = ElementTree.fromstring(value)
    return json.dumps({root.tag: recurse(root)}, indent=2, ensure_ascii=False)
