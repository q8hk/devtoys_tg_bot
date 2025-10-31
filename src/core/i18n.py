"""Internationalization helpers for loading localized resources."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping


class I18n:
    """Load JSON-based translation catalogs with graceful fallbacks."""

    def __init__(self, base_path: Path | str | None = None, default_locale: str = "en") -> None:
        root = Path(__file__).resolve().parents[2]
        self._base_path = Path(base_path) if base_path else root / "assets" / "i18n"
        self._default_locale = default_locale
        self._cache: dict[tuple[str, str], Mapping[str, Any]] = {}

    def _normalize_locale(self, locale: str | None) -> str:
        if not locale:
            return self._default_locale
        return locale.replace("_", "-").split("-", maxsplit=1)[0].lower()

    def _load_namespace(self, locale: str, namespace: str) -> Mapping[str, Any]:
        key = (locale, namespace)
        if key in self._cache:
            return self._cache[key]
        path = self._base_path / locale / f"{namespace}.json"
        if path.is_file():
            with path.open(encoding="utf-8") as fp:
                data = json.load(fp)
        else:
            data = {}
        self._cache[key] = data
        return data

    def clear_cache(self) -> None:
        """Clear the in-memory cache of loaded catalogs."""

        self._cache.clear()

    def translate(
        self,
        namespace: str,
        key: str,
        *,
        locale: str | None = None,
        default: Any | None = None,
    ) -> Any:
        """Return the translation for ``key`` in ``namespace``.

        Keys may be dotted paths (``section.subsection.value``). If the key is not
        found in the requested locale, the method falls back to the default
        locale. When no translation is available the provided ``default`` value is
        returned, otherwise the key itself is returned.
        """

        normalized_locale = self._normalize_locale(locale)
        value = self._resolve_value(self._load_namespace(normalized_locale, namespace), key)
        if value is not None:
            return value
        if normalized_locale != self._default_locale:
            value = self._resolve_value(self._load_namespace(self._default_locale, namespace), key)
            if value is not None:
                return value
        return default if default is not None else key

    def _resolve_value(self, data: Mapping[str, Any], dotted_key: str) -> Any:
        current: Any = data
        for part in dotted_key.split('.'):
            if isinstance(current, Mapping) and part in current:
                current = current[part]
            else:
                return None
        return current


_i18n = I18n()


def translate(namespace: str, key: str, *, locale: str | None = None, default: Any | None = None) -> Any:
    """Proxy helper using the module-level ``I18n`` instance."""

    return _i18n.translate(namespace, key, locale=locale, default=default)


__all__ = ["I18n", "translate"]
