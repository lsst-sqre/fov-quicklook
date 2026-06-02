import threading
from collections import Counter
from datetime import date
from functools import lru_cache
from itertools import islice
from types import EllipsisType
from typing import TYPE_CHECKING, Any, Iterable, cast
from uuid import UUID

from lsst.resources import ResourcePath

import quicklook.mylogging
from quicklook.config import ButlerScopeConfig, config
from quicklook.datasets import Dataset, get_dataset
from quicklook.datasource.types import QueryBuilderOptions, QueryWhereExample, VisitDayCount, VisitDayCountQuery, VisitEntry
from quicklook.types import CcdDataRef, CcdDataType, CcdName, VisitName, build_scope_id

from ..types import DataSourceBase, DataSourceCcdMetadata, Query, ResolvedVisitInfo, VisitResolutionError
from .instrument import Instrument
from .retrieve_data import retrieve_data

if TYPE_CHECKING:
    from lsst.daf.butler import Butler as ButlerType
    from lsst.daf.butler import DatasetRef as ButlerDatasetRef
    from lsst.daf.butler import DimensionRecord as ButlerDimensionRecord
    from lsst.daf.butler.registry import CollectionArgType as ButlerCollectionArgType
else:
    ButlerType = Any
    ButlerDatasetRef = Any
    ButlerDimensionRecord = Any
    ButlerCollectionArgType = Any


BY_UUID_DATA_TYPE = CcdDataType('by_uuid')
_QUERY_BUILDER_SUGGESTION_LIMIT = 100
_QUERY_BUILDER_PREFETCH_WAIT_SECONDS = 1.0
_resolved_visit_runs: dict[str, str] = {}
_resolved_visit_runs_lock = threading.Lock()
_query_builder_metadata_cache: dict[tuple[str, str], '_QueryRepositoryMetadata'] = {}
_query_builder_metadata_loading: dict[tuple[str, str], threading.Event] = {}
_query_builder_metadata_lock = threading.Lock()
logger = quicklook.mylogging.getLogger(__name__)


class _QueryRepositoryMetadata:
    def __init__(self, *, collections: tuple[str, ...], dataset_types: tuple[str, ...]):
        self.collections = collections
        self.dataset_types = dataset_types


