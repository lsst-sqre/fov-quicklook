from __future__ import annotations

from pathlib import Path

from deploy_broker.config import Settings


def test_settings_use_external_cwd_as_state_dir(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("DEPLOY_BROKER_STATE_DIR", raising=False)
    monkeypatch.delenv("DEPLOY_BROKER_API_TOKEN_FILE", raising=False)

    settings = Settings()

    assert settings.state_dir == tmp_path
    assert settings.api_token_path == tmp_path / "broker.key"


def test_settings_use_repo_default_state_dir_inside_repo(monkeypatch) -> None:
    project_dir = Path(__file__).resolve().parents[1]
    monkeypatch.chdir(project_dir)
    monkeypatch.delenv("DEPLOY_BROKER_STATE_DIR", raising=False)
    monkeypatch.delenv("DEPLOY_BROKER_API_TOKEN_FILE", raising=False)

    settings = Settings()

    assert settings.state_dir == project_dir / "state"
    assert settings.api_token_path == project_dir / "state" / "broker.key"


def test_explicit_token_command_none_overrides_environment(
    monkeypatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("DEPLOY_BROKER_TOKEN_COMMAND", "fetch-real-prod-token")

    settings = Settings(state_dir=tmp_path / "state", token_command=None)

    assert settings.token_command is None
