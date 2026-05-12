import asyncio
import pickle
import re
import time
from contextlib import asynccontextmanager
from dataclasses import dataclass
from functools import cached_property
from typing import Annotated, AsyncGenerator, Literal

import websockets
from fastapi import APIRouter, Depends, FastAPI, HTTPException, WebSocket
from pydantic import TypeAdapter
from sqlalchemy import select

import quicklook.mylogging
from quicklook.config import config
from quicklook.coordinator.api.types import (
    CreateQuicklookRequest,
    JobStatusList,
    SharedStatusMessage,
    SharedStatusMessageJobSharedLargeStatus,
    SharedStatusMessageJobStatusList,
)
from quicklook.datasource import get_datasource
from quicklook.datasource.types import VisitResolutionError
from quicklook.db import Quicklook, get_db_session
from quicklook.frontend.api.deps import dep_visit_name
from quicklook.generator.generate_single_fits_tiles import CcdMetadata
from quicklook.job.shared_large_status import JobSharedLargeStatus
from quicklook.job.status import JobStatus
from quicklook.object_storage import VisitObjectStorage
from quicklook.tileinfo import focal_plane_wcs
from quicklook.types import CcdName, Progress, VisitName
from quicklook.utils.broadcast import Broadcast
from quicklook.utils.hash_utils import json_digest
from quicklook.utils.http_request import http_request
from quicklook.utils.s3 import NoSuchKey
from quicklook.utils.system_status import get_memory_current
from quicklook.utils.websocket import run_until_disconnect, safe_websocket


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with _quicklook_status_relay():
        yield


router = APIRouter()

logger = quicklook.mylogging.getLogger(__name__)
_active_job_status_ws_connections = 0
_active_quicklook_metadata_ws_connections = 0


@router.post('/api/quicklooks', description='Create a quicklook')
async def create_quicklook(params: CreateQuicklookRequest):
    try:
        visit = (await get_datasource().resolve_visit_info(VisitName(params.visit))).visit_name
    except VisitResolutionError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    return await http_request(
        'post',
        f'{config.coordinator_base_url}/quicklooks',
        json=CreateQuicklookRequest(visit=str(visit)).model_dump(),
    )


@router.post('/api/quicklooks/{visit_name}/vote')
async def vote_quicklook(visit_name: Annotated[VisitName, Depends(dep_visit_name)]):
    return await http_request(
        'post',
        f'{config.coordinator_base_url}/quicklooks/{visit_name}/vote',
    )


@router.post('/api/quicklooks/{visit_name}/unvote')
async def unvote_quicklook(visit_name: Annotated[VisitName, Depends(dep_visit_name)]):
    return await http_request(
        'post',
        f'{config.coordinator_base_url}/quicklooks/{visit_name}/unvote',
    )


@router.get('/api/quicklooks/*/status', response_model=JobStatusList)
async def get_all_quicklook_jobs():
    jobs = _job_status_dict.last_value()
    if jobs is not None:
        return jobs
    jobs = await http_request(
        'get',
        f'{config.coordinator_base_url}/quicklooks/*/status',
    )
    _job_status_dict.put(jobs)
    return jobs


type_adapter_JsonStatus = TypeAdapter(JobStatus | None)


@router.websocket('/api/quicklooks/*/status.ws')
async def websocket_quicklooks_status(ws: WebSocket):
    global _active_job_status_ws_connections
    _active_job_status_ws_connections += 1
    logger.info(
        "Frontend quicklooks status ws connected active_connections=%d rss=%d active_jobs=%d",
        _active_job_status_ws_connections,
        get_memory_current(),
        len(_job_status_dict.last_value() or {}),
    )
    try:
        async with safe_websocket(ws):

            async def send_job_updates():
                async for jobs in _job_status_dict.subscribe():
                    await ws.send_json({visit: type_adapter_JsonStatus.dump_python(job) for visit, job in jobs.items()})

            await run_until_disconnect(ws, send_job_updates())
    finally:
        _active_job_status_ws_connections -= 1
        logger.info(
            "Frontend quicklooks status ws disconnected active_connections=%d rss=%d active_jobs=%d",
            _active_job_status_ws_connections,
            get_memory_current(),
            len(_job_status_dict.last_value() or {}),
        )


@dataclass
class QuicklookMetadataReady:
    visit_name: VisitName
    ccd_metadata_list: list[CcdMetadata]
    wcs: dict
    type: Literal['ready'] = 'ready'


