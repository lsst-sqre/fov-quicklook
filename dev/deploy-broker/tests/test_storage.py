from __future__ import annotations

from pathlib import Path

import pytest

from deploy_broker.config import Settings
from deploy_broker.storage import JobStore, TokenStore


def _settings(tmp_path: Path) -> Settings:
    return Settings(state_dir=tmp_path / "state")


def test_bootstrap_from_curl_files_stores_tokens_and_removes_sources(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    settings.ensure_state_dirs()
    settings.argocd_bootstrap_curl_path.write_text(
        "curl -H 'Cookie: argocd.token=stored-argocd-token'",
        encoding="utf-8",
    )
    settings.app_bootstrap_curl_path.write_text(
        'curl -H \'Cookie: gafaelfawr="stored-app-token"\'',
        encoding="utf-8",
    )

    token_store = TokenStore(settings)

    assert sorted(token_store.bootstrap_from_curl_files()) == ["app", "argocd"]
    assert token_store.get_argocd_token() == "stored-argocd-token"
    assert token_store.get_app_token() == "stored-app-token"
    assert not settings.argocd_bootstrap_curl_path.exists()
    assert not settings.app_bootstrap_curl_path.exists()


def test_bootstrap_from_curl_files_rejects_empty_files(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    settings.ensure_state_dirs()
    settings.argocd_bootstrap_curl_path.write_text("", encoding="utf-8")

    with pytest.raises(ValueError, match="is empty"):
        TokenStore(settings).bootstrap_from_curl_files()


def test_job_store_create_sets_request_log_path(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    settings.ensure_state_dirs()

    record = JobStore(settings).create(
        tracked_branch="u/michitaro/fov-quicklook-test",
        verify_mode="auto",
    )

    assert record.request_log_path == str(settings.request_log_path(record.request_id))
