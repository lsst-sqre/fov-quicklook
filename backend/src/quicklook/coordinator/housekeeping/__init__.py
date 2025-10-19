"""Housekeeping functions for managing object storage capacity."""

import logging
from datetime import datetime, timedelta

from sqlalchemy import delete, func, select

from quicklook.config import config
from quicklook.db import Access, Quicklook, get_db_session
from quicklook.object_storage import VisitObjectStorage
from quicklook.types import VisitName

logger = logging.getLogger(__name__)


async def select_quicklook_to_delete() -> str | None:
    """
    削除すべきquicklookを1つ選択する。
    最近1週間以内のアクセスが少ないもの順、それが同じならcreated_atが古いもの順。
    """
    async with get_db_session() as session:
        one_week_ago = datetime.now() - timedelta(days=7)

        # 1週間以内のアクセス数をカウント
        recent_access_count = (
            select(Access.visit_name, func.count(Access.id).label('access_count'))
            .where(Access.accessed_at >= one_week_ago)
            .group_by(Access.visit_name)
            .subquery()
        )

        # quicklooksとjoinして、アクセス数が少ない順、created_atが古い順でソート
        stmt = (
            select(Quicklook.visit_name)
            .outerjoin(recent_access_count, Quicklook.visit_name == recent_access_count.c.visit_name)
            .where(Quicklook.ready == True)  # ready=trueのもののみ対象
            .order_by(func.coalesce(recent_access_count.c.access_count, 0).asc(), Quicklook.created_at.asc())
            .limit(1)
        )

        result = await session.execute(stmt)
        row = result.first()
        return row[0] if row else None


async def delete_one_quicklook(visit_name: str) -> int:
    """
    指定されたquicklookを削除する。
    1. ready=falseに更新
    2. object storageのデータを削除
    3. DBエントリーを削除

    Returns:
        削除されたdisk_usage（bytes）
    """
    # ready=falseに更新
    async with get_db_session() as session:
        stmt = select(Quicklook).where(Quicklook.visit_name == visit_name)
        result = await session.execute(stmt)
        quicklook = result.scalar_one_or_none()

        if not quicklook:
            logger.warning(f"Quicklook {visit_name} not found for deletion")
            return 0

        disk_usage = quicklook.disk_usage
        quicklook.ready = False
        await session.commit()
        logger.info(f"Marked quicklook {visit_name} as not ready")

    # object storageのデータを削除
    storage = VisitObjectStorage(visit=VisitName(visit_name))
    await storage.delete_all()
    logger.info(f"Deleted object storage data for {visit_name}")

    # DBエントリーを削除
    async with get_db_session() as session:
        stmt = delete(Quicklook).where(Quicklook.visit_name == visit_name)
        await session.execute(stmt)
        await session.commit()
        logger.info(f"Deleted quicklook record for {visit_name}")

    return disk_usage


async def get_total_disk_usage() -> int:
    """現在のobject storageの総使用量を取得（bytes）"""
    async with get_db_session() as session:
        stmt = select(func.sum(Quicklook.disk_usage)).where(Quicklook.ready == True)
        result = await session.execute(stmt)
        total = result.scalar()
        return total if total is not None else 0


async def run_housekeeping(max_usage: int | None = None) -> None:
    """
    object storage容量管理のためのハウスキーピング。
    設定された上限を超えている場合、古いquicklookを削除する。

    Args:
        max_usage: テスト用の容量上限（指定しない場合はconfigの値を使用）
    """
    max_usage_limit = max_usage if max_usage is not None else config.max_object_storage_usage
    total_usage = await get_total_disk_usage()
    logger.info(f"Current object storage usage: {total_usage:,} bytes ({total_usage / 1024**3:.2f} GB)")

    if total_usage <= max_usage_limit:
        logger.info(f"Usage is within limit ({max_usage_limit:,} bytes), no housekeeping needed")
        return

    logger.info(f"Usage exceeds limit, starting housekeeping...")
    deleted_count = 0

    while total_usage > max_usage_limit:
        visit_name = await select_quicklook_to_delete()
        if not visit_name:
            logger.warning("No more quicklooks to delete, but still over limit")
            break

        freed_space = await delete_one_quicklook(visit_name)
        total_usage -= freed_space
        deleted_count += 1

        logger.info(
            f"Deleted quicklook {visit_name}, freed {freed_space:,} bytes. "
            f"Total usage now: {total_usage:,} bytes ({total_usage / 1024**3:.2f} GB)"
        )

    logger.info(f"Housekeeping completed. Deleted {deleted_count} quicklook(s)")


async def cleanup_at_startup() -> None:
    """
    起動時のクリーンアップ。
    ready=falseのquicklookエントリーを見つけて、関連データを削除する。
    """
    async with get_db_session() as session:
        stmt = select(Quicklook.visit_name).where(Quicklook.ready == False)
        result = await session.execute(stmt)
        unready_visits = [row[0] for row in result.all()]

    if not unready_visits:
        logger.info("No unready quicklooks found at startup")
        return

    logger.info(f"Found {len(unready_visits)} unready quicklook(s) at startup, cleaning up...")

    for visit_name in unready_visits:
        logger.info(f"Cleaning up unready quicklook: {visit_name}")
        await delete_one_quicklook(visit_name)

    logger.info(f"Startup cleanup completed. Cleaned {len(unready_visits)} quicklook(s)")
