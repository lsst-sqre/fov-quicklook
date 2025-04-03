import asyncio
import logging
from contextlib import asynccontextmanager, contextmanager
from typing import AsyncGenerator, Callable

from sqlalchemy import select, update

from quicklook import storage
from quicklook.config import config
from quicklook.coordinator.quicklookjob.job import QuicklookJob, QuicklookJobPhase
from quicklook.coordinator.quicklookjob.job_runner.housekeep import cleanup_job
from quicklook.db import db_context
from quicklook.models import QuicklookRecord
from quicklook.mutableconfig import mutable_config
from quicklook.types import Visit
from quicklook.utils.event import WatchEvent
from quicklook.utils.orderedsemaphore import OrderedSemaphore

from ..job import QuicklookJob, QuicklookJobPhase, QuicklookJobReport
from ..job_generate import job_generate
from ..job_merge import job_merge
from ..job_transfer import job_transfer
from .housekeep import housekeep
from .JobSynchronizer import JobSynchronizer

logger = logging.getLogger(f'uvicorn.{__name__}')

cleanup_delay = 1 if config.environment == 'test' else 5
# テスト時は0にしたいのだが、ここを0にするとfrontendプロセスが止まらなくなってしまう。
# 詳しくはREADME.ja.mdのtouble shootingを参照


class PseudoErrorForTest(RuntimeError): ...


class JobRunner:
    def __init__(self):
        self._synchronizer = JobSynchronizer()
        self._ram_limit = OrderedSemaphore(config.job_max_ram_limit_stage)
        self._disk_limit = OrderedSemaphore(config.job_max_disk_limit_stage)
        self._transfer_limit = OrderedSemaphore(2)
        self._housekeep_limit = OrderedSemaphore(1)

    async def enqueue(self, visit: Visit):
        if not self._synchronizer.has(visit) and not _db_has(visit):  # pragma: no branch
            job = QuicklookJob(visit=visit, phase=QuicklookJobPhase.QUEUED)
            self._synchronizer.add(job)
            await self.run(job)

    def subscribe(self) -> AsyncGenerator[list[WatchEvent[QuicklookJobReport]], None]:
        return self._synchronizer.subscribe()

    async def run(self, job: QuicklookJob):
        pseoudo_error = False
        try:
            await self._run_job_main_flow(job)
        except PseudoErrorForTest:
            # This is a special exception for testing purposes
            pseoudo_error = True
        except Exception as e:
            self._update_job_phase(job, QuicklookJobPhase.FAILED)
            logger.exception(f'Job failed: {job.visit.id}')
            await cleanup_job(job, tmp_tile=True, merged_tile=True, storage_tile=True, db_entry=True)
        finally:
            if pseoudo_error:
                await asyncio.sleep(1)
                self._sync_job(job)  # この２行はテストが終わるために必要。理由はよくわからない
                return

            await asyncio.sleep(cleanup_delay)
            self._synchronizer.delete(job)
            async with self._housekeep_limit:
                await housekeep()

    async def _run_job_main_flow(self, job: QuicklookJob) -> None:
        async with _overlapping_semaphore(self._ram_limit) as ram_limit_release:
            await job_generate(job, self._sync_job)
            _update_job_record_phase(job, 'in_progress')
            storage.put_quicklook_job_config(job)
            self._raise_error_for_test(job, stop_on=QuicklookJobPhase.GENERATE_DONE)
            async with _overlapping_semaphore(self._disk_limit) as _disk_limit_release:
                await job_merge(job, self._sync_job)
                await cleanup_job(job, tmp_tile=True, merged_tile=False)
                ram_limit_release()
                self._raise_error_for_test(job, stop_on=QuicklookJobPhase.MERGE_DONE)
                async with _overlapping_semaphore(self._transfer_limit) as _transfer_limit_release:
                    await job_transfer(job, self._sync_job)
        job.phase = QuicklookJobPhase.READY
        storage.save_quicklook_job(job)
        self._update_job_phase(job, QuicklookJobPhase.READY)
        _update_job_record_phase(job, 'ready')
        await cleanup_job(job, tmp_tile=True, merged_tile=True)

    def _raise_error_for_test(self, job: QuicklookJob, *, stop_on: QuicklookJobPhase):
        if mutable_config.job_stop_at == stop_on.name:
            self._update_job_phase(job, stop_on)
            raise PseudoErrorForTest()

    def _update_job_phase(self, job: QuicklookJob, phase: QuicklookJobPhase):
        job.phase = phase
        self._sync_job(job)

    def _sync_job(self, job: QuicklookJob):
        self._synchronizer.modify(job)

    def clear(self):
        self._synchronizer.delete_all()


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


def _db_has(visit: Visit) -> bool:
    from sqlalchemy import exists, select

    with db_context() as db:
        result = db.execute(
            select(exists().where(QuicklookRecord.id == visit.id).where(QuicklookRecord.phase != 'deleting')),
        ).scalar()
        assert isinstance(result, bool)
        return result


@asynccontextmanager
async def _overlapping_semaphore(sem: OrderedSemaphore):
    await sem.acquire()
    with _run_once_guard(sem.release) as release:
        yield release


@contextmanager
def _run_once_guard(f: Callable):
    called = False

    def g():
        nonlocal called
        if called:
            raise RuntimeError('run_on_exit_once_at_most called more than once')
        called = True
        f()

    try:
        yield g
    finally:
        if not called:
            f()


job_runner = JobRunner()