class ButlerDataSource(DataSourceBase):  # pragma: no cover
    def __init__(self):
        from .butlerutils import chown_pgpassfile

        chown_pgpassfile()

    def warm_query_builder_options_metadata_sync(self) -> None:
        for repository_name in _query_repository_names():
            _prime_query_builder_metadata_async(repository_name)

    def query_visits_sync(self, q: Query) -> list[VisitEntry]:
        return _get_scope_datasource(
            repository_name=q.repository_name,
            collection=q.collection,
            dataset_type=q.dataset_type,
        ).query_visits(q)

    def query_visit_day_counts_sync(self, q: VisitDayCountQuery) -> list[VisitDayCount]:
        return _get_scope_datasource(
            repository_name=q.repository_name,
            collection=q.collection,
            dataset_type=q.dataset_type,
        ).query_visit_day_counts(q.calendar_month)

    def get_query_builder_options_sync(
        self,
        *,
        repository_name: str | None = None,
        collection: str | None = None,
        dataset_type: str | None = None,
    ) -> QueryBuilderOptions:
        repositories = _query_repository_names()
        selected_repository = repository_name if repository_name in repositories else (repositories[0] if repositories else None)
        if selected_repository is None:
            return QueryBuilderOptions(
                repositories=[],
                collections=[],
                dataset_types=[],
                where_examples=[],
            )

        _prime_query_builder_metadata_async(selected_repository)
        selected_collection = _normalize_option_search_text(collection)
        selected_dataset_type = _normalize_option_search_text(dataset_type)
        if (
            selected_collection is not None
            and selected_dataset_type is not None
            and _collection_exists_for_repository(selected_repository, selected_collection)
            and _dataset_type_exists_for_repository(selected_repository, selected_dataset_type)
        ):
            return QueryBuilderOptions(
                repositories=repositories,
                collections=[selected_collection],
                dataset_types=[selected_dataset_type],
                where_examples=[],
            )

        collections = _query_collections_for_repository(
            selected_repository,
            search_text=collection,
        )
        selected_collection = (
            collection
            if collection and _collection_exists_for_repository(selected_repository, collection)
            else None
        )
        dataset_types = _query_dataset_types_for_repository(
            selected_repository,
            search_text=dataset_type,
        )
        selected_dataset_type = (
            dataset_type
            if dataset_type and _dataset_type_exists_for_repository(selected_repository, dataset_type)
            else None
        )
        return QueryBuilderOptions(
            repositories=repositories,
            collections=collections,
            dataset_types=dataset_types,
            # Keep this endpoint limited to registry metadata. Probing dataset
            # contents here made exact matches for large collections unstable
            # enough to flap the deployed frontend.
            where_examples=[],
        )

    def resolve_visit_sync(self, visit: VisitName) -> VisitName:
        return self.resolve_visit_info_sync(visit).visit_name

    def resolve_visit_info_sync(self, visit: VisitName) -> ResolvedVisitInfo:
        return _resolve_visit_info(visit)

    def get_visit_representative_uuid_sync(self, visit: VisitName) -> str:
        visit = self.resolve_visit_sync(visit)
        return _get_visit_datasource(visit).get_visit_representative_uuid_sync(visit)

    def list_ccds_sync(self, visit: VisitName) -> list[CcdName]:
        visit = self.resolve_visit_sync(visit)
        return _get_visit_datasource(visit).list_ccds(visit)

    def get_data_sync(self, ref: CcdDataRef) -> bytes:
        ref = _resolve_ref(ref, self.resolve_visit_sync(ref.visit))
        return _get_visit_datasource(ref.visit).get_data(ref)

    def get_metadata_sync(self, ref: CcdDataRef) -> DataSourceCcdMetadata:
        ref = _resolve_ref(ref, self.resolve_visit_sync(ref.visit))
        return _get_visit_datasource(ref.visit).get_metadata(ref)

    def get_exposure_data_types_sync(self, exposure_id: int) -> list[CcdDataType]:
        scope_ids: list[CcdDataType] = []
        for scope in config.butler_scopes:
            datasource = _get_scope_datasource(
                repository_name=scope.repository_name,
                collection=scope.collection,
                dataset_type=scope.dataset_type,
                instrument=scope.instrument,
            )
            if datasource.dataset.quicklook_dimension != 'exposure':
                continue
            if datasource.exposure_exists(exposure_id):
                scope_ids.append(CcdDataType(scope.id))
        return scope_ids


