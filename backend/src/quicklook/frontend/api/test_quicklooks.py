import pickle
from types import SimpleNamespace
from typing import cast

import pytest
from fastapi import HTTPException

from quicklook.coordinator.api.types import CreateQuicklookRequest
from quicklook.coordinator.api.types import SharedStatusMessageJobSharedLargeStatus
from quicklook.coordinator.api.types import SharedStatusMessageJobStatusList
from quicklook.datasource.types import ResolvedVisitInfo, VisitResolutionError
from quicklook.frontend.api import quicklooks
from quicklook.generator.generate_single_fits_tiles import CcdMetadata
from quicklook.job.job import Job
from quicklook.utils.broadcast import Broadcast
from quicklook.types import VisitName


async def test_create_quicklook_resolves_visit_before_forwarding(monkeypatch):
    received_visits: list[VisitName] = []
    forwarded_requests: list[tuple[str, str, dict]] = []

    class FakeDataSource:
        async def resolve_visit_info(self, visit: VisitName) -> ResolvedVisitInfo:
            received_visits.append(visit)
            return ResolvedVisitInfo(visit_name=VisitName('repo:raw:4242'))

    async def fake_http_request(method: str, url: str, **kwargs):
        forwarded_requests.append((method, url, kwargs))
        return {'ok': True}

    monkeypatch.setattr(quicklooks, 'get_datasource', lambda: FakeDataSource())
    monkeypatch.setattr(quicklooks, 'http_request', fake_http_request)

    result = await quicklooks.create_quicklook(CreateQuicklookRequest(visit='repo:by_uuid:uuid-1'))

    assert result == {'ok': True}
    assert received_visits == [VisitName('repo:by_uuid:uuid-1')]
    assert forwarded_requests == [
        (
            'post',
            f'{quicklooks.config.coordinator_base_url}/quicklooks',
            {'json': {'visit': 'repo:raw:4242'}},
        )
    ]


async def test_create_quicklook_returns_404_for_unknown_uuid(monkeypatch):
    class FakeDataSource:
        async def resolve_visit_info(self, visit: VisitName) -> ResolvedVisitInfo:
            del visit
            raise VisitResolutionError('Unknown dataset UUID: uuid-1')

    monkeypatch.setattr(quicklooks, 'get_datasource', lambda: FakeDataSource())

    try:
        await quicklooks.create_quicklook(CreateQuicklookRequest(visit='repo:by_uuid:uuid-1'))
    except HTTPException as e:
        assert e.status_code == 404
        assert e.detail == 'Unknown dataset UUID: uuid-1'
    else:  # pragma: no cover
        raise AssertionError('HTTPException was not raised')


async def test_status_relay_keeps_retrying_without_shutdown(monkeypatch):
    connect_calls: list[tuple[str, dict]] = []
    sleep_calls: list[int] = []

    class StopLoop(BaseException):
        pass

    class FakeConnect:
        def __init__(self, exc: BaseException):
            self._exc = exc

        async def __aenter__(self):
            raise self._exc

        async def __aexit__(self, exc_type, exc, tb):
            del exc_type, exc, tb
            return False

    def fake_connect(url: str, **kwargs):
        connect_calls.append((url, kwargs))
        if len(connect_calls) <= 6:
            return FakeConnect(RuntimeError(f'boom-{len(connect_calls)}'))
        return FakeConnect(StopLoop())

    async def fake_sleep(delay: int | float):
        sleep_calls.append(int(delay))

    async def fail_shutdown(**kwargs):
        del kwargs
        raise AssertionError('graceful_shutdown should not be called for shared-status reconnect failures')

    monkeypatch.setattr(quicklooks.websockets, 'connect', fake_connect)
    monkeypatch.setattr(quicklooks.asyncio, 'sleep', fake_sleep)
    monkeypatch.setattr('quicklook.utils.graceful_shutdown.graceful_shutdown', fail_shutdown)

    with pytest.raises(StopLoop):
        await quicklooks._status_relay_main_loop()

    assert len(connect_calls) == 7
    assert sleep_calls == [1, 2, 4, 8, 16, 32]
    assert {kwargs['max_size'] for _, kwargs in connect_calls} == {None}


async def test_status_relay_updates_job_status_from_binary_message(monkeypatch):
    job = Job(VisitName('repo:raw:4242'))
    msg = SharedStatusMessageJobStatusList(data={job.visit: job.status})
    payload = pickle.dumps(msg)

    class StopLoop(BaseException):
        pass

    class FakeWebSocket:
        def __init__(self):
            self._recv_count = 0

        async def recv(self):
            self._recv_count += 1
            if self._recv_count == 1:
                return payload
            raise StopLoop()

    class FakeConnect:
        async def __aenter__(self):
            return FakeWebSocket()

        async def __aexit__(self, exc_type, exc, tb):
            del exc_type, exc, tb
            return False

    monkeypatch.setattr(quicklooks, '_job_status_dict', Broadcast(max_queue_size=2))
    monkeypatch.setattr(quicklooks, '_job_shared_large_status_dict', {})
    monkeypatch.setattr(quicklooks.websockets, 'connect', lambda url, **kwargs: FakeConnect())

    with pytest.raises(StopLoop):
        await quicklooks._status_relay_main_loop()

    assert quicklooks._job_status_dict.last_value() == {job.visit: job.status}


