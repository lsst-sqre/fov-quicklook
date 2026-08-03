from quicklook.datasource.types import QueryBuilderOptions, QueryWhereExample
from quicklook.coordinator.api import query_builder_options


async def test_get_query_builder_options_uses_datasource(monkeypatch):
    class FakeDataSource:
        async def get_query_builder_options(self, **kwargs):
            assert kwargs == {
                'repository_name': 'repo',
                'collection': 'LSSTCam/raw/all',
                'dataset_type': 'raw',
            }
            return QueryBuilderOptions(
                repositories=['repo'],
                collections=['LSSTCam/raw/all'],
                dataset_types=['raw'],
                where_examples=[QueryWhereExample(label='Latest day_obs', where='day_obs=20250301')],
                collections_truncated=False,
                dataset_types_truncated=False,
            )

    monkeypatch.setattr(query_builder_options, 'get_datasource', lambda: FakeDataSource())

    result = await query_builder_options.get_query_builder_options(
        repository_name='repo',
        collection='LSSTCam/raw/all',
        dataset_type='raw',
    )

    assert result == QueryBuilderOptions(
        repositories=['repo'],
        collections=['LSSTCam/raw/all'],
        dataset_types=['raw'],
        where_examples=[QueryWhereExample(label='Latest day_obs', where='day_obs=20250301')],
        collections_truncated=False,
        dataset_types_truncated=False,
    )
