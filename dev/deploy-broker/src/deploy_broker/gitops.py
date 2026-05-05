from __future__ import annotations

import re
import shutil
from pathlib import Path

from .config import Settings
from .shell import run_command

EXPECTED_APP_REMOTE_URLS = {
    "https://github.com/lsst-sqre/fov-quicklook",
    "https://github.com/lsst-sqre/fov-quicklook.git",
    "git@github.com:lsst-sqre/fov-quicklook",
    "git@github.com:lsst-sqre/fov-quicklook.git",
    "ssh://git@github.com/lsst-sqre/fov-quicklook",
    "ssh://git@github.com/lsst-sqre/fov-quicklook.git",
}

EXPECTED_PHALANX_REMOTE_URLS = {
    "https://github.com/lsst-sqre/phalanx",
    "https://github.com/lsst-sqre/phalanx.git",
    "git@github.com:lsst-sqre/phalanx",
    "git@github.com:lsst-sqre/phalanx.git",
    "ssh://git@github.com/lsst-sqre/phalanx",
    "ssh://git@github.com/lsst-sqre/phalanx.git",
}

ALLOWED_PHALANX_PATHS = (
    "applications/fov-quicklook/",
    "docs/applications/fov-quicklook/",
    "environments/templates/applications/rsp/fov-quicklook.yaml",
)
FOV_QUICKLOOK_VALUES_PATH = "applications/fov-quicklook/values.yaml"
ALLOWED_PHALANX_CHANGE_POLICIES = (
    "fov-quicklook-paths",
    "values-yaml-only",
    "image-tag-only",
)
_IMAGE_TAG_DIFF_RE = re.compile(r"^tag:\s*\S.*$")


def validate_tracked_branch(branch: str) -> None:
    if not branch.startswith("u/michitaro/fov-quicklook-"):
        raise ValueError(
            f"tracked branch must match u/michitaro/fov-quicklook-*: {branch}"
        )


def derive_build_branch(tracked_branch: str) -> str:
    validate_tracked_branch(tracked_branch)
    suffix = tracked_branch.removeprefix("u/michitaro/fov-quicklook-")
    safe = "".join(char if char.isalnum() or char in "._-" else "-" for char in suffix)
    safe = safe.strip("-") or "manual"
    return f"fov-quicklook-local-{safe}"


def validate_build_branch(branch: str) -> None:
    if "/" in branch or not branch.startswith("fov-quicklook-local-"):
        raise ValueError(f"build branch must match fov-quicklook-local-*: {branch}")


def ensure_clean_worktree(repo_path: Path) -> None:
    status = run_command(["git", "status", "--porcelain"], cwd=repo_path).strip()
    if status:
        raise RuntimeError(f"repository has uncommitted changes: {repo_path}")


def current_branch(repo_path: Path, revision: str = "HEAD") -> str:
    return run_command(
        ["git", "rev-parse", "--abbrev-ref", revision],
        cwd=repo_path,
    ).strip()


def rev_parse(repo_path: Path, revision: str) -> str:
    return run_command(["git", "rev-parse", f"{revision}^{{commit}}"], cwd=repo_path).strip()


def maybe_merge_base(repo_path: Path, left: str, right: str) -> str | None:
    try:
        return run_command(["git", "merge-base", left, right], cwd=repo_path).strip()
    except Exception:
        return None


def create_bundle(repo_path: Path, revision: str, output_path: Path) -> dict[str, str | None]:
    ensure_clean_worktree(repo_path)
    branch_name = current_branch(repo_path, revision)
    if branch_name == "HEAD":
        raise RuntimeError("bundle creation requires a named branch, not detached HEAD")
    head_sha = rev_parse(repo_path, revision)
    base_sha = maybe_merge_base(repo_path, revision, "origin/main")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    run_command(
        ["git", "bundle", "create", str(output_path), branch_name],
        cwd=repo_path,
    )
    return {
        "branch_name": branch_name,
        "head_sha": head_sha,
        "base_sha": base_sha,
    }


def validate_remote_url(repo_path: Path, expected_urls: set[str]) -> None:
    remote_url = run_command(["git", "remote", "get-url", "origin"], cwd=repo_path).strip()
    if remote_url not in expected_urls:
        raise RuntimeError(f"unexpected remote for {repo_path}: {remote_url}")


def ensure_clone(path: Path, remote_url: str) -> None:
    if path.exists():
        validate_remote_url(path, {remote_url, remote_url.removesuffix(".git")})
        ensure_clean_worktree(path)
        run_command(["git", "fetch", "origin", "--prune"], cwd=path)
        return

    path.parent.mkdir(parents=True, exist_ok=True)
    run_command(["git", "clone", remote_url, str(path)])


def clone_workspace(base_repo: Path, workspace: Path, remote_url: str) -> None:
    if workspace.exists():
        shutil.rmtree(workspace)
    workspace.parent.mkdir(parents=True, exist_ok=True)
    run_command(["git", "clone", str(base_repo), str(workspace)])
    run_command(["git", "remote", "set-url", "origin", remote_url], cwd=workspace)


def import_bundle(
    workspace: Path,
    bundle_path: Path,
    source_branch: str,
    import_branch: str,
) -> str:
    run_command(
        [
            "git",
            "fetch",
            str(bundle_path),
            f"{source_branch}:refs/heads/{import_branch}",
        ],
        cwd=workspace,
    )
    run_command(["git", "checkout", import_branch], cwd=workspace)
    return rev_parse(workspace, "HEAD")


