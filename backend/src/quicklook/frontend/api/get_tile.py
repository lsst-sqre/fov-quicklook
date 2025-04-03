import asyncio
import logging
import traceback
from functools import cache
from typing import Annotated

import aiohttp
import numpy
from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select

from quicklook import storage
from quicklook.config import config
from quicklook.coordinator.quicklookjob.job import QuicklookJob, QuicklookJobPhase
from quicklook.db import db_context
from quicklook.deps.visit_from_path import visit_from_path
from quicklook.frontend.api.remotejobs import RemoteQuicklookJobsWatcher
from quicklook.models import QuicklookRecord
from quicklook.select_primary_generator import NoOverlappingGenerators, select_primary_generator
from quicklook.tileinfo import TileInfo
from quicklook.types import GeneratorPod, TileId, Visit
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
        report = RemoteQuicklookJobsWatcher().jobs.get(visit)
        job = storage.get_quicklook_job_config(visit)
        assert report and job
        if report and job:
            assert job.ccd_generator_map
            if report.phase >= QuicklookJobPhase.MERGE_DONE:
                return await fetch_merged_tile(visit, z, y, x, job.ccd_generator_map)
            if report.phase >= QuicklookJobPhase.GENERATE_DONE:
                return await gather_tile(visit, z, y, x, job.ccd_generator_map)

    raise HTTPException(status_code=404, detail='Tile not found')


async def get_tile_from_storage(visit: Visit, z: int, y: int, x: int) -> Response:
    headers = {'x-quicklook-phase': QuicklookJobPhase.READY.name}
    try:
        data = storage.get_quicklook_tile_bytes(visit, z, y, x)
    except NoSuchKey:
        return Response(blank_npy_zstd(), media_type='application/npy+zstd', headers={**headers, 'x-quicklook-error': 'Tile not found'})
    return Response(data, media_type='application/npy+zstd', headers=headers)


async def gather_tile(visit: Visit, z: int, y: int, x: int, ccd_generator_map: dict[str, GeneratorPod]) -> Response:
    ccd_names = TileInfo.of(z, y, x).ccd_names
    generators = set(ccd_generator_map[ccd_name] for ccd_name in ccd_names if ccd_name in ccd_generator_map)

    async def get_npy(generator: GeneratorPod) -> numpy.ndarray:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f'http://{generator.name}/quicklooks/{visit.id}/tiles/{z}/{y}/{x}',
                raise_for_status=True,
                timeout=aiohttp.ClientTimeout(total=1),
            ) as response:
                assert response.headers['Content-Type'] == 'application/npy'
                return npybytes2ndarray(await response.read())

    headers = {
        'x-quicklook-phase': QuicklookJobPhase.GENERATE_DONE.name,
    }
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
        return Response(blank_npy_zstd(), media_type='application/npy+zstd', headers={**headers, 'X-Quicklook-Error': 'Tile not found'})

    return Response(ndarray2npybytes(pool), media_type='application/npy', headers=headers)


async def fetch_merged_tile(visit: Visit, z: int, y: int, x: int, ccd_generator_map: dict[str, GeneratorPod]) -> Response:
    headers = {
        'x-quicklook-phase': QuicklookJobPhase.MERGE_DONE.name,
    }
    try:
        generator, _ = select_primary_generator(ccd_generator_map, TileId(z, y, x))
    except NoOverlappingGenerators:
        return Response(blank_npy_zstd(), media_type='application/npy+zstd', headers={**headers, 'x-quicklook-error': 'Tile not found'})
        
    async with aiohttp.ClientSession() as session:
        async with session.get(
            f'http://{generator.name}/quicklooks/{visit.id}/merged-tiles/{z}/{y}/{x}',
            raise_for_status=True,
        ) as response:
            assert response.headers['Content-Type'] == 'application/npy+zstd'
            return Response(await response.read(), media_type='application/npy+zstd', headers=headers)


ready_visits = SizeLimitedSet[Visit](config.max_storage_entries, ttl=30)


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


@cache
def blank_npy_zstd():
    arr = numpy.zeros((config.tile_size, config.tile_size), dtype=numpy.float32)
    return zstd.compress(ndarray2npybytes(arr))
