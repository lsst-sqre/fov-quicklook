from contextlib import asynccontextmanager

import quicklook.coordinator.housekeeping as housekeeping


async def test_cleanup_at_startup_queries_only_current_cache_version(monkeypatch):
    from quicklook.config import config

    monkeypatch.setattr(config, 'tile_cache_schema_version', 3)
    statements: list[str] = []

    class FakeSession:
        async def execute(self, statement):
            statements.append(str(statement))
            return type('Result', (), {'all': lambda self: []})()

    session = FakeSession()

    @asynccontextmanager
    async def fake_get_db_session():
        yield session

    monkeypatch.setattr(housekeeping, 'get_db_session', fake_get_db_session)
    monkeypatch.setattr(housekeeping, 'delete_one_quicklook', lambda visit_name: None)

    await housekeeping.cleanup_at_startup()

    assert len(statements) == 1
    assert 'quicklooks.ready = false' in statements[0].lower()
    assert 'quicklooks.cache_version =' in statements[0]


async def test_select_quicklook_to_delete_counts_only_current_cache_version(monkeypatch):
    from quicklook.config import config

    monkeypatch.setattr(config, 'tile_cache_schema_version', 4)
    monkeypatch.setattr(config, 'housekeeping_keep_recent_count', 10)
    statements: list[str] = []

    class FakeSession:
        async def execute(self, statement):
            statements.append(str(statement))
            return type('Result', (), {'scalar': lambda self: 0})()

    session = FakeSession()

    @asynccontextmanager
    async def fake_get_db_session():
        yield session

    monkeypatch.setattr(housekeeping, 'get_db_session', fake_get_db_session)

    assert await housekeeping.select_quicklook_to_delete() is None
    assert len(statements) == 1
    assert 'quicklooks.ready = true' in statements[0].lower()
    assert 'quicklooks.cache_version =' in statements[0]
