from quicklook.types import CcdId
from .types import DataSourceBase, DataSourceVisit, Query


class DummyDataSource(DataSourceBase):
    def query_visits(self, q: Query) -> list[DataSourceVisit]:
        return [
            DataSourceVisit('raw', 'raw:broccoli'),
            DataSourceVisit('calexp', 'calexp:192350'),
            DataSourceVisit('raw', f'query:{q.day_obs}'),
            *[DataSourceVisit('raw', f'raw:{i}') for i in range(50)],
        ][: q.limit]

    def get_data(self, ref: CcdId) -> bytes:
        return b''

    def list_ccds(self, visit: DataSourceVisit) -> list[str]:
        ...