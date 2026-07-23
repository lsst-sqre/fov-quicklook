from fastapi import FastAPI
from fastapi.testclient import TestClient

from quicklook.frontend.api.cache_entries import router


def test_delete_cache_entry_route_accepts_visit_names_with_slashes(monkeypatch):
    deleted: list[str] = []

    async def fake_delete_one_quicklook(visit_name: str) -> None:
        deleted.append(visit_name)

    monkeypatch.setattr("quicklook.frontend.api.cache_entries.delete_one_quicklook", fake_delete_one_quicklook)

    app = FastAPI()
    app.include_router(router, prefix="/fov-quicklook-dev")
    client = TestClient(app)

    visit_name = "reviewapp-ci:LSSTCam/raw/all:raw:exposure=910001"
    response = client.delete(f"/fov-quicklook-dev/api/cache_entries/{visit_name}")

    assert response.status_code == 200
    assert deleted == [visit_name]


def test_delete_cache_entry_route_normalizes_escaped_visit_names(monkeypatch):
    deleted: list[str] = []

    async def fake_delete_one_quicklook(visit_name: str) -> None:
        deleted.append(visit_name)

    monkeypatch.setattr("quicklook.frontend.api.cache_entries.delete_one_quicklook", fake_delete_one_quicklook)

    app = FastAPI()
    app.include_router(router, prefix="/fov-quicklook-dev")
    client = TestClient(app)

    visit_name = "reviewapp-ci:LSSTCam!-raw!-all:raw:exposure=910001"
    response = client.delete(f"/fov-quicklook-dev/api/cache_entries/{visit_name}")

    assert response.status_code == 200
    assert deleted == ["reviewapp-ci:LSSTCam/raw/all:raw:exposure=910001"]
