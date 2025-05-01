import logging

from fastapi import APIRouter, Query
from pydantic import BaseModel

from quicklook.datasource import get_datasource
from quicklook.datasource.types import DataSourceCcdMetadata
from quicklook.datasource.types import Query as DataSourceQuery
from quicklook.types import CcdDataType, CcdId, Visit

router = APIRouter()


class VisitListEntry(BaseModel):
    id: str


@router.get('/api/visits', response_model=list[VisitListEntry])
def list_visits(
    exposure: int | None = Query(None),
    day_obs: int | None = Query(None),
    limit: int = Query(default=1000, le=10000),
    data_type: CcdDataType = Query(default='raw'),
):
    ds = get_datasource()
    visits = ds.query_visits(
        DataSourceQuery(
            data_type=data_type,
            exposure=exposure,
            day_obs=day_obs,
            limit=limit,
        )
    )
    return [VisitListEntry(id=visit.id) for visit in visits]


@router.get('/api/visits/{id}/ccds/{ccd_name}', response_model=DataSourceCcdMetadata)
def get_visit_metadata(id: str, ccd_name: str):
    ds = get_datasource()
    ref = CcdId(visit=Visit.from_id(id), ccd_name=ccd_name)
    metadata = ds.get_metadata(ref)
    return metadata
