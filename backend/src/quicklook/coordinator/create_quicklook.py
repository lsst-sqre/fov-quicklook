import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any, cast

from quicklook.comm.coordinator import get_available_generators
from quicklook.comm.rpc import Rpc
from quicklook.comm.types import GeneratorId
from quicklook.config import config
from quicklook.datasource import get_datasource
from quicklook.db import Quicklook, get_session
from quicklook.generator.generate_single_fits_tiles import CcdMetadata, generate_single_fits_tiles
from quicklook.generator.merge_single_tile_fits import merge_single_fits_tiles
from quicklook.generator.transfer_fits_headers import transfer_fits_headers
from quicklook.generator.transfer_tiles import transfer_tiles
from quicklook.object_storage import VisitObjectStorage
from quicklook.job.job import Job
from quicklook.job.local_storage import CcdDistributionConfig
from quicklook.types import CcdDataRef, CcdName, Progress, ReturnValue
from quicklook.utils.pipeline import Pipeline, Stage

from ..comm.rpc_worker import YieledValue, adaptive_map_rpc, rpc_endpoint, rpc_scatter

logger = logging.getLogger(__name__)

ds = get_datasource()


@dataclass
class PipeLineResult:
    """パイプライン各ステージの結果を格納するコンテナ"""
    job: Job
    data: Any = None


async def create_quicklook(job: Job):  # pragma: no cover
    '''
    テスト用。
    本番ではパイプラインでquicklookを作成する。
    '''
    visit = job.visit
    ccd_refs = [CcdDataRef(visit=visit, ccd=ccd_name) for ccd_name in await ds.list_ccds(visit)]
    try:
        ccd_generator_map = await _generate_single_fits_tiles(job, ccd_refs)
        await _merge_tiles(job, ccd_generator_map)
        await _transfer_tiles(job)
    finally:
        await _finalize_error(job)


def quicklook_pipeline():
    async def generate_single_fits_tiles(result: PipeLineResult):
        job = result.job
        visit = job.visit
        try:
            # DBに初期レコードを作成
            await _create_quicklook_record(job)
            ccd_refs = [CcdDataRef(visit=visit, ccd=ccd_name) for ccd_name in await ds.list_ccds(visit)]
            ccd_generator_map = await _generate_single_fits_tiles(job, ccd_refs)
            return PipeLineResult(job=job, data=ccd_generator_map)
        except Exception:  # pragma: no cover
            await _finalize_error(job)
            raise

    async def merge_tiles(result: PipeLineResult):
        job = result.job
        ccd_generator_map = result.data
        try:
            await _merge_tiles(job, ccd_generator_map)
            return PipeLineResult(job=job)
        except Exception:  # pragma: no cover
            await _finalize_error(job)
            raise

    async def transfer_fits_headers(result: PipeLineResult):
        job = result.job
        try:
            uploaded_size = await _transfer_fits_headers(job)
            return PipeLineResult(job=job, data=uploaded_size)
        except Exception:  # pragma: no cover
            await _finalize_error(job)
            raise

    async def transfer_tiles(result: PipeLineResult):
        job = result.job
        fits_headers_size = result.data
        try:
            transfer_result = await _transfer_tiles(job)
            # FITS headersとtilesのサイズを合算
            total_uploaded_size = fits_headers_size + transfer_result.uploaded_size
            return PipeLineResult(job=job, data=total_uploaded_size)
        except Exception:  # pragma: no cover
            await _finalize_error(job)
            raise

    def select_next_result(results: list[PipeLineResult]):
        results.sort(key=lambda r: r.job.priority.sort_key())
        return results.pop(0)

    async def finalize_success(result: PipeLineResult):
        return await _finalize_success(result)

    return (
        Pipeline(
            Stage(
                generate_single_fits_tiles,
                parallel=config.pipeline_generate_single_fits_tiles,
                item_picker=select_next_result,
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
                transfer_fits_headers,
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
                item_picker=select_next_result,
            )
        )
        .append(Stage(finalize_success))
    )


def _ensure_users_exist_for_job(job: Job):
    if job.priority.user_count <= 0:  # pragma: no cover
        raise RuntimeError(f'No users for job {job.id} (visit={job.visit}), so skipping.')


async def _generate_single_fits_tiles(job: Job, ccd_refs: list[CcdDataRef]):
    _ensure_users_exist_for_job(job)

    async with job.watcher.watch():
        job.status.stage = 'generate_single_fits_tiles'

    ccd_generator_map: dict[CcdName, GeneratorId] = {}
    ccd_metadata_dict: dict[CcdName, CcdMetadata] = {}

    rpcs = [Rpc.create(generate_single_fits_tiles, job, ccd_ref) for ccd_ref in ccd_refs]

    async def on_yield(msg: YieledValue):
        match msg:
            case YieledValue(value=Progress() as p, args=(_, ccd_ref)):
                ccd_name = cast(CcdDataRef, ccd_ref).ccd
                async with job.watcher.watch():
                    job.status.generate_single_fits_tiles[ccd_name] = p
            case YieledValue(value=ReturnValue(value=CcdMetadata() as ccd_metadata)):
                ccd_metadata_dict[ccd_metadata.ccd_name] = ccd_metadata
            case _:  # pragma: no cover
                raise ValueError(f"Unexpected message: {msg}")

    async for result in adaptive_map_rpc(rpcs, stream=True, on_yield=on_yield):
        ccd_generator_map[result.args[1].ccd] = rpc_endpoint(result.generator_id)

    # JobStatusにccd_generator_mapを保存
    async with job.watcher.watch():
        job.status.ccd_generator_map = ccd_generator_map

    await rpc_scatter(Rpc.create(_save_job_metadata_rpc, job))
    
    # メタデータをobject storageに保存
    _save_quicklook_metadata(job, ccd_metadata_dict)

    return ccd_generator_map


