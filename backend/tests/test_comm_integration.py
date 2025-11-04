import time

import pytest
import requests

from quicklook.dev.run_uvicorn import run_uvicorn_app


def test_comm_integration():
    """CoordinatorとGeneratorの通信統合テスト"""

    # coordinatorを起動
    with run_uvicorn_app(
        'quicklook.dev.commapp:coordinator_app',
        port=9501,
        log_prefix='[coordinator] ',
        healthz='/comm/healthz',
    ) as coordinator_runner:
        coordinator_runner.wait_for_ready()
        assert len(requests.get(f'{coordinator_runner.base_url}/comm/generators').json()['generators']) == 0
        with run_uvicorn_app(
            'quicklook.dev.commapp:generator_app',
            port=9502,
            log_prefix='[generator] ',
            healthz='/comm/healthz',
        ) as generator_runner:
            generator_runner.wait_for_ready()

            assert len(requests.get(f'{coordinator_runner.base_url}/comm/generators').json()['generators']) == 1

            requests.post(f'{coordinator_runner.base_url}/comm/trigger-heartbeat')
            time.sleep(0.1)
            assert len(requests.get(f'{coordinator_runner.base_url}/comm/generators').json()['generators']) == 1

            requests.post(f'{coordinator_runner.base_url}/comm/trigger-heartbeat?fail_for_test=True')
            time.sleep(0.1)
            assert len(requests.get(f'{coordinator_runner.base_url}/comm/generators').json()['generators']) == 0


@pytest.mark.slow
def test_kill_generator():
    """kill_generator関数のテスト"""
    
    with run_uvicorn_app(
        'quicklook.dev.commapp:coordinator_app',
        port=9501,
        log_prefix='[coordinator] ',
        healthz='/comm/healthz',
    ) as coordinator_runner:
        coordinator_runner.wait_for_ready()
        
        with run_uvicorn_app(
            'quicklook.dev.commapp:generator_app',
            port=9502,
            log_prefix='[generator] ',
            healthz='/comm/healthz',
        ) as generator_runner:
            generator_runner.wait_for_ready()
            time.sleep(0.5)
            
            generators = requests.get(f'{coordinator_runner.base_url}/comm/generators').json()['generators']
            assert len(generators) == 1
            
            generator_id = list(generators.keys())[0]
            generator_info = generators[generator_id]
            
            response = requests.post(
                f"http://{generator_info['host']}:{generator_info['port']}/comm/shutdown"
            )
            assert response.status_code == 200
            
            time.sleep(1)
            
            try:
                requests.get(f"http://{generator_info['host']}:{generator_info['port']}/comm/healthz", timeout=1)
                assert False, "Generator should have been shut down"
            except requests.exceptions.RequestException:
                pass
