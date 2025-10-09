import quicklook.logging
from typing import Annotated

from fastapi import APIRouter, Depends, Response

from quicklook.datasource import get_datasource
from quicklook.frontend.api.deps import dep_ccd_data_ref
from quicklook.types import CcdDataRef, CcdName, VisitName

logger = quicklook.logging.getLogger(__name__)

router = APIRouter()


@router.get('/api/quicklooks/{visit_name}/fits/{ccd_name}')
async def get_fits_file(
    ccd_data_ref: Annotated[CcdDataRef, Depends(dep_ccd_data_ref)],
):
    ds = get_datasource()
    data = ds.get_data(ccd_data_ref)
    return Response(content=data, media_type='image/fits')
