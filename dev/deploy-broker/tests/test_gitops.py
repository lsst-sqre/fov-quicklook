from __future__ import annotations

from pathlib import Path

import pytest

from deploy_broker.gitops import create_bundle, derive_build_branch, rev_parse, update_image_tag
from deploy_broker.shell import run_command


def _init_repo(path: Path) -> None:
    run_command(["git", "init", "-b", "feature-branch"], cwd=path)
    run_command(["git", "config", "user.name", "Test User"], cwd=path)
    run_command(["git", "config", "user.email", "test@example.invalid"], cwd=path)
    (path / "README.txt").write_text("hello\n", encoding="utf-8")
    run_command(["git", "add", "README.txt"], cwd=path)
    run_command(["git", "commit", "-m", "initial"], cwd=path)


def test_create_bundle_for_clean_repo(tmp_path: Path) -> None:
    repo_path = tmp_path / "repo"
    repo_path.mkdir()
    _init_repo(repo_path)
    bundle_path = tmp_path / "bundle" / "app.bundle"

    metadata = create_bundle(repo_path, "HEAD", bundle_path)

    assert bundle_path.exists()
    assert metadata["branch_name"] == "feature-branch"
    assert metadata["head_sha"] == rev_parse(repo_path, "HEAD")


def test_create_bundle_rejects_dirty_repo(tmp_path: Path) -> None:
    repo_path = tmp_path / "repo"
    repo_path.mkdir()
    _init_repo(repo_path)
    (repo_path / "README.txt").write_text("dirty\n", encoding="utf-8")

    with pytest.raises(RuntimeError):
        create_bundle(repo_path, "HEAD", tmp_path / "bundle.bundle")


def test_derive_build_branch_sanitizes_suffix() -> None:
    assert (
        derive_build_branch("u/michitaro/fov-quicklook-topic:alpha")
        == "fov-quicklook-local-topic-alpha"
    )


def test_create_bundle_rejects_detached_head(tmp_path: Path) -> None:
    repo_path = tmp_path / "repo"
    repo_path.mkdir()
    _init_repo(repo_path)
    head_sha = rev_parse(repo_path, "HEAD")
    run_command(["git", "checkout", head_sha], cwd=repo_path)

    with pytest.raises(RuntimeError):
        create_bundle(repo_path, "HEAD", tmp_path / "bundle.bundle")


def test_update_image_tag_handles_blank_lines_in_image_block(tmp_path: Path) -> None:
    values_path = tmp_path / "values.yaml"
    values_path.write_text(
        """image:
  repository: ghcr.io/lsst-sqre/fov-quicklook

  pullPolicy: Always

  tag: main
config:
  pathPrefix: /fov-quicklook
""",
        encoding="utf-8",
    )

    update_image_tag(values_path, "test-tag")

    assert "  tag: test-tag\n" in values_path.read_text(encoding="utf-8")
