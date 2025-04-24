import asyncio
import logging
from dataclasses import asdict
from typing import Callable

import aiohttp

from quicklook.config import config
from quicklook.coordinator.quicklookjob.job import QuicklookJob, QuicklookJobPhase
from quicklook.coordinator.quicklookjob.tasks import TransferTask
from quicklook.types import GeneratorPod, TransferProgress, TransferTaskResponse
from quicklook.utils.message import message_from_async_reader

logger = logging.getLogger(f'uvicorn.{__name__}')


async def job_transfer(job: QuicklookJob, sync_job: Callable[[QuicklookJob], None]):
    job.phase = QuicklookJobPhase.TRANSFER_RUNNING
    sync_job(job)
    await _scatter_transfer_job(job, sync_job)
    job.transfer_progress = None
    job.phase = QuicklookJobPhase.TRANSFER_DONE
    sync_job(job)


async def _scatter_transfer_job(job: QuicklookJob, sync_job: Callable[[QuicklookJob], None]):
    ccd_generator_map = job.ccd_generator_map
    assert ccd_generator_map

    nodes: dict[str, TransferProgress] = {}

    async def run_1_task(g: GeneratorPod):
        for _ in range(5):
            try:
                return await run_1_task_noretry(g)
            except aiohttp.ServerTimeoutError:
                logger.warning(f'ClientTimeout for {g}')

        raise RuntimeError(f'ClientTimeout for {g} after 5 retries')

    async def run_1_task_noretry(g: GeneratorPod):
        task = TransferTask(visit=job.visit, generator=g, ccd_generator_map=ccd_generator_map)
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f'http://{g.host}:{g.port}/quicklooks/transfer',
                json=asdict(task),
                raise_for_status=True,
                timeout=config.transfer_timeout,
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
