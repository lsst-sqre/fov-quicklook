from functools import cache, lru_cache
from typing import TYPE_CHECKING, Any

from lsst.resources import ResourcePath

from quicklook.types import CcdDataType, CcdId

from ..types import DataSourceBase, DataSourceCcdMetadata, Query, Visit
from .instrument import Instrument
from .retrieve_data import retrieve_data

if TYPE_CHECKING:
    from lsst.daf.butler import Butler as ButlerType
else:
    ButlerType = Any


default_instrument = 'LSSTCam'
DataRef = Any


class ButlerDataSource(DataSourceBase):  # pragma: no cover
    def __init__(self):
        from quicklook.butlerutils import chown_pgpassfile

        chown_pgpassfile()

    def query_visits(self, q: Query) -> list[Visit]:
        return get_datasource(q.data_type).query_visits(q)

    def list_ccds(self, visit: Visit) -> list[str]:
        return get_datasource(visit.data_type).list_ccds(visit)

    def get_data(self, ref: CcdId) -> bytes:
        return get_datasource(ref.visit.data_type).get_data(ref)

    def get_metadata(self, ref: CcdId) -> DataSourceCcdMetadata: ...


class DataTypeSpecificDataSource:
    def query_visits(self, q: Query) -> list[Visit]: ...

    def list_ccds(self, visit: Visit) -> list[str]: ...

    def get_data(self, ref: CcdId) -> bytes: ...

    def get_metadata(self, ref: CcdId) -> DataSourceCcdMetadata: ...


class RawDataSource(DataTypeSpecificDataSource):
    def __init__(self):
        super().__init__()
        from lsst.daf.butler import Butler

        self._butler: ButlerType = Butler(
            'embargo',
            collections=['LSSTCam/raw/all'],
        )  # type: ignore

    def query_visits(self, q: Query) -> list[Visit]:
        from lsst.daf.butler import EmptyQueryResultError

        conds: list[str] = ["detector=0"]
        if q.exposure:
            conds.append(f"exposure='{q.exposure}'")
        if q.day_obs:
            conds.append(f"day_obs={q.day_obs}")
        where = " and ".join(conds)
        try:
            refs = self._butler.query_datasets(q.data_type, where=where, limit=q.limit, order_by=['-day_obs', '-exposure'])
        except EmptyQueryResultError:
            refs = []
        return [Visit.from_id(f'raw:{ref.dataId["exposure"]}') for ref in refs]

    def list_ccds(self, visit: Visit) -> list[str]:
        b = self._butler
        refs = b.query_datasets(visit.data_type, where=f"exposure={visit.name}")
        i = Instrument.get(default_instrument)
        return [i.detector_2_ccd[ref.dataId['detector']] for ref in refs]  # type: ignore

    def get_data(self, ref: CcdId) -> bytes:
        return retrieve_data(self._getUri(ref))

    def _getUri(self, ref: CcdId) -> ResourcePath:
        b = self._butler
        detector_id = Instrument.get(default_instrument).ccd_2_detector[ref.ccd_name]
        ref = self._refs_by_visit(ref.visit)[detector_id]
        return b.getURI(ref)  # type: ignore

    @lru_cache(maxsize=4)
    def _refs_by_visit(self, visit: Visit) -> dict:
        b = self._butler
        refs = b.query_datasets(visit.data_type, where=f"exposure={visit.name}")
        return {ref.dataId['detector']: ref for ref in refs}

    def get_metadata(self, ref: CcdId) -> DataSourceCcdMetadata:
        return DataSourceCcdMetadata(
            detector=0,
            ccd_name='X',
            day_obs=0,
            exposure=0,
            visit=Visit.from_id('raw:Dummy'),
        )


