import logging
from datetime import datetime

from fastapi import APIRouter
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select

from quicklook.coordinator.quicklookjob.job_runner import housekeep
from quicklook.db import db_context
from quicklook.models import QuicklookRecord

logger = logging.getLogger('uvicorn')

router = APIRouter()


class CacheEntry(BaseModel):
    id: str
    phase: QuicklookRecord.Phase
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(
        from_attributes=True,
    )


@router.get('/api/cache_entries')
async def list_cache_entries() -> list[CacheEntry]:
    with db_context() as db:
        q = db.execute(select(QuicklookRecord).order_by(QuicklookRecord.created_at.desc()))
        records = q.scalars().all()
        return [CacheEntry.model_validate(record) for record in records]


@router.post('/api/cache_entries:cleanup')
async def cleanup_cache_entries() -> None:
    await housekeep()
