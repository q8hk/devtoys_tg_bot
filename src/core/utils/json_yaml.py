"""Shared helpers for dealing with JSON and YAML payloads."""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Literal

import yaml

__all__ = [
    "JsonValidationError",
    "YamlValidationError",
    "ValidationResult",
    "AutoDetectResult",
    "DiffResult",
    "DiffSummary",
    "parse_json",
    "parse_yaml",
    "to_json",
    "to_yaml",
    "pretty_json",
    "minify_json",
    "convert_json_to_yaml",
    "convert_yaml_to_json",
    "validate_json",
    "validate_yaml",
    "detect_payload_format",
    "diff_keys",
    "summarize_diff",
]


class JsonValidationError(ValueError):
    """Raised when JSON parsing fails."""


class YamlValidationError(ValueError):
    """Raised when YAML parsing fails."""


@dataclass(slots=True)
class ValidationResult:
    """Represents the outcome of a JSON/YAML validation."""

    is_valid: bool
    error: str | None = None
    data: Any | None = None


@dataclass(slots=True)
class AutoDetectResult:
    """Result of attempting to auto-detect JSON vs YAML content."""

    format: Literal["json", "yaml", "unknown"]
    data: Any | None
    error: str | None = None

    @property
    def is_detected(self) -> bool:
        """Whether a supported format was successfully detected."""

        return self.format in {"json", "yaml"}


@dataclass(slots=True)
class DiffResult:
    """Summary of top-level key differences between two mappings."""

    added: set[str]
    removed: set[str]
    common: set[str]
    changed: set[str]

    def has_changes(self) -> bool:
        """Return ``True`` when any difference exists."""

        return bool(self.added or self.removed or self.changed)


@dataclass(slots=True)
class DiffSummary:
    """Detailed diff information including nested paths."""

    added: dict[str, Any]
    removed: dict[str, Any]
    changed: dict[str, tuple[Any, Any]]
    unchanged: dict[str, Any]

    def has_changes(self) -> bool:
        """Return ``True`` if any leaf-level difference exists."""

        return bool(self.added or self.removed or self.changed)


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

    return yaml.safe_dump(value, sort_keys=True, allow_unicode=True).rstrip("\n")


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


def validate_json(value: str) -> ValidationResult:
    """Validate JSON text returning the parsed payload when successful."""

    try:
        data = parse_json(value)
    except JsonValidationError as exc:
        return ValidationResult(is_valid=False, error=str(exc), data=None)
    return ValidationResult(is_valid=True, error=None, data=data)


def validate_yaml(value: str) -> ValidationResult:
    """Validate YAML text returning the parsed payload when successful."""

    try:
        data = parse_yaml(value)
    except YamlValidationError as exc:
        return ValidationResult(is_valid=False, error=str(exc), data=None)
    return ValidationResult(is_valid=True, error=None, data=data)


def detect_payload_format(value: str) -> AutoDetectResult:
    """Best-effort detection between JSON and YAML strings."""

    json_error: str | None = None
    try:
        data = parse_json(value)
    except JsonValidationError as exc:
        json_error = str(exc)
    else:
        return AutoDetectResult(format="json", data=data, error=None)

    try:
        data = parse_yaml(value)
    except YamlValidationError as exc:
        return AutoDetectResult(format="unknown", data=None, error=str(exc))

    if _looks_like_plain_text_yaml(value, data):
        return AutoDetectResult(format="unknown", data=None, error=json_error)

    return AutoDetectResult(format="yaml", data=data, error=None)


def diff_keys(left: Mapping[str, Any], right: Mapping[str, Any]) -> DiffResult:
    """Return a summary of the top-level key differences between ``left`` and ``right``."""

    left_keys = set(left)
    right_keys = set(right)
    common_keys = left_keys & right_keys
    changed = {key for key in common_keys if left[key] != right[key]}
    return DiffResult(
        added=right_keys - left_keys,
        removed=left_keys - right_keys,
        common=common_keys - changed,
        changed=changed,
    )


def summarize_diff(left: Any, right: Any) -> DiffSummary:
    """Produce a nested diff summary between two Python data structures."""

    summary = DiffSummary(added={}, removed={}, changed={}, unchanged={})
    _collect_differences(left, right, [], summary)
    return summary


def _collect_differences(left: Any, right: Any, path: list[str], summary: DiffSummary) -> None:
    if isinstance(left, Mapping) and isinstance(right, Mapping):
        left_keys = set(left)
        right_keys = set(right)
        for key in left_keys - right_keys:
            summary.removed[_format_path(path + [str(key)])] = left[key]
        for key in right_keys - left_keys:
            summary.added[_format_path(path + [str(key)])] = right[key]
        for key in left_keys & right_keys:
            _collect_differences(left[key], right[key], path + [str(key)], summary)
        return

    if _is_sequence(left) and _is_sequence(right):
        min_len = min(len(left), len(right))
        for index in range(min_len):
            _collect_differences(left[index], right[index], path + [f"[{index}]"], summary)
        for index in range(min_len, len(left)):
            summary.removed[_format_path(path + [f"[{index}]"])] = left[index]
        for index in range(min_len, len(right)):
            summary.added[_format_path(path + [f"[{index}]"])] = right[index]
        return

    path_key = _format_path(path)
    if left == right:
        summary.unchanged[path_key] = left
    else:
        summary.changed[path_key] = (left, right)


def _format_path(parts: list[str]) -> str:
    if not parts:
        return "$"
    result = "$"
    for part in parts:
        if part.startswith("["):
            result += part
        else:
            result += f".{part}"
    return result


def _is_sequence(value: Any) -> bool:
    return isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray))


def _looks_like_plain_text_yaml(source: str, parsed: Any) -> bool:
    """Heuristic to avoid treating arbitrary text as YAML."""

    stripped = source.strip()
    if not stripped:
        return True
    if isinstance(parsed, str):
        if stripped == parsed and not stripped.startswith(("'", '"')):
            if ":" in stripped or "\n" in stripped:
                return False
            return True
    if parsed is None and stripped.lower() not in {"null", "~"}:
        return True
    return False
