"""Inline keyboard builders for the bot."""

from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


HOME_SECTIONS = (
    ("text_tools", "Text"),
    ("data_tools", "Data"),
    ("security_tools", "Security"),
    ("media_tools", "Media"),
    ("web_tools", "Web"),
    ("time_tools", "Time"),
    ("color_tools", "Color"),
)


def build_home_keyboard(is_admin: bool) -> InlineKeyboardMarkup:
    """Return placeholder home keyboard."""
    buttons = [[InlineKeyboardButton(text=label, callback_data=callback)] for callback, label in HOME_SECTIONS]
    if is_admin:
        buttons.append([InlineKeyboardButton(text="Admin", callback_data="admin_panel")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)
