import json

import pytest
import requests
import websockets.sync.client as websockets
from websockets.exceptions import ConnectionClosedOK

from quicklook.config import config
from quicklook.coordinator.quicklookjob.job import QuicklookJobPhase
from quicklook.frontend.api.quicklooks import QuicklookStatus


@pytest.fixture(scope='module')
def one_quicklook_no_transfer_created(quicklooks_cleared):
    res = requests.post(f'http://127.0.0.1:{config.coordinator_port}/quicklooks', json={'visit': {'id': 'raw:broccoli'}, 'no_transfer': True})
    assert res.status_code == 200
    with websockets.connect(f'ws://127.0.0.1:{config.frontend_port}/api/quicklooks/raw:broccoli/status.ws') as ws:
        while True:
            try:
                print('.', end='', flush=True)
                status = json.loads(ws.recv())
                if isinstance(status, dict):
                    if status['phase'] in {QuicklookJobPhase.READY, QuicklookJobPhase.FAILED}:
                        break
            except ConnectionClosedOK:
                break


def test_create_quicklook_no_transfer(one_quicklook_no_transfer_created):
    # This only tests the fixture one_quicklook_no_transfer_created
    pass


def test_show_quicklook_no_transfer(one_quicklook_no_transfer_created):
    res = requests.get(f'http://127.0.0.1:{config.frontend_port}/api/quicklooks/raw:broccoli/status')
    assert res.status_code == 200
    QuicklookStatus.model_validate(res.json())


def test_get_tile_no_transfer(one_quicklook_no_transfer_created):
    res = requests.get(f'http://127.0.0.1:{config.frontend_port}/api/quicklooks/raw:broccoli/tiles/8/0/0')
    assert res.status_code == 200
    assert res.headers.get('x-quicklook-phase') in {'MERGE_DONE', 'GENERATE_DONE'}
    assert res.headers['Content-Type'] == 'application/npy'


def test_get_tile_for_blank_region_no_transfer(one_quicklook_no_transfer_created):
    res = requests.get(f'http://127.0.0.1:{config.frontend_port}/api/quicklooks/raw:broccoli/tiles/0/0/0')
    assert res.status_code == 200
    assert res.headers.get('x-quicklook-phase') in {'MERGE_DONE', 'GENERATE_DONE'}
    assert res.headers.get('x-quicklook-error') == 'Tile not found'
    assert res.headers['Content-Type'] == 'application/npy+zstd'


def test_get_fits_header_no_transfer(one_quicklook_no_transfer_created):
    res = requests.get(f'http://127.0.0.1:{config.frontend_port}/api/quicklooks/raw:broccoli/fits_header/R00_SG1')
    assert res.status_code == 200
    assert res.headers['Content-Type'] == 'application/json'
