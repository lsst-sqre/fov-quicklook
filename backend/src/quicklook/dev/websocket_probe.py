import argparse
import asyncio
import logging

import uvicorn
import websockets
from fastapi import FastAPI, WebSocket
from starlette.websockets import WebSocketDisconnect


logger = logging.getLogger(__name__)
app = FastAPI()


@app.get("/healthz")
async def healthz() -> dict[str, str]:
    return {"status": "ok"}


@app.websocket("/ws")
async def websocket_echo(ws: WebSocket) -> None:
    await ws.accept()
    try:
        while True:
            message = await ws.receive_text()
            await ws.send_text(message)
    except WebSocketDisconnect:
        return


async def run_client(url: str, message: str, repeat: bool, interval_seconds: float) -> int:
    while True:
        try:
            async with websockets.connect(url) as ws:
                await ws.send(message)
                echoed = await ws.recv()
                if echoed != message:
                    raise RuntimeError(f"Unexpected echo: {echoed!r}")
                logger.info("websocket probe succeeded url=%s message=%s", url, message)
        except Exception:
            logger.exception("websocket probe failed url=%s", url)
            return 1

        if not repeat:
            return 0
        await asyncio.sleep(interval_seconds)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Minimal websocket probe for pod-to-pod connectivity")
    parser.add_argument("--log-level", default="INFO")
    subparsers = parser.add_subparsers(dest="command", required=True)

    server = subparsers.add_parser("server")
    server.add_argument("--host", default="0.0.0.0")
    server.add_argument("--port", type=int, default=9801)

    client = subparsers.add_parser("client")
    client.add_argument("--url", required=True)
    client.add_argument("--message", default="ping")
    client.add_argument("--interval-seconds", type=float, default=10.0)
    client.add_argument("--repeat", action="store_true")
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    logging.basicConfig(
        level=getattr(logging, args.log_level.upper(), logging.INFO),
        format="%(levelname)s: %(message)s",
    )

    if args.command == "server":
        uvicorn.run(
            app,
            host=args.host,
            port=args.port,
            log_level=args.log_level.lower(),
            access_log=False,
            ws="websockets-sansio",
        )
        return 0

    return asyncio.run(
        run_client(
            url=args.url,
            message=args.message,
            repeat=args.repeat,
            interval_seconds=args.interval_seconds,
        )
    )


if __name__ == "__main__":
    raise SystemExit(main())
