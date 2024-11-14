import asyncio
from dataclasses import asdict

import aiohttp
from fastapi import APIRouter

from quicklook.coordinator.api.generators import get_generators
from quicklook.coordinator.quicklook import Quicklook, QuicklookMeta
from quicklook.coordinator.tasks import GeneratorTask, make_generator_tasks
from quicklook.db import db_context
from quicklook.generator.progress import GeneratorProgress
from quicklook.generator.tasks import process_ccd
from quicklook.types import GeneratorResult, MessageFromGeneratorToCoordinator, ProcessCcdResult
from quicklook.utils.message import message_from_async_reader

router = APIRouter()


async def run_next_job():
    ql = Quicklook.dequeue()
    if ql:  # pragma: no branch
        process_ccd_results = await run_generators(ql)
        ql.save_meta(QuicklookMeta(process_ccd_results=process_ccd_results))
        ql.notify()
        await run_transfers(ql)
        ql.phase = 'ready'
        ql.notify()
        ql.save()


async def run_generators(ql: Quicklook) -> list[ProcessCcdResult]:
    visit = ql.visit
    nodes: dict[str, GeneratorProgress] = {}
    tasks = make_generator_tasks(visit, get_generators())
    assert len(get_generators()) > 0
    ql.ccd_generator_map = tasks[0].ccd_generator_map

    async def run_1_generator(task: GeneratorTask):
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f'http://{task.generator.host}:{task.generator.port}/quicklooks',
                json=asdict(task),
                raise_for_status=True,
            ) as res:
                process_ccd_results: list[ProcessCcdResult] = []
                while True:
                    msg: MessageFromGeneratorToCoordinator = await message_from_async_reader(res.content.readexactly)
                    match msg:
                        case None:
                            break
                        case BaseException():
                            raise msg
                        case GeneratorProgress():
                            nodes[task.generator.name] = msg
                            ql.generating_progress = nodes
                            ql.notify()
                        case GeneratorResult():
                            process_ccd_results.extend(msg.process_ccd_resulsts)
                        case _:
                            raise TypeError(f'Unexpected message: {msg}')
                return process_ccd_results

    gathered_results: list[ProcessCcdResult] = []
    for fut in asyncio.as_completed([run_1_generator(task) for task in tasks]):
        gathered_results.extend(await fut)
    return gathered_results


async def run_transfers(ql: Quicklook): ...
