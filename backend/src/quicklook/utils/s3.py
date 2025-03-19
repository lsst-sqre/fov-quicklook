from dataclasses import dataclass
import io
from typing import Iterable, Dict, Any
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
    client = boto3.client(
        's3',
        endpoint_url=f"{'https' if settings.secure else 'http'}://{settings.endpoint}",
        aws_access_key_id=settings.access_key,
        aws_secret_access_key=settings.secret_key,
        config=Config(signature_version='s3v4'),
    )

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
    client = boto3.client(
        's3',
        endpoint_url=f"{'https' if s3_config.secure else 'http'}://{s3_config.endpoint}",
        aws_access_key_id=s3_config.access_key,
        aws_secret_access_key=s3_config.secret_key,
        config=Config(signature_version='s3v4'),
    )

    client.put_object(
        Bucket=s3_config.bucket,
        Key=key,
        Body=data,
        ContentType=content_type,
    )


def s3_list_objects(s3_config: S3Config, prefix: str) -> Iterable[S3Object]:
    client = boto3.client(
        's3',
        endpoint_url=f"{'https' if s3_config.secure else 'http'}://{s3_config.endpoint}",
        aws_access_key_id=s3_config.access_key,
        aws_secret_access_key=s3_config.secret_key,
        config=Config(signature_version='s3v4'),
    )

    paginator = client.get_paginator('list_objects_v2')
    for page in paginator.paginate(Bucket=s3_config.bucket, Prefix=prefix):
        if 'Contents' in page:
            for obj in page['Contents']:
                yield S3Object(object_name=obj['Key'])


def s3_list_object_name(s3_config: S3Config, prefix: str) -> Iterable[str]:
    client = boto3.client(
        's3',
        endpoint_url=f"{'https' if s3_config.secure else 'http'}://{s3_config.endpoint}",
        aws_access_key_id=s3_config.access_key,
        aws_secret_access_key=s3_config.secret_key,
        config=Config(signature_version='s3v4'),
    )

    paginator = client.get_paginator('list_objects_v2')
    for page in paginator.paginate(Bucket=s3_config.bucket, Prefix=prefix):
        if 'Contents' in page:
            for obj in page['Contents']:
                yield obj['Key']
