import re

from fastapi import APIRouter, HTTPException, Query
from quicklook.datasource import get_datasource
from quicklook.datasource.types import (
    DataSourceCcdMetadata,
    SpatialQuery,
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
ORDER_FIELD_PATTERN = re.compile(r'^-?[A-Za-z_][A-Za-z0-9_.]*$')


@router.get('/api/visits', response_model=list[VisitEntry])
async def list_visits(
    exposure: int | None = Query(None),
    day_obs: int | None = Query(None),
    limit: int = Query(default=100, gt=0, le=10000),
    offset: int = Query(default=0, ge=0),
    order: str | None = Query(None),
    ra_deg: float | None = Query(None),
    dec_deg: float | None = Query(None),
    radius_deg: float | None = Query(None),
    data_type: CcdDataType = Query(...),
    repository_name: str = Query(...),
):
    ds = get_datasource()
    try:
        return await ds.query_visits(
            DataSourceQuery(
                data_type=data_type,
                repository_name=repository_name,
                exposure=exposure,
                day_obs=day_obs,
                limit=limit,
                offset=offset,
                order=_parse_order(order),
                spatial=_parse_spatial_query(
                    ra_deg=ra_deg,
                    dec_deg=dec_deg,
                    radius_deg=radius_deg,
                ),
            )
        )
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e


@router.get('/api/visits/day_counts', response_model=list[VisitDayCount])
async def list_visit_day_counts(
    calendar_month: str = Query(..., pattern=r'^\d{4}-\d{2}$'),
    data_type: CcdDataType = Query(...),
    repository_name: str = Query(...),
):
    ds = get_datasource()
    try:
        return await ds.query_visit_day_counts(
            VisitDayCountQuery(
                data_type=data_type,
                repository_name=repository_name,
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


def _parse_order(order: str | None) -> tuple[str, ...] | None:
    if order is None:
        return None

    fields = [field.strip() for field in order.split(',')]
    if any(not field for field in fields):
        raise ValueError('order must be a comma-separated list of field names.')
    for field in fields:
        if not ORDER_FIELD_PATTERN.fullmatch(field):
            raise ValueError(f'Invalid order field: {field}')
    return tuple(fields)


def _parse_spatial_query(
    *,
    ra_deg: float | None,
    dec_deg: float | None,
    radius_deg: float | None,
) -> SpatialQuery | None:
    supplied = [ra_deg is not None, dec_deg is not None, radius_deg is not None]
    if not any(supplied):
        return None
    if not all(supplied):
        raise ValueError('ra_deg, dec_deg, and radius_deg must be specified together.')
    assert ra_deg is not None
    assert dec_deg is not None
    assert radius_deg is not None
    if not 0 <= ra_deg < 360:
        raise ValueError('ra_deg must be in [0, 360).')
    if not -90 <= dec_deg <= 90:
        raise ValueError('dec_deg must be in [-90, 90].')
    if radius_deg < 0:
        raise ValueError('radius_deg must be >= 0.')
    return SpatialQuery(ra_deg=ra_deg, dec_deg=dec_deg, radius_deg=radius_deg)
