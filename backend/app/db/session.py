from __future__ import annotations

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool

from app.core.config import get_settings

settings = get_settings()

_is_sqlite = settings.DATABASE_URL.startswith("sqlite")

# SQLite needs tuned connect args; pooling args are only valid for server DBs.
_engine_kwargs: dict = {
    "echo": settings.ENVIRONMENT == "development",
}
if _is_sqlite:
    _engine_kwargs["poolclass"] = NullPool
    _engine_kwargs["connect_args"] = {"timeout": 10, "check_same_thread": False}
else:
    _engine_kwargs["pool_size"] = settings.DB_POOL_SIZE
    _engine_kwargs["max_overflow"] = settings.DB_MAX_OVERFLOW

_engine = create_async_engine(settings.DATABASE_URL, **_engine_kwargs)

AsyncSessionLocal = async_sessionmaker(
    bind=_engine, class_=AsyncSession, expire_on_commit=False, autoflush=False
)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency yielding a transactional session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def init_db() -> None:
    """Create tables (dev/container bootstrap). Alembic owns migrations in prod."""
    from app.db.base import Base
    import app.models  # noqa: F401  (register models on Base.metadata)

    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


__all__ = ["AsyncSessionLocal", "get_session", "init_db", "_engine"]
