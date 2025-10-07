import asyncio
from contextlib import asynccontextmanager
from typing import Any, Coroutine

from fastapi import WebSocket
from fastapi.websockets import WebSocketState


@asynccontextmanager
async def safe_websocket(ws: WebSocket):
    await ws.accept()
    yield


async def run_until_disconnect(ws: WebSocket, coro: Coroutine[Any, Any, None]) -> None:
    """
    WebSocket接続が切断されるか、指定されたコルーチンが完了するまで実行する。

    接続切断は receive_text() を呼び出すことで WebSocketDisconnect 例外として検知される。
    """

    async def monitor_disconnect():
        await ws.receive_text()

    tasks = [asyncio.create_task(coro), asyncio.create_task(monitor_disconnect())]
    done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_EXCEPTION)
    for task in pending:
        task.cancel()
