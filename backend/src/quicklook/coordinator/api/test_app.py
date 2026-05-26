from types import SimpleNamespace

from quicklook.config import config
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


async def test_route_create_quicklook_deletes_stale_record_before_queueing(monkeypatch):
    pushed_visits: list[VisitName] = []
    deleted_records: list[object] = []
    commit_count = 0
    stale_quicklook = SimpleNamespace(cache_version=config.tile_cache_schema_version - 1)

    class FakeSession:
        async def execute(self, stmt):
            del stmt
            return SimpleNamespace(scalar_one_or_none=lambda: stale_quicklook)

        async def delete(self, quicklook):
            deleted_records.append(quicklook)

        async def commit(self):
            nonlocal commit_count
            commit_count += 1

    class FakeSessionContext:
        async def __aenter__(self):
            return FakeSession()

        async def __aexit__(self, exc_type, exc, tb):
            del exc_type, exc, tb
            return False

    class FakeRunningPipeline:
        async def push(self, visit: VisitName):
            pushed_visits.append(visit)

    monkeypatch.setattr(app_module, 'get_db_session', lambda: FakeSessionContext())
    monkeypatch.setattr(app_module, 'running_pipeline', FakeRunningPipeline(), raising=False)

    await app_module.route_create_quicklook(CreateQuicklookRequest(visit='repo:raw:4242'))

    assert deleted_records == [stale_quicklook]
    assert commit_count == 1
    assert pushed_visits == [VisitName('repo:raw:4242')]
