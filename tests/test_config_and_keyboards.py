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
