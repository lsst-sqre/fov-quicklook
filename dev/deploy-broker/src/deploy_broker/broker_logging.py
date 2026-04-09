from __future__ import annotations

import json
import logging
import re
import shlex
from collections.abc import Iterator, Mapping, Sequence
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from datetime import UTC, datetime
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any

from .config import Settings

_DEFAULT_OUTPUT_LIMIT = 4000
_LOG_RECORD_RESERVED = set(logging.makeLogRecord({}).__dict__.keys()) | {"message", "asctime"}
_SECRET_PATTERNS = (
    re.compile(r"(argocd\.token=)([^;\"'\s]+)"),
    re.compile(r'(gafaelfawr=\"?)([^\";\s]+)(\"?)'),
    re.compile(r"(?i)(authorization[:=]\s*bearer\s+)(\S+)"),
)


@dataclass
class AuditContext:
    correlation_id: str
    remote_host: str | None
    auth_mode: str | None


@dataclass
class DeployLogContext:
    request_id: str
    tracked_branch: str | None
    logger: logging.Logger
    step: str | None = None


_current_audit_context: ContextVar[AuditContext | None] = ContextVar(
    "deploy_broker_audit_context",
    default=None,
)
_current_deploy_context: ContextVar[DeployLogContext | None] = ContextVar(
    "deploy_broker_request_context",
    default=None,
)


class AuditJsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": mask_sensitive_text(record.getMessage()),
        }
        payload.update(_sanitize_log_record(record))
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=True)


class RequestDetailFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        rendered = super().format(record)
        extras = _sanitize_log_record(record)
        if not extras:
            return rendered
        suffix = " ".join(
            f"{key}={json.dumps(value, ensure_ascii=True)}"
            for key, value in sorted(extras.items())
        )
        return f"{rendered} {suffix}"


def configure_logging(settings: Settings) -> None:
    settings.ensure_state_dirs()
    audit_logger = logging.getLogger("deploy_broker.audit")
    _replace_handlers(
        audit_logger,
        [
            _audit_file_handler(settings),
        ],
        level=_coerce_log_level(settings.log_level),
    )


def audit_event(
    event: str,
    *,
    level: int = logging.INFO,
    message: str | None = None,
    **fields: object,
) -> None:
    logger = logging.getLogger("deploy_broker.audit")
    context = _current_audit_context.get()
    if context is not None:
        fields.setdefault("correlation_id", context.correlation_id)
        fields.setdefault("remote_host", context.remote_host)
        fields.setdefault("auth_mode", context.auth_mode)
    logger.log(
        level,
        mask_sensitive_text(message or event),
        extra={"event": event, **_sanitize_mapping(fields)},
    )


@contextmanager
def bind_audit_context(
    *,
    correlation_id: str,
    remote_host: str | None,
    auth_mode: str | None,
) -> Iterator[AuditContext]:
    context = AuditContext(
        correlation_id=correlation_id,
        remote_host=remote_host,
        auth_mode=auth_mode,
    )
    token = _current_audit_context.set(context)
    try:
        yield context
    finally:
        _current_audit_context.reset(token)


@contextmanager
def bind_request_log(
    settings: Settings,
    request_id: str,
    *,
    tracked_branch: str | None = None,
) -> Iterator[DeployLogContext]:
    context = DeployLogContext(
        request_id=request_id,
        tracked_branch=tracked_branch,
        logger=get_request_logger(settings, request_id),
    )
    token = _current_deploy_context.set(context)
    try:
        yield context
    finally:
        _current_deploy_context.reset(token)


def current_deploy_context() -> DeployLogContext | None:
    return _current_deploy_context.get()


def set_deploy_step(step: str | None) -> None:
    context = _current_deploy_context.get()
    if context is not None:
        context.step = step


def get_request_logger(settings: Settings, request_id: str) -> logging.Logger:
    logger = logging.getLogger(f"deploy_broker.request.{request_id}")
    log_path = settings.request_log_path(request_id)
    configured_path = getattr(logger, "_deploy_broker_log_path", None)
    if configured_path != str(log_path) or not logger.handlers:
        _replace_handlers(
            logger,
            [_request_file_handler(log_path)],
            level=_coerce_log_level(settings.log_level),
        )
        setattr(logger, "_deploy_broker_log_path", str(log_path))
    return logger


