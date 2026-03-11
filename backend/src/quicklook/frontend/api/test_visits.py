from types import SimpleNamespace

from fastapi import HTTPException

from quicklook.datasource.types import VisitResolutionError
from quicklook.frontend.api import visits


async def test_get_visit_metadata_returns_404_for_unknown_uuid(monkeypatch):
    class FakeDataSource:
        async def get_metadata(self, ref):
            del ref
            raise VisitResolutionError('Unknown dataset UUID: uuid-1')

    monkeypatch.setattr(visits, 'get_datasource', lambda: FakeDataSource())

    try:
        await visits.get_visit_metadata('repo:by_uuid:uuid-1', 'R22_S00')
    except HTTPException as e:
        assert e.status_code == 404
        assert e.detail == 'Unknown dataset UUID: uuid-1'
    else:  # pragma: no cover
        raise AssertionError('HTTPException was not raised')
