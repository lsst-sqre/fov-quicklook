import logging
from fastapi import APIRouter, WebSocket
from pydantic import BaseModel, ConfigDict
from starlette.websockets import WebSocketDisconnect

from quicklook.config import config
from quicklook.coordinator.api.quicklooks import QuicklookCreate
from quicklook.coordinator.quicklook import Quicklook, QuicklookMeta
from quicklook.frontend.api.http_request import http_request
from quicklook.frontend.api.remotequicklook import RemoteQuicklookWather, remote_quicklook
from quicklook.models import QuicklookRecord
from quicklook.types import GeneratorProgress, ProcessCcdResult, Visit
from quicklook.utils.websocket import safe_websocket

router = APIRouter()

logger = logging.getLogger(f'uvicorn.{__name__}')


class QuicklookStatus(BaseModel):
    id: str
    phase: QuicklookRecord.Phase
    generating_progress: dict[str, GeneratorProgress] | None
    meta: QuicklookMeta | None

    model_config = ConfigDict(
        from_attributes=True,
    )


@router.get('/api/quicklooks', response_model=list[QuicklookStatus])
async def list_quicklooks():
    return [*RemoteQuicklookWather().quicklooks.values()]


@router.get('/api/quicklooks/{id}/status', response_model=QuicklookStatus | None)
async def show_quicklook_status(id: str):
    return RemoteQuicklookWather().quicklooks.get(Visit.from_id(id))


@router.websocket('/api/quicklooks/{id}/status.ws')
async def show_quicklook_status_ws(id: str, client_ws: WebSocket):
    visit = Visit.from_id(id)
    await client_ws.accept()
    async with safe_websocket(client_ws):

        def pick(qls: dict[Visit, Quicklook]) -> Quicklook | None:
            return qls.get(visit)

        async for ql in RemoteQuicklookWather().watch(pick):
            try:
                model = QuicklookStatus.model_validate(ql).model_dump() if ql else None
                await client_ws.send_json(model)
            except WebSocketDisconnect:
                break


class QuicklookMetadata(BaseModel):
    id: str
    wcs: dict
    process_ccd_results: list[ProcessCcdResult] | None


@router.get('/api/quicklooks/{id}/metadata', response_model=QuicklookMetadata)
async def show_quicklook_metadata(
    id: str,
):
    scale = 0.2 / 3600.0  # pixel size in degree
    ql = remote_quicklook(Visit.from_id(id))
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
        process_ccd_results=ql and ql.meta and ql.meta.process_ccd_results,
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
