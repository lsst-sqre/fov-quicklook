"""Housekeeping functions for managing object storage capacity."""

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta

from sqlalchemy import delete, func, select

from quicklook.config import config
from quicklook.db import Access, Quicklook, get_db_session
from quicklook.object_storage import VisitObjectStorage, delete_cache_version, list_cache_versions
from quicklook.types import VisitName

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class StaleCacheCleanupPlan:
    stale_versions: frozenset[int]
    deleted_quicklook_count: int


async def prepare_stale_cache_cleanup() -> StaleCacheCleanupPlan:
    """Delete stale DB cache entries and return stale object-storage versions to clean in background."""
    current_version = config.tile_cache_schema_version

    async with get_db_session() as session:
        stale_rows = (
            await session.execute(
                select(Quicklook.visit_name, Quicklook.cache_version).where(Quicklook.cache_version != current_version)
            )
        ).all()
        stale_visits = [row[0] for row in stale_rows]
        stale_versions = {row[1] for row in stale_rows}

        if stale_visits:
            await session.execute(delete(Access).where(Access.visit_name.in_(stale_visits)))
            await session.execute(delete(Quicklook).where(Quicklook.visit_name.in_(stale_visits)))
            await session.commit()

    stale_versions |= list_cache_versions() - {current_version}
    if stale_versions or stale_visits:
        logger.info(
            "Prepared stale cache cleanup current_version=%d stale_versions=%s deleted_quicklooks=%d",
            current_version,
            sorted(stale_versions),
            len(stale_visits),
        )
    else:
        logger.info("No stale cache versions found at startup")

    return StaleCacheCleanupPlan(
        stale_versions=frozenset(stale_versions),
        deleted_quicklook_count=len(stale_visits),
    )


async def delete_stale_cache_versions(stale_versions: set[int] | frozenset[int]) -> None:
    if not stale_versions:
        return

    for cache_version in sorted(stale_versions):
        logger.info("Deleting stale cache version prefix version=%d", cache_version)
        delete_cache_version(cache_version)
    logger.info("Finished deleting stale cache versions: %s", sorted(stale_versions))


async def select_quicklook_to_delete() -> str | None:
    """
    削除すべきquicklookを1つ選択する。
    
    選択ロジック:
    1. ready=trueのquicklookの総数がN個（config.housekeeping_keep_recent_count）以下の場合は、何も削除しない
    2. N個を超える場合、最新のN個は保護し、残りの中から最近1週間以内のアクセスが少ないもの順、それが同じならcreated_atが古いもの順で選択
    
    これにより、アクセス頻度が高いものだけが残った場合でも新しいデータを追加できる。
    """
    async with get_db_session() as session:
        one_week_ago = datetime.now() - timedelta(days=7)

        # ready=trueのquicklook総数を取得
        total_count_stmt = select(func.count()).select_from(Quicklook).where(Quicklook.ready == True)
        total_count_result = await session.execute(total_count_stmt)
        total_count = total_count_result.scalar() or 0
        
        # 総数が保護数以下の場合は削除しない
        if total_count <= config.housekeeping_keep_recent_count:
            return None

        # 最新のN個のvisit_nameを取得（これらは削除候補から除外）
        recent_visits_stmt = (
            select(Quicklook.visit_name)
            .where(Quicklook.ready == True)
            .order_by(Quicklook.created_at.desc())
            .limit(config.housekeeping_keep_recent_count)
        )
        recent_visits_result = await session.execute(recent_visits_stmt)
        protected_visits = {row[0] for row in recent_visits_result.all()}

        # 1週間以内のアクセス数をカウント
        recent_access_count = (
            select(Access.visit_name, func.count(Access.id).label('access_count'))
            .where(Access.accessed_at >= one_week_ago)
            .group_by(Access.visit_name)
            .subquery()
        )

        # quicklooksとjoinして、保護されていないものの中からアクセス数が少ない順、created_atが古い順でソート
        stmt = (
            select(Quicklook.visit_name)
            .outerjoin(recent_access_count, Quicklook.visit_name == recent_access_count.c.visit_name)
            .where(Quicklook.ready == True)
        )
        
        if protected_visits:
            stmt = stmt.where(Quicklook.visit_name.notin_(protected_visits))
        
        stmt = stmt.order_by(func.coalesce(recent_access_count.c.access_count, 0).asc(), Quicklook.created_at.asc()).limit(1)

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
        cache_version = quicklook.cache_version
        quicklook.ready = False
        await session.commit()
        logger.info(f"Marked quicklook {visit_name} as not ready")

    # object storageのデータを削除
    storage = VisitObjectStorage.from_visit(VisitName(visit_name), cache_version=cache_version)
    await storage.delete_all()
    logger.info(f"Deleted object storage data for {visit_name}")

    # DBエントリーを削除（ORMを使ってカスケード削除）
    async with get_db_session() as session:
        stmt = select(Quicklook).where(Quicklook.visit_name == visit_name)
        result = await session.execute(stmt)
        quicklook_to_delete = result.scalar_one_or_none()
        
        if quicklook_to_delete:
            await session.delete(quicklook_to_delete)
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


_housekeeping_lock = asyncio.Lock()


async def run_housekeeping(max_usage: int | None = None) -> None:
    async with _housekeeping_lock:
        await run_housekeeping_without_lock(max_usage)


async def run_housekeeping_without_lock(max_usage: int | None = None) -> None:
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
