"""Application entry point for the DevToys-inspired Telegram bot."""

from __future__ import annotations

import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.bot import DefaultBotProperties

from .config import load_settings

logger = logging.getLogger(__name__)


def configure_logging() -> None:
    """Configure basic structured logging."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )


async def main() -> None:
    """Bootstrap application layers and start polling."""
    settings = load_settings()
    bot = Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dispatcher = Dispatcher()
    # TODO: Wire middlewares, routers, background tasks, and storage.
    logger.info("Bot initialized", extra={"admins": settings.admins})
    await bot.session.close()


if __name__ == "__main__":
    configure_logging()
    asyncio.run(main())
