import asyncio
import logging
from dataclasses import dataclass
from typing import Callable

import aiohttp
from sqlalchemy import select, update

from quicklook.config import config
from quicklook.coordinator.quicklookjob.job import QuicklookJob, QuicklookJobPhase
from quicklook.db import db_context
from quicklook.models import QuicklookRecord
from quicklook.types import GeneratorPod
from quicklook.utils.orderedsemaphore import OrderedSemaphore

from .job_generate import job_generate
from .job_merge import job_merge
from .job_transfer import job_transfer

logger = logging.getLogger(f'uvicorn.{__name__}')

cleanup_delay = 1 if config.environment == 'test' else 30
# テスト時は0にしたいのだが、ここを0にするとfrontendプロセスが止まらなくなってしまう。
# 詳しくはREADME.ja.mdのtouble shootingを参照


class QuicklookJobRunner:
    def __init__(
        self,
        *,
        job_sync: 'JobSynchronizer',
    ):
        self._job_sync = job_sync
        self._ram_limit = OrderedSemaphore(config.job_max_ram_limit_stage)
        self._disk_limit = OrderedSemaphore(config.job_max_disk_limit_stage)

    async def enqueue(self, job: QuicklookJob):
        await self.run(job)

    async def run(self, job: QuicklookJob):
        async with self._disk_limit:
            try:
                async with self._ram_limit:
                    await job_generate(job, self._job_sync.sync)
                    _update_job_record(job, 'in_progress')
                    await job_merge(job, self._job_sync.sync)
                if not job.no_transfer: # デバッグ用
                    await job_transfer(job, self._job_sync.sync)
                    job.phase = QuicklookJobPhase.READY
                    self._job_sync.sync(job)
                    _update_job_record(job, 'ready')
            except Exception:
                job.phase = QuicklookJobPhase.FAILED
                raise
            else:
                job.phase = QuicklookJobPhase.READY
            finally:
                self._job_sync.sync(job)

                async def a():
                    await asyncio.sleep(cleanup_delay)
                    self._job_sync.unlink(job)

                async def b():
                    await cleanup(job)

                await asyncio.gather(a(), b())


@dataclass
class JobSynchronizer:
    sync: Callable[[QuicklookJob], None]
    unlink: Callable[[QuicklookJob], None]


async def cleanup(job: QuicklookJob):
    async def run_1_task(g: GeneratorPod):
        async with aiohttp.ClientSession() as session:
            async with session.delete(
                f'http://{g.host}:{g.port}/quicklooks/{job.visit.id}',
                raise_for_status=True,
            ) as _:
                pass

    logger.info(f'cleanup: {job.visit.id}')
    assert job.ccd_generator_map
    generators = [*set(job.ccd_generator_map.values())]
    await asyncio.gather(*(run_1_task(g) for g in generators))


def _update_job_record(job: QuicklookJob, phase: QuicklookRecord.Phase):
    with db_context() as db:
        with db.begin():
            stmt = select(QuicklookRecord).where(QuicklookRecord.id == job.visit.id)
            record = db.execute(stmt).scalar_one_or_none()

            if record:
                stmt = update(QuicklookRecord).where(QuicklookRecord.id == job.visit.id).values(phase=phase)
                db.execute(stmt)
            else:
                db.add(QuicklookRecord(id=job.visit.id, phase=phase))
            # No need for explicit commit, it's handled by the transaction
