import asyncio

from fastapi.websockets import WebSocketDisconnect

from quicklook.utils.websocket import run_until_disconnect


class WaitingWebSocket:
    def __init__(self) -> None:
        self.receive_future = asyncio.get_running_loop().create_future()

    async def receive_text(self) -> str:
        return await self.receive_future


class DisconnectingWebSocket:
    async def receive_text(self) -> str:
        raise WebSocketDisconnect(1000, "")


async def test_run_until_disconnect_returns_when_coro_completes():
    ws = WaitingWebSocket()

    async def coro() -> None:
        await asyncio.sleep(0)

    await asyncio.wait_for(run_until_disconnect(ws, coro()), timeout=1)

    assert ws.receive_future.cancelled()


async def test_run_until_disconnect_cancels_worker_when_client_disconnects():
    ws = DisconnectingWebSocket()
    cancelled = asyncio.Event()

    async def coro() -> None:
        try:
            await asyncio.Future()
        except asyncio.CancelledError:
            cancelled.set()
            raise

    await asyncio.wait_for(run_until_disconnect(ws, coro()), timeout=1)

    assert cancelled.is_set()
