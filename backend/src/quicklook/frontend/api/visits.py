from fastapi import APIRouter, Query
from pydantic import BaseModel
from quicklook.datasource import get_datasource
from quicklook.datasource.types import Query as DataSourceQuery

router = APIRouter()


class VisitListEntry(BaseModel):
    id: str


@router.get('/api/visits', response_model=list[VisitListEntry])
def list_visits(
    exposure: str | None = Query(None),
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
