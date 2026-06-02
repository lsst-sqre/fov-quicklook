import re
from urllib.parse import urlencode

from fastapi import APIRouter, HTTPException, Query
from lsst.daf.butler._exceptions import ButlerUserError
from quicklook.config import config
from quicklook.datasets import get_dataset
from quicklook.datasource import get_datasource
from quicklook.datasource.types import (
    DataSourceCcdMetadata,
    QueryBuilderOptions,
    ResolvedVisitInfo,
    VisitDayCount,
    VisitDayCountQuery,
    VisitEntry,
    VisitRepresentativeUuid,
)
from quicklook.datasource.types import VisitResolutionError
from quicklook.datasource.types import Query as DataSourceQuery
from quicklook.types import CcdDataRef, CcdDataType, CcdName, VisitName
from quicklook.utils.coordinator_url import get_coordinator_base_url
from quicklook.utils.http_request import http_request

router = APIRouter()
_INVALID_WHERE_PATTERN = re.compile(r'[\x00-\x1f\x7f;]')
_MAX_WHERE_LENGTH = 1000


def _normalize_where(where: str | None) -> str | None:
    if where is None:
        return None
    normalized = where.strip()
    if not normalized:
        return None
    if normalized.casefold() in {'null', 'undefined'}:
        return None
    if len(normalized) > _MAX_WHERE_LENGTH:
        raise HTTPException(status_code=422, detail=f'where must be at most {_MAX_WHERE_LENGTH} characters long.')
    if _INVALID_WHERE_PATTERN.search(normalized):
        raise HTTPException(status_code=422, detail="where must not contain control characters or ';'.")
    return normalized


def _normalize_order_by(dataset_type: str, order_by: str | None) -> str | None:
    if order_by is None:
        return None
    normalized = order_by.strip()
    if not normalized:
        return None
    if normalized.casefold() in {'null', 'undefined'}:
        return None
    allowed_fields = get_dataset(dataset_type).order_by_fields
    if normalized not in allowed_fields:
        raise HTTPException(
            status_code=422,
            detail=f"order_by must be one of: {', '.join(allowed_fields)}",
        )
    return normalized


@router.get('/api/visits/query_builder_options', response_model=QueryBuilderOptions)
async def get_query_builder_options(
    repository_name: str | None = Query(None),
    collection: str | None = Query(None),
    dataset_type: str | None = Query(None),
):
    params = {
        key: value
        for key, value in {
            'repository_name': repository_name,
            'collection': collection,
            'dataset_type': dataset_type,
        }.items()
        if value is not None
    }
    query = urlencode(params)
    return await http_request(
        'get',
        f"{get_coordinator_base_url()}/query_builder_options{f'?{query}' if query else ''}",
    )


@router.get('/api/visits', response_model=list[VisitEntry])
async def list_visits(
    repository_name: str = Query(...),
    collection: str = Query(...),
    dataset_type: str = Query(...),
    where: str | None = Query(None),
    order_by: str | None = Query(None),
    reverse: bool | None = Query(None),
    limit: int = Query(default=100, le=10000),
    offset: int = Query(default=0, ge=0),
):
    ds = get_datasource()
    try:
        return await ds.query_visits(
            DataSourceQuery(
                repository_name=repository_name,
                collection=collection,
                dataset_type=dataset_type,
                where=_normalize_where(where),
                order_by=_normalize_order_by(dataset_type, order_by),
                reverse=reverse,
                limit=limit,
                offset=offset,
            )
        )
    except ButlerUserError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e


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
    except (ButlerUserError, ValueError) as e:
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
