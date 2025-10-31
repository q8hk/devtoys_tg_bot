"""Configuration objects and helpers."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
import logging
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


@dataclass(slots=True, frozen=True)
class BotConfig:
    """Bot-related runtime options."""

    token: str
    admins: tuple[int, ...]
    max_file_mb: int


@dataclass(slots=True, frozen=True)
class RateLimitConfig:
    """Rate limiting options."""

    per_user_per_minute: int
    redis_url: str | None


@dataclass(slots=True, frozen=True)
class PersistenceConfig:
    """Persistence directory configuration."""

    root: Path
    retention: timedelta
    cleanup_interval: timedelta


@dataclass(slots=True, frozen=True)
class LoggingConfig:
    """Logging configuration."""

    level: int


@dataclass(slots=True, frozen=True)
class AppConfig:
    """Aggregate application configuration dataclass."""

    bot: BotConfig
    rate_limit: RateLimitConfig
    persistence: PersistenceConfig
    logging: LoggingConfig

    @property
    def admins(self) -> list[int]:
        """Expose admin identifiers for backward compatibility."""

        return list(self.bot.admins)

    @property
    def max_file_mb(self) -> int:
        """Return the configured maximum file size in megabytes."""

        return self.bot.max_file_mb

    @property
    def bot_token(self) -> str:
        """Return the bot token."""

        return self.bot.token

    @property
    def persist_dir(self) -> Path:
        """Return the root persistence directory."""

        return self.persistence.root

    @property
    def redis_url(self) -> str | None:
        """Expose the configured Redis endpoint (if any)."""

        return self.rate_limit.redis_url


class Settings(BaseSettings):
    """Runtime configuration parsed from environment variables."""

    bot_token: str = Field(..., alias="BOT_TOKEN")
    admins_raw: object = Field(default=None, alias="ADMINS")
    max_file_mb: int = Field(15, alias="MAX_FILE_MB", ge=1)
    rate_limit_per_user_per_min: int = Field(30, alias="RATE_LIMIT_PER_USER_PER_MIN", ge=1)
    persist_dir: Path = Field(Path("/data"), alias="PERSIST_DIR")
    persist_retention_hours: int = Field(24, alias="PERSIST_RETENTION_HOURS", ge=1)
    persist_cleanup_interval_minutes: int = Field(
        30,
        alias="PERSIST_CLEANUP_INTERVAL_MINUTES",
        ge=1,
    )
    redis_url: str | None = Field(default=None, alias="REDIS_URL")
    log_level: str | int = Field("INFO", alias="LOG_LEVEL")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        env_json_loads=lambda value: value,
    )

    @field_validator("persist_dir", mode="before")
    @classmethod
    def _expand_persist_dir(cls, value: object) -> Path:
        path = Path(value).expanduser() if value is not None else Path("/data")
        return path

    @field_validator("log_level")
    @classmethod
    def _normalize_log_level(cls, value: str | int) -> int:
        if isinstance(value, int):
            return value
        name = value.upper().strip()
        if name not in logging._nameToLevel:  # noqa: SLF001 - accessing mapping for conversion only
            raise ValueError(f"Unknown log level: {value}")
        return logging._nameToLevel[name]

    def to_dataclass(self) -> AppConfig:
        """Transform runtime settings into frozen dataclasses."""

        bot_config = BotConfig(
            token=self.bot_token,
            admins=self._parse_admins(self.admins_raw),
            max_file_mb=self.max_file_mb,
        )
        rate_limit_config = RateLimitConfig(
            per_user_per_minute=self.rate_limit_per_user_per_min,
            redis_url=self.redis_url,
        )
        persistence_config = PersistenceConfig(
            root=self.persist_dir,
            retention=timedelta(hours=self.persist_retention_hours),
            cleanup_interval=timedelta(minutes=self.persist_cleanup_interval_minutes),
        )
        logging_config = LoggingConfig(level=self.log_level)
        return AppConfig(
            bot=bot_config,
            rate_limit=rate_limit_config,
            persistence=persistence_config,
            logging=logging_config,
        )

    @staticmethod
    def _parse_admins(value: object) -> tuple[int, ...]:
        if value in (None, ""):
            return ()
        if isinstance(value, (list, tuple, set)):
            return tuple(int(item) for item in value)
        if isinstance(value, str):
            parts = [chunk.strip() for chunk in value.split(",")]
            return tuple(int(chunk) for chunk in parts if chunk)
        if isinstance(value, (int, float)):
            return (int(value),)
        raise TypeError("ADMINS must be a comma separated string or iterable of integers")


def load_settings() -> AppConfig:
    """Load settings from the environment and return dataclasses."""

    return Settings().to_dataclass()


__all__ = [
    "AppConfig",
    "BotConfig",
    "LoggingConfig",
    "PersistenceConfig",
    "RateLimitConfig",
    "load_settings",
]
