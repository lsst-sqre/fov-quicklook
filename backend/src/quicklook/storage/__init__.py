from functools import cache

import minio

from quicklook.config import config
from quicklook.utils.s3 import download_object_from_s3, upload_object_to_s3


def put(key: str, value: bytes) -> None:
    upload_object_to_s3(_s3_client(), config.s3_tile.bucket, key, value, 'application/octet-stream')


def get(key: str) -> bytes | None:
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
