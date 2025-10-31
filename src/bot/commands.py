"""Bot command catalogue and helpers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from aiogram import Bot
from aiogram.types import (
    BotCommand,
    BotCommandScopeAllGroupChats,
    BotCommandScopeAllPrivateChats,
    BotCommandScopeDefault,
)


@dataclass(frozen=True, slots=True)
class CommandSpec:
    """Metadata describing a Telegram command exposed by the bot."""

    name: str
    description: str
    section: str | None = None
    show_in_menu: bool = True
    show_in_guide: bool = False


COMMAND_SPECS: tuple[CommandSpec, ...] = (
    # Core navigation commands.
    CommandSpec("start", "Open the main menu"),
    CommandSpec("help", "How to use the bot"),
    CommandSpec("tools", "Browse tool categories"),
    CommandSpec("recent", "Show your latest tasks"),
    CommandSpec("settings", "Adjust personal preferences"),
    CommandSpec("cancel", "Cancel the current action"),
    CommandSpec("privacy", "View privacy information"),
    CommandSpec("about", "Learn about the project"),
    # Text utilities.
    CommandSpec("text_tools", "List available text utilities", section="text_tools", show_in_guide=True),
    CommandSpec("text_trim", "Trim leading and trailing whitespace", section="text_tools", show_in_guide=True),
    CommandSpec("text_ltrim", "Remove leading whitespace", section="text_tools"),
    CommandSpec("text_rtrim", "Remove trailing whitespace", section="text_tools"),
    CommandSpec("text_normalize", "Normalize whitespace to single spaces", section="text_tools", show_in_guide=True),
    CommandSpec("text_upper", "Convert text to upper case", section="text_tools"),
    CommandSpec("text_lower", "Convert text to lower case", section="text_tools"),
    CommandSpec("text_title", "Convert text to title case", section="text_tools"),
    CommandSpec("text_sentence", "Convert text to sentence case", section="text_tools"),
    CommandSpec("text_slugify", "Generate a URL friendly slug", section="text_tools", show_in_guide=True),
    CommandSpec("text_sort", "Sort lines alphabetically", section="text_tools"),
    CommandSpec("text_unique", "Remove duplicate lines", section="text_tools"),
    CommandSpec("text_number", "Prefix lines with numbers", section="text_tools"),
    CommandSpec("text_strip_numbers", "Remove prefixed line numbers", section="text_tools"),
    CommandSpec("lorem", "Generate deterministic lorem ipsum", section="text_tools", show_in_guide=True),
    CommandSpec("regex", "Test a regular expression", section="text_tools", show_in_guide=True),
    # Data utilities (CSV, XML, JSON, UUID/ULID).
    CommandSpec("csvstats", "Inspect CSV/TSV structure and statistics", section="data_tools", show_in_guide=True),
    CommandSpec("tsvstats", "Inspect TSV/CSV structure and statistics", section="data_tools"),
    CommandSpec("csv2tsv", "Convert CSV data to TSV", section="data_tools", show_in_guide=True),
    CommandSpec("tsv2csv", "Convert TSV data to CSV", section="data_tools"),
    CommandSpec("csvtojson", "Convert CSV rows to JSON", section="data_tools", show_in_guide=True),
    CommandSpec("tsvtojson", "Convert TSV rows to JSON", section="data_tools"),
    CommandSpec("csvtondjson", "Convert CSV rows to NDJSON", section="data_tools"),
    CommandSpec("tsvtondjson", "Convert TSV rows to NDJSON", section="data_tools"),
    CommandSpec("reformatcsv", "Normalise CSV quoting and delimiter", section="data_tools"),
    CommandSpec("xml_pretty", "Pretty-print XML input", section="data_tools", show_in_guide=True),
    CommandSpec("xml_minify", "Minify XML input", section="data_tools"),
    CommandSpec("xml_to_json", "Convert XML to JSON", section="data_tools", show_in_guide=True),
    CommandSpec("json_to_xml", "Convert JSON to XML", section="data_tools"),
    CommandSpec("xml_xpath", "Evaluate an XPath expression", section="data_tools"),
    CommandSpec("uuid", "Generate UUIDs (v1/v4/v7)", section="data_tools", show_in_guide=True),
    CommandSpec("uuid_inspect", "Inspect and validate a UUID", section="data_tools"),
    CommandSpec("ulid", "Generate ULIDs", section="data_tools"),
    CommandSpec("ulid_inspect", "Inspect and validate a ULID", section="data_tools"),
    # Security utilities.
    CommandSpec("hash_algorithms", "List supported hash algorithms", section="security_tools"),
    CommandSpec("hash", "Calculate a hash digest", section="security_tools", show_in_guide=True),
    CommandSpec("hmac", "Generate an HMAC digest", section="security_tools", show_in_guide=True),
    CommandSpec("jwt", "Decode and inspect a JWT", section="security_tools", show_in_guide=True),
    CommandSpec("code_password", "Generate a password with options", section="security_tools"),
    CommandSpec("code_token", "Generate a random token", section="security_tools"),
    # Media utilities (images and QR codes).
    CommandSpec("image_info", "Inspect image metadata", section="media_tools", show_in_guide=True),
    CommandSpec("image_convert", "Convert an image to another format", section="media_tools", show_in_guide=True),
    CommandSpec("image_resize", "Resize an image by size or percent", section="media_tools", show_in_guide=True),
    CommandSpec("image_compress", "Compress an image with a quality factor", section="media_tools"),
    CommandSpec("image_base64", "Encode an image as Base64", section="media_tools"),
    CommandSpec("image_from_base64", "Create an image from Base64", section="media_tools"),
    CommandSpec("qr", "Generate a QR code for text or URLs", section="media_tools", show_in_guide=True),
    CommandSpec("wifi_qr", "Build a Wi-Fi configuration QR code", section="media_tools"),
    # Web utilities (URLs, HTML, code formatting).
    CommandSpec("urlencode", "Percent-encode text", section="web_tools", show_in_guide=True),
    CommandSpec("urldecode", "Decode percent-encoded text", section="web_tools"),
    CommandSpec("urlparse", "Inspect URL query parameters", section="web_tools", show_in_guide=True),
    CommandSpec("url", "Auto-detect and process URL input", section="web_tools"),
    CommandSpec("html_minify", "Minify HTML markup", section="web_tools"),
    CommandSpec("html_prettify", "Prettify HTML markup", section="web_tools"),
    CommandSpec("html_encode", "HTML-encode text", section="web_tools"),
    CommandSpec("html_decode", "Decode HTML entities", section="web_tools"),
    CommandSpec("html_strip", "Strip HTML tags to plain text", section="web_tools"),
    CommandSpec("code_json_pretty", "Pretty-print JSON", section="web_tools"),
    CommandSpec("code_json_minify", "Minify JSON", section="web_tools"),
    CommandSpec("code_css_pretty", "Pretty-print CSS", section="web_tools"),
    CommandSpec("code_css_minify", "Minify CSS", section="web_tools"),
    CommandSpec("code_js_pretty", "Pretty-print JavaScript", section="web_tools"),
    CommandSpec("code_js_minify", "Minify JavaScript", section="web_tools"),
    CommandSpec("code_diff", "Create a unified diff", section="web_tools", show_in_guide=True),
    # Time and date utilities.
    CommandSpec("epoch_to_datetime", "Convert Unix epoch to date/time", section="time_tools", show_in_guide=True),
    CommandSpec("datetime_to_epoch", "Convert date/time to Unix epoch", section="time_tools"),
    CommandSpec("convert_time", "Convert between time zones", section="time_tools", show_in_guide=True),
    CommandSpec("time_delta", "Add or subtract durations", section="time_tools", show_in_guide=True),
    # Colour utilities.
    CommandSpec("color", "Convert colours and preview palettes", section="color_tools", show_in_guide=True),
)


def _build_bot_commands(specs: Sequence[CommandSpec]) -> list[BotCommand]:
    return [BotCommand(command=spec.name, description=spec.description) for spec in specs]


def default_scope_command_specs() -> tuple[CommandSpec, ...]:
    """Commands applied to the default scope (all chats)."""

    return tuple(spec for spec in COMMAND_SPECS if spec.section is None and spec.show_in_menu)


def private_scope_command_specs() -> tuple[CommandSpec, ...]:
    """Commands shown in private chats."""

    return tuple(spec for spec in COMMAND_SPECS if spec.show_in_menu)


def group_scope_command_specs() -> tuple[CommandSpec, ...]:
    """Commands advertised in group chats."""

    return default_scope_command_specs()


def section_commands(section: str, *, for_guide: bool = False) -> tuple[CommandSpec, ...]:
    """Return command specs mapped to a home section."""

    commands = tuple(spec for spec in COMMAND_SPECS if spec.section == section)
    if not for_guide:
        return commands
    return tuple(spec for spec in commands if spec.show_in_guide)


async def setup_bot_commands(bot: Bot) -> None:
    """Register bot commands for default, private, and group scopes."""

    default_commands = _build_bot_commands(default_scope_command_specs())
    private_commands = _build_bot_commands(private_scope_command_specs())
    group_commands = _build_bot_commands(group_scope_command_specs())

    await bot.set_my_commands(default_commands, scope=BotCommandScopeDefault())
    await bot.set_my_commands(private_commands, scope=BotCommandScopeAllPrivateChats())
    await bot.set_my_commands(group_commands, scope=BotCommandScopeAllGroupChats())


__all__ = [
    "CommandSpec",
    "COMMAND_SPECS",
    "default_scope_command_specs",
    "private_scope_command_specs",
    "group_scope_command_specs",
    "section_commands",
    "setup_bot_commands",
]

