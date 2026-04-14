from calendar import monthrange
from collections import Counter
import threading
from functools import lru_cache
from itertools import islice
from types import EllipsisType
from typing import TYPE_CHECKING, Any, cast
from uuid import UUID

from lsst.resources import ResourcePath

from quicklook.config import CcdDataTypeConfig, config
from quicklook.datasource.types import (
    ButlerDatasetTypeDimensions,
    ButlerDatasetTypeInfo,
    ButlerQuery,
    ButlerQueryResult,
    ButlerQueryRow,
    MonthlyEntryCountQuery,
    VisitDayCount,
    VisitEntry,
)
from quicklook.types import CcdDataRef, CcdDataType, CcdName, VisitName
from quicklook.utils.async_wrap import async_wrap

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


DataRef = Any

BY_UUID_DATA_TYPE = CcdDataType('by_uuid')
QUERY_FILTER_ALIASES = {'filter': 'physical_filter'}
_resolved_visit_runs: dict[str, str] = {}
_resolved_visit_runs_lock = threading.Lock()


class ButlerDataSource(DataSourceBase):  # pragma: no cover
    def __init__(self):
        from .butlerutils import chown_pgpassfile

        chown_pgpassfile()

    def query_visits_sync(self, q: Query) -> list[VisitEntry]:
        return _get_datasource(q.data_type, q.repository_name).query_visits(q)

    def resolve_visit_sync(self, visit: VisitName) -> VisitName:
        return self.resolve_visit_info_sync(visit).visit_name

    def resolve_visit_info_sync(self, visit: VisitName) -> ResolvedVisitInfo:
        return _resolve_visit_info(visit)

    def list_ccds_sync(self, visit: VisitName) -> list[CcdName]:
        visit = self.resolve_visit_sync(visit)
        return _get_datasource(visit.data_type, visit.repository_name).list_ccds(visit)

    def get_data_sync(self, ref: CcdDataRef) -> bytes:
        ref = _resolve_ref(ref, self.resolve_visit_sync(ref.visit))
        return _get_datasource(ref.visit.data_type, ref.visit.repository_name).get_data(ref)

    def get_metadata_sync(self, ref: CcdDataRef) -> DataSourceCcdMetadata:
        ref = _resolve_ref(ref, self.resolve_visit_sync(ref.visit))
        return _get_datasource(ref.visit.data_type, ref.visit.repository_name).get_metadata(ref)

    def get_exposure_data_types_sync(self, exposure_id: int) -> list[CcdDataType]:
        types: list[CcdDataType] = []
        for data_type_config in config.ccd_data_types:
            datasource = _get_datasource(data_type_config.data_type, data_type_config.repository_name)
            if datasource.exposure_exists(exposure_id):
                types.append(CcdDataType(f"{data_type_config.repository_name}:{data_type_config.data_type}"))
        return types

    def query_monthly_entry_counts_sync(self, q: MonthlyEntryCountQuery) -> list[VisitDayCount]:
        return _get_datasource(q.data_type, q.repository_name).query_monthly_entry_counts(q)

    def query_butler_sync(self, q: ButlerQuery) -> ButlerQueryResult:
        config_entry = _resolve_data_type_config(q.data_type, q.repository_name)
        return _get_datasource(config_entry.data_type, config_entry.repository_name).query_butler(
            ButlerQuery(
                data_type=q.data_type,
                repository_name=config_entry.repository_name,
                limit=q.limit,
                offset=q.offset,
                collections=q.collections,
                order=q.order,
                filters=q.filters,
            )
        )

    query_butler = async_wrap(query_butler_sync)

    def list_butler_dataset_types_sync(self, repository_name: str | None = None) -> list[ButlerDatasetTypeInfo]:
        configs = config.ccd_data_types
        if repository_name is not None:
            configs = [item for item in configs if item.repository_name == repository_name]
        return [_dataset_type_info_from_config(item) for item in configs]

    list_butler_dataset_types = async_wrap(list_butler_dataset_types_sync)

    def get_butler_dataset_type_dimensions_sync(
        self,
        data_type: CcdDataType,
        repository_name: str | None = None,
    ) -> ButlerDatasetTypeDimensions:
        config_entry = _resolve_data_type_config(data_type, repository_name)
        return _get_datasource(config_entry.data_type, config_entry.repository_name).get_butler_dataset_type_dimensions()

    get_butler_dataset_type_dimensions = async_wrap(get_butler_dataset_type_dimensions_sync)


