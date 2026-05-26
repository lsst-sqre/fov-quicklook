from contextlib import asynccontextmanager

import quicklook.coordinator.housekeeping as housekeeping
from quicklook.object_storage import TileCacheMetadata, TileCacheMetadataError


async def test_prepare_stale_cache_cleanup_resets_when_metadata_is_missing(monkeypatch):
    written_metadata: list[TileCacheMetadata] = []

    class FakeSession:
        def __init__(self):
            self.executed = []
            self.commit_count = 0

        async def execute(self, statement):
            self.executed.append(statement)
            return type('Result', (), {'scalar': lambda self: 2})()

        async def commit(self):
            self.commit_count += 1

    session = FakeSession()

    @asynccontextmanager
    async def fake_get_db_session():
        yield session

    async def fake_get_tile_cache_metadata():
        return None

    async def fake_put_tile_cache_metadata(metadata: TileCacheMetadata):
        written_metadata.append(metadata)

    monkeypatch.setattr(housekeeping, 'get_db_session', fake_get_db_session)
    monkeypatch.setattr(housekeeping, 'get_tile_cache_metadata', fake_get_tile_cache_metadata)
    monkeypatch.setattr(housekeeping, 'put_tile_cache_metadata', fake_put_tile_cache_metadata)
    monkeypatch.setattr(housekeeping, 'list_cache_versions', lambda: set())

    plan = await housekeeping.prepare_stale_cache_cleanup()

    assert plan == housekeeping.StaleCacheCleanupPlan(stale_versions=frozenset(), deleted_quicklook_count=2)
    assert [statement.table.name for statement in session.executed[1:]] == ['accesses', 'quicklooks']
    assert session.commit_count == 1
    assert written_metadata == [TileCacheMetadata(schema_version=1)]


async def test_prepare_stale_cache_cleanup_resets_when_metadata_is_invalid(monkeypatch):
    resets: list[TileCacheMetadata] = []

    class FakeSession:
        def __init__(self):
            self.executed = []

        async def execute(self, statement):
            self.executed.append(statement)
            return type('Result', (), {'scalar': lambda self: 0})()

        async def commit(self):
            return None

    session = FakeSession()

    @asynccontextmanager
    async def fake_get_db_session():
        yield session

    async def fake_get_tile_cache_metadata():
        raise TileCacheMetadataError('broken metadata')

    async def fake_put_tile_cache_metadata(metadata: TileCacheMetadata):
        resets.append(metadata)

    monkeypatch.setattr(housekeeping, 'get_db_session', fake_get_db_session)
    monkeypatch.setattr(housekeeping, 'get_tile_cache_metadata', fake_get_tile_cache_metadata)
    monkeypatch.setattr(housekeeping, 'put_tile_cache_metadata', fake_put_tile_cache_metadata)
    monkeypatch.setattr(housekeeping, 'list_cache_versions', lambda: {1, 2})

    plan = await housekeeping.prepare_stale_cache_cleanup()

    assert plan == housekeeping.StaleCacheCleanupPlan(stale_versions=frozenset({2}), deleted_quicklook_count=0)
    assert resets == [TileCacheMetadata(schema_version=1)]


async def test_prepare_stale_cache_cleanup_returns_stale_versions_and_skips_when_clean(monkeypatch):
    from quicklook.config import config

    monkeypatch.setattr(config, 'tile_cache_schema_version', 3)
    writes: list[TileCacheMetadata] = []

    class FakeSession:
        def __init__(self):
            self.executed = []
            self.commit_count = 0

        async def execute(self, statement):
            self.executed.append(statement)
            return type('Result', (), {'scalar': lambda self: 1})()

        async def commit(self):
            self.commit_count += 1

    session = FakeSession()

    @asynccontextmanager
    async def fake_get_db_session():
        yield session

    async def fake_get_tile_cache_metadata():
        return TileCacheMetadata(schema_version=3)

    async def fake_put_tile_cache_metadata(metadata: TileCacheMetadata):
        writes.append(metadata)

    monkeypatch.setattr(housekeeping, 'get_db_session', fake_get_db_session)
    monkeypatch.setattr(housekeeping, 'get_tile_cache_metadata', fake_get_tile_cache_metadata)
    monkeypatch.setattr(housekeeping, 'put_tile_cache_metadata', fake_put_tile_cache_metadata)
    monkeypatch.setattr(housekeeping, 'list_cache_versions', lambda: {2, 3})

    plan = await housekeeping.prepare_stale_cache_cleanup()

    assert plan == housekeeping.StaleCacheCleanupPlan(stale_versions=frozenset({2}), deleted_quicklook_count=1)
    assert session.commit_count == 1
    assert writes == [TileCacheMetadata(schema_version=3)]


async def test_prepare_stale_cache_cleanup_skips_reset_when_metadata_and_prefixes_match(monkeypatch):
    class FakeSession:
        async def execute(self, statement):
            raise AssertionError(statement)

    session = FakeSession()

    @asynccontextmanager
    async def fake_get_db_session():
        yield session

    async def fake_get_tile_cache_metadata():
        return TileCacheMetadata(schema_version=1)

    async def fake_put_tile_cache_metadata(metadata: TileCacheMetadata):
        del metadata

    monkeypatch.setattr(housekeeping, 'get_db_session', fake_get_db_session)
    monkeypatch.setattr(housekeeping, 'get_tile_cache_metadata', fake_get_tile_cache_metadata)
    monkeypatch.setattr(housekeeping, 'put_tile_cache_metadata', fake_put_tile_cache_metadata)
    monkeypatch.setattr(housekeeping, 'list_cache_versions', lambda: {1})

    plan = await housekeeping.prepare_stale_cache_cleanup()

    assert plan == housekeeping.StaleCacheCleanupPlan(stale_versions=frozenset(), deleted_quicklook_count=0)


async def test_delete_stale_cache_versions_deletes_each_version(monkeypatch):
    deleted_versions: list[int] = []

    monkeypatch.setattr(housekeeping, 'delete_cache_version', deleted_versions.append)

    await housekeeping.delete_stale_cache_versions({5, 2})

    assert deleted_versions == [2, 5]
