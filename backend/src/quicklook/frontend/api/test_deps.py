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
