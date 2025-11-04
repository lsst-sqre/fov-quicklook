import pytest
from fastapi.testclient import TestClient

from quicklook.generator.api.app import app


@pytest.fixture
def client():
    with TestClient(app) as client:
        yield client


def test_healthz(client: TestClient) -> None:
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
