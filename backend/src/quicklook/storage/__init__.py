from functools import lru_cache
import pickle

from quicklook.config import config
from quicklook.coordinator.quicklookjob.job import QuicklookJob
from quicklook.types import PackedTileId, QuicklookMeta, Tile, Visit
from quicklook.utils import zstd
from quicklook.utils.s3 import NoSuchKey, s3_download_object, s3_upload_object
from quicklook.utils.timeit import timeit


def put(key: str, value: bytes) -> None:
    s3_upload_object(config.s3_tile, key, value, 'application/octet-stream')


def get(key: str) -> bytes:
    return s3_download_object(config.s3_tile, key)


def put_quicklook_meta(visit: Visit, meta: QuicklookMeta) -> None:
    put(f'quicklook/{visit.id}/meta', meta.model_dump_json().encode())


def get_quicklook_meta(visit: Visit) -> QuicklookMeta:
    return QuicklookMeta.model_validate_json(get(f'quicklook/{visit.id}/meta'))


def put_quicklook_job_config(job: QuicklookJob) -> None:
    visit = job.visit
    put(f'quicklook/{visit.id}/job-config', job.model_dump_json().encode())


@lru_cache(maxsize=32)
def get_quicklook_job_config(visit: Visit) -> QuicklookJob:
    # putは１度しか行われないのでキャッシュする
    return QuicklookJob.model_validate_json(get(f'quicklook/{visit.id}/job-config'))


def save_quicklook_job(job: QuicklookJob) -> None:
    put(f'quicklook/{job.visit.id}/job.json', job.model_dump_json().encode())


def load_quicklook_job(visit: Visit) -> QuicklookJob | None:
    try:
        raw = get(f'quicklook/{visit.id}/job.json')
        return QuicklookJob.model_validate_json(raw)
    except NoSuchKey:
        pass


def put_quicklook_packed_tile_array(visit: Visit, packed_id: PackedTileId, array: list[bytes | None]) -> None:
    # TODO: don't use pickle
    with timeit(f'put_quicklook_tile_bytes {visit.id} {packed_id.level} {packed_id.i} {packed_id.j}'):
        put(f'quicklook/{visit.id}/packed-tile/{packed_id.level}/{packed_id.i}/{packed_id.j}.npy.zstd', pickle.dumps(array))


@lru_cache(maxsize=128)  # 1 Tile 100kbほど。config.tile_pack == 2 で PackedTile 1.6MBほど
def get_quicklook_packed_tile_bytes(visit: Visit, packed_id: PackedTileId) -> list[bytes | None]:
    # TODO: don't use pickle
    return pickle.loads(get(f'quicklook/{visit.id}/packed-tile/{packed_id.level}/{packed_id.i}/{packed_id.j}.npy.zstd'))


def get_quicklook_tile_bytes(visit: Visit, level: int, i: int, j: int) -> bytes | None:
    packed_id = PackedTileId.from_unpacked(level, i, j)
    packed = get_quicklook_packed_tile_bytes(visit, packed_id)
    index = packed_id.index(i, j)
    return packed[index]