class ScopedButlerDataSource:
    def __init__(
        self,
        *,
        repository_name: str,
        collection: str,
        dataset_type: str,
        instrument: str = 'LSSTCam',
    ):
        from lsst.daf.butler import Butler

        self._repository_name = repository_name
        self._collection = collection
        self._dataset_type = dataset_type
        self._instrument = instrument
        self._dataset = get_dataset(dataset_type)
        self._butler: ButlerType = Butler(
            repository_name,
            instrument=instrument,
            collections=[collection],
        )  # type: ignore

    @property
    def repository_name(self) -> str:
        return self._repository_name

    @property
    def collection(self) -> str:
        return self._collection

    @property
    def dataset_type(self) -> str:
        return self._dataset_type

    @property
    def dataset(self) -> Dataset:
        return self._dataset

    @property
    def instrument(self) -> str:
        return self._instrument

    @property
    def data_id_dimension(self) -> str:
        return self.dataset.quicklook_dimension

    @property
    def partial(self) -> bool:
        return self.dataset.partial

    def query_visits(self, q: Query) -> list[VisitEntry]:
        records = self._query_dimension_records(
            self.data_id_dimension,
            datasets=self.dataset_type,
            where=q.where or self._build_latest_day_where(),
            limit=q.limit,
            offset=q.offset,
            order_by=self._normalize_order_by(q.order_by, q.reverse),
        )
        return [self._visit_entry_from_record(record) for record in records]

    def query_visit_day_counts(self, calendar_month: str) -> list[VisitDayCount]:
        start_day_obs, end_day_obs = _calendar_month_day_obs_range(calendar_month)
        data_ids = self._query_data_ids(
            ['day_obs', self.data_id_dimension],
            datasets=self.dataset_type,
            where=f"day_obs>={start_day_obs} and day_obs<{end_day_obs}",
            order_by=['day_obs'],
        )
        counts_by_day_obs = Counter(int(data_id['day_obs']) for data_id in data_ids)
        return [VisitDayCount(day_obs=day_obs, count=count) for day_obs, count in sorted(counts_by_day_obs.items())]

    def query_where_examples(self) -> list[QueryWhereExample]:
        latest_day_where = self._build_latest_day_where()
        records = self._query_dimension_records(
            self.data_id_dimension,
            datasets=self.dataset_type,
            where=latest_day_where,
            limit=1,
            order_by=self._normalize_order_by(None, None),
        )
        if len(records) == 0:
            return []

        record = records[0]
        examples: list[QueryWhereExample] = []
        day_obs = getattr(record, 'day_obs', None)
        if day_obs is not None:
            day_obs_value = int(day_obs)
            month_start, month_end = _day_obs_month_range(day_obs_value)
            examples.extend([
                QueryWhereExample(
                    label=f'Latest day_obs ({day_obs_value})',
                    where=f'day_obs={day_obs_value}',
                ),
                QueryWhereExample(
                    label=f'Month of latest day_obs ({day_obs_value // 100})',
                    where=f'day_obs>={month_start} and day_obs<{month_end}',
                ),
            ])

        record_id = getattr(record, 'id', None)
        if record_id is not None:
            examples.append(
                QueryWhereExample(
                    label=f'Latest {self.data_id_dimension} ({record_id})',
                    where=f'{self.data_id_dimension}={record_id}',
                )
            )

        deduped: list[QueryWhereExample] = []
        seen = set()
        for example in examples:
            if example.where in seen:
                continue
            seen.add(example.where)
            deduped.append(example)
        return deduped

    def list_ccds(self, visit: VisitName) -> list[CcdName]:
        refs = self._query_datasets(self._visit_where(visit), visit=visit)
        instrument = Instrument.get(self.instrument)
        ccd_names = list(dict.fromkeys(CcdName(instrument.detector_2_ccd[ref.dataId['detector']]) for ref in refs))  # type: ignore
        if self.dataset.exclude_corner_rafts:
            ccd_names = [ccd_name for ccd_name in ccd_names if ccd_name[:3] not in {'R00', 'R40', 'R04', 'R44'}]
        return ccd_names

    def exposure_exists(self, exposure_id: int) -> bool:
        from lsst.daf.butler._exceptions import EmptyQueryResultError, MissingCollectionError

        try:
            refs = self._query_datasets(f"{self.data_id_dimension}={exposure_id}", limit=1)
        except (EmptyQueryResultError, MissingCollectionError):
            return False
        return len(refs) > 0

    def get_data(self, ref: CcdDataRef) -> bytes:
        self._dataset_ref(ref)
        if self._is_virtual_review_app_fixture(ref.visit):
            return self._render_virtual_review_app_raw(ref)
        return retrieve_data(self._get_uri(ref), partial=self.partial)

    def get_metadata(self, ref: CcdDataRef) -> DataSourceCcdMetadata:
        detector_id = Instrument.get(self.instrument).ccd_2_detector[ref.ccd]
        butler_refs = self._query_datasets(self._visit_where(ref.visit, detector=detector_id), visit=ref.visit)
        if len(butler_refs) != 1:
            raise ValueError(
                f"Cannot find unique dataset for {ref.visit.cache_key} and detector {detector_id}. "
                f"found {len(butler_refs)} matches"
            )
        butler_ref = butler_refs[0]
        return DataSourceCcdMetadata(
            detector=detector_id,
            ccd_name=ref.ccd,
            day_obs=butler_ref.dataId.get('day_obs', -1),
            exposure=butler_ref.dataId.get(self.data_id_dimension, -1),
            visit_name=ref.visit,
            uuid=str(butler_ref.id),
        )

    def get_visit_representative_uuid_sync(self, visit: VisitName) -> str:
        refs = self._query_datasets(self._visit_where(visit), visit=visit, limit=1)
        if len(refs) == 0:
            raise VisitResolutionError(f"Cannot find dataset UUID for visit {visit.cache_key}")
        return str(refs[0].id)

    def _get_uri(self, ref: CcdDataRef) -> ResourcePath:
        butler_ref = self._dataset_ref(ref)
        return self._butler.getURI(butler_ref)  # type: ignore

    def _dataset_ref(self, ref: CcdDataRef) -> ButlerDatasetRef:
        detector_id = Instrument.get(self.instrument).ccd_2_detector[ref.ccd]
        return self._refs_by_visit(ref.visit)[detector_id]

    def _refs_by_visit(self, visit: VisitName) -> dict[int, ButlerDatasetRef]:
        refs = self._query_datasets(self._visit_where(visit), visit=visit)
        refs_by_detector: dict[int, ButlerDatasetRef] = {}
        for ref in refs:
            detector = cast(int, ref.dataId['detector'])
            if detector in refs_by_detector:
                raise ValueError(
                    f'Cannot find unique dataset for {visit.cache_key} and detector {detector}. found multiple matches'
                )
            refs_by_detector[detector] = ref
        return refs_by_detector

    def _build_latest_day_where(self) -> str | None:
        day_obs = self._get_latest_day_obs()
        if day_obs is None:
            return None
        return f'day_obs={day_obs}'

    def _get_latest_day_obs(self) -> int | None:
        records = self._query_dimension_records(
            self.data_id_dimension,
            datasets=self.dataset_type,
            limit=1,
            order_by=['-day_obs'],
        )
        if len(records) == 0:
            return None
        return cast(int, records[0].day_obs)

    def _normalize_order_by(self, field: str | None, reverse: bool | None) -> list[str]:
        default = self.dataset.default_order_by[0]
        default_field = default.removeprefix('-')
        default_reverse = default.startswith('-')
        selected_field = field or default_field
        selected_reverse = default_reverse if reverse is None else reverse
        prefix = '-' if selected_reverse else ''
        return [f'{prefix}{selected_field}']

    def _visit_where(self, visit: VisitName, *, detector: int | None = None) -> str:
        conds = [f'{key}={value}' for key, value in visit.dimensions.items()]
        if detector is not None:
            conds.append(f'detector={detector}')
        return ' and '.join(conds)

    def _query_dimension_records(
        self,
        dimension: str,
        *,
        datasets: str | None = None,
        where: str | None = None,
        limit: int | None = None,
        offset: int = 0,
        order_by: list[str] | None = None,
    ) -> list[ButlerDimensionRecord]:
        kwargs: dict[str, Any] = {}
        if datasets is not None:
            kwargs['datasets'] = datasets
            if self.dataset_type == 'difference_image':
                kwargs['collections'] = self._query_collections()
        if where:
            kwargs['where'] = where
        records = self._butler.registry.queryDimensionRecords(dimension, **kwargs)
        if order_by is not None:
            records = records.order_by(*order_by)
        if offset > 0:
            stop = None if limit is None else offset + limit
            return list(islice(records, offset, stop))
        if limit is not None:
            records = records.limit(limit)
        return list(records)

    def _query_data_ids(
        self,
        dimensions: list[str],
        *,
        datasets: str | None = None,
        where: str | None = None,
        limit: int | None = None,
        order_by: list[str] | None = None,
    ) -> list[Any]:
        kwargs: dict[str, Any] = {}
        if datasets is not None:
            kwargs['datasets'] = datasets
            if self.dataset_type == 'difference_image':
                kwargs['collections'] = self._query_collections()
        if where:
            kwargs['where'] = where
        data_ids = self._butler.registry.queryDataIds(dimensions, **kwargs)
        if order_by is not None:
            data_ids = data_ids.order_by(*order_by)
        if limit is not None:
            data_ids = data_ids.limit(limit)
        return list(data_ids)

    def _visit_entry_from_record(self, record: ButlerDimensionRecord) -> VisitEntry:
        visit = VisitName.from_parts(
            repository_name=self.repository_name,
            collection=self._resolved_collection_for_record(record),
            dataset_type=self.dataset_type,
            dimensions={self.data_id_dimension: getattr(record, 'id')},
        )
        return VisitEntry(
            id=str(visit),
            display_id=visit.cache_key,
            scope_id=visit.scope_id,
            obs_id=_record_string_attr(record, 'obs_id', default=str(record.id)),
            day_obs=cast(int, getattr(record, 'day_obs')),
            physical_filter=_record_string_attr(record, 'physical_filter', 'band'),
            exposure_time=_record_float_attr(record, 'exposure_time'),
            science_program=_record_string_attr(record, 'science_program'),
            observation_type=_record_string_attr(record, 'observation_type'),
            observation_reason=_record_string_attr(record, 'observation_reason'),
            target_name=_record_string_attr(record, 'target_name'),
        )

    def _resolved_collection_for_record(self, record: ButlerDimensionRecord) -> str:
        if self.dataset_type != 'difference_image':
            return self.collection
        refs = self._query_datasets(f'{self.data_id_dimension}={getattr(record, "id")}', limit=1)
        if len(refs) == 0:
            return self.collection
        return cast(str, refs[0].run)

    def _query_datasets(
        self,
        where: str,
        *,
        visit: VisitName | None = None,
        limit: int | None = None,
    ) -> list[ButlerDatasetRef]:
        if self.dataset_type != 'difference_image':
            refs = self._butler.query_datasets(self.dataset_type, where=where, limit=limit)
            return list(refs)

        results = self._butler.registry.queryDatasets(
            self.dataset_type,
            collections=self._query_collections(visit),
            where=where,
        )
        if limit is not None:
            return list(islice(results, limit))
        return list(results)

    def _query_collections(self, visit: VisitName | None = None) -> ButlerCollectionArgType | EllipsisType:
        if self.dataset_type != 'difference_image':
            return [self.collection]
        if visit is not None and (run := _get_resolved_visit_run(visit)) is not None:
            return [run]
        return ...

    def _is_virtual_review_app_fixture(self, visit: VisitName) -> bool:
        from quicklook.review_app.shared_fixtures import FIXTURE_REPOSITORY_NAME

        return visit.repository_name == FIXTURE_REPOSITORY_NAME and visit.dataset_type == 'raw'

    def _render_virtual_review_app_raw(self, ref: CcdDataRef) -> bytes:
        from quicklook.review_app.synthetic import render_virtual_raw_fits_bytes

        exposure_id = int(ref.visit.name)
        exposure = self._get_exposure_record(exposure_id)
        return render_virtual_raw_fits_bytes(
            ccd_name=ref.ccd,
            exposure_id=exposure_id,
            day_obs=cast(int, getattr(exposure, "day_obs")),
            physical_filter=_record_string_attr(exposure, "physical_filter", "band"),
            obs_id=_record_string_attr(exposure, "obs_id", default=str(exposure_id)),
        )

    def _get_exposure_record(self, exposure_id: int) -> ButlerDimensionRecord:
        records = self._query_dimension_records("exposure", where=f"exposure={exposure_id}", limit=1)
        if len(records) != 1:
            raise ValueError(f"Cannot find unique exposure record for exposure {exposure_id}. found {len(records)} matches")
        return records[0]


