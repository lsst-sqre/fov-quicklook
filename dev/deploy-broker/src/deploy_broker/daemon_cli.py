from __future__ import annotations

import argparse
import sys

import uvicorn

from .config import get_settings
from .server import create_app
from .storage import TokenStore


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the deploy broker daemon")
    parser.add_argument("--host", default=None)
    parser.add_argument("--port", type=int, default=None)
    args = parser.parse_args()

    settings = get_settings()
    bootstrapped = TokenStore(settings).bootstrap_from_curl_files()
    if bootstrapped:
        kinds = ", ".join(sorted(bootstrapped))
        print(f"Bootstrapped tokens from startup files: {kinds}", file=sys.stderr)
    app = create_app(settings)
    uvicorn.run(app, host=args.host or settings.host, port=args.port or settings.port)
