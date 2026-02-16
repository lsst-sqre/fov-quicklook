from contextlib import asynccontextmanager
from typing import Annotated

import fastapi
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from quicklook.comm.generator import GeneratorIdInitializer
from quicklook.comm.generator import lifespan as generator_lifespan
from quicklook.comm.generator import router as comm_generator_router
from quicklook.utils.http_client import managed_session
from quicklook.config import config
from quicklook.generator.api.ccd_processing import websocket_generate_tiles_raw
from quicklook.job.job import Job
from quicklook.rpc.lifespan import rpc_lifespan
from quicklook.rpc.server import create_rpc_endpoint
from quicklook.types import CcdName, TilePos
from quicklook.utils.async_process_generator import create_async_process_pool
from quicklook.utils.numpyutils import ndarray2npybytes
from quicklook.utils.system_status import ContainerStatus, get_container_status

import quicklook.mylogging

logger = quicklook.mylogging.getLogger(__name__)

# グローバルなプロセスプール
_process_pool = None


@asynccontextmanager
async def lifespan(app: fastapi.FastAPI):
    global _process_pool

    from quicklook.revision import GIT_REVISION
    logger.info("Generator starting, revision=%s", GIT_REVISION)

    async with managed_session():
        async with generator_lifespan(app):
            async with rpc_lifespan(app):
                async with create_async_process_pool(
                    max_workers=config.generator_max_concurrent_jobs,
                    initializers=[GeneratorIdInitializer()],
                ) as pool:
                    _process_pool = pool
                    try:
                        yield
                    finally:
                        _process_pool = None


app = fastapi.FastAPI(lifespan=lifespan)
app.include_router(comm_generator_router)


@app.websocket("/rpc")
async def websocket_rpc_endpoint(websocket: fastapi.WebSocket):
    """WebSocketベースのRPCエンドポイント"""
    await create_rpc_endpoint(app, websocket)


@app.get("/healthz")
async def route_healthz():
    return {"status": "ok"}


@app.get("/status", response_model=ContainerStatus)
async def route_get_status():
    """Get the current container status."""
    return get_container_status()


def dep_job(job_id: str):
    return Job.from_id(job_id)


def dep_tile_pos(level: int, i: int, j: int):
    return TilePos(level=level, i=i, j=j)


def dep_ccd_name(ccd_name: str):
    return CcdName(ccd_name)


@app.get('/jobs/{job_id}/tiles/{level}/{i}/{j}')
def route_get_single_fits_tile(
    job: Annotated[Job, fastapi.Depends(dep_job)],
    tile_pos: Annotated[TilePos, fastapi.Depends(dep_tile_pos)],
):
    return fastapi.Response(
        ndarray2npybytes(job.local_storage.single_fits_tile.load_local_merged(tile_pos)),
        media_type='application/npy',
    )


@app.get('/jobs/{job_id}/merged-tiles/{level}/{i}/{j}')
def route_get_merged_tile(
    job: Annotated[Job, fastapi.Depends(dep_job)],
    tile_pos: Annotated[TilePos, fastapi.Depends(dep_tile_pos)],
):
    data_bytes = job.local_storage.merged_fits_tile.load_compressed_data(tile_pos)
    return fastapi.Response(data_bytes, media_type='application/npy+zstd')


@app.get('/jobs/{job_id}/fits-headers/{ccd_name}.pickle')
def route_get_fits_headers(
    job: Annotated[Job, fastapi.Depends(dep_job)],
    ccd_name: Annotated[CcdName, fastapi.Depends(dep_ccd_name)],
):
    data_bytes = job.local_storage.fits_header.load_pickle_bytes(ccd_name)
    return fastapi.Response(
        data_bytes,
        media_type='application/python-pickle',
    )


@app.websocket('/jobs/{job_id}/generate-tiles')
async def route_websocket_generate_tiles(
    websocket: fastapi.WebSocket,
    job_id: str,
):
    """CCD処理用WebSocketエンドポイント（job_idはURL互換性のため保持、実際のJobはWebSocketで送信される）"""
    await websocket_generate_tiles_raw(websocket)
