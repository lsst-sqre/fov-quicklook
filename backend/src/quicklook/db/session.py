"""Database session management for async SQLAlchemy."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool

from quicklook.config import config


_engine: AsyncEngine | None = None
_async_session_maker: async_sessionmaker[AsyncSession] | None = None


def get_engine() -> AsyncEngine:
    global _engine
    if _engine is None:
        # テスト環境ではNullPoolを使用して接続プールを無効化
        poolclass = NullPool if config.environment == "test" else None
        _engine = create_async_engine(
            config.db_url,
            echo=config.log_level == "debug",
            pool_pre_ping=True,
            poolclass=poolclass,
        )
    return _engine


def get_session_maker() -> async_sessionmaker[AsyncSession]:
    global _async_session_maker
    if _async_session_maker is None:
        _async_session_maker = async_sessionmaker(
            get_engine(),
            class_=AsyncSession,
            expire_on_commit=False,
        )
    return _async_session_maker


@asynccontextmanager
async def get_session() -> AsyncIterator[AsyncSession]:
    session_maker = get_session_maker()
    async with session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def close_engine():
    global _engine
    if _engine is not None:
        await _engine.dispose()
        _engine = None