def _resolve_ref(ref: CcdDataRef, visit: VisitName) -> CcdDataRef:
    if visit == ref.visit:
        return ref
    return CcdDataRef(visit=visit, ccd=ref.ccd)


def _calendar_month_day_obs_range(calendar_month: str) -> tuple[int, int]:
    year_text, month_text = calendar_month.split('-', maxsplit=1)
    year = int(year_text)
    month = int(month_text)
    start = date(year, month, 1)
    end = date(year + (1 if month == 12 else 0), 1 if month == 12 else month + 1, 1)
    return int(start.strftime('%Y%m%d')), int(end.strftime('%Y%m%d'))


def _day_obs_month_range(day_obs: int) -> tuple[int, int]:
    day_obs_text = str(day_obs)
    return _calendar_month_day_obs_range(f'{day_obs_text[:4]}-{day_obs_text[4:6]}')


def _resolve_visit_info(visit: VisitName) -> ResolvedVisitInfo:
    if visit.data_type != BY_UUID_DATA_TYPE:
        return ResolvedVisitInfo(visit_name=visit)
    return _resolve_visit_cache(str(visit))


@lru_cache(256)
def _resolve_visit_cache(visit_name: str) -> ResolvedVisitInfo:
    visit = VisitName(visit_name)
    repository_butler = _get_repository_butler(visit.repository_name)
    dataset_ref = repository_butler.registry.getDataset(UUID(visit.name))
    if dataset_ref is None:
        raise VisitResolutionError(f'Unknown dataset UUID: {visit.name}')

    dataset_type = cast(str, dataset_ref.datasetType.name)
    collection = cast(str, dataset_ref.run)
    datasource = _get_scope_datasource(
        repository_name=visit.repository_name,
        collection=collection,
        dataset_type=dataset_type,
    )
    data_id = dataset_ref.dataId.get(datasource.data_id_dimension)
    if data_id is None:
        raise VisitResolutionError(
            f'UUID {visit.name} resolved to dataset type {dataset_type}, but dataId does not contain {datasource.data_id_dimension}'
        )
    resolved_visit = VisitName.from_parts(
        repository_name=visit.repository_name,
        collection=collection,
        dataset_type=dataset_type,
        dimensions={datasource.data_id_dimension: data_id},
    )
    _remember_resolved_visit_run(resolved_visit, collection)
    detector = dataset_ref.dataId.get('detector')
    return ResolvedVisitInfo(
        visit_name=resolved_visit,
        detector=None if detector is None else int(detector),
    )


