import asyncio
import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from quicklook.coordinator.quicklookjob.job import QuicklookJob
from quicklook.db import db_context
from quicklook.models import QuicklookRecord
from quicklook.types import GeneratorPod, Visit
from quicklook.utils.broadcastqueue import BroadcastQueue
from quicklook.utils.event import WatchEvent
from quicklook.utils.http_request import http_request

from .job import QuicklookJob, QuicklookJobPhase, QuicklookJobReport
from .job_runner import JobSynchronizer, QuicklookJobRunner

logger = logging.getLogger(f'uvicorn.{__name__}')


class _JobManager:
    # JobRunnerとの役割分担が微妙
    # こっちはFrontendとの同期が主目的
    #
    # JobRunnerにsynchronizerを持たせて統合するかも。

    def __init__(self):
        self._synchronizer = _JobSynchronizer()

    @asynccontextmanager
    async def activate(self):
        sync = JobSynchronizer(sync=self._sync_job, unlink=lambda j: self._synchronizer.delete(j))
        self._runner = QuicklookJobRunner(job_sync=sync)
        yield

    async def enqueue(self, visit: Visit):
        if not self._synchronizer.has(visit) and not _db_has(visit):  # pragma: no branch
            job = QuicklookJob(visit=visit, phase=QuicklookJobPhase.QUEUED)
            self._synchronizer.add(job)
            await self._runner.enqueue(job)

    def subscribe(self) -> AsyncGenerator[list[WatchEvent[QuicklookJobReport]], None]:
        return self._synchronizer.subscribe()

    async def clear(self):
        from quicklook.coordinator.api.generators import ctx

        async def delete_generator(g: GeneratorPod):
            await http_request('delete', f'http://{g.host}:{g.port}/quicklooks/*')

        await asyncio.gather(*(delete_generator(g) for g in ctx().generators))
        self._synchronizer.delete_all()

    def _sync_job(self, job: QuicklookJob):
        self._synchronizer.modify(job)


class _JobSynchronizer:
    def __init__(self):
        self._entries: dict[Visit, QuicklookJobReport] = {}
        self._q = BroadcastQueue[WatchEvent[QuicklookJobReport]]()

    def add(self, job: QuicklookJob):
        report = QuicklookJobReport.from_job(job)
        self._entries[job.visit] = report
        self._q.put(WatchEvent(report, 'added'))

    def delete(self, job: QuicklookJob):
        del self._entries[job.visit]
        self._q.put(WatchEvent(QuicklookJobReport.from_job(job), 'deleted'))

    def delete_all(self):
        for visit in list(self._entries):
            self.delete(QuicklookJob(visit=visit, phase=QuicklookJobPhase.QUEUED))

    def modify(self, job: QuicklookJob):
        report = QuicklookJobReport.from_job(job)
        self._entries[job.visit] = report
        self._q.put(WatchEvent(report, 'modified'))

    def has(self, visit: Visit) -> bool:
        return visit in self._entries

    async def subscribe(self) -> AsyncGenerator[list[WatchEvent[QuicklookJobReport]], None]:
        yield [WatchEvent(e, 'added') for e in self._entries.values()]
        with self._q.subscribe() as events:
            while True:
                yield [await events.get()]


def _db_has(visit: Visit) -> bool:
    from sqlalchemy import exists, select

    with db_context() as db:
        result = db.execute(select(exists().where(QuicklookRecord.id == visit.id))).scalar()
        assert isinstance(result, bool)
        return result


job_manager = _JobManager()
