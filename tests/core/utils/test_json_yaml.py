import json
import textwrap

from src.core.utils import json_yaml


def test_pretty_and_minify_roundtrip():
    raw = json.dumps({"foo": [1, 2, 3], "bar": {"nested": True}})
    pretty = json_yaml.pretty_json(raw)
    assert "\n" in pretty
    assert json.loads(json_yaml.minify_json(pretty)) == json.loads(raw)


def test_conversion_roundtrip():
    data = {"project": "DevToys", "features": ["convert", "validate"], "active": True}
    json_text = json_yaml.to_json(data, pretty=True)
    yaml_text = json_yaml.convert_json_to_yaml(json_text)
    converted_back = json_yaml.convert_yaml_to_json(yaml_text, pretty=False)
    assert json.loads(converted_back) == json.loads(json_text)


def test_validation_results():
    valid = json_yaml.validate_json('{"ok": 1}')
    assert valid.is_valid and valid.data == {"ok": 1}

    invalid = json_yaml.validate_json('{broken}')
    assert not invalid.is_valid
    assert invalid.error


def test_validate_yaml_success_and_failure():
    yaml_text = textwrap.dedent(
        """
        name: DevToys
        features:
          - convert
          - validate
        """
    ).strip()
    result = json_yaml.validate_yaml(yaml_text)
    assert result.is_valid and result.data["name"] == "DevToys"

    invalid = json_yaml.validate_yaml(": broken")
    assert not invalid.is_valid
    assert invalid.error


def test_auto_detect_json_yaml_unknown():
    json_result = json_yaml.detect_payload_format('{"foo": 1}')
    assert json_result.format == "json" and json_result.data == {"foo": 1}

    yaml_result = json_yaml.detect_payload_format("foo: bar\nitems:\n  - 1\n")
    assert yaml_result.format == "yaml"
    assert yaml_result.data == {"foo": "bar", "items": [1]}

    unknown_result = json_yaml.detect_payload_format("plain text value")
    assert unknown_result.format == "unknown"
    assert unknown_result.data is None


def test_diff_keys_reports_changes():
    left = {"a": 1, "b": {"nested": True}, "c": 3}
    right = {"b": {"nested": False}, "c": 3, "d": 4}
    diff = json_yaml.diff_keys(left, right)
    assert diff.added == {"d"}
    assert diff.removed == {"a"}
    assert diff.common == {"c"}
    assert diff.changed == {"b"}
    assert diff.has_changes()


def test_summarize_diff_nested_structures():
    left = {"name": "DevToys", "stats": {"stars": 5}, "items": [1, 2, 3]}
    right = {"name": "DevToys", "stats": {"stars": 6}, "items": [1, 4], "active": True}
    summary = json_yaml.summarize_diff(left, right)

    assert summary.changed["$.stats.stars"] == (5, 6)
    assert summary.unchanged["$.name"] == "DevToys"
    assert summary.unchanged["$.items[0]"] == 1
    assert summary.changed["$.items[1]"] == (2, 4)
    assert summary.removed["$.items[2]"] == 3
    assert summary.added["$.active"] is True
    assert summary.has_changes()
