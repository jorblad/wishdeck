"""DB-backed resolution of the hierarchical Settings Engine.

Layer 1 (DB) is read from ``system_settings``; Layer 2 (ENV) wins. This module
exposes helpers used by the settings API and by feature-flag lookups.
"""
from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import SETTING_DEFINITIONS, resolve_settings
from app.models.core import SystemSetting


async def get_db_settings(session: AsyncSession) -> dict[str, Any]:
    """Return {key: raw_string_value} for all persisted settings."""
    rows = await session.execute(select(SystemSetting))
    return {row.key: row.value for row in rows.scalars().all()}


async def get_resolved_settings(session: AsyncSession) -> list[dict[str, Any]]:
    """Resolve ENV over DB and return the full metadata list."""
    db_rows = await get_db_settings(session)
    return resolve_settings(db_rows)


async def get_effective(key: str, session: AsyncSession) -> Any:
    for s in await get_resolved_settings(session):
        if s["key"] == key:
            return s["value"]
    return None


async def ensure_seed_settings(session: AsyncSession) -> None:
    """Seed any missing DB rows from defaults (so the table exists on first run)."""
    existing = await get_db_settings(session)
    for definition in SETTING_DEFINITIONS:
        key = definition["key"]
        if key in existing:
            continue
        session.add(
            SystemSetting(
                key=key,
                value=None,
                value_type=definition["type"],
                description=definition.get("label"),
                is_public=definition.get("public", False),
            )
        )
    await session.flush()


async def update_settings(
    session: AsyncSession, values: dict[str, Any], *, require_editable: bool = True
) -> list[dict[str, Any]]:
    """Persist UI edits. Refuses to touch env-overridden (non-editable) keys."""
    editable = {d["key"] for d in SETTING_DEFINITIONS}
    rows = (await session.execute(select(SystemSetting))).scalars().all()
    by_key = {r.key: r for r in rows}

    for key, value in values.items():
        if require_editable and key not in editable:
            # Never allow the UI to override an env-managed variable.
            continue
        row = by_key.get(key)
        if row is None:
            row = SystemSetting(key=key, value_type="str")
            session.add(row)
            by_key[key] = row
        row.value = None if value is None else str(value)
        row.value_type = next(
            (d["type"] for d in SETTING_DEFINITIONS if d["key"] == key), "str"
        )

    await session.flush()
    return await get_resolved_settings(session)


__all__ = [
    "get_db_settings",
    "get_resolved_settings",
    "get_effective",
    "ensure_seed_settings",
    "update_settings",
]
