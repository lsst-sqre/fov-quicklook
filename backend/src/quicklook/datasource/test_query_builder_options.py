import sys
from types import SimpleNamespace

from lsst.daf.butler._exceptions import MissingCollectionError, MissingDatasetTypeError

from quicklook.datasource import butler_datasource as butler_datasource_module
from quicklook.datasource.butler_datasource import ButlerDataSource


def test_build_contains_glob():
    assert butler_datasource_module._build_contains_glob('nightly') == '*nightly*'


def test_butler_datasource_init_does_not_prime_query_builder_metadata(monkeypatch):
    calls: list[str] = []
    monkeypatch.setitem(
        sys.modules,
        'quicklook.datasource.butler_datasource.butlerutils',
        SimpleNamespace(chown_pgpassfile=lambda: calls.append('chown')),
    )
    monkeypatch.setattr(
        butler_datasource_module,
        '_prime_query_builder_metadata_async',
        lambda repository_name: calls.append(repository_name),
    )

    ButlerDataSource()

    assert calls == ['chown']


def test_get_query_builder_options_skips_unbounded_collection_queries(monkeypatch):
    monkeypatch.setattr(butler_datasource_module, '_query_repository_names', lambda: ['embargo', 'main'])
    monkeypatch.setattr(butler_datasource_module, '_prime_query_builder_metadata_async', lambda repository_name: None)

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
    monkeypatch.setattr(butler_datasource_module, '_prime_query_builder_metadata_async', lambda repository_name: None)
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


def test_get_query_builder_options_filters_partial_collection_from_cached_metadata(monkeypatch):
    monkeypatch.setattr(butler_datasource_module, '_query_repository_names', lambda: ['main'])
    monkeypatch.setattr(butler_datasource_module, '_prime_query_builder_metadata_async', lambda repository_name: None)
    monkeypatch.setattr(
        butler_datasource_module,
        '_get_query_repository_metadata_if_available',
        lambda repository_name, wait_for_prefetch=False: butler_datasource_module._QueryRepositoryMetadata(
            collections=('LSSTCam/raw/all', 'LSSTCam/runs/nightlyValidation/10'),
            dataset_types=('preliminary_visit_image', 'raw'),
        ),
    )

    ds = ButlerDataSource.__new__(ButlerDataSource)
    result = ds.get_query_builder_options_sync(repository_name='main', collection='nightly')

    assert result.collections == ['LSSTCam/runs/nightlyValidation/10']
    assert result.dataset_types == []
    assert result.where_examples == []


def test_get_query_builder_options_does_not_short_circuit_partial_dataset_type(monkeypatch):
    monkeypatch.setattr(butler_datasource_module, '_query_repository_names', lambda: ['main'])
    monkeypatch.setattr(butler_datasource_module, '_prime_query_builder_metadata_async', lambda repository_name: None)
    monkeypatch.setattr(
        butler_datasource_module,
        '_get_query_repository_metadata_if_available',
        lambda repository_name, wait_for_prefetch=False: butler_datasource_module._QueryRepositoryMetadata(
            collections=('LSSTCam/raw/all', 'LSSTCam/runs/nightlyValidation/10'),
            dataset_types=('preliminary_visit_image', 'raw'),
        ),
    )

    ds = ButlerDataSource.__new__(ButlerDataSource)
    result = ds.get_query_builder_options_sync(
        repository_name='main',
        collection='LSSTCam/runs/nightlyValidation/10',
        dataset_type='prelim',
    )

    assert result.collections == ['LSSTCam/runs/nightlyValidation/10']
    assert result.dataset_types == ['preliminary_visit_image']
    assert result.where_examples == []


def test_get_query_builder_options_falls_back_to_direct_collection_search_while_prefetch_runs(monkeypatch):
    monkeypatch.setattr(butler_datasource_module, '_query_repository_names', lambda: ['main'])
    prefetch_calls: list[str] = []
    monkeypatch.setattr(
        butler_datasource_module,
        '_prime_query_builder_metadata_async',
        lambda repository_name: prefetch_calls.append(repository_name),
    )
    monkeypatch.setattr(
        butler_datasource_module,
        '_get_query_repository_metadata_if_available',
        lambda repository_name, wait_for_prefetch=False: None,
    )
    monkeypatch.setattr(
        butler_datasource_module,
        '_repository_instrument',
        lambda repository_name: 'LSSTCam',
    )
    monkeypatch.setattr(
        butler_datasource_module,
        '_query_collections_for_repository_cache',
        lambda repository_name, instrument, search_text, thread_id: ('LSSTCam/runs/nightlyValidation/10',),
    )
    monkeypatch.setattr(
        butler_datasource_module,
        '_collection_exists_for_repository_cache',
        lambda repository_name, instrument, collection, thread_id: False,
    )

    ds = ButlerDataSource.__new__(ButlerDataSource)
    result = ds.get_query_builder_options_sync(repository_name='main', collection='nightly')

    assert result.collections == ['LSSTCam/runs/nightlyValidation/10']
    assert result.dataset_types == []
    assert result.where_examples == []
    assert prefetch_calls == ['main', 'main', 'main']


