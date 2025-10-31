"""Routers that expose tool-specific flows."""

from __future__ import annotations

from importlib import import_module

from aiogram import Router


_MODULES: tuple[str, ...] = (
    "base64_codec",
    "code_tools",
    "color_tools",
    "csv_tsv",
    "hash_tools",
    "html_tools",
    "image_tools",
    "json_yaml",
    "jwt_tools",
    "qr_tools",
    "regex_tools",
    "text_tools",
    "time_tools",
    "url_codec",
    "uuid_ulid",
    "xml_tools",
)


def _load_router(module_name: str) -> Router:
    module = import_module(f"{__name__}.{module_name}")
    router = getattr(module, "router", None)
    if isinstance(router, Router):
        return router
    router = Router(name=f"tools.{module_name}")
    setattr(module, "router", router)
    return router


def tool_routers() -> tuple[Router, ...]:
    """Return tool routers to be included in the dispatcher."""

    return tuple(_load_router(module_name) for module_name in _MODULES)


__all__ = ["tool_routers"]
