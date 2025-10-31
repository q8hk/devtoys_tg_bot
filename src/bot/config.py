"""Configuration objects and helpers."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration parsed from environment variables."""

    bot_token: str = Field(..., alias="BOT_TOKEN")
    admins: list[int] = Field(default_factory=list, alias="ADMINS")
    max_file_mb: int = Field(15, alias="MAX_FILE_MB")
    rate_limit_per_user_per_min: int = Field(30, alias="RATE_LIMIT_PER_USER_PER_MIN")
    persist_dir: Path = Field(Path("/data"), alias="PERSIST_DIR")
    redis_url: str | None = Field(default=None, alias="REDIS_URL")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @field_validator("admins", mode="before")
    @classmethod
    def _parse_admins(cls, value: Any) -> list[int]:
        if value is None or value == "":
            return []
        if isinstance(value, str):
            parts = [part.strip() for part in value.split(",")]
            return [int(part) for part in parts if part]
        if isinstance(value, (list, tuple, set)):
            return [int(item) for item in value if str(item).strip()]
        return [int(value)]


def load_settings() -> Settings:
    """Load settings from the environment."""

    return Settings()
