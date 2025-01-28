from functools import lru_cache
from typing import Any

from lsst.resources import ResourcePath

from quicklook.types import CcdId

from ..types import DataSourceBase, Query, Visit
from .instrument import Instrument
from .retrieve_data import retrieve_data

default_instrument = 'LSSTComCam'
DataRef = Any


class ButlerDataSource(DataSourceBase):
    def __init__(self):
        from quicklook.butlerutils import chown_pgpassfile

        chown_pgpassfile()
        from lsst.daf.butler import Butler

        self._butler = Butler("embargo", instrument=default_instrument, collections="LSSTComCam/raw/all")  # type: ignore

    def query_visits(self, q: Query) -> list[Visit]:
        from lsst.daf.butler import EmptyQueryResultError

        conds: list[str] = ["detector=0"]
        if q.exposure:
            conds.append(f"exposure='{q.exposure}'")
        if q.day_obs:
            conds.append(f"day_obs={q.day_obs}")
        where = " and ".join(conds)
        try:
            refs = self._butler.query_datasets(q.data_type, where=where, limit=q.limit)
        except EmptyQueryResultError:
            refs = []
        return [Visit(q.data_type, f'{q.data_type}:{ref.dataId['exposure']}') for ref in refs]

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
