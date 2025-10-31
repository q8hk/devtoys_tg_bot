"""Application entry point for the DevToys-inspired Telegram bot."""

from __future__ import annotations

import asyncio
import logging
from contextlib import suppress

from aiogram import Bot, Dispatcher
from aiogram.client.bot import DefaultBotProperties
from aiogram.enums import ParseMode
import structlog

from .config import AppConfig, load_settings
from .middlewares import LocalizationMiddleware, LoggingMiddleware, RateLimitMiddleware
from .persistence import PersistenceManager
from .routers import all_routers
from .storage import StorageManager


def configure_logging(config: AppConfig) -> None:
    """Configure structured logging with JSON output."""

    level = config.logging.level
    timestamper = structlog.processors.TimeStamper(fmt="iso", utc=True)
    shared_processors = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        timestamper,
    ]

    formatter = structlog.stdlib.ProcessorFormatter(
        processor=structlog.processors.JSONRenderer(),
        foreign_pre_chain=shared_processors,
    )
    handler = logging.StreamHandler()
    handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.addHandler(handler)
    root_logger.setLevel(level)

    structlog.configure(
        processors=[
            *shared_processors,
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer(),
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )


def register_middlewares(dispatcher: Dispatcher, config: AppConfig, logger: structlog.BoundLogger) -> None:
    """Attach global middlewares required for the bot."""

    dispatcher.update.outer_middleware(LoggingMiddleware(logger=logger.bind(middleware="logging")))
    dispatcher.update.middleware(LocalizationMiddleware(default_locale="en"))
    dispatcher.update.middleware(
        RateLimitMiddleware(
            limit_per_minute=config.rate_limit.per_user_per_minute,
            logger=logger.bind(middleware="rate_limit"),
        ),
    )


def register_routers(dispatcher: Dispatcher) -> None:
    """Include all routers defined in the project."""

    for router in all_routers():
        dispatcher.include_router(router)


async def main(config: AppConfig) -> None:
    """Bootstrap application layers and start polling."""

    logger = structlog.get_logger("bot")
    persistence_manager = PersistenceManager(config.persistence, logger=logger)

    bot = Bot(
        token=config.bot.token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    storage = StorageManager(
        config.persistence.root,
        max_age=config.persistence.retention,
        cleanup_interval=config.persistence.cleanup_interval,
    )
    await storage.startup()
    dispatcher = Dispatcher()
    dispatcher["config"] = config
    dispatcher["persistence_manager"] = persistence_manager
    dispatcher["storage_manager"] = storage

    register_middlewares(dispatcher, config, logger)
    register_routers(dispatcher)

    async def on_startup(*args, **kwargs) -> None:  # noqa: ANN002, ANN003 - aiogram callback signature
        await persistence_manager.start()
        logger.info("startup_complete")

    async def on_shutdown(*args, **kwargs) -> None:  # noqa: ANN002, ANN003 - aiogram callback signature
        await persistence_manager.shutdown()
        logger.info("shutdown_complete")

    try:
        await dispatcher.start_polling(
            bot,
            on_startup=on_startup,
            on_shutdown=on_shutdown,
        )
    finally:
        with suppress(Exception):
            await persistence_manager.shutdown()
        with suppress(Exception):
            await storage.shutdown()
        await bot.session.close()


def run() -> None:
    """Entry-point helper used by command line scripts."""

    config = load_settings()
    configure_logging(config)
    asyncio.run(main(config))


if __name__ == "__main__":
    run()
