"""Internationalization helpers for loading localized resources."""

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

    def __init__(self, locales_dir: Path | None = None, default_locale: str = "en") -> None:
        if locales_dir is None:
            locales_dir = Path(__file__).resolve().parent / "locales"
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
            logger.warning(
                "Locales directory missing; falling back to default locale",
                extra={"path": str(self._locales_dir)},
            )
            self._catalogs[self._default_locale] = {}
            return
        loaded_any = False
        for path in sorted(self._locales_dir.glob("*.json")):
            locale = self._normalize_locale(path.stem)
            try:
                with path.open("r", encoding="utf-8") as fp:
                    data = json.load(fp)
            except json.JSONDecodeError as exc:  # pragma: no cover - defensive logging
                raise I18nError(f"Failed to parse locale file '{path}'") from exc
            if not isinstance(data, Mapping):
                raise I18nError(f"Catalog '{path}' must contain an object at the root")
            self._catalogs[locale] = data
            loaded_any = True
        if not loaded_any:
            logger.warning(
                "No locale catalogs found; using empty default locale",
                extra={"path": str(self._locales_dir)},
            )
        self._catalogs.setdefault(self._default_locale, {})

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

        value = self._resolve_value(key, locale=locale, default=default if default is not None else key)
        if not isinstance(value, str):
            value = str(value)
        if kwargs:
            try:
                value = value.format(**kwargs)
            except Exception:  # pragma: no cover - formatting errors are logged then bubbled
                logger.exception(
                    "Failed to format translation",
                    extra={"key": key, "locale": self.resolve_locale(locale), "kwargs": kwargs},
                )
        return value

    def translate(
        self,
        domain: str,
        key: str,
        *,
        locale: str | None = None,
        default: Any = None,
        **kwargs: Any,
    ) -> Any:
        """Translate ``domain.key`` returning raw objects when available."""

        composite_key = f"{domain}.{key}" if domain else key
        value = self._resolve_value(composite_key, locale=locale, default=default)
        if isinstance(value, str) and kwargs:
            try:
                value = value.format(**kwargs)
            except Exception:  # pragma: no cover - formatting errors are logged then bubbled
                logger.exception(
                    "Failed to format translation",
                    extra={"key": composite_key, "locale": self.resolve_locale(locale), "kwargs": kwargs},
                )
        return value

    def get_context(self, locale: str | None) -> I18nContext:
        """Return a context helper bound to *locale*."""

        resolved = self.resolve_locale(locale)
        return I18nContext(i18n=self, locale=resolved)

    @staticmethod
    def _normalize_locale(locale: str) -> str:
        sanitized = locale.replace("_", "-").lower()
        return sanitized

    def _resolve_value(
        self,
        key: str,
        *,
        locale: str | None,
        default: Any,
    ) -> Any:
        resolved_locale = self.resolve_locale(locale)
        catalog = self._catalogs.get(resolved_locale)
        if catalog is None:
            raise CatalogNotFoundError(
                f"Locale '{resolved_locale}' is not available. Loaded: {self.available_locales()}"
            )
        value = self._lookup(catalog, key)
        if value is None and resolved_locale != self._default_locale:
            fallback_catalog = self._catalogs[self._default_locale]
            value = self._lookup(fallback_catalog, key)
        if value is None:
            if default is not None:
                return default
            logger.debug("Missing translation", extra={"key": key, "locale": resolved_locale})
            return default
        return value

    @staticmethod
    def _lookup(catalog: Mapping[str, Any], key: str) -> Any:
        parts = key.split(".") if key else []
        current: Any = catalog
        for part in parts:
            if isinstance(current, Mapping) and part in current:
                current = current[part]
            else:
                return None
        return current

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
