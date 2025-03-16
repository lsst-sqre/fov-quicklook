import logging
from typing import Annotated

from fastapi import APIRouter, Depends, Response

from quicklook.datasource import get_datasource
from quicklook.deps.visit_from_path import visit_from_path
from quicklook.types import CcdId, Visit

logger = logging.getLogger(f'uvicorn.{__name__}')

router = APIRouter()


@router.get('/api/quicklooks/{id}/fits/{ccd_name}')
async def get_fits_file(
    visit: Annotated[Visit, Depends(visit_from_path)],
    ccd_name: str,
):
    ds = get_datasource()
    data = ds.get_data(CcdId(visit, ccd_name))
    return Response(content=data, media_type='image/fits')
