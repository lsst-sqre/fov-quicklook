import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, WebSocket, status
from pydantic import BaseModel
from starlette.websockets import WebSocketDisconnect

from quicklook.config import config
from quicklook.coordinator.api.app import CreateQuicklookRequest
from quicklook.frontend.api.deps import dep_visit_name
from quicklook.generator.generate_single_fits_tiles import CcdMetadata
from quicklook.types import VisitName
from quicklook.utils.http_request import http_request

router = APIRouter()

logger = logging.getLogger(__name__)


@router.get('/api/quicklooks/*/status')
async def get_all_quicklook_jobs():
    return await http_request('get', f'{config.coordinator_base_url}/quicklooks/*/status')


class QuicklookStatus(BaseModel):
    id: str
    # phase: QuicklookJobPhase
    # generate_progress: dict[str, GenerateProgress] | None
    # transfer_progress: dict[str, TransferProgress] | None
    # merge_progress: dict[str, MergeProgress] | None

    # @classmethod
    # def from_report(cls, report: QuicklookJobReport) -> 'QuicklookStatus':
    #     return cls(
    #         id=report.visit.id,
    #         phase=report.phase,
    #         generate_progress=report.generate_progress,
    #         transfer_progress=report.transfer_progress,
    #         merge_progress=report.merge_progress,
    #     )


@router.websocket('/api/quicklooks.ws')
async def list_quicklooks_ws(client_ws: WebSocket):
    await client_ws.accept()
    async with safe_websocket(client_ws):
        async for jobs in RemoteQuicklookJobsWatcher().watch(lambda _: _.values()):
            try:
                await client_ws.send_json([QuicklookStatus.from_report(job).model_dump() for job in jobs])
            except WebSocketDisconnect:
                break


@router.get('/api/quicklooks/{visit_name}/status', response_model=QuicklookStatus | None)
async def show_quicklook_status(
    visit: Annotated[VisitName, Depends(dep_visit_name)],
):
    ...
    # report = RemoteQuicklookJobsWatcher().jobs.get(visit)
    # return quicklook_status(visit, report)


@router.websocket('/api/quicklooks/{visit_name}/status.ws')
async def show_quicklook_status_ws(
    visit: Annotated[VisitName, Depends(dep_visit_name)],
    client_ws: WebSocket,
):
    await client_ws.accept()
    # async with safe_websocket(client_ws):

    #     def pick(qls: dict[Visit, QuicklookJobReport]) -> QuicklookJobReport | None:
    #         return qls.get(visit)

    #     async for report in RemoteQuicklookJobsWatcher().watch(pick):  # pragma: no branch
    #         status = quicklook_status(visit, report)
    #         try:
    #             await client_ws.send_json(status.model_dump() if status else None)
    #         except WebSocketDisconnect:
    #             break


class QuicklookMetadata(BaseModel):
    # QuicklookMetaと紛らわしいがこちらはフロントエンド用
    id: str
    wcs: dict
    # ccd_meta: list[CcdMetadata] | None


@router.get(
    '/api/quicklooks/{visit_name}/metadata',
    response_model=QuicklookMetadata,
)
async def show_quicklook_metadata(
    visit: Annotated[VisitName, Depends(dep_visit_name)],
):
    ...
    # metadata = quicklook_metadata(visit=visit)
    # if metadata:
    #     touch_quicklook(visit=Visit.from_id(id))
    #     return metadata
    # raise HTTPException(status.HTTP_404_NOT_FOUND)


def quicklook_metadata(visit: VisitName) -> QuicklookMetadata | None:
    ...
    # meta = storage.get_quicklook_meta(visit)
    # if meta:
    #     scale = 0.2 / 3600.0  # pixel size in degree
    #     return QuicklookMetadata(
    #         id=visit.id,
    #         wcs={
    #             "NAXIS1": 63424,
    #             "NAXIS2": 63376,
    #             "CRVAL1": 0,
    #             "CRVAL2": 0,
    #             "CRPIX1": 31750.5,
    #             "CRPIX2": 31750.5,
    #             "CD1_1": -scale,
    #             "CD1_2": 0,
    #             "CD2_1": 0,
    #             "CD2_2": scale,
    #         },
    #         ccd_meta=meta.ccd_meta,
    #     )


@router.post('/api/quicklooks', description='Create a quicklook')
async def create_quicklook(params: CreateQuicklookRequest):
    return await http_request(
        'post',
        f'{config.coordinator_base_url}/quicklooks',
        json=params.model_dump(),
    )
