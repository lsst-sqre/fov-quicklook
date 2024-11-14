import logging
from contextlib import asynccontextmanager
from typing import Any

import aiohttp
from fastapi import FastAPI, WebSocket
from fastapi.routing import APIRoute
from pydantic import BaseModel, ConfigDict
from starlette.websockets import WebSocketDisconnect

from quicklook.config import config
from quicklook.coordinator.api.quicklooks import QuicklookCreate
from quicklook.coordinator.quicklook import Quicklook, QuicklookMeta
from quicklook.frontend.api import gettile
from quicklook.frontend.api.remotequicklook import RemoteQuicklookWather, remote_quicklook
from quicklook.models import QuicklookRecord
from quicklook.types import GeneratorProgress, ProcessCcdResult, Visit
from quicklook.utils.websocket import safe_websocket

logger = logging.getLogger(f'uvicorn.{__name__}')


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with RemoteQuicklookWather().activate():
        with Quicklook.enable_subscription():
            yield


app = FastAPI(lifespan=lifespan)


@app.get('/api/healthz', description='Health check')
async def healthz():
    return await http_request('get', f'{config.coordinator_base_url}/healthz')


@app.delete('/api/quicklooks/*', description='Delete all quicklooks')
async def delete_all_quicklooks():
    return await http_request('delete', f'{config.coordinator_base_url}/quicklooks/*')


class QuicklookCreateFrontend(BaseModel):
    id: str


@app.post('/api/quicklooks', description='Create a quicklook')
async def create_quicklook(params: QuicklookCreateFrontend):
    logger.info(f'create_quicklook: {params.id}')
    return await http_request(
        'post',
        f'{config.coordinator_base_url}/quicklooks',
        json=QuicklookCreate(visit=Visit.from_id(params.id)).model_dump(),
    )


class QuicklookStatus(BaseModel):
    id: str
    phase: QuicklookRecord.Phase
    generating_progress: dict[str, GeneratorProgress] | None
    meta: QuicklookMeta | None

    model_config = ConfigDict(
        from_attributes=True,
    )


@app.get('/api/quicklooks', response_model=list[QuicklookStatus])
async def list_quicklooks():
    return [*RemoteQuicklookWather().quicklooks.values()]


@app.get('/api/quicklooks/{id}/status', response_model=QuicklookStatus | None)
async def show_quicklook_status(id: str):
    return RemoteQuicklookWather().quicklooks.get(Visit.from_id(id))


@app.websocket('/api/quicklooks/{id}/status.ws')
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


@app.get('/api/quicklooks/{id}/metadata', response_model=QuicklookMetadata)
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


app.include_router(gettile.router)


# class FitsMeta(BaseModel):
#     obsid: str
#     raftbay: str
#     ccdslot: str


# class CcdMeta(BaseModel):
#     image_stat: ImageStat
#     ccd_name: str
#     ccd_corners: list[tuple[float, float]]
#     amps: list[AmpMeta]
#     # fits_meta: FitsMeta
# #     bbox: BBox
# #     image_stat: ImageStat
# #     worker_id: int


# class QuicklookMeta(BaseModel):
#     ccd_meta: dict[str, CcdMeta]
#     wcs: dict[str, Any]


# @app.get('/api/quicklooks/{visit_name}/meta', response_model=QuicklookMeta)
# async def quicklook_meta(visit_name: str):
#     while True:
#         res = await http_request('get', f'{config.coordinator_base_url}/quicklooks/{visit_name}/meta')
#         if res and res['status'] != 'processing':
#             break
#         await asyncio.sleep(1)

#     scale = 0.2 / 3600.0  # pixel size in degree
#     return QuicklookMeta(
#         ccd_meta={
#             "R14_S10": CcdMeta(
#                 amps=example_ccd_meta["R14_S10"]["amps"],
#                 ccd_name="R14_S10",
#                 ccd_corners=example_ccd_meta["R14_S10"]["ccd_corners"],
#                 # fits_meta=example_ccd_meta["R14_S10"]["fits_meta"],
#                 image_stat=example_ccd_meta["R14_S10"]["image_stat"],
#             ),
#         },
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
#     )


