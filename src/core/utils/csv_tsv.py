"""CSV and TSV utilities."""

from __future__ import annotations

import csv
import json
from dataclasses import dataclass, replace
from io import StringIO
from typing import Any

__all__ = [
    "DialectSummary",
    "ParseResult",
    "sniff_dialect",
    "parse_table",
    "convert_delimiter",
    "normalize_quoting",
    "csv_to_tsv",
    "tsv_to_csv",
    "to_json_rows",
    "to_ndjson",
    "table_stats",
]


@dataclass(slots=True)
class DialectSummary:
    """Light-weight representation of :mod:`csv` dialect settings."""

    delimiter: str
    quotechar: str
    doublequote: bool
    skipinitialspace: bool
    lineterminator: str
    quoting: int
    escapechar: str | None


@dataclass(slots=True)
class ParseResult:
    """Result of parsing a CSV/TSV payload."""

    headers: list[str] | None
    rows: list[list[str]]
    delimiter: str
    dialect: DialectSummary


_DEFAULT_DIALECT = DialectSummary(
    delimiter=",",
    quotechar="\"",
    doublequote=True,
    skipinitialspace=False,
    lineterminator="\n",
    quoting=csv.QUOTE_MINIMAL,
    escapechar=None,
)

_QUOTE_STYLES = {
    "minimal": csv.QUOTE_MINIMAL,
    "all": csv.QUOTE_ALL,
    "nonnumeric": csv.QUOTE_NONNUMERIC,
    "none": csv.QUOTE_NONE,
}


def _dialect_from_csv(dialect: csv.Dialect | type[csv.Dialect]) -> DialectSummary:
    return DialectSummary(
        delimiter=dialect.delimiter,
        quotechar=dialect.quotechar,
        doublequote=dialect.doublequote,
        skipinitialspace=dialect.skipinitialspace,
        lineterminator=dialect.lineterminator,
        quoting=dialect.quoting,
        escapechar=dialect.escapechar,
    )


def _detect_dialect(value: str) -> DialectSummary:
    sniffer = csv.Sniffer()
    try:
        detected = sniffer.sniff(value)
    except csv.Error:
        return _DEFAULT_DIALECT
    return _dialect_from_csv(detected)


def sniff_dialect(value: str) -> DialectSummary:
    """Detect CSV dialect parameters, falling back to Excel defaults."""

    return _detect_dialect(value)


def _dialect_kwargs(dialect: DialectSummary) -> dict[str, Any]:
    kwargs: dict[str, Any] = {
        "delimiter": dialect.delimiter,
        "quotechar": dialect.quotechar,
        "doublequote": dialect.doublequote,
        "skipinitialspace": dialect.skipinitialspace,
        "quoting": dialect.quoting,
        "lineterminator": dialect.lineterminator,
    }
    if dialect.escapechar is not None:
        kwargs["escapechar"] = dialect.escapechar
    return kwargs


def parse_table(
    value: str,
    *,
    delimiter: str | None = None,
    has_header: bool | None = None,
) -> ParseResult:
    """Parse ``value`` into rows and optional headers."""

    dialect = _detect_dialect(value)
    if delimiter is not None and delimiter != dialect.delimiter:
        dialect = replace(dialect, delimiter=delimiter)

    reader = csv.reader(StringIO(value), **_dialect_kwargs(dialect))
    rows = list(reader)

    detected_header = False
    if has_header is None and value.strip():
        try:
            detected_header = csv.Sniffer().has_header(value)
        except csv.Error:
            detected_header = False
    elif has_header:
        detected_header = True

    headers: list[str] | None = None
    data_rows = rows
    if detected_header and rows:
        headers = rows[0]
        data_rows = rows[1:]

    return ParseResult(headers=headers, rows=data_rows, delimiter=dialect.delimiter, dialect=dialect)


def _resolve_quoting(style: str | int | None, *, default: int) -> int:
    if style is None:
        return default
    if isinstance(style, int):
        return style
    try:
        return _QUOTE_STYLES[style.lower()]
    except KeyError as exc:
        raise ValueError(f"Unsupported quote style: {style!r}") from exc


