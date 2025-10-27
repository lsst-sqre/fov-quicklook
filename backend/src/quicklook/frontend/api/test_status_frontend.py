"""Tests for frontend status endpoint."""

import pytest
from unittest.mock import patch, mock_open, AsyncMock, MagicMock

from fastapi.testclient import TestClient

from quicklook.frontend.api.app import app
from quicklook.config import config


@pytest.fixture
def client():
    return TestClient(app)


def test_frontend_status_endpoint(client):
    """Test the /api/status endpoint returns system status."""
    with patch("builtins.open", mock_open(read_data="1048576")):
        with patch("quicklook.utils.system_status.socket.gethostname", return_value="frontend-container"):
            url = f"{config.frontend_app_prefix}/api/status"
            response = client.get(url)
            assert response.status_code == 200
            data = response.json()

            assert "frontend" in data
            assert data["frontend"]["container_name"] == "frontend-container"
            assert "coordinator" in data
            assert "generators" in data
            assert isinstance(data["generators"], dict)


def test_frontend_status_endpoint_coordinator_unreachable(client):
    """Test the /api/status endpoint when coordinator is unreachable."""
    with patch("builtins.open", mock_open(read_data="1048576")):
        with patch("quicklook.utils.system_status.socket.gethostname", return_value="frontend-container"):
            with patch("quicklook.utils.http_request.http_request") as mock_http:
                # Mock coordinator being unreachable
                mock_http.side_effect = Exception("Connection error")

                url = f"{config.frontend_app_prefix}/api/status"
                response = client.get(url)
                assert response.status_code == 200
                data = response.json()

                assert "frontend" in data
                assert data["frontend"]["container_name"] == "frontend-container"
                assert "coordinator" in data
                # Should have default status with zeros on error
                assert data["coordinator"]["memory_max"] == 0
                assert "generators" in data
                # generators should be a dict (possibly empty or with registered generators)
                assert isinstance(data["generators"], dict)
