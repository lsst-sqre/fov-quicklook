from __future__ import annotations

import argparse
import sys
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .client import BrokerClient, _settings_defaults


@dataclass
class VerificationStep:
    name: str
    detail: str


@dataclass
class VerificationOptions:
    logs_component: str
    logs_since_seconds: int
    include_sync: bool
    restart_components: list[str] | None
    deploy_tracked_branch: str | None
    app_repo: Path | None
    app_revision: str
    verify_mode: str
    phalanx_repo: Path | None
    phalanx_revision: str
    wait_for_deploy: bool
    deploy_timeout_seconds: int
    deploy_poll_seconds: int


def run_verification(
    client: BrokerClient,
    options: VerificationOptions,
    *,
    sleep: Callable[[int], None] = time.sleep,
    monotonic: Callable[[], float] = time.monotonic,
) -> list[VerificationStep]:
    steps = [
        _verify_healthz(client),
        _verify_app_token(client),
        _verify_argocd_status(client),
        _verify_argocd_branch(client),
        _verify_argocd_logs(client, options.logs_component, options.logs_since_seconds),
    ]

    if options.include_sync:
        steps.append(_verify_argocd_sync(client))

    if options.restart_components is not None:
        steps.append(_verify_argocd_restart(client, options.restart_components))

    if options.deploy_tracked_branch is not None:
        if options.app_repo is None:
            raise ValueError("--app-repo is required when --deploy-tracked-branch is set")
        steps.extend(
            _verify_deploy_request(
                client,
                tracked_branch=options.deploy_tracked_branch,
                app_repo=options.app_repo,
                app_revision=options.app_revision,
                verify_mode=options.verify_mode,
                phalanx_repo=options.phalanx_repo,
                phalanx_revision=options.phalanx_revision,
                wait_for_deploy=options.wait_for_deploy,
                deploy_timeout_seconds=options.deploy_timeout_seconds,
                deploy_poll_seconds=options.deploy_poll_seconds,
                sleep=sleep,
                monotonic=monotonic,
            )
        )

    return steps


def _verify_healthz(client: BrokerClient) -> VerificationStep:
    response = client.healthz()
    if response.get("status") != "ok":
        raise RuntimeError(f"broker healthz returned unexpected payload: {response}")
    return VerificationStep("healthz", "broker healthz returned status=ok")


def _verify_app_token(client: BrokerClient) -> VerificationStep:
    response = client.get_app_token()
    token = response.get("token")
    if not isinstance(token, str) or not token:
        raise RuntimeError("broker get-app-token returned empty token")
    return VerificationStep("get-app-token", "app token was returned")


def _verify_argocd_status(client: BrokerClient) -> VerificationStep:
    response = client.argocd_status()
    deployments = response.get("deployments")
    if not isinstance(deployments, list) or not deployments:
        raise RuntimeError(f"argocd-status returned unexpected payload: {response}")
    return VerificationStep("argocd-status", f"received {len(deployments)} deployments")


def _verify_argocd_branch(client: BrokerClient) -> VerificationStep:
    response = client.argocd_branch()
    branch = response.get("branch")
    path = response.get("path")
    if not isinstance(branch, str) or not branch:
        raise RuntimeError(f"argocd-get-branch returned unexpected payload: {response}")
    if not isinstance(path, str) or not path:
        raise RuntimeError(f"argocd-get-branch returned unexpected path: {response}")
    return VerificationStep("argocd-get-branch", f"branch={branch} path={path}")


def _verify_argocd_logs(
    client: BrokerClient,
    component: str,
    since_seconds: int,
) -> VerificationStep:
    response = client.argocd_logs(component, since_seconds)
    pod_name = response.get("pod_name")
    if not isinstance(pod_name, str) or not pod_name:
        raise RuntimeError(f"argocd-logs returned unexpected payload: {response}")
    return VerificationStep("argocd-logs", f"component={component} pod={pod_name}")


def _verify_argocd_sync(client: BrokerClient) -> VerificationStep:
    response = client.argocd_sync()
    if response.get("synced") is not True:
        raise RuntimeError(f"argocd-sync returned unexpected payload: {response}")
    return VerificationStep("argocd-sync", "sync request accepted")


def _verify_argocd_restart(
    client: BrokerClient,
    components: list[str],
) -> VerificationStep:
    response = client.argocd_restart(components)
    restarted = response.get("restarted")
    if not isinstance(restarted, list) or not restarted:
        raise RuntimeError(f"argocd-restart returned unexpected payload: {response}")
    return VerificationStep("argocd-restart", f"restarted={', '.join(restarted)}")


