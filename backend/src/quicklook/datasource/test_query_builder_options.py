from types import SimpleNamespace

from lsst.daf.butler._exceptions import MissingCollectionError, MissingDatasetTypeError

from quicklook.datasource import butler_datasource as butler_datasource_module
from quicklook.datasource.butler_datasource import ButlerDataSource


def test_build_contains_glob():
    assert butler_datasource_module._build_contains_glob('nightly') == '*nightly*'


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


def test_get_query_builder_options_keeps_exact_selection_metadata_only(monkeypatch):
    monkeypatch.setattr(butler_datasource_module, '_query_repository_names', lambda: ['main'])
    monkeypatch.setattr(
        butler_datasource_module,
        '_query_collections_for_repository',
        lambda repository_name, *, search_text=None: (_ for _ in ()).throw(
            AssertionError(f'_query_collections_for_repository should not be called: {repository_name}, {search_text}')
        ),
    )
    monkeypatch.setattr(
        butler_datasource_module,
        '_query_dataset_types_for_repository',
        lambda repository_name, *, search_text=None: (_ for _ in ()).throw(
            AssertionError(f'_query_dataset_types_for_repository should not be called: {repository_name}, {search_text}')
        ),
    )
    monkeypatch.setattr(
        butler_datasource_module,
        '_collection_exists_for_repository',
        lambda repository_name, collection: (_ for _ in ()).throw(
            AssertionError(f'_collection_exists_for_repository should not be called: {repository_name}, {collection}')
        ),
    )
    monkeypatch.setattr(
        butler_datasource_module,
        '_dataset_type_exists_for_repository',
        lambda repository_name, dataset_type: (_ for _ in ()).throw(
            AssertionError(f'_dataset_type_exists_for_repository should not be called: {repository_name}, {dataset_type}')
        ),
    )
    monkeypatch.setattr(
        butler_datasource_module,
        '_get_scope_datasource',
        lambda **kwargs: (_ for _ in ()).throw(AssertionError(f'_get_scope_datasource should not be called: {kwargs}')),
    )

    ds = ButlerDataSource.__new__(ButlerDataSource)
    result = ds.get_query_builder_options_sync(
        repository_name='main',
        collection='LSSTCam/raw/all',
        dataset_type='raw',
    )

    assert result.collections == ['LSSTCam/raw/all']
    assert result.dataset_types == ['raw']
    assert result.where_examples == []


def test_collection_exists_for_repository_returns_false_for_partial_match(monkeypatch):
    class FakeRegistry:
        def queryCollections(self, expression, *, flattenChains=False):
            assert expression == 'nightly'
            assert flattenChains is False
            raise MissingCollectionError('nightly')

    monkeypatch.setattr(
        butler_datasource_module,
        '_get_query_repository_butler',
        lambda repository_name, instrument: SimpleNamespace(registry=FakeRegistry()),
    )

    assert butler_datasource_module._collection_exists_for_repository_cache(
        'embargo',
        'LSSTCam',
        'nightly',
        thread_id=1001,
    ) is False


def test_dataset_type_exists_for_repository_returns_false_for_partial_match(monkeypatch):
    class FakeRegistry:
        def queryDatasetTypes(self, expression):
            assert expression == 'raw'
            raise MissingDatasetTypeError('raw')

    monkeypatch.setattr(
        butler_datasource_module,
        '_get_query_repository_butler',
        lambda repository_name, instrument: SimpleNamespace(registry=FakeRegistry()),
    )

    assert butler_datasource_module._dataset_type_exists_for_repository_cache(
        'embargo',
        'LSSTCam',
        'raw',
        thread_id=1002,
    ) is False
