from dataclasses import dataclass
from pathlib import Path

import minio

from quicklook.config import config
from quicklook.types import CcdId, Visit
from quicklook.utils.fits import fits_partial_load
from quicklook.utils.s3 import download_object_from_s3

from .types import DataSourceBase, Query, Visit


class DummyDataSource(DataSourceBase):
    def query_visits(self, q: Query) -> list[Visit]:
        return [
            Visit.from_id('raw:broccoli'),
            Visit.from_id('calexp:192350'),
            Visit.from_id(f'raw:{q.day_obs}'),
            *[Visit.from_id(f'raw:{i}') for i in range(50)],
        ][: q.limit]

    def get_data(self, ref: CcdId) -> bytes:
        return _s3_get_visit_ccd_fits(ref.visit, ref.ccd_name)

    def list_ccds(self, visit: Visit) -> list[str]:
        bucket = config.s3_repository.bucket
        prefix = f'{visit.data_type}/{visit.name}/'
        return [Path(obj.object_name).stem for obj in _s3_client().list_objects(bucket, prefix=prefix)]  # type: ignore


def _s3_get_visit_ccd_fits(visit: Visit, ccd_name: str) -> bytes:
    if visit.data_type == 'calexp':
        return _s3_get_visit_ccd_fits_calexp(visit, ccd_name)
    else:
        return _s3_get_visit_ccd_fits_raw(visit, ccd_name)


def _s3_get_visit_ccd_fits_raw(visit: Visit, ccd_name: str) -> bytes:
    bucket = config.s3_repository.bucket
    key = f'{visit.data_type}/{visit.name}/{ccd_name}.fits'
    return download_object_from_s3(_s3_client(), bucket, key)


def _s3_get_visit_ccd_fits_calexp(visit: Visit, ccd_name: str) -> bytes:
    def read(start: int, end: int) -> bytes:
        bucket = config.s3_repository.bucket
        key = f'{visit.data_type}/{visit.name}/{ccd_name}.fits'
        return download_object_from_s3(_s3_client(), bucket, key, offset=start, length=end - start)

    return fits_partial_load(read, [0, 1])


def _s3_client():
    s3_config = config.s3_repository
    return minio.Minio(
        s3_config.endpoint,
        access_key=s3_config.access_key,
        secret_key=s3_config.secret_key,
        secure=s3_config.secure,
    )
