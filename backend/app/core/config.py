"""
Hierarchical Settings Engine (12-Factor compliant).

Layer 1 (Database/UI): values stored in the `system_settings` table, editable
                       through the Admin UI.
Layer 2 (Environment): values injected via Pydantic Settings (ENV vars) at
                       container start time.

Precedence: ENV variable > DB/UI value > built-in default.

The API exposes (`GET /api/v1/settings`) merged metadata so the UI can render
a "Managed via environment variable" badge and disable the input.
"""
from __future__ import annotations

import json
import os
from datetime import timedelta
from functools import lru_cache
from typing import Any, Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


# ---------------------------------------------------------------------------
# Layer 2 — Pydantic Settings (ENV precedence source of truth)
# ---------------------------------------------------------------------------
class Settings(BaseSettings):
    """Runtime configuration. ENV > .env file > default.

    Database *credentials* are intentionally NOT part of the UI-editable set.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # --- Core / infrastructure -------------------------------------------
    APP_NAME: str = "WishDeck"
    APP_VERSION: str = "1.0.6"
    ENVIRONMENT: str = "production"  # development | production
    BASE_URL: str = "http://localhost:8000"
    LOG_LEVEL: str = "INFO"

    # --- Database (credentials only, never UI-editable) ------------------
    DATABASE_URL: str = "sqlite+aiosqlite:///./data/wishdeck.db"
    DB_POOL_SIZE: int = 10
    DB_MAX_OVERFLOW: int = 20

    # --- Security / JWT --------------------------------------------------
    SECRET_KEY: str = Field(
        default="change-me-in-production-please-use-a-long-random-string",
        description="HS256 signing secret for JWT cookies.",
    )
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days
    COOKIE_SECURE: bool = True
    COOKIE_SAMESITE: str = "lax"

    # --- Local auth ------------------------------------------------------
    ENABLE_REGISTRATION: bool = True

    # --- OIDC / SAML (mixed-mode) ---------------------------------------
    OIDC_ENABLED: bool = False
    OIDC_ISSUER_URL: Optional[str] = None
    OIDC_CLIENT_ID: Optional[str] = None
    OIDC_CLIENT_SECRET: Optional[str] = None
    OIDC_NAME: str = "SSO"
    OIDC_SCOPES: str = "openid email profile"
    OIDC_REDIRECT_URI: Optional[str] = None

    # --- Feature flags / product behaviour ------------------------------
    ALLOW_PUBLIC_CLAIMS: bool = True
    DEFAULT_LOCALE: str = "en"  # en | sv  (server-controlled fallback)
    DEFAULT_VISIBILITY: str = "private"  # private | unlisted | public
    ITEMS_PER_PAGE: int = 50
    DEFAULT_CURRENCY: str = "USD"  # fallback when scraping detects no currency

    @field_validator("DATABASE_URL")
    @classmethod
    def _require_async_driver(cls, v: str) -> str:
        if v.startswith("sqlite") and "+aiosqlite" not in v:
            v = v.replace("sqlite", "sqlite+aiosqlite", 1)
        # CloudNativePG (and most operators) hand out a bare `postgresql://` URI.
        # SQLAlchemy's asyncio engine requires a genuinely async DBAPI, so rewrite
        # the scheme to the psycopg3 dialect. psycopg2 (sync) is rejected.
        scheme = v.split(":", 1)[0]
        if scheme in ("postgresql", "postgres"):
            v = v.replace(scheme, "postgresql+psycopg", 1)
        elif scheme == "postgresql+psycopg2":
            v = v.replace("postgresql+psycopg2", "postgresql+psycopg", 1)
        return v


# ---------------------------------------------------------------------------
# Setting schema — the single source of truth describing what is editable
# ---------------------------------------------------------------------------
# type: bool | int | str | float ; group is used for UI sectioning.
SETTING_DEFINITIONS: list[dict[str, Any]] = [
    # General
    {"key": "APP_NAME", "type": "str", "group": "general", "public": True,
     "label": "Application name", "help": "Display name shown in the UI."},
    {"key": "BASE_URL", "type": "str", "group": "general", "public": True,
     "label": "Base URL", "help": "Public base URL used for links and OIDC callbacks."},
    {"key": "DEFAULT_LOCALE", "type": "str", "group": "general", "public": True,
     "label": "Default locale", "help": "Fallback UI language (en | sv)."},
    # Auth
    {"key": "ENABLE_REGISTRATION", "type": "bool", "group": "auth", "public": False,
     "label": "Allow local registration", "help": "Permit self-service account creation."},
    {"key": "OIDC_ENABLED", "type": "bool", "group": "auth", "public": False,
     "label": "Enable OIDC", "help": "Show SSO buttons on the login page."},
    {"key": "OIDC_ISSUER_URL", "type": "str", "group": "auth", "public": False,
     "label": "OIDC issuer URL", "help": "e.g. https://keycloak.example.com/realms/master"},
    {"key": "OIDC_CLIENT_ID", "type": "str", "group": "auth", "public": False,
     "label": "OIDC client ID", "help": "Relying-party client identifier."},
    {"key": "OIDC_CLIENT_SECRET", "type": "str", "group": "auth", "public": False,
     "label": "OIDC client secret", "help": "Relying-party secret (sensitive)."},
    {"key": "OIDC_NAME", "type": "str", "group": "auth", "public": False,
     "label": "OIDC provider label", "help": "Button label, e.g. 'Keycloak'."},
    {"key": "OIDC_SCOPES", "type": "str", "group": "auth", "public": False,
     "label": "OIDC scopes", "help": "Space separated scopes."},
    # Features
    {"key": "ALLOW_PUBLIC_CLAIMS", "type": "bool", "group": "features", "public": True,
     "label": "Allow public claims", "help": "Let anonymous visitors reserve items."},
    {"key": "DEFAULT_VISIBILITY", "type": "str", "group": "features", "public": True,
     "label": "Default visibility", "help": "private | unlisted | public"},
    {"key": "ITEMS_PER_PAGE", "type": "int", "group": "features", "public": True,
     "label": "Items per page", "help": "Pagination page size."},
    {"key": "DEFAULT_CURRENCY", "type": "str", "group": "features", "public": True,
     "label": "Default currency", "help": "Fallback ISO currency code when none is detected while scraping (e.g. USD)."},
]

# Keys that are NEVER user-editable via the UI (managed by ENV / infra only).
NON_EDITABLE_KEYS = {
    "DATABASE_URL", "DB_POOL_SIZE", "DB_MAX_OVERFLOW", "SECRET_KEY",
    "JWT_ALGORITHM", "ACCESS_TOKEN_EXPIRE_MINUTES", "COOKIE_SECURE",
    "COOKIE_SAMESITE", "ENVIRONMENT", "LOG_LEVEL", "APP_VERSION",
    "OIDC_REDIRECT_URI",
}


def _env_name(key: str) -> str:
    return key.upper()


def _env_is_set(key: str) -> bool:
    """True only when the variable is *explicitly* present in the environment."""
    return _env_name(key) in os.environ


def _coerce(value: Any, typ: str) -> Any:
    if value is None:
        return None
    if typ == "bool":
        if isinstance(value, bool):
            return value
        return str(value).strip().lower() in {"1", "true", "yes", "on"}
    if typ == "int":
        return int(value)
    if typ == "float":
        return float(value)
    return str(value)


# ---------------------------------------------------------------------------
# Hybrid resolution logic (Layer 1 + Layer 2)
# ---------------------------------------------------------------------------
def resolve_settings(db_rows: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    """Merge ENV (Layer 2) over DB (Layer 1) over defaults.

    `db_rows` is a mapping of key -> stored value (already coerced/raw string)
    as returned by the SystemSetting repository. If ``db_rows`` is ``None`` the
    ENV/default layer alone is resolved (used before the DB is reachable).
    """
    db_rows = db_rows or {}
    settings = Settings()
    out: list[dict[str, Any]] = []

    for definition in SETTING_DEFINITIONS:
        key = definition["key"]
        typ = definition["type"]

        env_present = _env_is_set(key)
        default = getattr(settings, key, None)

        if env_present:
            raw = os.environ[_env_name(key)]
            value = _coerce(raw, typ)
            source = "env"
        elif key in db_rows and db_rows[key] is not None:
            value = _coerce(db_rows[key], typ)
            source = "database"
        else:
            value = default
            source = "database" if key in db_rows else "default"

        out.append({
            "key": key,
            "value": value,
            "type": typ,
            "group": definition["group"],
            "label": definition["label"],
            "help": definition.get("help"),
            "is_env_overridden": env_present,
            "source": source,
            "editable": key not in NON_EDITABLE_KEYS,
            "public": definition.get("public", False),
        })
    return out


async def effective_value(key: str, source: Any = None) -> Any:
    """Return the single effective value for `key` (ENV wins).

    `source` may be a pre-fetched ``{key: value}`` mapping or an AsyncSession
    (the DB settings are then fetched lazily to avoid an import cycle).
    """
    db_rows: dict[str, Any] | None = None
    if source is not None:
        if isinstance(source, dict):
            db_rows = source
        else:  # AsyncSession
            from app.core.settings_service import get_db_settings

            db_rows = await get_db_settings(source)
    for s in resolve_settings(db_rows):
        if s["key"] == key:
            return s["value"]
    raise KeyError(key)


def serialize_for_env() -> dict[str, str]:
    """Render current settings as ENV-ready strings (used for debugging)."""
    s = Settings()
    return {k: str(v) for k, v in s.model_dump().items()}


@lru_cache
def get_settings() -> Settings:
    return Settings()


__all__ = [
    "Settings",
    "SETTING_DEFINITIONS",
    "NON_EDITABLE_KEYS",
    "resolve_settings",
    "effective_value",
    "get_settings",
    "serialize_for_env",
]