def _write_rows(
    result: ParseResult,
    *,
    target_delimiter: str,
    quoting: int | None = None,
    quotechar: str | None = None,
    escapechar: str | None = None,
    lineterminator: str | None = None,
) -> str:
    output = StringIO()
    writer_kwargs = {
        "delimiter": target_delimiter,
        "quoting": _resolve_quoting(quoting, default=result.dialect.quoting),
        "quotechar": quotechar or result.dialect.quotechar,
        "doublequote": result.dialect.doublequote,
        "skipinitialspace": result.dialect.skipinitialspace,
        "lineterminator": lineterminator or "\n",
    }
    escape = escapechar if escapechar is not None else result.dialect.escapechar
    if escape is not None:
        writer_kwargs["escapechar"] = escape
    writer = csv.writer(output, **writer_kwargs)
    if result.headers is not None:
        writer.writerow(result.headers)
    writer.writerows(result.rows)
    return output.getvalue().rstrip("\n")


def convert_delimiter(
    value: str,
    *,
    source: str | None = None,
    target: str = ",",
    has_header: bool | None = None,
    quote_style: str | int | None = None,
    quotechar: str | None = None,
    escapechar: str | None = None,
    lineterminator: str | None = None,
) -> str:
    """Convert ``value`` from ``source`` delimiter to ``target``."""

    result = parse_table(value, delimiter=source, has_header=has_header)
    return _write_rows(
        result,
        target_delimiter=target,
        quoting=quote_style,
        quotechar=quotechar,
        escapechar=escapechar,
        lineterminator=lineterminator,
    )


def normalize_quoting(
    value: str,
    *,
    delimiter: str | None = None,
    quote_style: str | int | None = "minimal",
    quotechar: str | None = "\"",
    escapechar: str | None = None,
    lineterminator: str | None = None,
    has_header: bool | None = None,
) -> str:
    """Re-write CSV/TSV data with normalized quoting rules."""

    result = parse_table(value, delimiter=delimiter, has_header=has_header)
    return _write_rows(
        result,
        target_delimiter=result.delimiter,
        quoting=quote_style,
        quotechar=quotechar,
        escapechar=escapechar,
        lineterminator=lineterminator,
    )


def csv_to_tsv(value: str, *, quote_style: str | int | None = None) -> str:
    """Convert a CSV payload into TSV."""

    return convert_delimiter(value, target="\t", quote_style=quote_style)


def tsv_to_csv(value: str, *, quote_style: str | int | None = None) -> str:
    """Convert a TSV payload into CSV."""

    return convert_delimiter(value, source="\t", target=",", quote_style=quote_style)


def _ensure_headers(
    result: ParseResult,
    headers: list[str] | None,
) -> list[str]:
    if headers is not None:
        return headers
    if result.headers is not None:
        return result.headers
    width = max((len(row) for row in result.rows), default=0)
    return [f"column_{index}" for index in range(1, width + 1)]


def to_json_rows(
    value: str,
    *,
    delimiter: str | None = None,
    headers: list[str] | None = None,
    has_header: bool | None = None,
) -> list[dict[str, Any]]:
    """Return a list of dictionaries representing rows."""

    result = parse_table(value, delimiter=delimiter, has_header=has_header)
    header_row = _ensure_headers(result, headers)
    width = len(header_row)
    rows: list[dict[str, Any]] = []
    for row in result.rows:
        padded = row + [""] * (width - len(row))
        rows.append({header_row[index]: padded[index] for index in range(width)})
    return rows


def to_ndjson(
    value: str,
    *,
    delimiter: str | None = None,
    headers: list[str] | None = None,
    has_header: bool | None = None,
) -> str:
    """Convert CSV/TSV data into newline delimited JSON (NDJSON)."""

    rows = to_json_rows(value, delimiter=delimiter, headers=headers, has_header=has_header)
    return "\n".join(json.dumps(row, ensure_ascii=False) for row in rows)


def table_stats(value: str, *, delimiter: str | None = None, has_header: bool | None = None) -> dict[str, Any]:
    """Return basic statistics for a CSV/TSV input."""

    result = parse_table(value, delimiter=delimiter, has_header=has_header)
    row_lengths = [len(row) for row in result.rows]
    if result.headers is not None:
        row_lengths.append(len(result.headers))
    column_max = max(row_lengths, default=0)
    column_min = min(row_lengths, default=0)
    row_count = len(result.rows) + (1 if result.headers is not None else 0)
    return {
        "rows": row_count,
        "columns": column_max,
        "columns_min": column_min,
        "has_header": result.headers is not None,
        "headers": result.headers,
        "delimiter": result.delimiter,
    }
