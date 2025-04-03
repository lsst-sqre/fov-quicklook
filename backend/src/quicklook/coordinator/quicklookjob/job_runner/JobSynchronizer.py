from quicklook.coordinator.quicklookjob.job import QuicklookJob, QuicklookJobPhase, QuicklookJobReport
from quicklook.types import Visit
from quicklook.utils.broadcastqueue import BroadcastQueue
from quicklook.utils.event import WatchEvent


from typing import AsyncGenerator


class JobSynchronizer:
    def __init__(self):
        self._entries: dict[Visit, QuicklookJobReport] = {}
        self._q = BroadcastQueue[WatchEvent[QuicklookJobReport]]()

    def add(self, job: QuicklookJob):
        report = QuicklookJobReport.from_job(job)
        self._entries[job.visit] = report
        self._q.put(WatchEvent(report, 'added'))

    def delete(self, job: QuicklookJob):
        self._entries.pop(job.visit)
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