"""JSON and YAML utility helpers exposed to the bot layer."""

from __future__ import annotations

from typing import Literal

from src.core.utils.json_yaml import (
    AutoDetectResult,
    DiffSummary,
    ValidationResult,
    detect_payload_format,
    summarize_diff,
    to_json,
    to_yaml,
    validate_json,
    validate_yaml,
)

__all__ = [
    "detect_payload",
    "pretty_format",
    "minify_payload",
    "convert_payload",
    "validate_payload",
    "diff_payloads",
]


def detect_payload(value: str) -> AutoDetectResult:
    """Auto-detect whether ``value`` is JSON or YAML."""

    return detect_payload_format(value)


def pretty_format(value: str) -> tuple[str, str]:
    """Return the detected format and a formatted string representation."""

    detection = detect_payload_format(value)
    if not detection.is_detected:
        raise ValueError("Unsupported content format")

    if detection.format == "json":
        return detection.format, to_json(detection.data, pretty=True)
    return detection.format, to_yaml(detection.data)


def minify_payload(value: str) -> str:
    """Return a minified JSON representation of ``value``."""

    detection = detect_payload_format(value)
    if not detection.is_detected:
        raise ValueError("Unsupported content format")
    return to_json(detection.data, pretty=False)


def convert_payload(value: str, target: Literal["json", "yaml"], *, pretty_json: bool = True) -> str:
    """Convert ``value`` to the requested ``target`` format."""

    detection = detect_payload_format(value)
    if not detection.is_detected:
        raise ValueError("Unsupported content format")
    if target == "json":
        return to_json(detection.data, pretty=pretty_json)
    if target == "yaml":
        return to_yaml(detection.data)
    raise ValueError(f"Unsupported target format: {target}")


def validate_payload(value: str) -> ValidationResult:
    """Validate JSON/YAML text returning structured feedback."""

    detection = detect_payload_format(value)
    if detection.is_detected:
        return ValidationResult(is_valid=True, error=None, data=detection.data)

    json_result = validate_json(value)
    if json_result.is_valid:
        return json_result

    yaml_result = validate_yaml(value)
    if yaml_result.is_valid:
        return yaml_result

    error = detection.error or json_result.error or yaml_result.error
    return ValidationResult(is_valid=False, error=error, data=None)


def diff_payloads(left: str, right: str) -> tuple[DiffSummary, AutoDetectResult, AutoDetectResult]:
    """Return a diff summary between two payloads and their detection metadata."""

    left_detection = detect_payload_format(left)
    right_detection = detect_payload_format(right)

    if not left_detection.is_detected or not right_detection.is_detected:
        raise ValueError("Both payloads must be valid JSON or YAML")

    summary = summarize_diff(left_detection.data, right_detection.data)
    return summary, left_detection, right_detection
