import asyncio
import time
from collections import OrderedDict
from dataclasses import dataclass, field
from typing import AsyncGenerator, Literal, Union

from pydantic import BaseModel

from quicklook.types import GeneratorPod, GeneratorProgress, ProcessCcdResult, Visit
from quicklook.utils.broadcastqueue import BroadcastQueue
from quicklook.utils.event import WatchEvent
from quicklook.utils.http_request import http_request


@dataclass
class QuicklookJob:
    Phase = Literal['queued', 'generating', 'transferring', 'ready']

    visit: Visit
    phase: Phase
    created_at: float = field(default_factory=lambda: time.time())
    generating_progress: dict[str, GeneratorProgress] | None = None
    transferreing_progress: dict[str, float] | None = None
    ccd_generator_map: dict[str, GeneratorPod] | None = None  # ccd_name -> GeneratorPod
    
    meta: Union['QuicklookMeta', None] = None

    async def cleanup(self):
        ...

    def sync(self):
        job_queue._sync_job(self)


class QuicklookMeta(BaseModel):
    ccd_meta: list[ProcessCcdResult]

    @classmethod
    def from_process_ccd_results(cls, results: list[ProcessCcdResult]) -> 'QuicklookMeta':
        return cls(ccd_meta=results)


class JobQueue:
    # jobのキュー管理をする
    # Frontendでもjobの一覧を保持するがそのための同期もここで行う
    def __init__(self):
        self._entries: OrderedDict[Visit, QuicklookJob] = OrderedDict()
        self._synchronizer = BroadcastQueue[WatchEvent[QuicklookJob]]()

    def enqueue(self, visit: Visit):
        if visit not in self._entries:
            job = QuicklookJob(visit=visit, phase='queued')
            self._entries[visit] = job
            self._synchronizer.put(WatchEvent(job, 'added'))

    async def dequeue(self):
        if len(self._entries) == 0:
            return
        _visit, job = self._entries.popitem(last=False)
        try:
            yield job
        finally:
            await job.cleanup()
            self._synchronizer.put(WatchEvent(job, 'deleted'))

    def _sync_job(self, job: QuicklookJob):
        self._synchronizer.put(WatchEvent(job, 'modified'))

    async def subscribe(self) -> AsyncGenerator[list[WatchEvent[QuicklookJob]], None]:
        yield [WatchEvent(e, 'added') for e in self._entries.values()]
        with self._synchronizer.subscribe() as events:
            while True:
                yield [await events.get()]

    async def clear(self):
        # TODO: このコードはデバッグ用
        from quicklook.coordinator.api.generators import ctx

        async def delete_generator(g: GeneratorPod):
            await http_request('delete', f'http://{g.host}:{g.port}/quicklooks/*')

        await asyncio.gather(*(delete_generator(g) for g in ctx().generators))


job_queue = JobQueue()
