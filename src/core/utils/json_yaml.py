"""Shared helpers for dealing with JSON and YAML payloads."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

import yaml

__all__ = [
    "JsonValidationError",
    "YamlValidationError",
    "parse_json",
    "parse_yaml",
    "to_json",
    "to_yaml",
    "pretty_json",
    "minify_json",
    "convert_json_to_yaml",
    "convert_yaml_to_json",
    "DiffResult",
    "diff_keys",
]


class JsonValidationError(ValueError):
    """Raised when JSON parsing fails."""


class YamlValidationError(ValueError):
    """Raised when YAML parsing fails."""


def parse_json(value: str) -> Any:
    """Parse ``value`` as JSON and raise :class:`JsonValidationError` on failure."""

    try:
        return json.loads(value)
    except json.JSONDecodeError as exc:  # pragma: no cover - defensive
        raise JsonValidationError(str(exc)) from exc


def parse_yaml(value: str) -> Any:
    """Parse ``value`` as YAML using :func:`yaml.safe_load`."""

    try:
        return yaml.safe_load(value)
    except yaml.YAMLError as exc:  # pragma: no cover - defensive
        raise YamlValidationError(str(exc)) from exc


def to_json(value: Any, *, pretty: bool = False) -> str:
    """Serialize *value* as JSON."""

    if pretty:
        return json.dumps(value, indent=2, ensure_ascii=False, sort_keys=True)
    return json.dumps(value, separators=(",", ":"), ensure_ascii=False, sort_keys=True)


def to_yaml(value: Any) -> str:
    """Serialize *value* as YAML using a deterministic configuration."""

    return yaml.safe_dump(value, sort_keys=True, allow_unicode=True).strip()


def pretty_json(value: str) -> str:
    """Return a formatted JSON string."""

    return to_json(parse_json(value), pretty=True)


def minify_json(value: str) -> str:
    """Return a compact JSON string."""

    return to_json(parse_json(value), pretty=False)


def convert_json_to_yaml(value: str) -> str:
    """Convert JSON text to YAML text."""

    return to_yaml(parse_json(value))


def convert_yaml_to_json(value: str, *, pretty: bool = True) -> str:
    """Convert YAML text to JSON text."""

    return to_json(parse_yaml(value), pretty=pretty)


@dataclass(slots=True)
class DiffResult:
    added: set[str]
    removed: set[str]
    common: set[str]


def diff_keys(left: dict[str, Any], right: dict[str, Any]) -> DiffResult:
    """Return a summary of the key differences between ``left`` and ``right``."""

    left_keys = set(left)
    right_keys = set(right)
    return DiffResult(
        added=right_keys - left_keys,
        removed=left_keys - right_keys,
        common=left_keys & right_keys,
    )
