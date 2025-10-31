"""Router package initialization."""

from __future__ import annotations

from aiogram import Router

from . import admin, files, home, tools


def _resolve_router(module: object, *, name: str) -> Router:
    router = getattr(module, "router", None)
    if isinstance(router, Router):
        return router
    router = Router(name=name)
    setattr(module, "router", router)
    return router


def all_routers() -> tuple[Router, ...]:
    """Return all routers that should be registered on dispatcher startup."""

    routers: list[Router] = [
        _resolve_router(home, name="home"),
        _resolve_router(files, name="files"),
        _resolve_router(admin, name="admin"),
    ]
    routers.extend(tools.tool_routers())
    return tuple(routers)


__all__ = ["all_routers"]
