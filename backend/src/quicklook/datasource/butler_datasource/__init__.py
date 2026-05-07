import threading
from collections import Counter
from datetime import date
from functools import lru_cache
from itertools import islice
from types import EllipsisType
from typing import TYPE_CHECKING, Any, cast
from uuid import UUID

from lsst.resources import ResourcePath

from quicklook.config import CcdDataTypeConfig, config
from quicklook.datasource.types import VisitDayCount, VisitDayCountQuery, VisitEntry
from quicklook.types import CcdDataRef, CcdDataType, CcdName, VisitName

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
_resolved_visit_runs: dict[str, str] = {}
_resolved_visit_runs_lock = threading.Lock()


class ButlerDataSource(DataSourceBase):  # pragma: no cover
    def __init__(self):
        from .butlerutils import chown_pgpassfile

        chown_pgpassfile()

    def query_visits_sync(self, q: Query) -> list[VisitEntry]:
        return _get_datasource(q.data_type, q.repository_name).query_visits(q)

    def query_visit_day_counts_sync(self, q: VisitDayCountQuery) -> list[VisitDayCount]:
        return _get_datasource(q.data_type, q.repository_name).query_visit_day_counts(q.calendar_month)

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

    def query_visit_day_counts(self, calendar_month: str) -> list[VisitDayCount]:
        start_day_obs, end_day_obs = _calendar_month_day_obs_range(calendar_month)
        data_ids = self._query_data_ids(
            ['day_obs', self.data_id_dimension],
            datasets=self.butler_data_type,
            where=f"day_obs>={start_day_obs} and day_obs<{end_day_obs}",
            order_by=['day_obs'],
        )
        counts_by_day_obs = Counter(int(data_id['day_obs']) for data_id in data_ids)
        return [VisitDayCount(day_obs=day_obs, count=count) for day_obs, count in sorted(counts_by_day_obs.items())]

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
        self._dataset_ref(ref)
        if self._is_virtual_review_app_fixture(ref.visit):
            return self._render_virtual_review_app_raw(ref)
        return retrieve_data(self._getUri(ref), partial=self.partial)

    def _getUri(self, ref: CcdDataRef) -> ResourcePath:
        b = self._butler
        butler_ref = self._dataset_ref(ref)
        return b.getURI(butler_ref)  # type: ignore

    def _dataset_ref(self, ref: CcdDataRef) -> ButlerDatasetRef:
        detector_id = Instrument.get(self.instrument).ccd_2_detector[ref.ccd]
        return self._refs_by_visit(ref.visit)[detector_id]

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
        where: str | None = None,
        limit: int | None = None,
        order_by: list[str] | None = None,
    ) -> list[ButlerDimensionRecord]:
        kwargs: dict[str, Any] = {}
        if datasets is not None:
            kwargs['datasets'] = datasets
            if self.butler_data_type == 'difference_image':
                kwargs['collections'] = self._query_collections()
        if where:
            kwargs['where'] = where
        records = self._butler.registry.queryDimensionRecords(dimension, **kwargs)
        if order_by is not None:
            records = records.order_by(*order_by)
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
            if self.butler_data_type == 'difference_image':
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

    def _get_exposure_record(self, exposure_id: int) -> ButlerDimensionRecord:
        records = self._query_dimension_records("exposure", where=f"exposure={exposure_id}", limit=1)
        if len(records) != 1:
            raise ValueError(f"Cannot find unique exposure record for exposure {exposure_id}. found {len(records)} matches")
        return records[0]

    def _is_virtual_review_app_fixture(self, visit: VisitName) -> bool:
        from quicklook.review_app.shared_fixtures import FIXTURE_REPOSITORY_NAME

        return visit.repository_name == FIXTURE_REPOSITORY_NAME and visit.data_type == "raw"

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


def _calendar_month_day_obs_range(calendar_month: str) -> tuple[int, int]:
    year_text, month_text = calendar_month.split('-', maxsplit=1)
    year = int(year_text)
    month = int(month_text)
    start = date(year, month, 1)
    end = date(year + (1 if month == 12 else 0), 1 if month == 12 else month + 1, 1)
    return int(start.strftime('%Y%m%d')), int(end.strftime('%Y%m%d'))


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


def _record_int_attr(record: ButlerDimensionRecord, *names: str, default: int = 0) -> int:
    for name in names:
        value = getattr(record, name, None)
        if value is not None:
            return int(value)
    return default


def _get_datasource(data_type: str, repository_name: str) -> DataTypeSpecificDataSource:
    thread_id = threading.get_ident()
    return _get_datasource_cache(data_type, repository_name, thread_id=thread_id)


@lru_cache(64)
def _get_datasource_cache(data_type: str, repository_name: str, thread_id: int) -> DataTypeSpecificDataSource:
    return _get_datasource_no_cache(data_type, repository_name)


def _get_datasource_no_cache(data_type: str, repository_name: str) -> DataTypeSpecificDataSource:
    for data_type_config in config.ccd_data_types:
        if data_type_config.data_type == data_type and data_type_config.repository_name == repository_name:
            return DataTypeSpecificDataSource(data_type_config)
    available = [(dt.data_type, dt.repository_name) for dt in config.ccd_data_types]
    raise ValueError(f'Unknown data type: ({data_type}, {repository_name}). Available: {available}')


def _get_repository_butler(repository_name: str) -> ButlerType:
    thread_id = threading.get_ident()
    return _get_repository_butler_cache(repository_name, thread_id=thread_id)


@lru_cache(32)
def _get_repository_butler_cache(repository_name: str, thread_id: int) -> ButlerType:
    del thread_id
    from lsst.daf.butler import Butler

    return Butler(repository_name)  # type: ignore
