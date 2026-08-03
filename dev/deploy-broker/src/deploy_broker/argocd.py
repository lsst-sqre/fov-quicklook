from __future__ import annotations

import json
from typing import Any

import httpx

from .config import Settings
from .gitops import EXPECTED_PHALANX_REMOTE_URLS
from .models import (
    ArgoCdBranchResponse,
    ArgoCdLogsResponse,
    ArgoCdRestartResponse,
    ArgoCdSyncResponse,
    ArgoCdStatusResponse,
    DeploymentStatusEntry,
)
from .storage import TokenStore

DEPLOYMENTS = ("coordinator", "generator", "frontend", "db", "debug")
DEFAULT_RESTART_DEPLOYMENTS = ("coordinator", "generator", "frontend", "debug")
AUTH_FAILURE_STATUS_CODES = {401, 403}


class ArgoCdClient:
    def __init__(self, settings: Settings, token_store: TokenStore) -> None:
        self._settings = settings
        self._token_store = token_store

    def _headers(self, *, refresh: bool = False) -> dict[str, str]:
        token = self._token_store.get_argocd_token(refresh=refresh)
        return {"Cookie": f"argocd.token={token}"}

    def _json_headers(self, *, refresh: bool = False) -> dict[str, str]:
        return {**self._headers(refresh=refresh), "Content-Type": "application/json"}

    def _http(self) -> httpx.Client:
        timeout = httpx.Timeout(self._settings.argocd_timeout_seconds)
        return httpx.Client(timeout=timeout)

    def _request(
        self,
        client: httpx.Client,
        method: str,
        url: str,
        *,
        params: dict[str, object] | None = None,
        content: str | None = None,
        json_headers: bool = False,
    ) -> httpx.Response:
        response: httpx.Response | None = None
        for refresh in (False, True):
            headers = (
                self._json_headers(refresh=refresh)
                if json_headers
                else self._headers(refresh=refresh)
            )
            response = client.request(
                method,
                url,
                params=params,
                content=content,
                headers=headers,
            )
            if response.status_code not in AUTH_FAILURE_STATUS_CODES or refresh:
                return response
        assert response is not None
        return response

    def _resource_name(self, component: str) -> str:
        if component in DEPLOYMENTS:
            return f"fov-quicklook-{component}"
        if component.startswith("fov-quicklook-"):
            return component
        raise ValueError(f"unknown component: {component}")

    def _validate_target_revision(self, branch: str) -> None:
        if branch == "main" or branch.startswith("u/michitaro/fov-quicklook-"):
            return
        raise ValueError(
            f"expected main or u/michitaro/fov-quicklook-* branch, got: {branch}"
        )

    def get_app_info(self) -> dict[str, Any]:
        with self._http() as client:
            response = self._request(
                client,
                "GET",
                f"{self._settings.argocd_base_url}/api/v1/applications/{self._settings.argocd_app_name}",
            )
            response.raise_for_status()
            app_info = response.json()
        self.validate_app_source(app_info)
        return app_info

    def validate_app_source(self, app_info: dict[str, Any]) -> None:
        source = app_info["spec"]["source"]
        repo_url = source["repoURL"]
        if repo_url not in EXPECTED_PHALANX_REMOTE_URLS:
            raise RuntimeError(f"unexpected ArgoCD repo URL: {repo_url}")
        path = source["path"]
        if path != self._settings.expected_argocd_path:
            raise RuntimeError(f"unexpected ArgoCD source path: {path}")

    def get_branch(self) -> ArgoCdBranchResponse:
        app_info = self.get_app_info()
        source = app_info["spec"]["source"]
        return ArgoCdBranchResponse(
            repo=source["repoURL"],
            path=source["path"],
            branch=source["targetRevision"],
        )

    def status(self) -> ArgoCdStatusResponse:
        entries: list[DeploymentStatusEntry] = []
        with self._http() as client:
            for component in DEPLOYMENTS:
                deployment = self._resource_name(component)
                response = self._request(
                    client,
                    "GET",
                    f"{self._settings.argocd_base_url}/api/v1/applications/{self._settings.argocd_app_name}/resource",
                    params={
                        "namespace": self._settings.argocd_namespace,
                        "resourceName": deployment,
                        "version": "v1",
                        "group": "apps",
                        "kind": "Deployment",
                    },
                )
                if response.is_error:
                    entries.append(
                        DeploymentStatusEntry(
                            deployment=deployment,
                            ready_replicas="?",
                            replicas="?",
                            image="取得失敗",
                        )
                    )
                    continue
                manifest = json.loads(response.json()["manifest"])
                entries.append(
                    DeploymentStatusEntry(
                        deployment=deployment,
                        ready_replicas=str(manifest["status"].get("readyReplicas", "0")),
                        replicas=str(manifest["status"].get("replicas", "?")),
                        image=manifest["spec"]["template"]["spec"]["containers"][0]["image"],
                    )
                )
        return ArgoCdStatusResponse(deployments=entries)

    def logs(self, component: str, since_seconds: int = 600) -> ArgoCdLogsResponse:
        deployment = self._resource_name(component)
        with self._http() as client:
            tree_response = self._request(
                client,
                "GET",
                f"{self._settings.argocd_base_url}/api/v1/applications/{self._settings.argocd_app_name}/resource-tree",
            )
            tree_response.raise_for_status()
            nodes = tree_response.json().get("nodes", [])

            pod_name = ""
            for node in nodes:
                if node.get("kind") == "Pod" and node.get("name", "").startswith(
                    f"{deployment}-"
                ):
                    pod_name = node["name"]
                    break
            if not pod_name:
                raise RuntimeError(f"pod not found for component: {component}")

            logs_response = self._request(
                client,
                "GET",
                f"{self._settings.argocd_base_url}/api/v1/applications/{self._settings.argocd_app_name}/logs",
                params={
                    "namespace": self._settings.argocd_namespace,
                    "podName": pod_name,
                    "container": deployment,
                    "sinceSeconds": since_seconds,
                },
            )
            logs_response.raise_for_status()

        lines: list[str] = []
        for line in logs_response.text.splitlines():
            try:
                lines.append(json.loads(line)["result"]["content"])
            except Exception:
                continue
        return ArgoCdLogsResponse(component=component, pod_name=pod_name, logs="".join(lines))

    def set_branch(self, branch: str, image_tag: str | None = None) -> None:
        self._validate_target_revision(branch)
        app_info = self.get_app_info()
        patch_source: dict[str, Any] = {"targetRevision": branch}
        if image_tag is not None:
            current_parameters = app_info["spec"]["source"].get("helm", {}).get("parameters", [])
            updated_parameters = [
                parameter
                for parameter in current_parameters
                if parameter.get("name") != "image.tag"
            ]
            updated_parameters.append({"name": "image.tag", "value": image_tag})
            patch_source["helm"] = {"parameters": updated_parameters}
        payload = {
            "name": self._settings.argocd_app_name,
            "patch": json.dumps({"spec": {"source": patch_source}}),
            "patchType": "merge",
        }
        with self._http() as client:
            response = self._request(
                client,
                "PATCH",
                f"{self._settings.argocd_base_url}/api/v1/applications/{self._settings.argocd_app_name}",
                content=json.dumps(payload),
                json_headers=True,
            )
            response.raise_for_status()
            self.validate_app_source(response.json())

    def sync(self) -> ArgoCdSyncResponse:
        self.get_app_info()
        with self._http() as client:
            response = self._request(
                client,
                "POST",
                f"{self._settings.argocd_base_url}/api/v1/applications/{self._settings.argocd_app_name}/sync",
                content=json.dumps({"name": self._settings.argocd_app_name}),
                json_headers=True,
            )
            response.raise_for_status()
        return ArgoCdSyncResponse()

    def restart(self, components: list[str] | None = None) -> ArgoCdRestartResponse:
        targets = components or list(DEFAULT_RESTART_DEPLOYMENTS)
        restarted: list[str] = []
        self.get_app_info()
        with self._http() as client:
            for component in targets:
                deployment = self._resource_name(component)
                response = self._request(
                    client,
                    "POST",
                    f"{self._settings.argocd_base_url}/api/v1/applications/{self._settings.argocd_app_name}/resource/actions/v2",
                    content=json.dumps(
                        {
                            "name": self._settings.argocd_app_name,
                            "namespace": self._settings.argocd_namespace,
                            "resourceName": deployment,
                            "version": "v1",
                            "group": "apps",
                            "kind": "Deployment",
                            "action": "restart",
                        }
                    ),
                    json_headers=True,
                )
                response.raise_for_status()
                restarted.append(deployment)
        return ArgoCdRestartResponse(restarted=restarted)

    def set_branch_and_sync(self, branch: str, image_tag: str | None = None) -> None:
        self.set_branch(branch, image_tag=image_tag)
        self.sync()