@dataclass
class QuicklookMetadataProgress:
    visit_name: VisitName
    progress: dict[CcdName, Progress]
    type: Literal['progress'] = 'progress'


@dataclass
class QuicklookMetadataPending:
    visit_name: VisitName
    type: Literal['pending'] = 'pending'


@dataclass
class QuicklookMetadataError:
    visit_name: VisitName
    type: Literal['error'] = 'error'


type QuicklookMetadata = QuicklookMetadataReady | QuicklookMetadataProgress | QuicklookMetadataPending | QuicklookMetadataError
type_adapter_QuicklookMetadata = TypeAdapter(QuicklookMetadata)


@router.get('/api/quicklooks/{visit_name}/quicklook_metadata', response_model=QuicklookMetadata)
async def get_quicklook_metadata(
    visit: Annotated[VisitName, Depends(dep_visit_name)],
):
    if metadata := await _get_quicklook_metadata_from_db(visit):
        _log_metadata_delivery(
            channel='http',
            source='db',
            visit=visit,
            metadata=metadata,
        )
        return metadata

    async for metadata in _get_quicklook_metadata_from_shared_status(visit):
        _log_metadata_delivery(
            channel='http',
            source='shared_status',
            visit=visit,
            metadata=metadata,
        )
        return metadata


@router.get('/api/quicklooks/{visit_name}/time_profile')
async def get_time_profile(
    visit: Annotated[VisitName, Depends(dep_visit_name)],
):
    object_storage = VisitObjectStorage(visit)
    try:
        return await object_storage.get_time_profile()
    except (NoSuchKey, Exception):
        return None


@router.websocket('/api/quicklooks/{visit_name}/quicklook_metadata.ws')
async def websocket_quicklook_metadata(
    ws: WebSocket,
    visit: Annotated[VisitName, Depends(dep_visit_name)],
):
    global _active_quicklook_metadata_ws_connections
    _active_quicklook_metadata_ws_connections += 1
    logger.info(
        "Frontend quicklook metadata ws connected visit=%s active_connections=%d rss=%d",
        visit,
        _active_quicklook_metadata_ws_connections,
        get_memory_current(),
    )
    try:
        async with safe_websocket(ws):

            async def push():
                if metadata := await _get_quicklook_metadata_from_db(visit):
                    _log_metadata_delivery(
                        channel='ws',
                        source='db',
                        visit=visit,
                        metadata=metadata,
                    )
                    await ws.send_json(type_adapter_QuicklookMetadata.dump_python(metadata))
                    return

                last_digest = None
                async for metadata in _get_quicklook_metadata_from_shared_status(visit):
                    metadata_json = type_adapter_QuicklookMetadata.dump_python(metadata)
                    current_digest = json_digest(metadata_json)
                    if current_digest == last_digest:
                        continue
                    _log_metadata_delivery(
                        channel='ws',
                        source='shared_status',
                        visit=visit,
                        metadata=metadata,
                    )
                    await ws.send_json(metadata_json)
                    last_digest = current_digest

            await run_until_disconnect(ws, push())
    finally:
        _active_quicklook_metadata_ws_connections -= 1
        logger.info(
            "Frontend quicklook metadata ws disconnected visit=%s active_connections=%d rss=%d",
            visit,
            _active_quicklook_metadata_ws_connections,
            get_memory_current(),
        )


async def _get_quicklook_metadata_from_db(visit: VisitName) -> QuicklookMetadata | None:
    async with get_db_session() as session:
        result = await session.execute(
            select(Quicklook).where(
                Quicklook.visit_name == visit,
                Quicklook.ready == True,
            )
        )
        quicklook: Quicklook | None = result.scalar_one_or_none()
        if quicklook:
            ccd_metadata_list = await VisitObjectStorage(visit).get_ccd_metadata_list()
            return QuicklookMetadataReady(
                visit_name=visit,
                ccd_metadata_list=ccd_metadata_list,
                wcs=focal_plane_wcs(),
            )


