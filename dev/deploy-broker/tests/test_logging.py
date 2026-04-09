from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

from deploy_broker.broker_logging import (
    audit_event,
    bind_request_log,
    configure_logging,
)
from deploy_broker.config import Settings
from deploy_broker.shell import CommandError, run_command


def _settings(tmp_path: Path) -> Settings:
    return Settings(state_dir=tmp_path / "state")


def _audit_entries(settings: Settings) -> list[dict[str, object]]:
    return [
        json.loads(line)
        for line in settings.audit_log_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def test_audit_event_writes_jsonl_log(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    configure_logging(settings)

    audit_event("daemon.start", host="127.0.0.1", port=8010)

    entry = _audit_entries(settings)[-1]
    assert entry["event"] == "daemon.start"
    assert entry["host"] == "127.0.0.1"
    assert entry["port"] == 8010


def test_run_command_logs_request_details_and_masks_stderr(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    configure_logging(settings)

    with bind_request_log(
        settings,
        "request-123",
        tracked_branch="u/michitaro/fov-quicklook-test",
    ):
        run_command(
            [
                sys.executable,
                "-c",
                'import sys; print("ok"); sys.stderr.write("Authorization: Bearer secret-token\\n")',
            ]
        )

    log_text = settings.request_log_path("request-123").read_text(encoding="utf-8")
    assert "Running command" in log_text
    assert "Command succeeded" in log_text
    assert "Command stderr" in log_text
    assert "secret-token" not in log_text
    assert "***" in log_text


def test_run_command_failure_logs_masked_output(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    configure_logging(settings)

    with bind_request_log(settings, "request-456"):
        with pytest.raises(CommandError):
            run_command(
                [
                    sys.executable,
                    "-c",
                    'import sys; sys.stderr.write("argocd.token=secret-token\\n"); sys.exit(3)',
                ]
            )

    log_text = settings.request_log_path("request-456").read_text(encoding="utf-8")
    assert "Command failed" in log_text
    assert "secret-token" not in log_text
    assert "argocd.token=***" in log_text
