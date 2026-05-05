from __future__ import annotations

from pathlib import Path

from .config import Settings
from .gitops import (
    EXPECTED_PHALANX_REMOTE_URLS,
    update_image_tag,
    validate_phalanx_changes,
    validate_remote_url,
    validate_tracked_branch,
)
from .shell import run_command


class PhalanxManager:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def prepare_workspace(
        self,
        workspace: Path,
        tracked_branch: str,
        imported_branch: str | None = None,
    ) -> None:
        validate_tracked_branch(tracked_branch)
        validate_remote_url(workspace, EXPECTED_PHALANX_REMOTE_URLS)
        run_command(["git", "fetch", "origin", "--prune"], cwd=workspace)
        if imported_branch is not None:
            run_command(["git", "checkout", "-B", tracked_branch, imported_branch], cwd=workspace)
            return

        if self._remote_branch_exists(workspace, tracked_branch):
            run_command(
                ["git", "checkout", "-B", tracked_branch, f"origin/{tracked_branch}"],
                cwd=workspace,
            )
            return
        run_command(["git", "checkout", "-B", tracked_branch, "origin/main"], cwd=workspace)

    def update_image_tag(self, workspace: Path, image_tag: str) -> None:
        values_path = workspace / "applications" / "fov-quicklook" / "values.yaml"
        update_image_tag(values_path, image_tag)

    def validate_changes(self, workspace: Path) -> None:
        validate_phalanx_changes(workspace, policy=self._settings.phalanx_change_policy)

    def commit_and_push(
        self,
        workspace: Path,
        tracked_branch: str,
        app_commit_sha: str,
        image_tag: str,
    ) -> str:
        validate_tracked_branch(tracked_branch)
        validate_remote_url(workspace, EXPECTED_PHALANX_REMOTE_URLS)
        if self._repo_clean(workspace):
            if self._remote_branch_exists(workspace, tracked_branch):
                return run_command(["git", "rev-parse", "HEAD"], cwd=workspace).strip()
            run_command(
                ["git", "push", "origin", f"HEAD:refs/heads/{tracked_branch}"],
                cwd=workspace,
            )
            return run_command(["git", "rev-parse", "HEAD"], cwd=workspace).strip()

        run_command(["git", "add", "applications/fov-quicklook/values.yaml"], cwd=workspace)
        run_command(
            [
                "git",
                "commit",
                "-m",
                f"deploy: {image_tag}",
                "-m",
                f"App commit: {app_commit_sha}",
            ],
            cwd=workspace,
        )
        run_command(["git", "push", "origin", f"HEAD:refs/heads/{tracked_branch}"], cwd=workspace)
        return run_command(["git", "rev-parse", "HEAD"], cwd=workspace).strip()

    def _remote_branch_exists(self, workspace: Path, branch: str) -> bool:
        try:
            run_command(["git", "ls-remote", "--exit-code", "--heads", "origin", branch], cwd=workspace)
        except Exception:
            return False
        return True

    def _repo_clean(self, workspace: Path) -> bool:
        return not run_command(["git", "status", "--porcelain"], cwd=workspace).strip()
