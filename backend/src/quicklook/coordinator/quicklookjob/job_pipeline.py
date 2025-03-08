import asyncio
from contextlib import asynccontextmanager
from dataclasses import asdict
from typing import AsyncGenerator

import aiohttp

from quicklook import storage
from quicklook.config import config
from quicklook.coordinator.api.generators import get_generators
from quicklook.coordinator.quicklookjob.job import QuicklookJob
from quicklook.coordinator.tasks import GeneratorTask, make_generator_tasks
from quicklook.db import db_context
from quicklook.generator.progress import GeneratorProgress
from quicklook.models import QuicklookRecord
from quicklook.types import CcdMeta, GeneratorPod, MessageFromGeneratorToCoordinator, QuicklookMeta, Visit
from quicklook.utils.broadcastqueue import BroadcastQueue
from quicklook.utils.event import WatchEvent
from quicklook.utils.http_request import http_request
from quicklook.utils.message import message_from_async_reader
from quicklook.utils.pipeline import Pipeline, Stage

from .job import QuicklookJob

backoff_time = 0.1 if config.environment == 'test' else 30


def job_stages() -> list[Stage[QuicklookJob]]:
    return [
        Stage(
            name='limit_temporary_quicklooks',
            concurrency=1,
            process_func=limit_temporary_quicklooks,
        ),
        Stage(
            name='generate',
            concurrency=config.max_generate_jobs,
            process_func=generate,
        ),
        Stage(
            name='transfer',
            concurrency=config.max_transfer_jobs,
            process_func=transfer,
        ),
    ]


temporary_quicklooks_queue = asyncio.Queue(config.max_temporary_quicklooks)


async def limit_temporary_quicklooks(job: QuicklookJob):
    # 一時的なQuicklookの数を制限する
    # transferが終わるまでgeneratorのRAMを解放できないため
    await temporary_quicklooks_queue.put(job)


async def generate(job: QuicklookJob):
    job.phase = 'generate:running'
    sync_job(job)
    process_ccd_results = await scatter_generator_job(job)
    storage.put_quicklook_meta(job.visit, QuicklookMeta(ccd_meta=process_ccd_results))
    job.phase = 'transfer:queued'
    sync_job(job)


async def transfer(job: QuicklookJob):
    job.phase = 'transfer:running'
    ...
    sync_job(job)
    job.phase = 'ready'
    sync_job(job)



async def scatter_generator_job(job: QuicklookJob) -> list[CcdMeta]:
    visit = job.visit
    nodes: dict[str, GeneratorProgress] = {}
    tasks = make_generator_tasks(visit, get_generators())
    assert len(get_generators()) > 0
    job.ccd_generator_map = tasks[0].ccd_generator_map

    async def run_generator(task: GeneratorTask):
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f'http://{task.generator.host}:{task.generator.port}/quicklooks',
                json=asdict(task),
                raise_for_status=True,
            ) as res:
                process_ccd_results: list[CcdMeta] = []
                while True:
                    msg: MessageFromGeneratorToCoordinator = await message_from_async_reader(res.content.readexactly)
                    match msg:
                        case None:
                            break
                        case BaseException():  # pragma: no cover
                            raise msg
                        case GeneratorProgress():
                            nodes[task.generator.name] = msg
                            job.generate_progress = nodes
                            sync_job(job)
                        case CcdMeta():
                            process_ccd_results.append(msg)
                        case _:  # pragma: no cover
                            raise TypeError(f'Unexpected message: {msg}')
                return process_ccd_results

    gathered_results: list[CcdMeta] = []
    for fut in asyncio.as_completed([run_generator(task) for task in tasks]):
        gathered_results.extend(await fut)
    return gathered_results


class _JobManager:
    def __init__(self):
        self._synchronizer = _JobSynchronizer()

    @asynccontextmanager
    async def activate(self):
        def unregister_from_synchronizer(job: QuicklookJob):
            temporary_quicklooks_queue.get_nowait()
            self._synchronizer.delete(job)

        async def on_task_complete(job: QuicklookJob):
            await asyncio.sleep(backoff_time)
            unregister_from_synchronizer(job)

        async def on_task_error(job: QuicklookJob, e: Exception):
            job.phase = 'failed'
            sync_job(job)
            await asyncio.sleep(backoff_time)
            unregister_from_synchronizer(job)

        async with Pipeline(
            job_stages(),
            on_task_complete=on_task_complete,
            on_task_error=on_task_error,
        ) as self._pipeline:
            yield

    async def enqueue(self, visit: Visit):
        if not self._synchronizer.has(visit) and not db_has(visit):
            job = QuicklookJob(visit=visit, phase='generate:queued')
            self._synchronizer.add(job)
            await self._pipeline.push_task(job)

    def subscribe(self) -> AsyncGenerator[list[WatchEvent[QuicklookJob]], None]:
        return self._synchronizer.subscribe()

    async def clear(self):
        from quicklook.coordinator.api.generators import ctx

        async def delete_generator(g: GeneratorPod):
            await http_request('delete', f'http://{g.host}:{g.port}/quicklooks/*')

        await asyncio.gather(*(delete_generator(g) for g in ctx().generators))


class _JobSynchronizer:
    def __init__(self):
        self._entries: dict[Visit, QuicklookJob] = {}
        self._q = BroadcastQueue[WatchEvent[QuicklookJob]]()

    def add(self, job: QuicklookJob):
        self._entries[job.visit] = job
        self._q.put(WatchEvent(job, 'added'))

    def delete(self, job: QuicklookJob):
        del self._entries[job.visit]
        self._q.put(WatchEvent(job, 'deleted'))

    def modify(self, job: QuicklookJob):
        self._q.put(WatchEvent(job, 'modified'))

    def has(self, visit: Visit) -> bool:
        return visit in self._entries

    async def subscribe(self) -> AsyncGenerator[list[WatchEvent[QuicklookJob]], None]:
        yield [WatchEvent(e, 'added') for e in self._entries.values()]
        with self._q.subscribe() as events:
            while True:
                yield [await events.get()]


def db_has(visit: Visit) -> bool:
    from sqlalchemy import exists, select

    with db_context() as db:
        result = db.execute(select(exists().where(QuicklookRecord.id == visit.id))).scalar()
        assert isinstance(result, bool)
        return result


def sync_job(job: QuicklookJob):
    job_manager._synchronizer.modify(job)


job_manager = _JobManager()
