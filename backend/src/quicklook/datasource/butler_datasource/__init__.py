import threading
import re
from collections import Counter
from dataclasses import dataclass
from datetime import date, datetime, timezone
from functools import lru_cache
from itertools import islice
from types import EllipsisType, SimpleNamespace
from typing import TYPE_CHECKING, Any, Callable, Iterable, cast
from uuid import UUID

from lsst.resources import ResourcePath
from sqlalchemy import and_, func, or_, select
from sqlalchemy.engine import Connection

import quicklook.mylogging
from quicklook.config import ButlerScopeConfig, config
from quicklook.datasets import Dataset, get_dataset
from quicklook.datasource.types import QueryBuilderOptions, QueryWhereExample, VisitDayCount, VisitDayCountQuery, VisitEntry
from quicklook.types import CcdDataRef, CcdDataType, CcdName, VisitName, build_scope_id

from ..types import DataSourceBase, DataSourceCcdMetadata, Query, ResolvedVisitInfo, VisitResolutionError
from ..visit_sort import sort_visit_entries
from .instrument import Instrument
from .retrieve_data import retrieve_data

if TYPE_CHECKING:
    from lsst.daf.butler import Butler as ButlerType
    from lsst.daf.butler import DatasetRef as ButlerDatasetRef
    from lsst.daf.butler import DimensionRecord as ButlerDimensionRecord
    from lsst.daf.butler.registry import Registry as ButlerRegistryType
    from lsst.daf.butler.registry import CollectionArgType as ButlerCollectionArgType
else:
    ButlerType = Any
    ButlerDatasetRef = Any
    ButlerDimensionRecord = Any
    ButlerRegistryType = Any
    ButlerCollectionArgType = Any


BY_UUID_DATA_TYPE = CcdDataType('by_uuid')
_QUERY_BUILDER_SUGGESTION_LIMIT = 100
_resolved_visit_runs: dict[str, str] = {}
_resolved_visit_runs_lock = threading.Lock()
logger = quicklook.mylogging.getLogger(__name__)

_SPATIAL_QUERY_WHERE_EXAMPLES = (
    QueryWhereExample(
        label='Spatial point (RA 270, Dec -30)',
        where="visit.region OVERLAPS POINT(270, -30)",
    ),
    QueryWhereExample(
        label='Trifid Nebula / NGC 6514',
        where="visit.region OVERLAPS POINT(270.921, -23.02)",
    ),
    QueryWhereExample(
        label='NGC 6357',
        where="visit.region OVERLAPS POINT(258.01, -34.75)",
    ),
    QueryWhereExample(
        label='Omega Centauri / NGC 5139',
        where="visit.region OVERLAPS POINT(201.69, -47.48)",
    ),
)

_EXPOSURE_FILTER_WHERE_EXAMPLES = (
    QueryWhereExample(
        label='Observation type: science',
        where="observation_type='science'",
    ),
    QueryWhereExample(
        label='Science program: BLOCK-407',
        where="science_program='BLOCK-407'",
    ),
    QueryWhereExample(
        label='Day Obs: 20260528 or 20260606',
        where='day_obs=20260528 or day_obs=20260606',
    ),
)

_VISIT_FILTER_WHERE_EXAMPLES = (
    QueryWhereExample(
        label='Science program: BLOCK-407',
        where="science_program='BLOCK-407'",
    ),
)

_EXPOSURE_SPATIAL_QUERY_DATASET_TYPES = frozenset({'raw', 'post_isr_image', 'calexp'})
_VISIT_SPATIAL_QUERY_DATASET_TYPES = frozenset({'difference_image', 'preliminary_visit_image'})
_UNSUPPORTED_SQL_CLAUSE = object()


@dataclass(frozen=True)
class _QueryBuilderSuggestionResult:
    values: tuple[str, ...]
    truncated: bool = False


def _query_builder_where_examples(
    repository_name: str,
    collection: str,
    dataset_type: str,
) -> list[QueryWhereExample]:
    del repository_name
    del collection
    if dataset_type in _EXPOSURE_SPATIAL_QUERY_DATASET_TYPES:
        return [*_SPATIAL_QUERY_WHERE_EXAMPLES, *_EXPOSURE_FILTER_WHERE_EXAMPLES]
    if dataset_type in _VISIT_SPATIAL_QUERY_DATASET_TYPES:
        return [*_SPATIAL_QUERY_WHERE_EXAMPLES, *_VISIT_FILTER_WHERE_EXAMPLES]
    return []


