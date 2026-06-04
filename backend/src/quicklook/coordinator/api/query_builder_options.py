from fastapi import APIRouter, Query

from quicklook.datasource import get_datasource
from quicklook.datasource.types import QueryBuilderOptions

router = APIRouter()


@router.get("/query_builder_options", response_model=QueryBuilderOptions)
async def get_query_builder_options(
    repository_name: str | None = Query(None),
    collection: str | None = Query(None),
    dataset_type: str | None = Query(None),
):
    ds = get_datasource()
    return await ds.get_query_builder_options(
        repository_name=repository_name,
        collection=collection,
        dataset_type=dataset_type,
    )
