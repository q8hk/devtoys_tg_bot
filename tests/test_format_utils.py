from src.core.utils import code_, csv_tsv, html_, xml_


def test_csv_conversion_and_stats():
    csv_text = "name,age\nAlice,30\nBob,25"
    tsv = csv_tsv.convert_delimiter(csv_text, target="\t")
    assert "Alice\t30" in tsv
    stats = csv_tsv.table_stats(csv_text)
    assert stats["rows"] == 3
    assert stats["columns"] == 2
    json_rows = csv_tsv.to_json_rows(csv_text)
    assert json_rows[0]["name"] == "Alice"


def test_xml_pretty_minify_and_json():
    xml_text = "<root><item id='1'>value</item></root>"
    pretty = xml_.pretty_xml(xml_text)
    assert "\n" in pretty
    assert xml_.minify_xml(pretty) == xml_.minify_xml(xml_text)
    json_repr = xml_.xml_to_json(xml_text)
    assert '"@attributes"' in json_repr


def test_html_helpers():
    html_text = "<p>Hello &amp; <strong>world</strong></p>"
    decoded = html_.decode_entities(html_text)
    stripped = html_.strip_tags(decoded)
    assert stripped == "Hello & world"
    assert html_.minify_html(decoded).startswith("<p>")
    assert html_.encode_entities("<tag>") == "&lt;tag&gt;"


def test_code_utils():
    password = code_.generate_password(length=12, use_digits=False, use_symbols=False)
    assert len(password) == 12
    assert password.isalpha()
    diff = code_.text_diff("a\n", "b\n")
    assert diff.startswith("---")
