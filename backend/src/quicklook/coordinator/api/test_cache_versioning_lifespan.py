from contextlib import asynccontextmanager
from types import SimpleNamespace

import quicklook.coordinator.api.app as coordinator_app


async def test_lifespan_runs_startup_cleanup_before_services(monkeypatch):
    events: list[str] = []

    async def fake_cleanup_at_startup():
        events.append('cleanup')

    @asynccontextmanager
    async def fake_managed_session():
        events.append('managed_session_enter')
        try:
            yield
        finally:
            events.append('managed_session_exit')

    @asynccontextmanager
    async def fake_coordinator_lifespan(app):
        del app
        events.append('coordinator_enter')
        try:
            yield
        finally:
            events.append('coordinator_exit')

    @asynccontextmanager
    async def fake_run_quicklook_pipeline():
        events.append('pipeline_enter')
        try:
            yield SimpleNamespace(push=None, jobs=None, subscribe_shared_status=None)
        finally:
            events.append('pipeline_exit')

    monkeypatch.setattr(coordinator_app, 'cleanup_at_startup', fake_cleanup_at_startup)
    monkeypatch.setattr(coordinator_app, 'managed_session', fake_managed_session)
    monkeypatch.setattr(coordinator_app, 'coordinator_lifespan', fake_coordinator_lifespan)
    monkeypatch.setattr(coordinator_app, 'run_quicklook_pipeline', fake_run_quicklook_pipeline)

    async with coordinator_app.lifespan(coordinator_app.app):
        events.append('lifespan_body')

    assert events == [
        'cleanup',
        'managed_session_enter',
        'coordinator_enter',
        'pipeline_enter',
        'lifespan_body',
        'pipeline_exit',
        'coordinator_exit',
        'managed_session_exit',
    ]
