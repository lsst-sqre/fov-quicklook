from dataclasses import dataclass
from functools import cache
from typing import Any, Iterable

import boto3
from botocore.client import Config


@dataclass(frozen=True)
class S3Config:
    endpoint: str
    access_key: str
    secret_key: str
    secure: bool
    bucket: str


class NoSuchKey(Exception):
    pass


@dataclass
class S3Object:
    object_name: str
    # boto3の結果をラップするためのクラス
    # MinioObjectと互換性を持たせるためobject_nameプロパティを提供


def s3_download_object(
    settings: S3Config,
    key: str,
    *,
    offset: int = 0,
    length: int = 0,
) -> bytes:
    client = _create_s3_client(settings)

    kwargs: dict[str, Any] = {"Bucket": settings.bucket, "Key": key}
    if offset > 0 or length > 0:
        range_value = f"bytes={offset}-"
        if length > 0:
            range_value = f"bytes={offset}-{offset + length - 1}"
        kwargs["Range"] = range_value

    try:
        response = client.get_object(**kwargs)
    except client.exceptions.NoSuchKey as e:
        raise NoSuchKey(f'No such key: {key}') from e
    return response['Body'].read()


def s3_upload_object(
    s3_config: S3Config,
    key: str,
    data: bytes,
    content_type: str,
) -> None:
    client = _create_s3_client(s3_config)

    client.put_object(
        Bucket=s3_config.bucket,
        Key=key,
        Body=data,
        ContentType=content_type,
    )


def s3_list_objects(s3_config: S3Config, prefix: str) -> Iterable[S3Object]:
    client = _create_s3_client(s3_config)

    paginator = client.get_paginator('list_objects_v2')
    for page in paginator.paginate(Bucket=s3_config.bucket, Prefix=prefix):
        if 'Contents' in page:
            for obj in page['Contents']:
                yield S3Object(object_name=obj['Key'])


def s3_list_object_name(s3_config: S3Config, prefix: str) -> Iterable[str]:
    client = _create_s3_client(s3_config)

    paginator = client.get_paginator('list_objects_v2')
    for page in paginator.paginate(Bucket=s3_config.bucket, Prefix=prefix):
        if 'Contents' in page:
            for obj in page['Contents']:
                yield obj['Key']


def _create_s3_client(settings: S3Config):
    import threading

    thread_id = threading.get_ident()
    return _create_s3_client_thread_local(settings, thread_id)


@cache
def _create_s3_client_thread_local(settings: S3Config, thread_id: int):
    """
    Create a boto3 S3 client with TCP keepalive enabled
    """
    return boto3.client(
        's3',
        endpoint_url=f"{'https' if settings.secure else 'http'}://{settings.endpoint}",
        aws_access_key_id=settings.access_key,
        aws_secret_access_key=settings.secret_key,
        config=Config(signature_version='s3v4', tcp_keepalive=True),
    )
