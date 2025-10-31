"""Handlers for the home menu flows."""

from __future__ import annotations

from html import escape
from typing import Mapping

from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from ..config import load_settings
from ..keyboards import build_home_keyboard, build_recent_keyboard, build_settings_keyboard
from ..services.history import RecentHistoryStorage
from core.i18n import I18n

router = Router(name="home")

_settings = load_settings()
_history_storage = RecentHistoryStorage(_settings.persist_dir / "history", _settings.redis_url)
_i18n = I18n()

_SECTION_GUIDES: Mapping[str, str] = {
    "text_tools": (
        "Text helpers:\n"
        "- /text_tools to list available commands\n"
        "- /text_trim <text> to trim whitespace\n"
        "- /lorem <words> [seed] for lorem ipsum"
    ),
    "data_tools": "Data utilities are coming soon. Try /json_pretty or /json_yaml when available.",
    "security_tools": (
        "Security helpers:\n"
        "- /hash_sha256 <text>\n"
        "- /base64_encode <text>\n"
        "- /jwt_decode <token>"
    ),
    "media_tools": "Media tools will guide you through image, QR, and file conversions (coming soon).",
    "web_tools": (
        "Web utilities:\n"
        "- /urlencode <text>\n"
        "- /urldecode <text>\n"
        "- /urlparse <query or url>"
    ),
    "time_tools": "Time helpers: try /epoch_to_human <epoch> or /time_now for quick conversions.",
    "color_tools": "Color utilities coming soon. You'll be able to convert HEX, RGB, and more.",
}


def _is_admin(user_id: int | None) -> bool:
    return bool(user_id and user_id in _settings.admins)


def _get_section_labels(locale: str | None) -> Mapping[str, str]:
    sections = _i18n.translate("home", "home_sections", locale=locale, default={})
    return sections if isinstance(sections, Mapping) else {}


async def _send_home(message: Message, *, locale: str | None) -> None:
    title = _i18n.translate("home", "start_title", locale=locale, default="DevToys Tools")
    body = _i18n.translate(
        "home",
        "start_body",
        locale=locale,
        default="Choose a category below to get started.",
    )
    sections = _get_section_labels(locale)
    admin_label = sections.get("admin_panel", "Admin")
    keyboard = build_home_keyboard(
        _is_admin(message.from_user.id if message.from_user else None),
        section_labels=sections,
        admin_label=admin_label,
    )
    await message.answer(
        "\n\n".join(part for part in (title, body) if part),
        reply_markup=keyboard,
        disable_web_page_preview=True,
    )


@router.message(CommandStart())
async def command_start(message: Message) -> None:
    """Render the home menu when the user issues /start."""

    locale = message.from_user.language_code if message.from_user else None
    if message.from_user:
        await _history_storage.add_task(message.from_user.id, "Opened home menu")
    await _send_home(message, locale=locale)


@router.message(Command("tools"))
async def command_tools(message: Message) -> None:
    """Alias for /start focusing on tool discovery."""

    locale = message.from_user.language_code if message.from_user else None
    await _send_home(message, locale=locale)


@router.message(Command("help"))
async def command_help(message: Message) -> None:
    """Provide contextual help information."""

    locale = message.from_user.language_code if message.from_user else None
    help_text = _i18n.translate("home", "help", locale=locale)
    await message.answer(help_text, disable_web_page_preview=True)


@router.message(Command("about"))
async def command_about(message: Message) -> None:
    locale = message.from_user.language_code if message.from_user else None
    about_text = _i18n.translate("home", "about", locale=locale)
    await message.answer(about_text, disable_web_page_preview=True)


@router.message(Command("privacy"))
async def command_privacy(message: Message) -> None:
    locale = message.from_user.language_code if message.from_user else None
    privacy_text = _i18n.translate("home", "privacy", locale=locale)
    await message.answer(privacy_text, disable_web_page_preview=True)


@router.message(Command("recent"))
async def command_recent(message: Message) -> None:
    locale = message.from_user.language_code if message.from_user else None
    user_id = message.from_user.id if message.from_user else None
    if not user_id:
        return
    tasks = await _history_storage.get_tasks(user_id)
    if tasks:
        intro = _i18n.translate("home", "recent_intro", locale=locale, default="Your latest tasks:")
        entries = "\n".join(f"{idx}. {item}" for idx, item in enumerate(tasks, start=1))
        text = f"{intro}\n{entries}"
    else:
        text = _i18n.translate("home", "recent_empty", locale=locale, default="No recent tasks yet.")
    keyboard = build_recent_keyboard(
        tasks,
        clear_label=_i18n.translate("home", "recent_manage.clear", locale=locale, default="Clear history"),
        back_label=_i18n.translate("home", "recent_manage.back", locale=locale, default="Back"),
    )
    await message.answer(text, reply_markup=keyboard)


