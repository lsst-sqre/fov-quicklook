import base64
import binascii
from datetime import datetime
from pathlib import Path

from quicklook.config import config
from quicklook.datasource.butler_datasource.instrument import Instrument
from quicklook.datasource.types import (
    QueryBuilderOptions,
    QueryWhereExample,
    VisitDayCount,
    VisitDayCountQuery,
    VisitEntry,
    VisitResolutionError,
)
from quicklook.review_app.shared_fixtures import DEFAULT_DUMMY_VISIT_COUNT, default_fixture_visits
from quicklook.types import CcdDataRef, CcdDataType, CcdName, VisitName, build_scope_id
from quicklook.utils.fits import fits_partial_load
from quicklook.utils.s3 import s3_download_object, s3_list_objects

from ..types import DataSourceBase, DataSourceCcdMetadata, Query


class DummyDataSource(DataSourceBase):
    def query_visits_sync(self, q: Query) -> list[VisitEntry]:
        visits = _default_dummy_visits()
        visits = _filter_visits(visits, q)
        return visits[q.offset : q.offset + q.limit]

    def query_visit_day_counts_sync(self, q: VisitDayCountQuery) -> list[VisitDayCount]:
        month_prefix = q.calendar_month.replace('-', '')
        counts: dict[int, int] = {}
        for visit in self.query_visits_sync(
            Query(
                repository_name=q.repository_name,
                collection=q.collection,
                dataset_type=q.dataset_type,
                limit=1000,
            )
        ):
            if not str(visit.day_obs).startswith(month_prefix):
                continue
            counts[visit.day_obs] = counts.get(visit.day_obs, 0) + 1
        return [VisitDayCount(day_obs=day_obs, count=count) for day_obs, count in sorted(counts.items())]

    def get_query_builder_options_sync(
        self,
        *,
        repository_name: str | None = None,
        collection: str | None = None,
        dataset_type: str | None = None,
    ) -> QueryBuilderOptions:
        visits = _default_dummy_visits()
        repositories = sorted({VisitName(visit.id).repository_name for visit in visits} | {scope.repository_name for scope in config.butler_scopes})
        selected_repository = repository_name if repository_name in repositories else (repositories[0] if repositories else None)
        scoped_visits = [
            visit
            for visit in visits
            if selected_repository is None or VisitName(visit.id).repository_name == selected_repository
        ]
        collection_search = collection.strip() if collection else ''
        collections = sorted({
            VisitName(visit.id).collection
            for visit in scoped_visits
            if not collection_search or collection_search.casefold() in VisitName(visit.id).collection.casefold()
        })
        selected_collection = collection if collection and any(candidate == collection for candidate in collections) else None
        dataset_type_search = dataset_type.strip() if dataset_type else ''
        dataset_types = sorted({
            VisitName(visit.id).dataset_type
            for visit in scoped_visits
            if not dataset_type_search or dataset_type_search.casefold() in VisitName(visit.id).dataset_type.casefold()
        })
        selected_dataset_type = dataset_type if dataset_type and any(candidate == dataset_type for candidate in dataset_types) else None
        where_examples = _build_dummy_where_examples(
            scoped_visits,
            collection=selected_collection,
            dataset_type=selected_dataset_type,
        )
        return QueryBuilderOptions(
            repositories=repositories,
            collections=collections,
            dataset_types=dataset_types,
            where_examples=where_examples,
        )

    def resolve_visit_sync(self, visit: VisitName) -> VisitName:
        if visit.data_type == "by_uuid":
            resolved_visit = _decode_dummy_visit_uuid(visit.name)
            if resolved_visit.repository_name != visit.repository_name:
                raise VisitResolutionError(f"Unknown dataset UUID: {visit.name}")
            return resolved_visit
        return visit

    def list_ccds_sync(self, visit: VisitName) -> list[CcdName]:
        visit = self.resolve_visit_sync(visit)
        ccds = [*_s3_list_visit_ccds(visit)]
        match config.environment:
            case 'test':
                ccds = ccds[:40]
            case 'development':
                ccds = ccds[:40]
        return ccds

    def get_data_sync(self, ref: CcdDataRef) -> bytes:
        ref = CcdDataRef(visit=self.resolve_visit_sync(ref.visit), ccd=ref.ccd)
        if ref.visit.dataset_type == "calexp":
            return _s3_get_visit_ccd_fits_calexp(ref)
        return _s3_get_visit_ccd_fits_raw(ref)

    def get_metadata_sync(self, ref: CcdDataRef) -> DataSourceCcdMetadata:
        ref = CcdDataRef(visit=self.resolve_visit_sync(ref.visit), ccd=ref.ccd)
        instrument = Instrument.get("LSSTCam")
        return DataSourceCcdMetadata(
            detector=instrument.ccd_2_detector[ref.ccd],
            ccd_name=ref.ccd,
            day_obs=-1,
            exposure=-1,
            visit_name=ref.visit,
            uuid=f"dummy-uuid-{ref.visit.name}-{ref.ccd}",
        )

    def get_visit_representative_uuid_sync(self, visit: VisitName) -> str:
        return _encode_dummy_visit_uuid(self.resolve_visit_sync(visit))

    def get_exposure_data_types_sync(self, exposure_id: int) -> list[CcdDataType]:
        matched_scope_ids: list[CcdDataType] = []
        for visit in _default_dummy_visits():
            visit_name = VisitName(visit.id)
            if visit_name.name != str(exposure_id):
                continue
            matched_scope_ids.append(CcdDataType(visit.scope_id))
        if matched_scope_ids:
            return matched_scope_ids
        return [
            CcdDataType(scope.id or build_scope_id(scope.repository_name, scope.collection, scope.dataset_type))
            for scope in config.butler_scopes
        ]


