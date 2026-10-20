from __future__ import annotations
import re
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from bot.models.base import Base

_engine = None
_sessionmaker = None


def _async_url(url: str) -> str:
    return re.sub(r"^postgres(ql)?://", "postgresql+asyncpg://", url)


def init_db(database_url: str) -> None:
    global _engine, _sessionmaker
    _engine = create_async_engine(_async_url(database_url), echo=False, poolclass=NullPool)
    _sessionmaker = async_sessionmaker(_engine, class_=AsyncSession, expire_on_commit=False)


async def create_tables() -> None:
    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


@asynccontextmanager
async def get_session() -> AsyncGenerator[AsyncSession, None]:
    if _sessionmaker is None:
        raise RuntimeError("Database not initialized. Call init_db() first.")
    async with _sessionmaker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
