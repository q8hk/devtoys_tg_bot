import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.core.utils import xml_ as xml_utils


SAMPLE_XML = """
<library>
  <book id=\"1\" genre=\"fiction\">
    <title>1984</title>
    <author>George Orwell</author>
  </book>
  <book id=\"2\" genre=\"nonfiction\">
    <title>Sapiens</title>
    <author>Yuval Noah Harari</author>
  </book>
</library>
""".strip()


def test_pretty_and_minify_roundtrip():
    minified = xml_utils.minify_xml(SAMPLE_XML)
    assert "\n" not in minified

    pretty = xml_utils.pretty_xml(minified)
    assert "\n  <book" in pretty

    assert xml_utils.minify_xml(pretty) == minified


def test_xml_json_roundtrip():
    json_text = xml_utils.xml_to_json(SAMPLE_XML)
    data = json.loads(json_text)

    assert set(data.keys()) == {"library"}
    library = data["library"]
    assert len(library["book"]) == 2
    assert library["book"][0]["title"] == "1984"
    assert library["book"][1]["author"] == "Yuval Noah Harari"

    reconstructed = xml_utils.json_to_xml(json_text)
    assert xml_utils.minify_xml(reconstructed) == xml_utils.minify_xml(SAMPLE_XML)


def test_json_to_xml_pretty_option():
    json_text = xml_utils.xml_to_json(SAMPLE_XML, pretty=False)
    xml_text = xml_utils.json_to_xml(json_text, pretty=True)
    assert "\n  <book" in xml_text


def test_xpath_queries():
    titles = xml_utils.xpath_query(SAMPLE_XML, ".//book[@genre='fiction']/title/text()")
    assert titles == ["1984"]

    ids = xml_utils.xpath_query(SAMPLE_XML, ".//book/@id")
    assert ids == ["1", "2"]

    books = xml_utils.xpath_query(SAMPLE_XML, "/library/book")
    assert [xml_utils.minify_xml(book) for book in books] == [
        '<book id="1" genre="fiction"><title>1984</title><author>George Orwell</author></book>',
        '<book id="2" genre="nonfiction"><title>Sapiens</title><author>Yuval Noah Harari</author></book>',
    ]


def test_xpath_validation_errors():
    with pytest.raises(ValueError):
        xml_utils.xpath_query(SAMPLE_XML, "../book")
    with pytest.raises(ValueError):
        xml_utils.xpath_query(SAMPLE_XML, "book[price>10]")


def test_json_to_xml_validation():
    with pytest.raises(ValueError):
        xml_utils.json_to_xml("[]")
