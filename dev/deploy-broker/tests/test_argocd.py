from __future__ import annotations

import json
from pathlib import Path

import httpx

from deploy_broker.argocd import ArgoCdClient
from deploy_broker.config import Settings
from deploy_broker.storage import TokenStore


def _settings(tmp_path: Path) -> Settings:
    return Settings(
        api_token="secret-token",
        state_dir=tmp_path / "state",
        token_command=None,
        argocd_base_url="https://argocd.example.invalid",
    )


def test_set_branch_updates_image_tag_override(tmp_path: Path, monkeypatch) -> None:
    settings = _settings(tmp_path)
    token_store = TokenStore(settings)
    token_store.set_argocd_token("bootstrap-argocd-token")
    client = ArgoCdClient(settings, token_store)
    requests: list[httpx.Request] = []

    app_info = {
        "spec": {
            "source": {
                "repoURL": "https://github.com/lsst-sqre/phalanx.git",
                "path": "applications/fov-quicklook",
                "targetRevision": "main",
                "helm": {
                    "parameters": [
                        {"name": "global.host", "value": "example.invalid"},
                        {"name": "image.tag", "value": "old-tag"},
                    ]
                },
            }
        }
    }

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if request.method == "GET":
            return httpx.Response(200, json=app_info)
        if request.method == "PATCH":
            return httpx.Response(200, json=app_info)
        raise AssertionError(f"unexpected request: {request.method} {request.url}")

    transport = httpx.MockTransport(handler)
    monkeypatch.setattr(client, "_http", lambda: httpx.Client(transport=transport))

    client.set_branch("u/michitaro/fov-quicklook-test", image_tag="new-tag")

    patch_request = requests[1]
    payload = json.loads(patch_request.content.decode("utf-8"))
    patch = json.loads(payload["patch"])
    parameters = patch["spec"]["source"]["helm"]["parameters"]

    assert patch["spec"]["source"]["targetRevision"] == "u/michitaro/fov-quicklook-test"
    assert {"name": "global.host", "value": "example.invalid"} in parameters
    assert {"name": "image.tag", "value": "new-tag"} in parameters
    assert not any(
        parameter.get("name") == "image.tag" and parameter.get("value") == "old-tag"
        for parameter in parameters
    )


def test_get_branch_refreshes_token_after_auth_failure(
    tmp_path: Path, monkeypatch
) -> None:
    settings = _settings(tmp_path)
    token_store = TokenStore(settings)
    client = ArgoCdClient(settings, token_store)
    token_requests: list[bool] = []

    def _get_token(*, refresh: bool = False) -> str:
        token_requests.append(refresh)
        return "fresh-token" if refresh else "stale-token"

    monkeypatch.setattr(token_store, "get_argocd_token", _get_token)

    app_info = {
        "spec": {
            "source": {
                "repoURL": "https://github.com/lsst-sqre/phalanx.git",
                "path": "applications/fov-quicklook",
                "targetRevision": "main",
            }
        }
    }

    def handler(request: httpx.Request) -> httpx.Response:
        if request.headers["Cookie"] == "argocd.token=stale-token":
            return httpx.Response(401, json={"message": "expired"})
        if request.headers["Cookie"] == "argocd.token=fresh-token":
            return httpx.Response(200, json=app_info)
        raise AssertionError(f"unexpected request headers: {request.headers}")

    transport = httpx.MockTransport(handler)
    monkeypatch.setattr(client, "_http", lambda: httpx.Client(transport=transport))

    branch = client.get_branch()

    assert branch.branch == "main"
    assert token_requests == [False, True]
