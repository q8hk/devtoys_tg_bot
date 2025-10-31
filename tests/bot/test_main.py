import asyncio
import logging
from types import SimpleNamespace

import pytest
from src.bot import main as bot_main


class DummySession:
    def __init__(self) -> None:
        self.closed = False

    async def close(self) -> None:
        self.closed = True


class DummyBot:
    def __init__(self, *, token: str, default: object) -> None:  # noqa: D401 - simple stub
        self.token = token
        self.default = default
        self.session = DummySession()


class DummyDispatcher:
    def __init__(self) -> None:
        self.polled_with: DummyBot | None = None

    async def start_polling(self, bot: DummyBot) -> None:
        self.polled_with = bot


def test_main_bootstrap_flow(monkeypatch: pytest.MonkeyPatch) -> None:
    settings = SimpleNamespace(bot_token="token", admins=[1])
    monkeypatch.setattr(bot_main, "load_settings", lambda: settings)
    monkeypatch.setattr(bot_main, "ParseMode", SimpleNamespace(HTML="HTML"))
    monkeypatch.setattr(
        bot_main,
        "DefaultBotProperties",
        lambda parse_mode: SimpleNamespace(parse_mode=parse_mode),
    )

    dispatcher = DummyDispatcher()
    monkeypatch.setattr(bot_main, "Dispatcher", lambda: dispatcher)

    created: dict[str, DummyBot] = {}

    def bot_factory(*, token: str, default: object) -> DummyBot:
        created["bot"] = DummyBot(token=token, default=default)
        return created["bot"]

    monkeypatch.setattr(bot_main, "Bot", bot_factory)

    asyncio.run(bot_main.main())

    assert dispatcher.polled_with is created["bot"]
    assert created["bot"].session.closed is True


def test_configure_logging_invokes_basic_config(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, object] = {}

    def fake_basic_config(**kwargs: object) -> None:
        captured.update(kwargs)

    monkeypatch.setattr(logging, "basicConfig", fake_basic_config)

    bot_main.configure_logging()

    assert captured["level"] == logging.INFO
    assert "format" in captured
