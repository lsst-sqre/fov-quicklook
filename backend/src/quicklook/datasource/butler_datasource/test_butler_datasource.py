from types import SimpleNamespace
from typing import Any, cast

import lsst.daf.butler as butler_module

from quicklook.config import CcdDataTypeConfig
from quicklook.datasource.butler_datasource import (
    ButlerDataSource,
    DataTypeSpecificDataSource,
    Instrument,
    _clear_resolved_visit_run_cache,
    _get_resolved_visit_run,
    _resolve_visit_cache,
)
from quicklook.datasource.types import VisitDayCount, VisitResolutionError
from quicklook.datasource.types import Query
from quicklook.types import CcdDataRef, CcdDataType, CcdName, VisitName


class FakeDimensionRecordResults:
    def __init__(self, records: list[SimpleNamespace]):
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


def _make_datasource(*, data_type: str, data_id_dimension: str, order_by: list[str], registry: object):
    ds = DataTypeSpecificDataSource.__new__(DataTypeSpecificDataSource)
    ds._config = CcdDataTypeConfig(
        data_type=data_type,
        display_name=data_type,
        collections=['dummy'],
        data_id_dimension=data_id_dimension,
        order_by=order_by,
        partial=False,
        repository_name='repo',
        instrument='LSSTCam',
    )
    ds._butler = cast(Any, SimpleNamespace(registry=registry))
    return ds


def test_instruments():
    i = Instrument.get('LSSTComCam')
    assert i.name == 'LSSTComCam'
    assert i.detector_2_ccd[0] == 'R22_S00'
    assert i.ccd_2_detector[CcdName('R22_S00')] == 0
    assert i.detector_2_ccd[8] == 'R22_S22'
    assert i.ccd_2_detector[CcdName('R22_S22')] == 8


def test_query_visits_uses_exposure_dimension_records(monkeypatch):
    calls: list[tuple[str, dict[str, object]]] = []

    class FakeRegistry:
        def queryDimensionRecords(self, dimension: str, **kwargs: object):
            calls.append((dimension, kwargs))
            return FakeDimensionRecordResults([
                SimpleNamespace(
                    id=101,
                    obs_id='obs-101',
                    day_obs=20250301,
                    physical_filter='r',
                    exposure_time=30.0,
                    science_program='program-1',
                    observation_type='science',
                    observation_reason='test',
                    target_name='target-101',
                ),
                SimpleNamespace(
                    id=102,
                    obs_id='obs-102',
                    day_obs=20250301,
                    physical_filter='i',
                    exposure_time=31.0,
                    science_program='program-2',
                    observation_type='science',
                    observation_reason='test',
                    target_name='target-102',
                ),
            ])

    ds = _make_datasource(
        data_type='raw',
        data_id_dimension='exposure',
        order_by=['-day_obs', '-exposure'],
        registry=FakeRegistry(),
    )
    monkeypatch.setattr(ds, '_get_latest_day_obs', lambda: 20250301)

    entries = ds.query_visits(
        Query(
            data_type=CcdDataType('raw'),
            repository_name='repo',
            limit=5,
        )
    )

    assert calls == [
        (
            'exposure',
            {
                'datasets': 'raw',
                'where': 'day_obs=20250301',
            },
        )
    ]
    assert [entry.id for entry in entries] == ['repo:raw:101', 'repo:raw:102']


