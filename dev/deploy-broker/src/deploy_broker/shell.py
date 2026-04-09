from __future__ import annotations

import logging
import subprocess
import time
from pathlib import Path

from .broker_logging import log_request_detail, sanitize_command, summarize_output


class CommandError(RuntimeError):
    def __init__(
        self,
        command: list[str],
        returncode: int,
        stdout: str,
        stderr: str,
    ) -> None:
        self.command = command
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr
        joined = " ".join(command)
        message = f"command failed ({returncode}): {joined}\nstdout:\n{stdout}\nstderr:\n{stderr}"
        super().__init__(message)


def run_command(
    command: list[str],
    *,
    cwd: Path | None = None,
    env: dict[str, str] | None = None,
    timeout: int | None = None,
) -> str:
    command_text = sanitize_command(command)
    started = time.perf_counter()
    log_request_detail(
        logging.INFO,
        "Running command",
        command=command_text,
        cwd=str(cwd) if cwd is not None else None,
    )
    result = subprocess.run(
        command,
        cwd=cwd,
        env=env,
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )
    duration_ms = round((time.perf_counter() - started) * 1000, 3)
    if result.returncode != 0:
        log_request_detail(
            logging.ERROR,
            "Command failed",
            command=command_text,
            cwd=str(cwd) if cwd is not None else None,
            returncode=result.returncode,
            duration_ms=duration_ms,
            stdout=summarize_output(result.stdout),
            stderr=summarize_output(result.stderr),
        )
        raise CommandError(
            command=command,
            returncode=result.returncode,
            stdout=result.stdout,
            stderr=result.stderr,
        )
    log_request_detail(
        logging.INFO,
        "Command succeeded",
        command=command_text,
        cwd=str(cwd) if cwd is not None else None,
        returncode=result.returncode,
        duration_ms=duration_ms,
    )
    stdout_excerpt = summarize_output(result.stdout)
    if stdout_excerpt is not None:
        log_request_detail(
            logging.DEBUG,
            "Command stdout",
            command=command_text,
            stdout=stdout_excerpt,
        )
    stderr_excerpt = summarize_output(result.stderr)
    if stderr_excerpt is not None:
        log_request_detail(
            logging.WARNING,
            "Command stderr",
            command=command_text,
            stderr=stderr_excerpt,
        )
    return result.stdout
