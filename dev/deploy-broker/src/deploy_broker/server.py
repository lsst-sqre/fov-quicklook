from __future__ import annotations

from fastapi import Depends, FastAPI, File, Form, HTTPException, UploadFile

from .config import Settings, get_settings
from .deploy import DeployBrokerService
from .models import (
    ArgoCdRestartRequest,
    DeployRequestArtifacts,
    TokenResponse,
)
from .security import require_bearer_token
from .storage import JobStore, TokenStore


def _raise_http_error(exc: Exception) -> None:
    if isinstance(exc, ValueError):
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if isinstance(exc, RuntimeError):
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    raise HTTPException(status_code=500, detail=str(exc)) from exc


def create_app(settings: Settings | None = None) -> FastAPI:
    resolved_settings = settings or get_settings()
    token_store = TokenStore(resolved_settings)
    job_store = JobStore(resolved_settings)
    service = DeployBrokerService(resolved_settings, job_store, token_store)

    app = FastAPI(title="fov-quicklook deploy broker")
    app.state.settings = resolved_settings
    app.state.service = service

    @app.get("/healthz")
    def healthz() -> dict[str, str]:
        return {"status": "ok"}

    @app.get(
        "/v1/tokens/app",
        dependencies=[Depends(require_bearer_token)],
        response_model=TokenResponse,
    )
    def get_app_token(refresh: bool = False) -> TokenResponse:
        try:
            return TokenResponse(token=service.get_app_token(refresh=refresh))
        except Exception as exc:
            _raise_http_error(exc)

    @app.get("/v1/argocd/status", dependencies=[Depends(require_bearer_token)])
    def argocd_status():
        try:
            return service.argocd_status()
        except Exception as exc:
            _raise_http_error(exc)

    @app.get("/v1/argocd/branch", dependencies=[Depends(require_bearer_token)])
    def argocd_branch():
        try:
            return service.argocd_branch()
        except Exception as exc:
            _raise_http_error(exc)

    @app.get("/v1/argocd/logs/{component}", dependencies=[Depends(require_bearer_token)])
    def argocd_logs(component: str, since_seconds: int = 600):
        try:
            return service.argocd_logs(component, since_seconds=since_seconds)
        except Exception as exc:
            _raise_http_error(exc)

    @app.post("/v1/argocd/sync", dependencies=[Depends(require_bearer_token)])
    def argocd_sync():
        try:
            return service.argocd_sync()
        except Exception as exc:
            _raise_http_error(exc)

    @app.post(
        "/v1/argocd/image-tag/clear",
        dependencies=[Depends(require_bearer_token)],
    )
    def argocd_clear_image_tag():
        try:
            return service.argocd_clear_image_tag()
        except Exception as exc:
            _raise_http_error(exc)

    @app.post("/v1/argocd/restart", dependencies=[Depends(require_bearer_token)])
    def argocd_restart(payload: ArgoCdRestartRequest):
        try:
            return service.argocd_restart(payload.components)
        except Exception as exc:
            _raise_http_error(exc)

    @app.post("/v1/deploy-requests", dependencies=[Depends(require_bearer_token)])
    async def request_deploy(
        deploy_name: str | None = Form(None),
        tracked_branch: str | None = Form(None),
        verify_mode: str = Form("auto"),
        app_branch_name: str = Form(...),
        app_head_sha: str = Form(...),
        app_base_sha: str | None = Form(None),
        phalanx_target_branch: str | None = Form(None),
        phalanx_branch_name: str | None = Form(None),
        phalanx_head_sha: str | None = Form(None),
        phalanx_base_sha: str | None = Form(None),
        app_bundle: UploadFile = File(...),
        phalanx_bundle: UploadFile | None = File(None),
    ):
        try:
            resolved_deploy_name = deploy_name or tracked_branch
            if not resolved_deploy_name:
                raise ValueError("deploy_name is required")

            resolved_phalanx_target = phalanx_target_branch
            if phalanx_bundle is not None and resolved_phalanx_target is None:
                if tracked_branch and tracked_branch.startswith("u/michitaro/fov-quicklook-"):
                    resolved_phalanx_target = tracked_branch
                else:
                    raise ValueError(
                        "phalanx_target_branch is required when phalanx_bundle is provided"
                    )

            metadata = DeployRequestArtifacts(
                deploy_name=resolved_deploy_name,
                phalanx_target_branch=resolved_phalanx_target,
                verify_mode=verify_mode,  # type: ignore[arg-type]
                app_branch_name=app_branch_name,
                app_head_sha=app_head_sha,
                app_base_sha=app_base_sha or None,
                phalanx_branch_name=phalanx_branch_name or None,
                phalanx_head_sha=phalanx_head_sha or None,
                phalanx_base_sha=phalanx_base_sha or None,
            )
            return service.start_deploy(
                metadata,
                await app_bundle.read(),
                await phalanx_bundle.read() if phalanx_bundle is not None else None,
            )
        except Exception as exc:
            _raise_http_error(exc)

    @app.get(
        "/v1/deploy-requests/{request_id}",
        dependencies=[Depends(require_bearer_token)],
    )
    def get_deploy_status(request_id: str):
        try:
            return service.get_deploy_status(request_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="request not found") from exc

    return app