def test_query_visits_uses_configured_dimension_for_visit_dataset():
    calls: list[tuple[str, dict[str, object]]] = []

    class FakeRegistry:
        def queryDimensionRecords(self, dimension: str, **kwargs: object):
            calls.append((dimension, kwargs))
            return FakeDimensionRecordResults([
                SimpleNamespace(
                    id=7001,
                    obs_id='obs-7001',
                    day_obs=20250302,
                    physical_filter='z',
                    exposure_time=15.0,
                    science_program='program-visit',
                    observation_type='science',
                    observation_reason='nightly',
                    target_name='target-7001',
                )
            ])

    ds = _make_datasource(
        data_type='preliminary_visit_image',
        data_id_dimension='visit',
        order_by=['-visit'],
        registry=FakeRegistry(),
    )

    entries = ds.query_visits(
        Query(
            data_type=CcdDataType('preliminary_visit_image'),
            repository_name='repo',
            limit=1,
            exposure=7001,
            day_obs=20250302,
        )
    )

    assert calls == [
        (
            'visit',
            {
                'datasets': 'preliminary_visit_image',
                'where': 'visit=7001 and day_obs=20250302',
            },
        )
    ]
    assert [entry.id for entry in entries] == ['repo:preliminary_visit_image:7001']


def test_query_dimension_records_applies_order_and_limit_after_query():
    calls: list[tuple[str, dict[str, object]]] = []
    order_calls: list[tuple[str, ...]] = []
    limit_calls: list[int] = []

    class TrackingResults(FakeDimensionRecordResults):
        def order_by(self, *args: str):
            order_calls.append(args)
            return self

        def limit(self, limit: int):
            limit_calls.append(limit)
            return super().limit(limit)

    class FakeRegistry:
        def queryDimensionRecords(self, dimension: str, **kwargs: object):
            calls.append((dimension, kwargs))
            return TrackingResults([
                SimpleNamespace(
                    id=1,
                    obs_id='obs-1',
                    day_obs=20250303,
                    physical_filter='g',
                    exposure_time=10.0,
                    science_program='program',
                    observation_type='science',
                    observation_reason='test',
                    target_name='target-1',
                )
            ])

    ds = _make_datasource(
        data_type='raw',
        data_id_dimension='exposure',
        order_by=['-day_obs', '-exposure'],
        registry=FakeRegistry(),
    )

    records = ds._query_dimension_records(
        'exposure',
        datasets='raw',
        where='day_obs=20250303',
        limit=7,
        order_by=['-day_obs', '-exposure'],
    )

    assert [record.id for record in records] == [1]
    assert calls == [('exposure', {'datasets': 'raw', 'where': 'day_obs=20250303'})]
    assert order_calls == [('-day_obs', '-exposure')]
    assert limit_calls == [7]


def test_query_visit_day_counts_uses_butler_counts_by_day():
    calls: list[tuple[str, dict[str, object]]] = []

    class FakeRegistry:
        def queryDimensionRecords(self, dimension: str, **kwargs: object):
            calls.append((dimension, kwargs))
            if dimension == 'day_obs':
                return FakeDimensionRecordResults([
                    SimpleNamespace(id=20250301),
                    SimpleNamespace(id=20250303),
                ])
            if dimension == 'exposure' and kwargs == {'datasets': 'raw', 'where': 'day_obs=20250301'}:
                return FakeDimensionRecordResults([
                    SimpleNamespace(id=101),
                    SimpleNamespace(id=102),
                ])
            if dimension == 'exposure' and kwargs == {'datasets': 'raw', 'where': 'day_obs=20250303'}:
                return FakeDimensionRecordResults([SimpleNamespace(id=103)])
            raise AssertionError((dimension, kwargs))

    ds = _make_datasource(
        data_type='raw',
        data_id_dimension='exposure',
        order_by=['-day_obs', '-exposure'],
        registry=FakeRegistry(),
    )

    counts = ds.query_visit_day_counts('2025-03')

    assert counts == [
        VisitDayCount(day_obs=20250301, count=2),
        VisitDayCount(day_obs=20250303, count=1),
    ]
    assert calls == [
        (
            'day_obs',
            {
                'datasets': 'raw',
                'where': 'day_obs>=20250301 and day_obs<20250401',
            },
        ),
        ('exposure', {'datasets': 'raw', 'where': 'day_obs=20250301'}),
        ('exposure', {'datasets': 'raw', 'where': 'day_obs=20250303'}),
    ]


