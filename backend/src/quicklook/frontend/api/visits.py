from fastapi import APIRouter, HTTPException, Query
from quicklook.datasource import get_datasource
from quicklook.datasource.butler_datasource import VisitEntry
from quicklook.datasource.types import DataSourceCcdMetadata, ResolvedVisitInfo
from quicklook.datasource.types import VisitResolutionError
from quicklook.datasource.types import Query as DataSourceQuery
from quicklook.types import CcdDataRef, CcdDataType, CcdName, VisitName

router = APIRouter()


@router.get('/api/visits', response_model=list[VisitEntry])
async def list_visits(
    exposure: int | None = Query(None),
    day_obs: int | None = Query(None),
    limit: int = Query(default=1000, le=10000),
    data_type: CcdDataType = Query(...),
    repository_name: str = Query(...),
):
    ds = get_datasource()
    return await ds.query_visits(
        DataSourceQuery(
            data_type=data_type,
            repository_name=repository_name,
            exposure=exposure,
            day_obs=day_obs,
            limit=limit,
        )
    )


@router.get(
    '/api/visits/{visit_name}/ccds/{ccd_name}',
    response_model=DataSourceCcdMetadata,
)
async def get_visit_metadata(
    visit_name: str,
    ccd_name: str,
) -> DataSourceCcdMetadata:
    ds = get_datasource()
    ref = CcdDataRef(
        visit=VisitName(visit_name),
        ccd=CcdName(ccd_name),
    )
    try:
        metadata = await ds.get_metadata(ref)
    except VisitResolutionError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    return metadata


@router.get('/api/visits/{visit_name}/resolution', response_model=ResolvedVisitInfo)
async def get_visit_resolution(visit_name: str) -> ResolvedVisitInfo:
    ds = get_datasource()
    try:
        return await ds.resolve_visit_info(VisitName(visit_name))
    except VisitResolutionError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


@router.get('/api/exposures/{id}/types', response_model=list[CcdDataType])
async def get_exposure_data_types(id: int):
    ds = get_datasource()
    return await ds.get_exposure_data_types(id)