@router.message(Command("cancel"))
async def command_cancel(message: Message, state: FSMContext) -> None:
    locale = message.from_user.language_code if message.from_user else None
    await state.clear()
    text = _i18n.translate("home", "cancelled", locale=locale, default="Cancelled.")
    await message.answer(text)


@router.message(Command("settings"))
async def command_settings(message: Message) -> None:
    locale = message.from_user.language_code if message.from_user else None
    options = _i18n.translate("home", "settings_options", locale=locale, default={})
    if not isinstance(options, Mapping):
        options = {}
    option_buttons = [(f"settings:{key}", str(label)) for key, label in options.items()]
    keyboard = build_settings_keyboard(
        option_buttons,
        back_label=_i18n.translate("home", "recent_manage.back", locale=locale, default="Back"),
    )
    intro = _i18n.translate("home", "settings_intro", locale=locale, default="Adjust your preferences:")
    await message.answer(intro, reply_markup=keyboard)


@router.callback_query(F.data == "recent:clear")
async def callback_recent_clear(callback: CallbackQuery) -> None:
    user = callback.from_user
    if not user:
        await callback.answer()
        return
    locale = user.language_code
    await _history_storage.clear(user.id)
    await callback.answer(_i18n.translate("home", "recent_cleared", locale=locale, default="History cleared."))
    text = _i18n.translate("home", "recent_empty", locale=locale, default="No recent tasks yet.")
    keyboard = build_recent_keyboard(
        [],
        clear_label=_i18n.translate("home", "recent_manage.clear", locale=locale, default="Clear history"),
        back_label=_i18n.translate("home", "recent_manage.back", locale=locale, default="Back"),
    )
    if callback.message:
        await callback.message.edit_text(text, reply_markup=keyboard)


@router.callback_query(F.data == "home")
async def callback_home(callback: CallbackQuery) -> None:
    user = callback.from_user
    if not user:
        await callback.answer()
        return
    locale = user.language_code
    sections = _get_section_labels(locale)
    admin_label = sections.get("admin_panel", "Admin")
    keyboard = build_home_keyboard(
        _is_admin(user.id),
        section_labels=sections,
        admin_label=admin_label,
    )
    title = _i18n.translate("home", "start_title", locale=locale, default="DevToys Tools")
    body = _i18n.translate(
        "home",
        "start_body",
        locale=locale,
        default="Choose a category below to get started.",
    )
    text = "\n\n".join(part for part in (title, body) if part)
    if callback.message:
        await callback.message.edit_text(text, reply_markup=keyboard, disable_web_page_preview=True)
    await callback.answer()


@router.callback_query(F.data.startswith("home:"))
async def callback_home_section(callback: CallbackQuery) -> None:
    user = callback.from_user
    if not user:
        await callback.answer()
        return
    locale = user.language_code
    data = callback.data or ""
    try:
        section = data.split(":", maxsplit=1)[1]
    except IndexError:
        await callback.answer()
        return
    sections = _get_section_labels(locale)
    label = sections.get(section, section.replace("_", " ").title())
    guide = _SECTION_GUIDES.get(section)
    if guide is None:
        guide = _i18n.translate(
            "home",
            "section_coming_soon",
            locale=locale,
            default="Content for this section is coming soon.",
        )
    else:
        guide = guide.replace("{label}", label)
    text = f"<b>{escape(label)}</b>\n\n{escape(guide)}"
    if callback.message:
        await callback.message.edit_text(text, disable_web_page_preview=True)
    await callback.answer()


@router.callback_query(F.data.startswith("recent:"))
async def callback_recent_item(callback: CallbackQuery) -> None:
    data = callback.data or ""
    if data == "recent:clear":
        return
    user = callback.from_user
    if not user:
        await callback.answer()
        return
    try:
        index = int(data.split(":", maxsplit=1)[1])
    except (IndexError, ValueError):
        await callback.answer()
        return
    tasks = await _history_storage.get_tasks(user.id)
    if 0 <= index < len(tasks):
        await callback.answer(tasks[index], show_alert=True)
    else:
        await callback.answer("Not found", show_alert=True)
