import asyncio
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from typing import AsyncIterator, Generic, TypeVar

T = TypeVar('T')


@dataclass
class Broadcast(Generic[T]):
    max_queue_size: int | None = None
    _upstream: asyncio.Queue[T] = field(default_factory=asyncio.Queue)
    _subscribers: set[asyncio.Queue[T]] = field(default_factory=set)

    def __post_init__(self):
        if self.max_queue_size is not None:
            assert self.max_queue_size > 0, "max_queue_size must be positive"

    def put(self, item: T):
        self._upstream.put_nowait(item)

    @asynccontextmanager
    async def activate(self):
        async def run():
            while True:
                item = await self._upstream.get()
                for subscriber in self._subscribers:
                    self._put_to_subscriber_queue(subscriber, item)

        task = asyncio.create_task(run())
        try:
            yield
        finally:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

    def _put_to_subscriber_queue(self, queue: asyncio.Queue[T], item: T):
        """キューにアイテムを追加。上限を超える場合は古いアイテムを削除。"""
        if self.max_queue_size is not None and queue.qsize() >= self.max_queue_size:
            queue.get_nowait()
        queue.put_nowait(item)

    async def subscribe(self) -> AsyncIterator[T]:
        queue = asyncio.Queue[T]()
        self._subscribers.add(queue)
        try:
            while True:
                item = await queue.get()
                yield item
        finally:
            self._subscribers.remove(queue)
