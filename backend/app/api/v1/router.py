from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.api.v1 import auth, settings, shares, users, utils, wishlists
from app.core.config import get_settings
from app.db.session import AsyncSessionLocal

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(auth.router)
api_router.include_router(settings.router)
api_router.include_router(wishlists.router)
api_router.include_router(shares.router)
api_router.include_router(users.router)
api_router.include_router(utils.router)


@api_router.get("/", tags=["meta"])
async def api_root() -> dict:
    settings = get_settings()
    return {"app": settings.APP_NAME, "version": settings.APP_VERSION}


@api_router.get("/healthz", tags=["probes"])
async def healthz() -> dict:
    return {"status": "ok"}


@api_router.get("/readyz", tags=["probes"])
async def readyz() -> JSONResponse:
    try:
        async with AsyncSessionLocal() as session:
            await session.execute(text("SELECT 1"))
        return JSONResponse({"status": "ready"})
    except Exception:
        return JSONResponse({"status": "not ready"}, status_code=503)


__all__ = ["api_router"]