def _remember_resolved_visit_run(visit: VisitName, run: str) -> None:
    with _resolved_visit_runs_lock:
        if len(_resolved_visit_runs) >= 256 and visit.cache_key not in _resolved_visit_runs:
            _resolved_visit_runs.pop(next(iter(_resolved_visit_runs)))
        _resolved_visit_runs[visit.cache_key] = run


def _get_resolved_visit_run(visit: VisitName) -> str | None:
    with _resolved_visit_runs_lock:
        return _resolved_visit_runs.get(visit.cache_key)


def _clear_resolved_visit_run_cache() -> None:
    with _resolved_visit_runs_lock:
        _resolved_visit_runs.clear()


def _record_string_attr(record: ButlerDimensionRecord, *names: str, default: str = '') -> str:
    for name in names:
        value = getattr(record, name, None)
        if value is not None:
            return cast(str, value)
    return default


def _record_float_attr(record: ButlerDimensionRecord, name: str, default: float = 0.0) -> float:
    value = getattr(record, name, None)
    if value is None:
        return default
    return float(value)


def _find_scope_config(repository_name: str, collection: str, dataset_type: str) -> ButlerScopeConfig | None:
    for scope in config.butler_scopes:
        if (
            scope.repository_name == repository_name
            and scope.collection == collection
            and scope.dataset_type == dataset_type
        ):
            return scope
    for scope in config.butler_scopes:
        if scope.repository_name == repository_name and scope.dataset_type == dataset_type:
            return scope
    return None


