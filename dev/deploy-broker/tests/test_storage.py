from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from deploy_broker.config import Settings
from deploy_broker.storage import TokenStore


def _settings(tmp_path: Path) -> Settings:
    return Settings(state_dir=tmp_path / "state", token_command=None)


def test_refresh_tokens_reads_json_from_command_and_caches_both_tokens(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    settings = _settings(tmp_path).model_copy(
        update={"token_command": "fetch-broker-tokens --json"}
    )
    token_store = TokenStore(settings)

    def _run(*args, **kwargs) -> subprocess.CompletedProcess[str]:
        assert args[0] == ["fetch-broker-tokens", "--json"]
        return subprocess.CompletedProcess(
            args=args[0],
            returncode=0,
            stdout='{"argocd_token":"stored-argocd-token","gafaelfawr_token":"stored-app-token"}',
            stderr="",
        )

    monkeypatch.setattr(subprocess, "run", _run)

    assert sorted(token_store.refresh_tokens()) == ["app", "argocd"]
    assert token_store.get_argocd_token() == "stored-argocd-token"
    assert token_store.get_app_token() == "stored-app-token"
    assert (
        settings.token_dir / "argocd.token"
    ).read_text(encoding="utf-8") == "stored-argocd-token"
    assert (settings.token_dir / "app.token").read_text(encoding="utf-8") == "stored-app-token"


def test_get_token_runs_command_when_cache_missing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    settings = _settings(tmp_path).model_copy(update={"token_command": "fetch-broker-tokens"})
    token_store = TokenStore(settings)
    calls = 0

    def _run(*args, **kwargs) -> subprocess.CompletedProcess[str]:
        nonlocal calls
        calls += 1
        return subprocess.CompletedProcess(
            args=args[0],
            returncode=0,
            stdout='{"argocd_token":"fresh-argocd","gafaelfawr_token":"fresh-app"}',
            stderr="",
        )

    monkeypatch.setattr(subprocess, "run", _run)

    assert token_store.get_argocd_token() == "fresh-argocd"
    assert token_store.get_app_token() == "fresh-app"
    assert calls == 1


def test_get_token_refreshes_when_requested(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    settings = _settings(tmp_path).model_copy(update={"token_command": "fetch-broker-tokens"})
    token_store = TokenStore(settings)
    token_store.set_argocd_token("stale-argocd")
    token_store.set_app_token("stale-app")

    def _run(*args, **kwargs) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(
            args=args[0],
            returncode=0,
            stdout='{"argocd_token":"fresh-argocd","gafaelfawr_token":"fresh-app"}',
            stderr="",
        )

    monkeypatch.setattr(subprocess, "run", _run)

    assert token_store.get_argocd_token(refresh=True) == "fresh-argocd"
    assert token_store.get_app_token() == "fresh-app"


def test_get_token_reuses_disk_cache_across_store_instances(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    settings = _settings(tmp_path).model_copy(update={"token_command": "fetch-broker-tokens"})
    calls = 0

    def _run(*args, **kwargs) -> subprocess.CompletedProcess[str]:
        nonlocal calls
        calls += 1
        return subprocess.CompletedProcess(
            args=args[0],
            returncode=0,
            stdout='{"argocd_token":"fresh-argocd","gafaelfawr_token":"fresh-app"}',
            stderr="",
        )

    monkeypatch.setattr(subprocess, "run", _run)

    assert TokenStore(settings).get_argocd_token() == "fresh-argocd"
    assert TokenStore(settings).get_app_token() == "fresh-app"
    assert calls == 1


def test_get_token_requires_configuration_when_cache_missing(tmp_path: Path) -> None:
    with pytest.raises(RuntimeError, match="App access token is not configured"):
        TokenStore(_settings(tmp_path)).get_app_token()


def test_get_token_normalizes_quoted_disk_cache(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    settings.token_dir.mkdir(parents=True, exist_ok=True)
    (settings.token_dir / "app.token").write_text('"cached-app-token"', encoding="utf-8")

    assert TokenStore(settings).get_app_token() == "cached-app-token"


def test_refresh_tokens_rejects_invalid_json(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    settings = _settings(tmp_path).model_copy(update={"token_command": "fetch-broker-tokens"})

    def _run(*args, **kwargs) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(
            args=args[0],
            returncode=0,
            stdout='{"argocd_token":"stored-argocd-token"}',
            stderr="",
        )

    monkeypatch.setattr(subprocess, "run", _run)

    with pytest.raises(RuntimeError, match="gafaelfawr_token"):
        TokenStore(settings).refresh_tokens()


def test_refresh_tokens_normalizes_quoted_app_token(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    settings = _settings(tmp_path).model_copy(update={"token_command": "fetch-broker-tokens"})

    def _run(*args, **kwargs) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(
            args=args[0],
            returncode=0,
            stdout='{"argocd_token":"stored-argocd-token","gafaelfawr_token":"\\"stored-app-token\\""}',
            stderr="",
        )

    monkeypatch.setattr(subprocess, "run", _run)

    assert TokenStore(settings).refresh_tokens() == ["argocd", "app"]
    assert TokenStore(settings).get_app_token() == "stored-app-token"
