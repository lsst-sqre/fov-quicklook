from fastapi import APIRouter

import quicklook.object_storage as storage

router = APIRouter()


@router.get('/api/storage', response_model=list[storage.Entry])
async def list_storage_entries(path: str) -> list[storage.Entry]:
    return [*storage.list_entries(path)]
