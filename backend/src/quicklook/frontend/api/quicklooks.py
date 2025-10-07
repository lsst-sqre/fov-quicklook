import asyncio
import logging
import os
import pickle
import re
import signal
from contextlib import asynccontextmanager
from typing import Annotated

import websockets
from fastapi import APIRouter, Depends, FastAPI, WebSocket
from pydantic import BaseModel, TypeAdapter
from sqlalchemy import select

from quicklook.config import config
from quicklook.coordinator.api.types import (
    CreateQuicklookRequest,
    JobStatusList,
    SharedStatusMessage,
    SharedStatusMessageJobSharedLargeStatus,
    SharedStatusMessageJobStatusList,
)
from quicklook.db import Quicklook, get_session
from quicklook.frontend.api.deps import dep_visit_name
from quicklook.generator.generate_single_fits_tiles import CcdMetadata
from quicklook.job.shared_large_status import JobSharedLargeStatus
from quicklook.job.status import JobStatus
from quicklook.object_storage import VisitObjectStorage
from quicklook.types import VisitName
from quicklook.utils.broadcast import Broadcast
from quicklook.utils.hash_utils import json_digest
from quicklook.utils.http_request import http_request
from quicklook.utils.websocket import run_until_disconnect, safe_websocket


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with quicklook_status_relay():
        yield


router = APIRouter()

logger = logging.getLogger(__name__)


@router.get('/api/quicklooks/*/status', response_model=JobStatusList)
async def get_all_quicklook_jobs():
    async for jobs in job_status_dict.subscribe():
        return jobs


type_adapter_JsonStatus = TypeAdapter(JobStatus | None)


@router.websocket('/api/quicklooks/*/status.ws')
async def websocket_quicklooks_status(ws: WebSocket):
    async with safe_websocket(ws):

        async def send_progress():
            async for jobs in job_status_dict.subscribe():
                await ws.send_json({visit: type_adapter_JsonStatus.dump_python(job) for visit, job in jobs.items()})

        await run_until_disconnect(ws, send_progress())


@router.get('/api/quicklooks/{visit_name}/status', response_model=JobStatus | None)
async def get_quicklook_status(
    visit: Annotated[VisitName, Depends(dep_visit_name)],
):
    async with get_session() as session:
        result = await session.execute(select(Quicklook).where(Quicklook.visit_name == visit, Quicklook.ready == True))
        quicklook = result.scalar_one_or_none()

        if quicklook is not None:
            from quicklook.job.job import Job

            job = Job(visit)
            job.status.stage = 'ready'
            return type_adapter_JsonStatus.dump_python(job.status)

    async for jobs in job_status_dict.subscribe():
        return type_adapter_JsonStatus.dump_python(jobs.get(visit))


@router.websocket('/api/quicklooks/{visit_name}/status.ws')
async def websocket_quicklook_status(
    ws: WebSocket,
    visit: Annotated[VisitName, Depends(dep_visit_name)],
):
    async with safe_websocket(ws):

        async def send_progress():
            async with get_session() as session:
                result = await session.execute(
                    select(Quicklook).where(Quicklook.visit_name == visit, Quicklook.ready == True)
                )
                quicklook = result.scalar_one_or_none()

                if quicklook is not None:
                    from quicklook.job.job import Job

                    job = Job(visit)
                    job.status.stage = 'ready'
                    await ws.send_json(type_adapter_JsonStatus.dump_python(job.status))
                    return

            last_digest = b''
            async for jobs in job_status_dict.subscribe():
                job_dict = type_adapter_JsonStatus.dump_python(jobs.get(visit))
                digest = json_digest(job_dict)
                if digest != last_digest:
                    await ws.send_json(job_dict)
                    last_digest = digest

        await run_until_disconnect(ws, send_progress())


job_shared_large_status_dict: dict[VisitName, JobSharedLargeStatus] = {}


@asynccontextmanager
async def quicklook_status_relay():
    global job_status_dict

    ws_base_url = re.sub(r'^http://', 'ws://', config.coordinator_base_url)
    job_status_dict = Broadcast[JobStatusList](max_queue_size=2)

    async def main():
        global job_shared_large_status_dict
        for i in reversed(range(5)):
            try:
                async with websockets.connect(f'{ws_base_url}/quicklooks/*/shared_status.ws') as ws:
                    while True:
                        msg_bytes = await ws.recv()
                        assert isinstance(msg_bytes, bytes)
                        msg: SharedStatusMessage = pickle.loads(msg_bytes)

                        match msg:
                            case SharedStatusMessageJobStatusList(data=data):
                                job_status_dict.put(data)
                            case SharedStatusMessageJobSharedLargeStatus(visit=visit, data=data):
                                job_shared_large_status_dict[visit] = data
                                jobs = job_status_dict.last_value()
                                if jobs:
                                    job_shared_large_status_dict = {
                                        visit: job_shared_large_status_dict[visit] for visit in jobs
                                    }
                                print(job_shared_large_status_dict)

            except Exception as e:
                logger.warning(f'Failed to connect to {ws_base_url}: {str(e)}. Remaining retries: {i}')
                import traceback

                traceback.print_exc()
                await asyncio.sleep(5)
        else:
            await _shutdown()

    main_task = asyncio.create_task(main())

    async with job_status_dict.activate():
        try:
            yield
        finally:
            main_task.cancel()
            try:
                await main_task
            except asyncio.CancelledError:
                pass


class QuicklookMetadata(BaseModel):
    visit_name: VisitName
    wcs: dict
    ccd_metadata_list: list[CcdMetadata]


@router.get(
    '/api/quicklooks/{visit_name}/metadata',
    response_model=QuicklookMetadata,
)
async def get_quicklook_metadata(
    visit: Annotated[VisitName, Depends(dep_visit_name)],
):

    ...
    # metadata = quicklook_metadata(visit=visit)
    # if metadata:
    #     touch_quicklook(visit=Visit.from_id(id))
    #     return metadata
    # raise HTTPException(status.HTTP_404_NOT_FOUND)


async def quicklook_metadata(visit: VisitName) -> QuicklookMetadata:
    storage = VisitObjectStorage(visit)
    ccd_metadata_list = await storage.get_ccd_metadata_list()
    scale = 0.2 / 3600.0  # pixel size in degree
    return QuicklookMetadata(
        visit_name=visit,
        wcs={
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
        },
        ccd_metadata_list=ccd_metadata_list,
    )


@router.post('/api/quicklooks', description='Create a quicklook')
async def create_quicklook(params: CreateQuicklookRequest):
    return await http_request(
        'post',
        f'{config.coordinator_base_url}/quicklooks',
        json=params.model_dump(),
    )


async def _shutdown():  # pragma: no cover
    await asyncio.sleep(10)  # 繰り返しの再起動を防ぐために少し待つ
    os.kill(os.getpid(), signal.SIGINT)
    # さらに待って強制終了
    await asyncio.sleep(10)
    os.kill(os.getpid(), signal.SIGKILL)
