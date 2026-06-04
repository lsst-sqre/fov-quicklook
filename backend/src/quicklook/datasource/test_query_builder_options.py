import sys
from types import SimpleNamespace

from lsst.daf.butler._exceptions import MissingCollectionError, MissingDatasetTypeError

from quicklook.datasource import butler_datasource as butler_datasource_module
from quicklook.datasource.butler_datasource import ButlerDataSource


def test_build_contains_glob():
    assert butler_datasource_module._build_contains_glob('nightly') == '*nightly*'


def test_butler_datasource_init_does_not_trigger_query_builder_lookup(monkeypatch):
    calls: list[str] = []
    monkeypatch.setitem(
        sys.modules,
        'quicklook.datasource.butler_datasource.butlerutils',
        SimpleNamespace(chown_pgpassfile=lambda: calls.append('chown')),
    )

    ButlerDataSource()

    assert calls == ['chown']


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


def test_get_query_builder_options_keeps_exact_selection_only(monkeypatch):
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


def test_get_query_builder_options_filters_partial_collection_with_direct_query(monkeypatch):
    monkeypatch.setattr(butler_datasource_module, '_query_repository_names', lambda: ['main'])
    monkeypatch.setattr(
        butler_datasource_module,
        '_query_collections_for_repository',
        lambda repository_name, *, search_text=None: (
            ['LSSTCam/runs/nightlyValidation/10'] if repository_name == 'main' and search_text == 'nightly' else []
        ),
    )
    monkeypatch.setattr(
        butler_datasource_module,
        '_query_dataset_types_for_repository',
        lambda repository_name, *, search_text=None: [],
    )

    ds = ButlerDataSource.__new__(ButlerDataSource)
    result = ds.get_query_builder_options_sync(repository_name='main', collection='nightly')

    assert result.collections == ['LSSTCam/runs/nightlyValidation/10']
    assert result.dataset_types == []
    assert result.where_examples == []


def test_get_query_builder_options_does_not_short_circuit_partial_dataset_type(monkeypatch):
    monkeypatch.setattr(butler_datasource_module, '_query_repository_names', lambda: ['main'])
    monkeypatch.setattr(
        butler_datasource_module,
        '_query_collections_for_repository',
        lambda repository_name, *, search_text=None: (
            ['LSSTCam/runs/nightlyValidation/10']
            if repository_name == 'main' and search_text == 'LSSTCam/runs/nightlyValidation/10'
            else []
        ),
    )
    monkeypatch.setattr(
        butler_datasource_module,
        '_query_dataset_types_for_repository',
        lambda repository_name, *, search_text=None: (
            ['preliminary_visit_image'] if repository_name == 'main' and search_text == 'prelim' else []
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


def test_query_builder_helpers_fall_back_to_empty_list(monkeypatch):
    monkeypatch.setattr(butler_datasource_module, '_repository_instrument', lambda repository_name: 'LSSTCam')
    monkeypatch.setattr(
        butler_datasource_module,
        '_query_collections_for_repository_cache',
        lambda repository_name, instrument, search_text, thread_id: (_ for _ in ()).throw(RuntimeError('boom')),
    )

    assert butler_datasource_module._query_collections_for_repository('main', search_text='raw') == []


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
