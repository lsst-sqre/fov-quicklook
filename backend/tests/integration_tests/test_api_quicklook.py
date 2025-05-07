import json
import time

import numpy
import pytest
import requests
import websockets.sync.client as websockets
from websockets.exceptions import ConnectionClosedOK

from quicklook.config import config
from quicklook.coordinator.quicklookjob.job import QuicklookJobPhase
from quicklook.frontend.api.quicklooks import QuicklookStatus
from quicklook.mutableconfig import MutableConfig
from quicklook.utils import zstd


def test_frontend_ok():
    res = requests.get(f'http://127.0.0.1:{config.frontend_port}/api/healthz')
    assert res.status_code == 200
    assert len(res.json()) >= 1


def test_frontend_systeminfo():
    res = requests.get(f'http://127.0.0.1:{config.frontend_port}/api/system_info')
    assert res.status_code == 200
    assert len(res.json()) >= 1


def test_frontend_status():
    res = requests.get(f'http://127.0.0.1:{config.frontend_port}/api/status')
    assert res.status_code == 200
    assert len(res.json()) >= 1


def test_coodinator_ok():
    res = requests.get(f'http://127.0.0.1:{config.coordinator_port}/healthz')
    assert res.status_code == 200
    assert len(res.json()) >= 1


def test_list_visits():
    res = requests.get(f'http://127.0.0.1:{config.frontend_port}/api/visits')
    assert res.status_code == 200


def update_mutable_config(new: dict):
    res = requests.post(
        f'http://127.0.0.1:{config.coordinator_port}/mutable-config',
        json=new,
    )
    assert res.status_code == 200


@pytest.fixture(scope='module', params=['GENERATE_DONE', 'MERGE_DONE', 'READY'])
def one_quicklook_created(request):
    job_stop_at = request.param
    update_mutable_config({'new': {'job_stop_at': job_stop_at}})

    clear_quicklooks()

    res = requests.post(f'http://127.0.0.1:{config.frontend_port}/api/quicklooks', json={'id': 'raw:broccoli'})
    assert res.status_code == 200
    with websockets.connect(f'ws://127.0.0.1:{config.frontend_port}/api/quicklooks/raw:broccoli/status.ws') as ws:
        while True:
            try:
                print('.', end='', flush=True)
                status = json.loads(ws.recv())
                if isinstance(status, dict):
                    if status['phase'] in {QuicklookJobPhase.READY, QuicklookJobPhase.FAILED, QuicklookJobPhase[job_stop_at]}:
                        break
            except ConnectionClosedOK:
                break
    yield job_stop_at
    time.sleep(1.5)  # テスト時にはjob_runnerが処理完了の1秒後にもう１度通知を行うため。


def test_create_quicklook(one_quicklook_created):
    # This only tests the fixture one_quicklook_created
    pass


def test_show_quicklook(one_quicklook_created):
    res = requests.get(f'http://127.0.0.1:{config.frontend_port}/api/quicklooks/raw:broccoli/status')
    assert res.status_code == 200
    QuicklookStatus.model_validate(res.json())


# def test_list_quicklooks(one_quicklook_created):
#     res = requests.get(f'http://127.0.0.1:{config.frontend_port}/api/quicklooks')
#     assert res.status_code == 200
#     response_json = res.json()
#     assert len(response_json) == 1
#     QuicklookStatus.model_validate(response_json[0])


def test_get_tile(one_quicklook_created):
    res = requests.get(f'http://127.0.0.1:{config.frontend_port}/api/quicklooks/raw:broccoli/tiles/8/0/0')
    assert res.status_code == 200
    match one_quicklook_created:
        case 'READY':
            assert res.headers['x-quicklook-phase'] == 'READY'
            assert res.headers['Content-Type'] == 'application/npy+zstd'
            assert res.content[:4] == b'\x28\xb5\x2f\xfd'
            assert is_valid_compressed_numpy_bytes(res.content)
        case 'GENERATE_DONE':
            assert res.headers['x-quicklook-phase'] == 'GENERATE_DONE'
            assert res.headers['Content-Type'] == 'application/npy'
            assert is_valid_numpy_bytes(res.content)
        case 'MERGE_DONE':
            assert res.headers['x-quicklook-phase'] == 'MERGE_DONE'
            assert res.headers['Content-Type'] == 'application/npy+zstd'
            assert res.content[:4] == b'\x28\xb5\x2f\xfd'
            assert is_valid_compressed_numpy_bytes(res.content)
        case _:
            assert False, f'Unexpected one_quicklook_created: {one_quicklook_created}'


def test_get_tile_for_blank_region(one_quicklook_created):
    res = requests.get(f'http://127.0.0.1:{config.frontend_port}/api/quicklooks/raw:broccoli/tiles/0/0/0')
    assert res.status_code == 200
    assert res.headers['x-quicklook-error'] == 'Tile not found'
    match one_quicklook_created:
        case 'READY':
            assert res.headers['Content-Type'] == 'application/npy+zstd'
            assert res.headers['x-quicklook-phase'] == 'READY'
            assert is_valid_compressed_numpy_bytes(res.content)
        case 'GENERATE_DONE':
            assert res.headers['Content-Type'] == 'application/npy+zstd'
            assert res.headers['x-quicklook-phase'] == 'GENERATE_DONE'
            assert is_valid_compressed_numpy_bytes(res.content)
        case 'MERGE_DONE':
            assert res.headers['Content-Type'] == 'application/npy+zstd'
            assert res.headers['x-quicklook-phase'] == 'MERGE_DONE'
            assert is_valid_compressed_numpy_bytes(res.content)
        case _:
            assert False, f'Unexpected one_quicklook_created: {one_quicklook_created}'


def is_valid_numpy_bytes(data: bytes) -> bool:
    return data[:6] == b'\x93NUMPY'


def is_valid_compressed_numpy_bytes(data: bytes) -> bool:
    raw = zstd.decompress(data)
    return is_valid_numpy_bytes(raw)


def test_get_fits_header(one_quicklook_created):
    res = requests.get(f'http://127.0.0.1:{config.frontend_port}/api/quicklooks/raw:broccoli/fits_header/R00_SG1')
    assert res.status_code == 200
    assert res.headers['Content-Type'] == 'application/json'


def clear_quicklooks():
    res = requests.delete(f'http://127.0.0.1:{config.frontend_port}/api/quicklooks/*')
    assert res.status_code == 200

    res = requests.get(f'http://127.0.0.1:{config.coordinator_port}/quicklooks')
    assert res.status_code == 200
    assert len(res.json()) == 0
