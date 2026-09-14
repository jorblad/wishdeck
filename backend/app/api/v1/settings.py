"""Settings API — exposes the hybrid ENV/DB resolution to the frontend."""
from __future__ import annotations

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, require_admin
from app.core.config import NON_EDITABLE_KEYS
from app.core.settings_service import (
    ensure_seed_settings,
    get_resolved_settings,
    update_settings,
)
from app.db.session import get_session
from app.models.core import User
from app.schemas import SettingsResponse, SettingsUpdate

router = APIRouter(prefix="/settings", tags=["settings"])


@router.get("/public", summary="Public effective settings (no auth)")
async def public_settings(
    session: AsyncSession = Depends(get_session),
) -> dict:
    """Return only the *public* settings with their effective values.

    The effective value already honours ENV > UI/DB > default, so the frontend
    can read e.g. ``DEFAULT_LOCALE`` regardless of where it was configured.
    """
    settings = await get_resolved_settings(session)
    return {s["key"]: s["value"] for s in settings if s.get("public")}


@router.get("", response_model=SettingsResponse)
async def list_settings(
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
) -> SettingsResponse:
    """Return every setting with its effective value, source and env-override flag."""
    await ensure_seed_settings(session)
    settings = await get_resolved_settings(session)
    # Hide sensitive values (secrets) for non-admins but keep metadata.
    if user.role.value != "admin":
        settings = [
            {**s, "value": ("••••••" if s["key"] in _SENSITIVE else s["value"])}
            for s in settings
        ]
    return SettingsResponse(settings=settings)


@router.put("", response_model=SettingsResponse, status_code=status.HTTP_200_OK)
async def update_ui_settings(
    payload: SettingsUpdate,
    session: AsyncSession = Depends(get_session),
    _admin: User = Depends(require_admin),
) -> SettingsResponse:
    """Persist UI edits. Env-overridden keys are silently ignored server-side."""
    updated = await update_settings(session, payload.values, require_editable=True)
    return SettingsResponse(settings=updated)


_SENSITIVE = {"OIDC_CLIENT_SECRET", "SECRET_KEY"}

__all__ = ["router", "NON_EDITABLE_KEYS"]
