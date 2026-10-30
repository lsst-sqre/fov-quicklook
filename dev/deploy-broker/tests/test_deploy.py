from __future__ import annotations

from pathlib import Path

import pytest

from deploy_broker.config import Settings
from deploy_broker.deploy import DeployBrokerService
from deploy_broker.models import DeployRequestArtifacts
from deploy_broker.storage import JobStore, TokenStore


class _FakeGitHub:
    def __init__(self) -> None:
        self.pushes: list[tuple[Path, str, str]] = []

    def push_build_branch(self, workspace: Path, commit_sha: str, build_branch: str) -> None:
        self.pushes.append((workspace, commit_sha, build_branch))

    def wait_for_build(self, build_branch: str, commit_sha: str) -> str:
        return "run-1"

    def resolve_image_tag(self, run_id: str) -> str:
        assert run_id == "run-1"
        return "feature-test"


class _FakeArgoCd:
    def __init__(self) -> None:
        self.target_revisions: list[str] = []
        self.image_tags: list[str] = []

    def set_target_revision(self, branch: str) -> None:
        self.target_revisions.append(branch)

    def set_image_tag_and_sync(self, image_tag: str) -> None:
        self.image_tags.append(image_tag)


class _FakeVerification:
    def run_basic_checks(self, verify_mode: str) -> dict[str, object]:
        return {"verify_mode": verify_mode}


class _FakePhalanx:
    def __init__(self) -> None:
        self.prepared: list[tuple[Path, str, str | None]] = []
        self.validated: list[Path] = []
        self.pushed: list[tuple[Path, str]] = []

    def prepare_workspace(
        self,
        workspace: Path,
        target_branch: str,
        imported_branch: str | None = None,
    ) -> None:
        self.prepared.append((workspace, target_branch, imported_branch))

    def validate_changes(self, workspace: Path) -> None:
        self.validated.append(workspace)

    def push_branch(self, workspace: Path, target_branch: str) -> str:
        self.pushed.append((workspace, target_branch))
        return "phalanx-sha"


@pytest.fixture
def service(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    settings = Settings(state_dir=tmp_path / "state", token_command=None)
    job_store = JobStore(settings)
    broker = DeployBrokerService(settings, job_store, TokenStore(settings))
    broker._github = _FakeGitHub()
    broker._argocd = _FakeArgoCd()
    broker._verification = _FakeVerification()
    broker._phalanx = _FakePhalanx()

    app_base = tmp_path / "app-base"
    phalanx_base = tmp_path / "phalanx-base"
    clone_calls: list[tuple[Path, str]] = []
    ensure_calls: list[tuple[Path, str]] = []

    monkeypatch.setattr(
        "deploy_broker.deploy.settings_repos",
        lambda _settings: (app_base, phalanx_base),
    )

    def _ensure_clone(path: Path, url: str) -> None:
        ensure_calls.append((path, url))

    def _clone_workspace(source: Path, destination: Path, _url: str) -> None:
        clone_calls.append((source, destination))
        destination.mkdir(parents=True, exist_ok=True)

    def _import_bundle(
        workspace: Path,
        bundle_path: Path,
        _branch_name: str,
        _import_branch: str,
    ) -> str:
        if workspace.name == "app":
            return "app-sha"
        return "phalanx-input-sha"

    monkeypatch.setattr("deploy_broker.deploy.ensure_clone", _ensure_clone)
    monkeypatch.setattr("deploy_broker.deploy.clone_workspace", _clone_workspace)
    monkeypatch.setattr("deploy_broker.deploy.import_bundle", _import_bundle)
    monkeypatch.setattr("deploy_broker.deploy.validate_remote_url", lambda *_args: None)

    return broker, job_store, ensure_calls, clone_calls


def _metadata(**overrides: object) -> DeployRequestArtifacts:
    values: dict[str, object] = {
        "deploy_name": "feature/test",
        "verify_mode": "none",
        "app_branch_name": "feature/test",
        "app_head_sha": "app-sha",
    }
    values.update(overrides)
    return DeployRequestArtifacts(**values)


def test_standard_deploy_only_overrides_image_tag(
    service, tmp_path: Path
) -> None:
    broker, job_store, ensure_calls, clone_calls = service
    record = job_store.create("feature/test", "none")
    app_bundle = tmp_path / "app.bundle"
    app_bundle.write_bytes(b"bundle")

    broker._run_deploy(record.request_id, _metadata(), app_bundle, None)

    result = job_store.load(record.request_id)
    assert result.status == "succeeded"
    assert result.build_branch == "fov-quicklook-local-feature-test"
    assert result.phalanx_commit_sha is None
    assert len(ensure_calls) == 1
    assert len(clone_calls) == 1
    assert broker._phalanx.prepared == []
    assert broker._phalanx.pushed == []
    assert broker._argocd.target_revisions == []
    assert broker._argocd.image_tags == ["feature-test"]


def test_phalanx_deploy_changes_target_revision_explicitly(
    service, tmp_path: Path
) -> None:
    broker, job_store, ensure_calls, clone_calls = service
    target_branch = "u/michitaro/fov-quicklook-phalanx-test"
    record = job_store.create(
        "feature/test",
        "none",
        phalanx_target_branch=target_branch,
    )
    app_bundle = tmp_path / "app.bundle"
    app_bundle.write_bytes(b"app")
    phalanx_bundle = tmp_path / "phalanx.bundle"
    phalanx_bundle.write_bytes(b"phalanx")
    metadata = _metadata(
        phalanx_target_branch=target_branch,
        phalanx_branch_name="local-phalanx-work",
        phalanx_head_sha="phalanx-input-sha",
    )

    broker._run_deploy(
        record.request_id,
        metadata,
        app_bundle,
        phalanx_bundle,
    )

    result = job_store.load(record.request_id)
    assert result.status == "succeeded"
    assert result.phalanx_commit_sha == "phalanx-sha"
    assert len(ensure_calls) == 2
    assert len(clone_calls) == 2
    assert broker._phalanx.prepared[0][1] == target_branch
    assert broker._phalanx.pushed[0][1] == target_branch
    assert broker._argocd.target_revisions == [target_branch]
    assert broker._argocd.image_tags == ["feature-test"]