class ButlerDataSource(DataSourceBase):  # pragma: no cover
    def __init__(self):
        from .butlerutils import chown_pgpassfile

        chown_pgpassfile()

    def warm_query_builder_options_metadata_sync(self) -> None:
        logger.info("Skipping Data Query metadata warmup to avoid unbounded Butler registry scans")

    def query_visits_sync(self, q: Query) -> list[VisitEntry]:
        if not q.collection:
            return _query_visits_across_scopes(q)
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

        selected_collection = _normalize_option_search_text(collection)
        selected_dataset_type = _normalize_option_search_text(dataset_type)
        if (
            selected_collection is not None
            and selected_dataset_type is not None
            and self._collection_exists_for_repository(selected_repository, selected_collection)
            and self._dataset_type_exists_for_repository(selected_repository, selected_dataset_type)
        ):
            return QueryBuilderOptions(
                repositories=repositories,
                collections=[selected_collection],
                dataset_types=[selected_dataset_type],
                where_examples=_query_builder_where_examples(
                    selected_repository,
                    selected_collection,
                    selected_dataset_type,
                ),
            )

        collections = self._query_collections_for_repository_result(
            selected_repository,
            search_text=collection,
        )
        selected_collection = (
            collection
            if collection and self._collection_exists_for_repository(selected_repository, collection)
            else None
        )
        dataset_types = self._query_dataset_types_for_repository_result(
            selected_repository,
            search_text=dataset_type,
        )
        return QueryBuilderOptions(
            repositories=repositories,
            collections=list(collections.values),
            dataset_types=list(dataset_types.values),
            # Keep this endpoint limited to registry metadata. Probing dataset
            # contents here made exact matches for large collections unstable
            # enough to flap the deployed frontend.
            where_examples=(
                _query_builder_where_examples(selected_repository, selected_collection, selected_dataset_type)
                if selected_collection is not None and selected_dataset_type is not None
                else []
            ),
            collections_truncated=collections.truncated,
            dataset_types_truncated=dataset_types.truncated,
        )

    def _query_collections_for_repository_result(
        self,
        repository_name: str,
        *,
        search_text: str | None = None,
    ) -> _QueryBuilderSuggestionResult:
        return _query_collections_for_repository_result_with_butler(
            repository_name,
            search_text=search_text,
        )

    def _query_dataset_types_for_repository_result(
        self,
        repository_name: str,
        *,
        search_text: str | None = None,
    ) -> _QueryBuilderSuggestionResult:
        return _query_dataset_types_for_repository_result_with_butler(
            repository_name,
            search_text=search_text,
        )

    def _collection_exists_for_repository(self, repository_name: str, collection: str) -> bool:
        return _collection_exists_for_repository_with_butler(repository_name, collection)

    def _dataset_type_exists_for_repository(self, repository_name: str, dataset_type: str) -> bool:
        return _dataset_type_exists_for_repository_with_butler(repository_name, dataset_type)

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
                scope_ids.append(CcdDataType(scope.id or build_scope_id(scope.repository_name, scope.collection, scope.dataset_type)))
        return scope_ids


class PostgresButlerDataSource(ButlerDataSource):  # pragma: no cover
    def _query_collections_for_repository_result(
        self,
        repository_name: str,
        *,
        search_text: str | None = None,
    ) -> _QueryBuilderSuggestionResult:
        return _query_collections_for_repository_result(
            repository_name,
            search_text=search_text,
        )

    def _query_dataset_types_for_repository_result(
        self,
        repository_name: str,
        *,
        search_text: str | None = None,
    ) -> _QueryBuilderSuggestionResult:
        return _query_dataset_types_for_repository_result(
            repository_name,
            search_text=search_text,
        )

    def _collection_exists_for_repository(self, repository_name: str, collection: str) -> bool:
        return _collection_exists_for_repository(repository_name, collection)

    def _dataset_type_exists_for_repository(self, repository_name: str, dataset_type: str) -> bool:
        return _dataset_type_exists_for_repository(repository_name, dataset_type)


class ScopedButlerDataSource:
    def __init__(
        self,
        *,
        repository_name: str,
        collection: str,
        dataset_type: str,
        instrument: str = 'LSSTCam',
        butler: ButlerType | None = None,
    ):
        self._repository_name = repository_name
        self._collection = collection
        self._dataset_type = dataset_type
        self._instrument = instrument
        self._dataset = get_dataset(dataset_type)
        self._butler = butler or _make_scope_butler(
            repository_name=repository_name,
            collection=collection,
            instrument=instrument,
        )

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
            where=q.where if q.where is not None else self._build_latest_day_where(),
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
        selected_reverse = default_reverse if selected_field == default_field else False
        if reverse:
            selected_reverse = not selected_reverse
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
            if not self.collection or self.dataset_type == 'difference_image':
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
            if not self.collection or self.dataset_type == 'difference_image':
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
            utc_start=_record_utc_start_attr(record),
        )

    def _resolved_collection_for_record(self, record: ButlerDimensionRecord) -> str:
        if self.collection and self.dataset_type != 'difference_image':
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
        results = self._butler.registry.queryDatasets(
            self.dataset_type,
            collections=self._query_collections(visit),
            where=where,
        )
        if limit is not None:
            return list(islice(results, limit))
        return list(results)

    def _query_collections(self, visit: VisitName | None = None) -> ButlerCollectionArgType | EllipsisType:
        if visit is not None and (run := _get_resolved_visit_run(visit)) is not None:
            return [run]
        if self.collection:
            if self.dataset_type != 'difference_image':
                return [self.collection]
            return ...
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