def _s3_get_visit_ccd_fits_raw(ref: CcdDataRef) -> bytes:
    key = f"{ref.visit.dataset_type}/{_shared_dummy_data_name()}/{ref.ccd}.fits"
    return s3_download_object(config.s3_test_data, key)


def _s3_get_visit_ccd_fits_calexp(ref: CcdDataRef) -> bytes:
    def read(start: int, end: int) -> bytes:
        key = f'{ref.visit.dataset_type}/{_shared_dummy_data_name()}/{ref.ccd}.fits'
        return s3_download_object(config.s3_test_data, key, offset=start, length=end - start)

    return fits_partial_load(read, [0, 1])


def _s3_list_visit_ccds(visit: VisitName) -> list[CcdName]:
    prefix = f"{visit.dataset_type}/{_shared_dummy_data_name()}/"
    return [
        CcdName(Path(Path(obj.key).name).stem)
        for obj in s3_list_objects(config.s3_test_data, prefix=prefix)
        if obj.type == 'file'
    ]


def _encode_dummy_visit_uuid(visit: VisitName) -> str:
    encoded = base64.urlsafe_b64encode(str(visit).encode("utf-8")).decode("ascii")
    return encoded.rstrip("=")


def _decode_dummy_visit_uuid(uuid_text: str) -> VisitName:
    padding = "=" * (-len(uuid_text) % 4)
    try:
        visit_name = base64.urlsafe_b64decode(f"{uuid_text}{padding}").decode("utf-8")
    except (binascii.Error, UnicodeDecodeError) as e:  # pragma: no cover
        raise VisitResolutionError(f"Unknown dataset UUID: {uuid_text}") from e
    return VisitName(visit_name)


def _build_dummy_visit(repository_name: str, collection: str, dataset_type: str, identifier: str) -> VisitName:
    return VisitName.from_parts(
        repository_name=repository_name,
        collection=collection,
        dataset_type=dataset_type,
        dimensions={'exposure': identifier},
    )


def _default_dummy_scope() -> tuple[str, str, str]:
    raw_scope = next((scope for scope in config.butler_scopes if scope.dataset_type == 'raw'), None)
    if raw_scope is not None:
        return raw_scope.repository_name, raw_scope.collection, raw_scope.dataset_type
    return 'dummy', 'LSSTCam/raw/all', 'raw'


def _shared_dummy_data_name() -> str:
    return str(default_fixture_visits(1)[0].exposure_id)


