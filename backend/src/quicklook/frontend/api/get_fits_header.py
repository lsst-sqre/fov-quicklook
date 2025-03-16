import logging
from typing import Annotated

import aiohttp
from fastapi import APIRouter, Depends, HTTPException, Response

from quicklook import storage
from quicklook.deps.visit_from_path import visit_from_path
from quicklook.types import Visit, HeaderType

logger = logging.getLogger(f'uvicorn.{__name__}')

router = APIRouter()


@router.get('/api/quicklooks/{id}/fits_header/{ccd_name}', response_model=list[HeaderType])
async def get_fits_header(
    visit: Annotated[Visit, Depends(visit_from_path)],
    ccd_name: str,
) -> Response:
    job = storage.get_quicklook_job_config(visit)
    ccd_generator_map = job.ccd_generator_map

    if ccd_generator_map is None:  # pragma: no cover
        raise HTTPException(status_code=503, detail='Quicklook is not ready')

    generator = ccd_generator_map.get(ccd_name)

    if generator is None:  # pragma: no cover
        raise HTTPException(status_code=404, detail='CCD not found')

    async with aiohttp.ClientSession() as session:
        async with session.get(
            f'http://{generator.name}/quicklooks/{visit.id}/fits_header/{ccd_name}',
            raise_for_status=True,
        ) as response:
            return Response(content=await response.read(), media_type='application/json')
