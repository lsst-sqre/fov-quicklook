from dataclasses import dataclass
import logging
from typing import cast

from quicklook.comm.coordinator import get_available_generators
from quicklook.comm.rpc import Rpc
from quicklook.config import config
from quicklook.datasource import get_datasource
from quicklook.generator.generate_single_fits_tiles import CcdMetadata, generate_single_fits_tiles
from quicklook.generator.merge_single_tile_fits import merge_single_fits_tiles
from quicklook.generator.transfer_tiles import transfer_tiles
from quicklook.job.job import Job
from quicklook.job.job_local_storage import CcdDistributionConfig
from quicklook.types import CcdDataRef, CcdName, Progress, ReturnValue
from quicklook.utils.pipeline import Pipeline, Stage

from ..comm.rpc_worker import YieledValue, adaptive_map_rpc, rpc_endpoint, rpc_scatter

logger = logging.getLogger(__name__)

ds = get_datasource()


async def create_quicklook(job: Job):
    '''
    テスト用。本番ではパイプラインでquicklookを作成する。
    '''
    visit = job.visit
    ccd_refs = [CcdDataRef(visit=visit, ccd=ccd_name) for ccd_name in await ds.list_ccds(visit)]
    try:
        ccd_generator_map = await _generate_single_fits_tiles(job, ccd_refs)
        await _merge_tiles(job, ccd_generator_map)
        await _transfer_tiles(job)
    finally:
        async with job.status.watch():
            job.status.stage = 'done'
        await _cleanup(job)


def quicklook_pipeline():
    async def generate_single_fits_tiles(job: Job):
        visit = job.visit
        try:
            ccd_refs = [CcdDataRef(visit=visit, ccd=ccd_name) for ccd_name in await ds.list_ccds(visit)]
            ccd_generator_map = await _generate_single_fits_tiles(job, ccd_refs)
            return job, ccd_generator_map
        except:
            await finalize(job)
            raise

    async def merge_tiles(args: tuple[Job, dict[CcdName, str]]):
        job, ccd_generator_map = args
        try:
            await _merge_tiles(job, ccd_generator_map)
            return job
        except:
            await finalize(job)
            raise

    async def transfer_tiles(job: Job):
        try:
            await _transfer_tiles(job)
            return job
        except:
            await finalize(job)
            raise

    async def finalize(job: Job):
        async with job.status.watch():
            job.status.stage = 'done'
        await _cleanup(job)
        return job

    return (
        Pipeline(
            Stage(
                generate_single_fits_tiles,
                parallel=config.pipeline_generate_single_fits_tiles,
            )
        )
        .append(
            Stage(
                merge_tiles,
                parallel=config.pipeline_merge_tiles,
            )
        )
        .append(
            Stage(
                # transferステージ。ここが一番時間がかかる
                # 1jobあたり20GBのローカルストレージが必要
                transfer_tiles,
                parallel=config.pipeline_transfer_tiles,
                queue_capacity=config.pipeline_transfer_queue_size,
            )
        )
        .append(Stage(finalize))
    )


async def _generate_single_fits_tiles(job: Job, ccd_refs: list[CcdDataRef]):
    async with job.status.watch():
        job.status.stage = 'generate_single_fits_tiles'

    ccd_generator_map: dict[CcdName, str] = {}
    ccd_metadata_dict: dict[CcdName, CcdMetadata] = {}

    rpcs = [Rpc.create(generate_single_fits_tiles, job, ccd_ref) for ccd_ref in ccd_refs]

    async def on_yield(msg: YieledValue):
        match msg:
            case YieledValue(value=Progress() as p, args=(_, ccd_ref)):
                ccd_name = cast(CcdDataRef, ccd_ref).ccd
                async with job.status.watch():
                    job.status.generate_single_fits_tiles[ccd_name] = p
            case YieledValue(value=ReturnValue(value=CcdMetadata() as ccd_metadata)):
                ccd_metadata_dict[ccd_metadata.ccd_name] = ccd_metadata

    async for result in adaptive_map_rpc(rpcs, stream=True, on_yield=on_yield):
        ccd_generator_map[result.args[1].ccd] = rpc_endpoint(result.generator_id)

    await rpc_scatter(Rpc.create(_save_job_metadata_rpc, job))

    return ccd_generator_map


def _save_job_metadata_rpc(job: Job):
    job.local_storage.metadata.save()


async def _merge_tiles(job: Job, ccd_generator_map: dict[CcdName, str]):
    async with job.status.watch():
        job.status.stage = 'merge_tiles'

    dist_config = CcdDistributionConfig(ccd_generator_map, get_available_generators())
    await rpc_scatter(Rpc.create(_save_ccd_distribution_config_rpc, job, dist_config))

    async def on_yield(msg):
        match msg:
            case YieledValue(value=Progress() as p, generator_id=generator_id):
                async with job.status.watch():
                    job.status.merge_tiles[generator_id] = p

    await rpc_scatter(Rpc.create(merge_single_fits_tiles, job), stream=True, on_yield=on_yield)
    await rpc_scatter(Rpc.create(_clear_single_fits_tiles_rpc, job))


def _clear_single_fits_tiles_rpc(job: Job):
    job.local_storage.single_fits_tile.clear()


def _save_ccd_distribution_config_rpc(job: Job, dist_config: CcdDistributionConfig):
    job.local_storage.ccd_distribution_config.save(dist_config)


async def _transfer_tiles(job: Job):
    async with job.status.watch() as status:
        status.stage = 'transfer_tiles'

    uploaded_size = 0

    async def on_yield(msg):
        nonlocal uploaded_size
        match msg:
            case YieledValue(value=Progress() as p, generator_id=generator_id):
                async with job.status.watch():
                    job.status.transfer_tiles[generator_id] = p
            case YieledValue(value=ReturnValue(value=int() as _uploaded_size), generator_id=generator_id):
                uploaded_size += _uploaded_size

    await rpc_scatter(Rpc.create(transfer_tiles, job), stream=True, on_yield=on_yield)
    return TransferTilesResult(
        uploaded_size=uploaded_size,
    )


@dataclass
class TransferTilesResult:
    uploaded_size: int


async def _cleanup(job: Job):
    await rpc_scatter(Rpc.create(_cleanup_rpc, job))


def _cleanup_rpc(job: Job):
    job.local_storage.clear_all()
