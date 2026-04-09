from __future__ import annotations

import logging
import time
import uuid

from fastapi import Depends, FastAPI, File, Form, HTTPException, Request, UploadFile

from .broker_logging import bind_audit_context, audit_event, configure_logging, summarize_exception
from .config import Settings, get_settings
from .deploy import DeployBrokerService
from .models import (
    ArgoCdRestartRequest,
    DeployRequestArtifacts,
    TokenResponse,
)
from .security import auth_mode_for_request, require_bearer_token
from .storage import JobStore, TokenStore


def _raise_http_error(exc: Exception) -> None:
    detail = summarize_exception(exc)
    if isinstance(exc, ValueError):
        raise HTTPException(status_code=400, detail=detail) from exc
    if isinstance(exc, RuntimeError):
        raise HTTPException(status_code=503, detail=detail) from exc
    raise HTTPException(status_code=500, detail=detail) from exc


def _audit_level_for_status(status_code: int) -> int:
    if status_code >= 500:
        return logging.ERROR
    if status_code >= 400:
        return logging.WARNING
    return logging.INFO


def _audit_resource(path: str) -> str:
    if path == "/healthz":
        return "healthz"
    if path == "/v1/tokens/app":
        return "app-token"
    if path == "/v1/argocd/status":
        return "argocd-status"
    if path == "/v1/argocd/branch":
        return "argocd-branch"
    if path.startswith("/v1/argocd/logs/"):
        return "argocd-logs"
    if path == "/v1/argocd/sync":
        return "argocd-sync"
    if path == "/v1/argocd/restart":
        return "argocd-restart"
    if path == "/v1/deploy-requests":
        return "deploy-request"
    if path.startswith("/v1/deploy-requests/"):
        return "deploy-request-status"
    return "unknown"


def _audit_operation(method: str) -> str:
    if method.upper() == "GET":
        return "read"
    return "mutate"


def create_app(settings: Settings | None = None) -> FastAPI:
    resolved_settings = settings or get_settings()
    configure_logging(resolved_settings)
    token_store = TokenStore(resolved_settings)
    job_store = JobStore(resolved_settings)
    service = DeployBrokerService(resolved_settings, job_store, token_store)

    app = FastAPI(title="fov-quicklook deploy broker")
    app.state.settings = resolved_settings
    app.state.service = service

    @app.middleware("http")
    async def audit_requests(request: Request, call_next):
        correlation_id = request.headers.get("X-Request-ID") or uuid.uuid4().hex
        auth_mode = auth_mode_for_request(request)
        remote_host = request.client.host if request.client is not None else None
        path = request.url.path
        query = dict(request.query_params)
        started = time.perf_counter()
        with bind_audit_context(
            correlation_id=correlation_id,
            remote_host=remote_host,
            auth_mode=auth_mode,
        ):
            try:
                response = await call_next(request)
            except Exception as exc:
                audit_event(
                    "http.request",
                    level=logging.ERROR,
                    correlation_id=correlation_id,
                    method=request.method,
                    path=path,
                    resource=_audit_resource(path),
                    operation=_audit_operation(request.method),
                    status_code=500,
                    duration_ms=round((time.perf_counter() - started) * 1000, 3),
                    query=query or None,
                    error=summarize_exception(exc),
                )
                raise
        response.headers["X-Request-ID"] = correlation_id
        audit_event(
            "http.request",
            level=_audit_level_for_status(response.status_code),
            correlation_id=correlation_id,
            remote_host=remote_host,
            auth_mode=auth_mode,
            method=request.method,
            path=path,
            resource=_audit_resource(path),
            operation=_audit_operation(request.method),
            status_code=response.status_code,
            duration_ms=round((time.perf_counter() - started) * 1000, 3),
            query=query or None,
        )
        return response

    @app.get("/healthz")
    def healthz() -> dict[str, str]:
        return {"status": "ok"}

    @app.get(
        "/v1/tokens/app",
        dependencies=[Depends(require_bearer_token)],
        response_model=TokenResponse,
    )
    def get_app_token() -> TokenResponse:
        try:
            return TokenResponse(token=service.get_app_token())
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

    @app.post("/v1/argocd/restart", dependencies=[Depends(require_bearer_token)])
    def argocd_restart(payload: ArgoCdRestartRequest):
        try:
            return service.argocd_restart(payload.components)
        except Exception as exc:
            _raise_http_error(exc)

    @app.post("/v1/deploy-requests", dependencies=[Depends(require_bearer_token)])
    async def request_deploy(
        tracked_branch: str = Form(...),
        verify_mode: str = Form("auto"),
        app_branch_name: str = Form(...),
        app_head_sha: str = Form(...),
        app_base_sha: str | None = Form(None),
        phalanx_branch_name: str | None = Form(None),
        phalanx_head_sha: str | None = Form(None),
        phalanx_base_sha: str | None = Form(None),
        app_bundle: UploadFile = File(...),
        phalanx_bundle: UploadFile | None = File(None),
    ):
        try:
            metadata = DeployRequestArtifacts(
                tracked_branch=tracked_branch,
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
