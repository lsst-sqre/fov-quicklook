from types import SimpleNamespace

from fastapi import HTTPException

from quicklook.datasource.types import MonthlyEntryCountQuery, ResolvedVisitInfo, VisitDayCount, VisitResolutionError
from quicklook.frontend.api import visits
from quicklook.types import CcdDataType, VisitName


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
                visit_name=VisitName('repo:raw:4242'),
                detector=90,
            )

    monkeypatch.setattr(visits, 'get_datasource', lambda: FakeDataSource())

    resolved = await visits.get_visit_resolution('repo:by_uuid:uuid-1')

    assert resolved == ResolvedVisitInfo(
        visit_name=VisitName('repo:raw:4242'),
        detector=90,
    )


async def test_list_visit_monthly_counts_delegates_to_datasource(monkeypatch):
    captured_queries: list[MonthlyEntryCountQuery] = []

    class FakeDataSource:
        async def query_monthly_entry_counts(self, q: MonthlyEntryCountQuery) -> list[VisitDayCount]:
            captured_queries.append(q)
            return [VisitDayCount(day_obs=20250301, count=4)]

    monkeypatch.setattr(visits, 'get_datasource', lambda: FakeDataSource())

    result = await visits.list_visit_monthly_counts(
        year=2025,
        month=3,
        data_type=CcdDataType('raw'),
        repository_name='repo',
    )

    assert result == [VisitDayCount(day_obs=20250301, count=4)]
    assert captured_queries == [
        MonthlyEntryCountQuery(
            data_type=CcdDataType('raw'),
            repository_name='repo',
            year=2025,
            month=3,
        )
    ]
