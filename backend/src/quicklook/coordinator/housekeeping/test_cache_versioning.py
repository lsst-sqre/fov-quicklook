from contextlib import asynccontextmanager

import quicklook.coordinator.housekeeping as housekeeping
from quicklook.coordinator.housekeeping import StaleCacheCleanupPlan


async def test_prepare_stale_cache_cleanup_deletes_stale_db_entries_and_returns_stale_versions(monkeypatch):
    from quicklook.config import config

    monkeypatch.setattr(config, 'tile_cache_schema_version', 3)

    class FakeSession:
        def __init__(self):
            self.executed = []
            self.commit_count = 0

        async def execute(self, statement):
            self.executed.append(statement)
            if len(self.executed) == 1:
                return type('Result', (), {'all': lambda self: [('visit-old-1', 1), ('visit-old-2', 1)]})()

        async def commit(self):
            self.commit_count += 1

    session = FakeSession()

    @asynccontextmanager
    async def fake_get_db_session():
        yield session

    monkeypatch.setattr(housekeeping, 'get_db_session', fake_get_db_session)
    monkeypatch.setattr(housekeeping, 'list_cache_versions', lambda: {2, 3})

    plan = await housekeeping.prepare_stale_cache_cleanup()

    assert plan == StaleCacheCleanupPlan(stale_versions=frozenset({1, 2}), deleted_quicklook_count=2)
    assert [statement.table.name for statement in session.executed[1:]] == ['accesses', 'quicklooks']
    assert session.commit_count == 1


async def test_prepare_stale_cache_cleanup_returns_storage_only_versions_without_db_delete(monkeypatch):
    from quicklook.config import config

    monkeypatch.setattr(config, 'tile_cache_schema_version', 4)

    class FakeSession:
        def __init__(self):
            self.executed = []
            self.commit_count = 0

        async def execute(self, statement):
            self.executed.append(statement)
            return type('Result', (), {'all': lambda self: []})()

        async def commit(self):
            self.commit_count += 1

    session = FakeSession()

    @asynccontextmanager
    async def fake_get_db_session():
        yield session

    monkeypatch.setattr(housekeeping, 'get_db_session', fake_get_db_session)
    monkeypatch.setattr(housekeeping, 'list_cache_versions', lambda: {4, 5})

    plan = await housekeeping.prepare_stale_cache_cleanup()

    assert plan == StaleCacheCleanupPlan(stale_versions=frozenset({5}), deleted_quicklook_count=0)
    assert len(session.executed) == 1
    assert session.commit_count == 0


async def test_delete_stale_cache_versions_deletes_each_version(monkeypatch):
    deleted_versions: list[int] = []

    monkeypatch.setattr(housekeeping, 'delete_cache_version', deleted_versions.append)

    await housekeeping.delete_stale_cache_versions({5, 2})

    assert deleted_versions == [2, 5]
