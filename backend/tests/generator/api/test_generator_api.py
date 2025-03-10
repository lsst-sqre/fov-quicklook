import io
from dataclasses import asdict

import pytest
from fastapi.testclient import TestClient

from quicklook.config import config
from quicklook.coordinator.quicklookjob.tasks import GenerateTask
from quicklook.generator.api import GeneratorRuntimeSettings, app
from quicklook.types import GeneratorPod, GenerateProgress, CcdMeta, Visit
from quicklook.utils.message import message_from_stream

# pytestmark = pytest.mark.focus


@pytest.fixture(scope='module')
def client():
    with GeneratorRuntimeSettings.stack.push(GeneratorRuntimeSettings(port=config.generator_port)):
        with TestClient(app) as client:
            yield client


def test_healthz(client: TestClient):
    res = client.get('/healthz')
    assert res.status_code == 200


def test_pod_status(client: TestClient):
    res = client.get('/pod_status')
    assert res.status_code == 200


def test_create_quicklook(client: TestClient):
    task = GenerateTask(
        generator=GeneratorPod(host='localhost', port=8000),
        visit=Visit.from_id('raw:broccoli'),
        ccd_names=['R30_S20'],
    )
    res = client.post('/quicklooks', json=asdict(task))
    buf = io.BytesIO(res.content)
    while msg := message_from_stream(buf):
        assert isinstance(msg, (GenerateProgress, CcdMeta))

    assert res.status_code == 200
