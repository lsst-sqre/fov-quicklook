import fastapi

from quicklook.datasource.types import VisitResolutionError
from quicklook.frontend.api import deps
from quicklook.types import VisitName


async def test_dep_visit_name_resolves_visit_with_datasource(monkeypatch):
    received: list[VisitName] = []

    class FakeDataSource:
        async def resolve_visit(self, visit: VisitName) -> VisitName:
            received.append(visit)
            return VisitName('repo:raw:4242')

    monkeypatch.setattr(deps, 'get_datasource', lambda: FakeDataSource())

    resolved = await deps.dep_visit_name('repo:by_uuid:uuid-1')

    assert resolved == VisitName('repo:raw:4242')
    assert received == [VisitName('repo:by_uuid:uuid-1')]


async def test_dep_visit_name_returns_404_for_unknown_uuid(monkeypatch):
    class FakeDataSource:
        async def resolve_visit(self, visit: VisitName) -> VisitName:
            del visit
            raise VisitResolutionError('Unknown dataset UUID: uuid-1')

    monkeypatch.setattr(deps, 'get_datasource', lambda: FakeDataSource())

    try:
        await deps.dep_visit_name('repo:by_uuid:uuid-1')
    except fastapi.HTTPException as e:
        assert e.status_code == 404
        assert e.detail == 'Unknown dataset UUID: uuid-1'
    else:  # pragma: no cover
        raise AssertionError('HTTPException was not raised')
