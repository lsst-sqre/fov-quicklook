from types import SimpleNamespace

from quicklook.coordinator.api import app as app_module
from quicklook.coordinator.api.types import CreateQuicklookRequest
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


async def test_route_create_quicklook_queues_requested_visit(monkeypatch):
    pushed_visits: list[VisitName] = []

    class FakeRunningPipeline:
        async def push(self, visit: VisitName):
            pushed_visits.append(visit)

    monkeypatch.setattr(app_module, 'get_db_session', lambda: _FakeSessionContext())
    monkeypatch.setattr(app_module, 'running_pipeline', FakeRunningPipeline(), raising=False)

    await app_module.route_create_quicklook(CreateQuicklookRequest(visit='repo:raw:4242'))

    assert pushed_visits == [VisitName('repo:raw:4242')]
