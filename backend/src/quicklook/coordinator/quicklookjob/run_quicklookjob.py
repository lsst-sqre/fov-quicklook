# このファイルの内容は ./quicklookjob.py にあるべきもののような気がする
import asyncio
from dataclasses import asdict

import aiohttp
from fastapi import APIRouter

from quicklook import storage
from quicklook.coordinator.api.generators import get_generators
from . import QuicklookJob, job_queue
from quicklook.coordinator.tasks import GeneratorTask, make_generator_tasks
from quicklook.generator.progress import GeneratorProgress
from quicklook.types import MessageFromGeneratorToCoordinator, CcdMeta, QuicklookMeta
from quicklook.utils.message import message_from_async_reader

router = APIRouter()


async def run_next_job():
    async for job in job_queue.dequeue():
        process_ccd_results = await _run_generators(job)
        storage.put_quicklook_meta(job.visit, QuicklookMeta(ccd_meta=process_ccd_results))
        job.phase = 'transferring'
        job.sync()
        await _run_transfers(job)
        job.phase = 'ready'
        job.sync()


async def _run_generators(job: QuicklookJob) -> list[CcdMeta]:
    visit = job.visit
    nodes: dict[str, GeneratorProgress] = {}
    tasks = make_generator_tasks(visit, get_generators())
    assert len(get_generators()) > 0
    job.ccd_generator_map = tasks[0].ccd_generator_map

    async def run_1_generator(task: GeneratorTask):
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
                            job.generating_progress = nodes
                            job.sync()
                        case CcdMeta():
                            process_ccd_results.append(msg)
                        case _:  # pragma: no cover
                            raise TypeError(f'Unexpected message: {msg}')
                return process_ccd_results

    gathered_results: list[CcdMeta] = []
    for fut in asyncio.as_completed([run_1_generator(task) for task in tasks]):
        gathered_results.extend(await fut)
    return gathered_results


async def _run_transfers(job: QuicklookJob): ...
