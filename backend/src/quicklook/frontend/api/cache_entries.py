import quicklook.logging
from datetime import datetime

from fastapi import APIRouter
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select

from quicklook.coordinator.housekeeping import delete_one_quicklook, select_quicklook_to_delete
from quicklook.db import Quicklook
from quicklook.db.session import get_db_session

logger = quicklook.logging.getLogger('uvicorn')

router = APIRouter()


class CacheEntry(BaseModel):
    visit_name: str
    ready: bool
    created_at: datetime
    disk_usage: int

    model_config = ConfigDict(
        from_attributes=True,
    )


@router.get('/api/cache_entries')
async def list_cache_entries() -> list[CacheEntry]:
    async with get_db_session() as db:
        result = await db.execute(select(Quicklook))
        rows = result.scalars().all()

    return [CacheEntry.model_validate(r) for r in rows]


@router.delete('/api/cache_entries/*')
async def delete_all_cache_entries() -> None:
    while visit_name := await select_quicklook_to_delete():
        print(f'Deleting quicklook for visit: {visit_name}')
        await delete_one_quicklook(visit_name)
    print('Finished deleting all quicklooks')


@router.delete('/api/cache_entries/{visit_name}')
async def delete_cache_entry(visit_name: str) -> None:
    await delete_one_quicklook(visit_name)
