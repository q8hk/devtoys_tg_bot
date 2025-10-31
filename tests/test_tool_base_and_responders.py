import asyncio
from pathlib import Path

import pytest
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.base import StorageKey
from aiogram.fsm.storage.memory import MemoryStorage

from src.bot.config import Settings
from src.bot.rate_limit import RateLimitExceededError, RateLimiter
from src.bot.routers.tools.base import (
    ToolExecutionHelper,
    ToolStates,
    ToolValidationError,
)
from src.bot.utils.responders import (
    DEFAULT_TEXT_THRESHOLD,
    ToolResponse,
    build_text_response,
    chunk_text,
)


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    return Settings.model_validate(
        {
            "BOT_TOKEN": "token",
            "ADMINS_LIST": [],
            "MAX_FILE_MB": 10,
            "RATE_LIMIT_PER_USER_PER_MIN": 3,
            "PERSIST_DIR": tmp_path,
        }
    )


def test_tool_execution_creates_job_dir_and_clears_state(settings: Settings) -> None:
    helper = ToolExecutionHelper(settings)
    storage = MemoryStorage()
    state = FSMContext(storage=storage, key=StorageKey(bot_id=1, chat_id=10, user_id=99))

    captured_context = None

    async def executor(context, data):
        nonlocal captured_context
        captured_context = context
        return data.upper()

    result = asyncio.run(
        helper.execute(
            state=state,
            user_id=99,
            chat_id=10,
            raw_input="payload",
            validator=lambda value: value,
            executor=executor,
        )
    )

    assert isinstance(result, ToolResponse)
    assert result.text == "PAYLOAD"
    assert captured_context is not None
    assert captured_context.job_path.exists()
    assert captured_context.job_id
    assert asyncio.run(state.get_state()) is None


def test_tool_execution_rate_limit(settings: Settings) -> None:
    limiter = RateLimiter(limit_per_minute=1)
    helper = ToolExecutionHelper(settings, rate_limiter=limiter)
    storage = MemoryStorage()
    state = FSMContext(storage=storage, key=StorageKey(bot_id=1, chat_id=1, user_id=7))

    asyncio.run(
        helper.execute(
            state=state,
            user_id=7,
            chat_id=1,
            raw_input="ok",
            validator=lambda value: value,
            executor=lambda context, data: data,
        )
    )

    with pytest.raises(RateLimitExceededError):
        asyncio.run(
            helper.execute(
                state=state,
                user_id=7,
                chat_id=1,
                raw_input="again",
                validator=lambda value: value,
                executor=lambda context, data: data,
            )
        )


def test_validator_failure_sets_state(settings: Settings) -> None:
    helper = ToolExecutionHelper(settings)
    storage = MemoryStorage()
    state = FSMContext(storage=storage, key=StorageKey(bot_id=1, chat_id=5, user_id=2))

    def fail(_value: str) -> str:
        raise ToolValidationError("bad")

    with pytest.raises(ToolValidationError):
        asyncio.run(
            helper.execute(
                state=state,
                user_id=2,
                chat_id=5,
                raw_input="",
                validator=fail,
                executor=lambda context, data: data,
            )
        )

    assert asyncio.run(state.get_state()) == ToolStates.awaiting_input.state


def test_chunk_text() -> None:
    chunks = chunk_text("abcd", limit=2)
    assert chunks == ["ab", "cd"]


def test_build_text_response_small_payload(tmp_path: Path) -> None:
    response = build_text_response("hi", threshold=10)
    assert not response.is_document
    assert response.text == "hi"


def test_build_text_response_large_payload(tmp_path: Path) -> None:
    text = "x" * (DEFAULT_TEXT_THRESHOLD + 10)
    response = build_text_response(text, persist_path=tmp_path, file_name="result.txt")
    assert response.is_document
    assert response.file_name == "result.txt"
    assert response.document is not None
    assert str(response.document.path).endswith("result.txt")
    assert (tmp_path / "result.txt").exists()