def _get_visit_datasource(visit: VisitName) -> ScopedButlerDataSource:
    return _get_scope_datasource(
        repository_name=visit.repository_name,
        collection=visit.collection,
        dataset_type=visit.dataset_type,
    )


def _get_scope_datasource(
    *,
    repository_name: str,
    collection: str,
    dataset_type: str,
    instrument: str | None = None,
) -> ScopedButlerDataSource:
    thread_id = threading.get_ident()
    return _get_scope_datasource_cache(
        repository_name=repository_name,
        collection=collection,
        dataset_type=dataset_type,
        instrument=instrument or (_find_scope_config(repository_name, collection, dataset_type) or ButlerScopeConfig(
            dataset_type=dataset_type,
            display_name=dataset_type,
            collection=collection,
            repository_name=repository_name,
        )).instrument,
        thread_id=thread_id,
    )


@lru_cache(128)
def _get_scope_datasource_cache(
    *,
    repository_name: str,
    collection: str,
    dataset_type: str,
    instrument: str,
    thread_id: int,
) -> ScopedButlerDataSource:
    del thread_id
    return ScopedButlerDataSource(
        repository_name=repository_name,
        collection=collection,
        dataset_type=dataset_type,
        instrument=instrument,
    )


def _get_repository_butler(repository_name: str) -> ButlerType:
    thread_id = threading.get_ident()
    return _get_repository_butler_cache(repository_name, thread_id=thread_id)


