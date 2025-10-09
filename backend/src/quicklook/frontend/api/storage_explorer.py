from fastapi import APIRouter

import quicklook.object_storage as storage

router = APIRouter()


@router.get('/api/storage', response_model=list[storage.Entry])
async def list_storage_entries(path: str) -> list[storage.Entry]:
    return [*storage.list_entries(path)]


@router.delete('/api/storage/by-prefix')
def delete_storage_entries_by_prefix(prefix: str) -> None:
    storage.delete_objects_by_prefix(prefix)


@router.delete('/api/storage')
def delete_storage_entry(path: str) -> None:
    storage.delete_object(path)
