from dataclasses import dataclass
from functools import cache
from typing import Any, Iterable, Literal

import boto3
from botocore.client import Config


@dataclass(frozen=True)
class S3Config:
    endpoint: str
    access_key: str
    secret_key: str
    secure: bool
    bucket: str
    type: Literal['s3', 'minio'] = 's3'


class NoSuchKey(Exception):
    pass


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
    from quicklook.utils.timeit import timeit

    client = _create_s3_client(s3_config)
    with timeit(f'uploading {key}, {len(data)} bytes'):
        client.put_object(
            Bucket=s3_config.bucket,
            Key=key,
            Body=data,
            ContentType=content_type,
        )


@dataclass
class S3Object:
    key: str
    type: Literal['file', 'directory']
    size: int | None


def s3_list_objects(s3_config: S3Config, prefix: str, delimiter: str = '/') -> Iterable[S3Object]:
    client = _create_s3_client(s3_config)
    paginator = client.get_paginator('list_objects_v2')
    for page in paginator.paginate(Bucket=s3_config.bucket, Prefix=prefix, Delimiter=delimiter):
        if 'Contents' in page:
            for obj in page['Contents']:
                yield S3Object(key=obj['Key'], type='file', size=obj['Size'])
        if 'CommonPrefixes' in page:
            for obj in page['CommonPrefixes']:
                yield S3Object(key=obj['Prefix'], type='directory', size=None)


def s3_delete_object(
    s3_config: S3Config,
    key: str,
) -> None:
    client = _create_s3_client(s3_config)
    client.delete_object(Bucket=s3_config.bucket, Key=key)


def s3_delete_objects_with_prefix(
    s3_config: S3Config,
    prefix: str,
) -> None:
    if s3_config.type == 'minio':
        return _minio_delete_objects_with_prefix(s3_config, prefix)

    client = _create_s3_client(s3_config)
    paginator = client.get_paginator('list_objects_v2')
    pages = paginator.paginate(Bucket=s3_config.bucket, Prefix=prefix)

    for page in pages:
        if 'Contents' not in page:
            continue
        objects_to_delete = [{'Key': obj['Key']} for obj in page['Contents']]
        if objects_to_delete:
            client.delete_objects(Bucket=s3_config.bucket, Delete={'Objects': objects_to_delete})


def _minio_delete_objects_with_prefix(
    s3_config: S3Config,
    prefix: str,
) -> None:
    from minio import Minio
    from minio.deleteobjects import DeleteObject
    import logging

    logger = logging.getLogger(f'uvicorn.{__name__}')

    client = Minio(
        endpoint=s3_config.endpoint,
        access_key=s3_config.access_key,
        secret_key=s3_config.secret_key,
        secure=s3_config.secure,
    )

    for error in client.remove_objects(s3_config.bucket, (DeleteObject(obj.object_name) for obj in client.list_objects(s3_config.bucket, prefix, recursive=True) if obj.object_name)):
        logger.error(f'Error deleting {error}')


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
        config=Config(
            signature_version='s3v4',
            tcp_keepalive=True,
            request_checksum_calculation='when_required',
            response_checksum_validation='when_required',
            s3={'addressing_style': 'path'},
        ),
    )


'''
# debug用jupyterで実行


import boto3
import os
from botocore.client import Config
from typing import Iterable, Literal
from dataclasses import dataclass


secret_key = os.environ['QUICKLOOK_s3_tile__secret_key']
access_key = os.environ['QUICKLOOK_s3_tile__access_key']
bucket = 'fov-quicklook-tile'

client = boto3.client(
    's3',
    endpoint_url="https://sdfembs3.sdf.slac.stanford.edu:443",
    aws_access_key_id=access_key,
    aws_secret_access_key=secret_key,
    config=Config(
        signature_version='s3v4',
        tcp_keepalive=True,
        request_checksum_calculation='when_required',
        response_checksum_validation='when_required',
        s3={'addressing_style': 'path'},
    ),
)


@dataclass
class S3Object:
    key: str
    type: Literal['file', 'directory']
    size: int | None

def s3_list_objects(prefix: str, delimiter: str = '/') -> Iterable[S3Object]:
    paginator = client.get_paginator('list_objects_v2')
    for page in paginator.paginate(Bucket=bucket, Prefix=prefix, Delimiter=delimiter):
        if 'Contents' in page:
            for obj in page['Contents']:
                yield S3Object(key=obj['Key'], type='file', size=obj['Size'])
        if 'CommonPrefixes' in page:
            for obj in page['CommonPrefixes']:
                yield S3Object(key=obj['Prefix'], type='directory', size=None)


[*s3_list_objects('/quicklook/')]
'''