def _save_quicklook_metadata(job: Job, ccd_metadata_dict: dict[CcdName, CcdMetadata]) -> None:
    """quicklookメタデータをobject storageに保存"""
    visit_storage = VisitObjectStorage(job.visit)
    metadata_list = list(ccd_metadata_dict.values())
    visit_storage.put_ccd_metadata_list_sync(metadata_list)


def _save_job_metadata_rpc(job: Job):
    job.local_storage.metadata.save()


async def _merge_tiles(job: Job, ccd_generator_map: dict[CcdName, GeneratorId]):
    _ensure_users_exist_for_job(job)

    async with job.watcher.watch():
        job.status.stage = 'merge_tiles'

    dist_config = CcdDistributionConfig(ccd_generator_map, get_available_generators())
    await rpc_scatter(Rpc.create(_save_ccd_distribution_config_rpc, job, dist_config))

    async def on_yield(msg):
        match msg:
            case YieledValue(value=Progress() as p, generator_id=generator_id):
                async with job.watcher.watch():
                    job.status.merge_tiles[generator_id] = p
            case _:  # pragma: no cover
                raise ValueError(f"Unexpected message: {msg}")

    await rpc_scatter(Rpc.create(merge_single_fits_tiles, job), stream=True, on_yield=on_yield)
    
    # transfer_fits_headersをmerge_tilesの後に実行
    await _transfer_fits_headers(job)
    
    await rpc_scatter(Rpc.create(_clear_single_fits_tiles_rpc, job))


def _clear_single_fits_tiles_rpc(job: Job):
    job.local_storage.single_fits_tile.clear()


def _save_ccd_distribution_config_rpc(job: Job, dist_config: CcdDistributionConfig):
    job.local_storage.ccd_distribution_config.save(dist_config)


async def _transfer_fits_headers(job: Job) -> int:
    """FITS headerをobject storageにアップロードする"""
    _ensure_users_exist_for_job(job)

    async with job.watcher.watch():
        job.status.stage = 'transfer_fits_headers'

    total_uploaded_size = 0

    async def on_yield(msg):
        nonlocal total_uploaded_size
        match msg:
            case YieledValue(value=Progress() as p, generator_id=generator_id):
                # Progressを記録（必要に応じて）
                pass
            case YieledValue(value=ReturnValue(value=int() as uploaded_size), generator_id=generator_id):
                total_uploaded_size += uploaded_size
            case _:  # pragma: no cover
                raise ValueError(f"Unexpected message: {msg}")

    await rpc_scatter(Rpc.create(transfer_fits_headers, job), stream=True, on_yield=on_yield)
    return total_uploaded_size


async def _transfer_tiles(job: Job):
    _ensure_users_exist_for_job(job)

    async with job.watcher.watch():
        job.status.stage = 'transfer_tiles'

    uploaded_size = 0

    async def on_yield(msg):
        nonlocal uploaded_size
        match msg:
            case YieledValue(value=Progress() as p, generator_id=generator_id):
                async with job.watcher.watch():
                    job.status.transfer_tiles[generator_id] = p
            case YieledValue(value=ReturnValue(value=int() as _uploaded_size), generator_id=generator_id):
                uploaded_size += _uploaded_size
            case _:  # pragma: no cover
                raise ValueError(f"Unexpected message: {msg}")

    await rpc_scatter(Rpc.create(transfer_tiles, job), stream=True, on_yield=on_yield)
    return TransferTilesResult(
        uploaded_size=uploaded_size,
    )


@dataclass
class TransferTilesResult:
    uploaded_size: int


async def _create_quicklook_record(job: Job):
    """DBにquicklookの初期レコードを作成（ready=False）"""
    async with get_session() as session:
        quicklook = Quicklook(
            visit_name=str(job.visit),
            job_id=job.id,
            disk_usage=0,
            ready=False,
            created_at=datetime.now(),
        )
        session.add(quicklook)
        await session.commit()
        logger.info(f"Created quicklook record for {job.visit} (job_id={job.id})")


async def _finalize_success(result: PipeLineResult):
    """正常終了時の処理：DBレコードをready=Trueに更新"""
    job = result.job
    total_uploaded_size = result.data
    async with job.watcher.watch():
        job.status.stage = 'done'
    
    # DBレコードを更新
    async with get_session() as session:
        from sqlalchemy import select, update
        stmt = (
            update(Quicklook)
            .where(Quicklook.visit_name == str(job.visit))
            .values(ready=True, disk_usage=total_uploaded_size)
        )
        await session.execute(stmt)
        await session.commit()
        logger.info(f"Updated quicklook record for {job.visit}: ready=True, disk_usage={total_uploaded_size}")
    
    await rpc_scatter(Rpc.create(_cleanup_rpc, job))
    return job


async def _finalize_error(job: Job):
    """エラー時の処理：DBレコードとobject storageを削除"""
    async with job.watcher.watch():
        job.status.stage = 'error'
    
    # エラー時はobject storageのデータを削除
    logger.info(f"Deleting object storage data for {job.visit} due to error")
    await job.object_storage.delete_all()
    
    # DBレコードも削除
    async with get_session() as session:
        from sqlalchemy import delete
        stmt = delete(Quicklook).where(Quicklook.visit_name == str(job.visit))
        await session.execute(stmt)
        await session.commit()
        logger.info(f"Deleted quicklook record for {job.visit} due to error")
    
    await rpc_scatter(Rpc.create(_cleanup_rpc, job))
    return job


def _cleanup_rpc(job: Job):
    job.local_storage.clear_all()
