import socket

from quicklook.utils import http_client


async def test_managed_session_uses_ipv4_connector(monkeypatch):
    connector_kwargs = {}
    closed = False

    class FakeConnector:
        def __init__(self, **kwargs):
            connector_kwargs.update(kwargs)

    class FakeSession:
        def __init__(self, *, connector):
            self.connector = connector

        async def close(self):
            nonlocal closed
            closed = True

    monkeypatch.setattr(http_client, "_session", None)
    monkeypatch.setattr(http_client.aiohttp, "TCPConnector", FakeConnector)
    monkeypatch.setattr(http_client.aiohttp, "ClientSession", FakeSession)

    async with http_client.managed_session():
        assert connector_kwargs["family"] == socket.AF_INET
        assert isinstance(http_client.get_session(), FakeSession)

    assert closed is True
