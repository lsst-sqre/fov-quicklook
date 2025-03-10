import asyncio
import logging
from contextlib import asynccontextmanager
from dataclasses import asdict
from typing import AsyncGenerator

import aiohttp

from quicklook import storage
from quicklook.config import config
from quicklook.coordinator.api.generators import get_generators
from quicklook.coordinator.quicklookjob.job import QuicklookJob
from quicklook.coordinator.quicklookjob.tasks import GenerateTask, TransferTask
from quicklook.datasource import get_datasource
from quicklook.db import db_context
from quicklook.generator.progress import GenerateProgress
from quicklook.models import QuicklookRecord
from quicklook.types import CcdMeta, GeneratorPod, GenerateTaskResponse, QuicklookMeta, TransferProgress, TransferTaskResponse, Visit
from quicklook.utils.broadcastqueue import BroadcastQueue
from quicklook.utils.event import WatchEvent
from quicklook.utils.http_request import http_request
from quicklook.utils.message import message_from_async_reader
from quicklook.utils.pipeline import Pipeline, Stage
from quicklook.utils.timeit import timeit

from .job import QuicklookJob, QuicklookJobReport

logger = logging.getLogger(f'uvicorn.{__name__}')

backoff_time = 1 if config.environment == 'test' else 30
# テスト時は0にしたいのだが、ここを0にするとfrontendプロセスが止まらなくなってしまう。
# 詳しくはREADME.ja.mdのtouble shootingを参照


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
    process_ccd_results = await scatter_generate_job(job)
    storage.put_quicklook_meta(job.visit, QuicklookMeta(ccd_meta=process_ccd_results))
    job.generate_progress = None
    job.phase = 'transfer:queued'
    sync_job(job)


async def transfer(job: QuicklookJob):
    with db_context() as db:
        db.add(QuicklookRecord(id=job.visit.id, phase='in_progress'))
        db.commit()

    storage.put_quicklook_job_config(job)

    job.phase = 'transfer:running'
    sync_job(job)
    await scatter_transfer_job(job)
    job.transfer_progress = None
    job.phase = 'ready'
    sync_job(job)

    with db_context() as db:
        db.query(QuicklookRecord).filter(QuicklookRecord.id == job.visit.id).update({'phase': 'ready'})
        db.commit()


async def cleanup(job: QuicklookJob):
    pass


def make_generate_tasks(job: QuicklookJob, generators: list[GeneratorPod]):
    ds = get_datasource()

    visit = job.visit

    with timeit(f'Listing CCDs for visit {visit}', loglevel=logging.INFO):
        ccd_names_for_visit = [*ds.list_ccds(visit)]

    if config.dev_ccd_limit is not None:  # pragma: no cover
        ccd_names_for_visit = ccd_names_for_visit[: config.dev_ccd_limit]

    ng = len(generators)
    nc = len(ccd_names_for_visit)

    tasks: list[GenerateTask] = []
    ccd_generator_map: dict[str, GeneratorPod] = {}

    for i, g in enumerate(generators):
        ccd_names = [ccd_name for ccd_name in ccd_names_for_visit[i * nc // ng : (i + 1) * nc // ng]]
        task = GenerateTask(generator=g, visit=visit, ccd_names=ccd_names)
        tasks.append(task)
        for ccd_name in ccd_names:
            ccd_generator_map[ccd_name] = g

    return tasks, ccd_generator_map


async def scatter_generate_job(job: QuicklookJob) -> list[CcdMeta]:
    nodes: dict[str, GenerateProgress] = {}
    tasks, ccd_generator_map = make_generate_tasks(job, get_generators())
    assert len(get_generators()) > 0
    job.ccd_generator_map = ccd_generator_map

    async def run_1_task(task: GenerateTask):
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f'http://{task.generator.host}:{task.generator.port}/quicklooks',
                json=asdict(task),
                raise_for_status=True,
            ) as res:
                process_ccd_results: list[CcdMeta] = []
                while True:
                    msg: GenerateTaskResponse = await message_from_async_reader(res.content.readexactly)
                    match msg:
                        case None:
                            break
                        case BaseException():  # pragma: no cover
                            raise msg
                        case GenerateProgress():
                            nodes[task.generator.name] = msg
                            job.generate_progress = nodes
                            sync_job(job)
                        case CcdMeta():
                            process_ccd_results.append(msg)
                        case _:  # pragma: no cover
                            raise TypeError(f'Unexpected message: {msg}')
                return process_ccd_results

    gathered_results: list[CcdMeta] = []
    for fut in asyncio.as_completed([run_1_task(task) for task in tasks]):
        gathered_results.extend(await fut)
    return gathered_results


async def scatter_transfer_job(job: QuicklookJob):
    ccd_generator_map = job.ccd_generator_map
    assert ccd_generator_map

    nodes: dict[str, TransferProgress] = {}

    async def run_1_task(g: GeneratorPod):
        task = TransferTask(generator=g, visit=job.visit, ccd_generator_map=ccd_generator_map)
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f'http://{g.host}:{g.port}/quicklooks/transfer',
                json=asdict(task),
                raise_for_status=True,
            ) as res:
                while True:
                    msg: TransferTaskResponse = await message_from_async_reader(res.content.readexactly)
                    match msg:
                        case None:
                            break
                        case BaseException():  # pragma: no cover
                            raise msg
                        case TransferProgress():
                            nodes[g.name] = msg
                            job.transfer_progress = nodes
                            sync_job(job)
                        case _:  # pragma: no cover
                            raise TypeError(f'Unexpected message: {msg}')

    generators = [*set(ccd_generator_map.values())]
    await asyncio.gather(*(run_1_task(g) for g in generators))


class _JobManager:
    def __init__(self):
        self._synchronizer = _JobSynchronizer()

    @asynccontextmanager
    async def activate(self):
        async def backoff(job: QuicklookJob):
            await cleanup(job)
            await asyncio.sleep(backoff_time)
            temporary_quicklooks_queue.get_nowait()
            self._synchronizer.delete(job)

        async def on_task_complete(job: QuicklookJob):
            await backoff(job)

        async def on_task_error(job: QuicklookJob, e: Exception):  # pragma: no cover
            job.phase = 'failed'
            sync_job(job)
            await backoff(job)

        async with Pipeline(
            job_stages(),
            on_task_complete=on_task_complete,
            on_task_error=on_task_error,
        ) as self._pipeline:
            yield

    async def enqueue(self, visit: Visit):
        if not self._synchronizer.has(visit) and not db_has(visit):  # pragma: no branch
            job = QuicklookJob(visit=visit, phase='generate:queued')
            self._synchronizer.add(job)
            await self._pipeline.push_task(job)

    def subscribe(self) -> AsyncGenerator[list[WatchEvent[QuicklookJobReport]], None]:
        return self._synchronizer.subscribe()

    async def clear(self):
        from quicklook.coordinator.api.generators import ctx

        async def delete_generator(g: GeneratorPod):
            await http_request('delete', f'http://{g.host}:{g.port}/quicklooks/*')

        await asyncio.gather(*(delete_generator(g) for g in ctx().generators))


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


def db_has(visit: Visit) -> bool:
    from sqlalchemy import exists, select

    with db_context() as db:
        result = db.execute(select(exists().where(QuicklookRecord.id == visit.id))).scalar()
        assert isinstance(result, bool)
        return result


def sync_job(job: QuicklookJob):
    job_manager._synchronizer.modify(job)


job_manager = _JobManager()
