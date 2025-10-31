"""Shared helpers for tool routers."""

from __future__ import annotations

import inspect
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Awaitable, Mapping, Protocol, TypeVar

from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from ulid import ULID

from ...config import Settings
from ...rate_limit import RateLimiter
from ...utils.responders import DEFAULT_TEXT_THRESHOLD, ToolResponse, build_text_response


class ToolStates(StatesGroup):
    """Common FSM states used across tool flows."""

    idle = State()
    awaiting_input = State()
    processing = State()


class ToolValidationError(ValueError):
    """Raised when incoming data cannot be validated."""


@dataclass(slots=True)
class ToolRunContext:
    """Context information for a single tool execution."""

    settings: Settings
    user_id: int
    chat_id: int
    job_id: str
    job_path: Path

    def ensure_directory(self) -> None:
        """Ensure the job directory exists on disk."""

        self.job_path.mkdir(parents=True, exist_ok=True)

    def file_path(self, file_name: str) -> Path:
        """Return the absolute path for ``file_name`` inside ``job_path``."""

        return self.job_path / file_name


TValidated = TypeVar("TValidated")
TResult = TypeVar("TResult")


class Validator(Protocol[TValidated]):
    """Callable responsible for validating incoming data."""

    def __call__(self, data: Any) -> TValidated | Awaitable[TValidated]:
        """Validate the provided input."""


class Executor(Protocol[TValidated, TResult]):
    """Callable responsible for executing the tool logic."""

    def __call__(self, context: ToolRunContext, data: TValidated) -> TResult | Awaitable[TResult]:
        """Run the tool with ``data`` returning a result."""


class ResponseBuilder(Protocol[TResult]):
    """Callable used to convert execution results into ``ToolResponse``."""

    def __call__(self, context: ToolRunContext, result: TResult) -> ToolResponse:
        """Return a ready-to-send response."""


class ToolExecutionHelper:
    """Utility orchestrating validation, rate limiting, and response preparation."""

    def __init__(self, settings: Settings, rate_limiter: RateLimiter | None = None) -> None:
        self._settings = settings
        self._rate_limiter = rate_limiter or RateLimiter(settings.rate_limit_per_user_per_min)

    async def start(self, state: FSMContext) -> None:
        """Mark the FSM state as awaiting input."""

        await state.set_state(ToolStates.awaiting_input)

    async def execute(
        self,
        *,
        state: FSMContext,
        user_id: int,
        chat_id: int,
        raw_input: Any,
        validator: Validator[TValidated],
        executor: Executor[TValidated, TResult],
        response_builder: ResponseBuilder[TResult] | None = None,
        response_options: Mapping[str, Any] | None = None,
    ) -> ToolResponse:
        """Execute a tool flow returning a ``ToolResponse``."""

        await self._rate_limiter.check(user_id)
        await state.set_state(ToolStates.processing)

        try:
            validated = await self._run_validator(validator, raw_input)
        except ToolValidationError:
            await state.set_state(ToolStates.awaiting_input)
            raise

        context = self._build_context(user_id=user_id, chat_id=chat_id)
        context.ensure_directory()

        try:
            result = await self._run_executor(executor, context, validated)
        finally:
            await state.clear()

        builder = response_builder or self._default_response_builder(response_options)
        return builder(context, result)

    async def _run_validator(
        self, validator: Validator[TValidated], raw_input: Any
    ) -> TValidated:
        try:
            result = validator(raw_input)
            if inspect.isawaitable(result):
                return await result  # type: ignore[return-value]
            return result  # type: ignore[return-value]
        except ToolValidationError:
            raise
        except ValueError as exc:  # pragma: no cover - defensive branch
            raise ToolValidationError(str(exc)) from exc

    def _build_context(self, *, user_id: int, chat_id: int) -> ToolRunContext:
        job_id = str(ULID())
        job_path = self._settings.persist_dir / "users" / str(user_id) / "jobs" / job_id
        return ToolRunContext(
            settings=self._settings,
            user_id=user_id,
            chat_id=chat_id,
            job_id=job_id,
            job_path=job_path,
        )

    async def _run_executor(
        self,
        executor: Executor[TValidated, TResult],
        context: ToolRunContext,
        validated: TValidated,
    ) -> TResult:
        result = executor(context, validated)
        if inspect.isawaitable(result):
            return await result  # type: ignore[return-value]
        return result  # type: ignore[return-value]

    def _default_response_builder(
        self, options: Mapping[str, Any] | None
    ) -> ResponseBuilder[TResult]:
        opts = dict(options or {})

        def builder(context: ToolRunContext, result: TResult) -> ToolResponse:
            if isinstance(result, ToolResponse):
                return result
            response_kwargs = {
                "persist_path": context.job_path,
                "threshold": opts.get("threshold", DEFAULT_TEXT_THRESHOLD),
            }
            if "parse_mode" in opts:
                response_kwargs["parse_mode"] = opts["parse_mode"]
            if "keyboard" in opts:
                response_kwargs["keyboard"] = opts["keyboard"]
            if "file_name" in opts:
                response_kwargs["file_name"] = opts["file_name"]
            return build_text_response(str(result), **response_kwargs)

        return builder
