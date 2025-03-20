from quicklook import storage
from quicklook.mutableconfig import mutable_config
import asyncio
import logging
from dataclasses import dataclass
from typing import Callable

import aiohttp
from sqlalchemy import select, update

from quicklook.config import config
from quicklook.coordinator.api import mutable_config_route
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
        test_skip = False
        async with self._disk_limit:
            try:
                async with self._ram_limit:
                    await job_generate(job, self._job_sync.sync)

                    _update_job_record_phase(job, 'in_progress')
                    storage.put_quicklook_job_config(job)

                    if mutable_config.job_stop_at == 'GENERATE_DONE':
                        self._update_job_phase(job, QuicklookJobPhase.GENERATE_DONE)
                        raise JobSkipForTest

                    await job_merge(job, self._job_sync.sync)
                    if mutable_config.job_stop_at == 'MERGE_DONE':
                        self._update_job_phase(job, QuicklookJobPhase.MERGE_DONE)
                        raise JobSkipForTest

                # await job_transfer(job, self._job_sync.sync)

                job.phase = QuicklookJobPhase.READY
                self._update_job_phase(job, QuicklookJobPhase.READY)
                _update_job_record_phase(job, 'ready')
            except JobSkipForTest:
                # This is a special exception for testing purposes
                test_skip = True
            except Exception:
                self._update_job_phase(job, QuicklookJobPhase.FAILED)
                raise
            else:
                self._update_job_phase(job, QuicklookJobPhase.READY)
            finally:
                if test_skip:
                    await asyncio.sleep(1)
                    self._job_sync.sync(job)  # この２行はテストが終わるために必要。理由はよくわからない
                    return

                async def delay_unlink_job():
                    await asyncio.sleep(cleanup_delay)
                    self._job_sync.unlink(job)

                await asyncio.gather(delay_unlink_job(), cleanup(job))

    def _update_job_phase(self, job: QuicklookJob, phase: QuicklookJobPhase):
        job.phase = phase
        self._job_sync.sync(job)


class JobSkipForTest(RuntimeError): ...


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


def _update_job_record_phase(job: QuicklookJob, phase: QuicklookRecord.Phase):
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
