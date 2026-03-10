from types import SimpleNamespace

from quicklook.config import CcdDataTypeConfig
from quicklook.datasource.butler_datasource import DataTypeSpecificDataSource, Instrument
from quicklook.datasource.types import Query
from quicklook.types import CcdDataType, CcdName


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
    ds._butler = SimpleNamespace(registry=registry)
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
            return [
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
            ]

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
                'limit': 5,
                'order_by': ['-day_obs', '-exposure'],
            },
        )
    ]
    assert [entry.id for entry in entries] == ['repo:raw:101', 'repo:raw:102']


def test_query_visits_uses_configured_dimension_for_visit_dataset():
    calls: list[tuple[str, dict[str, object]]] = []

    class FakeRegistry:
        def queryDimensionRecords(self, dimension: str, **kwargs: object):
            calls.append((dimension, kwargs))
            return [
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
            ]

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
                'limit': 1,
                'order_by': ['-visit'],
            },
        )
    ]
    assert [entry.id for entry in entries] == ['repo:preliminary_visit_image:7001']
