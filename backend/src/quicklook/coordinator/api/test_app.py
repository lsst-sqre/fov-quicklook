from fastapi import HTTPException

from types import SimpleNamespace

from quicklook.coordinator.api import app as app_module
from quicklook.coordinator.api.types import CreateQuicklookRequest
from quicklook.datasource.types import VisitResolutionError
from quicklook.types import VisitName


class _FakeSession:
    async def execute(self, stmt):
        del stmt
        return SimpleNamespace(scalar_one_or_none=lambda: None)


class _FakeSessionContext:
    async def __aenter__(self):
        return _FakeSession()

    async def __aexit__(self, exc_type, exc, tb):
        del exc_type, exc, tb
        return False


async def test_route_create_quicklook_resolves_visit_before_queueing(monkeypatch):
    resolved_visits: list[VisitName] = []
    pushed_visits: list[VisitName] = []

    class FakeDataSource:
        async def resolve_visit(self, visit: VisitName) -> VisitName:
            resolved_visits.append(visit)
            return VisitName('repo:raw:4242')

    class FakeRunningPipeline:
        async def push(self, visit: VisitName):
            pushed_visits.append(visit)

    monkeypatch.setattr(app_module, 'get_datasource', lambda: FakeDataSource())
    monkeypatch.setattr(app_module, 'get_db_session', lambda: _FakeSessionContext())
    monkeypatch.setattr(app_module, 'running_pipeline', FakeRunningPipeline(), raising=False)

    await app_module.route_create_quicklook(CreateQuicklookRequest(visit='repo:by_uuid:uuid-1'))

    assert resolved_visits == [VisitName('repo:by_uuid:uuid-1')]
    assert pushed_visits == [VisitName('repo:raw:4242')]


async def test_route_create_quicklook_returns_404_for_unknown_uuid(monkeypatch):
    class FakeDataSource:
        async def resolve_visit(self, visit: VisitName) -> VisitName:
            del visit
            raise VisitResolutionError('Unknown dataset UUID: uuid-1')

    monkeypatch.setattr(app_module, 'get_datasource', lambda: FakeDataSource())

    try:
        await app_module.route_create_quicklook(CreateQuicklookRequest(visit='repo:by_uuid:uuid-1'))
    except HTTPException as e:
        assert e.status_code == 404
        assert e.detail == 'Unknown dataset UUID: uuid-1'
    else:  # pragma: no cover
        raise AssertionError('HTTPException was not raised')
