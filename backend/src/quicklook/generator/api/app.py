from contextlib import asynccontextmanager
from typing import Annotated

import fastapi
from fastapi.responses import StreamingResponse

from quicklook.comm import rpc
from quicklook.comm.generator import GeneratorIdInitializer
from quicklook.comm.generator import lifespan as generator_lifespan
from quicklook.comm.generator import router as comm_generator_router
from quicklook.job.job import Job
from quicklook.types import TilePos
from quicklook.utils.async_process_generator import create_async_process_pool
from quicklook.utils.numpyutils import ndarray2npybytes

# グローバルなプロセスプール
_process_pool = None


@asynccontextmanager
async def lifespan(app: fastapi.FastAPI):
    global _process_pool

    from quicklook.config import config

    async with generator_lifespan(app):
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


@app.get("/healthz")
async def route_healthz():
    return {"status": "ok"}


@app.post('/rpc')
async def route_rpc(request: fastapi.Request):
    if _process_pool is None:
        raise RuntimeError("Process pool not initialized")

    return StreamingResponse(
        _process_pool.run_async_process_generator(_rpc_worker, await request.body()),
        media_type='application/octet-stream',
    )


def _rpc_worker(body: bytes):
    for progress in rpc.create_rpc_caller_endpoint(body):
        yield progress


def dep_job(job_id: str):
    return Job.from_id(job_id)


def dep_tile_pos(level: int, i: int, j: int):
    return TilePos(level=level, i=i, j=j)


@app.get('/jobs/{job_id}/tiles/{level}/{i}/{j}')
def route_get_single_fits_tile(
    job: Annotated[Job, fastapi.Depends(dep_job)],
    tile_pos: Annotated[TilePos, fastapi.Depends(dep_tile_pos)],
):
    return fastapi.Response(
        ndarray2npybytes(job.local_storage.single_fits_tile.load_local_merged(tile_pos)),
        media_type='application/octet-stream',
    )


@app.get('/jobs/{job_id}/merged-tiles/{level}/{i}/{j}')
def route_get_merged_tile(
    job: Annotated[Job, fastapi.Depends(dep_job)],
    tile_pos: Annotated[TilePos, fastapi.Depends(dep_tile_pos)],
):
    try:
        data_bytes = job.local_storage.merged_fits_tile.load_compressed_data(tile_pos)
    except FileNotFoundError:
        raise fastapi.HTTPException(status_code=404)
    return fastapi.Response(data_bytes, media_type='application/octet-stream')
