import threading
from functools import cache, lru_cache
from typing import TYPE_CHECKING, Any, ClassVar, cast
from venv import logger

from lsst.resources import ResourcePath

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


default_instrument = 'LSSTCam'
DataRef = Any


class ButlerDataSource(DataSourceBase):  # pragma: no cover
    def __init__(self):
        from .butlerutils import chown_pgpassfile

        chown_pgpassfile()

    def query_visits_sync(self, q: Query) -> list[VisitEntry]:
        return _get_datasource(q.data_type).query_visits(q)

    def list_ccds_sync(self, visit: VisitName) -> list[CcdName]:
        return _get_datasource(visit.data_type).list_ccds(visit)

    def get_data_sync(self, ref: CcdDataRef) -> bytes:
        return _get_datasource(ref.visit.data_type).get_data(ref)

    def get_metadata_sync(self, ref: CcdDataRef) -> DataSourceCcdMetadata:
        return _get_datasource(ref.visit.data_type).get_metadata(ref)

    def get_exposure_data_types_sync(self, exposure_id: int) -> list[CcdDataType]:
        types: list[CcdDataType] = []
        for data_type in cast(list[CcdDataType], ['raw', 'post_isr_image', 'preliminary_visit_image']):
            datasource = _get_datasource(data_type)
            if datasource.exposure_exists(exposure_id):
                types.append(data_type)
        return types


class DataTypeSpecificDataSource:
    # データタイプ固有の属性
    collections: ClassVar[list[str]]
    data_id_key: ClassVar[str] = "exposure"  # デフォルトはexposure
    data_type: ClassVar[str]
    order_by: ClassVar[list[str]] = ["-exposure"]
    partial: bool = False

    def __init__(self):
        super().__init__()
        from lsst.daf.butler import Butler

        self._butler: ButlerType = Butler(
            'embargo',
            instrument=default_instrument,
            collections=self.collections,
        )  # type: ignore

    def query_visits(self, q: Query) -> list[VisitEntry]:
        '''
        もしday_obsが指定されていない場合は、day_obsを最新の1日分に指定して実行する
        '''

        from lsst.daf.butler import EmptyQueryResultError

        if q.day_obs is None:
            q.day_obs = self._get_latest_day_obs()

        conds: list[str] = ['detector=0']
        if q.exposure:
            conds.append(f"{self.data_id_key}={q.exposure}")
        if q.day_obs:
            conds.append(f"day_obs={q.day_obs}")
        where = " and ".join(conds)
        try:
            refs = self._butler.query_datasets(q.data_type, where=where, limit=q.limit, order_by=self.order_by)
        except EmptyQueryResultError:
            return []

        exposures = self._get_exposure_info(q.day_obs or -1)  # q.day_obsはNoneではありえない

        return [
            VisitEntry(
                id=f'{self.data_type}:{ref.dataId[self.data_id_key]}',
                obs_id=exp.obs_id,
                day_obs=exp.day_obs,
                physical_filter=exp.physical_filter,
                exposure_time=exp.exposure_time,
                science_program=exp.science_program,
                observation_type=exp.observation_type,
                observation_reason=exp.observation_reason,
                target_name=exp.target_name,
            )
            for ref, exp in [(ref, exposures[cast(int, ref.dataId[self.data_id_key])]) for ref in refs]
        ]

    def list_ccds(self, visit: VisitName) -> list[CcdName]:
        b = self._butler
        refs = b.query_datasets(visit.data_type, where=f"{self.data_id_key}={visit.name}")
        i = Instrument.get(default_instrument)
        ccd_names = [CcdName(i.detector_2_ccd[ref.dataId['detector']]) for ref in refs]  # type: ignore
        if visit.data_type == 'post_isr_image':
            # ４隅のraftは位置情報がrawと違うため除外する
            ccd_names = [ccd_name for ccd_name in ccd_names if ccd_name[:3] not in {'R00', 'R40', 'R04', 'R44'}]
        return ccd_names

    def exposure_exists(self, exposure_id: int) -> bool:
        from lsst.daf.butler._exceptions import EmptyQueryResultError, MissingCollectionError

        b = self._butler
        try:
            refs = b.query_datasets(self.data_type, where=f"{self.data_id_key}={exposure_id}", limit=1)

        except (EmptyQueryResultError, MissingCollectionError):
            return False
        return len(refs) > 0

    def get_data(self, ref: CcdDataRef) -> bytes:
        return retrieve_data(self._getUri(ref), partial=self.partial)

    def _getUri(self, ref: CcdDataRef) -> ResourcePath:
        b = self._butler
        detector_id = Instrument.get(default_instrument).ccd_2_detector[ref.ccd_name]
        butler_ref = self._refs_by_visit(ref.visit)[detector_id]
        return b.getURI(butler_ref)  # type: ignore

    def _refs_by_visit(self, visit: VisitName) -> dict[int, ButlerDatasetRef]:
        b = self._butler
        refs = b.query_datasets(visit.data_type, where=f"{self.data_id_key}={visit.name}")
        return {cast(int, ref.dataId['detector']): ref for ref in refs}

    def get_metadata(self, ref: CcdDataRef) -> DataSourceCcdMetadata:
        b = self._butler
        detector_id = Instrument.get(default_instrument).ccd_2_detector[ref.ccd_name]
        butler_refs = b.query_datasets(
            ref.visit.data_type,
            where=f"{self.data_id_key}={ref.visit.name} and detector={detector_id}",
        )
        if len(butler_refs) != 1:
            raise ValueError(
                f"Cannot find unique dataset for {ref.visit.name} and detector {detector_id}. found {len(butler_refs)} matches"
            )
        butler_ref = butler_refs[0]
        return DataSourceCcdMetadata(
            detector=detector_id,
            ccd_name=ref.ccd_name,
            day_obs=butler_ref.dataId.get('day_obs', -1),
            exposure=butler_ref.dataId.get(self.data_id_key, -1),
            visit_name=ref.visit,
            uuid=str(butler_ref.id),
        )

    def _get_latest_day_obs(self) -> int | None:
        # 最新のday_obsを取得する
        b = self._butler
        refs = b.query_datasets(self.data_type, where="detector=0", order_by=["-day_obs"], limit=1)
        if len(refs) == 0:
            return None
        return refs[0].dataId['day_obs']  # type: ignore

    def _get_exposure_info(self, day_obs: int) -> dict[int, ButlerDimensionRecord]:
        records = self._butler.registry.queryDimensionRecords('exposure', where=f"day_obs={day_obs}")
        return {record.id: record for record in records}


