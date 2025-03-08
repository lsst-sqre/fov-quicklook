from functools import cache

import minio

from quicklook.config import config
from quicklook.coordinator.quicklookjob.job import QuicklookJob
from quicklook.types import QuicklookMeta, Visit
from quicklook.utils.s3 import download_object_from_s3, upload_object_to_s3


def put(key: str, value: bytes) -> None:
    upload_object_to_s3(_s3_client(), config.s3_tile.bucket, key, value, 'application/octet-stream')


def get(key: str) -> bytes:
    return download_object_from_s3(_s3_client(), config.s3_tile.bucket, key)


@cache
def _s3_client():
    s3_config = config.s3_tile
    return minio.Minio(
        s3_config.endpoint,
        access_key=s3_config.access_key,
        secret_key=s3_config.secret_key,
        secure=s3_config.secure,
    )


def put_quicklook_meta(visit: Visit, meta: QuicklookMeta) -> None:
    put(f'quicklook/{visit.id}/meta', meta.model_dump_json().encode())


def get_quicklook_meta(visit: Visit) -> QuicklookMeta:
    return QuicklookMeta.model_validate_json(get(f'quicklook/{visit.id}/meta'))


def put_quicklook_job_config(job: QuicklookJob) -> None:
    visit = job.visit
    put(f'quicklook/{visit.id}/job-config', job.model_dump_json().encode())


def get_quicklook_job_config(visit: Visit) -> QuicklookJob:
    return QuicklookJob.model_validate_json(get(f'quicklook/{visit.id}/job-config'))


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
