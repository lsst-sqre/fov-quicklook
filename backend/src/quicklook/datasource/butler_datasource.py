from .types import CcdRef, DataSourceBase, Query, Visit


class ButlerDataSource(DataSourceBase):
    def __init__(self):
        from quicklook.butlerutils import chown_pgpassfile

        chown_pgpassfile()
        from lsst.daf.butler import Butler

        self._butler = Butler("embargo", instrument="LSSTComCam", collections="LSSTComCam/raw/all")  # type: ignore

    def query_datasets(self, q: Query) -> list[Visit]:
        from lsst.daf.butler import EmptyQueryResultError

        conds: list[str] = ["detector=0"]
        if q.exposure:
            conds.append(f"exposure='{q.exposure}'")
        if q.day_obs:
            conds.append(f"day_obs={q.day_obs}")
        where = " and ".join(conds)
        try:
            refs = self._butler.query_datasets("raw", where=where, limit=q.limit)
        except EmptyQueryResultError:
            refs = []
        return [Visit(exposure=str(ref.dataId['exposure'])) for ref in refs]

    def get_data(self, ref: CcdRef) -> bytes:
        return b''