async def _get_quicklook_metadata_from_shared_status(visit: VisitName) -> AsyncGenerator[QuicklookMetadata, None]:
    job_status = None
    async for jobs in _job_status_dict.subscribe():
        # TODO: refactoring
        # タイル生成jobが完了すると即座にjobsからエントリーが消える
        # その場合はQuicklookMetadataReadyを返したいので。
        job_status = jobs.get(visit, job_status)
        match job_status:
            case None | JobStatus(stage='queued'):
                yield QuicklookMetadataPending(visit_name=visit)
            case JobStatus(stage='generate_single_fits_tiles'):
                yield QuicklookMetadataProgress(
                    visit_name=visit,
                    progress=job_status.generate_single_fits_tiles,
                )
            case JobStatus(stage='merge_tiles' | 'upload_to_object_storage'):
                yield QuicklookMetadataReady(
                    visit_name=visit,
                    ccd_metadata_list=_get_ccd_metadata_list_for_shared_status(visit),
                    wcs=focal_plane_wcs(),
                )
            case JobStatus(stage='ready'):
                yield QuicklookMetadataReady(
                    visit_name=visit,
                    ccd_metadata_list=_get_ccd_metadata_list_for_shared_status(visit, allow_recent_ready=True),
                    wcs=focal_plane_wcs(),
                )
            case JobStatus(stage='error'):
                yield QuicklookMetadataError(visit_name=visit)
            case _:  # pragma: no cover
                raise ValueError(f"Unknown job status stage: {job_status.stage}")


@dataclass
class RecentReadyMetadata:
    ccd_metadata_list: list[CcdMetadata]
    expires_at: float


_job_shared_large_status_dict: dict[VisitName, JobSharedLargeStatus] = {}
_recent_ready_metadata_dict: dict[VisitName, RecentReadyMetadata] = {}
_job_status_dict = Broadcast[JobStatusList](max_queue_size=2)
_RECENT_READY_METADATA_TTL_SECONDS = 30.0
_STATUS_RELAY_RETRY_MAX_DELAY_SECONDS = 60


@dataclass
class QuicklookSharedStatus:
    visit_name: VisitName

    @cached_property
    def job_status(self) -> JobStatus | None:
        jobs = _job_status_dict.last_value()
        if jobs and (job_status := jobs.get(self.visit_name)):
            return job_status

    @cached_property
    def job(self):
        if self.job_status:
            return self.job_status.job

    @cached_property
    def _large_status(self) -> JobSharedLargeStatus | None:
        return _job_shared_large_status_dict.get(self.visit_name)

    @cached_property
    def dist_config(self):
        return self._large_status.dist_config if self._large_status else None


def _log_metadata_delivery(
    *,
    channel: str,
    source: str,
    visit: VisitName,
    metadata: QuicklookMetadata,
) -> None:
    if isinstance(metadata, QuicklookMetadataReady):
        metadata_type = 'ready'
        ccd_count = len(metadata.ccd_metadata_list)
    elif isinstance(metadata, QuicklookMetadataProgress):
        metadata_type = 'progress'
        ccd_count = len(metadata.progress)
    elif isinstance(metadata, QuicklookMetadataPending):
        metadata_type = 'pending'
        ccd_count = 0
    else:
        metadata_type = 'error'
        ccd_count = 0

    logger.info(
        "Frontend quicklook metadata channel=%s source=%s visit=%s metadata_type=%s ccd_count=%d active_jobs=%d large_status_entries=%d recent_ready_entries=%d active_large_status_ccds=%d recent_ready_ccds=%d rss=%d",
        channel,
        source,
        visit,
        metadata_type,
        ccd_count,
        len(_job_status_dict.last_value() or {}),
        len(_job_shared_large_status_dict),
        len(_recent_ready_metadata_dict),
        sum(len(status.ccd_metadata_list) for status in _job_shared_large_status_dict.values()),
        sum(len(status.ccd_metadata_list) for status in _recent_ready_metadata_dict.values()),
        get_memory_current(),
    )


def _log_shared_status_cache(reason: str, *, visit: VisitName | None = None, ccd_count: int | None = None) -> None:
    logger.info(
        "Frontend shared status cache reason=%s visit=%s ccd_count=%s active_jobs=%d large_status_entries=%d recent_ready_entries=%d active_large_status_ccds=%d recent_ready_ccds=%d rss=%d",
        reason,
        visit or '-',
        ccd_count if ccd_count is not None else '-',
        len(_job_status_dict.last_value() or {}),
        len(_job_shared_large_status_dict),
        len(_recent_ready_metadata_dict),
        sum(len(status.ccd_metadata_list) for status in _job_shared_large_status_dict.values()),
        sum(len(status.ccd_metadata_list) for status in _recent_ready_metadata_dict.values()),
        get_memory_current(),
    )


