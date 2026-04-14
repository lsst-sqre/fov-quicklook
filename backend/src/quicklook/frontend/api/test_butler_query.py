from quicklook.datasource.types import ButlerDatasetTypeDimensions, ButlerDatasetTypeInfo, ButlerQuery, ButlerQueryResult, ButlerQueryRow
from quicklook.frontend.api import butler_query
from quicklook.types import VisitName


async def test_query_butler_passes_reserved_and_dynamic_filters(monkeypatch):
    captured: list[ButlerQuery] = []

    class FakeDataSource:
        async def query_butler(self, q: ButlerQuery) -> ButlerQueryResult:
            captured.append(q)
            return ButlerQueryResult(
                repository_name='embargo',
                data_type='raw',
                data_id_dimension='exposure',
                applied_collections=['LSSTCam/raw/all'],
                applied_filters={'day_obs': '20260503', 'physical_filter': 'g'},
                order=['-day_obs', '-exposure'],
                limit=10,
                offset=20,
                returned_count=1,
                has_more=True,
                columns=['exposure', 'day_obs'],
                rows=[ButlerQueryRow(visit_name=VisitName('embargo:raw:202605030001'), record={'exposure': 202605030001})],
            )

        async def list_butler_dataset_types(self, repository_name=None):
            del repository_name
            return []

        async def get_butler_dataset_type_dimensions(self, data_type, repository_name=None):
            del data_type, repository_name
            raise AssertionError('not used')

    monkeypatch.setattr(butler_query, 'get_datasource', lambda: FakeDataSource())

    request = type('Request', (), {
        'query_params': type('QueryParams', (), {
            'getlist': staticmethod(lambda key: {
                'collection': ['LSSTCam/raw/all'],
                'order': ['-day_obs,-exposure'],
            }.get(key, [])),
            'multi_items': staticmethod(lambda: [
                ('data_type', 'raw'),
                ('day_obs', '20260503'),
                ('filter', 'g'),
                ('limit', '10'),
                ('offset', '20'),
                ('collection', 'LSSTCam/raw/all'),
                ('order', '-day_obs,-exposure'),
            ]),
        })(),
    })()

    result = await butler_query.query_butler(
        request=request,
        data_type='raw',
        repository_name=None,
        limit=10,
        offset=20,
    )

    assert result.returned_count == 1
    assert captured == [
        ButlerQuery(
            data_type='raw',
            repository_name=None,
            limit=10,
            offset=20,
            collections=['LSSTCam/raw/all'],
            order=['-day_obs', '-exposure'],
            filters={'day_obs': '20260503', 'filter': 'g'},
        )
    ]


async def test_list_butler_dataset_types_delegates(monkeypatch):
    class FakeDataSource:
        async def list_butler_dataset_types(self, repository_name=None):
            assert repository_name == 'embargo'
            return [
                ButlerDatasetTypeInfo(
                    repository_name='embargo',
                    data_type='raw',
                    display_name='Raw',
                    data_id_dimension='exposure',
                    default_collections=['LSSTCam/raw/all'],
                    default_order=['-day_obs', '-exposure'],
                )
            ]

        async def query_butler(self, q):
            del q
            raise AssertionError('not used')

        async def get_butler_dataset_type_dimensions(self, data_type, repository_name=None):
            del data_type, repository_name
            raise AssertionError('not used')

    monkeypatch.setattr(butler_query, 'get_datasource', lambda: FakeDataSource())

    result = await butler_query.list_butler_dataset_types(repository_name='embargo')

    assert [item.data_type for item in result] == ['raw']


async def test_get_butler_dataset_type_dimensions_delegates(monkeypatch):
    class FakeDataSource:
        async def get_butler_dataset_type_dimensions(self, data_type, repository_name=None):
            assert data_type == 'raw'
            assert repository_name == 'embargo'
            return ButlerDatasetTypeDimensions(
                repository_name='embargo',
                data_type='raw',
                data_id_dimension='exposure',
                dimensions=['band', 'detector', 'exposure'],
                filter_aliases={'filter': 'physical_filter'},
            )

        async def query_butler(self, q):
            del q
            raise AssertionError('not used')

        async def list_butler_dataset_types(self, repository_name=None):
            del repository_name
            raise AssertionError('not used')

    monkeypatch.setattr(butler_query, 'get_datasource', lambda: FakeDataSource())

    result = await butler_query.get_butler_dataset_type_dimensions('raw', repository_name='embargo')

    assert result.dimensions == ['band', 'detector', 'exposure']