def test_resolve_visit_sync_uses_uuid_to_select_configured_dataset(monkeypatch):
    _resolve_visit_cache.cache_clear()
    _clear_resolved_visit_run_cache()

    class ResolverRegistry:
        def getDataset(self, dataset_uuid):
            assert str(dataset_uuid) == '726a5858-33d0-5d75-ab98-ea273c4c3792'
            return SimpleNamespace(
                datasetType=SimpleNamespace(name='raw'),
                dataId={'exposure': 4242},
                run='u/test/raw-run',
            )

    resolver_ds = _make_datasource(
        data_type='raw',
        data_id_dimension='exposure',
        order_by=['-exposure'],
        registry=ResolverRegistry(),
    )
    target_ds = _make_datasource(
        data_type='raw',
        data_id_dimension='exposure',
        order_by=['-exposure'],
        registry=object(),
    )

    monkeypatch.setattr(
        'quicklook.datasource.butler_datasource._get_repository_butler',
        lambda repository_name: cast(Any, SimpleNamespace(registry=resolver_ds._butler.registry)),
    )
    monkeypatch.setattr(
        'quicklook.datasource.butler_datasource._get_datasource',
        lambda data_type, repository_name: target_ds,
    )

    ds = ButlerDataSource.__new__(ButlerDataSource)
    visit = ds.resolve_visit_sync(VisitName('repo:by_uuid:726a5858-33d0-5d75-ab98-ea273c4c3792'))
    resolved = ds.resolve_visit_info_sync(VisitName('repo:by_uuid:726a5858-33d0-5d75-ab98-ea273c4c3792'))

    assert visit == VisitName('repo:raw:4242')
    assert resolved.visit_name == VisitName('repo:raw:4242')
    assert resolved.detector is None


def test_resolve_visit_sync_supports_difference_image_dataset_type(monkeypatch):
    _resolve_visit_cache.cache_clear()
    _clear_resolved_visit_run_cache()

    class ResolverRegistry:
        def getDataset(self, dataset_uuid):
            assert str(dataset_uuid) == '019bbefe-465a-7815-a05c-13dc47a78418'
            return SimpleNamespace(
                datasetType=SimpleNamespace(name='difference_image'),
                dataId={'visit': 9876, 'detector': 90},
                run='u/test/difference-run',
            )

    target_ds = _make_datasource(
        data_type='difference_image',
        data_id_dimension='visit',
        order_by=['-visit'],
        registry=object(),
    )

    monkeypatch.setattr(
        'quicklook.datasource.butler_datasource._get_repository_butler',
        lambda repository_name: cast(Any, SimpleNamespace(registry=ResolverRegistry())),
    )
    monkeypatch.setattr(
        'quicklook.datasource.butler_datasource._get_datasource',
        lambda data_type, repository_name: target_ds,
    )

    ds = ButlerDataSource.__new__(ButlerDataSource)
    visit = ds.resolve_visit_sync(VisitName('embargo:by_uuid:019bbefe-465a-7815-a05c-13dc47a78418'))
    resolved = ds.resolve_visit_info_sync(VisitName('embargo:by_uuid:019bbefe-465a-7815-a05c-13dc47a78418'))

    assert visit == VisitName('embargo:difference_image:9876')
    assert _get_resolved_visit_run(visit) == 'u/test/difference-run'
    assert resolved.detector == 90


def test_get_repository_butler_cache_uses_repository_only(monkeypatch):
    from quicklook.datasource.butler_datasource import _get_repository_butler_cache

    _get_repository_butler_cache.cache_clear()
    calls: list[tuple[tuple[object, ...], dict[str, object]]] = []

    def fake_butler(*args: object, **kwargs: object):
        calls.append((args, kwargs))
        return object()

    monkeypatch.setattr(butler_module, 'Butler', fake_butler)

    _get_repository_butler_cache('main', thread_id=1)

    assert calls == [(('main',), {})]