class PostgresScopedButlerDataSource(ScopedButlerDataSource):
    def query_visits(self, q: Query) -> list[VisitEntry]:
        sql_records = _query_dimension_records_with_sql(
            registry=self._butler.registry,
            collection=self._query_collections(),
            dataset_type=self.dataset_type,
            data_id_dimension=self.data_id_dimension,
            instrument=self.instrument,
            where=q.where if q.where is not None else self._build_latest_day_where(),
            limit=q.limit,
            offset=q.offset,
            order_by=self._normalize_order_by(q.order_by, q.reverse),
        )
        if sql_records is not None:
            return [self._visit_entry_from_record(record) for record in sql_records]
        return super().query_visits(q)

    def query_visit_day_counts(self, calendar_month: str) -> list[VisitDayCount]:
        start_day_obs, end_day_obs = _calendar_month_day_obs_range(calendar_month)
        sql_counts = _query_visit_day_counts_with_sql(
            registry=self._butler.registry,
            collection=self.collection,
            dataset_type=self.dataset_type,
            data_id_dimension=self.data_id_dimension,
            instrument=self.instrument,
            start_day_obs=start_day_obs,
            end_day_obs=end_day_obs,
        )
        if sql_counts is not None:
            return sql_counts
        return super().query_visit_day_counts(calendar_month)


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


def _query_dimension_records_with_sql(
    *,
    registry: ButlerRegistryType,
    collection: ButlerCollectionArgType | EllipsisType,
    dataset_type: str,
    data_id_dimension: str,
    instrument: str,
    where: str | None,
    limit: int | None,
    offset: int,
    order_by: list[str] | None,
) -> list[ButlerDimensionRecord] | None:
    collection_names = _resolve_sql_collection_names(collection)
    if collection_names is None:
        return None

    try:
        sql_registry = _get_sql_registry(registry)
        collection_table = sql_registry._managers.collections._tables.collection
        dimension_table = sql_registry._managers.dimensions._tables[data_id_dimension]
        dataset_storage = sql_registry._managers.datasets._find_storage(dataset_type)
        tag_table = sql_registry._managers.datasets._get_tags_table(dataset_storage.dynamic_tables)
        order_columns = _resolve_sql_order_by_columns(
            dimension_table=dimension_table,
            data_id_dimension=data_id_dimension,
            order_by=order_by,
        )
        where_clause = _resolve_sql_where_clause(
            dimension_table=dimension_table,
            data_id_dimension=data_id_dimension,
            where=where,
        )
    except (AttributeError, KeyError, TypeError, ValueError) as e:
        logger.info(
            "Falling back to Butler visit query dataset_type=%s collection=%s reason=%s",
            dataset_type,
            collection_names,
            e,
        )
        return None

    if order_columns is None or where_clause is _UNSUPPORTED_SQL_CLAUSE:
        return None

    with _get_db_connection(registry) as db:
        collection_ids = tuple(
            cast(int, value)
            for value in db.execute(
                select(collection_table.c['collection_id'])
                .where(collection_table.c['name'].in_(collection_names))
            ).scalars().all()
        )
        if not collection_ids:
            return []

        tag_exists = (
            select(1)
            .select_from(tag_table)
            .where(tag_table.c['collection_id'].in_(collection_ids))
            .where(tag_table.c['instrument'] == instrument)
            .where(tag_table.c[data_id_dimension] == dimension_table.c['id'])
            .where(tag_table.c['instrument'] == dimension_table.c['instrument'])
            .exists()
        )
        sql = (
            select(dimension_table)
            .where(dimension_table.c['instrument'] == instrument)
            .where(tag_exists)
            .order_by(*order_columns)
        )
        if where_clause is not None:
            sql = sql.where(where_clause)
        if limit is not None:
            sql = sql.limit(limit)
        if offset > 0:
            sql = sql.offset(offset)
        rows = db.execute(sql).all()

    return [cast(ButlerDimensionRecord, SimpleNamespace(**row._mapping)) for row in rows]


