import os

import pytest

from src.bot import config, keyboards


def test_settings_admin_parsing(monkeypatch):
    monkeypatch.setenv("BOT_TOKEN", "token")
    monkeypatch.setenv("ADMINS", "1, 2,3")
    settings = config.load_settings()
    assert settings.admins == [1, 2, 3]
    assert settings.max_file_mb == 15


@pytest.mark.parametrize("is_admin, expected_rows", [(True, 8), (False, 7)])
def test_home_keyboard_rows(is_admin, expected_rows):
    keyboard = keyboards.build_home_keyboard(is_admin)
    assert len(keyboard.inline_keyboard) == expected_rows


def test_tool_footer_keyboard_defaults():
    keyboard = keyboards.build_tool_footer_keyboard()
    assert keyboard.inline_keyboard[0][0].text == "⬅️ Back"
    assert keyboard.inline_keyboard[0][1].text == "🏠 Home"
    assert len(keyboard.inline_keyboard) == 2


def test_tool_footer_keyboard_custom_callbacks():
    keyboard = keyboards.build_tool_footer_keyboard(
        back_callback="go_back",
        home_callback="go_home",
        run_again_callback=None,
        copy_callback="copy",
    )
    assert len(keyboard.inline_keyboard) == 2
    assert keyboard.inline_keyboard[0][0].callback_data == "go_back"
    assert keyboard.inline_keyboard[1][0].callback_data == "copy"
