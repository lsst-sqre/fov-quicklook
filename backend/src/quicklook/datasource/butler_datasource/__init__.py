import threading
from functools import lru_cache
from typing import TYPE_CHECKING, Any, cast

from lsst.resources import ResourcePath

from quicklook.config import CcdDataTypeConfig, config
from quicklook.datasource.types import VisitEntry
from quicklook.types import CcdDataRef, CcdDataType, CcdName, VisitName

from ..types import DataSourceBase, DataSourceCcdMetadata, Query
from .instrument import Instrument
from .retrieve_data import retrieve_data

if TYPE_CHECKING:
    from lsst.daf.butler import Butler as ButlerType
    from lsst.daf.butler import DatasetRef as ButlerDatasetRef
    from lsst.daf.butler import DimensionRecord as ButlerDimensionRecord
else:
    ButlerType = Any
    ButlerDatasetRef = Any
    ButlerDimensionRecord = Any


DataRef = Any


class ButlerDataSource(DataSourceBase):  # pragma: no cover
    def __init__(self):
        from .butlerutils import chown_pgpassfile

        chown_pgpassfile()

    def query_visits_sync(self, q: Query) -> list[VisitEntry]:
        return _get_datasource(q.data_type, q.repository_name).query_visits(q)

    def list_ccds_sync(self, visit: VisitName) -> list[CcdName]:
        return _get_datasource(visit.data_type, visit.repository_name).list_ccds(visit)

    def get_data_sync(self, ref: CcdDataRef) -> bytes:
        return _get_datasource(ref.visit.data_type, ref.visit.repository_name).get_data(ref)

    def get_metadata_sync(self, ref: CcdDataRef) -> DataSourceCcdMetadata:
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

    def list_ccds(self, visit: VisitName) -> list[CcdName]:
        b = self._butler
        refs = b.query_datasets(self.butler_data_type, where=f"{self.data_id_dimension}={visit.name}")
        i = Instrument.get(self.instrument)
        ccd_names = [CcdName(i.detector_2_ccd[ref.dataId['detector']]) for ref in refs]  # type: ignore
        if self.butler_data_type == 'post_isr_image':
            # ４隅のraftは位置情報がrawと違うため除外する
            ccd_names = [ccd_name for ccd_name in ccd_names if ccd_name[:3] not in {'R00', 'R40', 'R04', 'R44'}]
        return ccd_names

    def exposure_exists(self, exposure_id: int) -> bool:
        from lsst.daf.butler._exceptions import EmptyQueryResultError, MissingCollectionError

        b = self._butler
        try:
            refs = b.query_datasets(self.butler_data_type, where=f"{self.data_id_dimension}={exposure_id}", limit=1)

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
        b = self._butler
        refs = b.query_datasets(self.butler_data_type, where=f"{self.data_id_dimension}={visit.name}")
        return {cast(int, ref.dataId['detector']): ref for ref in refs}

    def get_metadata(self, ref: CcdDataRef) -> DataSourceCcdMetadata:
        b = self._butler
        detector_id = Instrument.get(self.instrument).ccd_2_detector[ref.ccd]
        butler_refs = b.query_datasets(
            self.butler_data_type,
            where=f"{self.data_id_dimension}={ref.visit.name} and detector={detector_id}",
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
        if where:
            kwargs['where'] = where
        if limit is not None:
            kwargs['limit'] = limit
        if order_by is not None:
            kwargs['order_by'] = order_by
        return list(self._butler.registry.queryDimensionRecords(dimension, **kwargs))

    def _visit_entry_from_record(self, record: ButlerDimensionRecord) -> VisitEntry:
        return VisitEntry(
            id=f'{self.repository_name}:{self.butler_data_type}:{record.id}',
            obs_id=record.obs_id,
            day_obs=record.day_obs,
            physical_filter=record.physical_filter,
            exposure_time=record.exposure_time,
            science_program=record.science_program,
            observation_type=record.observation_type,
            observation_reason=record.observation_reason,
            target_name=record.target_name,
        )

    def _get_exposure_info(self, day_obs: int) -> dict[int, ButlerDimensionRecord]:
        records = self._butler.registry.queryDimensionRecords('exposure', where=f"day_obs={day_obs}")
        return {record.id: record for record in records}


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
