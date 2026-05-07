import json
from pathlib import Path

from quicklook.config import config
from quicklook.datasource.butler_datasource.instrument import Instrument
from quicklook.datasource.types import VisitDayCount, VisitDayCountQuery, VisitEntry
from quicklook.types import CcdDataRef, CcdDataType, CcdName, VisitName
from quicklook.utils.fits import fits_partial_load
from quicklook.utils.s3 import NoSuchKey, s3_download_object, s3_list_objects

from ..types import DataSourceBase, DataSourceCcdMetadata, Query, VisitName

SHARED_SAMPLE_MANIFEST_KEY = "_fixtures/review-app/sample-manifest.json"


class DummyDataSource(DataSourceBase):
    def query_visits_sync(self, q: Query) -> list[VisitEntry]:
        visits = _load_shared_dummy_visits() or _default_dummy_visits()
        visits = _filter_visits(visits, q)
        return visits[: q.limit]

    def query_visit_day_counts_sync(self, q: VisitDayCountQuery) -> list[VisitDayCount]:
        month_prefix = q.calendar_month.replace('-', '')
        counts: dict[int, int] = {}
        for visit in self.query_visits_sync(
            Query(
                data_type=q.data_type,
                repository_name=q.repository_name,
                limit=1000,
            )
        ):
            if not str(visit.day_obs).startswith(month_prefix):
                continue
            counts[visit.day_obs] = counts.get(visit.day_obs, 0) + 1
        return [VisitDayCount(day_obs=day_obs, count=count) for day_obs, count in sorted(counts.items())]

    def resolve_visit_sync(self, visit: VisitName) -> VisitName:
        return visit

    def list_ccds_sync(self, visit: VisitName) -> list[CcdName]:
        ccds = [*_s3_list_visit_ccds(visit)]
        match config.environment:
            case 'test':
                ccds = ccds[:40]
            case 'development':
                ccds = ccds[:40]
                # pass
        return ccds

    def get_data_sync(self, ref: CcdDataRef) -> bytes:
        if ref.visit.data_type == "calexp":
            return _s3_get_visit_ccd_fits_calexp(ref)
        else:
            return _s3_get_visit_ccd_fits_raw(ref)

    def get_metadata_sync(self, ref: CcdDataRef) -> DataSourceCcdMetadata:
        i = Instrument.get("LSSTCam")
        return DataSourceCcdMetadata(
            detector=i.ccd_2_detector[ref.ccd],
            ccd_name=ref.ccd,
            day_obs=-1,
            exposure=-1,
            visit_name=ref.visit,
            uuid=f"dummy-uuid-{ref.visit.name}-{ref.ccd}",
        )

    def get_exposure_data_types_sync(self, exposure_id: int) -> list[CcdDataType]:
        if visits := _load_shared_dummy_visits():
            matched_types = [
                CcdDataType(f"{VisitName(visit.id).repository_name}:{VisitName(visit.id).data_type}")
                for visit in visits
                if VisitName(visit.id).name == str(exposure_id)
            ]
            if matched_types:
                return matched_types
        return [CcdDataType(f"{dt.repository_name}:{dt.data_type}") for dt in config.ccd_data_types]


def _s3_get_visit_ccd_fits_raw(ref: CcdDataRef) -> bytes:
    key = f"{ref.visit.data_type}/{ref.visit.name}/{ref.ccd}.fits"
    return s3_download_object(config.s3_test_data, key)


def _s3_get_visit_ccd_fits_calexp(ref: CcdDataRef) -> bytes:
    def read(start: int, end: int) -> bytes:
        key = f'{ref.visit.data_type}/{ref.visit.name}/{ref.ccd}.fits'
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


def _default_dummy_visits() -> list[VisitEntry]:
    return [
        create_dummy_visit_entry("dummy:raw:broccoli", 20230101, "r", 30.0, target_name="dummy_target"),
        create_dummy_visit_entry("dummy:calexp:192350", 20230102, "g", 15.0, target_name="dummy_target_2"),
        *[create_dummy_visit_entry(f"dummy:raw:dummy-{i}", 20230104, "z") for i in range(50)],
    ]


def _load_shared_dummy_visits() -> list[VisitEntry] | None:
    try:
        payload = s3_download_object(config.s3_test_data, SHARED_SAMPLE_MANIFEST_KEY)
    except NoSuchKey:
        return None

    data = json.loads(payload)
    visits = data.get("visits")
    if not isinstance(visits, list):
        raise ValueError(f"Unexpected manifest format in {SHARED_SAMPLE_MANIFEST_KEY}")
    return [
        VisitEntry(**{key: value for key, value in visit.items() if key != "ccds"})
        for visit in visits
    ]


def _filter_visits(visits: list[VisitEntry], q: Query) -> list[VisitEntry]:
    filtered: list[VisitEntry] = []
    for visit in visits:
        visit_name = VisitName(visit.id)
        if visit_name.repository_name != q.repository_name:
            continue
        if visit_name.data_type != q.data_type:
            continue
        if q.day_obs is not None and visit.day_obs != q.day_obs:
            continue
        if q.exposure is not None and visit_name.name != str(q.exposure):
            continue
        filtered.append(visit)
    return filtered


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
