from types import SimpleNamespace

from quicklook.datasource import butler_datasource as butler_datasource_module
from quicklook.datasource.butler_datasource import ButlerDataSource
from quicklook.datasource.types import QueryWhereExample


def test_get_query_builder_options_skips_unbounded_collection_queries(monkeypatch):
    monkeypatch.setattr(butler_datasource_module, '_query_repository_names', lambda: ['embargo', 'main'])

    collections_called = False
    dataset_types_called = False

    def fake_query_collections(*args: object, **kwargs: object) -> list[str]:
        del args
        nonlocal collections_called
        collections_called = True
        assert kwargs == {'search_text': None}
        return []

    def fake_query_dataset_types(*args: object, **kwargs: object) -> list[str]:
        del args
        nonlocal dataset_types_called
        dataset_types_called = True
        assert kwargs == {'search_text': None}
        return []

    monkeypatch.setattr(butler_datasource_module, '_query_collections_for_repository', fake_query_collections)
    monkeypatch.setattr(butler_datasource_module, '_query_dataset_types_for_repository', fake_query_dataset_types)

    ds = ButlerDataSource.__new__(ButlerDataSource)
    result = ds.get_query_builder_options_sync(repository_name='main')

    assert result.repositories == ['embargo', 'main']
    assert result.collections == []
    assert result.dataset_types == []
    assert result.where_examples == []
    assert collections_called is True
    assert dataset_types_called is True


def test_get_query_builder_options_uses_exact_selection_for_where_examples(monkeypatch):
    monkeypatch.setattr(butler_datasource_module, '_query_repository_names', lambda: ['main'])
    monkeypatch.setattr(
        butler_datasource_module,
        '_query_collections_for_repository',
        lambda repository_name, *, search_text=None: ['LSSTCam/raw/all'] if repository_name == 'main' and search_text == 'LSSTCam/raw/all' else [],
    )
    monkeypatch.setattr(
        butler_datasource_module,
        '_query_dataset_types_for_repository',
        lambda repository_name, *, search_text=None: ['raw'] if repository_name == 'main' and search_text == 'raw' else [],
    )
    monkeypatch.setattr(
        butler_datasource_module,
        '_collection_exists_for_repository',
        lambda repository_name, collection: repository_name == 'main' and collection == 'LSSTCam/raw/all',
    )
    monkeypatch.setattr(
        butler_datasource_module,
        '_dataset_type_exists_for_repository',
        lambda repository_name, dataset_type: repository_name == 'main' and dataset_type == 'raw',
    )
    monkeypatch.setattr(
        butler_datasource_module,
        '_get_scope_datasource',
        lambda **kwargs: SimpleNamespace(
            query_where_examples=lambda: [QueryWhereExample(label='Latest day_obs', where='day_obs=20250301')],
            **kwargs,
        ),
    )

    ds = ButlerDataSource.__new__(ButlerDataSource)
    result = ds.get_query_builder_options_sync(
        repository_name='main',
        collection='LSSTCam/raw/all',
        dataset_type='raw',
    )

    assert result.collections == ['LSSTCam/raw/all']
    assert result.dataset_types == ['raw']
    assert result.where_examples == [QueryWhereExample(label='Latest day_obs', where='day_obs=20250301')]