class DataTypeSpecificDataSource:
    """設定から動的に生成されるデータタイプ固有のデータソース"""

    def __init__(self, data_type_config: CcdDataTypeConfig):
        from lsst.daf.butler import Butler

        self._config = data_type_config
        self._butler: ButlerType = Butler(
            data_type_config.repository_name,
            instrument=data_type_config.instrument,
            collections=data_type_config.collections,
        )  # type: ignore

    @property
    def butler_data_type(self) -> str:
        """Butler dataset type name for queries"""
        return self._config.data_type

    @property
    def repository_name(self) -> str:
        return self._config.repository_name

    @property
    def data_id_dimension(self) -> str:
        return self._config.data_id_dimension

    @property
    def order_by(self) -> list[str]:
        return self._config.order_by

    @property
    def partial(self) -> bool:
        return self._config.partial

    @property
    def instrument(self) -> str:
        return self._config.instrument

    def query_visits(self, q: Query) -> list[VisitEntry]:
        '''
        もしday_obsが指定されていない場合は、day_obsを最新の1日分に指定して実行する
        '''

        if q.day_obs is None:
            q.day_obs = self._get_latest_day_obs()

        conds: list[str] = []
        if q.exposure is not None:
            conds.append(f"{self.data_id_dimension}={q.exposure}")
        if q.day_obs is not None:
            conds.append(f"day_obs={q.day_obs}")
        where = " and ".join(conds)

        records = self._query_dimension_records(
            self.data_id_dimension,
            datasets=self.butler_data_type,
            where=where,
            limit=q.limit,
            order_by=self.order_by,
        )
        return [self._visit_entry_from_record(record) for record in records]

    def query_monthly_entry_counts(self, q: MonthlyEntryCountQuery) -> list[VisitDayCount]:
        month_start = q.year * 10000 + q.month * 100 + 1
        month_end = q.year * 10000 + q.month * 100 + monthrange(q.year, q.month)[1]
        records = self._query_dimension_records(
            self.data_id_dimension,
            datasets=self.butler_data_type,
            where=f"day_obs>={month_start} and day_obs<={month_end}",
        )
        counts = Counter(cast(int, getattr(record, 'day_obs')) for record in records)
        return [VisitDayCount(day_obs=day_obs, count=counts[day_obs]) for day_obs in sorted(counts)]

    def query_butler(self, q: ButlerQuery) -> ButlerQueryResult:
        order = q.order or self.order_by
        filters = { _normalize_query_filter_key(key): value for key, value in q.filters.items() }
        fetch_limit = q.offset + q.limit + 1
        records = self._query_dimension_records(
            self.data_id_dimension,
            datasets=self.butler_data_type,
            collections=q.collections if q.collections is not None else self._query_collections(),
            where=_build_where(filters),
            limit=fetch_limit,
            order_by=order,
        )
        has_more = len(records) > (q.offset + q.limit)
        page_records = records[q.offset:q.offset + q.limit]
        rows = [
            ButlerQueryRow(
                visit_name=VisitName(f'{self.repository_name}:{self.butler_data_type}:{record.id}'),
                record=_serialize_dimension_record(record, self.data_id_dimension),
            )
            for record in page_records
        ]
        return ButlerQueryResult(
            repository_name=self.repository_name,
            data_type=CcdDataType(self.butler_data_type),
            data_id_dimension=self.data_id_dimension,
            applied_collections=_serialize_collections(q.collections if q.collections is not None else self._query_collections()),
            applied_filters=filters,
            order=order,
            limit=q.limit,
            offset=q.offset,
            returned_count=len(rows),
            has_more=has_more,
            columns=_collect_query_columns(rows, self.data_id_dimension),
            rows=rows,
        )

    def get_butler_dataset_type_dimensions(self) -> ButlerDatasetTypeDimensions:
        dataset_type = self._butler.registry.getDatasetType(self.butler_data_type)
        dimensions = sorted(cast(list[str], list(dataset_type.dimensions.names)))
        return ButlerDatasetTypeDimensions(
            repository_name=self.repository_name,
            data_type=CcdDataType(self.butler_data_type),
            data_id_dimension=self.data_id_dimension,
            dimensions=dimensions,
            filter_aliases=QUERY_FILTER_ALIASES,
        )

    def list_ccds(self, visit: VisitName) -> list[CcdName]:
        refs = self._query_datasets(f"{self.data_id_dimension}={visit.name}", visit=visit)
        i = Instrument.get(self.instrument)
        ccd_names = list(dict.fromkeys(CcdName(i.detector_2_ccd[ref.dataId['detector']]) for ref in refs))  # type: ignore
        if self.butler_data_type in {'post_isr_image', 'difference_image'}:
            # ４隅のraftは位置情報がrawと違うため除外する
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
        return retrieve_data(self._getUri(ref), partial=self.partial)

    def _getUri(self, ref: CcdDataRef) -> ResourcePath:
        b = self._butler
        detector_id = Instrument.get(self.instrument).ccd_2_detector[ref.ccd]
        butler_ref = self._refs_by_visit(ref.visit)[detector_id]
        return b.getURI(butler_ref)  # type: ignore

    def _refs_by_visit(self, visit: VisitName) -> dict[int, ButlerDatasetRef]:
        refs = self._query_datasets(f"{self.data_id_dimension}={visit.name}", visit=visit)
        refs_by_detector: dict[int, ButlerDatasetRef] = {}
        for ref in refs:
            detector = cast(int, ref.dataId['detector'])
            if detector in refs_by_detector:
                raise ValueError(
                    f'Cannot find unique dataset for {visit.name} and detector {detector}. found multiple matches'
                )
            refs_by_detector[detector] = ref
        return refs_by_detector

    def get_metadata(self, ref: CcdDataRef) -> DataSourceCcdMetadata:
        detector_id = Instrument.get(self.instrument).ccd_2_detector[ref.ccd]
        butler_refs = self._query_datasets(
            f"{self.data_id_dimension}={ref.visit.name} and detector={detector_id}",
            visit=ref.visit,
        )
        if len(butler_refs) != 1:
            raise ValueError(
                f"Cannot find unique dataset for {ref.visit.name} and detector {detector_id}. found {len(butler_refs)} matches"
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

    def _get_latest_day_obs(self) -> int | None:
        records = self._query_dimension_records(
            self.data_id_dimension,
            datasets=self.butler_data_type,
            limit=1,
            order_by=["-day_obs"],
        )
        if len(records) == 0:
            return None
        return cast(int, records[0].day_obs)

    def _query_dimension_records(
        self,
        dimension: str,
        *,
        datasets: str | None = None,
        collections: ButlerCollectionArgType | EllipsisType | None = None,
        where: str | None = None,
        limit: int | None = None,
        order_by: list[str] | None = None,
    ) -> list[ButlerDimensionRecord]:
        kwargs: dict[str, Any] = {}
        if datasets is not None:
            kwargs['datasets'] = datasets
            if collections is not None:
                kwargs['collections'] = collections
            elif self.butler_data_type == 'difference_image':
                kwargs['collections'] = self._query_collections()
        if where:
            kwargs['where'] = where
        records = self._butler.registry.queryDimensionRecords(dimension, **kwargs)
        if order_by is not None:
            records = records.order_by(*order_by)
        if limit is not None:
            records = records.limit(limit)
        return list(records)

    def _visit_entry_from_record(self, record: ButlerDimensionRecord) -> VisitEntry:
        return VisitEntry(
            id=f'{self.repository_name}:{self.butler_data_type}:{record.id}',
            obs_id=_record_string_attr(record, 'obs_id', default=str(record.id)),
            day_obs=cast(int, getattr(record, 'day_obs')),
            physical_filter=_record_string_attr(record, 'physical_filter', 'band'),
            exposure_time=_record_float_attr(record, 'exposure_time'),
            science_program=_record_string_attr(record, 'science_program'),
            observation_type=_record_string_attr(record, 'observation_type'),
            observation_reason=_record_string_attr(record, 'observation_reason'),
            target_name=_record_string_attr(record, 'target_name'),
        )

    def _get_exposure_info(self, day_obs: int) -> dict[int, ButlerDimensionRecord]:
        records = self._butler.registry.queryDimensionRecords('exposure', where=f"day_obs={day_obs}")
        return {record.id: record for record in records}

    def _query_datasets(
        self,
        where: str,
        *,
        visit: VisitName | None = None,
        limit: int | None = None,
    ) -> list[ButlerDatasetRef]:
        if self.butler_data_type != 'difference_image':
            refs = self._butler.query_datasets(self.butler_data_type, where=where, limit=limit)
            return list(refs)

        results = self._butler.registry.queryDatasets(
            self.butler_data_type,
            collections=self._query_collections(visit),
            where=where,
        )
        if limit is not None:
            return list(islice(results, limit))
        return list(results)

    def _query_collections(self, visit: VisitName | None = None) -> ButlerCollectionArgType | EllipsisType:
        if self.butler_data_type != 'difference_image':
            return self._config.collections
        if visit is not None and (run := _get_resolved_visit_run(visit)) is not None:
            return [run]
        return ...


def _resolve_ref(ref: CcdDataRef, visit: VisitName) -> CcdDataRef:
    if visit == ref.visit:
        return ref
    return CcdDataRef(visit=visit, ccd=ref.ccd)


def _resolve_visit(visit: VisitName) -> VisitName:
    return _resolve_visit_info(visit).visit_name


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
    try:
        datasource = _get_datasource(dataset_type, visit.repository_name)
    except ValueError as e:
        raise VisitResolutionError(
            f'UUID {visit.name} resolves to unsupported dataset type {dataset_type} in repository {visit.repository_name}'
        ) from e
    data_id = dataset_ref.dataId.get(datasource.data_id_dimension)
    if data_id is None:
        raise VisitResolutionError(
            f'UUID {visit.name} resolved to dataset type {dataset_type}, but dataId does not contain {datasource.data_id_dimension}'
        )
    resolved_visit = VisitName(f'{visit.repository_name}:{dataset_type}:{data_id}')
    _remember_resolved_visit_run(resolved_visit, cast(str, dataset_ref.run))
    detector = dataset_ref.dataId.get('detector')
    return ResolvedVisitInfo(
        visit_name=resolved_visit,
        detector=None if detector is None else int(detector),
    )


def _remember_resolved_visit_run(visit: VisitName, run: str) -> None:
    with _resolved_visit_runs_lock:
        if len(_resolved_visit_runs) >= 256 and str(visit) not in _resolved_visit_runs:
            _resolved_visit_runs.pop(next(iter(_resolved_visit_runs)))
        _resolved_visit_runs[str(visit)] = run


def _get_resolved_visit_run(visit: VisitName) -> str | None:
    with _resolved_visit_runs_lock:
        return _resolved_visit_runs.get(str(visit))


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


def _serialize_dimension_record(record: ButlerDimensionRecord, primary_dimension: str) -> dict[str, object]:
    if hasattr(record, 'toDict'):
        raw = cast(dict[str, object], record.toDict(splitTimespan=True))
    else:
        raw = cast(dict[str, object], vars(record))
    primary_value = cast(object, getattr(record, 'id', raw.get(primary_dimension)))
    raw.setdefault('id', primary_value)
    raw.setdefault(primary_dimension, primary_value)
    return {key: _jsonify_value(value) for key, value in raw.items()}


def _jsonify_value(value: object) -> object:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, dict):
        return {str(key): _jsonify_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_jsonify_value(item) for item in value]
    return str(value)


