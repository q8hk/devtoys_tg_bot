"""CSV and TSV utilities."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from io import StringIO
from typing import Any

__all__ = [
    "DialectSummary",
    "sniff_dialect",
    "convert_delimiter",
    "to_json_rows",
    "table_stats",
]


@dataclass(slots=True)
class DialectSummary:
    delimiter: str
    quotechar: str
    doublequote: bool
    skipinitialspace: bool


def sniff_dialect(value: str) -> DialectSummary:
    """Detect CSV dialect parameters."""

    sniffer = csv.Sniffer()
    dialect = sniffer.sniff(value)
    return DialectSummary(
        delimiter=dialect.delimiter,
        quotechar=dialect.quotechar,
        doublequote=dialect.doublequote,
        skipinitialspace=dialect.skipinitialspace,
    )


def _reader(value: str, delimiter: str) -> list[list[str]]:
    reader = csv.reader(StringIO(value), delimiter=delimiter)
    return [row for row in reader]


def convert_delimiter(value: str, *, source: str | None = None, target: str = ",") -> str:
    """Convert ``value`` from ``source`` delimiter to ``target``."""

    delimiter = source or sniff_dialect(value).delimiter
    rows = _reader(value, delimiter)
    output = StringIO()
    writer = csv.writer(output, delimiter=target)
    writer.writerows(rows)
    return output.getvalue().strip("\n")


def to_json_rows(value: str, *, delimiter: str | None = None, headers: list[str] | None = None) -> list[dict[str, Any]]:
    """Return a list of dictionaries representing rows."""

    delimiter = delimiter or sniff_dialect(value).delimiter
    reader = csv.DictReader(StringIO(value), delimiter=delimiter, fieldnames=headers)
    return [dict(row) for row in reader]


def table_stats(value: str, *, delimiter: str | None = None) -> dict[str, Any]:
    """Return basic statistics for a CSV/TSV input."""

    delimiter = delimiter or sniff_dialect(value).delimiter
    rows = _reader(value, delimiter)
    column_count = max((len(row) for row in rows), default=0)
    return {
        "rows": len(rows),
        "columns": column_count,
        "delimiter": delimiter,
    }
