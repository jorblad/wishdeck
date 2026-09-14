"""Shared pytest fixtures: isolated SQLite DB per test + ASGI client."""
from __future__ import annotations

import os

# Configure the app for the test environment BEFORE importing it.
os.environ.setdefault("ENVIRONMENT", "test")
os.environ.setdefault("SECRET_KEY", "test-secret-key-not-for-production")
os.environ.setdefault("COOKIE_SECURE", "false")  # cookies must flow over http in tests

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.db.base import Base
from app.db.session import get_session
from app.main import app


@pytest_asyncio.fixture
async def engine(tmp_path):
    db_file = tmp_path / "test.db"
    eng = create_async_engine(f"sqlite+aiosqlite:///{db_file}", echo=False)
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield eng
    await eng.dispose()


@pytest_asyncio.fixture
async def session_factory(engine):
    return async_sessionmaker(engine, expire_on_commit=False)


@pytest_asyncio.fixture
async def client(session_factory):
    async def _override_get_session():
        async with session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    app.dependency_overrides[get_session] = _override_get_session
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()


async def register_and_login(client: AsyncClient, email="owner@example.com", password="S3cret!!") -> None:
    await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password, "full_name": "Owner"},
    )
    await client.post("/api/v1/auth/login", json={"username": email, "password": password})
