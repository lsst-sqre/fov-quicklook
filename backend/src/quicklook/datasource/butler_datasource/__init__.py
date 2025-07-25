from dataclasses import dataclass
from functools import cache, lru_cache
from typing import TYPE_CHECKING, Any, ClassVar, cast
from venv import logger

from lsst.resources import ResourcePath
from numpy import record

from quicklook.types import CcdDataType, CcdId

from ..types import DataSourceBase, DataSourceCcdMetadata, Query, Visit
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


@dataclass
class VisitEntry:
    id: str
    day_obs: int
    physical_filter: str
    obs_id: str
    exposure_time: float
    science_program: str
    observation_type: str
    observation_reason: str
    target_name: str


class ButlerDataSource(DataSourceBase):  # pragma: no cover
    def __init__(self):
        from quicklook.butlerutils import chown_pgpassfile

        chown_pgpassfile()

    def query_visits(self, q: Query) -> list[VisitEntry]:
        return get_datasource(q.data_type).query_visits(q)

    def list_ccds(self, visit: Visit) -> list[str]:
        return get_datasource(visit.data_type).list_ccds(visit)

    def get_data(self, ccd_id: CcdId) -> bytes:
        return get_datasource(ccd_id.visit.data_type).get_data(ccd_id)

    def get_metadata(self, ccd_id: CcdId) -> DataSourceCcdMetadata:
        return get_datasource(ccd_id.visit.data_type).get_metadata(ccd_id)

    def get_exposure_data_types(self, exposure_id: int) -> list[CcdDataType]:
        types: list[CcdDataType] = []
        for data_type in cast(list[CcdDataType], ['raw', 'post_isr_image', 'preliminary_visit_image']):
            datasource = get_datasource(data_type)
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

    def list_ccds(self, visit: Visit) -> list[str]:
        b = self._butler
        refs = b.query_datasets(visit.data_type, where=f"{self.data_id_key}={visit.name}")
        i = Instrument.get(default_instrument)
        return [i.detector_2_ccd[ref.dataId['detector']] for ref in refs]  # type: ignore

    def exposure_exists(self, exposure_id: int) -> bool:
        from lsst.daf.butler._exceptions import EmptyQueryResultError

        b = self._butler
        try:
            refs = b.query_datasets(self.data_type, where=f"{self.data_id_key}={exposure_id}", limit=1)
        except EmptyQueryResultError:
            return False
        return len(refs) > 0

    def get_data(self, ccd_id: CcdId) -> bytes:
        return retrieve_data(self._getUri(ccd_id), partial=self.partial)

    def _getUri(self, ccd_id: CcdId) -> ResourcePath:
        b = self._butler
        detector_id = Instrument.get(default_instrument).ccd_2_detector[ccd_id.ccd_name]
        ref = self._refs_by_visit(ccd_id.visit)[detector_id]
        return b.getURI(ref)  # type: ignore

    @lru_cache(maxsize=4)
    def _refs_by_visit(self, visit: Visit) -> dict[int, ButlerDatasetRef]:
        b = self._butler
        refs = b.query_datasets(visit.data_type, where=f"{self.data_id_key}={visit.name}")
        return {cast(int, ref.dataId['detector']): ref for ref in refs}

    def get_metadata(self, ccd_id: CcdId) -> DataSourceCcdMetadata:
        b = self._butler
        detector_id = Instrument.get(default_instrument).ccd_2_detector[ccd_id.ccd_name]
        refs = b.query_datasets(
            ccd_id.visit.data_type,
            where=f"{self.data_id_key}={ccd_id.visit.name} and detector={detector_id}",
        )
        if len(refs) != 1:
            raise ValueError(f"Cannot find unique dataset for {ccd_id.visit.name} and detector {detector_id}. found {len(refs)} matches")
        ref = refs[0]
        return DataSourceCcdMetadata(
            detector=detector_id,
            ccd_name=ccd_id.ccd_name,
            day_obs=ref.dataId.get('day_obs', -1),
            exposure=ref.dataId.get(self.data_id_key, -1),
            visit=Visit.from_id('raw:Dummy'),
            uuid=str(ref.id),
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


@cache
def get_datasource(data_type: CcdDataType) -> DataTypeSpecificDataSource:
    match data_type:
        case 'raw':
            return RawDataSource()
        case 'post_isr_image':
            return PostIsrImageDataSource()
        case 'preliminary_visit_image':
            return PreliminaryVisitImageDataSource()
    raise ValueError(f'Unknown data type: {data_type}')
