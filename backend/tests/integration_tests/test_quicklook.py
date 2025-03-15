import json

import pytest
import requests
import websockets.sync.client as websockets
from websockets.exceptions import ConnectionClosedOK

from quicklook.config import config
from quicklook.frontend.api.quicklooks import QuicklookStatus


def test_frontend_ok():
    res = requests.get(f'http://127.0.0.1:{config.frontend_port}/api/healthz')
    assert res.status_code == 200
    assert len(res.json()) >= 1


def test_frontend_systeminfo():
    res = requests.get(f'http://127.0.0.1:{config.frontend_port}/api/system_info')
    assert res.status_code == 200
    assert len(res.json()) >= 1


def test_coodinator_ok():
    res = requests.get(f'http://127.0.0.1:{config.coordinator_port}/healthz')
    assert res.status_code == 200
    assert len(res.json()) >= 1


def test_list_visits():
    res = requests.get(f'http://127.0.0.1:{config.frontend_port}/api/visits')
    assert res.status_code == 200


@pytest.fixture(scope='module')
def one_quicklook_created(quicklooks_cleared):
    res = requests.post(f'http://127.0.0.1:{config.coordinator_port}/quicklooks', json={'visit': {'id': 'raw:broccoli'}})
    assert res.status_code == 200
    with websockets.connect(f'ws://127.0.0.1:{config.frontend_port}/api/quicklooks/raw:broccoli/status.ws') as ws:
        while True:
            try:
                print('.', end='', flush=True)
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


def test_get_tile_for_blank_region(one_quicklook_created):
    res = requests.get(f'http://127.0.0.1:{config.frontend_port}/api/quicklooks/raw:broccoli/tiles/0/0/0')
    assert res.status_code == 200
    assert res.headers['Content-Type'] == 'application/npy+zstd'


def test_get_fits_header(one_quicklook_created):
    res = requests.get(f'http://127.0.0.1:{config.frontend_port}/api/quicklooks/raw:broccoli/fits_header/R00_SG1')
    assert res.status_code == 200
    assert res.headers['Content-Type'] == 'application/json'
