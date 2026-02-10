import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from typing import Callable, Coroutine, TypeVar, cast

import quicklook.mylogging
from quicklook.comm.rpc_worker import YieledValue, rpc_scatter, rpc_scatter_stream
from quicklook.config import config
from quicklook.coordinator.housekeeping import run_housekeeping
from quicklook.datasource import get_datasource
from quicklook.db import Quicklook, get_db_session
from quicklook.generator.generate_single_fits_tiles import CcdMetadata
from quicklook.generator.merge_single_tile_fits import merge_single_fits_tiles
from quicklook.generator.transfer_fits_headers import transfer_fits_headers
from quicklook.generator.transfer_tiles import transfer_tiles
from quicklook.job.job import Job
from quicklook.job.tile_profile import TileProfile
from quicklook.types import CcdDataRef, Progress, ReturnValue
from quicklook.utils.pipeline import Pipeline, Stage

from .generate_single_fits_tiles_coordinator import generate_single_fits_tiles_coordinator

logger = quicklook.mylogging.getLogger(__name__)

ds = get_datasource()


T = TypeVar('T')


@dataclass
class _PipelineResult:
    job: Job
    ccd_metadata_list: list[CcdMetadata] = field(default_factory=list)
    uploaded_size: int = 0
    tile_profile: TileProfile = field(default_factory=TileProfile)


def quicklook_pipeline():
    def with_stage_timeout(
        stage_name: str,
    ) -> Callable[
        [Callable[[_PipelineResult], Coroutine[None, None, T]]], Callable[[_PipelineResult], Coroutine[None, None, T]]
    ]:
        """ステージにタイムアウトとエラーハンドリングを適用するデコレーター"""

        def decorator(
            func: Callable[[_PipelineResult], Coroutine[None, None, T]],
        ) -> Callable[[_PipelineResult], Coroutine[None, None, T]]:
            async def wrapper(result: _PipelineResult) -> T:
                try:
                    return await asyncio.wait_for(func(result), timeout=config.pipeline_stage_timeout)
                except asyncio.TimeoutError:
                    error_msg = f"Stage {stage_name} timed out after {config.pipeline_stage_timeout} seconds"
                    logger.error(error_msg)
                    await _finalize_error(result.job, error_msg)
                    from quicklook.comm.coordinator import shutdown_all_generators

                    await shutdown_all_generators()
                    raise
                except Exception as e:
                    await _finalize_error(result.job, str(e))
                    raise

            return wrapper

        return decorator

    async def arg_adapter(job: Job):
        return _PipelineResult(job=job)

    @with_stage_timeout('generate_single_fits_tiles')
    async def generate_single_fits_tiles(result: _PipelineResult):
        job = result.job
        visit = job.visit

        _ensure_users_exist_for_job(job)

        async with job.watcher.watch_status():
            job.status.stage = 'generate_single_fits_tiles'

        await _create_quicklook_record(job)
        ccd_refs = [CcdDataRef(visit=visit, ccd=ccd_name) for ccd_name in await ds.list_ccds(visit)]
        result.tile_profile.generate_single_fits_tiles.start()
        ccd_metadata_list = await generate_single_fits_tiles_coordinator(job, ccd_refs)
        result.tile_profile.generate_single_fits_tiles.finish()
        result.ccd_metadata_list = ccd_metadata_list
        return result

    @with_stage_timeout('merge_tiles')
    async def merge_tiles(result: _PipelineResult):
        job = result.job
        result.tile_profile.merge_tiles.start()
        await _merge_tiles(job)
        result.tile_profile.merge_tiles.finish()
        return result

    @with_stage_timeout('upload_to_object_storage')
    async def upload_to_object_storage(result: _PipelineResult):
        job = result.job
        result.tile_profile.upload_to_object_storage.start()
        uploaded_size = await _transfer_tiles(job)
        uploaded_size += +await _transfer_fits_headers(job) + await _transfer_quicklook_metadata(
            job, result.ccd_metadata_list
        )
        result.tile_profile.upload_to_object_storage.finish()
        result.uploaded_size = uploaded_size
        return result

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

    await rpc_scatter_stream(on_yield, merge_single_fits_tiles, job)


def _clear_single_fits_tiles_rpc(job: Job):
    job.local_storage.single_fits_tile.clear()


async def _transfer_tiles(job: Job):
    _ensure_users_exist_for_job(job)

    async with job.watcher.watch_status():
        job.status.stage = 'upload_to_object_storage'

    # TODO: 本当はディスク節約のため_merge_tilesの最後でやりたいのだが
    # 先にstageをupload_to_object_storageに変更する必要がある。
    await rpc_scatter(_clear_single_fits_tiles_rpc, job)

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

    await rpc_scatter_stream(on_yield, transfer_tiles, job)
    return uploaded_size


async def _transfer_quicklook_metadata(job: Job, ccd_metadata_list: list[CcdMetadata]) -> int:
    """quicklookメタデータをobject storageに保存"""
    return await job.object_storage.put_ccd_metadata_list(ccd_metadata_list)


async def _transfer_fits_headers(job: Job) -> int:
    """FITS headerをobject storageにアップロードする"""
    uploaded_sizes = await rpc_scatter(transfer_fits_headers, job)
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

    profile_summary = result.tile_profile.summary()
    logger.info(
        "Tile profile for %s: generate=%.1fs, merge=%.1fs, upload=%.1fs, total=%.1fs",
        job.visit,
        profile_summary['generate_single_fits_tiles'],
        profile_summary['merge_tiles'],
        profile_summary['upload_to_object_storage'],
        profile_summary['total'],
    )
    await job.object_storage.put_tile_profile(profile_summary)

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

    await rpc_scatter(_cleanup_rpc, job)
    await run_housekeeping()
    return job


async def _finalize_error(job: Job, error_message: str | None = None):
    """エラー時の処理：DBレコードとobject storageを削除"""
    async with job.watcher.watch_status():
        job.status.stage = 'error'
        if error_message:
            job.status.error_message = error_message

    # エラー時はobject storageのデータを削除
    logger.info(f"Deleting object storage data for {job.visit} due to error")
    await job.object_storage.delete_all()

    # DBレコードも削除（カスケード削除でAccessも削除される）
    async with get_db_session() as session:
        from sqlalchemy import select

        stmt = select(Quicklook).where(Quicklook.visit_name == str(job.visit))
        result = await session.execute(stmt)
        quicklook = result.scalar_one_or_none()
        if quicklook:
            await session.delete(quicklook)
            await session.commit()
            logger.info(f"Deleted quicklook record for {job.visit} due to error")
        else:
            logger.warning(f"Quicklook record for {job.visit} not found during error cleanup")

    await rpc_scatter(_cleanup_rpc, job)
    await run_housekeeping()
    return job


def _cleanup_rpc(job: Job):
    job.local_storage.clear_all()
