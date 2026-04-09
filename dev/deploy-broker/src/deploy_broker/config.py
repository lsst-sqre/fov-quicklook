from __future__ import annotations

import os
import secrets
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[4]


def _project_dir() -> Path:
    return _repo_root() / "dev" / "deploy-broker"


def _running_inside_repo() -> bool:
    cwd = Path.cwd().resolve()
    try:
        cwd.relative_to(_repo_root())
    except ValueError:
        return False
    return True


def _state_dir() -> Path:
    if _running_inside_repo():
        return _project_dir() / "state"
    return Path.cwd().resolve()


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="DEPLOY_BROKER_", extra="ignore")

    host: str = "127.0.0.1"
    port: int = 8010
    api_token: str | None = None
    api_token_file: Path | None = None

    state_dir: Path = Field(default_factory=_state_dir)

    app_repo_slug: str = "lsst-sqre/fov-quicklook"
    app_repo_url: str = "https://github.com/lsst-sqre/fov-quicklook.git"
    app_remote_name: str = "origin"
    app_workflow_file: str = "build-and-push.yml"

    phalanx_repo_url: str = "https://github.com/lsst-sqre/phalanx.git"

    argocd_server: str = "usdf-rsp-dev.slac.stanford.edu"
    argocd_base_url: str = "https://usdf-rsp-dev.slac.stanford.edu/argo-cd"
    argocd_app_name: str = "fov-quicklook"
    argocd_namespace: str = "fov-quicklook"
    expected_argocd_path: str = "applications/fov-quicklook"
    argocd_timeout_seconds: int = 120
    argocd_connect_timeout_seconds: int = 15

    app_base_url: str = "https://usdf-rsp-dev.slac.stanford.edu/fov-quicklook"

    build_wait_seconds: int = 1800
    build_poll_seconds: int = 15

    log_level: str = "INFO"
    log_max_bytes: int = 5_000_000
    log_backup_count: int = 5

    @property
    def repo_root(self) -> Path:
        return _repo_root()

    @property
    def token_dir(self) -> Path:
        return self.state_dir / "tokens"

    @property
    def log_dir(self) -> Path:
        return self.state_dir / "logs"

    @property
    def audit_log_path(self) -> Path:
        return self.log_dir / "broker-audit.jsonl"

    def request_log_path(self, request_id: str) -> Path:
        return self.request_dir / request_id / "broker.log"

    @property
    def bootstrap_dir(self) -> Path:
        return self.state_dir / "bootstrap"

    @property
    def argocd_bootstrap_curl_path(self) -> Path:
        return self.bootstrap_dir / "argocd.curl"

    @property
    def app_bootstrap_curl_path(self) -> Path:
        return self.bootstrap_dir / "app.curl"

    @property
    def job_dir(self) -> Path:
        return self.state_dir / "jobs"

    @property
    def repo_cache_dir(self) -> Path:
        return self.state_dir / "repos"

    @property
    def request_dir(self) -> Path:
        return self.state_dir / "requests"

    @property
    def api_token_path(self) -> Path:
        if self.api_token_file is not None:
            return self.api_token_file
        return self.state_dir / "broker.key"

    def ensure_state_dirs(self) -> None:
        for path in (
            self.state_dir,
            self.log_dir,
            self.bootstrap_dir,
            self.token_dir,
            self.job_dir,
            self.repo_cache_dir,
            self.request_dir,
        ):
            path.mkdir(parents=True, exist_ok=True)

    def resolve_api_token(self) -> str:
        if self.api_token:
            return self.api_token

        self.ensure_state_dirs()
        token_path = self.api_token_path
        if token_path.exists():
            return token_path.read_text(encoding="utf-8").strip()

        token = secrets.token_urlsafe(32)
        token_path.parent.mkdir(parents=True, exist_ok=True)
        token_path.write_text(token, encoding="utf-8")
        os.chmod(token_path, 0o600)
        return token


def get_settings() -> Settings:
    settings = Settings()
    settings.ensure_state_dirs()
    return settings
