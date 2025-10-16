import asyncio
import queue
from contextlib import AsyncExitStack, asynccontextmanager
from dataclasses import dataclass, field
from typing import Awaitable, Callable, Generator

from quicklook.comm.coordinator import get_available_generators
from quicklook.comm.rpc_worker import rpc_scatter
from quicklook.comm.types import GeneratorId, GeneratorInfo
from quicklook.generator.generate_single_fits_tiles import (
    CcdMetadata,
    GenerateSingleFitsTilesProgress,
    generate_single_fits_tiles_pipeline,
)
from quicklook.job.job import Job
from quicklook.job.local_storage import CcdDistributionConfig
from quicklook.rpc.client import Rpc
from quicklook.rpc.queue import RpcQueue
from quicklook.types import CcdDataRef, CcdName


def enable_faulthandler():
    # Enable faulthandler for easier debugging
    import faulthandler, signal, sys

    faulthandler.enable(sys.stderr, all_threads=True)
    faulthandler.register(signal.SIGUSR1, file=sys.stderr, all_threads=True)
    print('Enabled faulthandler')


enable_faulthandler() # TODO: Remove this line in production


async def generate_single_fits_tile(job: Job, ccd_refs: list[CcdDataRef]) -> list[CcdMetadata]:
    ccd_generator_map: dict[CcdName, GeneratorId] = {}
    ccd_metadata_dict: dict[CcdName, CcdMetadata] = {}
    ccd_refs_to_process = [*ccd_refs]
    done = asyncio.Event()

    async def on_message(msg: CcdMetadata | GenerateSingleFitsTilesProgress, generator: GeneratorInfo):
        match msg:
            case GenerateSingleFitsTilesProgress(ccd_name=ccd_name, progress=progress):
                async with job.watcher.watch_status():
                    job.status.generate_single_fits_tiles[ccd_name] = progress
            case CcdMetadata(ccd_name=ccd_name):
                ccd_generator_map[ccd_name] = generator.id
                ccd_metadata_dict[ccd_name] = msg
                if len(ccd_metadata_dict) == len(ccd_refs):
                    done.set()

    generators = get_available_generators()
    workers = [
        _GenerateSingleFitsTilesPipelineWorker(
            generator,
            job,
            on_message=on_message,
        )
        for generator in generators.values()
    ]

    stack = AsyncExitStack()
    async with stack:
        for worker in workers:
            await stack.enter_async_context(worker.activate())
        while len(ccd_refs_to_process) > 0:
            ccd_ref = ccd_refs_to_process.pop(0)
            available_workers, _ = await asyncio.wait(
                [asyncio.create_task(worker.wait_until_available()) for worker in workers],
                return_when=asyncio.FIRST_COMPLETED,
            )
            worker = sorted([await w for w in available_workers], key=lambda w: w.running_jobs)[0]
            await worker.submit(ccd_ref)

    await done.wait()

    dist_config = CcdDistributionConfig(ccd_generator_map, generators)
    async with job.watcher.notify_shared_large_status():
        job.shared_large_status.dist_config = dist_config
        job.shared_large_status.ccd_metadata_list = [*ccd_metadata_dict.values()]

    await rpc_scatter(_save_job_metadata_rpc, job)
    await rpc_scatter(_save_ccd_distribution_config_rpc, job, dist_config)

    return [*ccd_metadata_dict.values()]


@dataclass
class _GenerateSingleFitsTilesPipelineWorker:
    generator: GeneratorInfo
    job: Job
    on_message: Callable[[CcdMetadata | GenerateSingleFitsTilesProgress, GeneratorInfo], Awaitable[None]]
    max_jobs: int = 8

    _running_jobs: int = 0
    _available_event: asyncio.Event = field(default_factory=asyncio.Event)
    _input_queue: asyncio.Queue[CcdDataRef | None] = field(default_factory=asyncio.Queue)

    @asynccontextmanager
    async def activate(self):
        self._available_event.set()

        async def consume_rpc():
            rpc = Rpc(
                f'{self.generator.ws_url}/rpc',
                _generate_single_fits_tiles_rpc,
                self.job,
                RpcQueue(self._input_queue),
            )
            async for msg in rpc.iterate():
                match msg:
                    case CcdMetadata():
                        self._running_jobs -= 1
                        if self._running_jobs < self.max_jobs:
                            self._available_event.set()
                await self.on_message(msg, self.generator)

        async with asyncio.TaskGroup() as tg:
            t = tg.create_task(consume_rpc())
            try:
                yield
            finally:
                await self._input_queue.put(None)
        t.result()

    async def submit(self, ccd_ref: CcdDataRef):
        self._running_jobs += 1
        if not self.available():
            self._available_event.clear()
        await self._input_queue.put(ccd_ref)

    def available(self):
        return self._running_jobs < self.max_jobs

    async def wait_until_available(self):
        await self._available_event.wait()
        return self

    @property
    def running_jobs(self):
        return self._running_jobs


def _generate_single_fits_tiles_rpc(
    job: Job,
    ccd_refs_q: queue.Queue[CcdDataRef | None],
) -> Generator[GenerateSingleFitsTilesProgress | CcdMetadata]:
    def ccd_refs():
        while ccd_ref := ccd_refs_q.get():
            yield ccd_ref

    try:
        for msg in generate_single_fits_tiles_pipeline(job, ccd_refs()):
            yield msg
    except Exception:
        import traceback

        traceback.print_exc()
        raise


def _save_job_metadata_rpc(job: Job):
    job.local_storage.metadata.save()


def _save_ccd_distribution_config_rpc(job: Job, dist_config: CcdDistributionConfig):
    job.local_storage.ccd_distribution_config.save(dist_config)
