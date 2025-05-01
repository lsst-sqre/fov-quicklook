import pickle
from dataclasses import dataclass
from functools import lru_cache
from typing import Iterable, Literal

from quicklook.config import config
from quicklook.coordinator.quicklookjob.job import QuicklookJob
from quicklook.types import PackedTileId, QuicklookMeta, Visit
from quicklook.utils.s3 import NoSuchKey, s3_delete_object, s3_delete_objects_with_prefix, s3_download_object, s3_list_objects, s3_upload_object


def put(key: str, value: bytes) -> None:
    s3_upload_object(config.s3_tile, key, value, 'application/octet-stream')


def get(key: str) -> bytes:
    return s3_download_object(config.s3_tile, key)


@dataclass
class Entry:
    name: str
    type: Literal['directory', 'file']
    size: int | None


def list_entries(prefix: str) -> Iterable[Entry]:
    for obj in s3_list_objects(config.s3_tile, prefix=prefix):
        if obj.type == 'file':
            yield Entry(name=obj.key.split('/')[-1], type=obj.type, size=obj.size)
        elif obj.type == 'directory':
            yield Entry(name=f'{obj.key.split('/')[-2]}/', type=obj.type, size=None)


def delete_object(key: str) -> None:
    s3_delete_object(config.s3_tile, key)


def delete_objects_by_prefix(prefix: str) -> None:
    s3_delete_objects_with_prefix(config.s3_tile, prefix)


def put_quicklook_meta(visit: Visit, meta: QuicklookMeta) -> None:
    put(f'quicklook/{visit.id}/meta', meta.model_dump_json().encode())


def get_quicklook_meta(visit: Visit) -> QuicklookMeta | None:
    try:
        return QuicklookMeta.model_validate_json(get(f'quicklook/{visit.id}/meta'))
    except NoSuchKey:
        pass


def put_quicklook_job_config(job: QuicklookJob) -> None:
    visit = job.visit
    put(f'quicklook/{visit.id}/job-config', job.model_dump_json().encode())


@lru_cache(maxsize=32)
def get_quicklook_job_config(visit: Visit) -> QuicklookJob:
    # putは１度しか行われないのでキャッシュする
    return QuicklookJob.model_validate_json(get(f'quicklook/{visit.id}/job-config'))


def save_quicklook_job(job: QuicklookJob) -> None:
    put(f'quicklook/{job.visit.id}/job', job.model_dump_json().encode())


def load_quicklook_job(visit: Visit) -> QuicklookJob | None:
    try:
        raw = get(f'quicklook/{visit.id}/job')
        return QuicklookJob.model_validate_json(raw)
    except NoSuchKey:
        pass


def put_quicklook_packed_tile_array(visit: Visit, packed_id: PackedTileId, array: list[bytes | None]) -> None:
    # TODO: don't use pickle
    data = pickle.dumps(array)
    put(f'quicklook/{visit.id}/packed-tile/{packed_id.level}/{packed_id.i}/{packed_id.j}.npy.zstd.list.pickle', data)


@lru_cache(maxsize=128)  # 1 Tile 100kbほど。config.tile_pack == 2 で PackedTile 1.6MBほど
def get_quicklook_packed_tile_bytes(visit: Visit, packed_id: PackedTileId) -> list[bytes | None]:
    # TODO: don't use pickle
    return pickle.loads(get(f'quicklook/{visit.id}/packed-tile/{packed_id.level}/{packed_id.i}/{packed_id.j}.npy.zstd.list.pickle'))


def get_quicklook_tile_bytes(visit: Visit, level: int, i: int, j: int) -> bytes | None:
    packed_id = PackedTileId.from_unpacked(level, i, j)
    packed = get_quicklook_packed_tile_bytes(visit, packed_id)
    index = packed_id.index(i, j)
    return packed[index]


def remove_visit_data(visit: Visit) -> None:
    delete_objects_by_prefix(f'quicklook/{visit.id}/')


def clear_all():
    delete_objects_by_prefix('quicklook/')


def list_quicklooks() -> Iterable[Visit]:
    for e in list_entries('quicklook/'):
        if e.type == 'directory':
            yield Visit.from_id(e.name.split('/')[0])
