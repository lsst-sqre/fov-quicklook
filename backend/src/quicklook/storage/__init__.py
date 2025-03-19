from functools import lru_cache

from quicklook.config import config
from quicklook.coordinator.quicklookjob.job import QuicklookJob
from quicklook.types import QuicklookMeta, Tile, Visit
from quicklook.utils import zstd
from quicklook.utils.s3 import s3_download_object, s3_upload_object


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


def put_quicklook_tile(tile: Tile):
    put(
        f'quicklook/{tile.visit.id}/tile/{tile.level}/{tile.i}/{tile.j}.npy.zstd',
        zstd.compress(tile.data.tobytes()),
    )


def get_quicklook_tile_bytes(visit: Visit, level: int, i: int, j: int) -> bytes:
    return get(f'quicklook/{visit.id}/tile/{level}/{i}/{j}.npy.zstd')


# from minio import Minio
# import os


# client = Minio(
#     endpoint='sdfembs3.sdf.slac.stanford.edu:443',
#     access_key=os.environ['QUICKLOOK_s3_repository__access_key'],
#     secret_key=os.environ['QUICKLOOK_s3_repository__secret_key'],
#     secure=True,
# )

# bucket_name = 'fov-quicklook-tile'
# print(client.bucket_exists(bucket_name))
