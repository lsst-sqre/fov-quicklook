from __future__ import annotations

import argparse
import logging

import uvicorn

from .broker_logging import audit_event, configure_logging, summarize_exception
from .config import get_settings
from .server import create_app
from .storage import TokenStore


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the deploy broker daemon")
    parser.add_argument("--host", default=None)
    parser.add_argument("--port", type=int, default=None)
    args = parser.parse_args()

    settings = get_settings()
    configure_logging(settings)
    bootstrapped = TokenStore(settings).bootstrap_from_curl_files()
    host = args.host or settings.host
    port = args.port or settings.port
    audit_event(
        "daemon.start",
        host=host,
        port=port,
        state_dir=settings.state_dir,
        bootstrapped=sorted(bootstrapped),
    )
    try:
        app = create_app(settings)
        uvicorn.run(app, host=host, port=port)
        audit_event("daemon.stop", host=host, port=port, state_dir=settings.state_dir)
    except Exception as exc:
        audit_event(
            "daemon.crash",
            level=logging.ERROR,
            host=host,
            port=port,
            state_dir=settings.state_dir,
            error=summarize_exception(exc),
        )
        raise
