import sys
from types import SimpleNamespace

import sqlalchemy

from quicklook.datasource import butler_datasource as butler_datasource_module
from quicklook.datasource.butler_datasource import ButlerDataSource


def test_limit_query_builder_suggestions_marks_truncation():
    result = butler_datasource_module._limit_query_builder_suggestions(tuple(f"collection-{index}" for index in range(101)))

    assert len(result.values) == 100
    assert result.values[0] == "collection-0"
    assert result.values[-1] == "collection-99"
    assert result.truncated is True


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

    def fake_query_collections(*args: object, **kwargs: object):
        del args
        nonlocal collections_called
        collections_called = True
        assert kwargs == {'search_text': None}
        return butler_datasource_module._QueryBuilderSuggestionResult(())

    def fake_query_dataset_types(*args: object, **kwargs: object):
        del args
        nonlocal dataset_types_called
        dataset_types_called = True
        assert kwargs == {'search_text': None}
        return butler_datasource_module._QueryBuilderSuggestionResult(())

    monkeypatch.setattr(butler_datasource_module, '_query_collections_for_repository_result', fake_query_collections)
    monkeypatch.setattr(butler_datasource_module, '_query_dataset_types_for_collection', fake_query_dataset_types)

    ds = ButlerDataSource.__new__(ButlerDataSource)
    result = ds.get_query_builder_options_sync(repository_name='main')

    assert result.repositories == ['embargo', 'main']
    assert result.collections == []
    assert result.dataset_types == []
    assert result.collections_truncated is False
    assert result.dataset_types_truncated is False
    assert result.where_examples == []
    assert collections_called is True
    assert dataset_types_called is True


