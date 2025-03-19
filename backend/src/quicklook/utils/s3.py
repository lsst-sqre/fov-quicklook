from dataclasses import dataclass
import io
from typing import Iterable
import minio
from minio.datatypes import Object as MinioObject


@dataclass(frozen=True)
class S3Config:
    endpoint: str
    access_key: str
    secret_key: str
    secure: bool
    bucket: str


def s33_download_object(
    settings: S3Config,
    key: str,
    *,
    offset: int = 0,
    length: int = 0,
) -> bytes:
    client = minio.Minio(
        settings.endpoint,
        access_key=settings.access_key,
        secret_key=settings.secret_key,
        secure=settings.secure,
    )
    response = None
    try:
        response = client.get_object(
            settings.bucket,
            key,
            offset=offset,
            length=length,
        )
        return response.read()

    finally:
        if response:  # pragma: no branch
            response.close()
            response.release_conn()


def s3_upload_object(
    s3_config: S3Config,
    key: str,
    data: bytes,
    content_type: str,
) -> None:
    client = minio.Minio(
        s3_config.endpoint,
        access_key=s3_config.access_key,
        secret_key=s3_config.secret_key,
        secure=s3_config.secure,
    )
    data_buf = io.BytesIO(data)
    client.put_object(
        s3_config.bucket,
        key,
        data_buf,
        len(data),
        content_type=content_type,
    )


def s3_list_objects(s3_config: S3Config, prefix: str) -> Iterable[MinioObject]:
    client = minio.Minio(
        s3_config.endpoint,
        access_key=s3_config.access_key,
        secret_key=s3_config.secret_key,
        secure=s3_config.secure,
    )
    return client.list_objects(s3_config.bucket, prefix=prefix)


def s3_list_object_name(s3_config: S3Config, prefix: str) -> Iterable[str]:
    client = minio.Minio(
        s3_config.endpoint,
        access_key=s3_config.access_key,
        secret_key=s3_config.secret_key,
        secure=s3_config.secure,
    )
    for obj in client.list_objects(s3_config.bucket, prefix=prefix):
        assert obj.object_name
        yield obj.object_name