@lru_cache(32)
def _get_repository_butler_cache(repository_name: str, thread_id: int) -> ButlerType:
    del thread_id
    from lsst.daf.butler import Butler

    return Butler(repository_name)  # type: ignore


def _query_repository_names() -> list[str]:
    return sorted({scope.repository_name for scope in config.butler_scopes})


def _repository_instrument(repository_name: str) -> str:
    for scope in config.butler_scopes:
        if scope.repository_name == repository_name:
            return scope.instrument
    return 'LSSTCam'


def _get_query_repository_butler(repository_name: str, instrument: str) -> ButlerType:
    thread_id = threading.get_ident()
    return _get_query_repository_butler_cache(repository_name, instrument, thread_id=thread_id)


@lru_cache(32)
def _get_query_repository_butler_cache(repository_name: str, instrument: str, thread_id: int) -> ButlerType:
    del thread_id
    from lsst.daf.butler import Butler

    return Butler(repository_name, instrument=instrument, without_datastore=True)  # type: ignore


def _dataset_required_dimension_names(dataset_type: Any) -> tuple[str, ...]:
    required = getattr(dataset_type.dimensions, 'required', ())
    return tuple(sorted(cast(str, getattr(dimension, 'name', str(dimension))) for dimension in required))


def _prime_query_builder_metadata_async(repository_name: str) -> None:
    instrument = _repository_instrument(repository_name)
    key = (repository_name, instrument)
    with _query_builder_metadata_lock:
        if key in _query_builder_metadata_cache or key in _query_builder_metadata_loading:
            return
        event = threading.Event()
        _query_builder_metadata_loading[key] = event

    def worker() -> None:
        try:
            metadata = _load_query_repository_metadata(repository_name, instrument)
        except Exception:
            with _query_builder_metadata_lock:
                _query_builder_metadata_loading.pop(key, None)
                event.set()
            logger.exception(
                "Failed to preload Data Query metadata for repository=%s instrument=%s",
                repository_name,
                instrument,
            )
        else:
            with _query_builder_metadata_lock:
                _query_builder_metadata_cache[key] = metadata
                _query_builder_metadata_loading.pop(key, None)
                event.set()

    threading.Thread(
        target=worker,
        name=f'query-builder-metadata-{repository_name}',
        daemon=True,
    ).start()


def _get_query_repository_metadata_if_available(
    repository_name: str,
    *,
    wait_for_prefetch: bool = False,
) -> _QueryRepositoryMetadata | None:
    instrument = _repository_instrument(repository_name)
    key = (repository_name, instrument)
    with _query_builder_metadata_lock:
        metadata = _query_builder_metadata_cache.get(key)
        event = _query_builder_metadata_loading.get(key)
    if metadata is not None:
        return metadata
    if wait_for_prefetch and event is not None:
        event.wait(timeout=_QUERY_BUILDER_PREFETCH_WAIT_SECONDS)
        with _query_builder_metadata_lock:
            return _query_builder_metadata_cache.get(key)
    return None


def _load_query_repository_metadata(repository_name: str, instrument: str) -> _QueryRepositoryMetadata:
    butler = _get_query_repository_butler(repository_name, instrument)
    collections = tuple(sorted(cast(str, collection) for collection in butler.registry.queryCollections('*', flattenChains=False)))
    dataset_types: set[str] = set()
    for dataset_type in butler.registry.queryDatasetTypes('*'):
        dataset_type_name = cast(str, dataset_type.name)
        try:
            get_dataset(dataset_type_name).quicklook_dimensions(_dataset_required_dimension_names(dataset_type))
        except ValueError:
            continue
        dataset_types.add(dataset_type_name)
    return _QueryRepositoryMetadata(
        collections=collections,
        dataset_types=tuple(sorted(dataset_types)),
    )


