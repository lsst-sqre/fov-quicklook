from quicklook.comm.coordinator import get_available_generators
from quicklook.comm.rpc import Rpc
from quicklook.datasource import get_datasource
from quicklook.generator.generate_single_fits_tiles import generate_single_fits_tiles
from quicklook.generator.job import Job
from quicklook.generator.jobstorage import CcdDistributionConfig, JobStorage
from quicklook.generator.merge_single_tile_fits import merge_single_fits_tiles
from quicklook.types import CcdId, Visit

from ..comm.rpc_worker import adaptive_map_rpc, rpc_endpoint, rpc_scatter

ds = get_datasource()


async def create_quickook(visit: Visit):
    job = Job(visit=visit)
    ccd_ids = [CcdId(visit, ccd_name) for ccd_name in ds.list_ccds(visit)]
    try:
        ccd_generator_map = await _generate_single_fits_tiles(job, ccd_ids)
        await _merge_tiles(job, ccd_generator_map)
        await _transfer_tiles(job)
    finally:
        await rpc_scatter(Rpc.create(_clear_all, job))


async def _generate_single_fits_tiles(job: Job, ccd_ids: list[CcdId]):
    rpcs = [Rpc.create(generate_single_fits_tiles, job, ccd_id) for ccd_id in ccd_ids]
    ccd_generator_map: dict[str, str] = {}

    async for result in adaptive_map_rpc(rpcs, stream=True, on_progress=print):
        ccd_generator_map[result.rpc_args[1].ccd_name] = rpc_endpoint(result.generator_id)

    return ccd_generator_map


async def _merge_tiles(job: Job, ccd_generator_map: dict[str, str]):
    dist_config = CcdDistributionConfig(ccd_generator_map, get_available_generators())
    await rpc_scatter(Rpc.create(_save_ccd_distribution_config, job, dist_config))
    await rpc_scatter(Rpc.create(merge_single_fits_tiles, job))
    await rpc_scatter(Rpc.create(_clear_single_fits_tiles, job))


async def _transfer_tiles(job: Job):
    pass


def _save_ccd_distribution_config(job: Job, dist_config: CcdDistributionConfig):
    JobStorage(job).ccd_distribution_config.save(dist_config)


def _clear_single_fits_tiles(job: Job):
    JobStorage(job).single_fits_tile.clear()


def _clear_all(job):
    storage = JobStorage(job)
    storage.clear_all()