@asynccontextmanager
async def _quicklook_status_relay():
    main_task = asyncio.create_task(_status_relay_main_loop())
    async with _job_status_dict.activate():
        try:
            yield
        finally:
            main_task.cancel()
            try:
                await main_task
            except asyncio.CancelledError:
                pass


async def _status_relay_main_loop():
    global _job_shared_large_status_dict
    ws_url = f"{re.sub(r'^http://', 'ws://', config.coordinator_base_url)}/quicklooks/*/shared_status.ws"
    retry_count = 0

    while True:
        try:
            async with websockets.connect(ws_url, max_size=None) as ws:
                if retry_count:
                    logger.info(f"Reconnected to {ws_url} after {retry_count} retries")
                    retry_count = 0
                while True:
                    msg = _decode_shared_status_message(await ws.recv())
                    _apply_shared_status_message(msg)

        except Exception as e:
            retry_count += 1
            delay_seconds = min(2 ** (retry_count - 1), _STATUS_RELAY_RETRY_MAX_DELAY_SECONDS)
            logger.exception(
                f"Shared-status relay disconnected from {ws_url}: {e}. "
                f"Retrying in {delay_seconds} seconds (attempt {retry_count})"
            )
            await asyncio.sleep(delay_seconds)


def _decode_shared_status_message(msg_bytes: bytes | str) -> SharedStatusMessage:
    if not isinstance(msg_bytes, bytes):
        raise TypeError(f"Expected binary shared-status message, got {type(msg_bytes).__name__}")

    return pickle.loads(msg_bytes)


def _prune_recent_ready_metadata(now: float | None = None) -> None:
    global _recent_ready_metadata_dict

    if not _recent_ready_metadata_dict:
        return

    current_time = time.monotonic() if now is None else now
    _recent_ready_metadata_dict = {
        visit: metadata
        for visit, metadata in _recent_ready_metadata_dict.items()
        if metadata.expires_at > current_time
    }


def _get_ccd_metadata_list_for_shared_status(
    visit: VisitName,
    *,
    allow_recent_ready: bool = False,
) -> list[CcdMetadata]:
    _prune_recent_ready_metadata()

    if large_status := _job_shared_large_status_dict.get(visit):
        return large_status.ccd_metadata_list

    if allow_recent_ready and (recent_ready_metadata := _recent_ready_metadata_dict.get(visit)):
        return recent_ready_metadata.ccd_metadata_list

    raise KeyError(visit)


def _apply_shared_status_message(msg: SharedStatusMessage) -> None:
    global _job_shared_large_status_dict, _recent_ready_metadata_dict

    match msg:
        case SharedStatusMessageJobStatusList(data=data):
            previous_jobs = _job_status_dict.last_value() or {}
            current_time = time.monotonic()
            _prune_recent_ready_metadata(current_time)
            moved_to_recent_ready = False

            for visit, previous_status in previous_jobs.items():
                if visit in data:
                    continue

                large_status = _job_shared_large_status_dict.pop(visit, None)
                if previous_status.stage == 'ready' and large_status is not None:
                    # Keep only the metadata briefly so the UI can bridge the
                    # transition to object storage without retaining the full Job.
                    _recent_ready_metadata_dict[visit] = RecentReadyMetadata(
                        ccd_metadata_list=large_status.ccd_metadata_list,
                        expires_at=current_time + _RECENT_READY_METADATA_TTL_SECONDS,
                    )
                    moved_to_recent_ready = True

            _job_shared_large_status_dict = {
                visit: large_status
                for visit, large_status in _job_shared_large_status_dict.items()
                if visit in data
            }
            _job_status_dict.put(data)
            if moved_to_recent_ready:
                _log_shared_status_cache('job_status_list')
        case SharedStatusMessageJobSharedLargeStatus(visit=visit, data=data):
            _prune_recent_ready_metadata()
            _recent_ready_metadata_dict.pop(visit, None)
            _job_shared_large_status_dict[visit] = data
            jobs = _job_status_dict.last_value()
            if jobs:
                _job_shared_large_status_dict = {
                    visit: _job_shared_large_status_dict[visit]
                    for visit in jobs
                    if visit in _job_shared_large_status_dict
                }
            _log_shared_status_cache(
                'shared_large_status',
                visit=visit,
                ccd_count=len(data.ccd_metadata_list),
            )
