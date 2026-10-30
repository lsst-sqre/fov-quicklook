from __future__ import annotations

from pathlib import Path

from .config import Settings
from .gitops import (
    EXPECTED_PHALANX_REMOTE_URLS,
    validate_phalanx_changes,
    validate_remote_url,
    validate_phalanx_target_branch,
)
from .shell import run_command


class PhalanxManager:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def prepare_workspace(
        self,
        workspace: Path,
        target_branch: str,
        imported_branch: str | None = None,
    ) -> None:
        validate_phalanx_target_branch(target_branch)
        validate_remote_url(workspace, EXPECTED_PHALANX_REMOTE_URLS)
        run_command(["git", "fetch", "origin", "--prune"], cwd=workspace)
        if imported_branch is not None:
            run_command(
                ["git", "checkout", "-B", target_branch, imported_branch],
                cwd=workspace,
            )
            return

        if self._remote_branch_exists(workspace, target_branch):
            run_command(
                ["git", "checkout", "-B", target_branch, f"origin/{target_branch}"],
                cwd=workspace,
            )
            return
        run_command(
            ["git", "checkout", "-B", target_branch, "origin/main"],
            cwd=workspace,
        )

    def validate_changes(self, workspace: Path) -> None:
        validate_phalanx_changes(
            workspace,
            policy=self._settings.phalanx_change_policy,
        )

    def push_branch(self, workspace: Path, target_branch: str) -> str:
        validate_phalanx_target_branch(target_branch)
        validate_remote_url(workspace, EXPECTED_PHALANX_REMOTE_URLS)
        if not self._repo_clean(workspace):
            raise RuntimeError(
                "Phalanx workspace has uncommitted changes after bundle import"
            )
        run_command(
            ["git", "push", "origin", f"HEAD:refs/heads/{target_branch}"],
            cwd=workspace,
        )
        return run_command(["git", "rev-parse", "HEAD"], cwd=workspace).strip()

    def _remote_branch_exists(self, workspace: Path, branch: str) -> bool:
        try:
            run_command(
                ["git", "ls-remote", "--exit-code", "--heads", "origin", branch],
                cwd=workspace,
            )
        except Exception:
            return False
        return True

    def _repo_clean(self, workspace: Path) -> bool:
        return not run_command(
            ["git", "status", "--porcelain"],
            cwd=workspace,
        ).strip()
