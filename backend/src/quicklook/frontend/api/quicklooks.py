import asyncio
import quicklook.logging
import os
import pickle
import re
import signal
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import Annotated, AsyncGenerator, Callable, Literal, TypeVar

import websockets
from fastapi import APIRouter, Depends, FastAPI, WebSocket
from pydantic import TypeAdapter
from sqlalchemy import select

from quicklook.config import config
from quicklook.coordinator.api.types import CreateQuicklookRequest, JobStatusList, SharedStatusMessage, SharedStatusMessageJobSharedLargeStatus, SharedStatusMessageJobStatusList
from quicklook.db import Quicklook, get_db_session
from quicklook.frontend.api.deps import dep_visit_name
from quicklook.generator.generate_single_fits_tiles import CcdMetadata
from quicklook.job.job import Job
from quicklook.job.shared_large_status import JobSharedLargeStatus
from quicklook.job.status import JobStatus
from quicklook.object_storage import VisitObjectStorage
from quicklook.types import CcdName, Progress, VisitName
from quicklook.utils.broadcast import Broadcast
from quicklook.utils.hash_utils import json_digest
from quicklook.utils.http_request import http_request
from quicklook.utils.websocket import run_until_disconnect, safe_websocket


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with _quicklook_status_relay():
        yield


router = APIRouter()

logger = quicklook.logging.getLogger(__name__)


@router.post('/api/quicklooks', description='Create a quicklook')
async def create_quicklook(params: CreateQuicklookRequest):
    return await http_request(
        'post',
        f'{config.coordinator_base_url}/quicklooks',
        json=params.model_dump(),
    )


@router.get('/api/quicklooks/*/status', response_model=JobStatusList)
async def get_all_quicklook_jobs():
    # 開発用途
    async for jobs in _job_status_dict.subscribe():
        return jobs


type_adapter_JsonStatus = TypeAdapter(JobStatus | None)


@router.websocket('/api/quicklooks/*/status.ws')
async def websocket_quicklooks_status(ws: WebSocket):
    # 開発用途
    async with safe_websocket(ws):

        async def send_job_updates():
            async for jobs in _job_status_dict.subscribe():
                await ws.send_json({visit: type_adapter_JsonStatus.dump_python(job) for visit, job in jobs.items()})

        await run_until_disconnect(ws, send_job_updates())


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
class QuicklookMetadataError:
    visit_name: VisitName
    type: Literal['error'] = 'error'


type QuicklookMetadata = QuicklookMetadataReady | QuicklookMetadataProgress | QuicklookMetadataError
type_adapter_QuicklookMetadata = TypeAdapter(QuicklookMetadata)


@router.get('/api/quicklooks/{visit_name}/quicklook_metadata', response_model=QuicklookMetadata)
async def get_quicklook_metadata(
    visit: Annotated[VisitName, Depends(dep_visit_name)],
):
    if metadata := await _get_quicklook_metadata_from_db(visit):
        return metadata

    async for metadata in _get_quicklook_metadata_from_shared_status(visit):
        return metadata


@router.websocket('/api/quicklooks/{visit_name}/quicklook_metadata.ws')
async def websocket_quicklook_metadata(
    ws: WebSocket,
    visit: Annotated[VisitName, Depends(dep_visit_name)],
):
    async with safe_websocket(ws):

        async def push():
            if metadata := await _get_quicklook_metadata_from_db(visit):
                await ws.send_json(type_adapter_QuicklookMetadata.dump_python(metadata))
                return

            # async for metadata in _yield_on_digest_change(
            #     _get_quicklook_metadata_from_shared_status(visit),
            #     json_digest,
            # ):
            #     await ws.send_json(type_adapter_QuicklookMetadata.dump_python(metadata))
            async for metadata in _get_quicklook_metadata_from_shared_status(visit):
                await ws.send_json(type_adapter_QuicklookMetadata.dump_python(metadata))

        await run_until_disconnect(ws, push())


T = TypeVar('T')


async def _yield_on_digest_change(g: AsyncGenerator, digest: Callable[[T], bytes]) -> AsyncGenerator[T, None]:
    last_digest = None
    async for value in g:
        current_digest = digest(value)
        if current_digest != last_digest:
            yield value
            last_digest = current_digest


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
                wcs=_quicklook_metadata_wcs(),
            )


async def _get_quicklook_metadata_from_shared_status(visit: VisitName) -> AsyncGenerator[QuicklookMetadata, None]:
    async for jobs in _job_status_dict.subscribe():
        job_status = jobs.get(visit)
        match job_status:
            case None:
                yield QuicklookMetadataProgress(visit, progress={})
            case JobStatus(stage='queued' | 'generate_single_fits_tiles'):
                yield QuicklookMetadataProgress(
                    visit_name=visit,
                    progress=job_status.generate_single_fits_tiles,
                )
            case JobStatus(stage='merge_tiles' | 'transfer_fits_headers' | 'transfer_tiles' | 'ready'):
                yield QuicklookMetadataReady(
                    visit_name=visit,
                    ccd_metadata_list=_job_shared_large_status_dict[visit].ccd_metadata_list,
                    wcs=_quicklook_metadata_wcs(),
                )
            case JobStatus(stage='error'):
                yield QuicklookMetadataError(visit_name=visit)
            case _:
                raise ValueError(f"Unknown job status stage: {job_status.stage}")


_job_shared_large_status_dict: dict[VisitName, JobSharedLargeStatus] = {}
_job_status_dict = Broadcast[JobStatusList](max_queue_size=2)


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
    ws_base_url = re.sub(r'^http://', 'ws://', config.coordinator_base_url)
    for i in reversed(range(5)):
        try:
            async with websockets.connect(f'{ws_base_url}/quicklooks/*/shared_status.ws') as ws:
                while True:
                    msg_bytes = await ws.recv()
                    assert isinstance(msg_bytes, bytes)
                    msg: SharedStatusMessage = pickle.loads(msg_bytes)

                    match msg:
                        case SharedStatusMessageJobStatusList(data=data):
                            _job_status_dict.put(data)
                        case SharedStatusMessageJobSharedLargeStatus(visit=visit, data=data):
                            _job_shared_large_status_dict[visit] = data
                            jobs = _job_status_dict.last_value()
                            if jobs:
                                _job_shared_large_status_dict = {
                                    visit: _job_shared_large_status_dict[visit] for visit in jobs
                                }

        except Exception as e:
            logger.warning(f'Failed to connect to {ws_base_url}: {str(e)}. Remaining retries: {i}')
            import traceback

            traceback.print_exc()
            await asyncio.sleep(5)
    else:
        await _shutdown()


def _quicklook_metadata_wcs():
    scale = 0.2 / 3600.0  # pixel size in degree
    return {
        "NAXIS1": 63424,
        "NAXIS2": 63376,
        "CRVAL1": 0,
        "CRVAL2": 0,
        "CRPIX1": 31750.5,
        "CRPIX2": 31750.5,
        "CD1_1": -scale,
        "CD1_2": 0,
        "CD2_1": 0,
        "CD2_2": scale,
    }


async def _shutdown():  # pragma: no cover
    await asyncio.sleep(10)  # 繰り返しの再起動を防ぐために少し待つ
    os.kill(os.getpid(), signal.SIGINT)
    # さらに待って強制終了
    await asyncio.sleep(10)
    os.kill(os.getpid(), signal.SIGKILL)
