from __future__ import annotations

import argparse
import json
import tempfile
from pathlib import Path
from typing import Any

import httpx

from .config import Settings
from .gitops import create_bundle


class BrokerClient:
    def __init__(self, base_url: str, api_token: str | None) -> None:
        headers = {"Authorization": f"Bearer {api_token}"} if api_token else None
        self._client = httpx.Client(
            base_url=base_url.rstrip("/"),
            headers=headers,
            timeout=120,
        )

    def close(self) -> None:
        self._client.close()

    def healthz(self) -> dict[str, Any]:
        response = self._client.get("/healthz")
        response.raise_for_status()
        return response.json()

    def get_app_token(self, *, refresh: bool = False) -> dict[str, Any]:
        params = {"refresh": "true"} if refresh else None
        response = self._client.get("/v1/tokens/app", params=params)
        response.raise_for_status()
        return response.json()

    def argocd_status(self) -> dict[str, Any]:
        response = self._client.get("/v1/argocd/status")
        response.raise_for_status()
        return response.json()

    def argocd_branch(self) -> dict[str, Any]:
        response = self._client.get("/v1/argocd/branch")
        response.raise_for_status()
        return response.json()

    def argocd_logs(self, component: str, since_seconds: int) -> dict[str, Any]:
        response = self._client.get(
            f"/v1/argocd/logs/{component}",
            params={"since_seconds": since_seconds},
        )
        response.raise_for_status()
        return response.json()

    def argocd_sync(self) -> dict[str, Any]:
        response = self._client.post("/v1/argocd/sync")
        response.raise_for_status()
        return response.json()

    def argocd_restart(self, components: list[str]) -> dict[str, Any]:
        response = self._client.post("/v1/argocd/restart", json={"components": components})
        response.raise_for_status()
        return response.json()

    def request_deploy(
        self,
        tracked_branch: str,
        app_repo_path: Path,
        app_revision: str,
        verify_mode: str,
        phalanx_repo_path: Path | None,
        phalanx_revision: str | None,
    ) -> dict[str, Any]:
        with tempfile.TemporaryDirectory() as temp_dir_name:
            temp_dir = Path(temp_dir_name)
            app_bundle_path = temp_dir / "app.bundle"
            app_meta = create_bundle(app_repo_path, app_revision, app_bundle_path)

            data: dict[str, Any] = {
                "tracked_branch": tracked_branch,
                "verify_mode": verify_mode,
                "app_branch_name": app_meta["branch_name"],
                "app_head_sha": app_meta["head_sha"],
                "app_base_sha": app_meta["base_sha"] or "",
            }
            files: dict[str, Any] = {
                "app_bundle": (
                    app_bundle_path.name,
                    app_bundle_path.read_bytes(),
                    "application/octet-stream",
                )
            }

            if phalanx_repo_path is not None:
                phalanx_bundle_path = temp_dir / "phalanx.bundle"
                phalanx_meta = create_bundle(
                    phalanx_repo_path,
                    phalanx_revision or "HEAD",
                    phalanx_bundle_path,
                )
                data.update(
                    {
                        "phalanx_branch_name": phalanx_meta["branch_name"],
                        "phalanx_head_sha": phalanx_meta["head_sha"],
                        "phalanx_base_sha": phalanx_meta["base_sha"] or "",
                    }
                )
                files["phalanx_bundle"] = (
                    phalanx_bundle_path.name,
                    phalanx_bundle_path.read_bytes(),
                    "application/octet-stream",
                )

            response = self._client.post("/v1/deploy-requests", data=data, files=files)
            response.raise_for_status()
            return response.json()

    def get_deploy_status(self, request_id: str) -> dict[str, Any]:
        response = self._client.get(f"/v1/deploy-requests/{request_id}")
        response.raise_for_status()
        return response.json()


def _settings_defaults() -> tuple[str, str | None]:
    settings = Settings()
    api_token = settings.api_token
    if api_token is None and settings.api_token_file and settings.api_token_file.exists():
        api_token = settings.api_token_file.read_text(encoding="utf-8").strip() or None
    return (
        "http://127.0.0.1:8010",
        api_token,
    )


def _print_json(data: dict[str, Any]) -> None:
    print(json.dumps(data, ensure_ascii=True, indent=2))


def main() -> None:
    default_base_url, default_api_token = _settings_defaults()

    parser = argparse.ArgumentParser(description="Client for the deploy broker daemon")
    parser.add_argument("--server", default=default_base_url)
    parser.add_argument("--api-token", default=default_api_token)
    subparsers = parser.add_subparsers(dest="command", required=True)

    deploy_parser = subparsers.add_parser("request-deploy")
    deploy_parser.add_argument("tracked_branch")
    deploy_parser.add_argument("--app-repo", default=".")
    deploy_parser.add_argument("--app-revision", default="HEAD")
    deploy_parser.add_argument("--verify-mode", default="auto", choices=("none", "auto", "all"))
    deploy_parser.add_argument("--phalanx-repo")
    deploy_parser.add_argument("--phalanx-revision", default="HEAD")

    status_parser = subparsers.add_parser("get-deploy-status")
    status_parser.add_argument("request_id")

    logs_parser = subparsers.add_parser("argocd-logs")
    logs_parser.add_argument("component")
    logs_parser.add_argument("--since-seconds", type=int, default=600)

    restart_parser = subparsers.add_parser("argocd-restart")
    restart_parser.add_argument("components", nargs="*")

    get_app_token_parser = subparsers.add_parser("get-app-token")
    get_app_token_parser.add_argument(
        "--refresh",
        action="store_true",
        help="refresh the app token via the configured token command before returning it",
    )
    subparsers.add_parser("argocd-status")
    subparsers.add_parser("argocd-get-branch")
    subparsers.add_parser("argocd-sync")

    args = parser.parse_args()
    client = BrokerClient(args.server, args.api_token)
    try:
        if args.command == "get-app-token":
            _print_json(client.get_app_token(refresh=args.refresh))
        elif args.command == "argocd-status":
            _print_json(client.argocd_status())
        elif args.command == "argocd-get-branch":
            _print_json(client.argocd_branch())
        elif args.command == "argocd-logs":
            _print_json(client.argocd_logs(args.component, args.since_seconds))
        elif args.command == "argocd-sync":
            _print_json(client.argocd_sync())
        elif args.command == "argocd-restart":
            _print_json(client.argocd_restart(args.components))
        elif args.command == "request-deploy":
            _print_json(
                client.request_deploy(
                    tracked_branch=args.tracked_branch,
                    app_repo_path=Path(args.app_repo).resolve(),
                    app_revision=args.app_revision,
                    verify_mode=args.verify_mode,
                    phalanx_repo_path=Path(args.phalanx_repo).resolve()
                    if args.phalanx_repo
                    else None,
                    phalanx_revision=args.phalanx_revision,
                )
            )
        elif args.command == "get-deploy-status":
            _print_json(client.get_deploy_status(args.request_id))
    finally:
        client.close()
