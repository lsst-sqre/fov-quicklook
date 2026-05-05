from __future__ import annotations

from pathlib import Path

import pytest

from deploy_broker.verify_cli import VerificationOptions, run_verification


class _FakeClient:
    def __init__(self) -> None:
        self.calls: list[tuple[str, object]] = []
        self.deploy_status_responses: list[dict[str, object]] = []

    def healthz(self) -> dict[str, object]:
        self.calls.append(("healthz", None))
        return {"status": "ok"}

    def get_app_token(self) -> dict[str, object]:
        self.calls.append(("get_app_token", None))
        return {"token": "app-token"}

    def argocd_status(self) -> dict[str, object]:
        self.calls.append(("argocd_status", None))
        return {"deployments": [{"deployment": "fov-quicklook-frontend"}]}

    def argocd_branch(self) -> dict[str, object]:
        self.calls.append(("argocd_branch", None))
        return {"branch": "main", "path": "applications/fov-quicklook"}

    def argocd_logs(self, component: str, since_seconds: int) -> dict[str, object]:
        self.calls.append(("argocd_logs", (component, since_seconds)))
        return {"component": component, "pod_name": "pod-1", "logs": ""}

    def argocd_sync(self) -> dict[str, object]:
        self.calls.append(("argocd_sync", None))
        return {"synced": True}

    def argocd_restart(self, components: list[str]) -> dict[str, object]:
        self.calls.append(("argocd_restart", components))
        if components:
            restarted = [f"fov-quicklook-{component}" for component in components]
        else:
            restarted = ["fov-quicklook-coordinator"]
        return {"restarted": restarted}

    def request_deploy(
        self,
        tracked_branch: str,
        app_repo_path: Path,
        app_revision: str,
        verify_mode: str,
        phalanx_repo_path: Path | None,
        phalanx_revision: str | None,
    ) -> dict[str, object]:
        self.calls.append(
            (
                "request_deploy",
                (
                    tracked_branch,
                    app_repo_path,
                    app_revision,
                    verify_mode,
                    phalanx_repo_path,
                    phalanx_revision,
                ),
            )
        )
        return {"request_id": "req-1", "status": "queued"}

    def get_deploy_status(self, request_id: str) -> dict[str, object]:
        self.calls.append(("get_deploy_status", request_id))
        if not self.deploy_status_responses:
            raise AssertionError("unexpected poll")
        return self.deploy_status_responses.pop(0)


def _options(**overrides: object) -> VerificationOptions:
    base = VerificationOptions(
        logs_component="coordinator",
        logs_since_seconds=600,
        include_sync=False,
        restart_components=None,
        deploy_tracked_branch=None,
        app_repo=None,
        app_revision="HEAD",
        verify_mode="auto",
        phalanx_repo=None,
        phalanx_revision="HEAD",
        wait_for_deploy=True,
        deploy_timeout_seconds=1800,
        deploy_poll_seconds=15,
    )
    return VerificationOptions(**{**base.__dict__, **overrides})


def test_run_verification_performs_readonly_checks() -> None:
    client = _FakeClient()

    steps = run_verification(client, _options())

    assert [step.name for step in steps] == [
        "healthz",
        "get-app-token",
        "argocd-status",
        "argocd-get-branch",
        "argocd-logs",
    ]
    assert client.calls == [
        ("healthz", None),
        ("get_app_token", None),
        ("argocd_status", None),
        ("argocd_branch", None),
        ("argocd_logs", ("coordinator", 600)),
    ]


def test_run_verification_can_include_mutating_checks() -> None:
    client = _FakeClient()

    steps = run_verification(
        client,
        _options(
            include_sync=True,
            restart_components=["frontend", "generator"],
        ),
    )

    assert [step.name for step in steps][-2:] == ["argocd-sync", "argocd-restart"]
    assert ("argocd_sync", None) in client.calls
    assert ("argocd_restart", ["frontend", "generator"]) in client.calls


def test_run_verification_waits_for_deploy_success(tmp_path: Path) -> None:
    client = _FakeClient()
    client.deploy_status_responses = [
        {"request_id": "req-1", "status": "running"},
        {
            "request_id": "req-1",
            "status": "succeeded",
            "step": "complete",
            "verification": {"healthz_ok": True},
        },
    ]
    slept: list[int] = []
    now = 0.0

    def _sleep(seconds: int) -> None:
        nonlocal now
        slept.append(seconds)
        now += seconds

    steps = run_verification(
        client,
        _options(deploy_tracked_branch="u/michitaro/fov-quicklook-test", app_repo=tmp_path),
        sleep=_sleep,
        monotonic=lambda: now,
    )

    assert [step.name for step in steps][-2:] == ["request-deploy", "get-deploy-status"]
    assert slept == [15, 15]


def test_run_verification_requires_app_repo_for_deploy() -> None:
    with pytest.raises(ValueError, match="--app-repo"):
        run_verification(_FakeClient(), _options(deploy_tracked_branch="u/michitaro/fov-quicklook-test"))


def test_run_verification_raises_on_failed_deploy(tmp_path: Path) -> None:
    client = _FakeClient()
    client.deploy_status_responses = [
        {
            "request_id": "req-1",
            "status": "failed",
            "error": "boom",
        }
    ]

    with pytest.raises(RuntimeError, match="failed"):
        run_verification(
            client,
            _options(deploy_tracked_branch="u/michitaro/fov-quicklook-test", app_repo=tmp_path),
            sleep=lambda _seconds: None,
            monotonic=lambda: 0.0,
        )
