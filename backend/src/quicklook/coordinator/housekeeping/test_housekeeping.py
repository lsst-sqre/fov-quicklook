import pytest
from datetime import datetime, timedelta
from sqlalchemy import delete, select

from quicklook.coordinator.housekeeping import (
    cleanup_at_startup,
    delete_one_quicklook,
    housekeeping,
    select_quicklook_to_delete,
)
from quicklook.db import Access, Quicklook, get_session
from quicklook.types import VisitName

pytestmark = pytest.mark.slow


@pytest.fixture(autouse=True)
async def reset_db():
    """テスト開始時にDBを全てリセット"""
    async with get_session() as session:
        await session.execute(delete(Access))
        await session.execute(delete(Quicklook))
        await session.commit()


async def test_select_quicklook_to_delete_oldest():
    """最もアクセスが少なく古いquicklookが選択されることを確認"""
    async with get_session() as session:
        # 3つのquicklookを作成
        now = datetime.now()
        quicklook1 = Quicklook(
            visit_name="raw:visit1",
            job_id="job1",
            disk_usage=1000,
            ready=True,
            created_at=now - timedelta(days=3)
        )
        quicklook2 = Quicklook(
            visit_name="raw:visit2",
            job_id="job2",
            disk_usage=2000,
            ready=True,
            created_at=now - timedelta(days=2)
        )
        quicklook3 = Quicklook(
            visit_name="raw:visit3",
            job_id="job3",
            disk_usage=3000,
            ready=True,
            created_at=now - timedelta(days=1)
        )
        session.add_all([quicklook1, quicklook2, quicklook3])
        
        # visit2にアクセス記録を追加
        access = Access(visit_name="raw:visit2", accessed_at=now)
        session.add(access)
        
        await session.commit()
    
    # アクセスがなく最も古いvisit1が選ばれるはず
    result = await select_quicklook_to_delete()
    assert result == "raw:visit1"


async def test_select_quicklook_to_delete_no_ready():
    """ready=falseのquicklookは選択されないことを確認"""
    async with get_session() as session:
        now = datetime.now()
        quicklook1 = Quicklook(
            visit_name="raw:visit1",
            job_id="job1",
            disk_usage=1000,
            ready=False,  # ready=false
            created_at=now - timedelta(days=3)
        )
        quicklook2 = Quicklook(
            visit_name="raw:visit2",
            job_id="job2",
            disk_usage=2000,
            ready=True,
            created_at=now - timedelta(days=1)
        )
        session.add_all([quicklook1, quicklook2])
        await session.commit()
    
    # ready=trueのvisit2が選ばれるはず
    result = await select_quicklook_to_delete()
    assert result == "raw:visit2"


async def test_delete_one_quicklook():
    """quicklookが正しく削除されることを確認"""
    async with get_session() as session:
        now = datetime.now()
        quicklook = Quicklook(
            visit_name="raw:test_delete",
            job_id="job_delete",
            disk_usage=5000,
            ready=True,
            created_at=now
        )
        session.add(quicklook)
        await session.commit()
    
    # 削除を実行
    disk_usage = await delete_one_quicklook("raw:test_delete")
    assert disk_usage == 5000
    
    # DBから削除されていることを確認
    async with get_session() as session:
        stmt = select(Quicklook).where(Quicklook.visit_name == "raw:test_delete")
        result = await session.execute(stmt)
        assert result.first() is None


async def test_cleanup_at_startup():
    """起動時のクリーンアップが動作することを確認"""
    async with get_session() as session:
        now = datetime.now()
        quicklook1 = Quicklook(
            visit_name="raw:incomplete1",
            job_id="job_incomplete1",
            disk_usage=1000,
            ready=False,  # 不完全なエントリー
            created_at=now
        )
        quicklook2 = Quicklook(
            visit_name="raw:complete",
            job_id="job_complete",
            disk_usage=2000,
            ready=True,
            created_at=now
        )
        session.add_all([quicklook1, quicklook2])
        await session.commit()
    
    # クリーンアップを実行
    await cleanup_at_startup()
    
    # ready=falseのエントリーが削除されていることを確認
    async with get_session() as session:
        stmt = select(Quicklook).where(Quicklook.visit_name == "raw:incomplete1")
        result = await session.execute(stmt)
        assert result.first() is None
        
        # ready=trueのエントリーは残っていることを確認
        stmt = select(Quicklook).where(Quicklook.visit_name == "raw:complete")
        result = await session.execute(stmt)
        assert result.first() is not None


async def test_housekeeping_with_limit():
    """容量制限を超えた場合にhousekeepingが動作することを確認"""
    async with get_session() as session:
        now = datetime.now()
        # 合計10000バイトのquicklookを作成
        for i in range(5):
            quicklook = Quicklook(
                visit_name=f"raw:visit{i}",
                job_id=f"job{i}",
                disk_usage=2000,
                ready=True,
                created_at=now - timedelta(days=i)
            )
            session.add(quicklook)
        await session.commit()
    
    # 制限を6000バイトに設定してhousekeepingを実行
    await housekeeping(max_usage=6000)
    
    # 削除後、合計が6000バイト以下になっているはず
    async with get_session() as session:
        stmt = select(Quicklook)
        result = await session.execute(stmt)
        remaining = result.scalars().all()
        total_usage = sum(q.disk_usage for q in remaining)
        assert total_usage <= 6000
