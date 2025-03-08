import logging

from fastapi import APIRouter, WebSocket
from pydantic import BaseModel, ConfigDict
from starlette.websockets import WebSocketDisconnect

from quicklook import storage
from quicklook.config import config
from quicklook.coordinator.api.quicklooks import QuicklookCreate
from quicklook.coordinator.quicklookjob.job import QuicklookJob, QuicklookJobPhase, QuicklookJobReport
from quicklook.frontend.api.remotejobs import RemoteQuicklookJobsWather
from quicklook.types import CcdMeta, GeneratorProgress, QuicklookMeta, Visit
from quicklook.utils.http_request import http_request
from quicklook.utils.websocket import safe_websocket

router = APIRouter()

logger = logging.getLogger(f'uvicorn.{__name__}')


class QuicklookStatus(BaseModel):
    phase: QuicklookJobPhase
    generate_progress: dict[str, GeneratorProgress] | None

    model_config = ConfigDict(
        from_attributes=True,
    )


@router.get('/api/quicklooks', response_model=list[QuicklookStatus])
async def list_quicklooks():
    return [*RemoteQuicklookJobsWather().jobs.values()]


@router.get('/api/quicklooks/{id}/status', response_model=QuicklookStatus | None)
async def show_quicklook_status(id: str):
    return RemoteQuicklookJobsWather().jobs.get(Visit.from_id(id))


@router.websocket('/api/quicklooks/{id}/status.ws')
async def show_quicklook_status_ws(id: str, client_ws: WebSocket):
    visit = Visit.from_id(id)
    await client_ws.accept()
    async with safe_websocket(client_ws):

        def pick(qls: dict[Visit, QuicklookJobReport]) -> QuicklookJobReport | None:
            return qls.get(visit)

        async for job in RemoteQuicklookJobsWather().watch(pick):
            try:
                model = QuicklookStatus.model_validate(job).model_dump() if job else None
                await client_ws.send_json(model)
            except WebSocketDisconnect:
                break


class QuicklookMetadata(BaseModel):
    # QuicklookMetaと紛らわしいがこちらはフロントエンド用
    id: str
    wcs: dict
    ccd_meta: list[CcdMeta] | None


@router.get('/api/quicklooks/{id}/metadata', response_model=QuicklookMetadata)
async def show_quicklook_metadata(
    id: str,
):
    scale = 0.2 / 3600.0  # pixel size in degree
    meta = storage.get_quicklook_meta(Visit.from_id(id))
    return QuicklookMetadata(
        id=id,
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
        ccd_meta=meta.ccd_meta,
    )


@router.delete('/api/quicklooks/*', description='Delete all quicklooks')
async def delete_all_quicklooks():
    return await http_request('delete', f'{config.coordinator_base_url}/quicklooks/*')


class QuicklookCreateFrontend(BaseModel):
    id: str


@router.post('/api/quicklooks', description='Create a quicklook')
async def create_quicklook(params: QuicklookCreateFrontend):
    logger.info(f'create_quicklook: {params.id}')
    return await http_request(
        'post',
        f'{config.coordinator_base_url}/quicklooks',
        json=QuicklookCreate(visit=Visit.from_id(params.id)).model_dump(),
    )
