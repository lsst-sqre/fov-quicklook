import json
import contextlib
import multiprocessing
import os
import signal
import time

import pytest
import requests
import websockets.sync.client as websockets
from websockets.exceptions import ConnectionClosedOK

from quicklook.config import config
from quicklook.frontend.api.quicklooks import QuicklookStatus
from quicklook.utils.uvicorn import uvicorn_run


@pytest.mark.focus
def test_frontend_ok():
    res = requests.get(f'http://127.0.0.1:{config.frontend_port}/api/healthz')
    assert res.status_code == 200
    assert len(res.json()) >= 1


def test_coodinator_ok():
    res = requests.get(f'http://127.0.0.1:{config.coordinator_port}/healthz')
    assert res.status_code == 200
    assert len(res.json()) >= 1


@pytest.mark.focus
def test_list_visits():
    res = requests.get(f'http://127.0.0.1:{config.frontend_port}/api/visits')
    assert res.status_code == 200


@pytest.fixture(scope='module')
def quicklooks_cleared():
    res = requests.delete(f'http://127.0.0.1:{config.frontend_port}/api/quicklooks/*')
    assert res.status_code == 200

    res = requests.get(f'http://127.0.0.1:{config.frontend_port}/api/quicklooks')
    assert res.status_code == 200
    assert len(res.json()) == 0


@pytest.fixture(scope='module')
def one_quicklook_created(quicklooks_cleared):
    res = requests.post(f'http://127.0.0.1:{config.coordinator_port}/quicklooks', json={'visit': {'id': 'raw:broccoli'}})
    assert res.status_code == 200
    with websockets.connect(f'ws://127.0.0.1:{config.frontend_port}/api/quicklooks/raw:broccoli/status.ws') as ws:
        while True:
            try:
                status = json.loads(ws.recv())
                if isinstance(status, dict):
                    if status['phase'] in {'ready', 'failed'}:
                        break
            except ConnectionClosedOK:
                break


def test_create_quicklook(one_quicklook_created):
    # This only tests the fixture one_quicklook_created
    pass


def test_show_quicklook(one_quicklook_created):
    res = requests.get(f'http://127.0.0.1:{config.frontend_port}/api/quicklooks/raw:broccoli/status')
    assert res.status_code == 200
    QuicklookStatus.model_validate(res.json())


def test_list_quicklooks(one_quicklook_created):
    res = requests.get(f'http://127.0.0.1:{config.frontend_port}/api/quicklooks')
    assert res.status_code == 200
    response_json = res.json()
    assert len(response_json) == 1
    QuicklookStatus.model_validate(response_json[0])


def test_get_tile(one_quicklook_created):
    res = requests.get(f'http://127.0.0.1:{config.frontend_port}/api/quicklooks/raw:broccoli/tiles/8/0/0')
    assert res.status_code == 200
    assert res.headers['Content-Type'] == 'application/npy'


def test_get_fits_header(one_quicklook_created):
    res = requests.get(f'http://127.0.0.1:{config.frontend_port}/api/quicklooks/raw:broccoli/fits_header/R00_SG1')
    assert res.status_code == 200
    assert res.headers['Content-Type'] == 'application/json'


def test_get_tile_for_blank_region(one_quicklook_created):
    res = requests.get(f'http://127.0.0.1:{config.frontend_port}/api/quicklooks/raw:broccoli/tiles/0/0/0')
    assert res.status_code == 200
    assert res.headers['Content-Type'] == 'application/npy+zstd'


@pytest.fixture(scope='module', autouse=True)
def ensure_coordinator_and_generator_are_running(run_coordinator_process, run_generator_process, run_frontend_process):
    res = requests.get(f'http://127.0.0.1:{config.coordinator_port}/healthz')
    assert res.status_code == 200
    generators: list = res.json()
    assert len(generators) >= 1


@pytest.fixture(scope='module')
def run_coordinator_process():
    from quicklook.coordinator.api import app

    with run_uvicorn_app('quicklook.coordinator.api:app', port=config.coordinator_port, log_prefix='[coordinator] '):
        yield


@pytest.fixture(scope='module')
def run_generator_process(run_coordinator_process):
    from quicklook.generator.api import GeneratorRuntimeSettings

    with GeneratorRuntimeSettings.stack.push(GeneratorRuntimeSettings(port=config.generator_port)) as settings:
        with run_uvicorn_app('quicklook.generator.api:app', port=settings.port, log_prefix='[generator1] '):
            with GeneratorRuntimeSettings.stack.push(GeneratorRuntimeSettings(port=config.generator_port + 1)) as settings:
                with run_uvicorn_app('quicklook.generator.api:app', port=settings.port, log_prefix='[generator2] '):
                    yield


@pytest.fixture(scope='module')
def run_frontend_process(run_coordinator_process, run_generator_process):
    from quicklook.frontend.api import app

    port = config.frontend_port
    with run_uvicorn_app('quicklook.frontend.api:app', port=port, healthz='/api/healthz', log_prefix='[frontend] '):
        yield


@contextlib.contextmanager
def run_uvicorn_app(app: str, *, port: int, timeout=10, log_prefix='', healthz='/healthz'):
    p = multiprocessing.Process(target=uvicorn_run, args=(app,), kwargs={'port': port, 'log_prefix': log_prefix})
    p.start()
    for _ in range(timeout):
        try:
            requests.get(f'http://127.0.0.1:{port}{healthz}')
            break
        except requests.exceptions.ConnectionError:
            pass
        time.sleep(1)
    else:
        raise TimeoutError(f'{app} did not start in {timeout} seconds')
    yield
    assert p.pid
    os.kill(p.pid, signal.SIGINT)  # p.terminate() を使うとcoverageがとれないのでSIGINTを送る
    p.join()
