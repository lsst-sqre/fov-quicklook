"""Tests for generator status endpoint."""

import pytest
from unittest.mock import patch, mock_open, AsyncMock
from fastapi.testclient import TestClient

from quicklook.generator.api.app import app


@pytest.fixture
def client():
    return TestClient(app)


def test_generator_status_endpoint(client):
    """Test the /status endpoint returns ContainerStatus."""
    with patch("builtins.open", mock_open(read_data="1048576")):
        with patch("quicklook.utils.system_status.socket.gethostname", return_value="generator-container"):
            response = client.get("/status")
            assert response.status_code == 200
            data = response.json()
            
            assert "container_name" in data
            assert data["container_name"] == "generator-container"
            assert "memory_max" in data
            assert "memory_current" in data
            assert "cpu_max" in data
            assert "cpu_current" in data
            assert "uptime" in data
