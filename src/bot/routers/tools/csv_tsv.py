"""CSV and TSV handlers."""

from __future__ import annotations

import html
import json
import logging
from typing import Final

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import BufferedInputFile, Message

from core.utils.csv_tsv import (
    convert_delimiter,
    csv_to_tsv,
    table_stats,
    to_json_rows,
    to_ndjson,
    tsv_to_csv,
)

logger = logging.getLogger(__name__)

router = Router(name="tools-csv-tsv")

_MESSAGE_LIMIT: Final[int] = 3500


def _command_name(message: Message) -> str:
    if not message.text:
        return ""
    return message.text.split(maxsplit=1)[0].split("@", 1)[0].lower()


def _extract_payload(message: Message) -> str | None:
    if message.text:
        parts = message.text.split(maxsplit=1)
        if len(parts) == 2:
            return parts[1].strip()
    if message.reply_to_message and message.reply_to_message.text:
        return message.reply_to_message.text.strip()
    return None


def _format_code_block(content: str) -> str:
    return f"<pre><code>{html.escape(content)}</code></pre>"


async def _send_large_response(message: Message, content: str, filename: str) -> None:
    if len(content) <= _MESSAGE_LIMIT:
        await message.answer(_format_code_block(content))
        return
    await message.answer_document(
        BufferedInputFile(content.encode("utf-8"), filename=filename),
        caption="Result",
    )


async def _handle_error(message: Message, exc: Exception) -> None:
    logger.exception("CSV/TSV processing failed", exc_info=exc)
    await message.answer(
        "!  Unable to process the provided data. Please verify the format and try again."
    )


@router.message(Command(commands=["csvstats", "tsvstats"]))
async def handle_stats(message: Message) -> None:
    payload = _extract_payload(message)
    if not payload:
        await message.answer(
            "Send CSV/TSV data after the command or reply to a message containing the data."
        )
        return
    try:
        stats = table_stats(payload)
    except Exception as exc:  # pragma: no cover - defensive
        await _handle_error(message, exc)
        return

    delimiter = stats["delimiter"]
    delimiter_label = "TAB" if delimiter == "\t" else delimiter
    headers = stats.get("headers")
    header_line = ", ".join(headers) if headers else "(none)"
    reply = (
        "<b>Table statistics</b>\n"
        f"Rows: <code>{stats['rows']}</code>\n"
        f"Columns (max): <code>{stats['columns']}</code>\n"
        f"Columns (min): <code>{stats['columns_min']}</code>\n"
        f"Has header: <code>{'yes' if stats['has_header'] else 'no'}</code>\n"
        f"Delimiter: <code>{html.escape(delimiter_label)}</code>\n"
        f"Headers: <code>{html.escape(header_line)}</code>"
    )
    await message.answer(reply)


@router.message(Command(commands=["csv2tsv"]))
async def handle_csv_to_tsv(message: Message) -> None:
    payload = _extract_payload(message)
    if not payload:
        await message.answer("Provide CSV data after the command or reply to a CSV message.")
        return
    try:
        converted = csv_to_tsv(payload)
    except Exception as exc:  # pragma: no cover - defensive
        await _handle_error(message, exc)
        return
    await _send_large_response(message, converted, "converted.tsv")


@router.message(Command(commands=["tsv2csv"]))
async def handle_tsv_to_csv(message: Message) -> None:
    payload = _extract_payload(message)
    if not payload:
        await message.answer("Provide TSV data after the command or reply to a TSV message.")
        return
    try:
        converted = tsv_to_csv(payload)
    except Exception as exc:  # pragma: no cover - defensive
        await _handle_error(message, exc)
        return
    await _send_large_response(message, converted, "converted.csv")


@router.message(Command(commands=["csvtojson", "tsvtojson"]))
async def handle_to_json(message: Message) -> None:
    payload = _extract_payload(message)
    if not payload:
        await message.answer(
            "Send CSV/TSV data after the command or reply to a message to convert it to JSON."
        )
        return
    delimiter = "\t" if _command_name(message).startswith("/tsv") else None
    try:
        rows = to_json_rows(payload, delimiter=delimiter)
        json_text = json.dumps(rows, ensure_ascii=False, indent=2)
    except Exception as exc:  # pragma: no cover - defensive
        await _handle_error(message, exc)
        return
    await _send_large_response(message, json_text, "result.json")


@router.message(Command(commands=["csvtondjson", "tsvtondjson"]))
async def handle_to_ndjson(message: Message) -> None:
    payload = _extract_payload(message)
    if not payload:
        await message.answer(
            "Send CSV/TSV data after the command or reply to a message to convert it to NDJSON."
        )
        return
    delimiter = "\t" if _command_name(message).startswith("/tsv") else None
    try:
        ndjson = to_ndjson(payload, delimiter=delimiter)
    except Exception as exc:  # pragma: no cover - defensive
        await _handle_error(message, exc)
        return
    await _send_large_response(message, ndjson, "result.ndjson")


@router.message(Command(commands=["reformatcsv"]))
async def handle_reformat(message: Message) -> None:
    payload = _extract_payload(message)
    if not payload:
        await message.answer(
            "Send CSV data after the command or reply to a message to reapply consistent quoting."
        )
        return
    try:
        reformatted = convert_delimiter(payload, target=",", quote_style="minimal")
    except Exception as exc:  # pragma: no cover - defensive
        await _handle_error(message, exc)
        return
    await _send_large_response(message, reformatted, "reformatted.csv")

