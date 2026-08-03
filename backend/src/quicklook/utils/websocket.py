import asyncio
from contextlib import asynccontextmanager, suppress
from typing import Any, Coroutine

from fastapi import WebSocket
from fastapi.websockets import WebSocketDisconnect


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
    try:
        done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
        for task in pending:
            task.cancel()
        for task in pending:
            with suppress(asyncio.CancelledError):
                await task
        for task in done:
            try:
                await task
            except WebSocketDisconnect:
                pass
    finally:
        for task in tasks:
            if task.done():
                continue
            task.cancel()
            with suppress(asyncio.CancelledError):
                await task
