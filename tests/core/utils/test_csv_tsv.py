"""Tests for CSV/TSV utilities."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.core.utils.csv_tsv import (
    csv_to_tsv,
    normalize_quoting,
    parse_table,
    sniff_dialect,
    table_stats,
    to_json_rows,
    to_ndjson,
    tsv_to_csv,
    convert_delimiter,
)


def test_sniff_dialect_detects_csv_delimiter() -> None:
    summary = sniff_dialect("name,age\nAlice,30\n")
    assert summary.delimiter == ","
    assert summary.quotechar == "\""


def test_sniff_dialect_detects_tsv_delimiter() -> None:
    summary = sniff_dialect("name\tage\nAlice\t30\n")
    assert summary.delimiter == "\t"


def test_parse_table_detects_headers() -> None:
    result = parse_table("name,age\nAlice,30\nBob,25\n")
    assert result.headers == ["name", "age"]
    assert result.rows == [["Alice", "30"], ["Bob", "25"]]


def test_convert_delimiter_to_tab() -> None:
    converted = convert_delimiter("name,age\nAlice,30\n", target="\t")
    assert converted == "name\tage\nAlice\t30"


def test_normalize_quoting_to_all() -> None:
    normalized = normalize_quoting("name,age\nAlice,30\nBob,25\n", quote_style="all")
    assert normalized == '"name","age"\n"Alice","30"\n"Bob","25"'


def test_to_json_rows_without_headers_generates_defaults() -> None:
    rows = to_json_rows("1,2,3\n4,5\n", has_header=False)
    assert rows == [
        {"column_1": "1", "column_2": "2", "column_3": "3"},
        {"column_1": "4", "column_2": "5", "column_3": ""},
    ]


def test_to_ndjson_serializes_rows() -> None:
    ndjson = to_ndjson("name,age\nAlice,30\nBob,25\n")
    lines = ndjson.splitlines()
    assert lines == [
        json.dumps({"name": "Alice", "age": "30"}),
        json.dumps({"name": "Bob", "age": "25"}),
    ]


def test_table_stats_reports_dimensions_and_headers() -> None:
    stats = table_stats("name,age\nAlice,30\nBob,25\n")
    assert stats == {
        "rows": 3,
        "columns": 2,
        "columns_min": 2,
        "has_header": True,
        "headers": ["name", "age"],
        "delimiter": ",",
    }


def test_csv_tsv_roundtrip() -> None:
    csv_text = "name,age\nAlice,30\n"
    tsv_text = csv_to_tsv(csv_text)
    assert tsv_text == "name\tage\nAlice\t30"
    assert tsv_to_csv(tsv_text) == "name,age\nAlice,30"