def _default_dummy_visits() -> list[VisitEntry]:
    repository_name, collection, dataset_type = _default_dummy_scope()
    return [
        create_dummy_visit_entry(
            _build_dummy_visit(repository_name, collection, dataset_type, str(visit.exposure_id)),
            visit.day_obs,
            visit.physical_filter,
            exposure_time=visit.exposure_time,
            obs_id=visit.obs_id,
            science_program=visit.science_program,
            observation_type=visit.observation_type,
            observation_reason=visit.observation_reason,
            target_name=visit.target_name,
            utc_start=visit.utc_start,
        )
        for visit in default_fixture_visits(DEFAULT_DUMMY_VISIT_COUNT)
    ]


def _filter_visits(visits: list[VisitEntry], q: Query) -> list[VisitEntry]:
    return [
        visit
        for visit in visits
        if _matches_scope(VisitName(visit.id), q) and _matches_where(visit, q.where)
    ]


def _matches_scope(visit_name: VisitName, q: Query) -> bool:
    return (
        visit_name.repository_name == q.repository_name
        and visit_name.collection == q.collection
        and visit_name.dataset_type == q.dataset_type
    )


def _matches_where(visit: VisitEntry, where: str | None) -> bool:
    if not where:
        return True
    visit_name = VisitName(visit.id)
    values: dict[str, str] = {
        'day_obs': str(visit.day_obs),
        **visit_name.dimensions,
    }
    for cond in where.split(' and '):
        if '>=' in cond:
            key, value = cond.split('>=', maxsplit=1)
            if values.get(key) is None or int(values[key]) < int(value):
                return False
            continue
        if '<' in cond:
            key, value = cond.split('<', maxsplit=1)
            if values.get(key) is None or int(values[key]) >= int(value):
                return False
            continue
        if '=' in cond:
            key, value = cond.split('=', maxsplit=1)
            if values.get(key) != value:
                return False
            continue
        raise ValueError(f'Unsupported where clause for dummy datasource: {cond}')
    return True


def create_dummy_visit_entry(
    visit: VisitName | str,
    day_obs: int,
    physical_filter: str,
    exposure_time: float = 20.0,
    obs_id: str = "dummy_obs_id",
    science_program: str = "dummy_program",
    observation_type: str = "science",
    observation_reason: str = "test",
    target_name: str | None = None,
    utc_start: datetime | None = None,
) -> VisitEntry:
    visit_name = VisitName(visit) if isinstance(visit, str) else visit
    if target_name is None:
        target_name = f"dummy_target_{visit_name.name}"

    return VisitEntry(
        id=str(visit_name),
        display_id=visit_name.cache_key,
        scope_id=visit_name.scope_id,
        day_obs=day_obs,
        physical_filter=physical_filter,
        obs_id=obs_id,
        exposure_time=exposure_time,
        science_program=science_program,
        observation_type=observation_type,
        observation_reason=observation_reason,
        target_name=target_name,
        uuid=_encode_dummy_visit_uuid(visit_name),
        utc_start=utc_start,
    )


def _build_dummy_where_examples(
    visits: list[VisitEntry],
    *,
    collection: str | None,
    dataset_type: str | None,
) -> list[QueryWhereExample]:
    if collection is None or dataset_type is None:
        return []

    matching_visits = [
        visit
        for visit in visits
        if VisitName(visit.id).collection == collection and VisitName(visit.id).dataset_type == dataset_type
    ]
    if not matching_visits:
        return []

    latest_visit = max(matching_visits, key=lambda visit: (visit.day_obs, visit.display_id))
    visit_name = VisitName(latest_visit.id)
    examples = [
        QueryWhereExample(
            label=f"Latest day_obs ({latest_visit.day_obs})",
            where=f"day_obs={latest_visit.day_obs}",
        ),
    ]
    if visit_name.dimensions:
        key = sorted(visit_name.dimensions)[0]
        value = visit_name.dimensions[key]
        examples.append(
            QueryWhereExample(
                label=f"Latest {key} ({value})",
                where=f"{key}={value}",
            )
        )
    return examples
