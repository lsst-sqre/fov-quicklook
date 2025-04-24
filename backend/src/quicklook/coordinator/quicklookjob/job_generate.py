import asyncio
import logging
from dataclasses import asdict
from typing import Callable

import aiohttp

from quicklook import storage
from quicklook.config import config
from quicklook.coordinator.api.generators import get_generators
from quicklook.coordinator.quicklookjob.job import QuicklookJob, QuicklookJobPhase
from quicklook.coordinator.quicklookjob.tasks import GenerateTask
from quicklook.datasource import get_datasource
from quicklook.generator.progress import GenerateProgress
from quicklook.types import CcdMeta, GenerateTaskResponse, GeneratorPod, QuicklookMeta
from quicklook.utils.message import message_from_async_reader
from quicklook.utils.timeit import timeit

logger = logging.getLogger(f'uvicorn.{__name__}')


async def job_generate(job: QuicklookJob, sync_job: Callable[[QuicklookJob], None]):
    job.phase = QuicklookJobPhase.GENERATE_RUNNING
    sync_job(job)
    process_ccd_results = await _scatter_generate_job(job, sync_job)
    storage.put_quicklook_meta(job.visit, QuicklookMeta(ccd_meta=process_ccd_results))
    job.generate_progress = None
    job.phase = QuicklookJobPhase.GENERATE_DONE
    sync_job(job)


def _make_generate_tasks(job: QuicklookJob, generators: list[GeneratorPod]):
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


async def _scatter_generate_job(job: QuicklookJob, sync_job: Callable[[QuicklookJob], None]) -> list[CcdMeta]:
    nodes: dict[str, GenerateProgress] = {}
    tasks, ccd_generator_map = _make_generate_tasks(job, get_generators())
    assert len(get_generators()) > 0
    job.ccd_generator_map = ccd_generator_map

    async def run_1_task(task: GenerateTask):
        for _ in range(5):
            try:
                return await run_1_task_noretry(task)
            except aiohttp.ServerTimeoutError:
                logger.warning(f'ClientTimeout for {task}')

        raise RuntimeError(f'ClientTimeout for {task} after 5 retries')

    async def run_1_task_noretry(task: GenerateTask):
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f'http://{task.generator.host}:{task.generator.port}/quicklooks',
                json=asdict(task),
                raise_for_status=True,
                timeout=config.generate_timeout,
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
