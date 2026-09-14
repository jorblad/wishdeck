from __future__ import annotations

from fastapi import APIRouter

from app.api.v1 import auth, settings, utils, wishlists

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(auth.router)
api_router.include_router(settings.router)
api_router.include_router(wishlists.router)
api_router.include_router(utils.router)

__all__ = ["api_router"]