def _query_visit_day_counts_with_sql(
    *,
    registry: ButlerRegistryType,
    collection: str,
    dataset_type: str,
    data_id_dimension: str,
    instrument: str,
    start_day_obs: int,
    end_day_obs: int,
) -> list[VisitDayCount] | None:
    if not collection:
        return None

    try:
        sql_registry = _get_sql_registry(registry)
        collection_table = sql_registry._managers.collections._tables.collection
        dimension_table = sql_registry._managers.dimensions._tables[data_id_dimension]
        dataset_storage = sql_registry._managers.datasets._find_storage(dataset_type)
        tag_table = sql_registry._managers.datasets._get_tags_table(dataset_storage.dynamic_tables)
        data_id_column = tag_table.c[data_id_dimension]
        day_obs_column = dimension_table.c['day_obs']
        dimension_id_column = dimension_table.c['id']
        dimension_instrument_column = dimension_table.c['instrument']
    except (AttributeError, KeyError, TypeError, ValueError) as e:
        logger.info(
            "Falling back to Butler day-count query dataset_type=%s collection=%s reason=%s",
            dataset_type,
            collection,
            e,
        )
        return None

    with _get_db_connection(registry) as db:
        collection_id = db.execute(
            select(collection_table.c['collection_id'])
            .where(collection_table.c['name'] == collection)
            .limit(1)
        ).scalar_one_or_none()
        if collection_id is None:
            logger.info(
                "Falling back to Butler day-count query dataset_type=%s collection=%s reason=collection-not-found",
                dataset_type,
                collection,
            )
            return None
        rows = db.execute(
            select(
                day_obs_column,
                func.count(data_id_column.distinct()).label('visit_count'),
            )
            .select_from(
                tag_table.join(
                    dimension_table,
                    and_(
                        tag_table.c['instrument'] == dimension_instrument_column,
                        data_id_column == dimension_id_column,
                    ),
                )
            )
            .where(tag_table.c['collection_id'] == collection_id)
            .where(tag_table.c['instrument'] == instrument)
            .where(day_obs_column >= start_day_obs)
            .where(day_obs_column < end_day_obs)
            .group_by(day_obs_column)
            .order_by(day_obs_column)
        ).all()

    return [
        VisitDayCount(
            day_obs=cast(int, row._mapping['day_obs']),
            count=cast(int, row._mapping['visit_count']),
        )
        for row in rows
    ]


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


def _record_utc_start_attr(record: ButlerDimensionRecord) -> datetime | None:
    timespan = getattr(record, 'timespan', None)
    if timespan is None:
        return None
    value = getattr(timespan, 'start', None)
    if value is None:
        value = getattr(timespan, 'begin', None)
    if value is None:
        return None
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)
    utc_value = getattr(value, 'utc', None)
    if utc_value is None:
        return None
    return utc_value.to_datetime(timezone=timezone.utc)


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


def _matching_scope_configs(repository_name: str, dataset_type: str) -> list[ButlerScopeConfig]:
    return [
        scope
        for scope in config.butler_scopes
        if scope.repository_name == repository_name and scope.dataset_type == dataset_type
    ]


