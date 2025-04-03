from fastapi import APIRouter, Query
from pydantic import BaseModel
from quicklook.datasource import get_datasource
from quicklook.datasource.types import DataSourceCcdMetadata, Query as DataSourceQuery
from quicklook.tileinfo import ccds_by_name
from quicklook.types import CcdId, Visit

router = APIRouter()


class VisitListEntry(BaseModel):
    id: str


@router.get('/api/visits', response_model=list[VisitListEntry])
def list_visits(
    exposure: int | None = Query(None),
    day_obs: int | None = Query(None),
    limit: int = Query(default=1000, le=10000),
):
    ds = get_datasource()
    visits = ds.query_visits(
        DataSourceQuery(
            data_type='raw',
            exposure=exposure,
            day_obs=day_obs,
            limit=limit,
        )
    )
    return [VisitListEntry(id=visit.id) for visit in visits]


@router.get('/api/visits/{id}/ccds/{ccd_name}', response_model=DataSourceCcdMetadata | None)
def get_visit_metadata(id: str, ccd_name: str):
    ds = get_datasource()
    ref = CcdId(visit=Visit.from_id(id), ccd_name=ccd_name)
    return ds.get_metadata(ref)
