from fastapi import HTTPException
from lsst.daf.butler._exceptions import MissingCollectionError

from quicklook.datasource.types import (
    QueryBuilderOptions,
    QueryWhereExample,
    ResolvedVisitInfo,
    VisitDayCount,
    VisitRepresentativeUuid,
    VisitResolutionError,
)
from quicklook.frontend.api import visits
from quicklook.types import VisitName


async def test_list_visits_forwards_limit_and_offset(monkeypatch):
    captured = {}

    class FakeDataSource:
        async def query_visits(self, q):
            captured["query"] = q
            return []

    monkeypatch.setattr(visits, 'get_datasource', lambda: FakeDataSource())

    result = await visits.list_visits(
        repository_name='repo',
        collection='LSSTCam/raw/all',
        dataset_type='raw',
        where='day_obs=20250301',
        order_by='day_obs',
        reverse=True,
        limit=1000,
        offset=1000,
    )

    assert result == []
    assert captured["query"].repository_name == 'repo'
    assert captured["query"].collection == 'LSSTCam/raw/all'
    assert captured["query"].dataset_type == 'raw'
    assert captured["query"].limit == 1000
    assert captured["query"].offset == 1000
    assert captured["query"].where == 'day_obs=20250301'
    assert captured["query"].order_by == 'day_obs'
    assert captured["query"].reverse is True


