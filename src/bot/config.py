"""Configuration objects and helpers."""

from __future__ import annotations

import os
from pathlib import Path

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration parsed from environment variables."""

    bot_token: str = Field(..., alias="BOT_TOKEN")
    admins: list[int] = Field(default_factory=list, alias="ADMINS_LIST")
    max_file_mb: int = Field(15, alias="MAX_FILE_MB")
    rate_limit_per_user_per_min: int = Field(30, alias="RATE_LIMIT_PER_USER_PER_MIN")
    persist_dir: Path = Field(Path("/data"), alias="PERSIST_DIR")
    redis_url: str | None = Field(default=None, alias="REDIS_URL")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        env_json_loads=lambda value: value,
    )

    @model_validator(mode="after")
    def _populate_admins(self) -> Settings:
        if self.admins:
            return self
        raw = os.getenv("ADMINS", "")
        if not raw:
            self.admins = []
        else:
            parts = [part.strip() for part in raw.split(",")]
            self.admins = [int(part) for part in parts if part]
        return self


def load_settings() -> Settings:
    """Load settings from the environment."""

    return Settings()
