# TODO: このモジュールの削除。どこからも使われていないかも。
from __future__ import annotations

import asyncio
from collections import deque
from types import TracebackType
from typing import Deque


class _FairGate:
    """入口でFIFO整列し、順番にセマフォへ通す簡易ゲート。"""

    def __init__(self) -> None:
        self._q: Deque[asyncio.Future[None]] = deque()
        self._lock = asyncio.Lock()
        self._loop = asyncio.get_running_loop()

    async def enter(self) -> None:
        fut: asyncio.Future[None] = self._loop.create_future()
        async with self._lock:
            need_wait = bool(self._q)
            self._q.append(fut)
            if not need_wait:
                # 先頭は即時通過
                fut.set_result(None)
        await fut

    async def leave(self) -> None:
        async with self._lock:
            # 今の呼び出しは先頭を消費済みとみなす
            if self._q:
                self._q.popleft()
            # 次の待機者を通す
            while self._q:
                nxt = self._q[0]
                if not nxt.done():
                    nxt.set_result(None)
                    break
                self._q.popleft()


class FairSemaphore:
    """FIFOゲートで順番を固定してから、実セマフォで同時実行数を制御。"""

    def __init__(self, value: int = 1) -> None:
        self._sem = asyncio.Semaphore(value)
        self._gate = _FairGate()

    async def acquire(self) -> bool:
        await self._gate.enter()
        try:
            return await self._sem.acquire()
        except BaseException:
            await self._gate.leave()
            raise

    async def release(self) -> None:
        try:
            self._sem.release()
        finally:
            await self._gate.leave()

    async def __aenter__(self) -> FairSemaphore:
        await self.acquire()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> bool:
        await self.release()
        return False
