from fastapi import APIRouter, Query

from quicklook.datasource import get_datasource
from quicklook.datasource.butler_datasource import VisitEntry
from quicklook.datasource.types import DataSourceCcdMetadata
from quicklook.datasource.types import Query as DataSourceQuery
from quicklook.types import CcdDataType, CcdId, Visit

router = APIRouter()


@router.get('/api/visits', response_model=list[VisitEntry])
def list_visits(
    exposure: int | None = Query(None),
    day_obs: int | None = Query(None),
    limit: int = Query(default=1000, le=10000),
    data_type: CcdDataType = Query(default='raw'),
):
    ds = get_datasource()
    return ds.query_visits(
        DataSourceQuery(
            data_type=data_type,
            exposure=exposure,
            day_obs=day_obs,
            limit=limit,
        )
    )


@router.get('/api/visits/{id}/ccds/{ccd_name}', response_model=DataSourceCcdMetadata)
def get_visit_metadata(id: str, ccd_name: str):
    ds = get_datasource()
    ref = CcdId(visit=Visit.from_id(id), ccd_name=ccd_name)
    metadata = ds.get_metadata(ref)
    return metadata


@router.get('/api/exposures/{id}/types', response_model=list[CcdDataType])
def get_exposure_data_types(id: int):
    ds = get_datasource()
    return ds.get_exposure_data_types(id)
