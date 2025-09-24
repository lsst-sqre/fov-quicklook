from fastapi.testclient import TestClient
import requests
from quicklook.coordinator.app import app
import pytest

from quicklook.config import config
from quicklook.dev.run_uvicorn import find_free_tcp_port, run_uvicorn_app


client = TestClient(app)


def test_healthz() -> None:
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_route_create_quicklook(coordinator_url: str):
    res = requests.post(f'{coordinator_url}/quicklooks', json={'visit': 'raw:broccoli'})
    assert res.status_code == 200



@pytest.fixture(scope='module')
def coordinator_url():
    # Generator２つが登録された状態でCoordinatorを起動する
    with run_uvicorn_app(
        'quicklook.coordinator.app:app',
        port=9501,
        log_prefix='[coordinator] ',
        healthz='/healthz',
    ) as coordinator_runner:
        coordinator_runner.wait_for_ready()
        config.generator_port = find_free_tcp_port()
        with run_uvicorn_app(
            'quicklook.generator.app:app',
            port=config.generator_port,
            log_prefix='[generator1] ',
            healthz='/healthz',
        ) as generator_runner1:
            generator_runner1.wait_for_ready()
            # config.generator_port = find_free_tcp_port()
            # with run_uvicorn_app(
            #     'quicklook.generator.app:app',
            #     port=config.generator_port,
            #     log_prefix='[generator2] ',
            #     healthz='/healthz',
            # ) as generator_runner2:
            #     generator_runner2.wait_for_ready()
            yield coordinator_runner.base_url
