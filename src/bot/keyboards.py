"""Inline keyboard builders for the bot."""

from __future__ import annotations

from typing import Iterable, Sequence

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


HOME_SECTIONS: Sequence[tuple[str, str]] = (
    ("text_tools", "Text"),
    ("data_tools", "Data"),
    ("security_tools", "Security"),
    ("media_tools", "Media"),
    ("web_tools", "Web"),
    ("time_tools", "Time"),
    ("color_tools", "Color"),
)

BACK_CALLBACK = "tools:back"
HOME_CALLBACK = "home:open"
RUN_AGAIN_CALLBACK = "tools:run_again"
COPY_CALLBACK = "tools:copy"


def build_home_keyboard(is_admin: bool) -> InlineKeyboardMarkup:
    """Return a simple home keyboard grouping tool categories."""
    buttons = [[InlineKeyboardButton(text=label, callback_data=callback)] for callback, label in HOME_SECTIONS]
    if is_admin:
        buttons.append([InlineKeyboardButton(text="Admin", callback_data="admin_panel")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def build_back_button(callback_data: str = BACK_CALLBACK) -> InlineKeyboardButton:
    """Create a shared "Back" button used across tool flows."""

    return InlineKeyboardButton(text="⬅️ Back", callback_data=callback_data)


def build_home_button(callback_data: str = HOME_CALLBACK) -> InlineKeyboardButton:
    """Create a shared "Home" button used across tool flows."""

    return InlineKeyboardButton(text="🏠 Home", callback_data=callback_data)


def build_run_again_button(callback_data: str = RUN_AGAIN_CALLBACK) -> InlineKeyboardButton:
    """Create a shared "Run again" button used after tool completion."""

    return InlineKeyboardButton(text="🔁 Run again", callback_data=callback_data)


def build_copy_button(callback_data: str = COPY_CALLBACK) -> InlineKeyboardButton:
    """Create a shared "Copy" button used to resurface the latest result."""

    return InlineKeyboardButton(text="📋 Copy", callback_data=callback_data)


def build_tool_footer_keyboard(
    *,
    back_callback: str = BACK_CALLBACK,
    home_callback: str = HOME_CALLBACK,
    run_again_callback: str | None = RUN_AGAIN_CALLBACK,
    copy_callback: str | None = COPY_CALLBACK,
    extra_rows: Iterable[Sequence[InlineKeyboardButton]] | None = None,
) -> InlineKeyboardMarkup:
    """Build the shared footer keyboard for tool responses.

    The keyboard always contains a first row with "Back" and "Home" buttons. Optional
    "Run again" and "Copy" buttons share the second row when callbacks are provided.
    Additional rows can be appended through ``extra_rows`` for tool-specific actions.
    """

    first_row = [build_back_button(back_callback), build_home_button(home_callback)]
    rows: list[list[InlineKeyboardButton]] = [first_row]

    optional_row: list[InlineKeyboardButton] = []
    if run_again_callback:
        optional_row.append(build_run_again_button(run_again_callback))
    if copy_callback:
        optional_row.append(build_copy_button(copy_callback))
    if optional_row:
        rows.append(optional_row)

    if extra_rows:
        for row in extra_rows:
            rows.append(list(row))

    return InlineKeyboardMarkup(inline_keyboard=rows)
