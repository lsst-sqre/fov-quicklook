from contextlib import ExitStack
import time

from fastapi.testclient import TestClient
import requests
from quicklook.coordinator.app import app
import pytest

from quicklook.config import config
from quicklook.dev.run_uvicorn import find_free_tcp_port, run_uvicorn_app


pytestmark = pytest.mark.slow


client = TestClient(app)


def test_healthz() -> None:
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_route_create_quicklook(coordinator_url: str):
    res = requests.post(f'{coordinator_url}/quicklooks', json={'visit': 'raw:broccoli'})
    assert res.status_code == 200


num_generators = 8


@pytest.fixture(scope='module')
def coordinator_url():
    # Generatorを設定された個数分起動した状態でCoordinatorを起動する
    with run_uvicorn_app(
        'quicklook.coordinator.app:app',
        port=9501,
        log_prefix='[coordinator] ',
        healthz='/healthz',
    ) as coordinator_runner:
        coordinator_runner.wait_for_ready()
        original_generator_port = config.generator_port
        with ExitStack() as stack:
            try:
                for index in range(num_generators):
                    config.generator_port = find_free_tcp_port()
                    generator_runner = stack.enter_context(
                        run_uvicorn_app(
                            'quicklook.generator.app:app',
                            port=config.generator_port,
                            log_prefix=f'[generator{index + 1}] ',
                            healthz='/healthz',
                            log_level='warning',
                        )
                    )
                    generator_runner.wait_for_ready()
                if num_generators > 0 and config.environment == 'test':
                    _wait_for_registered_generators(coordinator_runner.base_url, num_generators)
                yield coordinator_runner.base_url
            finally:
                config.generator_port = original_generator_port


def _wait_for_registered_generators(base_url: str, expected_count: int, timeout: float = 5.0) -> None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        response = requests.get(f'{base_url}/comm/generators')
        if len(response.json().get('generators', {})) >= expected_count:
            return
        time.sleep(0.1)
    raise TimeoutError(f'Generators did not register within {timeout} seconds')
