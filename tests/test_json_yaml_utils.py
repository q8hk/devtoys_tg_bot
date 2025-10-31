import json

import pytest

from src.core.utils import json_yaml


def test_json_yaml_roundtrip():
    data = {"name": "DevToys", "features": ["convert", "validate"]}
    json_text = json_yaml.to_json(data, pretty=True)
    yaml_text = json_yaml.convert_json_to_yaml(json_text)
    assert "name: DevToys" in yaml_text
    converted_back = json_yaml.convert_yaml_to_json(yaml_text)
    assert json.loads(converted_back) == json.loads(json_text)


def test_parse_errors():
    with pytest.raises(json_yaml.JsonValidationError):
        json_yaml.parse_json("not json")
    with pytest.raises(json_yaml.YamlValidationError):
        json_yaml.parse_yaml("\t::broken")


def test_diff_keys():
    left = {"a": 1, "b": 2}
    right = {"b": 2, "c": 3}
    diff = json_yaml.diff_keys(left, right)
    assert diff.added == {"c"}
    assert diff.removed == {"a"}
    assert diff.common == {"b"}


def test_pretty_and_minify_are_inverse():
    raw = '{"foo": [1, 2, 3]}'
    formatted = json_yaml.pretty_json(raw)
    assert "\n" in formatted
    assert json.loads(json_yaml.minify_json(formatted)) == json.loads(raw)
