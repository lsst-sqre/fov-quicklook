from dataclasses import dataclass, field
from datetime import datetime
from typing import cast

import quicklook.logging
from quicklook.comm.coordinator import get_available_generators
from quicklook.comm.types import GeneratorId
from quicklook.comm.rpc_worker import YieledValue, adaptive_map_rpc, rpc_endpoint, rpc_scatter
from quicklook.config import config
from quicklook.datasource import get_datasource
from quicklook.db import Quicklook, get_db_session
from quicklook.generator.generate_single_fits_tiles import CcdMetadata, generate_single_fits_tiles
from quicklook.generator.merge_single_tile_fits import merge_single_fits_tiles
from quicklook.generator.transfer_fits_headers import transfer_fits_headers
from quicklook.generator.transfer_tiles import transfer_tiles
from quicklook.job.job import Job
from quicklook.job.local_storage import CcdDistributionConfig
from quicklook.types import CcdDataRef, CcdName, Progress, ReturnValue
from quicklook.utils.pipeline import Pipeline, Stage

logger = quicklook.logging.getLogger(__name__)

ds = get_datasource()


@dataclass
class _PipelineResult:
    job: Job
    ccd_metadata_list: list[CcdMetadata] = field(default_factory=list)
    uploaded_size: int = 0


def quicklook_pipeline():
    async def arg_adapter(job: Job):
        return _PipelineResult(job=job)

    async def generate_single_fits_tiles(result: _PipelineResult):
        job = result.job
        visit = job.visit
        try:
            # DBに初期レコードを作成
            await _create_quicklook_record(job)
            ccd_refs = [CcdDataRef(visit=visit, ccd=ccd_name) for ccd_name in await ds.list_ccds(visit)]
            ccd_metadata_list = await _generate_single_fits_tiles(job, ccd_refs)
            result.ccd_metadata_list = ccd_metadata_list
            return result
        except Exception:  # pragma: no cover
            await _finalize_error(job)
            raise

    async def merge_tiles(result: _PipelineResult):
        job = result.job
        try:
            await _merge_tiles(job)
            return result
        except Exception:  # pragma: no cover
            await _finalize_error(job)
            raise

    async def upload_to_object_storage(result: _PipelineResult):
        job = result.job
        try:
            uploaded_size = await _transfer_tiles(job)
            uploaded_size += +await _transfer_fits_headers(job) + await _transfer_quicklook_metadata(
                job, result.ccd_metadata_list
            )
            result.uploaded_size = uploaded_size
            return result
        except Exception:  # pragma: no cover
            await _finalize_error(job)
            raise

    async def finalize_success(result: _PipelineResult):
        return await _finalize_success(result)

    def select_next_result(results: list[_PipelineResult]):
        results.sort(key=lambda r: r.job.priority.sort_key())
        return results.pop(0)

    return (
        Pipeline(Stage(arg_adapter))
        .append(
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
                upload_to_object_storage,
                parallel=config.pipeline_transfer_queue_size,
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

    async with job.watcher.watch_status():
        job.status.stage = 'generate_single_fits_tiles'

    ccd_generator_map: dict[CcdName, GeneratorId] = {}
    ccd_metadata_list: list[CcdMetadata] = []

    # 各CCDに対するRPCタスクの引数リストを作成
    items = [(job, ccd_ref) for ccd_ref in ccd_refs]

    async def on_yield(msg: YieledValue):
        match msg:
            case YieledValue(value=Progress() as p, args=(_, ccd_ref)):
                ccd_name = cast(CcdDataRef, ccd_ref).ccd
                async with job.watcher.watch_status():
                    job.status.generate_single_fits_tiles[ccd_name] = p
            case YieledValue(value=ReturnValue(value=CcdMetadata() as ccd_metadata)):
                ccd_metadata_list.append(ccd_metadata)
            case _:  # pragma: no cover
                raise ValueError(f"Unexpected message: {msg}")

    async for result in adaptive_map_rpc(generate_single_fits_tiles, items, stream=True, on_yield=on_yield):
        ccd_generator_map[result.args[1].ccd] = rpc_endpoint(result.generator_id)

    dist_config = CcdDistributionConfig(ccd_generator_map, get_available_generators())
    async with job.watcher.notify_shared_large_status():
        job.shared_large_status.dist_config = dist_config
        job.shared_large_status.ccd_metadata_list = ccd_metadata_list

    await rpc_scatter(_save_job_metadata_rpc, args=(job,))
    await rpc_scatter(_save_ccd_distribution_config_rpc, args=(job, dist_config))

    return ccd_metadata_list


def _save_job_metadata_rpc(job: Job):
    job.local_storage.metadata.save()


async def _merge_tiles(job: Job):
    _ensure_users_exist_for_job(job)

    async with job.watcher.watch_status():
        job.status.stage = 'merge_tiles'

    async def on_yield(msg):
        match msg:
            case YieledValue(value=Progress() as p, generator_id=generator_id):
                async with job.watcher.watch_status():
                    job.status.merge_tiles[generator_id] = p
            case _:  # pragma: no cover
                raise ValueError(f"Unexpected message: {msg}")

    await rpc_scatter(merge_single_fits_tiles, args=(job,), stream=True, on_yield=on_yield)


def _clear_single_fits_tiles_rpc(job: Job):
    job.local_storage.single_fits_tile.clear()


def _save_ccd_distribution_config_rpc(job: Job, dist_config: CcdDistributionConfig):
    job.local_storage.ccd_distribution_config.save(dist_config)


async def _transfer_tiles(job: Job):
    _ensure_users_exist_for_job(job)

    async with job.watcher.watch_status():
        job.status.stage = 'upload_to_object_storage'

    # TODO: 本当はディスク節約のため_merge_tilesの最後でやりたいのだが
    # 先にstageをupload_to_object_storageに変更する必要がある。
    await rpc_scatter(_clear_single_fits_tiles_rpc, args=(job,))

    uploaded_size = 0

    async def on_yield(msg):
        nonlocal uploaded_size
        match msg:
            case YieledValue(value=Progress() as p, generator_id=generator_id):
                async with job.watcher.watch_status():
                    job.status.transfer_tiles[generator_id] = p
            case YieledValue(value=ReturnValue(value=int() as _uploaded_size), generator_id=generator_id):
                uploaded_size += _uploaded_size
            case _:  # pragma: no cover
                raise ValueError(f"Unexpected message: {msg}")

    await rpc_scatter(transfer_tiles, args=(job,), stream=True, on_yield=on_yield)
    return uploaded_size


async def _transfer_quicklook_metadata(job: Job, ccd_metadata_list: list[CcdMetadata]) -> int:
    """quicklookメタデータをobject storageに保存"""
    return await job.object_storage.put_ccd_metadata_list(ccd_metadata_list)


async def _transfer_fits_headers(job: Job) -> int:
    """FITS headerをobject storageにアップロードする"""
    uploaded_sizes = cast(list[int], await rpc_scatter(transfer_fits_headers, args=(job,)))
    return sum(uploaded_sizes)


async def _create_quicklook_record(job: Job):
    """DBにquicklookの初期レコードを作成（ready=False）"""
    async with get_db_session() as session:
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


async def _finalize_success(result: _PipelineResult):
    """正常終了時の処理：DBレコードをready=Trueに更新"""
    job = result.job
    total_uploaded_size = result.uploaded_size
    async with job.watcher.watch_status():
        job.status.stage = 'ready'

    # DBレコードを更新
    async with get_db_session() as session:
        from sqlalchemy import update

        stmt = (
            update(Quicklook)
            .where(Quicklook.visit_name == str(job.visit))
            .values(ready=True, disk_usage=total_uploaded_size)
        )
        await session.execute(stmt)
        await session.commit()
        logger.info(f"Updated quicklook record for {job.visit}: ready=True, disk_usage={total_uploaded_size}")

    await rpc_scatter(_cleanup_rpc, args=(job,))
    return job


async def _finalize_error(job: Job):
    """エラー時の処理：DBレコードとobject storageを削除"""
    async with job.watcher.watch_status():
        job.status.stage = 'error'

    # エラー時はobject storageのデータを削除
    logger.info(f"Deleting object storage data for {job.visit} due to error")
    await job.object_storage.delete_all()

    # DBレコードも削除
    async with get_db_session() as session:
        from sqlalchemy import delete

        stmt = delete(Quicklook).where(Quicklook.visit_name == str(job.visit))
        await session.execute(stmt)
        await session.commit()
        logger.info(f"Deleted quicklook record for {job.visit} due to error")

    await rpc_scatter(_cleanup_rpc, args=(job,))
    return job


def _cleanup_rpc(job: Job):
    job.local_storage.clear_all()
