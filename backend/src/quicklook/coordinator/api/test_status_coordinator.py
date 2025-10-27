"""Tests for coordinator status endpoint."""

import pytest
from unittest.mock import patch, mock_open, AsyncMock, MagicMock
import asyncio

from fastapi.testclient import TestClient

from quicklook.coordinator.api.app import app


@pytest.fixture
def client():
    return TestClient(app)


def test_coordinator_status_endpoint(client):
    """Test the /status endpoint returns coordinator and generators status."""
    with patch("builtins.open", mock_open(read_data="1048576")):
        with patch("quicklook.utils.system_status.socket.gethostname", return_value="coordinator-container"):
            with patch("aiohttp.ClientSession") as mock_session_class:
                # Mock the generator response
                mock_response = AsyncMock()
                mock_response.status = 200
                mock_response.json = AsyncMock(
                    return_value={
                        "container_name": "generator-container",
                        "memory_max": 2097152,
                        "memory_current": 1048576,
                        "cpu_max": 50000,
                        "cpu_current": 123456789,
                        "uptime": 3600.0,
                    }
                )
                mock_response.raise_for_status = MagicMock()

                mock_session = AsyncMock()
                mock_session.get = AsyncMock()
                mock_session.get.return_value.__aenter__.return_value = mock_response
                mock_session_class.return_value.__aenter__.return_value = mock_session

                response = client.get("/status")
                assert response.status_code == 200
                data = response.json()

                assert "coordinator" in data
                assert data["coordinator"]["container_name"] == "coordinator-container"
                assert "generators" in data
                assert isinstance(data["generators"], dict)