def _build_where(filters: dict[str, str]) -> str | None:
    if not filters:
        return None
    return ' and '.join(f'{key}={_format_butler_literal(value)}' for key, value in filters.items())


def _format_butler_literal(value: str) -> str:
    if value == '':
        return "''"
    lowered = value.lower()
    if lowered in {'true', 'false'}:
        return lowered
    try:
        int(value)
    except ValueError:
        try:
            float(value)
        except ValueError:
            return "'" + value.replace("\\", "\\\\").replace("'", "\\'") + "'"
        else:
            return value
    else:
        return value


def _normalize_query_filter_key(key: str) -> str:
    return QUERY_FILTER_ALIASES.get(key, key)


def _collect_query_columns(rows: list[ButlerQueryRow], primary_dimension: str) -> list[str]:
    preferred = [
        primary_dimension,
        'id',
        'day_obs',
        'obs_id',
        'physical_filter',
        'band',
        'science_program',
        'observation_type',
        'observation_reason',
        'target_name',
    ]
    seen: set[str] = set()
    columns: list[str] = []
    for column in preferred:
        if any(column in row.record for row in rows):
            columns.append(column)
            seen.add(column)
    for column in sorted({key for row in rows for key in row.record if key not in seen}):
        columns.append(column)
    return columns


def _serialize_collections(collections: ButlerCollectionArgType | EllipsisType | None) -> list[str] | None:
    if collections is None or collections is ...:
        return None
    if isinstance(collections, str):
        return [collections]
    return [str(item) for item in collections]


