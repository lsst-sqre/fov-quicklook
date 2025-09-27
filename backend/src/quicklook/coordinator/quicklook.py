from typing import cast

from quicklook.comm.coordinator import get_available_generators
from quicklook.comm.rpc import Rpc
from quicklook.datasource import get_datasource
from quicklook.generator.generate_single_fits_tiles import CcdMetadata, generate_single_fits_tiles
from quicklook.generator.job import Job
from quicklook.generator.job_local_storage import CcdDistributionConfig
from quicklook.generator.merge_single_tile_fits import merge_single_fits_tiles
from quicklook.generator.transfer_tiles import transfer_tiles
from quicklook.types import CcdDataRef, CcdName, Progress, ReturnValue, VisitName

from ..comm.rpc_worker import YieledValue, adaptive_map_rpc, rpc_endpoint, rpc_scatter

ds = get_datasource()


async def create_quickook(visit: VisitName):
    job = Job(visit=visit)
    ccd_refs = [CcdDataRef(visit=visit, ccd=ccd_name) for ccd_name in ds.list_ccds(visit)]
    try:
        ccd_generator_map = await _generate_single_fits_tiles(job, ccd_refs)
        await rpc_scatter(Rpc.create(_save_job_metadata, job))
        await _merge_tiles(job, ccd_generator_map)
        await _transfer_tiles(job)
    finally:
        pass
        # await rpc_scatter(Rpc.create(_cleanup, job))


async def _generate_single_fits_tiles(job: Job, ccd_refs: list[CcdDataRef]):
    ccd_generator_map: dict[CcdName, str] = {}
    ccd_metadata_dict: dict[CcdName, CcdMetadata] = {}

    rpcs = [Rpc.create(generate_single_fits_tiles, job, ccd_ref) for ccd_ref in ccd_refs]

    def on_yield(msg: YieledValue):
        match msg:
            case YieledValue(value=Progress() as p, args=(_, ccd_ref)):
                ccd_name = cast(CcdDataRef, ccd_ref).ccd
                job.status.generate_single_fits_tiles[ccd_name] = p
                job.status.notify()
            case YieledValue(value=ReturnValue(value=CcdMetadata() as ccd_metadata)):
                ccd_metadata_dict[ccd_metadata.ccd_name] = ccd_metadata

    async for result in adaptive_map_rpc(rpcs, stream=True, on_yield=on_yield):
        ccd_generator_map[result.args[1].ccd] = rpc_endpoint(result.generator_id)

    return ccd_generator_map


async def _merge_tiles(job: Job, ccd_generator_map: dict[CcdName, str]):
    dist_config = CcdDistributionConfig(ccd_generator_map, get_available_generators())
    await rpc_scatter(Rpc.create(_save_ccd_distribution_config, job, dist_config))

    def on_yield(msg):
        match msg:
            case YieledValue(value=Progress() as p, generator_id=generator_id):
                job.status.merge_tiles[generator_id] = p
                job.status.notify()

    await rpc_scatter(Rpc.create(merge_single_fits_tiles, job), stream=True, on_yield=on_yield)
    # await rpc_scatter(Rpc.create(_clear_single_fits_tiles, job))


async def _transfer_tiles(job: Job):
    def on_yield(msg):
        match msg:
            case YieledValue(value=Progress() as p, generator_id=generator_id):
                job.status.transfer_tiles[generator_id] = p
                job.status.notify()

    await rpc_scatter(Rpc.create(transfer_tiles, job), stream=True, on_yield=on_yield)


def _save_ccd_distribution_config(job: Job, dist_config: CcdDistributionConfig):
    job.local_storage.ccd_distribution_config.save(dist_config)


def _clear_single_fits_tiles(job: Job):
    job.local_storage.single_fits_tile.clear()


def _cleanup(job: Job):
    job.local_storage.clear_all()


def _save_job_metadata(job: Job):
    job.local_storage.metadata.save()
