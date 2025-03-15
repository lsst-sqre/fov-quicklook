import concurrent.futures
import contextlib
import multiprocessing
import os
import signal
import time

import pytest
import requests

from quicklook.config import config
from quicklook.utils.uvicorn import uvicorn_run


@pytest.fixture(scope='module', autouse=True)
def ensure_coordinator_and_generator_are_running(run_coordinator_process, run_generator_process, run_frontend_process):
    # Wait for generator and frontend to be ready simultaneously
    with concurrent.futures.ThreadPoolExecutor() as executor:
        futures = [executor.submit(run_generator_process), executor.submit(run_frontend_process)]
        # Wait for both to complete and propagate any exceptions
        for future in concurrent.futures.as_completed(futures):
            future.result()

    res = requests.get(f'http://127.0.0.1:{config.coordinator_port}/healthz')
    assert res.status_code == 200
    generators: list = res.json()
    assert len(generators) >= 1


@pytest.fixture(scope='module')
def run_coordinator_process():
    from quicklook.coordinator.api import app

    with run_uvicorn_app('quicklook.coordinator.api:app', port=config.coordinator_port, log_prefix='[coordinator] ') as wait_for_ready:
        wait_for_ready()
        yield


@pytest.fixture(scope='module')
def run_generator_process(run_coordinator_process):
    from quicklook.generator.api import GeneratorRuntimeSettings

    with GeneratorRuntimeSettings.stack.push(GeneratorRuntimeSettings(port=config.generator_port)) as settings:
        with run_uvicorn_app('quicklook.generator.api:app', port=settings.port, log_prefix='[generator1] ') as wait_for_ready1:
            with GeneratorRuntimeSettings.stack.push(GeneratorRuntimeSettings(port=config.generator_port + 1)) as settings:
                with run_uvicorn_app('quicklook.generator.api:app', port=settings.port, log_prefix='[generator2] ') as wait_for_ready2:

                    def wait_for_ready():
                        with concurrent.futures.ThreadPoolExecutor() as executor:
                            futures = [executor.submit(wait_for_ready1), executor.submit(wait_for_ready2)]
                            # Wait for both to complete and propagate any exceptions
                            for future in concurrent.futures.as_completed(futures):
                                future.result()

                    yield wait_for_ready


@pytest.fixture(scope='module')
def run_frontend_process():
    with run_uvicorn_app('quicklook.frontend.api:app', port=config.frontend_port, healthz='/api/healthz', log_prefix='[frontend] ') as wait_for_ready:
        yield wait_for_ready


@contextlib.contextmanager
def run_uvicorn_app(app: str, *, port: int, timeout=10, log_prefix='', healthz='/healthz'):
    p = multiprocessing.Process(target=uvicorn_run, args=(app,), kwargs={'port': port, 'log_prefix': log_prefix})
    p.start()

    def wait_for_ready():
        for _ in range(timeout):
            try:
                requests.get(f'http://127.0.0.1:{port}{healthz}')
                break
            except requests.exceptions.ConnectionError:
                pass
            time.sleep(1)
        else:
            raise TimeoutError(f'{app} did not start in {timeout} seconds')

    try:
        yield wait_for_ready
    finally:
        assert p.pid
        os.kill(p.pid, signal.SIGINT)  # p.terminate() を使うとcoverageがとれないのでSIGINTを送る
        p.join()


@pytest.fixture(scope='module')
def quicklooks_cleared():
    res = requests.delete(f'http://127.0.0.1:{config.frontend_port}/api/quicklooks/*')
    assert res.status_code == 200

    res = requests.get(f'http://127.0.0.1:{config.frontend_port}/api/quicklooks')
    assert res.status_code == 200
    assert len(res.json()) == 0
