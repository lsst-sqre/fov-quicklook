import asyncio
import logging
from datetime import datetime, timedelta
from typing import Iterable

import aiohttp
from sqlalchemy import delete, select, update

from quicklook import storage
from quicklook.config import config
from quicklook.coordinator.quicklookjob.job import QuicklookJob
from quicklook.db import db_context
from quicklook.models import QuicklookRecord
from quicklook.types import GeneratorPod, Visit
from quicklook.utils.timeit import timeit

logger = logging.getLogger(f'uvicorn.{__name__}')


async def housekeep(expiration_threshold: datetime | None = None):
    if expiration_threshold is None:
        expiration_threshold = datetime.now() - timedelta(minutes=5)
    for visit in _iter_expired_records(expiration_threshold):
        await _delete_visit(visit)


async def _delete_visit(visit: Visit):
    with timeit(f'housekeep {visit.id}'):
        with db_context() as db:
            db.execute(
                update(QuicklookRecord).where(QuicklookRecord.id == visit.id).values(phase='deleting'),
            )
            db.commit()
        await asyncio.to_thread(lambda: storage.remove_visit_data(visit))
        with db_context() as db:
            db.execute(
                delete(QuicklookRecord).where(QuicklookRecord.id == visit.id),
            )
            db.commit()


async def clear_imcomplete_quicklooks():
    '''
    delete quicklook recoreds that are not in the ready state
    '''
    with db_context() as db:
        imcplete_quicklooks = (
            db.execute(
                select(QuicklookRecord).where(
                    QuicklookRecord.phase != 'ready',
                )
            )
            .scalars()
            .all()
        )
        for record in imcplete_quicklooks:
            with timeit(f'clear_imcomplete_quicklooks {record.id}'):
                await remove_storage_and_db_entry(
                    Visit.from_id(record.id),
                    storage_tile=True,
                    db_entry=True,
                )
    await remove_dangling_tiles()


def _iter_expired_records(expiration_threshold: datetime) -> Iterable[Visit]:
    with db_context() as db:
        # 1. phaseがreadyのレコードを新しい順に取得し、config.max_storage_entries以降を削除対象にする
        # 新しいものを保持するために、作成日時の降順でソート
        recent_ready_subquery = select(QuicklookRecord.id).where(QuicklookRecord.phase == 'ready').order_by(QuicklookRecord.created_at.desc()).limit(config.max_storage_entries).subquery()  # 降順ソートで新しいものを先頭に

        # ready状態だが、保持する最新のconfig.max_storage_entries件には含まれないもの
        ready_records = db.execute(select(QuicklookRecord).where((QuicklookRecord.phase == 'ready') & (~QuicklookRecord.id.in_(select(recent_ready_subquery.c.id))))).scalars().all()

        # 2. phaseがreadyでなくupdated_atがexpiration_thresholdより前のものを取得
        not_ready_records = db.execute(select(QuicklookRecord).where((QuicklookRecord.phase != 'ready') & (QuicklookRecord.updated_at <= expiration_threshold))).scalars().all()

        # 両方の結果を結合
        all_expired_records: Iterable[QuicklookRecord] = ready_records + not_ready_records  # type: ignore

    # 結果をyield
    for record in all_expired_records:
        yield Visit.from_id(record.id)


async def cleanup_job(
    job: QuicklookJob,
    *,
    tmp_tile: bool = False,
    merged_tile: bool = False,
    storage_tile: bool = False,
    db_entry: bool = False,
):
    async def run_1_task(g: GeneratorPod):
        async with aiohttp.ClientSession() as session:
            async with session.delete(
                f'http://{g.host}:{g.port}/quicklooks/{job.visit.id}',
                json={'tmp_tile': tmp_tile, 'merged_tile': merged_tile},
                raise_for_status=True,
            ) as _:
                pass

    with timeit(f'cleanup_job {job.visit.id}'):
        assert job.ccd_generator_map
        generators = [*set(job.ccd_generator_map.values())]
        try:
            await asyncio.gather(*(run_1_task(g) for g in generators))
        except Exception as e:
            logger.exception(f'cleanup_job failed: {job.visit.id} {e}')

        visit = job.visit

        if storage_tile:
            await asyncio.to_thread(lambda: storage.remove_visit_data(visit))

        if db_entry:
            with db_context() as db:
                stmt = delete(QuicklookRecord).where(QuicklookRecord.id == visit.id)
                db.execute(stmt)
                db.commit()


async def remove_dangling_tiles():
    with timeit('remove_dangling_tiles'):
        # ストレージ内の全てのquicklookを取得
        existing_tiles = set(storage.list_quicklooks())

        # データベース内の全てのQuicklookRecordのIDを取得
        with db_context() as db:
            db_records = db.execute(select(QuicklookRecord.id)).scalars().all()
            db_visits = {Visit.from_id(record_id) for record_id in db_records}

        # ストレージには存在するがデータベースには存在しないタイルを特定
        dangling_visits = existing_tiles - db_visits

        # 孤立したタイルを削除
        for visit in dangling_visits:
            logger.info(f"Removing dangling tiles for visit {visit.id}")
            await asyncio.to_thread(lambda v=visit: storage.remove_visit_data(v))


async def remove_storage_and_db_entry(
    visit: Visit,
    *,
    storage_tile: bool = False,
    db_entry: bool = False,
):
    """
    指定されたVisitのストレージデータとDBエントリを削除する汎用関数
    """
    with timeit(f'remove_storage_and_db_entry {visit.id}'):
        if storage_tile:
            await asyncio.to_thread(lambda: storage.remove_visit_data(visit))

        if db_entry:
            with db_context() as db:
                stmt = delete(QuicklookRecord).where(QuicklookRecord.id == visit.id)
                db.execute(stmt)
                db.commit()
