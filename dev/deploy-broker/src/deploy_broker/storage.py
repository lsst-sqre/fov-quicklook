from __future__ import annotations

import fcntl
import json
import os
import shlex
import subprocess
import threading
import uuid
from contextlib import contextmanager
from pathlib import Path

from .config import Settings
from .models import DeployRequestRecord, JobLogEntry


class TokenStore:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._lock = threading.RLock()

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
    def _refresh_lock_path(self) -> Path:
        return self._settings.token_dir / ".refresh.lock"

    @contextmanager
    def _refresh_lock(self):
        self._settings.token_dir.mkdir(parents=True, exist_ok=True)
        with self._refresh_lock_path.open("a+", encoding="utf-8") as handle:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
            try:
                yield
            finally:
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)

    def _has_token_command(self) -> bool:
        return bool((self._settings.token_command or "").strip())

    def _token_command_argv(self) -> list[str]:
        command = (self._settings.token_command or "").strip()
        if not command:
            raise RuntimeError("token command is not configured")
        try:
            return shlex.split(command)
        except ValueError as exc:
            raise RuntimeError(f"invalid token command: {exc}") from exc

    def _parse_token_payload(self, stdout: str) -> tuple[str, str]:
        try:
            payload = json.loads(stdout)
        except json.JSONDecodeError as exc:
            raise RuntimeError("token command produced invalid JSON") from exc
        if not isinstance(payload, dict):
            raise RuntimeError("token command JSON must be an object")

        argocd_token = payload.get("argocd_token")
        if not isinstance(argocd_token, str) or not argocd_token.strip():
            raise RuntimeError(
                "token command JSON must contain non-empty string argocd_token"
            )
        app_token = payload.get("gafaelfawr_token")
        if not isinstance(app_token, str) or not app_token.strip():
            raise RuntimeError(
                "token command JSON must contain non-empty string gafaelfawr_token"
            )
        return argocd_token.strip(), app_token.strip()

    def _refresh_tokens_locked(self) -> list[str]:
        argv = self._token_command_argv()
        try:
            completed = subprocess.run(
                argv,
                capture_output=True,
                text=True,
                encoding="utf-8",
                timeout=self._settings.token_command_timeout_seconds,
                check=False,
            )
        except OSError as exc:
            raise RuntimeError(f"failed to run token command: {exc}") from exc
        except subprocess.TimeoutExpired as exc:
            raise RuntimeError(
                "token command timed out after "
                f"{self._settings.token_command_timeout_seconds} seconds"
            ) from exc

        if completed.returncode != 0:
            detail = completed.stderr.strip() or completed.stdout.strip()
            suffix = f": {detail}" if detail else ""
            raise RuntimeError(
                f"token command exited with status {completed.returncode}{suffix}"
            )

        stdout = completed.stdout.strip()
        if not stdout:
            raise RuntimeError("token command produced empty stdout")

        argocd_token, app_token = self._parse_token_payload(stdout)
        self._write_secret(self._argocd_path, argocd_token)
        self._write_secret(self._app_path, app_token)
        return ["argocd", "app"]

    @property
    def _argocd_path(self) -> Path:
        return self._settings.token_dir / "argocd.token"

    @property
    def _app_path(self) -> Path:
        return self._settings.token_dir / "app.token"

    def set_argocd_token(self, token: str) -> None:
        with self._lock:
            self._write_secret(self._argocd_path, token)

    def set_app_token(self, token: str) -> None:
        with self._lock:
            self._write_secret(self._app_path, token)

    def refresh_tokens(self) -> list[str]:
        with self._lock:
            with self._refresh_lock():
                return self._refresh_tokens_locked()

    def _get_token(self, path: Path, missing_message: str, *, refresh: bool) -> str:
        with self._lock:
            token = None if refresh else self._read_text(path)
            if token:
                return token
            if not self._has_token_command():
                raise RuntimeError(missing_message)
            with self._refresh_lock():
                token = None if refresh else self._read_text(path)
                if token:
                    return token
                self._refresh_tokens_locked()
            token = self._read_text(path)
            if token:
                return token
            raise RuntimeError(missing_message)

    def get_argocd_token(self, *, refresh: bool = False) -> str:
        return self._get_token(
            self._argocd_path,
            "ArgoCD token is not configured",
            refresh=refresh,
        )

    def get_app_token(self, *, refresh: bool = False) -> str:
        return self._get_token(
            self._app_path,
            "App access token is not configured",
            refresh=refresh,
        )


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
