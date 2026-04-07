from __future__ import annotations

import json
import re
import time
from pathlib import Path

from .config import Settings
from .gitops import EXPECTED_APP_REMOTE_URLS, validate_build_branch, validate_remote_url
from .shell import run_command

_IMAGE_TAG_RE = re.compile(r"Pushed ghcr\.io/lsst-sqre/fov-quicklook:(\S+)")


class GitHubBuildClient:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def ensure_auth(self) -> None:
        run_command(["gh", "auth", "status"])

    def push_build_branch(self, repo_path: Path, commit_sha: str, build_branch: str) -> None:
        validate_build_branch(build_branch)
        self.ensure_auth()
        validate_remote_url(repo_path, EXPECTED_APP_REMOTE_URLS)
        run_command(
            [
                "git",
                "push",
                self._settings.app_remote_name,
                f"{commit_sha}:refs/heads/{build_branch}",
                "--force",
            ],
            cwd=repo_path,
        )

    def wait_for_build(self, build_branch: str, commit_sha: str) -> str:
        deadline = time.time() + self._settings.build_wait_seconds
        while time.time() < deadline:
            output = run_command(
                [
                    "gh",
                    "run",
                    "list",
                    "--repo",
                    self._settings.app_repo_slug,
                    "--workflow",
                    self._settings.app_workflow_file,
                    "--branch",
                    build_branch,
                    "--limit",
                    "20",
                    "--json",
                    "databaseId,status,conclusion,headSha,createdAt,url",
                ]
            )
            runs = json.loads(output)
            matching = [run for run in runs if run.get("headSha") == commit_sha]
            matching.sort(key=lambda run: run.get("createdAt", ""), reverse=True)
            if matching:
                run = matching[0]
                if run.get("status") == "completed":
                    if run.get("conclusion") != "success":
                        raise RuntimeError(
                            f"GitHub Actions build failed: {run.get('url') or run.get('databaseId')}"
                        )
                    return str(run["databaseId"])
            time.sleep(self._settings.build_poll_seconds)
        raise RuntimeError("timed out waiting for GitHub Actions build")

    def resolve_image_tag(self, run_id: str) -> str:
        output = run_command(
            [
                "gh",
                "run",
                "view",
                run_id,
                "--repo",
                self._settings.app_repo_slug,
                "--log",
            ]
        )
        match = _IMAGE_TAG_RE.search(output)
        if not match:
            raise RuntimeError("failed to resolve image tag from workflow log")
        return match.group(1)