def _dataset_type_info_from_config(data_type_config: CcdDataTypeConfig) -> ButlerDatasetTypeInfo:
    return ButlerDatasetTypeInfo(
        repository_name=data_type_config.repository_name,
        data_type=CcdDataType(data_type_config.data_type),
        display_name=data_type_config.display_name,
        data_id_dimension=data_type_config.data_id_dimension,
        default_collections=data_type_config.collections,
        default_order=data_type_config.order_by,
    )


def _resolve_data_type_config(data_type: str, repository_name: str | None = None) -> CcdDataTypeConfig:
    matches = [
        data_type_config
        for data_type_config in config.ccd_data_types
        if data_type_config.data_type == data_type
        and (repository_name is None or data_type_config.repository_name == repository_name)
    ]
    if len(matches) == 1:
        return matches[0]
    if len(matches) == 0:
        available = [(item.repository_name, item.data_type) for item in config.ccd_data_types]
        raise ValueError(
            f'Unknown data type: ({repository_name}, {data_type}). Available: {available}'
        )
    repositories = sorted({item.repository_name for item in matches})
    raise ValueError(
        f'Data type {data_type} is configured for multiple repositories. Specify repository_name. '
        f'Available repositories: {repositories}'
    )


def _get_datasource(data_type: str, repository_name: str) -> DataTypeSpecificDataSource:
    thread_id = threading.get_ident()
    return _get_datasource_cache(data_type, repository_name, thread_id=thread_id)


@lru_cache(64)
def _get_datasource_cache(data_type: str, repository_name: str, thread_id: int) -> DataTypeSpecificDataSource:
    return _get_datasource_no_cache(data_type, repository_name)


def _get_datasource_no_cache(data_type: str, repository_name: str) -> DataTypeSpecificDataSource:
    return DataTypeSpecificDataSource(_resolve_data_type_config(data_type, repository_name))


def _get_repository_butler(repository_name: str) -> ButlerType:
    thread_id = threading.get_ident()
    return _get_repository_butler_cache(repository_name, thread_id=thread_id)


@lru_cache(32)
def _get_repository_butler_cache(repository_name: str, thread_id: int) -> ButlerType:
    del thread_id
    from lsst.daf.butler import Butler

    return Butler(repository_name)  # type: ignore
