import asyncio
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Generator, Generic, TypeVar

T = TypeVar('T')


class BroadcastQueue(Generic[T]):
    def __init__(self):
        self._q = asyncio.Queue[T]()
        self._subscriptions: list['Subscription[T]'] = []

    def put(self, value: T) -> None:
        self._q.put_nowait(value)
        for subscriber in self._subscriptions:
            subscriber._put(value)

    @contextmanager
    def subscribe(self) -> Generator['Subscription[T]', None, None]:
        s = Subscription[T]()
        self._subscriptions.append(s)
        try:
            yield s
        finally:
            self._subscriptions.remove(s)


@dataclass
class Subscription(Generic[T]):
    _q: asyncio.Queue[T] = field(default_factory=asyncio.Queue)

    def _put(self, value: T):
        self._q.put_nowait(value)

    async def get(self) -> T:
        return await self._q.get()
