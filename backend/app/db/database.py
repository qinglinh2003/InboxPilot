"""Async SQLAlchemy engine, session factory, and lifecycle helpers.

Uses lazy initialization so that the engine is not created at import
time — this avoids failures when environment variables are not yet set
(e.g. during test collection).

Usage in FastAPI::

    @app.on_event("startup")
    async def on_startup() -> None:
        await init_db()

    @app.get("/example")
    async def example(db: AsyncSession = Depends(get_db)):
        ...
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from functools import lru_cache

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.config import get_settings


@lru_cache(maxsize=1)
def _get_engine() -> AsyncEngine:
    """Create and cache the async SQLAlchemy engine."""
    return create_async_engine(
        get_settings().DATABASE_URL,
        echo=False,
        future=True,
    )


@lru_cache(maxsize=1)
def _get_session_factory() -> async_sessionmaker[AsyncSession]:
    """Create and cache the async session factory."""
    return async_sessionmaker(
        bind=_get_engine(),
        class_=AsyncSession,
        expire_on_commit=False,
    )


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Yield an async DB session and ensure it is closed afterward.

    Designed for use as a FastAPI ``Depends()`` dependency.
    """
    session_factory = _get_session_factory()
    async with session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def init_db() -> None:
    """Create all tables that do not yet exist.

    Imports ``Base`` from :mod:`app.db.models` so every registered ORM
    model is picked up by ``metadata.create_all``.
    """
    from app.db.models import Base  # noqa: F811 — intentional lazy import

    engine = _get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
