from typing import Any, cast

from fastapi import APIRouter, HTTPException, Query, Request

from quicklook.datasource import get_datasource
from quicklook.datasource.types import ButlerDatasetTypeDimensions, ButlerDatasetTypeInfo, ButlerQuery, ButlerQueryResult
from quicklook.types import CcdDataType

router = APIRouter()

_RESERVED_QUERY_KEYS = {'data_type', 'repository_name', 'collection', 'limit', 'offset', 'order'}


def _get_butler_datasource() -> Any:
    datasource = get_datasource()
    required = (
        'query_butler',
        'list_butler_dataset_types',
        'get_butler_dataset_type_dimensions',
    )
    if not all(hasattr(datasource, name) for name in required):
        raise HTTPException(status_code=501, detail='Butler query API is only available with the Butler datasource.')
    return datasource


def _parse_multi_param(request: Request, key: str) -> list[str] | None:
    values: list[str] = []
    for raw in request.query_params.getlist(key):
        for value in raw.split(','):
            value = value.strip()
            if value:
                values.append(value)
    return values or None


def _extract_dimension_filters(request: Request) -> dict[str, str]:
    filters: dict[str, str] = {}
    for key, value in request.query_params.multi_items():
        if key in _RESERVED_QUERY_KEYS or value == '':
            continue
        filters[key] = value
    return filters


@router.get(
    '/api/butler/query',
    response_model=ButlerQueryResult,
    summary='Query Butler dimension records',
    description=(
        'Searches the configured Butler dataset type and returns paged dimension-record results. '
        'Reserved parameters are data_type, repository_name, collection, limit, offset, and order. '
        'Any other query parameter is forwarded as a Butler dimension filter.'
    ),
)
async def query_butler(
    request: Request,
    data_type: CcdDataType = Query(...),
    repository_name: str | None = Query(None),
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
) -> ButlerQueryResult:
    datasource = _get_butler_datasource()
    try:
        return await datasource.query_butler(
            ButlerQuery(
                data_type=data_type,
                repository_name=repository_name,
                limit=limit,
                offset=offset,
                collections=_parse_multi_param(request, 'collection'),
                order=_parse_multi_param(request, 'order') or [],
                filters=_extract_dimension_filters(request),
            )
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.get(
    '/api/butler/dataset_types',
    response_model=list[ButlerDatasetTypeInfo],
    summary='List supported Butler dataset types',
)
async def list_butler_dataset_types(
    repository_name: str | None = Query(None),
) -> list[ButlerDatasetTypeInfo]:
    datasource = _get_butler_datasource()
    try:
        return cast(list[ButlerDatasetTypeInfo], await datasource.list_butler_dataset_types(repository_name=repository_name))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.get(
    '/api/butler/dataset_types/{data_type}/dimensions',
    response_model=ButlerDatasetTypeDimensions,
    summary='Describe Butler dataset query dimensions',
)
async def get_butler_dataset_type_dimensions(
    data_type: CcdDataType,
    repository_name: str | None = Query(None),
) -> ButlerDatasetTypeDimensions:
    datasource = _get_butler_datasource()
    try:
        return cast(
            ButlerDatasetTypeDimensions,
            await datasource.get_butler_dataset_type_dimensions(data_type=data_type, repository_name=repository_name),
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