class RawDataSource(DataTypeSpecificDataSource):
    collections = ['LSSTCam/raw/all']
    data_type = 'raw'
    order_by = ['-day_obs', '-exposure']


class PostIsrImageDataSource(DataTypeSpecificDataSource):
    collections = ['LSSTCam/runs/nightlyValidation']
    data_type = 'post_isr_image'
    partial = True


class PreliminaryVisitImageDataSource(DataTypeSpecificDataSource):
    collections = ['LSSTCam/runs/nightlyValidation']
    data_type = 'preliminary_visit_image'
    data_id_key = "visit"
    order_by = ['-visit']
    partial = True


def _get_datasource(data_type: CcdDataType) -> DataTypeSpecificDataSource:
    thread_id = threading.get_ident()
    return _get_datasource_cache(data_type, thread_id=thread_id)


@lru_cache(64)
def _get_datasource_cache(data_type: CcdDataType, thread_id: int) -> DataTypeSpecificDataSource:
    return _get_datasource_no_cache(data_type)


def _get_datasource_no_cache(data_type: CcdDataType) -> DataTypeSpecificDataSource:
    match data_type:
        case 'raw':
            return RawDataSource()
        case 'post_isr_image':
            return PostIsrImageDataSource()
        case 'preliminary_visit_image':
            return PreliminaryVisitImageDataSource()
    raise ValueError(f'Unknown data type: {data_type}')
