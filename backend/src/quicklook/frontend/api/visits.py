from fastapi import APIRouter, Query
from pydantic import BaseModel
from quicklook.datasource import get_datasource
from quicklook.datasource.types import Query as DataSourceQuery

router = APIRouter()


class VisitListEntry(BaseModel):
    name: str


@router.get('/api/visits', response_model=list[VisitListEntry])
def list_visits(
    exposure: str | None = Query(None),
    day_obs: int | None = Query(None),
    limit: int = Query(default=100, le=1000),
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
    return [VisitListEntry(name=visit.name) for visit in visits]
