from __future__ import annotations

import threading
from pathlib import Path

from .argocd import ArgoCdClient
from .config import Settings
from .gitops import (
    EXPECTED_APP_REMOTE_URLS,
    EXPECTED_PHALANX_REMOTE_URLS,
    clone_workspace,
    derive_build_branch,
    ensure_clone,
    import_bundle,
    settings_repos,
    validate_build_branch,
    validate_remote_url,
)
from .github_actions import GitHubBuildClient
from .models import DeployRequestArtifacts, DeployRequestRecord
from .phalanx import PhalanxManager
from .security import extract_app_token, extract_argocd_token
from .storage import JobStore, TokenStore
from .verification import VerificationClient


class DeployBrokerService:
    def __init__(self, settings: Settings, job_store: JobStore, token_store: TokenStore) -> None:
        self._settings = settings
        self._job_store = job_store
        self._token_store = token_store
        self._argocd = ArgoCdClient(settings, token_store)
        self._github = GitHubBuildClient(settings)
        self._phalanx = PhalanxManager(settings)
        self._verification = VerificationClient(settings, token_store)

    def store_argocd_token_from_curl(self, curl_command: str) -> None:
        self._token_store.set_argocd_token(extract_argocd_token(curl_command))

    def store_app_token_from_curl(self, curl_command: str) -> None:
        self._token_store.set_app_token(extract_app_token(curl_command))

    def get_app_token(self, *, refresh: bool = False) -> str:
        return self._token_store.get_app_token(refresh=refresh)

    def argocd_status(self):
        return self._argocd.status()

    def argocd_branch(self):
        return self._argocd.get_branch()

    def argocd_logs(self, component: str, since_seconds: int = 600):
        return self._argocd.logs(component, since_seconds=since_seconds)

    def argocd_sync(self):
        return self._argocd.sync()

    def argocd_clear_image_tag(self) -> dict[str, bool]:
        self._argocd.clear_image_tag_override_and_sync()
        return {"cleared": True, "synced": True}

    def argocd_restart(self, components: list[str] | None = None):
        return self._argocd.restart(components)

    def get_deploy_status(self, request_id: str) -> DeployRequestRecord:
        return self._job_store.load(request_id)

    def start_deploy(
        self,
        metadata: DeployRequestArtifacts,
        app_bundle: bytes,
        phalanx_bundle: bytes | None,
    ) -> DeployRequestRecord:
        has_phalanx_bundle = phalanx_bundle is not None
        has_phalanx_target = metadata.phalanx_target_branch is not None
        if has_phalanx_bundle != has_phalanx_target:
            raise ValueError(
                "phalanx_bundle and phalanx_target_branch must be specified together"
            )
        if has_phalanx_bundle and metadata.phalanx_branch_name is None:
            raise ValueError("phalanx_branch_name is required with phalanx_bundle")

        record = self._job_store.create(
            metadata.deploy_name,
            metadata.verify_mode,
            phalanx_target_branch=metadata.phalanx_target_branch,
        )
        artifact_dir = self._settings.request_dir / record.request_id
        artifact_dir.mkdir(parents=True, exist_ok=True)

        app_bundle_path = artifact_dir / "app.bundle"
        app_bundle_path.write_bytes(app_bundle)

        phalanx_bundle_path: Path | None = None
        if phalanx_bundle is not None:
            phalanx_bundle_path = artifact_dir / "phalanx.bundle"
            phalanx_bundle_path.write_bytes(phalanx_bundle)

        record = self._job_store.update(
            record.request_id,
            app_branch_name=metadata.app_branch_name,
            phalanx_branch_name=metadata.phalanx_branch_name,
        )

        thread = threading.Thread(
            target=self._run_deploy,
            args=(record.request_id, metadata, app_bundle_path, phalanx_bundle_path),
            daemon=True,
        )
        thread.start()
        return record

    def _run_deploy(
        self,
        request_id: str,
        metadata: DeployRequestArtifacts,
        app_bundle_path: Path,
        phalanx_bundle_path: Path | None,
    ) -> None:
        try:
            self._job_store.update(request_id, status="running", step="preparing")
            app_base_repo, phalanx_base_repo = settings_repos(self._settings)

            self._log(request_id, "Ensuring clean app base clone is available")
            ensure_clone(app_base_repo, self._settings.app_repo_url)
            validate_remote_url(app_base_repo, EXPECTED_APP_REMOTE_URLS)

            workspace_root = self._settings.request_dir / request_id / "workspaces"
            app_workspace = workspace_root / "app"
            clone_workspace(app_base_repo, app_workspace, self._settings.app_repo_url)
            validate_remote_url(app_workspace, EXPECTED_APP_REMOTE_URLS)

            phalanx_workspace: Path | None = None
            if phalanx_bundle_path is not None:
                self._log(request_id, "Ensuring clean Phalanx base clone is available")
                ensure_clone(phalanx_base_repo, self._settings.phalanx_repo_url)
                validate_remote_url(phalanx_base_repo, EXPECTED_PHALANX_REMOTE_URLS)
                phalanx_workspace = workspace_root / "phalanx"
                clone_workspace(
                    phalanx_base_repo,
                    phalanx_workspace,
                    self._settings.phalanx_repo_url,
                )
                validate_remote_url(phalanx_workspace, EXPECTED_PHALANX_REMOTE_URLS)

            self._job_store.update(request_id, step="importing-bundles")
            self._log(request_id, "Importing app bundle into clean workspace")
            app_import_branch = f"broker-app-{request_id}"
            app_commit_sha = import_bundle(
                app_workspace,
                app_bundle_path,
                metadata.app_branch_name,
                app_import_branch,
            )
            if app_commit_sha != metadata.app_head_sha:
                raise RuntimeError(
                    f"app bundle head SHA mismatch: expected {metadata.app_head_sha}, got {app_commit_sha}"
                )
            self._job_store.update(request_id, app_commit_sha=app_commit_sha)

            phalanx_import_branch: str | None = None
            if phalanx_bundle_path is not None:
                if phalanx_workspace is None or metadata.phalanx_branch_name is None:
                    raise RuntimeError("Phalanx workspace metadata is incomplete")
                self._log(request_id, "Importing optional phalanx bundle")
                phalanx_import_branch = f"broker-phalanx-{request_id}"
                phalanx_commit_sha = import_bundle(
                    phalanx_workspace,
                    phalanx_bundle_path,
                    metadata.phalanx_branch_name,
                    phalanx_import_branch,
                )
                if metadata.phalanx_head_sha and phalanx_commit_sha != metadata.phalanx_head_sha:
                    raise RuntimeError(
                        f"phalanx bundle head SHA mismatch: expected {metadata.phalanx_head_sha}, got {phalanx_commit_sha}"
                    )
                self._job_store.update(request_id, phalanx_commit_sha=phalanx_commit_sha)

            build_branch = derive_build_branch(metadata.deploy_name)
            validate_build_branch(build_branch)
            self._job_store.update(request_id, build_branch=build_branch, step="building")
            self._log(request_id, f"Pushing app commit to build branch {build_branch}")
            self._github.push_build_branch(app_workspace, app_commit_sha, build_branch)
            run_id = self._github.wait_for_build(build_branch, app_commit_sha)
            image_tag = self._github.resolve_image_tag(run_id)
            self._job_store.update(request_id, run_id=run_id, image_tag=image_tag)
            self._log(request_id, f"Resolved image tag {image_tag}")

            if phalanx_workspace is not None:
                target_branch = metadata.phalanx_target_branch
                if target_branch is None:
                    raise RuntimeError("Phalanx target branch is missing")
                self._job_store.update(request_id, step="materializing-phalanx")
                self._phalanx.prepare_workspace(
                    phalanx_workspace,
                    target_branch,
                    imported_branch=phalanx_import_branch,
                )
                self._phalanx.validate_changes(phalanx_workspace)
                phalanx_commit_sha = self._phalanx.push_branch(
                    phalanx_workspace,
                    target_branch,
                )
                self._job_store.update(request_id, phalanx_commit_sha=phalanx_commit_sha)
                self._log(request_id, f"Pushed Phalanx branch {target_branch}")
                self._argocd.set_target_revision(target_branch)
                self._log(request_id, f"ArgoCD targetRevision updated to {target_branch}")
            else:
                self._log(request_id, "Keeping current ArgoCD targetRevision unchanged")

            self._job_store.update(request_id, step="argocd-sync")
            self._argocd.set_image_tag_and_sync(image_tag)
            self._log(request_id, "ArgoCD image.tag override updated and sync triggered")

            self._job_store.update(request_id, step="verification")
            verification = self._verification.run_basic_checks(metadata.verify_mode)

            self._job_store.update(
                request_id,
                status="succeeded",
                step="complete",
                verification=verification,
            )
        except Exception as exc:
            self._job_store.append_log(request_id, f"ERROR: {exc}")
            self._job_store.update(
                request_id,
                status="failed",
                error=str(exc),
                step="failed",
            )

    def _log(self, request_id: str, message: str) -> None:
        self._job_store.append_log(request_id, message)
