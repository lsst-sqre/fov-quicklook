from __future__ import annotations

from pathlib import Path

from deploy_broker.client import _settings_defaults


def test_client_defaults_to_local_broker(monkeypatch) -> None:
    monkeypatch.delenv("DEPLOY_BROKER_API_TOKEN", raising=False)
    monkeypatch.delenv("DEPLOY_BROKER_API_TOKEN_FILE", raising=False)
    monkeypatch.setattr("deploy_broker.client._fallback_api_token_files", lambda: ())
    monkeypatch.setattr("deploy_broker.client._fallback_base_url", lambda: "http://127.0.0.1:8010")

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
    monkeypatch.setattr("deploy_broker.client._fallback_api_token_files", lambda: ())

    _, api_token = _settings_defaults()

    assert api_token == "file-token"


def test_client_reads_broker_key_fallback(monkeypatch, tmp_path: Path) -> None:
    token_file = tmp_path / "broker-key"
    token_file.write_text("home-token", encoding="utf-8")
    monkeypatch.delenv("DEPLOY_BROKER_API_TOKEN", raising=False)
    monkeypatch.delenv("DEPLOY_BROKER_API_TOKEN_FILE", raising=False)
    monkeypatch.setattr(
        "deploy_broker.client._fallback_api_token_files",
        lambda: (token_file,),
    )

    _, api_token = _settings_defaults()

    assert api_token == "home-token"


def test_client_reads_broker_url_fallback(monkeypatch) -> None:
    monkeypatch.setattr(
        "deploy_broker.client._fallback_base_url",
        lambda: "https://broker.example.invalid",
    )
    monkeypatch.setattr("deploy_broker.client._fallback_api_token_files", lambda: ())

    server, _ = _settings_defaults()

    assert server == "https://broker.example.invalid"
