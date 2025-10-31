"""Regex testing handlers."""

from __future__ import annotations

from dataclasses import dataclass
from html import escape

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from core.utils.regex_ import RegexResult, parse_flag_tokens, run_regex

router = Router(name="regex-tools")

USAGE_MESSAGE = (
    "<b>Regex tester</b>\n"
    "Use the command in the following format:\n"
    "<code>/regex &lt;pattern&gt;\n"
    "flags: imsx (optional)\n"
    "limit: 5 (optional)\n"
    "timeout: 120 (optional, milliseconds)\n"
    "text:\n"
    "Your sample text here</code>"
)


@dataclass(slots=True)
class RegexCommand:
    pattern: str
    text: str
    flags: int
    limit: int
    timeout: float


def _parse_argument_block(arguments: str) -> RegexCommand:
    if not arguments.strip():
        raise ValueError("Provide a regex pattern and sample text.")

    lines = arguments.splitlines()
    pattern_line = lines[0].strip()
    if pattern_line.lower().startswith("pattern:"):
        pattern = pattern_line.split(":", 1)[1].strip()
    else:
        pattern = pattern_line
    if not pattern:
        raise ValueError("Regex pattern cannot be empty.")

    flags_tokens = ""
    limit = 20
    timeout = 100.0
    text_lines: list[str] = []
    in_text_block = False

    for raw_line in lines[1:]:
        stripped = raw_line.strip()
        lowered = stripped.lower()

        if in_text_block:
            text_lines.append(raw_line)
            continue

        if not stripped:
            continue

        if lowered.startswith("flags:"):
            flags_tokens = raw_line.split(":", 1)[1].strip()
            continue
        if lowered.startswith("limit:"):
            limit_value = raw_line.split(":", 1)[1].strip()
            if limit_value:
                try:
                    limit = int(limit_value)
                except ValueError as exc:
                    raise ValueError("Limit must be an integer.") from exc
            continue
        if lowered.startswith("timeout:"):
            timeout_value = raw_line.split(":", 1)[1].strip()
            if timeout_value:
                try:
                    timeout = float(timeout_value)
                except ValueError as exc:
                    raise ValueError("Timeout must be a number in milliseconds.") from exc
            continue
        if lowered == "text:":
            in_text_block = True
            continue

        in_text_block = True
        text_lines.append(raw_line)

    if not text_lines:
        raise ValueError("Provide sample text after the pattern.")

    try:
        flags_value = parse_flag_tokens(flags_tokens) if flags_tokens else 0
    except ValueError as exc:
        raise ValueError(f"Unsupported flags: {exc}") from exc

    return RegexCommand(
        pattern=pattern,
        text="\n".join(text_lines),
        flags=flags_value,
        limit=limit,
        timeout=timeout,
    )


def _format_regex_result(result: RegexResult) -> str:
    if result.timed_out and not result.matches:
        header = "!  <b>Regex execution timed out before any matches were found.</b>"
    elif result.timed_out:
        header = "!  <b>Regex execution timed out. Partial matches:</b>"
    elif not result.matches:
        header = "info <b>No matches found.</b>"
    else:
        header = f"check <b>Found {len(result.matches)} match(es).</b>"

    lines = [header]
    indent = "&nbsp;&nbsp;"
    for index, match in enumerate(result.matches, start=1):
        lines.append(
            f"{index}. <code>{escape(match.value)}</code> "
            f"[{match.span[0]}:{match.span[1]}]"
        )
        if match.groups:
            for group_index, value in enumerate(match.groups, start=1):
                display = escape(value) if value is not None else "empty"
                lines.append(f"{indent}Group {group_index}: <code>{display}</code>")
        if match.named_groups:
            for name, value in match.named_groups.items():
                display = escape(value) if value is not None else "empty"
                lines.append(f"{indent}{escape(name)}: <code>{display}</code>")

    return "\n".join(lines)


@router.message(Command("regex"))
async def handle_regex_command(message: Message) -> None:
    content = message.text or message.caption or ""
    if not content:
        await message.reply(USAGE_MESSAGE)
        return

    parts = content.split(maxsplit=1)
    arguments = parts[1] if len(parts) > 1 else ""
    if not arguments:
        await message.reply(USAGE_MESSAGE)
        return

    try:
        command = _parse_argument_block(arguments)
    except ValueError as exc:
        await message.reply(f"!  {escape(str(exc))}\n\n{USAGE_MESSAGE}")
        return

    try:
        result = run_regex(
            command.pattern,
            command.text,
            flags=command.flags,
            limit=command.limit,
            timeout=command.timeout,
        )
    except ValueError as exc:
        await message.reply(f"!  Regex error: {escape(str(exc))}")
        return

    await message.reply(_format_regex_result(result))