def test_get_query_builder_options_keeps_exact_selection_only(monkeypatch):
    monkeypatch.setattr(butler_datasource_module, '_query_repository_names', lambda: ['main'])
    monkeypatch.setattr(
        butler_datasource_module,
        '_query_collections_for_repository_result',
        lambda repository_name, *, search_text=None: (_ for _ in ()).throw(
            AssertionError(f'_query_collections_for_repository_result should not be called: {repository_name}, {search_text}')
        ),
    )
    monkeypatch.setattr(
        butler_datasource_module,
        '_query_dataset_types_for_collection',
        lambda repository_name, collection, *, search_text=None: (_ for _ in ()).throw(
            AssertionError(
                f'_query_dataset_types_for_collection should not be called: {repository_name}, {collection}, {search_text}'
            )
        ),
    )
    monkeypatch.setattr(
        butler_datasource_module,
        '_collection_exists_for_repository',
        lambda repository_name, collection: repository_name == 'main' and collection == 'LSSTCam/raw/all',
    )
    monkeypatch.setattr(
        butler_datasource_module,
        '_dataset_type_exists_for_collection',
        lambda repository_name, collection, dataset_type: (
            repository_name == 'main' and collection == 'LSSTCam/raw/all' and dataset_type == 'raw'
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
    assert result.where_examples == []


def test_get_query_builder_options_filters_partial_collection_with_direct_query(monkeypatch):
    monkeypatch.setattr(butler_datasource_module, '_query_repository_names', lambda: ['main'])
    monkeypatch.setattr(
        butler_datasource_module,
        '_query_collections_for_repository_result',
        lambda repository_name, *, search_text=None: (
            butler_datasource_module._QueryBuilderSuggestionResult(('LSSTCam/runs/nightlyValidation/10',), truncated=True)
            if repository_name == 'main' and search_text == 'nightly'
            else butler_datasource_module._QueryBuilderSuggestionResult(())
        ),
    )
    monkeypatch.setattr(
        butler_datasource_module,
        '_query_dataset_types_for_collection',
        lambda repository_name, collection, *, search_text=None: butler_datasource_module._QueryBuilderSuggestionResult(()),
    )

    ds = ButlerDataSource.__new__(ButlerDataSource)
    result = ds.get_query_builder_options_sync(repository_name='main', collection='nightly')

    assert result.collections == ['LSSTCam/runs/nightlyValidation/10']
    assert result.collections_truncated is True
    assert result.dataset_types == []
    assert result.where_examples == []


def test_get_query_builder_options_does_not_short_circuit_partial_dataset_type(monkeypatch):
    monkeypatch.setattr(butler_datasource_module, '_query_repository_names', lambda: ['main'])
    monkeypatch.setattr(
        butler_datasource_module,
        '_collection_exists_for_repository',
        lambda repository_name, collection: repository_name == 'main' and collection == 'LSSTCam/runs/nightlyValidation/10',
    )
    monkeypatch.setattr(
        butler_datasource_module,
        '_query_collections_for_repository_result',
        lambda repository_name, *, search_text=None: (
            butler_datasource_module._QueryBuilderSuggestionResult(('LSSTCam/runs/nightlyValidation/10',))
            if repository_name == 'main' and search_text == 'LSSTCam/runs/nightlyValidation/10'
            else butler_datasource_module._QueryBuilderSuggestionResult(())
        ),
    )
    monkeypatch.setattr(
        butler_datasource_module,
        '_query_dataset_types_for_collection',
        lambda repository_name, collection, *, search_text=None: (
            butler_datasource_module._QueryBuilderSuggestionResult(('preliminary_visit_image',))
            if repository_name == 'main' and collection == 'LSSTCam/runs/nightlyValidation/10' and search_text == 'prelim'
            else butler_datasource_module._QueryBuilderSuggestionResult(())
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


def test_query_builder_helpers_fall_back_to_empty_result(monkeypatch):
    monkeypatch.setattr(butler_datasource_module, '_repository_instrument', lambda repository_name: 'LSSTCam')
    monkeypatch.setattr(
        butler_datasource_module,
        '_query_collections_for_repository_cache',
        lambda repository_name, instrument, search_text, thread_id: (_ for _ in ()).throw(RuntimeError('boom')),
    )

    assert butler_datasource_module._query_collections_for_repository_result('main', search_text='raw') == (
        butler_datasource_module._QueryBuilderSuggestionResult(())
    )


def test_collection_exists_for_repository_returns_false_when_sql_query_is_empty(monkeypatch):
    collection_table = sqlalchemy.table('collection', sqlalchemy.column('name'))

    class FakeConnection:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def execute(self, sql):
            del sql
            return SimpleNamespace(scalar_one_or_none=lambda: None)

    monkeypatch.setattr(
        butler_datasource_module,
        '_get_query_repository_butler',
        lambda repository_name, instrument: SimpleNamespace(registry=object()),
    )
    monkeypatch.setattr(
        butler_datasource_module,
        '_get_sql_registry',
        lambda registry: SimpleNamespace(
            _managers=SimpleNamespace(
                collections=SimpleNamespace(_tables=SimpleNamespace(collection=collection_table)),
            ),
        ),
    )
    monkeypatch.setattr(butler_datasource_module, '_get_db_connection', lambda registry: FakeConnection())

    assert butler_datasource_module._collection_exists_for_repository_cache(
        'embargo',
        'LSSTCam',
        'nightly',
        thread_id=1001,
    ) is False


def test_dataset_type_exists_for_collection_returns_false_when_sql_query_is_empty(monkeypatch):
    dataset_type_table = sqlalchemy.table('dataset_type', sqlalchemy.column('name'), sqlalchemy.column('id'))
    summary_table = sqlalchemy.table(
        'collection_summary_dataset_type',
        sqlalchemy.column('dataset_type_id'),
        sqlalchemy.column('collection_id'),
    )
    collection_table = sqlalchemy.table('collection', sqlalchemy.column('name'), sqlalchemy.column('collection_id'))

    class FakeConnection:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def execute(self, sql):
            del sql
            return SimpleNamespace(scalar_one_or_none=lambda: None)

    monkeypatch.setattr(
        butler_datasource_module,
        '_get_query_repository_butler',
        lambda repository_name, instrument: SimpleNamespace(registry=object()),
    )
    monkeypatch.setattr(butler_datasource_module, '_is_query_builder_dataset_type', lambda *args: True)
    monkeypatch.setattr(
        butler_datasource_module,
        '_get_sql_registry',
        lambda registry: SimpleNamespace(
            _managers=SimpleNamespace(
                datasets=SimpleNamespace(
                    _static=SimpleNamespace(dataset_type=dataset_type_table),
                    _summaries=SimpleNamespace(
                        _tables=SimpleNamespace(datasetType=summary_table),
                        _collectionKeyName='collection_id',
                    ),
                ),
                collections=SimpleNamespace(
                    _tables=SimpleNamespace(collection=collection_table),
                    _collectionIdName='collection_id',
                ),
            ),
        ),
    )
    monkeypatch.setattr(butler_datasource_module, '_get_db_connection', lambda registry: FakeConnection())

    assert butler_datasource_module._dataset_type_exists_for_collection_cache(
        'embargo',
        'LSSTCam',
        'LSSTCam/raw/all',
        'raw',
        thread_id=1002,
    ) is False
