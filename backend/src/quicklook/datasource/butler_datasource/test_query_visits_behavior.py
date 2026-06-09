from types import SimpleNamespace
from typing import Any, cast

from quicklook.datasets import get_dataset
from quicklook.datasource.butler_datasource import ScopedButlerDataSource
from quicklook.datasource.types import Query


class FakeDimensionRecordResults:
    def __init__(self, records: list[Any]):
        self._records = records

    def order_by(self, *args: str):
        return self

    def limit(self, limit: int):
        return FakeDimensionRecordResults(self._records[:limit])

    def __iter__(self):
        return iter(self._records)

    def count(self, *, exact: bool = True, discard: bool = False):
        del exact, discard
        return len(self._records)


def _make_datasource(*, dataset_type: str, registry: object):
    ds = ScopedButlerDataSource.__new__(ScopedButlerDataSource)
    ds._repository_name = 'repo'
    ds._collection = 'LSSTCam/raw/all'
    ds._dataset_type = dataset_type
    ds._instrument = 'LSSTCam'
    ds._dataset = get_dataset(dataset_type)
    ds._butler = cast(Any, SimpleNamespace(registry=registry))
    return ds


def test_query_visits_does_not_apply_latest_day_filter_for_explicit_empty_where(monkeypatch):
    calls: list[tuple[str, dict[str, object]]] = []

    class FakeRegistry:
        def queryDimensionRecords(self, dimension: str, **kwargs: object):
            calls.append((dimension, kwargs))
            return FakeDimensionRecordResults([])

    ds = _make_datasource(dataset_type='raw', registry=FakeRegistry())
    monkeypatch.setattr(ds, '_get_latest_day_obs', lambda: 20250301)

    ds.query_visits(
        Query(
            repository_name='repo',
            collection='LSSTCam/raw/all',
            dataset_type='raw',
            where='',
            limit=5,
        )
    )

    assert calls == [
        (
            'exposure',
            {
                'datasets': 'raw',
            },
        )
    ]


def test_query_visits_reverse_flips_default_order(monkeypatch):
    order_calls: list[tuple[str, ...]] = []

    class TrackingResults(FakeDimensionRecordResults):
        def order_by(self, *args: str):
            order_calls.append(args)
            return self

    class FakeRegistry:
        def queryDimensionRecords(self, dimension: str, **kwargs: object):
            assert dimension == 'exposure'
            assert kwargs == {
                'datasets': 'raw',
                'where': 'day_obs=20250301',
            }
            return TrackingResults([])

    ds = _make_datasource(dataset_type='raw', registry=FakeRegistry())
    monkeypatch.setattr(ds, '_get_latest_day_obs', lambda: 20250301)

    ds.query_visits(
        Query(
            repository_name='repo',
            collection='LSSTCam/raw/all',
            dataset_type='raw',
            limit=5,
            reverse=True,
        )
    )

    assert order_calls == [('day_obs',)]


def test_query_visits_resolves_collection_from_dataset_run_when_collection_is_empty(monkeypatch):
    record = SimpleNamespace(
        id=2026012800342,
        day_obs=20260128,
        physical_filter='r_57',
        exposure_time=30.0,
        science_program='nightly',
        observation_type='science',
        observation_reason='survey',
        target_name='field-342',
        obs_id='obs-342',
    )

    class FakeRegistry:
        def queryDimensionRecords(self, dimension: str, **kwargs: object):
            assert dimension == 'exposure'
            assert kwargs == {
                'datasets': 'raw',
                'where': 'day_obs=20250301',
            }
            return FakeDimensionRecordResults([record])

    ds = _make_datasource(dataset_type='raw', registry=FakeRegistry())
    ds._collection = ''
    monkeypatch.setattr(ds, '_get_latest_day_obs', lambda: 20250301)
    monkeypatch.setattr(
        ds,
        '_query_datasets',
        lambda where, **kwargs: [SimpleNamespace(run='LSSTCam/raw/all')],
    )

    visits = ds.query_visits(
        Query(
            repository_name='repo',
            collection='',
            dataset_type='raw',
            limit=5,
        )
    )

    assert [visit.display_id for visit in visits] == [
        'repo:LSSTCam/raw/all:raw:exposure=2026012800342',
    ]
