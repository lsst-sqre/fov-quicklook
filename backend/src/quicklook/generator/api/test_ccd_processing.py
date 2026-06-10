import pytest
from starlette.websockets import WebSocketState

from quicklook.generator.api import ccd_processing
from quicklook.generator.api.ccd_processing_protocol import CompletedMessage
from quicklook.job.job import Job
from quicklook.types import CcdName, VisitName


def test_validate_job_cache_version_accepts_matching_version(monkeypatch):
    monkeypatch.setattr(ccd_processing.config, 'tile_cache_schema_version', 4)

    ccd_processing.validate_job_cache_version(Job(VisitName('repo:raw:4242'), cache_version=4))


def test_validate_job_cache_version_rejects_mismatch(monkeypatch):
    monkeypatch.setattr(ccd_processing.config, 'tile_cache_schema_version', 4)

    with pytest.raises(RuntimeError, match='controller=3, generator=4'):
        ccd_processing.validate_job_cache_version(Job(VisitName('repo:raw:4242'), cache_version=3))


async def test_send_generator_message_skips_closed_websocket():
    class FakeWebSocket:
        client_state = WebSocketState.DISCONNECTED

        async def send_bytes(self, data: bytes) -> None:  # pragma: no cover
            raise AssertionError(f"send_bytes should not be called: {data!r}")

    await ccd_processing._send_generator_message(
        FakeWebSocket(),  # type: ignore[arg-type]
        CompletedMessage(ccd_name=CcdName('R00_S00')),
    )
