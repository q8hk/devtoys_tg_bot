from __future__ import annotations

# Shared error types for the bot.


class BotError(Exception):
    """Base exception for known bot errors."""


class ToolValidationError(BotError):
    """Raised when user input fails validation."""


class ToolExecutionError(BotError):
    """Raised when a tool fails to complete its work."""