async def test_get_query_builder_options_forwards_filters(monkeypatch):
    captured = {}

    async def fake_http_request(method: str, url: str, **kwargs):
        captured["request"] = (method, url, kwargs)
        return QueryBuilderOptions(
            repositories=['repo'],
            collections=['LSSTCam/raw/all'],
            dataset_types=['raw'],
            where_examples=[QueryWhereExample(label='Latest day_obs', where='day_obs=20250301')],
            collections_truncated=False,
            dataset_types_truncated=False,
        )

    monkeypatch.setattr(visits, 'http_request', fake_http_request)
    monkeypatch.setattr(visits.config, 'coordinator_base_url', 'http://coordinator:9501')

    result = await visits.get_query_builder_options(
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
    assert captured["request"] == (
        'get',
        'http://coordinator:9501/query_builder_options?repository_name=repo&collection=LSSTCam%2Fraw%2Fall&dataset_type=raw',
        {},
    )


async def test_list_visits_rejects_unsafe_where(monkeypatch):
    class FakeDataSource:
        async def query_visits(self, q):  # pragma: no cover
            del q
            raise AssertionError('query_visits should not be called')

    monkeypatch.setattr(visits, 'get_datasource', lambda: FakeDataSource())

    try:
        await visits.list_visits(
            repository_name='repo',
            collection='LSSTCam/raw/all',
            dataset_type='raw',
            where='day_obs=20250301;\nselect * from visits',
            order_by=None,
            reverse=None,
            limit=100,
            offset=0,
        )
    except HTTPException as e:
        assert e.status_code == 422
        assert e.detail == "where must not contain control characters or ';'."
    else:  # pragma: no cover
        raise AssertionError('HTTPException was not raised')


async def test_list_visits_treats_literal_null_where_as_absent(monkeypatch):
    captured = {}

    class FakeDataSource:
        async def query_visits(self, q):
            captured["query"] = q
            return []

    monkeypatch.setattr(visits, 'get_datasource', lambda: FakeDataSource())

    result = await visits.list_visits(
        repository_name='repo',
        collection='LSSTCam/raw/all',
        dataset_type='raw',
        where='null',
        order_by='null',
        reverse=None,
        limit=100,
        offset=0,
    )

    assert result == []
    assert captured["query"].where is None
    assert captured["query"].order_by is None


async def test_list_visits_keeps_explicit_empty_where(monkeypatch):
    captured = {}

    class FakeDataSource:
        async def query_visits(self, q):
            captured["query"] = q
            return []

    monkeypatch.setattr(visits, 'get_datasource', lambda: FakeDataSource())

    result = await visits.list_visits(
        repository_name='repo',
        collection='LSSTCam/raw/all',
        dataset_type='raw',
        where='',
        order_by='day_obs',
        reverse=None,
        limit=100,
        offset=0,
    )

    assert result == []
    assert captured["query"].where == ''
    assert captured["query"].order_by == 'day_obs'


async def test_list_visits_rejects_unknown_order_by(monkeypatch):
    class FakeDataSource:
        async def query_visits(self, q):  # pragma: no cover
            del q
            raise AssertionError('query_visits should not be called')

    monkeypatch.setattr(visits, 'get_datasource', lambda: FakeDataSource())

    try:
        await visits.list_visits(
            repository_name='repo',
            collection='LSSTCam/raw/all',
            dataset_type='raw',
            where=None,
            order_by='drop_table',
            reverse=None,
            limit=100,
            offset=0,
        )
    except HTTPException as e:
        assert e.status_code == 422
        assert 'order_by must be one of:' in e.detail
    else:  # pragma: no cover
        raise AssertionError('HTTPException was not raised')


async def test_list_visits_returns_422_for_unknown_collection(monkeypatch):
    class FakeDataSource:
        async def query_visits(self, q):
            del q
            raise MissingCollectionError("No collection with name 'nightlyValidation/raw/all' found.")

    monkeypatch.setattr(visits, 'get_datasource', lambda: FakeDataSource())

    try:
        await visits.list_visits(
            repository_name='repo',
            collection='nightlyValidation/raw/all',
            dataset_type='raw',
            where=None,
            order_by='day_obs',
            reverse=None,
            limit=100,
            offset=0,
        )
    except HTTPException as e:
        assert e.status_code == 422
        assert e.detail == "No collection with name 'nightlyValidation/raw/all' found."
    else:  # pragma: no cover
        raise AssertionError('HTTPException was not raised')


async def test_get_visit_metadata_returns_404_for_unknown_uuid(monkeypatch):
    class FakeDataSource:
        async def get_metadata(self, ref):
            del ref
            raise VisitResolutionError('Unknown dataset UUID: uuid-1')

    monkeypatch.setattr(visits, 'get_datasource', lambda: FakeDataSource())

    try:
        await visits.get_visit_metadata('repo:by_uuid:uuid-1', 'R22_S00')
    except HTTPException as e:
        assert e.status_code == 404
        assert e.detail == 'Unknown dataset UUID: uuid-1'
    else:  # pragma: no cover
        raise AssertionError('HTTPException was not raised')


async def test_get_visit_resolution_returns_detector(monkeypatch):
    class FakeDataSource:
        async def resolve_visit_info(self, visit: VisitName) -> ResolvedVisitInfo:
            assert visit == VisitName('repo:by_uuid:uuid-1')
            return ResolvedVisitInfo(
                visit_name=VisitName('repo:LSSTCam!-raw!-all:raw:exposure=4242'),
                detector=90,
            )

    monkeypatch.setattr(visits, 'get_datasource', lambda: FakeDataSource())

    resolved = await visits.get_visit_resolution('repo:by_uuid:uuid-1')

    assert resolved == ResolvedVisitInfo(
        visit_name=VisitName('repo:LSSTCam!-raw!-all:raw:exposure=4242'),
        detector=90,
    )


async def test_get_visit_representative_uuid_returns_uuid(monkeypatch):
    class FakeDataSource:
        async def get_visit_representative_uuid(self, visit: VisitName) -> str:
            assert visit == VisitName('repo:LSSTCam!-raw!-all:raw:exposure=4242')
            return 'uuid-4242'

    monkeypatch.setattr(visits, 'get_datasource', lambda: FakeDataSource())

    representative = await visits.get_visit_representative_uuid('repo:LSSTCam!-raw!-all:raw:exposure=4242')

    assert representative == VisitRepresentativeUuid(uuid='uuid-4242')


async def test_list_visit_day_counts_returns_backend_counts(monkeypatch):
    class FakeDataSource:
        async def query_visit_day_counts(self, q):
            assert q.calendar_month == '2025-03'
            assert q.repository_name == 'repo'
            assert q.collection == 'LSSTCam/raw/all'
            assert q.dataset_type == 'raw'
            return [
                VisitDayCount(day_obs=20250301, count=2),
                VisitDayCount(day_obs=20250302, count=5),
            ]

    monkeypatch.setattr(visits, 'get_datasource', lambda: FakeDataSource())

    counts = await visits.list_visit_day_counts(
        calendar_month='2025-03',
        repository_name='repo',
        collection='LSSTCam/raw/all',
        dataset_type='raw',
    )

    assert counts == [
        VisitDayCount(day_obs=20250301, count=2),
        VisitDayCount(day_obs=20250302, count=5),
    ]


async def test_list_visit_day_counts_returns_422_for_unknown_collection(monkeypatch):
    class FakeDataSource:
        async def query_visit_day_counts(self, q):
            del q
            raise MissingCollectionError("No collection with name 'nightlyValidation/raw/all' found.")

    monkeypatch.setattr(visits, 'get_datasource', lambda: FakeDataSource())

    try:
        await visits.list_visit_day_counts(
            calendar_month='2025-03',
            repository_name='repo',
            collection='nightlyValidation/raw/all',
            dataset_type='raw',
        )
    except HTTPException as e:
        assert e.status_code == 422
        assert e.detail == "No collection with name 'nightlyValidation/raw/all' found."
    else:  # pragma: no cover
        raise AssertionError('HTTPException was not raised')