class VisitListEntry(BaseModel):
    name: str


@app.get('/api/visits', response_model=list[VisitListEntry])
def list_visits():
    return [
        VisitListEntry(name='raw:broccoli'),
        VisitListEntry(name='calexp:192350'),
    ]


async def http_request(method: str, url: str, *, content: bytes | None = None, json: Any | None = None) -> Any:
    async with aiohttp.ClientSession() as session:
        async with session.request(method, url, data=content, json=json) as response:
            response.raise_for_status()
            return await response.json()


def use_route_names_as_operation_ids(app: FastAPI) -> None:
    """
    https://fastapi.tiangolo.com/advanced/path-operation-advanced-configuration/

    Simplify operation IDs so that generated API clients have simpler function
    names.

    Should be called only after all routes have been added.
    """
    for route in app.routes:
        if isinstance(route, APIRoute):
            route.operation_id = route.name  # in this case, 'read_items'


use_route_names_as_operation_ids(app)


example_ccd_meta = {
    "R14_S10": {
        "ccd_name": "R14_S10",
        "ccd_corners": [[50878, 17048.5], [54973, 17048.5], [54973, 21051.5], [50878, 21051.5]],
        "bbox": {"miny": 17048.5, "maxy": 21051.5, "minx": 50878, "maxx": 54973},
        "image_stat": {"median": 424.9140625, "mad": 33.916015625, "shape": [4004, 4096]},
        "fits_meta": {"obsid": "MC_C_20200818_000099", "raftbay": "R14", "ccdslot": "S10"},
        "amps": [
            {"amp_id": 1, "bbox": {"miny": 19050.5, "maxy": 21051.5, "minx": 50878, "maxx": 51389}},
            {"amp_id": 2, "bbox": {"miny": 19050.5, "maxy": 21051.5, "minx": 51390, "maxx": 51901}},
            {"amp_id": 3, "bbox": {"miny": 19050.5, "maxy": 21051.5, "minx": 51902, "maxx": 52413}},
            {"amp_id": 4, "bbox": {"miny": 19050.5, "maxy": 21051.5, "minx": 52414, "maxx": 52925}},
            {"amp_id": 5, "bbox": {"miny": 19050.5, "maxy": 21051.5, "minx": 52926, "maxx": 53437}},
            {"amp_id": 6, "bbox": {"miny": 19050.5, "maxy": 21051.5, "minx": 53438, "maxx": 53949}},
            {"amp_id": 7, "bbox": {"miny": 19050.5, "maxy": 21051.5, "minx": 53950, "maxx": 54461}},
            {"amp_id": 8, "bbox": {"miny": 19050.5, "maxy": 21051.5, "minx": 54462, "maxx": 54973}},
            {"amp_id": 9, "bbox": {"miny": 17048.5, "maxy": 19049.5, "minx": 54462, "maxx": 54973}},
            {"amp_id": 10, "bbox": {"miny": 17048.5, "maxy": 19049.5, "minx": 53950, "maxx": 54461}},
            {"amp_id": 11, "bbox": {"miny": 17048.5, "maxy": 19049.5, "minx": 53438, "maxx": 53949}},
            {"amp_id": 12, "bbox": {"miny": 17048.5, "maxy": 19049.5, "minx": 52926, "maxx": 53437}},
            {"amp_id": 13, "bbox": {"miny": 17048.5, "maxy": 19049.5, "minx": 52414, "maxx": 52925}},
            {"amp_id": 14, "bbox": {"miny": 17048.5, "maxy": 19049.5, "minx": 51902, "maxx": 52413}},
            {"amp_id": 15, "bbox": {"miny": 17048.5, "maxy": 19049.5, "minx": 51390, "maxx": 51901}},
            {"amp_id": 16, "bbox": {"miny": 17048.5, "maxy": 19049.5, "minx": 50878, "maxx": 51389}},
        ],
    },
}
