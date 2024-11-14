from contextlib import asynccontextmanager

from fastapi import WebSocket
from fastapi.websockets import WebSocketState


@asynccontextmanager
async def safe_websocket(ws: WebSocket):
    try:
        yield
    finally:
        try:
            await ws.close()
        except RuntimeError as e:  # pragma: no cover
            if str(e) not in {
                'Cannot call "send" once a close message has been sent.',
                "Unexpected ASGI message 'websocket.close', after sending 'websocket.close' or response already completed.",
            }:
                raise
