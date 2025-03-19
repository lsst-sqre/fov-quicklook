import asyncio
import logging
import traceback
from functools import cache
from typing import Annotated

import aiohttp
import numpy
from fastapi import APIRouter, Depends, HTTPException, Response, status
from fastapi.responses import StreamingResponse
from sqlalchemy import select

from quicklook import storage
from quicklook.config import config
from quicklook.coordinator.quicklookjob.job import QuicklookJob, QuicklookJobPhase
from quicklook.db import db_context
from quicklook.deps.visit_from_path import visit_from_path
from quicklook.models import QuicklookRecord
from quicklook.tileinfo import TileInfo
from quicklook.types import GeneratorPod, Visit
from quicklook.utils import zstd
from quicklook.utils.numpyutils import ndarray2npybytes, npybytes2ndarray
from quicklook.utils.s3 import NoSuchKey
from quicklook.utils.sizelimitedset import SizeLimitedSet

logger = logging.getLogger(f'uvicorn.{__name__}')

router = APIRouter()


@router.get('/api/quicklooks/{id}/tiles/{z}/{y}/{x}')
async def get_tile(
    visit: Annotated[Visit, Depends(visit_from_path)],
    z: int,
    y: int,
    x: int,
) -> Response:
    if is_visit_ready(visit):
        return await get_tile_from_storage(visit, z, y, x)
    else:
        job = storage.get_quicklook_job_config(visit)
        if job:  # pragma: no branch
            return await gather_tiles(job, visit, z, y, x)
    raise HTTPException(status_code=404, detail='Quicklook not found')  # pragma: no cover


async def get_tile_from_storage(visit: Visit, z: int, y: int, x: int) -> Response:
    try:
        data = storage.get_quicklook_tile_bytes(visit, z, y, x)
    except NoSuchKey:
        return Response(blank_npy_zstd(), media_type='application/npy+zstd')
    return Response(data, media_type='application/npy+zstd')


ready_visits = SizeLimitedSet[Visit](32)


def is_visit_ready(visit: Visit):
    if visit in ready_visits:
        ready_visits.add(visit)
        return True
    with db_context() as db:
        record = db.execute(select(QuicklookRecord).where(QuicklookRecord.id == visit.id)).scalar_one_or_none()
        if record and record.phase == 'ready':
            ready_visits.add(visit)
            return True
    return False


async def gather_tiles(
    ql: QuicklookJob,
    visit: Visit,
    z: int,
    y: int,
    x: int,
) -> Response:
    ccd_generator_map = ql.ccd_generator_map

    if ccd_generator_map is None:  # pragma: no cover
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail='Quicklook is not ready')

    ccd_names = TileInfo.of(z, y, x).ccd_names
    generators = set(ccd_generator_map[ccd_name] for ccd_name in ccd_names if ccd_name in ccd_generator_map)

    async def get_npy(generator: GeneratorPod) -> numpy.ndarray:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f'http://{generator.name}/quicklooks/{visit.id}/tiles/{z}/{y}/{x}',
                raise_for_status=True,
            ) as response:
                return npybytes2ndarray(await response.read())

    pool: numpy.ndarray | None = None
    for fut in asyncio.as_completed([get_npy(g) for g in generators]):
        try:
            arr = await fut
        except Exception:  # pragma: no cover
            traceback.print_exc()
            continue
        if pool is None:
            pool = arr
        else:
            pool += arr
    if pool is None:
        logger.warning(f'No tile found for {visit.id}/{z}/{y}/{x}')
        return Response(blank_npy_zstd(), media_type='application/npy+zstd')

    return Response(ndarray2npybytes(pool), media_type='application/npy')


@cache
def blank_npy_zstd():
    arr = numpy.zeros((config.tile_size, config.tile_size), dtype=numpy.float32)
    return zstd.compress(ndarray2npybytes(arr))
