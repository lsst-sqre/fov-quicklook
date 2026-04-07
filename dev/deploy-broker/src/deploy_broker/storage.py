from __future__ import annotations

import json
import os
import threading
import uuid
from pathlib import Path

from .config import Settings
from .models import DeployRequestRecord, JobLogEntry
from .security import extract_app_token, extract_argocd_token


class TokenStore:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def _read_text(self, path: Path) -> str | None:
        if not path.exists():
            return None
        content = path.read_text(encoding="utf-8").strip()
        return content or None

    def _write_secret(self, path: Path, token: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(token, encoding="utf-8")
        os.chmod(path, 0o600)

    @property
    def _argocd_path(self) -> Path:
        return self._settings.token_dir / "argocd.token"

    @property
    def _app_path(self) -> Path:
        return self._settings.token_dir / "app.token"

    def set_argocd_token(self, token: str) -> None:
        self._write_secret(self._argocd_path, token)

    def set_app_token(self, token: str) -> None:
        self._write_secret(self._app_path, token)

    def bootstrap_from_curl_files(self) -> list[str]:
        bootstrapped: list[str] = []
        for kind, path, extractor, setter in (
            (
                "argocd",
                self._settings.argocd_bootstrap_curl_path,
                extract_argocd_token,
                self.set_argocd_token,
            ),
            (
                "app",
                self._settings.app_bootstrap_curl_path,
                extract_app_token,
                self.set_app_token,
            ),
        ):
            if not path.exists():
                continue
            content = path.read_text(encoding="utf-8").strip()
            if not content:
                raise ValueError(f"{path} is empty")
            setter(extractor(content))
            path.unlink()
            bootstrapped.append(kind)
        return bootstrapped

    def get_argocd_token(self) -> str:
        token = self._read_text(self._argocd_path)
        if token:
            return token

        raise RuntimeError("ArgoCD token is not configured")

    def get_app_token(self) -> str:
        token = self._read_text(self._app_path)
        if token:
            return token

        raise RuntimeError("App access token is not configured")


class JobStore:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._lock = threading.Lock()

    def _job_path(self, request_id: str) -> Path:
        return self._settings.job_dir / f"{request_id}.json"

    def create(self, tracked_branch: str, verify_mode: str) -> DeployRequestRecord:
        request_id = uuid.uuid4().hex
        record = DeployRequestRecord(
            request_id=request_id,
            status="queued",
            tracked_branch=tracked_branch,
            verify_mode=verify_mode,  # type: ignore[arg-type]
        )
        self.save(record)
        return record

    def _write_record(self, path: Path, record: DeployRequestRecord) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        temp_path = path.with_suffix(f"{path.suffix}.tmp")
        temp_path.write_text(
            json.dumps(record.model_dump(), ensure_ascii=True, indent=2),
            encoding="utf-8",
        )
        os.replace(temp_path, path)

    def save(self, record: DeployRequestRecord) -> DeployRequestRecord:
        with self._lock:
            path = self._job_path(record.request_id)
            self._write_record(path, record)
        return record

    def load(self, request_id: str) -> DeployRequestRecord:
        path = self._job_path(request_id)
        if not path.exists():
            raise KeyError(request_id)
        return DeployRequestRecord.model_validate_json(path.read_text(encoding="utf-8"))

    def update(self, request_id: str, **changes: object) -> DeployRequestRecord:
        with self._lock:
            record = self.load(request_id)
            updated = record.model_copy(update=changes)
            self._write_record(self._job_path(request_id), updated)
            return updated

    def append_log(self, request_id: str, message: str) -> DeployRequestRecord:
        with self._lock:
            record = self.load(request_id)
            logs = [*record.logs, JobLogEntry(message=message)]
            updated = record.model_copy(update={"logs": logs})
            self._write_record(self._job_path(request_id), updated)
            return updated
