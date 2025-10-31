"""Inline keyboard builders for frequently used menus."""

from __future__ import annotations

from textwrap import shorten
from typing import Mapping, Sequence

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


HOME_SECTIONS: tuple[tuple[str, str], ...] = (
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


def build_home_keyboard(
    is_admin: bool,
    section_labels: Mapping[str, str] | None = None,
    *,
    admin_label: str | None = None,
) -> InlineKeyboardMarkup:
    """Build the home menu keyboard grouping tools by category."""

    provided_labels = section_labels or {}
    rows: list[list[InlineKeyboardButton]] = []
    for slug, fallback in HOME_SECTIONS:
        label = provided_labels.get(slug, fallback)
        rows.append([InlineKeyboardButton(text=label, callback_data=f"home:{slug}")])
    if is_admin:
        rows.append([
            InlineKeyboardButton(
                text=admin_label or provided_labels.get("admin_panel", "Admin"),
                callback_data="admin_panel",
            )
        ])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def build_recent_keyboard(
    recent_tasks: Sequence[str],
    *,
    clear_label: str,
    back_label: str,
    back_callback: str = "home",
) -> InlineKeyboardMarkup:
    """Return an inline keyboard for navigating recent tasks."""

    rows: list[list[InlineKeyboardButton]] = []
    for index, item in enumerate(recent_tasks, start=1):
        text = shorten(item, width=46, placeholder="...")
        rows.append([
            InlineKeyboardButton(text=f"{index}. {text}", callback_data=f"recent:{index - 1}")
        ])
    if recent_tasks:
        rows.append([InlineKeyboardButton(text=clear_label, callback_data="recent:clear")])
    rows.append([InlineKeyboardButton(text=back_label, callback_data=back_callback)])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def build_settings_keyboard(
    options: Sequence[tuple[str, str]],
    *,
    back_label: str,
    back_callback: str = "home",
) -> InlineKeyboardMarkup:
    """Return an inline keyboard listing configurable settings options."""

    rows: list[list[InlineKeyboardButton]] = [
        [InlineKeyboardButton(text=label, callback_data=callback)] for callback, label in options
    ]
    rows.append([InlineKeyboardButton(text=back_label, callback_data=back_callback)])
    return InlineKeyboardMarkup(inline_keyboard=rows)


__all__ = [
    "HOME_SECTIONS",
    "build_home_keyboard",
    "build_recent_keyboard",
    "build_settings_keyboard",
]