def is_allowed_phalanx_path(path: str) -> bool:
    return any(
        path == allowed or path.startswith(allowed)
        for allowed in ALLOWED_PHALANX_PATHS
    )


def _diff_range_args(base_ref: str, head_ref: str | None = None) -> list[str]:
    if head_ref is None:
        return [base_ref]
    return [base_ref, head_ref]


def collect_changed_files(
    repo_path: Path,
    base_ref: str,
    head_ref: str | None = None,
) -> list[str]:
    output = run_command(
        [
            "git",
            "diff",
            "--name-only",
            "--diff-filter=ACDMRT",
            *_diff_range_args(base_ref, head_ref),
        ],
        cwd=repo_path,
    )
    return [line for line in output.splitlines() if line.strip()]


def collect_diff_text(
    repo_path: Path,
    base_ref: str,
    path: str,
    head_ref: str | None = None,
) -> str:
    return run_command(
        [
            "git",
            "diff",
            "--no-color",
            "--unified=0",
            *_diff_range_args(base_ref, head_ref),
            "--",
            path,
        ],
        cwd=repo_path,
    )


def _resolve_phalanx_base_ref(repo_path: Path) -> str:
    merge_base = maybe_merge_base(repo_path, "HEAD", "origin/main")
    if merge_base is not None:
        return merge_base
    try:
        return rev_parse(repo_path, "HEAD^")
    except Exception as exc:
        raise RuntimeError(
            "phalanx validation requires origin/main or at least one parent commit"
        ) from exc


def _validate_phalanx_change_policy(policy: str) -> None:
    if policy not in ALLOWED_PHALANX_CHANGE_POLICIES:
        raise ValueError(
            "unknown phalanx change policy: "
            f"{policy} (expected one of {', '.join(ALLOWED_PHALANX_CHANGE_POLICIES)})"
        )


def _validate_path_allowlist(files: list[str]) -> None:
    unsafe = [path for path in files if not is_allowed_phalanx_path(path)]
    if unsafe:
        raise RuntimeError(
            "phalanx changes include unsafe paths: " + ", ".join(sorted(unsafe))
        )


def _validate_values_yaml_only(files: list[str]) -> None:
    unsafe = [path for path in files if path != FOV_QUICKLOOK_VALUES_PATH]
    if unsafe:
        raise RuntimeError(
            "phalanx policy values-yaml-only rejects changes outside "
            f"{FOV_QUICKLOOK_VALUES_PATH}: {', '.join(sorted(unsafe))}"
        )


def _validate_image_tag_only(repo_path: Path, base_ref: str, files: list[str]) -> None:
    _validate_values_yaml_only(files)
    diff_text = collect_diff_text(repo_path, base_ref, FOV_QUICKLOOK_VALUES_PATH)
    meaningful_lines: list[str] = []
    for line in diff_text.splitlines():
        if (
            not line
            or line.startswith("diff --git ")
            or line.startswith("index ")
            or line.startswith("--- ")
            or line.startswith("+++ ")
            or line.startswith("@@")
            or line.startswith("\\ No newline at end of file")
        ):
            continue
        if line[0] not in "+-":
            raise RuntimeError("phalanx policy image-tag-only encountered unexpected diff")
        changed = line[1:].strip()
        meaningful_lines.append(changed)
        if not _IMAGE_TAG_DIFF_RE.match(changed):
            raise RuntimeError(
                "phalanx policy image-tag-only allows only image.tag line changes"
            )
    if not meaningful_lines:
        raise RuntimeError("phalanx policy image-tag-only found no image.tag changes")


def validate_phalanx_changes(
    repo_path: Path,
    policy: str = "fov-quicklook-paths",
) -> None:
    _validate_phalanx_change_policy(policy)
    base_ref = _resolve_phalanx_base_ref(repo_path)
    files = collect_changed_files(repo_path, base_ref)

    if not files:
        return

    if policy == "fov-quicklook-paths":
        _validate_path_allowlist(files)
        return
    if policy == "values-yaml-only":
        _validate_values_yaml_only(files)
        return
    if policy == "image-tag-only":
        _validate_image_tag_only(repo_path, base_ref, files)
        return

    raise AssertionError(f"unhandled phalanx change policy: {policy}")


def update_image_tag(values_path: Path, image_tag: str) -> None:
    lines = values_path.read_text(encoding="utf-8").splitlines(keepends=True)
    in_image_block = False
    replaced = False
    for index, line in enumerate(lines):
        if line.strip() == "image:":
            in_image_block = True
            continue
        if in_image_block and line.strip() and not line.startswith(" "):
            in_image_block = False
        if in_image_block and line.strip().startswith("tag:"):
            newline = "\n" if line.endswith("\n") else ""
            lines[index] = f"  tag: {image_tag}{newline}"
            replaced = True
            break
    if not replaced:
        raise RuntimeError("failed to update image tag in values.yaml")
    values_path.write_text("".join(lines), encoding="utf-8")


def settings_repos(settings: Settings) -> tuple[Path, Path]:
    return (
        settings.repo_cache_dir / "app-repo",
        settings.repo_cache_dir / "phalanx-repo",
    )
