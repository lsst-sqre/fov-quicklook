from fastapi import HTTPException

from quicklook.coordinator.api.types import CreateQuicklookRequest
from quicklook.datasource.types import ResolvedVisitInfo, VisitResolutionError
from quicklook.frontend.api import quicklooks
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