def test_get_metadata_sync_resolves_by_uuid_before_delegating(monkeypatch):
    resolved_visit = VisitName('repo:raw:4242')
    expected_metadata = SimpleNamespace(visit_name=resolved_visit)
    captured_refs: list[CcdDataRef] = []

    class TargetDataSource:
        def get_metadata(self, ref: CcdDataRef):
            captured_refs.append(ref)
            return expected_metadata

    monkeypatch.setattr(ButlerDataSource, 'resolve_visit_sync', lambda self, visit: resolved_visit)
    monkeypatch.setattr(
        'quicklook.datasource.butler_datasource._get_datasource',
        lambda data_type, repository_name: TargetDataSource(),
    )

    ds = ButlerDataSource.__new__(ButlerDataSource)
    metadata = ds.get_metadata_sync(CcdDataRef(VisitName('repo:by_uuid:uuid-1'), CcdName('R22_S00')))

    assert metadata is expected_metadata
    assert captured_refs == [CcdDataRef(visit=resolved_visit, ccd=CcdName('R22_S00'))]


def test_list_ccds_excludes_corner_rafts_for_difference_image(monkeypatch):
    _clear_resolved_visit_run_cache()
    captured: dict[str, object] = {}

    class FakeRegistry:
        def queryDatasets(self, dataset_type: str, **kwargs: object):
            captured['dataset_type'] = dataset_type
            captured.update(kwargs)
            return [
                SimpleNamespace(dataId={'detector': 1}),
                SimpleNamespace(dataId={'detector': 2}),
            ]

    ds = _make_datasource(
        data_type='difference_image',
        data_id_dimension='visit',
        order_by=['-visit'],
        registry=FakeRegistry(),
    )
    monkeypatch.setattr(
        'quicklook.datasource.butler_datasource.Instrument.get',
        lambda instrument: SimpleNamespace(detector_2_ccd={1: 'R00_S00', 2: 'R22_S00'}),
    )

    ccds = ds.list_ccds(VisitName('repo:difference_image:42'))

    assert ccds == [CcdName('R22_S00')]
    assert captured == {
        'dataset_type': 'difference_image',
        'collections': ...,
        'where': 'visit=42',
    }


def test_query_visits_difference_image_uses_all_run_collections():
    calls: list[tuple[str, dict[str, object]]] = []

    class FakeRegistry:
        def queryDimensionRecords(self, dimension: str, **kwargs: object):
            calls.append((dimension, kwargs))
            return FakeDimensionRecordResults([
                SimpleNamespace(
                    id=7001,
                    obs_id='obs-7001',
                    day_obs=20250302,
                    physical_filter='z',
                    exposure_time=15.0,
                    science_program='program-visit',
                    observation_type='science',
                    observation_reason='nightly',
                    target_name='target-7001',
                )
            ])

    ds = _make_datasource(
        data_type='difference_image',
        data_id_dimension='visit',
        order_by=['-visit'],
        registry=FakeRegistry(),
    )

    entries = ds.query_visits(
        Query(
            data_type=CcdDataType('difference_image'),
            repository_name='repo',
            limit=1,
            exposure=7001,
            day_obs=20250302,
        )
    )

    assert calls == [
        (
            'visit',
            {
                'datasets': 'difference_image',
                'collections': ...,
                'where': 'visit=7001 and day_obs=20250302',
            },
        )
    ]
    assert [entry.id for entry in entries] == ['repo:difference_image:7001']


def test_query_visits_difference_image_falls_back_when_visit_record_lacks_obs_id():
    class FakeRegistry:
        def queryDimensionRecords(self, dimension: str, **kwargs: object):
            del dimension, kwargs
            return FakeDimensionRecordResults([
                SimpleNamespace(
                    id=7001,
                    day_obs=20250302,
                    band='z',
                )
            ])

    ds = _make_datasource(
        data_type='difference_image',
        data_id_dimension='visit',
        order_by=['-visit'],
        registry=FakeRegistry(),
    )

    [entry] = ds.query_visits(
        Query(
            data_type=CcdDataType('difference_image'),
            repository_name='repo',
            limit=1,
            exposure=7001,
            day_obs=20250302,
        )
    )

    assert entry.id == 'repo:difference_image:7001'
    assert entry.obs_id == '7001'
    assert entry.day_obs == 20250302
    assert entry.physical_filter == 'z'
    assert entry.exposure_time == 0.0
    assert entry.science_program == ''
    assert entry.observation_type == ''
    assert entry.observation_reason == ''
    assert entry.target_name == ''


