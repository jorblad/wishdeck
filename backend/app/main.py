"""WishDeck FastAPI application entrypoint (12-Factor, stateless)."""
from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1.router import api_router
from app.core.config import get_settings
from app.db.session import AsyncSessionLocal, init_db
from app.core.settings_service import ensure_seed_settings

logging.basicConfig(
    level=os.environ.get("LOG_LEVEL", "INFO"),
    format='%(asctime)s %(levelname)s %(name)s %(message)s',
)
logger = logging.getLogger("wishdeck")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Booting WishDeck %s", get_settings().APP_VERSION)
    # Production deploys run `alembic upgrade head` in the container entrypoint
    # (auto-migration on deploy/upgrade). create_all is idempotent and only
    # creates missing tables, so it is a safe fallback for dev/standalone runs
    # and never conflicts with Alembic on an already-migrated database.
    await init_db()
    async with AsyncSessionLocal() as session:
        await ensure_seed_settings(session)
    yield
    logger.info("Shutdown complete")


app = FastAPI(
    title=get_settings().APP_NAME,
    version=get_settings().APP_VERSION,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    # Wildcard + credentials is rejected by browsers, so list explicit origins.
    allow_origins=os.environ.get(
        "CORS_ORIGINS",
        "http://localhost:9000,http://localhost:8080,http://localhost",
    ).split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)


@app.get("/healthz", tags=["probes"])
async def healthz() -> dict:
    return {"status": "ok"}


@app.get("/readyz", tags=["probes"])
async def readyz() -> Response:
    try:
        async with AsyncSessionLocal() as session:
            await session.execute(__import__("sqlalchemy").text("SELECT 1"))
        return JSONResponse({"status": "ready"})
    except Exception as exc:  # noqa: BLE001
        return JSONResponse({"status": "not ready", "detail": str(exc)}, status_code=503)


@app.get("/", tags=["meta"])
async def root() -> dict:
    return {"app": get_settings().APP_NAME, "version": get_settings().APP_VERSION}


__all__ = ["app"]
