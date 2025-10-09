"""Database models and session tests."""

import pytest
from datetime import datetime
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import create_async_engine

from quicklook.db import Base, Quicklook, Access, get_db_session
from quicklook.config import config


@pytest.fixture
async def setup_database():
    """テスト用のデータベーステーブルを作成・削除"""
    engine = create_async_engine(config.db_url, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


async def test_create_quicklook(setup_database):
    """Quicklookレコードの作成テスト"""
    from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession
    engine = create_async_engine(config.db_url, echo=False)
    session_maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with session_maker() as session:
        quicklook = Quicklook(
            visit_name="test_visit",
            job_id="test_job_001",
            disk_usage=1000000,
            ready=False,
        )
        session.add(quicklook)
        await session.commit()

        result = await session.execute(
            select(Quicklook).where(Quicklook.visit_name == "test_visit")
        )
        saved_quicklook = result.scalar_one()

        assert saved_quicklook.visit_name == "test_visit"
        assert saved_quicklook.job_id == "test_job_001"
        assert saved_quicklook.disk_usage == 1000000
        assert saved_quicklook.ready is False
        assert saved_quicklook.created_at is not None
    
    await engine.dispose()


async def test_create_access(setup_database):
    """Accessレコードの作成テスト"""
    from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession
    engine = create_async_engine(config.db_url, echo=False)
    session_maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with session_maker() as session:
        quicklook = Quicklook(
            visit_name="test_visit_2",
            job_id="test_job_002",
            disk_usage=2000000,
            ready=True,
        )
        session.add(quicklook)
        await session.commit()

        access = Access(
            visit_name="test_visit_2",
            accessed_at=datetime.utcnow(),
        )
        session.add(access)
        await session.commit()

        result = await session.execute(
            select(Access).where(Access.visit_name == "test_visit_2")
        )
        saved_access = result.scalar_one()

        assert saved_access.visit_name == "test_visit_2"
        assert saved_access.accessed_at is not None
    
    await engine.dispose()


async def test_quicklook_with_multiple_accesses(setup_database):
    """1つのQuicklookに複数のAccessを紐付けるテスト"""
    from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession
    engine = create_async_engine(config.db_url, echo=False)
    session_maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with session_maker() as session:
        quicklook = Quicklook(
            visit_name="test_visit_3",
            job_id="test_job_003",
            disk_usage=3000000,
            ready=True,
        )
        session.add(quicklook)
        await session.commit()

        for i in range(3):
            access = Access(
                visit_name="test_visit_3",
                accessed_at=datetime.utcnow(),
            )
            session.add(access)
        await session.commit()

        result = await session.execute(
            select(func.count()).select_from(Access).where(Access.visit_name == "test_visit_3")
        )
        count = result.scalar()

        assert count == 3
    
    await engine.dispose()


async def test_cascade_delete(setup_database):
    """Quicklook削除時にAccessもカスケード削除されることを確認"""
    from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession
    engine = create_async_engine(config.db_url, echo=False)
    session_maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with session_maker() as session:
        quicklook = Quicklook(
            visit_name="test_visit_4",
            job_id="test_job_004",
            disk_usage=4000000,
            ready=True,
        )
        session.add(quicklook)
        await session.commit()

        for i in range(2):
            access = Access(
                visit_name="test_visit_4",
                accessed_at=datetime.utcnow(),
            )
            session.add(access)
        await session.commit()

        result = await session.execute(
            select(Quicklook).where(Quicklook.visit_name == "test_visit_4")
        )
        quicklook_to_delete = result.scalar_one()
        await session.delete(quicklook_to_delete)
        await session.commit()

        access_result = await session.execute(
            select(func.count()).select_from(Access).where(Access.visit_name == "test_visit_4")
        )
        access_count = access_result.scalar()

        assert access_count == 0
    
    await engine.dispose()
