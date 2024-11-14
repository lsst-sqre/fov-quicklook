from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import minio

from quicklook.config import config
from quicklook.types import CcdId, Visit
from quicklook.utils.fits import fits_partial_load
from quicklook.utils.s3 import download_object_from_s3


def s3_get_visit_ccd_fits(visit: Visit, ccd_name: str) -> bytes:
    if visit.data_type == 'calexp':
        return s3_get_visit_ccd_fits_calexp(visit, ccd_name)
    else:
        return s3_get_visit_ccd_fits_raw(visit, ccd_name)


def s3_get_visit_ccd_fits_raw(visit: Visit, ccd_name: str) -> bytes:
    bucket = config.s3_repository.bucket
    key = f'{visit.data_type}/{visit.name}/{ccd_name}.fits'
    return download_object_from_s3(s3_client(), bucket, key)


def s3_get_visit_ccd_fits_calexp(visit: Visit, ccd_name: str) -> bytes:
    def read(start: int, end: int) -> bytes:
        bucket = config.s3_repository.bucket
        key = f'{visit.data_type}/{visit.name}/{ccd_name}.fits'
        return download_object_from_s3(s3_client(), bucket, key, offset=start, length=end - start)

    return fits_partial_load(read, [0, 1])


@dataclass
class S3CcdObject:
    url: str
    ccd_id: CcdId
    obj: object


def s3_list_visit_ccds(visit: Visit) -> Iterable[S3CcdObject]:
    bucket = config.s3_repository.bucket
    prefix = f'{visit.data_type}/{visit.name}/'
    for obj in s3_client().list_objects(bucket, prefix=prefix):
        yield S3CcdObject(
            url=f'{config.s3_repository.endpoint}/{bucket}/{obj.object_name}',
            ccd_id=CcdId(visit, Path(obj.object_name).stem),  # type: ignore
            obj=obj,
        )


def s3_client():
    s3_config = config.s3_repository
    return minio.Minio(
        s3_config.endpoint,
        access_key=s3_config.access_key,
        secret_key=s3_config.secret_key,
        secure=s3_config.secure,
    )
