import logging

from fastapi import APIRouter, HTTPException, WebSocket, status
from pydantic import BaseModel, TypeAdapter
from starlette.websockets import WebSocketDisconnect

from quicklook import storage
from quicklook.config import config
from quicklook.coordinator.api.quicklooks import QuicklookCreate
from quicklook.coordinator.quicklookjob.job import QuicklookJobPhase, QuicklookJobReport
from quicklook.frontend.api.remotejobs import RemoteQuicklookJobsWatcher
from quicklook.types import CcdMeta, GenerateProgress, MergeProgress, TransferProgress, Visit
from quicklook.utils.http_request import http_request
from quicklook.utils.websocket import safe_websocket

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
    a = TypeAdapter(list[QuicklookJobReport])
    reports: list[QuicklookJobReport] = a.validate_python(await http_request('get', f'{config.coordinator_base_url}/quicklook-jobs'))
    return [QuicklookStatus.from_report(r) for r in reports]


@router.websocket('/api/quicklooks.ws')
async def list_quicklooks_ws(client_ws: WebSocket):
    await client_ws.accept()
    async with safe_websocket(client_ws):
        async for jobs in RemoteQuicklookJobsWatcher().watch(lambda _: _.values()):
            try:
                await client_ws.send_json([QuicklookStatus.from_report(job).model_dump() for job in jobs])
            except WebSocketDisconnect:
                break


@router.get('/api/quicklooks/{id}/status', response_model=QuicklookStatus | None)
async def show_quicklook_status(id: str):
    visit = Visit.from_id(id)
    report = RemoteQuicklookJobsWatcher().jobs.get(visit)
    return quicklook_status(visit, report)


@router.websocket('/api/quicklooks/{id}/status.ws')
async def show_quicklook_status_ws(id: str, client_ws: WebSocket):
    visit = Visit.from_id(id)
    await client_ws.accept()
    async with safe_websocket(client_ws):

        def pick(qls: dict[Visit, QuicklookJobReport]) -> QuicklookJobReport | None:
            return qls.get(visit)

        async for report in RemoteQuicklookJobsWatcher().watch(pick):  # pragma: no branch
            status = quicklook_status(visit, report)
            try:
                await client_ws.send_json(status.model_dump() if status else None)
            except WebSocketDisconnect:
                break


def quicklook_status(visit: Visit, report: QuicklookJobReport | None) -> QuicklookStatus | None:
    if report:
        status = QuicklookStatus.from_report(report)
    else:
        job = storage.load_quicklook_job(visit)
        if job:
            status = QuicklookStatus.from_report(QuicklookJobReport.from_job(job))
        else:
            status = None
    return status


class QuicklookMetadata(BaseModel):
    # QuicklookMetaと紛らわしいがこちらはフロントエンド用
    id: str
    wcs: dict
    ccd_meta: list[CcdMeta] | None


@router.get('/api/quicklooks/{id}/metadata', response_model=QuicklookMetadata)
async def show_quicklook_metadata(id: str):
    metadata = quicklook_metadata(visit=Visit.from_id(id))
    if metadata:
        return metadata
    raise HTTPException(status.HTTP_404_NOT_FOUND)


def quicklook_metadata(visit: Visit) -> QuicklookMetadata | None:
    meta = storage.get_quicklook_meta(visit)
    if meta:
        scale = 0.2 / 3600.0  # pixel size in degree
        return QuicklookMetadata(
            id=visit.id,
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
