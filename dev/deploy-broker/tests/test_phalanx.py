from __future__ import annotations

from pathlib import Path

from pytest import MonkeyPatch

from deploy_broker.config import Settings
from deploy_broker.phalanx import PhalanxManager


def test_push_branch_pushes_imported_snapshot_even_if_target_exists(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
) -> None:
    manager = PhalanxManager(Settings(state_dir=tmp_path / "state"))
    workspace = tmp_path / "phalanx"
    workspace.mkdir()
    calls: list[list[str]] = []

    monkeypatch.setattr(
        "deploy_broker.phalanx.validate_remote_url",
        lambda *_args: None,
    )

    def _run_command(argv: list[str], *, cwd: Path | None = None) -> str:
        assert cwd == workspace
        calls.append(argv)
        if argv == ["git", "status", "--porcelain"]:
            return ""
        if argv == ["git", "rev-parse", "HEAD"]:
            return "phalanx-sha\n"
        return ""

    monkeypatch.setattr("deploy_broker.phalanx.run_command", _run_command)

    sha = manager.push_branch(
        workspace,
        "u/michitaro/fov-quicklook-config-test",
    )

    assert sha == "phalanx-sha"
    assert [
        "git",
        "push",
        "origin",
        "HEAD:refs/heads/u/michitaro/fov-quicklook-config-test",
    ] in calls