class PostIsrImageDataSource(DataTypeSpecificDataSource):
    def __init__(self):
        super().__init__()
        from lsst.daf.butler import Butler

        self._butler: ButlerType = Butler(
            'embargo',
            collections=['LSSTCam/runs/nightlyValidation'],
        )  # type: ignore

    def query_visits(self, q: Query) -> list[Visit]:
        from lsst.daf.butler import EmptyQueryResultError

        conds: list[str] = ["detector=0"]
        if q.exposure:
            conds.append(f"exposure='{q.exposure}'")
        if q.day_obs:
            conds.append(f"day_obs={q.day_obs}")
        where = " and ".join(conds)
        try:
            refs = self._butler.query_datasets(q.data_type, where=where, limit=q.limit, order_by='-exposure')
        except EmptyQueryResultError:
            refs = []
        return [Visit.from_id(f'post_isr_image:{ref.dataId["exposure"]}') for ref in refs]

    def list_ccds(self, visit: Visit) -> list[str]:
        b = self._butler
        refs = b.query_datasets(visit.data_type, where=f"exposure={visit.name}")
        i = Instrument.get(default_instrument)
        return [i.detector_2_ccd[ref.dataId['detector']] for ref in refs]  # type: ignore

    def get_data(self, ref: CcdId) -> bytes:
        return retrieve_data(self._getUri(ref))

    def _getUri(self, ref: CcdId) -> ResourcePath:
        b = self._butler
        detector_id = Instrument.get(default_instrument).ccd_2_detector[ref.ccd_name]
        ref = self._refs_by_visit(ref.visit)[detector_id]
        return b.getURI(ref)  # type: ignore

    @lru_cache(maxsize=4)
    def _refs_by_visit(self, visit: Visit) -> dict:
        b = self._butler
        refs = b.query_datasets(visit.data_type, where=f"exposure={visit.name}")
        return {ref.dataId['detector']: ref for ref in refs}

    def get_metadata(self, ref: CcdId) -> DataSourceCcdMetadata:
        return DataSourceCcdMetadata(
            detector=0,
            ccd_name='X',
            day_obs=0,
            exposure=0,
            visit=Visit.from_id('raw:Dummy'),
        )


class PreliminaryVisitImageDataSource(DataTypeSpecificDataSource):
    def __init__(self):
        super().__init__()
        from lsst.daf.butler import Butler

        self._butler: ButlerType = Butler(
            'embargo',
            collections=['LSSTCam/runs/nightlyValidation'],
        )  # type: ignore

    def query_visits(self, q: Query) -> list[Visit]:
        from lsst.daf.butler import EmptyQueryResultError

        conds: list[str] = ["detector=0"]
        if q.exposure:
            conds.append(f"visit='{q.exposure}'")
        if q.day_obs:
            conds.append(f"day_obs={q.day_obs}")
        where = " and ".join(conds)
        try:
            refs = self._butler.query_datasets(q.data_type, where=where, limit=q.limit, order_by='-visit')
        except EmptyQueryResultError:
            refs = []
        return [Visit.from_id(f'preliminary_visit_image:{ref.dataId["visit"]}') for ref in refs]

    def list_ccds(self, visit: Visit) -> list[str]:
        b = self._butler
        refs = b.query_datasets(visit.data_type, where=f"visit={visit.name}")
        i = Instrument.get(default_instrument)
        return [i.detector_2_ccd[ref.dataId['detector']] for ref in refs]  # type: ignore

    def get_data(self, ref: CcdId) -> bytes:
        return retrieve_data(self._getUri(ref))

    def _getUri(self, ref: CcdId) -> ResourcePath:
        b = self._butler
        detector_id = Instrument.get(default_instrument).ccd_2_detector[ref.ccd_name]
        ref = self._refs_by_visit(ref.visit)[detector_id]
        return b.getURI(ref)  # type: ignore

    @lru_cache(maxsize=4)
    def _refs_by_visit(self, visit: Visit) -> dict:
        b = self._butler
        refs = b.query_datasets(visit.data_type, where=f"visit={visit.name}")
        return {ref.dataId['detector']: ref for ref in refs}

    def get_metadata(self, ref: CcdId) -> DataSourceCcdMetadata:
        return DataSourceCcdMetadata(
            detector=0,
            ccd_name='X',
            day_obs=0,
            exposure=0,
            visit=Visit.from_id('raw:Dummy'),
        )


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
