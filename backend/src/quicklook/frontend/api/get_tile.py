import asyncio
import datetime
from functools import cache
from typing import Annotated

import aiohttp
import numpy
from fastapi import APIRouter, Depends, HTTPException, Response

import quicklook.mylogging
from quicklook.comm.types import GeneratorInfo
from quicklook.config import config
from quicklook.generator.generator_assignment import GeneratorAssignment, NoGeneratorFoundError
from quicklook.object_storage import VisitObjectStorage
from quicklook.tileinfo import TileInfo
from quicklook.utils.http_client import get_session
from quicklook.types import TilePos, VisitName
from quicklook.utils import zstd
from quicklook.utils.numpyutils import ndarray2npybytes, npybytes2ndarray
from quicklook.utils.s3 import NoSuchKey

from .deps import dep_tile_pos, dep_visit_name
from .quicklooks import QuicklookSharedStatus

logger = quicklook.mylogging.getLogger(__name__)

router = APIRouter()


@router.get('/api/quicklooks/{visit_name}/tiles/{z}/{y}/{x}')
async def get_tile(
    visit: Annotated[VisitName, Depends(dep_visit_name)],
    tile_pos: Annotated[TilePos, Depends(dep_tile_pos)],
) -> Response:
    shared_status = QuicklookSharedStatus(visit)
    job_status = shared_status.job_status

    if job_status is None:
        return await _get_tile_from_object_storage(visit, tile_pos)

    match job_status.stage:
        case 'merge_tiles':
            return await _gather_single_fits_tiles(visit, tile_pos, shared_status)
        case 'upload_to_object_storage':
            return await _fetch_merged_tile(visit, tile_pos, shared_status)
        case 'ready':
            return await _get_tile_from_object_storage(visit, tile_pos)
        case _:
            raise HTTPException(404)

    raise HTTPException(status_code=404, detail='Tile not found')


async def _get_tile_from_object_storage(visit: VisitName, pos: TilePos) -> Response:
    object_storage = VisitObjectStorage.from_visit(visit)
    headers = get_cache_headers()
    try:
        data_bytes = await object_storage.get_quicklook_tile_bytes(pos)
    except NoSuchKey:
        raise HTTPException(404)
    if data_bytes is None:
        return Response(blank_npy_zstd(), media_type='application/npy+zstd', headers=headers)
    return Response(data_bytes, media_type='application/npy+zstd', headers=headers)


async def _gather_single_fits_tiles(
    visit: VisitName,
    pos: TilePos,
    shared_status: QuicklookSharedStatus,
) -> Response:
    job = shared_status.job
    dist_config = shared_status.dist_config

    if not (job and dist_config):
        raise HTTPException(404)

    async def get_npy(generator: GeneratorInfo) -> numpy.ndarray:
        session = get_session()
        async with session.get(
            f'{generator.url}/jobs/{job.id}/tiles/{pos.level}/{pos.i}/{pos.j}',
            raise_for_status=True,
            timeout=aiohttp.ClientTimeout(total=1),
        ) as response:
            assert (
                response.headers['Content-Type'] == 'application/npy'
            ), f'Unexpected Content-Type: {response.headers["Content-Type"]}'
            return npybytes2ndarray(await response.read())

    generators = set(
        dist_config.generators[dist_config.ccd_generator_map[ccd]]
        for ccd in TileInfo.from_pos(pos).ccd_names
        if ccd in dist_config.ccd_generator_map
    )

    pool: numpy.ndarray | None = None
    async with asyncio.TaskGroup() as tg:
        tasks = [tg.create_task(get_npy(g)) for g in generators]
        for fut in asyncio.as_completed(tasks):
            arr = await fut
            if pool is None:
                pool = arr.copy()
            else:
                pool += arr

    headers = get_cache_headers()

    if pool is None:
        return Response(
            blank_npy_zstd(),
            media_type='application/npy+zstd',
            headers=headers,
        )

    return Response(
        zstd.compress(ndarray2npybytes(pool)),
        media_type='application/npy+zstd',
        headers=headers,
    )


async def _fetch_merged_tile(
    visit: VisitName,
    pos: TilePos,
    shared_status: QuicklookSharedStatus,
) -> Response:
    job = shared_status.job
    dist_config = shared_status.dist_config

    if not (job and dist_config):
        raise HTTPException(404)

    headers = get_cache_headers()
    ga = GeneratorAssignment(pos, dist_config)

    try:
        generator_id = ga.primary_generator_id
    except NoGeneratorFoundError:
        return Response(
            blank_npy_zstd(),
            media_type='application/npy+zstd',
            headers=headers,
        )

    generator = dist_config.generators[generator_id]

    session = get_session()
    async with session.get(
        f'{generator.url}/jobs/{job.id}/merged-tiles/{pos.level}/{pos.i}/{pos.j}',
        raise_for_status=True,
    ) as response:
        assert response.headers['Content-Type'] == 'application/npy+zstd'
        return Response(await response.read(), media_type='application/npy+zstd', headers=headers)


@cache
def blank_npy_zstd():
    arr = numpy.zeros((config.tile_size, config.tile_size, 2), dtype=numpy.float32)
    return zstd.compress(ndarray2npybytes(arr))


def get_cache_headers() -> dict[str, str]:
    return {
        "Cache-Control": "public, max-age=86400",
        "Expires": (datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=1)).strftime(
            "%a, %d %b %Y %H:%M:%S GMT"
        ),
    }