def _query_visits_across_scopes(q: Query) -> list[VisitEntry]:
    scopes = _matching_scope_configs(q.repository_name, q.dataset_type)
    if not scopes:
        return _get_scope_datasource(
            repository_name=q.repository_name,
            collection='',
            dataset_type=q.dataset_type,
        ).query_visits(q)

    per_scope_limit = q.limit + q.offset
    entries: list[VisitEntry] = []
    seen_ids: set[str] = set()
    for scope in scopes:
        datasource = _get_scope_datasource(
            repository_name=scope.repository_name,
            collection=scope.collection,
            dataset_type=scope.dataset_type,
            instrument=scope.instrument,
        )
        for entry in datasource.query_visits(
            Query(
                repository_name=q.repository_name,
                collection=scope.collection,
                dataset_type=q.dataset_type,
                limit=per_scope_limit,
                offset=0,
                where=q.where,
                order_by=q.order_by,
                reverse=q.reverse,
            )
        ):
            if entry.id in seen_ids:
                continue
            seen_ids.add(entry.id)
            entries.append(entry)

    sorted_entries = sort_visit_entries(entries, dataset_type=q.dataset_type, order_by=q.order_by, reverse=q.reverse)
    return sorted_entries[q.offset : q.offset + q.limit]


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
    return _make_scoped_butler_datasource(
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


def make_butler_datasource() -> ButlerDataSource:
    if _default_query_registry_is_postgres():
        return PostgresButlerDataSource()
    return ButlerDataSource()


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


def _query_collections_for_repository_result_with_butler(
    repository_name: str,
    *,
    search_text: str | None = None,
) -> _QueryBuilderSuggestionResult:
    instrument = _repository_instrument(repository_name)
    thread_id = threading.get_ident()
    return _run_query_builder_fallback(
        repository_name=repository_name,
        action='collection suggestions',
        default=_QueryBuilderSuggestionResult(()),
        func=lambda: _query_collections_for_repository_cache_with_butler(
            repository_name,
            instrument,
            _normalize_option_search_text(search_text),
            thread_id=thread_id,
        ),
    )


@lru_cache(128)
def _query_collections_for_repository_cache_with_butler(
    repository_name: str,
    instrument: str,
    search_text: str | None,
    thread_id: int,
) -> _QueryBuilderSuggestionResult:
    del thread_id
    butler = _get_query_repository_butler(repository_name, instrument)
    collections = sorted(cast(str, value) for value in butler.registry.queryCollections(...))
    return _limit_query_builder_suggestions(
        tuple(
            collection
            for collection in collections
            if _query_builder_search_matches(collection, search_text)
        )
    )


def _query_dataset_types_for_repository_result_with_butler(
    repository_name: str,
    *,
    search_text: str | None = None,
) -> _QueryBuilderSuggestionResult:
    instrument = _repository_instrument(repository_name)
    thread_id = threading.get_ident()
    return _run_query_builder_fallback(
        repository_name=repository_name,
        action='dataset type suggestions',
        default=_QueryBuilderSuggestionResult(()),
        func=lambda: _query_dataset_types_for_repository_cache_with_butler(
            repository_name,
            instrument,
            _normalize_option_search_text(search_text),
            thread_id=thread_id,
        ),
    )


@lru_cache(128)
def _query_dataset_types_for_repository_cache_with_butler(
    repository_name: str,
    instrument: str,
    search_text: str | None,
    thread_id: int,
) -> _QueryBuilderSuggestionResult:
    del thread_id
    butler = _get_query_repository_butler(repository_name, instrument)
    names = sorted(
        cast(str, candidate.name)
        for candidate in butler.registry.queryDatasetTypes(...)
    )
    return _limit_query_builder_suggestions(
        tuple(
            dataset_type
            for dataset_type in names
            if _query_builder_search_matches(dataset_type, search_text)
            and _dataset_type_supports_query_builder(butler, dataset_type)
        )
    )


def _collection_exists_for_repository_with_butler(repository_name: str, collection: str) -> bool:
    instrument = _repository_instrument(repository_name)
    thread_id = threading.get_ident()
    return _run_query_builder_fallback(
        repository_name=repository_name,
        action='collection existence check',
        default=False,
        func=lambda: _collection_exists_for_repository_cache_with_butler(
            repository_name,
            instrument,
            collection,
            thread_id=thread_id,
        ),
    )


@lru_cache(256)
def _collection_exists_for_repository_cache_with_butler(
    repository_name: str,
    instrument: str,
    collection: str,
    thread_id: int,
) -> bool:
    del thread_id
    butler = _get_query_repository_butler(repository_name, instrument)
    return any(candidate == collection for candidate in butler.registry.queryCollections(...))


def _dataset_type_exists_for_repository_with_butler(repository_name: str, dataset_type: str) -> bool:
    instrument = _repository_instrument(repository_name)
    thread_id = threading.get_ident()
    return _run_query_builder_fallback(
        repository_name=repository_name,
        action='dataset type existence check',
        default=False,
        func=lambda: _dataset_type_exists_for_repository_cache_with_butler(
            repository_name,
            instrument,
            dataset_type,
            thread_id=thread_id,
        ),
    )


@lru_cache(256)
def _dataset_type_exists_for_repository_cache_with_butler(
    repository_name: str,
    instrument: str,
    dataset_type: str,
    thread_id: int,
) -> bool:
    del thread_id
    butler = _get_query_repository_butler(repository_name, instrument)
    return _dataset_type_supports_query_builder(butler, dataset_type)


def _query_collections_for_repository(repository_name: str, *, search_text: str | None = None) -> list[str]:
    return list(_query_collections_for_repository_result(repository_name, search_text=search_text).values)


def _query_collections_for_repository_result(
    repository_name: str,
    *,
    search_text: str | None = None,
) -> _QueryBuilderSuggestionResult:
    instrument = _repository_instrument(repository_name)
    thread_id = threading.get_ident()
    return _run_query_builder_fallback(
        repository_name=repository_name,
        action='collection suggestions',
        default=_QueryBuilderSuggestionResult(()),
        func=lambda: _query_collections_for_repository_cache(
            repository_name,
            instrument,
            _normalize_option_search_text(search_text),
            thread_id=thread_id,
        ),
    )


@lru_cache(128)
def _query_collections_for_repository_cache(
    repository_name: str,
    instrument: str,
    search_text: str | None,
    thread_id: int,
) -> _QueryBuilderSuggestionResult:
    del thread_id
    butler = _get_query_repository_butler(repository_name, instrument)
    return _query_collection_suggestions(butler, search_text)


def _query_collection_suggestions(
    butler: ButlerType,
    search_text: str | None,
) -> _QueryBuilderSuggestionResult:
    sql_registry = _get_sql_registry(butler.registry)
    collection_table = sql_registry._managers.collections._tables.collection
    sql = select(collection_table.c['name']).order_by(collection_table.c['name']).limit(_QUERY_BUILDER_SUGGESTION_LIMIT + 1)
    if search_text is not None:
        sql = sql.where(collection_table.c['name'].contains(search_text, autoescape=True))
    with _get_db_connection(butler.registry) as db:
        values = tuple(cast(str, value) for value in db.execute(sql).scalars().all())
    return _limit_query_builder_suggestions(values)


def query_collections(butler: ButlerType, search_pattern: str) -> Iterable[str]:
    return _query_collection_suggestions(butler, search_pattern).values


def _query_dataset_types_for_repository_result(
    repository_name: str,
    *,
    search_text: str | None = None,
) -> _QueryBuilderSuggestionResult:
    instrument = _repository_instrument(repository_name)
    thread_id = threading.get_ident()
    return _run_query_builder_fallback(
        repository_name=repository_name,
        action='dataset type suggestions',
        default=_QueryBuilderSuggestionResult(()),
        func=lambda: _query_dataset_types_for_repository_cache(
            repository_name,
            instrument,
            _normalize_option_search_text(search_text),
            thread_id=thread_id,
        ),
    )


@lru_cache(128)
def _query_dataset_types_for_repository_cache(
    repository_name: str,
    instrument: str,
    search_text: str | None,
    thread_id: int,
) -> _QueryBuilderSuggestionResult:
    del thread_id
    butler = _get_query_repository_butler(repository_name, instrument)
    return _query_dataset_type_suggestions_for_repository(
        butler,
        search_text=search_text,
    )


def _query_dataset_type_suggestions_for_repository(
    butler: ButlerType,
    *,
    search_text: str | None,
) -> _QueryBuilderSuggestionResult:
    sql_registry = _get_sql_registry(butler.registry)
    dataset_manager = sql_registry._managers.datasets
    dataset_type_table = dataset_manager._static.dataset_type
    sql = select(dataset_type_table.c['name']).order_by(dataset_type_table.c['name']).distinct()
    if search_text is not None:
        sql = sql.where(dataset_type_table.c['name'].contains(search_text, autoescape=True))
    return _filter_query_builder_dataset_types(
        butler=butler,
        dataset_type_sql=sql,
    )


def query_datasets_for_collection(
    butler: ButlerType,
    collection: str,
    search_pattern: str,
) -> Iterable[str]:
    del collection
    return _query_dataset_type_suggestions_for_repository(
        butler,
        search_text=search_pattern,
    ).values


def _filter_query_builder_dataset_types(
    *,
    butler: ButlerType,
    dataset_type_sql: Any,
) -> _QueryBuilderSuggestionResult:
    dataset_types: list[str] = []
    seen: set[str] = set()
    batch_size = _QUERY_BUILDER_SUGGESTION_LIMIT + 1
    offset = 0
    with _get_db_connection(butler.registry) as db:
        while len(dataset_types) <= _QUERY_BUILDER_SUGGESTION_LIMIT:
            names = tuple(cast(str, value) for value in db.execute(dataset_type_sql.limit(batch_size).offset(offset)).scalars().all())
            if not names:
                break
            offset += len(names)
            for dataset_type_name in names:
                if dataset_type_name in seen:
                    continue
                seen.add(dataset_type_name)
                if not _dataset_type_supports_query_builder(butler, dataset_type_name):
                    continue
                dataset_types.append(dataset_type_name)
                if len(dataset_types) > _QUERY_BUILDER_SUGGESTION_LIMIT:
                    return _limit_query_builder_suggestions(tuple(dataset_types))
            if len(names) < batch_size:
                break
    return _limit_query_builder_suggestions(tuple(dataset_types))


def _limit_query_builder_suggestions(matches: tuple[str, ...]) -> _QueryBuilderSuggestionResult:
    return _QueryBuilderSuggestionResult(
        values=matches[:_QUERY_BUILDER_SUGGESTION_LIMIT],
        truncated=len(matches) > _QUERY_BUILDER_SUGGESTION_LIMIT,
    )


def _query_builder_search_matches(value: str, search_text: str | None) -> bool:
    if search_text is None:
        return True
    return search_text.casefold() in value.casefold()


def _get_sql_registry(registry: ButlerRegistryType) -> Any:
    sql_registry = getattr(registry, '_registry', registry)
    if not hasattr(sql_registry, '_db') or not hasattr(sql_registry, '_managers'):
        raise TypeError(f'Query builder registry does not expose SQL internals: {type(registry)!r}')
    return sql_registry


def _get_db_connection(registry: ButlerRegistryType) -> Connection:
    return _get_sql_registry(registry)._db._engine.connect()


def _default_query_registry_is_postgres() -> bool:
    for scope in config.butler_scopes:
        return _is_repository_query_backend_postgres(scope.repository_name, scope.instrument)
    return False


@lru_cache(32)
def _is_repository_query_backend_postgres(
    repository_name: str,
    instrument: str,
) -> bool:
    return _is_postgres_registry(_get_query_repository_butler(repository_name, instrument).registry)


def _is_postgres_registry(registry: ButlerRegistryType) -> bool:
    try:
        return _get_sql_registry(registry)._db._engine.dialect.name == 'postgresql'
    except Exception:
        return False


def _make_scope_butler(
    *,
    repository_name: str,
    collection: str,
    instrument: str,
) -> ButlerType:
    from lsst.daf.butler import Butler

    butler_kwargs: dict[str, Any] = {
        'instrument': instrument,
    }
    if collection:
        butler_kwargs['collections'] = [collection]
    return Butler(
        repository_name,
        **butler_kwargs,
    )  # type: ignore


def _make_scoped_butler_datasource(
    *,
    repository_name: str,
    collection: str,
    dataset_type: str,
    instrument: str,
) -> ScopedButlerDataSource:
    butler = _make_scope_butler(
        repository_name=repository_name,
        collection=collection,
        instrument=instrument,
    )
    datasource_class = PostgresScopedButlerDataSource if _is_postgres_registry(butler.registry) else ScopedButlerDataSource
    return datasource_class(
        repository_name=repository_name,
        collection=collection,
        dataset_type=dataset_type,
        instrument=instrument,
        butler=butler,
    )


def _collection_exists_for_repository(repository_name: str, collection: str) -> bool:
    instrument = _repository_instrument(repository_name)
    thread_id = threading.get_ident()
    return _run_query_builder_fallback(
        repository_name=repository_name,
        action='collection existence check',
        default=False,
        func=lambda: _collection_exists_for_repository_cache(
            repository_name,
            instrument,
            collection,
            thread_id=thread_id,
        ),
    )


@lru_cache(256)
def _collection_exists_for_repository_cache(
    repository_name: str,
    instrument: str,
    collection: str,
    thread_id: int,
) -> bool:
    del thread_id
    butler = _get_query_repository_butler(repository_name, instrument)
    sql_registry = _get_sql_registry(butler.registry)
    collection_table = sql_registry._managers.collections._tables.collection
    sql = select(collection_table.c['name']).where(collection_table.c['name'] == collection).limit(1)
    with _get_db_connection(butler.registry) as db:
        return db.execute(sql).scalar_one_or_none() is not None


def _dataset_type_exists_for_repository(repository_name: str, dataset_type: str) -> bool:
    instrument = _repository_instrument(repository_name)
    thread_id = threading.get_ident()
    return _run_query_builder_fallback(
        repository_name=repository_name,
        action='dataset type existence check',
        default=False,
        func=lambda: _dataset_type_exists_for_repository_cache(
            repository_name,
            instrument,
            dataset_type,
            thread_id=thread_id,
        ),
    )


@lru_cache(256)
def _dataset_type_exists_for_repository_cache(
    repository_name: str,
    instrument: str,
    dataset_type: str,
    thread_id: int,
) -> bool:
    del thread_id
    butler = _get_query_repository_butler(repository_name, instrument)
    if not _is_query_builder_dataset_type(repository_name, instrument, dataset_type):
        return False
    sql_registry = _get_sql_registry(butler.registry)
    dataset_manager = sql_registry._managers.datasets
    dataset_type_table = dataset_manager._static.dataset_type
    sql = select(dataset_type_table.c['name']).where(dataset_type_table.c['name'] == dataset_type).limit(1)
    with _get_db_connection(butler.registry) as db:
        return db.execute(sql).scalar_one_or_none() is not None


def _is_query_builder_dataset_type(repository_name: str, instrument: str, dataset_type: str) -> bool:
    thread_id = threading.get_ident()
    return _run_query_builder_fallback(
        repository_name=repository_name,
        action='dataset type compatibility check',
        default=False,
        func=lambda: _is_query_builder_dataset_type_cache(
            repository_name,
            instrument,
            dataset_type,
            thread_id=thread_id,
        ),
    )


@lru_cache(256)
def _is_query_builder_dataset_type_cache(
    repository_name: str,
    instrument: str,
    dataset_type: str,
    thread_id: int,
) -> bool:
    del thread_id
    butler = _get_query_repository_butler(repository_name, instrument)
    return _dataset_type_supports_query_builder(butler, dataset_type)


def _dataset_type_supports_query_builder(butler: ButlerType, dataset_type: str) -> bool:
    from lsst.daf.butler._exceptions import MissingDatasetTypeError

    try:
        candidate = butler.registry.getDatasetType(dataset_type)
    except MissingDatasetTypeError:
        return False
    try:
        get_dataset(dataset_type).quicklook_dimensions(_dataset_required_dimension_names(candidate))
    except ValueError:
        return False
    return True


def _normalize_option_search_text(text: str | None) -> str | None:
    if text is None:
        return None
    normalized = text.strip()
    return normalized or None


def _resolve_sql_collection_names(collection: ButlerCollectionArgType | EllipsisType) -> list[str] | None:
    if collection is ...:
        return None
    if isinstance(collection, str):
        return [collection]
    try:
        return [cast(str, value) for value in collection]
    except TypeError:
        return None


def _resolve_sql_order_by_columns(
    *,
    dimension_table: Any,
    data_id_dimension: str,
    order_by: list[str] | None,
) -> list[Any] | None:
    if order_by is None:
        return None
    columns: list[Any] = []
    for item in order_by:
        descending = item.startswith('-')
        column = _resolve_sql_dimension_column(
            dimension_table=dimension_table,
            data_id_dimension=data_id_dimension,
            field=item.removeprefix('-'),
        )
        if column is None:
            return None
        columns.append(column.desc() if descending else column.asc())
    return columns


def _resolve_sql_where_clause(
    *,
    dimension_table: Any,
    data_id_dimension: str,
    where: str | None,
) -> Any:
    if where in (None, ''):
        return None
    disjunctions: list[Any] = []
    for or_part in where.split(' or '):
        conjunctions: list[Any] = []
        for and_part in or_part.split(' and '):
            predicate = _resolve_sql_predicate(
                dimension_table=dimension_table,
                data_id_dimension=data_id_dimension,
                predicate=and_part.strip(),
            )
            if predicate is _UNSUPPORTED_SQL_CLAUSE:
                return _UNSUPPORTED_SQL_CLAUSE
            conjunctions.append(predicate)
        disjunctions.append(and_(*conjunctions))
    if len(disjunctions) == 1:
        return disjunctions[0]
    return or_(*disjunctions)


def _resolve_sql_predicate(
    *,
    dimension_table: Any,
    data_id_dimension: str,
    predicate: str,
) -> Any:
    for operator_text in ('>=', '<', '='):
        if operator_text not in predicate:
            continue
        field_text, value_text = predicate.split(operator_text, maxsplit=1)
        column = _resolve_sql_dimension_column(
            dimension_table=dimension_table,
            data_id_dimension=data_id_dimension,
            field=field_text.strip(),
        )
        if column is None:
            return _UNSUPPORTED_SQL_CLAUSE
        value = _resolve_sql_literal(column, value_text.strip())
        if value is _UNSUPPORTED_SQL_CLAUSE:
            return _UNSUPPORTED_SQL_CLAUSE
        return {
            '>=': column >= value,
            '<': column < value,
            '=': column == value,
        }[operator_text]
    return _UNSUPPORTED_SQL_CLAUSE


def _resolve_sql_dimension_column(
    *,
    dimension_table: Any,
    data_id_dimension: str,
    field: str,
) -> Any | None:
    if field == data_id_dimension:
        return dimension_table.c['id']
    if field in dimension_table.c:
        return dimension_table.c[field]
    if field == 'physical_filter' and 'band' in dimension_table.c:
        return dimension_table.c['band']
    return None


def _resolve_sql_literal(column: Any, value_text: str) -> Any:
    if re.fullmatch(r"'([^'\\]|\\.)*'", value_text):
        return value_text[1:-1].replace("\\'", "'")

    python_type = getattr(column.type, 'python_type', None)
    if python_type is int and re.fullmatch(r'-?\d+', value_text):
        return int(value_text)
    if python_type is float and re.fullmatch(r'-?\d+(?:\.\d+)?', value_text):
        return float(value_text)
    if python_type is bool and value_text in {'true', 'false'}:
        return value_text == 'true'
    if python_type is str and re.fullmatch(r'[A-Za-z0-9_.:-]+', value_text):
        return value_text
    return _UNSUPPORTED_SQL_CLAUSE


def _run_query_builder_fallback(
    *,
    repository_name: str,
    action: str,
    default: Any,
    func: Callable[[], Any],
) -> Any:
    try:
        return func()
    except Exception:
        logger.exception(
            "Falling back to default after Data Query %s failed for repository=%s",
            action,
            repository_name,
        )
        return default
