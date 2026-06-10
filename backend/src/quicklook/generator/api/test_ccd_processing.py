import pickle

import pytest
from fastapi.testclient import TestClient

from quicklook.generator.api import ccd_processing
from quicklook.generator.api.app import app
from quicklook.generator.api.ccd_processing_protocol import AssignCcdMessage, CompletedMessage, InitJobMessage, ProgressMessage
from quicklook.generator.generate_single_fits_tiles import CcdMetadata, GenerateSingleFitsTilesProgress
from quicklook.generator.preprocess_ccd import ImageStat
from quicklook.job.job import Job
from quicklook.types import CcdDataRef, CcdName, Progress, VisitName
from quicklook.utils.geom import BBox


@pytest.fixture
def client():
    return TestClient(app)


def test_validate_job_cache_version_accepts_matching_version(monkeypatch):
    monkeypatch.setattr(ccd_processing.config, 'tile_cache_schema_version', 4)

    ccd_processing.validate_job_cache_version(Job(VisitName('repo:raw:4242'), cache_version=4))


def test_validate_job_cache_version_rejects_mismatch(monkeypatch):
    monkeypatch.setattr(ccd_processing.config, 'tile_cache_schema_version', 4)

    with pytest.raises(RuntimeError, match='controller=3, generator=4'):
        ccd_processing.validate_job_cache_version(Job(VisitName('repo:raw:4242'), cache_version=3))


def test_generate_tiles_websocket_relays_progress_and_completion(monkeypatch, client):
    def fake_pipeline(_job, refs):
        for ref in list(refs):
            yield GenerateSingleFitsTilesProgress(ccd_name=ref.ccd, progress=Progress(total=4, count=1))
            yield CcdMetadata(
                ccd_name=ref.ccd,
                image_stat=ImageStat(
                    median=0.0,
                    mad=1.0,
                    shape=(1, 1),
                ),
                amps=[],
                bbox=BBox(0, 0, 1, 1),
            )

    monkeypatch.setattr(ccd_processing, 'generate_single_fits_tiles_pipeline', fake_pipeline)
    monkeypatch.setattr(ccd_processing, 'validate_job_cache_version', lambda _job: None)

    with client.websocket_connect('/jobs/test/generate-tiles') as ws:
        job = Job(VisitName('repo:raw:123'))
        ref = CcdDataRef(job.visit, CcdName('R00_S00'))

        ws.send_bytes(pickle.dumps(InitJobMessage(job=job)))
        ws.send_bytes(pickle.dumps(AssignCcdMessage(ccd_ref=ref)))
        ws.send_bytes(pickle.dumps(AssignCcdMessage(ccd_ref=None)))

        progress_msg = pickle.loads(ws.receive_bytes())
        completed_msg = pickle.loads(ws.receive_bytes())

    assert isinstance(progress_msg, ProgressMessage)
    assert progress_msg.ccd_name == ref.ccd
    assert progress_msg.progress == Progress(total=4, count=1)

    assert isinstance(completed_msg, CompletedMessage)
    assert completed_msg.ccd_name == ref.ccd
