from __future__ import annotations

import logging
import threading
from pathlib import Path

from .argocd import ArgoCdClient
from .broker_logging import (
    audit_event,
    bind_request_log,
    current_deploy_context,
    log_request_detail,
    set_deploy_step,
    summarize_exception,
)
from .config import Settings
from .gitops import (
    EXPECTED_APP_REMOTE_URLS,
    EXPECTED_PHALANX_REMOTE_URLS,
    clone_workspace,
    derive_build_branch,
    ensure_clone,
    import_bundle,
    rev_parse,
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

    def get_app_token(self) -> str:
        token = self._token_store.get_app_token()
        audit_event(
            "app-token.read",
            resource="app-token",
            operation="read",
        )
        return token

    def argocd_status(self):
        return self._argocd.status()

    def argocd_branch(self):
        return self._argocd.get_branch()

    def argocd_logs(self, component: str, since_seconds: int = 600):
        return self._argocd.logs(component, since_seconds=since_seconds)

    def argocd_sync(self):
        result = self._argocd.sync()
        audit_event(
            "argocd.sync",
            resource="argocd-sync",
            operation="mutate",
            synced=result.synced,
        )
        return result

    def argocd_restart(self, components: list[str] | None = None):
        result = self._argocd.restart(components)
        audit_event(
            "argocd.restart",
            resource="argocd-restart",
            operation="mutate",
            restarted=result.restarted,
        )
        return result

    def get_deploy_status(self, request_id: str) -> DeployRequestRecord:
        return self._job_store.load(request_id)

    def start_deploy(
        self,
        metadata: DeployRequestArtifacts,
        app_bundle: bytes,
        phalanx_bundle: bytes | None,
    ) -> DeployRequestRecord:
        record = self._job_store.create(metadata.tracked_branch, metadata.verify_mode)
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
        with bind_request_log(
            self._settings,
            record.request_id,
            tracked_branch=metadata.tracked_branch,
        ):
            log_request_detail(
                logging.INFO,
                "Accepted deploy request",
                verify_mode=metadata.verify_mode,
                app_branch_name=metadata.app_branch_name,
                phalanx_branch_name=metadata.phalanx_branch_name,
                request_log_path=record.request_log_path,
            )
        audit_event(
            "deploy.request.accepted",
            resource="deploy-request",
            operation="mutate",
            request_id=record.request_id,
            tracked_branch=metadata.tracked_branch,
            verify_mode=metadata.verify_mode,
            app_branch_name=metadata.app_branch_name,
            phalanx_branch_name=metadata.phalanx_branch_name,
            request_log_path=record.request_log_path,
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
        with bind_request_log(self._settings, request_id, tracked_branch=metadata.tracked_branch):
            try:
                self._job_store.update(request_id, status="running", step="preparing")
                set_deploy_step("preparing")
                self._log(request_id, "Ensuring clean base clones are available")
                audit_event(
                    "deploy.started",
                    request_id=request_id,
                    tracked_branch=metadata.tracked_branch,
                    verify_mode=metadata.verify_mode,
                    request_log_path=str(self._settings.request_log_path(request_id)),
                )
                app_base_repo, phalanx_base_repo = settings_repos(self._settings)

                ensure_clone(app_base_repo, self._settings.app_repo_url)
                ensure_clone(phalanx_base_repo, self._settings.phalanx_repo_url)
                validate_remote_url(app_base_repo, EXPECTED_APP_REMOTE_URLS)
                validate_remote_url(phalanx_base_repo, EXPECTED_PHALANX_REMOTE_URLS)

                workspace_root = self._settings.request_dir / request_id / "workspaces"
                app_workspace = workspace_root / "app"
                phalanx_workspace = workspace_root / "phalanx"
                clone_workspace(app_base_repo, app_workspace, self._settings.app_repo_url)
                clone_workspace(
                    phalanx_base_repo,
                    phalanx_workspace,
                    self._settings.phalanx_repo_url,
                )
                validate_remote_url(app_workspace, EXPECTED_APP_REMOTE_URLS)
                validate_remote_url(phalanx_workspace, EXPECTED_PHALANX_REMOTE_URLS)

                self._job_store.update(request_id, step="importing-bundles")
                set_deploy_step("importing-bundles")
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
                log_request_detail(
                    logging.INFO,
                    "Imported app bundle",
                    app_commit_sha=app_commit_sha,
                    app_branch_name=metadata.app_branch_name,
                )

                phalanx_import_branch: str | None = None
                if phalanx_bundle_path is not None and metadata.phalanx_branch_name is not None:
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
                    log_request_detail(
                        logging.INFO,
                        "Imported phalanx bundle",
                        phalanx_commit_sha=phalanx_commit_sha,
                        phalanx_branch_name=metadata.phalanx_branch_name,
                    )

                build_branch = derive_build_branch(metadata.tracked_branch)
                validate_build_branch(build_branch)
                self._job_store.update(request_id, build_branch=build_branch, step="building")
                set_deploy_step("building")
                self._log(request_id, f"Pushing app commit to build branch {build_branch}")
                self._github.push_build_branch(app_workspace, app_commit_sha, build_branch)
                run_id = self._github.wait_for_build(build_branch, app_commit_sha)
                image_tag = self._github.resolve_image_tag(run_id)
                self._job_store.update(request_id, run_id=run_id, image_tag=image_tag)
                self._log(request_id, f"Resolved image tag {image_tag}")
                log_request_detail(
                    logging.INFO,
                    "Resolved build artifacts",
                    build_branch=build_branch,
                    run_id=run_id,
                    image_tag=image_tag,
                )

                self._job_store.update(request_id, step="materializing-phalanx")
                set_deploy_step("materializing-phalanx")
                self._log(request_id, "Preparing Phalanx workspace")
                self._phalanx.prepare_workspace(
                    phalanx_workspace,
                    metadata.tracked_branch,
                    imported_branch=phalanx_import_branch,
                )
                self._phalanx.validate_changes(phalanx_workspace)
                self._phalanx.update_image_tag(phalanx_workspace, image_tag)
                self._phalanx.validate_changes(phalanx_workspace)
                phalanx_commit_sha = self._phalanx.commit_and_push(
                    phalanx_workspace,
                    metadata.tracked_branch,
                    app_commit_sha,
                    image_tag,
                )
                self._job_store.update(request_id, phalanx_commit_sha=phalanx_commit_sha)
                self._log(request_id, f"Pushed phalanx branch {metadata.tracked_branch}")
                log_request_detail(
                    logging.INFO,
                    "Updated phalanx branch",
                    phalanx_commit_sha=phalanx_commit_sha,
                    image_tag=image_tag,
                )

                self._job_store.update(request_id, step="argocd-sync")
                set_deploy_step("argocd-sync")
                self._argocd.set_branch_and_sync(metadata.tracked_branch, image_tag=image_tag)
                self._log(request_id, "ArgoCD branch updated and sync triggered")

                self._job_store.update(request_id, step="verification")
                set_deploy_step("verification")
                self._log(request_id, "Running verification checks")
                verification = self._verification.run_basic_checks(metadata.verify_mode)

                self._job_store.update(
                    request_id,
                    status="succeeded",
                    step="complete",
                    verification=verification,
                )
                set_deploy_step("complete")
                self._log(request_id, "Deploy request completed successfully")
                log_request_detail(
                    logging.INFO,
                    "Verification finished",
                    verification=verification,
                )
                audit_event(
                    "deploy.completed",
                    request_id=request_id,
                    tracked_branch=metadata.tracked_branch,
                    run_id=run_id,
                    image_tag=image_tag,
                    verification=verification,
                )
            except Exception as exc:
                error_message = summarize_exception(exc)
                context = current_deploy_context()
                log_request_detail(
                    logging.ERROR,
                    "Deploy request failed",
                    error=error_message,
                )
                self._job_store.append_log(request_id, f"ERROR: {error_message}")
                self._job_store.update(
                    request_id,
                    status="failed",
                    error=error_message,
                    step="failed",
                )
                set_deploy_step("failed")
                audit_event(
                    "deploy.failed",
                    level=logging.ERROR,
                    request_id=request_id,
                    tracked_branch=metadata.tracked_branch,
                    step=context.step if context is not None else "failed",
                    error=error_message,
                )
                return

    def _log(self, request_id: str, message: str) -> None:
        self._job_store.append_log(request_id, message)
        log_request_detail(logging.INFO, message)
