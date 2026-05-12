from __future__ import annotations

import json
import sys
from pathlib import Path

from deploy_broker.client import _settings_defaults


def test_client_defaults_to_local_broker(monkeypatch) -> None:
    monkeypatch.delenv("DEPLOY_BROKER_API_TOKEN", raising=False)

    server, api_token = _settings_defaults()

    assert server == "http://127.0.0.1:8010"
    assert api_token is None


def test_client_uses_explicit_api_token_env(monkeypatch) -> None:
    monkeypatch.setenv("DEPLOY_BROKER_API_TOKEN", "env-token")

    _, api_token = _settings_defaults()

    assert api_token == "env-token"


def test_client_reads_explicit_api_token_file(monkeypatch, tmp_path: Path) -> None:
    token_file = tmp_path / "broker.key"
    token_file.write_text("file-token", encoding="utf-8")
    monkeypatch.delenv("DEPLOY_BROKER_API_TOKEN", raising=False)
    monkeypatch.setenv("DEPLOY_BROKER_API_TOKEN_FILE", str(token_file))

    _, api_token = _settings_defaults()

    assert api_token == "file-token"


def test_main_passes_refresh_flag_to_get_app_token(monkeypatch, capsys) -> None:
    calls: list[tuple[str, bool]] = []

    class _FakeClient:
        def __init__(self, server: str, api_token: str | None) -> None:
            assert server == "http://broker.invalid"
            assert api_token == "secret-token"

        def get_app_token(self, *, refresh: bool = False) -> dict[str, str]:
            calls.append(("get_app_token", refresh))
            return {"token": "fresh-app-token"}

        def close(self) -> None:
            calls.append(("close", False))

    monkeypatch.setattr("deploy_broker.client.BrokerClient", _FakeClient)
    monkeypatch.setattr(sys, "argv", ["deploy-broker-client", "--server", "http://broker.invalid", "--api-token", "secret-token", "get-app-token", "--refresh"])

    from deploy_broker.client import main

    main()

    output = capsys.readouterr()
    assert json.loads(output.out) == {"token": "fresh-app-token"}
    assert calls == [("get_app_token", True), ("close", False)]
