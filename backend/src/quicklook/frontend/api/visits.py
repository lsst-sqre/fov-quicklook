from fastapi import APIRouter, HTTPException, Query
from quicklook.datasource import get_datasource
from quicklook.datasource.types import (
    DataSourceCcdMetadata,
    ResolvedVisitInfo,
    VisitDayCount,
    VisitDayCountQuery,
    VisitEntry,
    VisitRepresentativeUuid,
)
from quicklook.datasource.types import VisitResolutionError
from quicklook.datasource.types import Query as DataSourceQuery
from quicklook.types import CcdDataRef, CcdDataType, CcdName, VisitName

router = APIRouter()


@router.get('/api/visits', response_model=list[VisitEntry])
async def list_visits(
    repository_name: str = Query(...),
    collection: str = Query(...),
    dataset_type: str = Query(...),
    where: str | None = Query(None),
    order_by: str | None = Query(None),
    reverse: bool | None = Query(None),
    limit: int = Query(default=1000, le=10000),
    offset: int = Query(default=0, ge=0),
):
    ds = get_datasource()
    return await ds.query_visits(
        DataSourceQuery(
            repository_name=repository_name,
            collection=collection,
            dataset_type=dataset_type,
            where=where,
            order_by=order_by,
            reverse=reverse,
            limit=limit,
            offset=offset,
        )
    )


@router.get('/api/visits/day_counts', response_model=list[VisitDayCount])
async def list_visit_day_counts(
    calendar_month: str = Query(..., pattern=r'^\d{4}-\d{2}$'),
    repository_name: str = Query(...),
    collection: str = Query(...),
    dataset_type: str = Query(...),
):
    ds = get_datasource()
    try:
        return await ds.query_visit_day_counts(
            VisitDayCountQuery(
                repository_name=repository_name,
                collection=collection,
                dataset_type=dataset_type,
                calendar_month=calendar_month,
            )
        )
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e


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


@router.get('/api/visits/{visit_name}/representative_uuid', response_model=VisitRepresentativeUuid)
async def get_visit_representative_uuid(visit_name: str) -> VisitRepresentativeUuid:
    ds = get_datasource()
    try:
        return VisitRepresentativeUuid(
            uuid=await ds.get_visit_representative_uuid(VisitName(visit_name))
        )
    except VisitResolutionError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


@router.get('/api/exposures/{id}/types', response_model=list[CcdDataType])
async def get_exposure_data_types(id: int):
    ds = get_datasource()
    return await ds.get_exposure_data_types(id)