def test_list_ccds_uses_resolved_run_for_difference_image(monkeypatch):
    _clear_resolved_visit_run_cache()
    captured: dict[str, object] = {}

    class FakeRegistry:
        def queryDatasets(self, dataset_type: str, **kwargs: object):
            captured['dataset_type'] = dataset_type
            captured.update(kwargs)
            return [SimpleNamespace(dataId={'detector': 2})]

    ds = _make_datasource(
        data_type='difference_image',
        data_id_dimension='visit',
        order_by=['-visit'],
        registry=FakeRegistry(),
    )
    visit = VisitName('repo:difference_image:42')
    monkeypatch.setattr(
        'quicklook.datasource.butler_datasource.Instrument.get',
        lambda instrument: SimpleNamespace(detector_2_ccd={2: 'R22_S00'}),
    )

    monkeypatch.setattr(
        'quicklook.datasource.butler_datasource._get_resolved_visit_run',
        lambda arg_visit: 'u/test/run' if arg_visit == visit else None,
    )

    ccds = ds.list_ccds(visit)

    assert ccds == [CcdName('R22_S00')]
    assert captured == {
        'dataset_type': 'difference_image',
        'collections': ['u/test/run'],
        'where': 'visit=42',
    }


def test_resolve_visit_sync_raises_visit_resolution_error_for_unknown_uuid(monkeypatch):
    _resolve_visit_cache.cache_clear()
    _clear_resolved_visit_run_cache()

    class ResolverRegistry:
        def getDataset(self, dataset_uuid):
            del dataset_uuid
            return None

    monkeypatch.setattr(
        'quicklook.datasource.butler_datasource._get_repository_butler',
        lambda repository_name: cast(Any, SimpleNamespace(registry=ResolverRegistry())),
    )

    ds = ButlerDataSource.__new__(ButlerDataSource)

    try:
        ds.resolve_visit_sync(VisitName('repo:by_uuid:726a5858-33d0-5d75-ab98-ea273c4c3792'))
    except VisitResolutionError as e:
        assert str(e) == 'Unknown dataset UUID: 726a5858-33d0-5d75-ab98-ea273c4c3792'
    else:  # pragma: no cover
        raise AssertionError('VisitResolutionError was not raised')


def test_resolve_visit_sync_raises_visit_resolution_error_for_unsupported_dataset_type(monkeypatch):
    _resolve_visit_cache.cache_clear()
    _clear_resolved_visit_run_cache()

    class ResolverRegistry:
        def getDataset(self, dataset_uuid):
            del dataset_uuid
            return SimpleNamespace(
                datasetType=SimpleNamespace(name='unsupported_image'),
                dataId={'visit': 1234},
            )

    monkeypatch.setattr(
        'quicklook.datasource.butler_datasource._get_repository_butler',
        lambda repository_name: cast(Any, SimpleNamespace(registry=ResolverRegistry())),
    )

    ds = ButlerDataSource.__new__(ButlerDataSource)

    try:
        ds.resolve_visit_sync(VisitName('embargo:by_uuid:019bbefe-465a-7815-a05c-13dc47a78418'))
    except VisitResolutionError as e:
        assert (
            str(e)
            == 'UUID 019bbefe-465a-7815-a05c-13dc47a78418 resolves to unsupported dataset type unsupported_image in repository embargo'
        )
    else:  # pragma: no cover
        raise AssertionError('VisitResolutionError was not raised')
