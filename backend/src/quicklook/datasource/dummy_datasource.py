from .types import CcdRef, DataSourceBase, Query, Visit


class DummyDataSource(DataSourceBase):
    def query_datasets(self, q: Query) -> list[Visit]:
        return [
            Visit(exposure='raw:broccoli'),
            Visit(exposure='calexp:192350'),
            Visit(exposure=f'query:{q.day_obs}'),
            *[Visit(exposure=f'raw:{i}') for i in range(50)],
        ][: q.limit]

    def get_data(self, ref: CcdRef) -> bytes:
        return b''