def _verify_deploy_request(
    client: BrokerClient,
    *,
    tracked_branch: str,
    app_repo: Path,
    app_revision: str,
    verify_mode: str,
    phalanx_repo: Path | None,
    phalanx_revision: str,
    wait_for_deploy: bool,
    deploy_timeout_seconds: int,
    deploy_poll_seconds: int,
    sleep: Callable[[int], None],
    monotonic: Callable[[], float],
) -> list[VerificationStep]:
    response = client.request_deploy(
        tracked_branch=tracked_branch,
        app_repo_path=app_repo,
        app_revision=app_revision,
        verify_mode=verify_mode,
        phalanx_repo_path=phalanx_repo,
        phalanx_revision=phalanx_revision,
    )
    request_id = response.get("request_id")
    status = response.get("status")
    if not isinstance(request_id, str) or not request_id:
        raise RuntimeError(f"request-deploy returned unexpected payload: {response}")
    if status not in {"queued", "running", "succeeded", "failed"}:
        raise RuntimeError(f"request-deploy returned unexpected status: {response}")

    steps = [
        VerificationStep(
            "request-deploy",
            f"request_id={request_id} status={status}",
        )
    ]
    if not wait_for_deploy:
        return steps

    deadline = monotonic() + deploy_timeout_seconds
    while status not in {"succeeded", "failed"}:
        if monotonic() >= deadline:
            raise RuntimeError(
                f"deploy request {request_id} did not finish within {deploy_timeout_seconds} seconds"
            )
        sleep(deploy_poll_seconds)
        response = client.get_deploy_status(request_id)
        status = response.get("status")

    if status != "succeeded":
        raise RuntimeError(
            f"deploy request {request_id} failed: {response.get('error') or response}"
        )

    detail = f"request_id={request_id} completed with step={response.get('step')}"
    verification = response.get("verification")
    if isinstance(verification, dict) and verification:
        detail += f" verification={verification}"
    steps.append(VerificationStep("get-deploy-status", detail))
    return steps


def _build_parser() -> argparse.ArgumentParser:
    default_base_url, default_api_token = _settings_defaults()
    parser = argparse.ArgumentParser(
        description="Smoke test deploy broker features on the broker host"
    )
    parser.add_argument("--server", default=default_base_url)
    parser.add_argument("--api-token", default=default_api_token)
    parser.add_argument("--logs-component", default="coordinator")
    parser.add_argument("--logs-since-seconds", type=int, default=600)
    parser.add_argument(
        "--include-sync",
        action="store_true",
        help="also call argocd-sync (mutating)",
    )
    parser.add_argument(
        "--restart-components",
        nargs="*",
        help="also call argocd-restart; omit component names to use broker defaults",
    )
    parser.add_argument(
        "--deploy-tracked-branch",
        help="also submit a deploy request for the given tracked branch (mutating)",
    )
    parser.add_argument("--app-repo", help="required when --deploy-tracked-branch is used")
    parser.add_argument("--app-revision", default="HEAD")
    parser.add_argument("--verify-mode", default="auto", choices=("none", "auto", "all"))
    parser.add_argument("--phalanx-repo")
    parser.add_argument("--phalanx-revision", default="HEAD")
    parser.add_argument(
        "--no-wait-deploy",
        action="store_true",
        help="submit deploy request but do not poll for completion",
    )
    parser.add_argument("--deploy-timeout-seconds", type=int, default=1800)
    parser.add_argument("--deploy-poll-seconds", type=int, default=15)
    return parser


def _options_from_args(args: argparse.Namespace) -> VerificationOptions:
    return VerificationOptions(
        logs_component=args.logs_component,
        logs_since_seconds=args.logs_since_seconds,
        include_sync=args.include_sync,
        restart_components=args.restart_components,
        deploy_tracked_branch=args.deploy_tracked_branch,
        app_repo=Path(args.app_repo).resolve() if args.app_repo else None,
        app_revision=args.app_revision,
        verify_mode=args.verify_mode,
        phalanx_repo=Path(args.phalanx_repo).resolve() if args.phalanx_repo else None,
        phalanx_revision=args.phalanx_revision,
        wait_for_deploy=not args.no_wait_deploy,
        deploy_timeout_seconds=args.deploy_timeout_seconds,
        deploy_poll_seconds=args.deploy_poll_seconds,
    )


def main() -> None:
    parser = _build_parser()
    args = parser.parse_args()
    options = _options_from_args(args)

    client = BrokerClient(args.server, args.api_token)
    try:
        steps = run_verification(client, options)
    except Exception as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
    finally:
        client.close()

    for step in steps:
        print(f"OK {step.name}: {step.detail}")
