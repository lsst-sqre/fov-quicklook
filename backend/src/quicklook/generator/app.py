from functools import lru_cache
from typing import Annotated

import fastapi
from fastapi.responses import StreamingResponse

from quicklook.comm import rpc
from quicklook.comm.generator import lifespan as generator_lifespan
from quicklook.comm.generator import router as comm_generator_router
from quicklook.generator.job import Job
from quicklook.generator.jobstorage import JobStorage
from quicklook.types import TilePos
from quicklook.utils.async_process_generator import run_async_process_generator
from quicklook.utils.numpyutils import ndarray2npybytes

app = fastapi.FastAPI(lifespan=generator_lifespan)
app.include_router(comm_generator_router)


@app.get("/healthz")
async def route_healthz():
    return {"status": "ok"}


@app.post('/rpc')
async def route_rpc(request: fastapi.Request):
    return StreamingResponse(
        run_async_process_generator(_rpc_worker, await request.body()),
        media_type='application/octet-stream',
    )


def _rpc_worker(body: bytes):
    for progress in rpc.create_rpc_caller_endpoint(body):
        yield progress


@lru_cache(maxsize=8)
def dep_job_storage(job_id: str):
    return JobStorage(Job.from_id(job_id))


def dep_tile_pos(level: int, i: int, j: int):
    return TilePos(level=level, i=i, j=j)


@app.get('/jobs/{job_id}/tiles/{level}/{i}/{j}')
def get_local_tile(
    job_storage: Annotated[JobStorage, fastapi.Depends(dep_job_storage)],
    tile_pos: Annotated[TilePos, fastapi.Depends(dep_tile_pos)],
):
    return fastapi.Response(
        ndarray2npybytes(job_storage.single_fits_tile.load_local_merged(tile_pos)),
        media_type='application/octet-stream',
    )
