from __future__ import annotations

from datetime import datetime, UTC
from typing import Any, Literal

from pydantic import BaseModel, Field


class TokenResponse(BaseModel):
    token: str


class DeploymentStatusEntry(BaseModel):
    deployment: str
    ready_replicas: str
    replicas: str
    image: str


class ArgoCdStatusResponse(BaseModel):
    deployments: list[DeploymentStatusEntry]


class ArgoCdBranchResponse(BaseModel):
    repo: str
    path: str
    branch: str


class ArgoCdLogsResponse(BaseModel):
    component: str
    pod_name: str
    logs: str


class ArgoCdSyncResponse(BaseModel):
    synced: bool = True


class ArgoCdRestartRequest(BaseModel):
    components: list[str] = Field(default_factory=list)


class ArgoCdRestartResponse(BaseModel):
    restarted: list[str]


class JobLogEntry(BaseModel):
    timestamp: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())
    message: str


class DeployRequestRecord(BaseModel):
    request_id: str
    status: Literal["queued", "running", "succeeded", "failed"]
    tracked_branch: str
    verify_mode: Literal["none", "auto", "all"]
    build_branch: str | None = None
    app_commit_sha: str | None = None
    phalanx_commit_sha: str | None = None
    app_branch_name: str | None = None
    phalanx_branch_name: str | None = None
    image_tag: str | None = None
    run_id: str | None = None
    step: str | None = None
    error: str | None = None
    logs: list[JobLogEntry] = Field(default_factory=list)
    verification: dict[str, Any] | None = None


class DeployRequestArtifacts(BaseModel):
    tracked_branch: str
    verify_mode: Literal["none", "auto", "all"]
    app_branch_name: str
    app_head_sha: str
    app_base_sha: str | None = None
    phalanx_branch_name: str | None = None
    phalanx_head_sha: str | None = None
    phalanx_base_sha: str | None = None