def test_apply_shared_status_message_moves_ready_metadata_to_short_lived_cache(monkeypatch):
    job = Job(VisitName('repo:raw:4242'))
    job.status.stage = 'ready'

    ccd_metadata = [cast(CcdMetadata, object())]
    job.shared_large_status.ccd_metadata_list = ccd_metadata

    status_dict = Broadcast(max_queue_size=2)
    status_dict.put({job.visit: job.status})

    monkeypatch.setattr(quicklooks, '_job_status_dict', status_dict)
    monkeypatch.setattr(quicklooks, '_job_shared_large_status_dict', {job.visit: job.shared_large_status})
    monkeypatch.setattr(quicklooks, '_recent_ready_metadata_dict', {})
    monkeypatch.setattr(quicklooks.time, 'monotonic', lambda: 100.0)

    quicklooks._apply_shared_status_message(SharedStatusMessageJobStatusList(data={}))

    assert quicklooks._job_status_dict.last_value() == {}
    assert quicklooks._job_shared_large_status_dict == {}
    assert quicklooks._get_ccd_metadata_list_for_shared_status(job.visit, allow_recent_ready=True) == ccd_metadata


def test_recent_ready_metadata_expires(monkeypatch):
    visit = VisitName('repo:raw:4242')
    ccd_metadata = [cast(CcdMetadata, object())]

    monkeypatch.setattr(quicklooks, '_job_shared_large_status_dict', {})
    monkeypatch.setattr(
        quicklooks,
        '_recent_ready_metadata_dict',
        {
            visit: quicklooks.RecentReadyMetadata(
                ccd_metadata_list=ccd_metadata,
                expires_at=100.0,
            )
        },
    )
    monkeypatch.setattr(quicklooks.time, 'monotonic', lambda: 101.0)

    with pytest.raises(KeyError):
        quicklooks._get_ccd_metadata_list_for_shared_status(visit, allow_recent_ready=True)

    assert quicklooks._recent_ready_metadata_dict == {}


def test_shared_large_status_replaces_recent_ready_metadata(monkeypatch):
    visit = VisitName('repo:raw:4242')
    job = Job(visit)
    active_metadata = [cast(CcdMetadata, object())]
    job.shared_large_status.ccd_metadata_list = active_metadata

    monkeypatch.setattr(quicklooks, '_job_status_dict', Broadcast(max_queue_size=2))
    monkeypatch.setattr(quicklooks, '_job_shared_large_status_dict', {})
    monkeypatch.setattr(
        quicklooks,
        '_recent_ready_metadata_dict',
        {
            visit: quicklooks.RecentReadyMetadata(
                ccd_metadata_list=[cast(CcdMetadata, object())],
                expires_at=100.0,
            )
        },
    )
    monkeypatch.setattr(quicklooks.time, 'monotonic', lambda: 50.0)

    quicklooks._apply_shared_status_message(
        SharedStatusMessageJobSharedLargeStatus(
            visit=visit,
            data=job.shared_large_status,
        )
    )

    assert quicklooks._recent_ready_metadata_dict == {}
    assert quicklooks._get_ccd_metadata_list_for_shared_status(visit) == active_metadata

async def test_get_all_quicklook_jobs_returns_cached_broadcast_value(monkeypatch):
    job = Job(VisitName('repo:raw:4242'))
    broadcast = Broadcast(max_queue_size=2)
    broadcast.put({job.visit: job.status})

    monkeypatch.setattr(quicklooks, '_job_status_dict', broadcast)

    async def fail_http_request(*args, **kwargs):
        raise AssertionError((args, kwargs))

    monkeypatch.setattr(quicklooks, 'http_request', fail_http_request)

    jobs = await quicklooks.get_all_quicklook_jobs()

    assert jobs == {job.visit: job.status}


async def test_get_all_quicklook_jobs_falls_back_to_coordinator(monkeypatch):
    monkeypatch.setattr(quicklooks, '_job_status_dict', Broadcast(max_queue_size=2))
    received: list[tuple[str, str, dict]] = []

    async def fake_http_request(method: str, url: str, **kwargs):
        received.append((method, url, kwargs))
        return {}

    monkeypatch.setattr(quicklooks, 'http_request', fake_http_request)

    jobs = await quicklooks.get_all_quicklook_jobs()

    assert jobs == {}
    assert received == [('get', f'{quicklooks.config.coordinator_base_url}/quicklooks/*/status', {})]
    assert quicklooks._job_status_dict.last_value() == {}


async def test_get_quicklook_metadata_from_db_filters_current_cache_version(monkeypatch):
    statements: list[str] = []

    class FakeSession:
        async def execute(self, stmt):
            statements.append(str(stmt))
            return SimpleNamespace(scalar_one_or_none=lambda: None)

    class FakeSessionContext:
        async def __aenter__(self):
            return FakeSession()

        async def __aexit__(self, exc_type, exc, tb):
            del exc_type, exc, tb
            return False

    monkeypatch.setattr(quicklooks, 'get_db_session', lambda: FakeSessionContext())

    assert await quicklooks._get_quicklook_metadata_from_db(VisitName('repo:raw:4242')) is None
    assert len(statements) == 1
    assert 'quicklooks.ready = true' in statements[0].lower()
    assert 'quicklooks.cache_version =' not in statements[0]
