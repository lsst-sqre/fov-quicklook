import asyncio
import threading
import time
from contextlib import ExitStack, contextmanager
from dataclasses import dataclass
from typing import Callable

import pytest
import requests
import uvicorn
from sqlalchemy import delete

from quicklook.config import config
from quicklook.coordinator.create_quicklook import create_quicklook, quicklook_pipeline
from quicklook.db import Access, Quicklook, get_session
from quicklook.dev.run_uvicorn import find_free_tcp_port, run_uvicorn_app
from quicklook.job.job import Job
from quicklook.job.status_printer import JobStatusPrinter
from quicklook.types import VisitName
from quicklook.utils.pipeline import Stage

pytestmark = pytest.mark.slow


@pytest.fixture(scope='module', autouse=True)
async def reset_db():
    """テスト開始時にquickloooksテーブルをリセット"""
    async with get_session() as session:
        await session.execute(delete(Access))
        await session.execute(delete(Quicklook))
        await session.commit()


async def test_create_quicklook_pipeline():
    job = Job(VisitName('raw:broccoli'))
    job.watcher.on_change_status(print_job_status)
    ev = asyncio.Event()

    async def on_change(job: Job):
        if job.status.stage in {'ready', 'error'}:
            ev.set()
            assert job.status.stage == 'ready'

    job.watcher.on_change_status(on_change, which=lambda s: s.stage)

    async with quicklook_pipeline().run() as ph:
        await ph.push(job)
        await ev.wait()


@pytest.mark.skip("Skipping test_create_quicklook")
async def test_create_quicklook():
    job = Job(VisitName('raw:broccoli'))
    job.watcher.on_change_status(print_job_status)
    await create_quicklook(job)


printer = JobStatusPrinter()


async def print_job_status(job: Job):
    printer(job.watcher)


@pytest.fixture(scope='module', autouse=True)
def running_app(running_coordinator: 'RunningCoordinator'):
    with run_generators(running_coordinator.base_url):
        yield running_coordinator


@pytest.fixture(scope='module')
def running_coordinator():
    '''
    テストと同じプロセス内でuvicornを実行する。
    '''
    app = 'quicklook.coordinator.api.app:app'
    port = find_free_tcp_port()
    server = uvicorn.Server(uvicorn.Config(app, port=port, log_level='warning', ws='websockets-sansio'))
    t = threading.Thread(target=server.run, daemon=True)
    t.start()
    base_url = f'http://127.0.0.1:{port}'
    timeout = 5
    start = time.time()
    while time.time() - start < timeout:
        try:
            requests.get(f'{base_url}/healthz')
            break
        except requests.exceptions.ConnectionError:
            time.sleep(0.1)
    else:
        raise TimeoutError(f'{app} did not start in {timeout} seconds')

    def stop():
        server.should_exit = True

    try:
        yield RunningCoordinator(base_url, stop=stop)
    finally:
        stop()
        t.join()


@dataclass
class RunningCoordinator:
    base_url: str
    stop: Callable[[], None]


@contextmanager
def run_generators(
    coordinator_base_url: str,
    num_generators: int = 2,
):
    original_generator_port = config.generator_port
    original_coordinator_base_url = config.coordinator_base_url
    with ExitStack() as stack:
        try:
            for index in range(num_generators):
                config.generator_port = find_free_tcp_port()
                config.coordinator_base_url = coordinator_base_url
                stack.enter_context(
                    run_uvicorn_app(
                        'quicklook.generator.api.app:app',
                        port=config.generator_port,
                        log_prefix=f'[generator{index + 1}] ',
                        healthz='/healthz',
                        log_level='warning',
                    )
                )
            _wait_for_registered_generators(coordinator_base_url, num_generators)
            yield coordinator_base_url
        finally:
            config.generator_port = original_generator_port
            config.coordinator_base_url = original_coordinator_base_url


def _wait_for_registered_generators(
    coordinator_base_url: str,
    expected_count: int,
    timeout: float = 5.0,
) -> None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        response = requests.get(f'{coordinator_base_url}/comm/generators')
        if len(response.json().get('generators', {})) >= expected_count:
            return
        time.sleep(0.1)
    raise TimeoutError(f'Generators did not register within {timeout} seconds')
