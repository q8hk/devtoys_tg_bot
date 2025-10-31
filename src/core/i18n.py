"""Internationalization helpers."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

logger = logging.getLogger(__name__)


class I18nError(RuntimeError):
    """Base error for I18n failures."""


class CatalogNotFoundError(I18nError):
    """Raised when a catalog for a locale is missing."""


class MessageNotFoundError(I18nError):
    """Raised when a message key cannot be located."""


@dataclass(slots=True)
class I18nContext:
    """Translator bound to a specific locale."""

    i18n: "I18n"
    locale: str

    def gettext(self, key: str, /, **kwargs: Any) -> str:
        """Translate a key using the bound locale."""

        return self.i18n.gettext(key, locale=self.locale, **kwargs)

    __call__ = gettext


class I18n:
    """Loads JSON catalogs and provides translation helpers."""

    def __init__(self, locales_dir: Path, default_locale: str = "en") -> None:
        self._locales_dir = locales_dir
        self._default_locale = self._normalize_locale(default_locale)
        self._catalogs: dict[str, Mapping[str, Any]] = {}
        self.reload()

    @property
    def default_locale(self) -> str:
        return self._default_locale

    @property
    def locales_dir(self) -> Path:
        return self._locales_dir

    def reload(self) -> None:
        """Reload catalogs from disk."""

        self._catalogs = {}
        if not self._locales_dir.exists():
            raise CatalogNotFoundError(
                f"Locales directory '{self._locales_dir}' does not exist"
            )
        for path in sorted(self._locales_dir.glob("*.json")):
            locale = self._normalize_locale(path.stem)
            try:
                with path.open("r", encoding="utf-8") as fp:
                    data = json.load(fp)
            except json.JSONDecodeError as exc:
                raise I18nError(f"Failed to parse locale file '{path}'") from exc
            if not isinstance(data, Mapping):
                raise I18nError(
                    f"Catalog '{path}' must contain an object at the root"
                )
            self._catalogs[locale] = data
        if self._default_locale not in self._catalogs:
            raise CatalogNotFoundError(
                f"Default locale '{self._default_locale}' not found in {self._locales_dir}"
            )

    def available_locales(self) -> tuple[str, ...]:
        """Return the loaded locales."""

        return tuple(self._catalogs.keys())

    def resolve_locale(self, locale: str | None) -> str:
        """Resolve a locale using fallbacks."""

        if locale:
            normalized = self._normalize_locale(locale)
            if normalized in self._catalogs:
                return normalized
            base = normalized.split("-")[0]
            if base in self._catalogs:
                return base
        return self._default_locale

    def gettext(
        self,
        key: str,
        /,
        *,
        locale: str | None = None,
        default: str | None = None,
        **kwargs: Any,
    ) -> str:
        """Translate *key* using *locale* or the default.

        Nested keys can be accessed with dot-notation (e.g. ``errors.general``).
        """

        resolved_locale = self.resolve_locale(locale)
        catalog = self._catalogs.get(resolved_locale)
        if catalog is None:
            raise CatalogNotFoundError(
                f"Locale '{resolved_locale}' is not available. Loaded: {self.available_locales()}"
            )
        message = self._lookup(catalog, key)
        if message is None and resolved_locale != self._default_locale:
            fallback_catalog = self._catalogs[self._default_locale]
            message = self._lookup(fallback_catalog, key)
        if message is None:
            if default is not None:
                message = default
            else:
                logger.debug("Missing translation", extra={"key": key, "locale": resolved_locale})
                message = key
        if kwargs:
            try:
                message = message.format(**kwargs)
            except Exception:  # pragma: no cover - formatting errors are logged then bubbled
                logger.exception(
                    "Failed to format translation",
                    extra={"key": key, "locale": resolved_locale, "kwargs": kwargs},
                )
        return message

    def get_context(self, locale: str | None) -> I18nContext:
        """Return a context helper bound to *locale*."""

        resolved = self.resolve_locale(locale)
        return I18nContext(i18n=self, locale=resolved)

    @staticmethod
    def _normalize_locale(locale: str) -> str:
        sanitized = locale.replace("_", "-").lower()
        return sanitized

    @staticmethod
    def _lookup(catalog: Mapping[str, Any], key: str) -> str | None:
        parts = key.split(".") if key else []
        current: Any = catalog
        for part in parts:
            if isinstance(current, Mapping) and part in current:
                current = current[part]
            else:
                return None
        if isinstance(current, str):
            return current
        return None

    def __contains__(self, locale: str) -> bool:
        return self._normalize_locale(locale) in self._catalogs

    def __len__(self) -> int:
        return len(self._catalogs)


__all__ = [
    "I18n",
    "I18nContext",
    "I18nError",
    "CatalogNotFoundError",
    "MessageNotFoundError",
]
