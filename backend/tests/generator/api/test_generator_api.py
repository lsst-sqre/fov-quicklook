import io
from dataclasses import asdict

import pytest
from fastapi.testclient import TestClient

from quicklook.config import config
from quicklook.coordinator.tasks import GeneratorTask
from quicklook.generator.api import GeneratorRuntimeSettings, app
from quicklook.types import GeneratorPod, GeneratorProgress, ProcessCcdResult, Visit
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


def test_create_quicklook(client: TestClient):
    task = GeneratorTask(
        generator=GeneratorPod(host='localhost', port=8000),
        visit=Visit.from_id('raw:broccoli'),
        ccd_names=['R30_S20'],
        ccd_generator_map={},
    )
    res = client.post('/quicklooks', json=asdict(task))
    buf = io.BytesIO(res.content)
    while msg := message_from_stream(buf):
        assert isinstance(msg, (GeneratorProgress, ProcessCcdResult))

    assert res.status_code == 200
