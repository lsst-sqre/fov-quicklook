import fastapi
import pytest
from fastapi.testclient import TestClient
from fastapi import HTTPException, status

from quicklook.frontend.api import app
from quicklook.frontend.api.hips.router import validate_path


@pytest.fixture(scope='module')
def client():
    with TestClient(app) as client:
        yield client


def test_get_hips_file_with_invalid_path(client: TestClient):
    """Test that get_hips_file returns 404 for invalid paths."""
    # Test path starting with ..
    response = client.get("/api/hips/repo1//config")
    assert response.status_code == 404


@pytest.mark.parametrize("path", ["tiles/dir", "something.jpg", "nested/folder/structure/file.png", "Allsky.jpg"])
def test_valid_paths(path: str) -> None:
    """有効なパスが正しく検証されることをテスト"""
    result = validate_path(path)
    assert result == path, f"Expected '{path}' to be valid, but got '{result}'"


@pytest.mark.parametrize(
    "path",
    [
        "../config",
        "/etc/passwd",
        "tiles/../../../etc/passwd",
        "normal/path/../../../etc/passwd",
    ],
)
def test_invalid_paths(path: str) -> None:
    """無効なパスが適切に拒否されることをテスト"""
    with pytest.raises(HTTPException) as excinfo:
        validate_path(path)
    assert excinfo.value.status_code == status.HTTP_404_NOT_FOUND


def test_edge_cases() -> None:
    """エッジケースのテスト"""
    # Empty path should be normalized to "."
    assert validate_path("") == "."

    # Path with just dots
    with pytest.raises(HTTPException):
        validate_path("..")

    # Double slashes should be normalized
    assert validate_path("folder//file.txt") == "folder/file.txt"

    # Current directory reference should be removed
    assert validate_path("./file.txt") == "file.txt"


def test_hips_path_with_leading_slash(client: TestClient):
    """Test that paths starting with a slash are rejected"""
    response = client.get("/api/hips/repo1//config")
    assert response.status_code == 404