def _filter_query_builder_options(options: tuple[str, ...], search_text: str) -> list[str]:
    normalized_search_text = search_text.casefold()
    return [
        option for option in options
        if normalized_search_text in option.casefold()
    ][: _QUERY_BUILDER_SUGGESTION_LIMIT]


def _query_collections_for_repository(repository_name: str, *, search_text: str | None = None) -> list[str]:
    if not (search := _normalize_option_search_text(search_text)):
        return []
    metadata = _get_query_repository_metadata_if_available(repository_name, wait_for_prefetch=True)
    if metadata is None:
        _prime_query_builder_metadata_async(repository_name)
        return []
    return _filter_query_builder_options(metadata.collections, search)


@lru_cache(128)
def _query_collections_for_repository_cache(
    repository_name: str,
    instrument: str,
    search_text: str,
    thread_id: int,
) -> tuple[str, ...]:
    del thread_id
    butler = _get_query_repository_butler(repository_name, instrument)
    collections = butler.registry.queryCollections(
        _build_contains_glob(search_text),
        flattenChains=False,
    )
    return tuple(sorted(cast(str, collection) for collection in islice(collections, _QUERY_BUILDER_SUGGESTION_LIMIT)))


def _query_dataset_types_for_repository(repository_name: str, *, search_text: str | None = None) -> list[str]:
    if not (search := _normalize_option_search_text(search_text)):
        return []
    metadata = _get_query_repository_metadata_if_available(repository_name, wait_for_prefetch=True)
    if metadata is None:
        _prime_query_builder_metadata_async(repository_name)
        return []
    return _filter_query_builder_options(metadata.dataset_types, search)


@lru_cache(128)
def _query_dataset_types_for_repository_cache(
    repository_name: str,
    instrument: str,
    search_text: str,
    thread_id: int,
) -> tuple[str, ...]:
    del thread_id
    butler = _get_query_repository_butler(repository_name, instrument)
    dataset_types: list[str] = []
    for dataset_type in butler.registry.queryDatasetTypes(_build_contains_glob(search_text)):
        dataset_type_name = cast(str, dataset_type.name)
        try:
            get_dataset(dataset_type_name).quicklook_dimensions(_dataset_required_dimension_names(dataset_type))
        except ValueError:
            continue
        dataset_types.append(dataset_type_name)
        if len(dataset_types) >= _QUERY_BUILDER_SUGGESTION_LIMIT:
            break
    return tuple(sorted(set(dataset_types)))


def _collection_exists_for_repository(repository_name: str, collection: str) -> bool:
    metadata = _get_query_repository_metadata_if_available(repository_name, wait_for_prefetch=True)
    if metadata is None:
        _prime_query_builder_metadata_async(repository_name)
        return False
    return collection in metadata.collections


@lru_cache(256)
def _collection_exists_for_repository_cache(
    repository_name: str,
    instrument: str,
    collection: str,
    thread_id: int,
) -> bool:
    del thread_id
    from lsst.daf.butler._exceptions import MissingCollectionError

    butler = _get_query_repository_butler(repository_name, instrument)
    try:
        return collection in butler.registry.queryCollections(collection, flattenChains=False)
    except MissingCollectionError:
        return False


def _dataset_type_exists_for_repository(repository_name: str, dataset_type: str) -> bool:
    metadata = _get_query_repository_metadata_if_available(repository_name, wait_for_prefetch=True)
    if metadata is None:
        _prime_query_builder_metadata_async(repository_name)
        return False
    return dataset_type in metadata.dataset_types


@lru_cache(256)
def _dataset_type_exists_for_repository_cache(
    repository_name: str,
    instrument: str,
    dataset_type: str,
    thread_id: int,
) -> bool:
    del thread_id
    from lsst.daf.butler._exceptions import MissingDatasetTypeError

    butler = _get_query_repository_butler(repository_name, instrument)
    try:
        return any(cast(str, candidate.name) == dataset_type for candidate in butler.registry.queryDatasetTypes(dataset_type))
    except MissingDatasetTypeError:
        return False


def _normalize_option_search_text(text: str | None) -> str | None:
    if text is None:
        return None
    normalized = text.strip()
    return normalized or None


def _build_contains_glob(search_text: str) -> str:
    return f'*{search_text}*'
