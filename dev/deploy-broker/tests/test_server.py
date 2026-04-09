from __future__ import annotations

import json
from pathlib import Path

from fastapi.testclient import TestClient
from pytest import MonkeyPatch

from deploy_broker.config import Settings
from deploy_broker.server import create_app


def _settings(tmp_path: Path) -> Settings:
    return Settings(
        api_token="secret-token",
        state_dir=tmp_path / "state",
    )


def test_get_app_token_requires_configured_token(tmp_path: Path) -> None:
    app = create_app(_settings(tmp_path))
    client = TestClient(app, base_url="http://example.invalid")

    response = client.get(
        "/v1/tokens/app",
        headers={"Authorization": "Bearer secret-token"},
    )

    assert response.status_code == 503
    assert response.json() == {"detail": "App access token is not configured"}


def test_auth_is_required_for_non_loopback_requests(tmp_path: Path) -> None:
    app = create_app(_settings(tmp_path))
    client = TestClient(app, base_url="http://example.invalid")

    response = client.get("/v1/tokens/app")

    assert response.status_code == 401


def test_auth_is_not_required_for_loopback_requests(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    token_dir = settings.token_dir
    token_dir.mkdir(parents=True, exist_ok=True)
    (token_dir / "app.token").write_text("stored-app-token", encoding="utf-8")
    app = create_app(settings)
    client = TestClient(app, base_url="http://127.0.0.1:8010")

    response = client.get("/v1/tokens/app")

    assert response.status_code == 200
    assert response.json() == {"token": "stored-app-token"}


def test_healthz_writes_http_audit_log(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    app = create_app(settings)
    client = TestClient(app, base_url="http://example.invalid")

    response = client.get("/healthz")

    entries = [
        json.loads(line)
        for line in settings.audit_log_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    entry = entries[-1]
    assert response.status_code == 200
    assert response.headers["X-Request-ID"]
    assert entry["event"] == "http.request"
    assert entry["path"] == "/healthz"
    assert entry["resource"] == "healthz"
    assert entry["status_code"] == 200
    assert entry["auth_mode"] == "missing"


def test_get_app_token_logs_audit_event(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    settings.token_dir.mkdir(parents=True, exist_ok=True)
    (settings.token_dir / "app.token").write_text("stored-app-token", encoding="utf-8")
    app = create_app(settings)
    client = TestClient(app, base_url="http://example.invalid")

    response = client.get(
        "/v1/tokens/app",
        headers={"Authorization": "Bearer secret-token"},
    )

    entries = [
        json.loads(line)
        for line in settings.audit_log_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert response.status_code == 200
    assert any(entry["event"] == "app-token.read" for entry in entries)


def test_argocd_sync_endpoint_calls_service(tmp_path: Path, monkeypatch: MonkeyPatch) -> None:
    app = create_app(_settings(tmp_path))
    monkeypatch.setattr(app.state.service, "argocd_sync", lambda: {"synced": True})
    client = TestClient(app, base_url="http://example.invalid")

    response = client.post(
        "/v1/argocd/sync",
        headers={"Authorization": "Bearer secret-token"},
    )

    assert response.status_code == 200
    assert response.json() == {"synced": True}


def test_argocd_restart_endpoint_passes_components(
    tmp_path: Path, monkeypatch: MonkeyPatch
) -> None:
    app = create_app(_settings(tmp_path))
    captured: dict[str, list[str]] = {}

    def _restart(components: list[str]) -> dict[str, object]:
        captured["components"] = components
        return {"restarted": [f"fov-quicklook-{name}" for name in components]}

    monkeypatch.setattr(app.state.service, "argocd_restart", _restart)
    client = TestClient(app, base_url="http://example.invalid")

    response = client.post(
        "/v1/argocd/restart",
        headers={"Authorization": "Bearer secret-token"},
        json={"components": ["frontend"]},
    )

    assert response.status_code == 200
    assert captured["components"] == ["frontend"]
    assert response.json() == {"restarted": ["fov-quicklook-frontend"]}
