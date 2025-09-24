from dataclasses import dataclass
from functools import lru_cache

from quicklook.comm.coordinator import get_available_generators
from quicklook.comm.types import GeneratorInfo
from quicklook.config import config
from quicklook.datasource import get_datasource
from quicklook.generator.job.generate_single_fits_tiles import generate_single_fits_tiles
from quicklook.job import Job
from quicklook.rpc import Rpc, run_rpc
from quicklook.types import CcdId, Visit
from quicklook.utils.dynamic_dispatch import Worker, dynamic_dispatch
from quicklook.utils.timeit import timeit

ds = get_datasource()


async def create_quickook(visit: Visit):
    job = Job(visit=visit)

    with timeit(f'Listing CCDs for visit {visit}'):
        ccd_ids = [CcdId(visit, ccd_name) for ccd_name in ds.list_ccds(visit)][:8]

    try:
        await _generate_single_fits_tiles(visit, job, ccd_ids)
    finally:
        ...
        # await job.cleanup()


@dataclass
class CcdWorkerMapping:
    pass


async def _generate_single_fits_tiles(visit, job, ccd_ids: list[CcdId]):
    workers = [create_generate_single_fits_tiles_worker(g) for g in get_available_generators()]
    args_list = [GenerateSingleFitsTileTaskArgs(job, ccd_id) for ccd_id in ccd_ids]
    async for result in dynamic_dispatch(workers, args_list, max_redistribution_count=1):
        print(result.value)


def sample(*args):
    print(args)


def create_generate_single_fits_tiles_worker(generator: GeneratorInfo) -> Worker:
    async def run(args: GenerateSingleFitsTileTaskArgs):
        rpc = Rpc.create(generate_single_fits_tiles, args.job, args.ccd_id)
        # rpc = Rpc.create(sample, args.job, args.ccd_id)
        return await run_rpc(f'{generator.url}/rpc', rpc)

    async def kill():
        pass

    return Worker(
        run=run,
        kill=kill,
        capacity=config.generator_max_concurrent_jobs,
    )


@dataclass
class GenerateSingleFitsTileTaskArgs:
    job: Job
    ccd_id: CcdId
