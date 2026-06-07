"""Async SQLAlchemy 2.0 engine + session (Postgres only).

The dual SQLite/Postgres wrapper from the old `server/` is gone — one database,
one driver (asyncpg). Schema lives in `app/models/orm.py`; migrations in Alembic.
"""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.config import get_settings

logger = logging.getLogger(__name__)


class Base(DeclarativeBase):
    """Declarative base for all ORM models."""


_engine = None
_sessionmaker: async_sessionmaker[AsyncSession] | None = None


def get_engine():
    global _engine
    if _engine is None:
        settings = get_settings()
        _engine = create_async_engine(
            settings.database_url,
            echo=False,
            pool_pre_ping=True,
        )
    return _engine


def get_sessionmaker() -> async_sessionmaker[AsyncSession]:
    global _sessionmaker
    if _sessionmaker is None:
        _sessionmaker = async_sessionmaker(
            get_engine(), expire_on_commit=False, class_=AsyncSession
        )
    return _sessionmaker


async def get_session() -> AsyncIterator[AsyncSession]:
    """FastAPI dependency — yields a session and commits/rolls back around the request."""
    async with get_sessionmaker()() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def ping() -> bool:
    """Lightweight connectivity check for startup/health."""
    from sqlalchemy import text
    async with get_sessionmaker()() as session:
        await session.execute(text("SELECT 1"))
    return True


async def create_tables() -> None:
    """Create any missing tables from the ORM metadata (idempotent).

    Used at startup instead of Alembic — the schema is single-version for now.
    Reintroduce Alembic when the schema needs versioned migrations in production.
    """
    import app.models.orm  # noqa: F401 — register tables on Base.metadata
    from sqlalchemy import text

    async with get_engine().begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        # Additive, idempotent column migrations (Postgres). Keeps existing data
        # while the schema evolves; reintroduce Alembic for anything non-additive.
        await conn.execute(
            text("ALTER TABLE assets ADD COLUMN IF NOT EXISTS owner VARCHAR(128)")
        )
        await conn.execute(
            text("ALTER TABLE reports ADD COLUMN IF NOT EXISTS content BYTEA")
        )
        await conn.execute(
            text("ALTER TABLE assets ADD COLUMN IF NOT EXISTS issuer_name VARCHAR(255)")
        )
        # Normalise coupon rates to the canonical fraction form (0.04 == 4%).
        # Idempotent: once a 4.0 row becomes 0.04 it is <= 1 and is skipped.
        # No real coupon exceeds 100%, so >1 reliably flags whole-percent rows.
        await conn.execute(
            text("UPDATE assets SET coupon_rate = coupon_rate / 100 WHERE coupon_rate > 1")
        )
