"""Routers that expose tool-specific flows."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover - imported for type hints only
    from aiogram import Dispatcher
    from ...storage import StorageManager


@dataclass(slots=True)
class ToolContext:
    """Shared dependencies for tool handlers."""

    storage: "StorageManager"


def attach_tool_context(dispatcher: "Dispatcher", storage: "StorageManager") -> None:
    """Bind the tool context to the dispatcher for easy access by routers."""

    dispatcher.workflow_data["tool_context"] = ToolContext(storage=storage)


def get_tool_context(dispatcher: "Dispatcher") -> ToolContext:
    """Retrieve the shared tool context from the dispatcher."""

    context = dispatcher.workflow_data.get("tool_context")
    if context is None:
        msg = "Tool context has not been initialised"
        raise RuntimeError(msg)
    return context


__all__ = ["ToolContext", "attach_tool_context", "get_tool_context"]
