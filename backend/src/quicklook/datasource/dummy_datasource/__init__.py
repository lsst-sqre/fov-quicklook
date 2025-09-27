from pathlib import Path

from quicklook.config import config
from quicklook.datasource.butler_datasource.instrument import Instrument
from quicklook.datasource.types import VisitEntry
from quicklook.types import CcdDataRef, CcdDataType, CcdName, VisitName
from quicklook.utils.fits import fits_partial_load
from quicklook.utils.s3 import s3_download_object, s3_list_objects

from ..types import DataSourceBase, DataSourceCcdMetadata, Query, VisitName


class DummyDataSource(DataSourceBase):
    def query_visits(self, q: Query) -> list[VisitEntry]:
        return [
            create_dummy_visit_entry("raw:broccoli", 20230101, "r", 30.0, target_name="dummy_target"),
            create_dummy_visit_entry("calexp:192350", 20230102, "g", 15.0, target_name="dummy_target_2"),
            *[create_dummy_visit_entry(f"raw:dummy-{i}", 20230104, "z") for i in range(50)],
        ][: q.limit]

    def list_ccds(self, visit: VisitName) -> list[CcdName]:
        ccds = [*_s3_list_visit_ccds(visit)]
        if config.environment == 'test':
            ccds = ccds[:10]  # テスト環境では4つに制限
        return ccds

    def get_data(self, ref: CcdDataRef) -> bytes:
        if ref.visit.data_type == "calexp":
            return _s3_get_visit_ccd_fits_calexp(ref)
        else:
            return _s3_get_visit_ccd_fits_raw(ref)

    def get_metadata(self, ref: CcdDataRef) -> DataSourceCcdMetadata:
        i = Instrument.get("LSSTCam")
        return DataSourceCcdMetadata(
            detector=i.ccd_2_detector[ref.ccd_name],
            ccd_name=ref.ccd_name,
            day_obs=-1,
            exposure=-1,
            visit_name=ref.visit,
            uuid=f"dummy-uuid-{ref.visit.name}-{ref.ccd_name}",
        )

    def get_exposure_data_types(self, exposure_id: int) -> list[CcdDataType]:
        return ['raw', 'post_isr_image']


def _s3_get_visit_ccd_fits_raw(ref: CcdDataRef) -> bytes:
    key = f"{ref.visit.data_type}/{ref.visit.name}/{ref.ccd_name}.fits"
    return s3_download_object(config.s3_test_data, key)


def _s3_get_visit_ccd_fits_calexp(ref: CcdDataRef) -> bytes:
    def read(start: int, end: int) -> bytes:
        key = f'{ref.visit.data_type}/{ref.visit.name}/{ref.ccd_name}.fits'
        return s3_download_object(config.s3_test_data, key, offset=start, length=end - start)

    return fits_partial_load(read, [0, 1])


def _s3_list_visit_ccds(visit: VisitName) -> list[CcdName]:
    prefix = f"{visit.data_type}/{visit.name}/"
    ccd_names: list[CcdName] = []

    for obj in s3_list_objects(config.s3_test_data, prefix=prefix):
        if obj.type == 'file':
            # Extract the CCD name from the file path (remove .fits extension)
            file_name = Path(obj.key).name
            ccd_name = CcdName(Path(file_name).stem)
            ccd_names.append(ccd_name)

    return ccd_names


def create_dummy_visit_entry(
    visit_id: str,
    day_obs: int,
    physical_filter: str,
    exposure_time: float = 20.0,
    obs_id: str = "dummy_obs_id",
    science_program: str = "dummy_program",
    observation_type: str = "science",
    observation_reason: str = "test",
    target_name: str | None = None,
) -> VisitEntry:
    """
    ダミーのVisitEntryを作成するヘルパー関数
    """
    if target_name is None:
        target_name = f"dummy_target_{visit_id.split(':')[-1]}"

    return VisitEntry(
        id=visit_id,
        day_obs=day_obs,
        physical_filter=physical_filter,
        obs_id=obs_id,
        exposure_time=exposure_time,
        science_program=science_program,
        observation_type=observation_type,
        observation_reason=observation_reason,
        target_name=target_name,
    )
