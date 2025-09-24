import time

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

            # 成功のheartbeatを起動
            requests.post(f'{coordinator_runner.base_url}/comm/trigger-heartbeat')
            time.sleep(0.1)
            assert len(requests.get(f'{coordinator_runner.base_url}/comm/generators').json()['generators']) == 1

            # 失敗のheartbeatを起動し、Generatorが終了することを確認
            requests.post(f'{coordinator_runner.base_url}/comm/trigger-heartbeat?fail_for_test=True')
            time.sleep(0.1)
            assert len(requests.get(f'{coordinator_runner.base_url}/comm/generators').json()['generators']) == 0
