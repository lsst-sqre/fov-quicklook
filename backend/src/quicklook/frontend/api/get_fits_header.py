import io
import pickle
from typing import Annotated

import aiohttp
import astropy.io.fits as pyfits
from fastapi import APIRouter, Depends, HTTPException

import quicklook.mylogging
import quicklook.object_storage as storage
from quicklook.datasource import get_datasource
from quicklook.frontend.api.quicklooks import QuicklookSharedStatus
from quicklook.types import CcdDataRef, CcdName, VisitName
from quicklook.utils.http_client import get_session
from quicklook.utils.fitsheader import HeaderType, fitsheader_to_list
from quicklook.utils.s3 import NoSuchKey

from .deps import dep_ccd_name, dep_visit_name

logger = quicklook.mylogging.getLogger(__name__)

router = APIRouter()


@router.get(
    '/api/quicklooks/{visit_name}/fits_header/{ccd_name}',
    response_model=list[HeaderType],
)
async def get_fits_header(
    visit: Annotated[VisitName, Depends(dep_visit_name)],
    ccd: Annotated[CcdName, Depends(dep_ccd_name)],
):
    shared_status = QuicklookSharedStatus(visit)
    job_status = shared_status.job_status

    if job_status is None:
        return await _get_fits_header(visit, ccd)

    match job_status.stage:
        case 'merge_tiles' | 'upload_to_object_storage':
            return await _get_fits_header_from_generator(visit, ccd, shared_status)
        case 'ready':
            return await _get_fits_header(visit, ccd)
        case _:
            raise HTTPException(status_code=404, detail='Quicklook metadata not found')


async def _get_fits_header(visit: VisitName, ccd: CcdName) -> list[HeaderType]:
    try:
        return await _get_fits_header_from_object_storage(visit, ccd)
    except NoSuchKey:
        return await _get_fits_header_from_datasource(visit, ccd)


async def _get_fits_header_from_object_storage(visit: VisitName, ccd: CcdName) -> list[HeaderType]:
    return await storage.VisitObjectStorage.from_visit(visit).get_fits_headers(ccd)


async def _get_fits_header_from_datasource(visit: VisitName, ccd: CcdName) -> list[HeaderType]:
    # ponytail: read the FITS once when the cached header is missing; add a
    # ranged-header reader only if this path becomes measurably slow.
    data = await get_datasource().get_data(CcdDataRef(visit=visit, ccd=ccd))
    with pyfits.open(io.BytesIO(data), memmap=False) as hdul:
        return fitsheader_to_list(hdul)


async def _get_fits_header_from_generator(
    visit: VisitName,
    ccd: CcdName,
    shared_status: QuicklookSharedStatus,
) -> list[HeaderType]:
    job = shared_status.job
    dist_config = shared_status.dist_config

    if not (job and dist_config):
        raise HTTPException(status_code=404, detail='Quicklook metadata not found')

    generator = dist_config.generators[dist_config.ccd_generator_map[ccd]]
    url = f'{generator.url}/jobs/{job.id}/fits-headers/{ccd}.pickle'
    session = get_session()
    async with session.get(url, raise_for_status=True) as response:
        assert response.content_type == 'application/python-pickle'
        data_bytes = await response.read()
        return pickle.loads(data_bytes)
