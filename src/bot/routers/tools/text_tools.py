"""Text utility handlers."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from aiogram import Router
from aiogram.filters import Command
from aiogram.filters.command import CommandObject
from aiogram.types import Message
from core.utils import text as text_utils

__all__ = ["router"]


@dataclass(slots=True)
class _SimpleTransform:
    command: str
    description: str
    transform: Callable[[str], str]


router = Router(name="text_tools")


_TRANSFORMS: tuple[_SimpleTransform, ...] = (
    _SimpleTransform(
        "text_trim",
        "Trim leading and trailing whitespace.",
        text_utils.trim,
    ),
    _SimpleTransform(
        "text_ltrim",
        "Remove leading whitespace only.",
        text_utils.ltrim,
    ),
    _SimpleTransform(
        "text_rtrim",
        "Remove trailing whitespace only.",
        text_utils.rtrim,
    ),
    _SimpleTransform(
        "text_normalize",
        "Normalize whitespace to single spaces.",
        text_utils.normalize_whitespace,
    ),
    _SimpleTransform(
        "text_upper",
        "Convert text to upper case.",
        text_utils.to_upper,
    ),
    _SimpleTransform(
        "text_lower",
        "Convert text to lower case.",
        text_utils.to_lower,
    ),
    _SimpleTransform(
        "text_title",
        "Convert text to title case.",
        text_utils.to_title,
    ),
    _SimpleTransform(
        "text_sentence",
        "Convert text to sentence case.",
        text_utils.to_sentence,
    ),
    _SimpleTransform(
        "text_slugify",
        "Create a URL friendly slug.",
        text_utils.slugify,
    ),
    _SimpleTransform(
        "text_sort",
        "Sort lines alphabetically.",
        text_utils.sort_lines,
    ),
    _SimpleTransform(
        "text_unique",
        "Remove duplicate lines.",
        text_utils.unique_lines,
    ),
    _SimpleTransform(
        "text_number",
        "Prefix lines with numbers.",
        text_utils.add_line_numbers,
    ),
    _SimpleTransform(
        "text_strip_numbers",
        "Remove previously added line numbers.",
        text_utils.strip_line_numbers,
    ),
)


_HELP_MESSAGE = "\n".join(
    [
        "Available text tools:",
        *[f"/{item.command} - {item.description}" for item in _TRANSFORMS],
        "/lorem - Generate Lorem Ipsum text. Optionally pass `<words> [seed]`.",
    ]
)

_DEFAULT_LOREM_WORDS = text_utils.LoremConfig().words


@router.message(Command("text_tools"))
async def show_text_tools(message: Message) -> None:
    """List available text tool commands."""

    await message.answer(_HELP_MESSAGE, parse_mode=None)


def _register_simple_transform(transform: _SimpleTransform) -> None:
    usage = f"Usage: /{transform.command} <text>"

    async def handler(
        message: Message,
        command: CommandObject | None = None,
        *,
        _transform: _SimpleTransform = transform,
    ) -> None:
        if command is None or not command.args:
            await message.answer(usage, parse_mode=None)
            return
        result = _transform.transform(command.args)
        await message.answer(result, parse_mode=None)

    router.message.register(handler, Command(transform.command))


for _transform in _TRANSFORMS:
    _register_simple_transform(_transform)


@router.message(Command("lorem"))
async def handle_lorem(message: Message, command: CommandObject | None = None) -> None:
    """Generate deterministic Lorem Ipsum text."""

    words = None
    seed = None
    if command and command.args:
        parts = command.args.split()
        if parts:
            try:
                words = int(parts[0])
            except ValueError:
                words = None
        if len(parts) > 1:
            try:
                seed = int(parts[1])
            except ValueError:
                seed = None
    config = text_utils.LoremConfig(words=words or _DEFAULT_LOREM_WORDS, seed=seed)
    result = text_utils.generate_lorem_ipsum(config)
    await message.answer(result, parse_mode=None)

