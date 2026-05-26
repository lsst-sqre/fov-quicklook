from contextlib import asynccontextmanager

import quicklook.coordinator.housekeeping as housekeeping
from quicklook.object_storage import TileCacheMetadata, TileCacheMetadataError


async def test_reset_tile_cache_state_clears_db_storage_and_writes_metadata(monkeypatch):
    from quicklook.config import config

    monkeypatch.setattr(config, 'tile_cache_schema_version', 2)

    class FakeSession:
        def __init__(self):
            self.executed = []
            self.commit_count = 0

        async def execute(self, statement):
            self.executed.append(statement)

        async def commit(self):
            self.commit_count += 1

    session = FakeSession()
    deleted_prefixes: list[str] = []
    written_metadata: list[TileCacheMetadata] = []

    @asynccontextmanager
    async def fake_get_db_session():
        yield session

    async def fake_put_tile_cache_metadata(metadata: TileCacheMetadata):
        written_metadata.append(metadata)

    monkeypatch.setattr(housekeeping, 'get_db_session', fake_get_db_session)
    monkeypatch.setattr(housekeeping, 'delete_objects_by_prefix', deleted_prefixes.append)
    monkeypatch.setattr(housekeeping, 'put_tile_cache_metadata', fake_put_tile_cache_metadata)

    await housekeeping.reset_tile_cache_state()

    assert [statement.table.name for statement in session.executed] == ['accesses', 'quicklooks']
    assert session.commit_count == 1
    assert deleted_prefixes == ['']
    assert written_metadata == [TileCacheMetadata(schema_version=2)]


async def test_ensure_tile_cache_schema_version_resets_when_metadata_is_missing(monkeypatch):
    resets: list[str] = []

    async def fake_get_tile_cache_metadata():
        return None

    async def fake_reset_tile_cache_state():
        resets.append('reset')

    monkeypatch.setattr(housekeeping, 'get_tile_cache_metadata', fake_get_tile_cache_metadata)
    monkeypatch.setattr(housekeeping, 'reset_tile_cache_state', fake_reset_tile_cache_state)

    await housekeeping.ensure_tile_cache_schema_version()

    assert resets == ['reset']


async def test_ensure_tile_cache_schema_version_resets_when_metadata_mismatches(monkeypatch):
    from quicklook.config import config

    monkeypatch.setattr(config, 'tile_cache_schema_version', 3)
    resets: list[str] = []

    async def fake_get_tile_cache_metadata():
        return TileCacheMetadata(schema_version=1)

    async def fake_reset_tile_cache_state():
        resets.append('reset')

    monkeypatch.setattr(housekeeping, 'get_tile_cache_metadata', fake_get_tile_cache_metadata)
    monkeypatch.setattr(housekeeping, 'reset_tile_cache_state', fake_reset_tile_cache_state)

    await housekeeping.ensure_tile_cache_schema_version()

    assert resets == ['reset']


async def test_ensure_tile_cache_schema_version_skips_reset_when_metadata_matches(monkeypatch):
    resets: list[str] = []

    async def fake_get_tile_cache_metadata():
        return TileCacheMetadata(schema_version=1)

    async def fake_reset_tile_cache_state():
        resets.append('reset')

    monkeypatch.setattr(housekeeping, 'get_tile_cache_metadata', fake_get_tile_cache_metadata)
    monkeypatch.setattr(housekeeping, 'reset_tile_cache_state', fake_reset_tile_cache_state)

    await housekeeping.ensure_tile_cache_schema_version()

    assert resets == []


async def test_ensure_tile_cache_schema_version_resets_when_metadata_is_invalid(monkeypatch):
    resets: list[str] = []

    async def fake_get_tile_cache_metadata():
        raise TileCacheMetadataError('broken metadata')

    async def fake_reset_tile_cache_state():
        resets.append('reset')

    monkeypatch.setattr(housekeeping, 'get_tile_cache_metadata', fake_get_tile_cache_metadata)
    monkeypatch.setattr(housekeeping, 'reset_tile_cache_state', fake_reset_tile_cache_state)

    await housekeeping.ensure_tile_cache_schema_version()

    assert resets == ['reset']
