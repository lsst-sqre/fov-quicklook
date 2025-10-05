import logging
from typing import Annotated

import aiohttp
from fastapi import APIRouter, Depends, HTTPException, Response

from quicklook.job.job import Job

from .deps import dep_ccd_name, dep_visit_name
import quicklook.object_storage as storage
from quicklook.types import CcdName, VisitName
from quicklook.utils.fitsheader import HeaderType

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get('/api/quicklooks/{visit_name}/fits_header/{ccd_name}', response_model=list[HeaderType])
async def get_fits_header(
    visit: Annotated[VisitName, Depends(dep_visit_name)],
    ccd: Annotated[CcdName, Depends(dep_ccd_name)],
):
    # TODO: implement
    return []

    # generator = ccd_generator_map.get(ccd_name)

    # if generator is None:  # pragma: no cover
    #     raise HTTPException(status_code=404, detail='CCD not found')

    # async with aiohttp.ClientSession() as session:
    #     async with session.get(
    #         f'http://{generator.name}/quicklooks/{visit.id}/fits_header/{ccd_name}',
    #         raise_for_status=True,
    #     ) as response:
    #         return Response(content=await response.read(), media_type='application/json')
