import logging

from fastapi import APIRouter, WebSocket
from pydantic import BaseModel
from starlette.websockets import WebSocketDisconnect

from quicklook import storage
from quicklook.config import config
from quicklook.coordinator.api.quicklooks import QuicklookCreate
from quicklook.coordinator.quicklookjob.job import QuicklookJobPhase, QuicklookJobReport
from quicklook.frontend.api.remotejobs import RemoteQuicklookJobsWather
from quicklook.types import CcdMeta, GenerateProgress, MergeProgress, TransferProgress, Visit
from quicklook.utils.http_request import http_request
from quicklook.utils.websocket import safe_websocket
from pydantic import field_validator

router = APIRouter()

logger = logging.getLogger(f'uvicorn.{__name__}')


class QuicklookStatus(BaseModel):
    id: str
    phase: QuicklookJobPhase
    generate_progress: dict[str, GenerateProgress] | None
    transfer_progress: dict[str, TransferProgress] | None
    merge_progress: dict[str, MergeProgress] | None

    @classmethod
    def from_report(cls, report: QuicklookJobReport) -> 'QuicklookStatus':
        return cls(
            id=report.visit.id,
            phase=report.phase,
            generate_progress=report.generate_progress,
            transfer_progress=report.transfer_progress,
            merge_progress=report.merge_progress,
        )


@router.get('/api/quicklooks', response_model=list[QuicklookStatus])
async def list_quicklooks():
    return [QuicklookStatus.from_report(job) for job in RemoteQuicklookJobsWather().jobs.values()]


@router.get('/api/quicklooks/{id}/status', response_model=QuicklookStatus | None)
async def show_quicklook_status(id: str):
    report = RemoteQuicklookJobsWather().jobs.get(Visit.from_id(id))
    if report is None:
        return None
    return QuicklookStatus.from_report(report)


@router.websocket('/api/quicklooks/{id}/status.ws')
async def show_quicklook_status_ws(id: str, client_ws: WebSocket):
    visit = Visit.from_id(id)
    await client_ws.accept()
    async with safe_websocket(client_ws):

        def pick(qls: dict[Visit, QuicklookJobReport]) -> QuicklookJobReport | None:
            return qls.get(visit)

        async for job in RemoteQuicklookJobsWather().watch(pick):  # pragma: no branch
            try:
                model = QuicklookStatus.from_report(job).model_dump() if job else None
                await client_ws.send_json(model)
            except WebSocketDisconnect:
                break

        return


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
    no_transfer: bool = False

    @field_validator('no_transfer')
    @classmethod
    def validate_no_transfer(cls, value: bool) -> bool:
        if value and config.environment != 'test':  # pragma: no cover
            raise ValueError("no_transfer can only be set to True in test environment")
        return value


@router.post('/api/quicklooks', description='Create a quicklook')
async def create_quicklook(params: QuicklookCreateFrontend):
    logger.info(f'create_quicklook: {params.id}')
    return await http_request(
        'post',
        f'{config.coordinator_base_url}/quicklooks',
        json=QuicklookCreate(visit=Visit.from_id(params.id), no_transfer=params.no_transfer).model_dump(),
    )
