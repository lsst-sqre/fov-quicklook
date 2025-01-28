from quicklook.types import CcdId
from .types import DataSourceBase, Visit, Query


class DummyDataSource(DataSourceBase):
    def query_visits(self, q: Query) -> list[Visit]:
        return [
            Visit('raw', 'raw:broccoli'),
            Visit('calexp', 'calexp:192350'),
            Visit('raw', f'query:{q.day_obs}'),
            *[Visit('raw', f'raw:{i}') for i in range(50)],
        ][: q.limit]

    def get_data(self, ref: CcdId) -> bytes:
        return b''

    def list_ccds(self, visit: Visit) -> list[str]:
        ...