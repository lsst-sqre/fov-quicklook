import pytest
from fastapi.testclient import TestClient

from quicklook.coordinator.api import app

pytestmark = pytest.mark.focus


@pytest.fixture(scope='module')
def client():
    with TestClient(app) as client:
        yield client


@pytest.fixture(autouse=True)
def delete_all_quicklooks(client: TestClient):
    res = client.delete('/quicklooks/*')
    assert res.status_code == 200
    yield


def test_healthz(client: TestClient):
    res = client.get('/healthz')
    assert res.status_code == 200

