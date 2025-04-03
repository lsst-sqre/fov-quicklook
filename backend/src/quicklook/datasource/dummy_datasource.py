from pathlib import Path

from quicklook.config import config
from quicklook.datasource.butler_datasource.instrument import Instrument
from quicklook.types import CcdId, Visit
from quicklook.utils.fits import fits_partial_load
from quicklook.utils.s3 import s3_download_object, s3_list_objects

from .types import DataSourceBase, DataSourceCcdMetadata, Query, Visit


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
        prefix = f'{visit.data_type}/{visit.name}/'
        return [Path(obj.key).stem for obj in s3_list_objects(config.s3_test_data, prefix=prefix)]

    def get_metadata(self, ref: CcdId) -> DataSourceCcdMetadata:
        i = Instrument.get('LSSTCam')
        return DataSourceCcdMetadata(
            detector=i.ccd_2_detector[ref.ccd_name],
            ccd_name=ref.ccd_name,
            day_obs=-1,
            exposure=-1,
            visit=ref.visit,
        )


def _s3_get_visit_ccd_fits(visit: Visit, ccd_name: str) -> bytes:
    if visit.data_type == 'calexp':
        return _s3_get_visit_ccd_fits_calexp(visit, ccd_name)
    else:
        return _s3_get_visit_ccd_fits_raw(visit, ccd_name)


def _s3_get_visit_ccd_fits_raw(visit: Visit, ccd_name: str) -> bytes:
    key = f'{visit.data_type}/{visit.name}/{ccd_name}.fits'
    return s3_download_object(config.s3_test_data, key)


def _s3_get_visit_ccd_fits_calexp(visit: Visit, ccd_name: str) -> bytes:
    def read(start: int, end: int) -> bytes:
        key = f'{visit.data_type}/{visit.name}/{ccd_name}.fits'
        return s3_download_object(config.s3_test_data, key, offset=start, length=end - start)

    return fits_partial_load(read, [0, 1])
