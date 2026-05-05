from __future__ import annotations

import argparse
import sys

import uvicorn

from .config import get_settings
from .server import create_app


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the deploy broker daemon")
    parser.add_argument("--host", default=None)
    parser.add_argument("--port", type=int, default=None)
    args = parser.parse_args()

    settings = get_settings()
    if not (settings.token_command or "").strip():
        print(
            "ERROR: DEPLOY_BROKER_TOKEN_COMMAND must be configured before starting deploy-broker-daemon",
            file=sys.stderr,
            flush=True,
        )
        raise SystemExit(1)
    api_token = settings.resolve_api_token()
    print(f"Broker bearer token: {api_token}", file=sys.stderr, flush=True)
    app = create_app(settings)
    uvicorn.run(app, host=args.host or settings.host, port=args.port or settings.port)
