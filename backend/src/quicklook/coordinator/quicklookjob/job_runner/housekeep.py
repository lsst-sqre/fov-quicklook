import asyncio
from datetime import datetime, timedelta
import logging
from typing import Iterable

import aiohttp
from sqlalchemy import delete
from sqlalchemy import func as sql_func
from sqlalchemy import select, update

from quicklook import storage
from quicklook.config import config
from quicklook.coordinator.quicklookjob.job import QuicklookJob
from quicklook.db import db_context
from quicklook.models import QuicklookRecord
from quicklook.types import GeneratorPod, Visit
from quicklook.utils.timeit import timeit


logger = logging.getLogger(f'uvicorn.{__name__}')


async def housekeep():
    for visit in _iter_expired_records():
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


def _iter_expired_records() -> Iterable[Visit]:
    with db_context() as db:
        # 1. phaseがreadyでconfig.max_storage_entries番目より古いものを取得
        ready_subquery = (
            # this comment prevents automatic formatting
            select(QuicklookRecord.id)
            .where(QuicklookRecord.phase == 'ready')
            .order_by(QuicklookRecord.created_at)
            .limit(config.max_storage_entries)
            .subquery()
        )

        ready_records = (
            db.execute(
                select(QuicklookRecord).where(
                    # this comment prevents automatic formatting
                    (QuicklookRecord.phase == 'ready')
                    & (~QuicklookRecord.id.in_(select(ready_subquery.c.id)))
                )
            )
            .scalars()
            .all()
        )

        # 2. phaseがreadyでなくupdated_atが1時間以上前のものを取得
        cutoff = datetime.now() - timedelta(hours=1)
        not_ready_records = db.execute(select(QuicklookRecord).where((QuicklookRecord.phase != 'ready') & (QuicklookRecord.updated_at <= cutoff))).scalars().all()

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
        await asyncio.gather(*(run_1_task(g) for g in generators))

        if storage_tile:
            await asyncio.to_thread(lambda: storage.remove_visit_data(job.visit))

        if db_entry:
            with db_context() as db:
                stmt = delete(QuicklookRecord).where(QuicklookRecord.id == job.visit.id)
                db.execute(stmt)
                db.commit()