def test_get_query_builder_options_keeps_exact_selection_while_prefetch_runs(monkeypatch):
    monkeypatch.setattr(butler_datasource_module, '_query_repository_names', lambda: ['main'])
    monkeypatch.setattr(
        butler_datasource_module,
        '_prime_query_builder_metadata_async',
        lambda repository_name: None,
    )
    monkeypatch.setattr(
        butler_datasource_module,
        '_get_query_repository_metadata_if_available',
        lambda repository_name, wait_for_prefetch=False: None,
    )
    monkeypatch.setattr(
        butler_datasource_module,
        '_repository_instrument',
        lambda repository_name: 'LSSTCam',
    )
    monkeypatch.setattr(
        butler_datasource_module,
        '_collection_exists_for_repository_cache',
        lambda repository_name, instrument, collection, thread_id: collection == 'LSSTCam/raw/all',
    )
    monkeypatch.setattr(
        butler_datasource_module,
        '_dataset_type_exists_for_repository_cache',
        lambda repository_name, instrument, dataset_type, thread_id: dataset_type == 'raw',
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


def test_dataset_type_exists_for_repository_filters_non_quicklook_dataset_types(monkeypatch):
    class FakeDatasetType:
        name = 'not_quicklook'
        dimensions = SimpleNamespace(required=(SimpleNamespace(name='visit'),))

    class FakeRegistry:
        def queryDatasetTypes(self, expression):
            assert expression == 'not_quicklook'
            return [FakeDatasetType()]

    monkeypatch.setattr(
        butler_datasource_module,
        '_get_query_repository_butler',
        lambda repository_name, instrument: SimpleNamespace(registry=FakeRegistry()),
    )
    monkeypatch.setattr(
        butler_datasource_module,
        'get_dataset',
        lambda dataset_type_name: SimpleNamespace(
            quicklook_dimensions=lambda dims: (_ for _ in ()).throw(ValueError('unsupported'))
        ),
    )

    assert butler_datasource_module._dataset_type_exists_for_repository_cache(
        'embargo',
        'LSSTCam',
        'not_quicklook',
        thread_id=1003,
    ) is False


def test_get_query_builder_options_returns_empty_options_when_direct_fallback_raises(monkeypatch):
    monkeypatch.setattr(butler_datasource_module, '_query_repository_names', lambda: ['main'])
    monkeypatch.setattr(
        butler_datasource_module,
        '_prime_query_builder_metadata_async',
        lambda repository_name: None,
    )
    monkeypatch.setattr(
        butler_datasource_module,
        '_get_query_repository_metadata_if_available',
        lambda repository_name, wait_for_prefetch=False: None,
    )
    monkeypatch.setattr(
        butler_datasource_module,
        '_repository_instrument',
        lambda repository_name: 'LSSTCam',
    )
    monkeypatch.setattr(
        butler_datasource_module,
        '_collection_exists_for_repository_cache',
        lambda repository_name, instrument, collection, thread_id: (_ for _ in ()).throw(RuntimeError('boom')),
    )
    monkeypatch.setattr(
        butler_datasource_module,
        '_dataset_type_exists_for_repository_cache',
        lambda repository_name, instrument, dataset_type, thread_id: (_ for _ in ()).throw(RuntimeError('boom')),
    )
    monkeypatch.setattr(
        butler_datasource_module,
        '_query_collections_for_repository_cache',
        lambda repository_name, instrument, search_text, thread_id: (_ for _ in ()).throw(RuntimeError('boom')),
    )
    monkeypatch.setattr(
        butler_datasource_module,
        '_query_dataset_types_for_repository_cache',
        lambda repository_name, instrument, search_text, thread_id: (_ for _ in ()).throw(RuntimeError('boom')),
    )

    ds = ButlerDataSource.__new__(ButlerDataSource)
    result = ds.get_query_builder_options_sync(
        repository_name='main',
        collection='LSSTCam/raw/all',
        dataset_type='difference_image',
    )

    assert result.collections == []
    assert result.dataset_types == []
    assert result.where_examples == []
