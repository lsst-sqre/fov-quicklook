from __future__ import annotations

from pathlib import Path

import httpx

from deploy_broker.config import Settings
from deploy_broker.storage import TokenStore
from deploy_broker.verification import VerificationClient


def _settings(tmp_path: Path) -> Settings:
    return Settings(
        state_dir=tmp_path / "state",
        token_command=None,
        app_base_url="https://quicklook.example.invalid",
    )


def test_run_basic_checks_refreshes_token_after_auth_failure(
    tmp_path: Path, monkeypatch
) -> None:
    settings = _settings(tmp_path)
    token_store = TokenStore(settings)
    client = VerificationClient(settings, token_store)
    token_requests: list[bool] = []

    def _get_token(*, refresh: bool = False) -> str:
        token_requests.append(refresh)
        return "fresh-token" if refresh else "stale-token"

    monkeypatch.setattr(token_store, "get_app_token", _get_token)

    def handler(request: httpx.Request) -> httpx.Response:
        cookie = request.headers["Cookie"]
        if cookie == 'gafaelfawr="stale-token"':
            return httpx.Response(302)
        if request.url.path == "/api/healthz":
            return httpx.Response(200)
        if request.url.path == "/":
            return httpx.Response(200)
        raise AssertionError(f"unexpected path: {request.url.path}")

    transport = httpx.MockTransport(handler)
    real_client = httpx.Client
    monkeypatch.setattr(
        httpx,
        "Client",
        lambda **kwargs: real_client(transport=transport, **kwargs),
    )

    result = client.run_basic_checks("all")

    assert result["healthz_ok"] is True
    assert result["frontend_ok"] is True
    assert token_requests == [False, True]


def test_run_basic_checks_raises_when_status_stays_non_200(
    tmp_path: Path, monkeypatch
) -> None:
    settings = _settings(tmp_path)
    token_store = TokenStore(settings)
    client = VerificationClient(settings, token_store)

    monkeypatch.setattr(token_store, "get_app_token", lambda *, refresh=False: "bad-token")

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(302)

    transport = httpx.MockTransport(handler)
    real_client = httpx.Client
    monkeypatch.setattr(
        httpx,
        "Client",
        lambda **kwargs: real_client(transport=transport, **kwargs),
    )

    try:
        client.run_basic_checks("all")
    except RuntimeError as exc:
        assert "healthz returned 302" in str(exc)
        assert "frontend returned 302" in str(exc)
    else:
        raise AssertionError("expected RuntimeError for non-200 verification")
