import time
import requests

from quicklook.dev.run_uvicorn import run_uvicorn_app


def test_comm_integration():
    """CoordinatorとGeneratorの通信統合テスト"""

    # coordinatorを起動
    with run_uvicorn_app('quicklook.dev.commapp:coordinator_app', port=9501, log_prefix='[coordinator] ') as wait_for_coordinator:
        wait_for_coordinator()
        assert len(requests.get('http://127.0.0.1:9501/generators').json()['generators']) == 0
        with run_uvicorn_app('quicklook.dev.commapp:generator_app', port=9502, log_prefix='[generator] ') as wait_for_generator:
            wait_for_generator()
            time.sleep(0.1)
            assert len(requests.get('http://127.0.0.1:9501/generators').json()['generators']) == 1

            # 成功のheartbeatを起動
            requests.post('http://127.0.0.1:9501/trigger-heartbeat')
            time.sleep(0.1)
            assert len(requests.get('http://127.0.0.1:9501/generators').json()['generators']) == 1

            # 失敗のheartbeatを起動し、Generatorが終了することを確認
            requests.post('http://127.0.0.1:9501/trigger-heartbeat?fail_for_test=True')
            time.sleep(0.1)
            assert len(requests.get('http://127.0.0.1:9501/generators').json()['generators']) == 0