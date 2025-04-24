import asyncio
import logging
from dataclasses import asdict
from typing import Callable

import aiohttp

from quicklook import storage
from quicklook.coordinator.quicklookjob.job import QuicklookJob, QuicklookJobPhase
from quicklook.coordinator.quicklookjob.tasks import MergeTask
from quicklook.types import GeneratorPod, MergeProgress, MergeTaskResponse
from quicklook.utils.message import message_from_async_reader

logger = logging.getLogger(f'uvicorn.{__name__}')


async def job_merge(job: QuicklookJob, sync_job: Callable[[QuicklookJob], None]):
    job.phase = QuicklookJobPhase.MERGE_RUNNING
    sync_job(job)
    await _scatter_merge_job(job, sync_job)
    job.merge_progress = None
    job.phase = QuicklookJobPhase.MERGE_DONE
    sync_job(job)


async def _scatter_merge_job(job: QuicklookJob, sync_job: Callable[[QuicklookJob], None]):
    ccd_generator_map = job.ccd_generator_map
    assert ccd_generator_map

    nodes: dict[str, MergeProgress] = {}

    async def run_1_task(g: GeneratorPod):
        for _ in range(5):
            try:
                return await run_1_task_noretry(g)
            except aiohttp.ServerTimeoutError:
                logger.warning(f'ClientTimeout for {g}')

        raise RuntimeError(f'ClientTimeout for {g} after 5 retries')

    async def run_1_task_noretry(g: GeneratorPod):
        task = MergeTask(generator=g, visit=job.visit, ccd_generator_map=ccd_generator_map)
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f'http://{g.host}:{g.port}/quicklooks/merge',
                json=asdict(task),
                raise_for_status=True,
                timeout=aiohttp.ClientTimeout(total=3600),
            ) as res:
                while True:
                    msg: MergeTaskResponse = await message_from_async_reader(res.content.readexactly)
                    match msg:
                        case None:
                            break
                        case BaseException():  # pragma: no cover
                            raise msg
                        case MergeProgress():
                            nodes[g.name] = msg
                            job.merge_progress = nodes
                            sync_job(job)
                        case _:  # pragma: no cover
                            raise TypeError(f'Unexpected message: {msg}')

    generators = [*set(ccd_generator_map.values())]
    await asyncio.gather(*(run_1_task(g) for g in generators))