def log_request_detail(
    level: int,
    message: str,
    **fields: object,
) -> None:
    context = _current_deploy_context.get()
    if context is None:
        return
    extra: dict[str, object] = {"request_id": context.request_id}
    if context.tracked_branch is not None:
        extra["tracked_branch"] = context.tracked_branch
    if context.step is not None:
        extra["step"] = context.step
    extra.update(_sanitize_mapping(fields))
    context.logger.log(level, mask_sensitive_text(message), extra=extra)


def mask_sensitive_text(text: str) -> str:
    masked = text
    for pattern in _SECRET_PATTERNS:
        masked = pattern.sub(r"\1***", masked)
    return masked


def sanitize_command(command: Sequence[str]) -> str:
    return mask_sensitive_text(shlex.join(command))


def summarize_output(
    text: str,
    *,
    limit: int = _DEFAULT_OUTPUT_LIMIT,
) -> str | None:
    sanitized = mask_sensitive_text(text).strip()
    if not sanitized:
        return None
    if len(sanitized) <= limit:
        return sanitized
    truncated = len(sanitized) - limit
    return f"{sanitized[:limit]}\n... ({truncated} chars truncated)"


def summarize_exception(exc: Exception) -> str:
    command = getattr(exc, "command", None)
    returncode = getattr(exc, "returncode", None)
    stdout = getattr(exc, "stdout", None)
    stderr = getattr(exc, "stderr", None)
    if isinstance(command, list) and isinstance(returncode, int):
        summary = f"command failed ({returncode}): {sanitize_command(command)}"
        stderr_excerpt = summarize_output(str(stderr or ""), limit=500)
        stdout_excerpt = summarize_output(str(stdout or ""), limit=500)
        parts = [summary]
        if stderr_excerpt:
            parts.append(f"stderr={stderr_excerpt}")
        elif stdout_excerpt:
            parts.append(f"stdout={stdout_excerpt}")
        return " | ".join(parts)
    return mask_sensitive_text(str(exc))


def _coerce_log_level(level_name: str) -> int:
    level = getattr(logging, level_name.upper(), None)
    if not isinstance(level, int):
        raise ValueError(f"invalid log level: {level_name}")
    return level


def _audit_file_handler(settings: Settings) -> RotatingFileHandler:
    handler = RotatingFileHandler(
        settings.audit_log_path,
        maxBytes=settings.log_max_bytes,
        backupCount=settings.log_backup_count,
        encoding="utf-8",
    )
    handler.setFormatter(AuditJsonFormatter())
    return handler


def _request_file_handler(path: Path) -> logging.FileHandler:
    path.parent.mkdir(parents=True, exist_ok=True)
    handler = logging.FileHandler(path, encoding="utf-8")
    handler.setFormatter(RequestDetailFormatter("%(asctime)s %(levelname)s %(message)s"))
    return handler


def _replace_handlers(
    logger: logging.Logger,
    handlers: list[logging.Handler],
    *,
    level: int,
) -> None:
    for handler in list(logger.handlers):
        logger.removeHandler(handler)
        handler.close()
    for handler in handlers:
        logger.addHandler(handler)
    logger.setLevel(level)
    logger.propagate = False


def _sanitize_log_record(record: logging.LogRecord) -> dict[str, Any]:
    extras: dict[str, Any] = {}
    for key, value in record.__dict__.items():
        if key in _LOG_RECORD_RESERVED or key.startswith("_"):
            continue
        extras[key] = _sanitize_value(value)
    return extras


def _sanitize_mapping(values: Mapping[str, object]) -> dict[str, Any]:
    return {
        key: sanitized
        for key, value in values.items()
        if (sanitized := _sanitize_value(value)) is not None
    }


def _sanitize_value(value: object) -> Any:
    if value is None:
        return None
    if isinstance(value, str):
        return mask_sensitive_text(value)
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, Mapping):
        sanitized: dict[str, Any] = {}
        for key, nested_value in value.items():
            nested = _sanitize_value(nested_value)
            if nested is not None:
                sanitized[str(key)] = nested
        return sanitized
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return [nested for nested_value in value if (nested := _sanitize_value(nested_value)) is not None]
    if isinstance(value, (bool, int, float)):
        return value
    return mask_sensitive_text(str(value))
