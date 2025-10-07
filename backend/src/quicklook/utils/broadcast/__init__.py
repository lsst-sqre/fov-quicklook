import asyncio
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from typing import AsyncIterator, Generic, TypeVar

# セントリネル。_last_value に値が設定されていないことを示すために使う。
NO_VALUE = object()

T = TypeVar('T')


@dataclass
class Broadcast(Generic[T]):
    """単純なブロードキャストユーティリティ。

    Attributes:
        max_queue_size: 各購読者キューの最大サイズ。Noneなら無制限。
        notify_last_on_subscribe: True の場合、直近に put された値を購読開始時に即座に通知する。
    """

    max_queue_size: int | None = None
    notify_last_on_subscribe: bool = True
    _upstream: asyncio.Queue[T] = field(default_factory=asyncio.Queue)
    _subscribers: set[asyncio.Queue[T]] = field(default_factory=set)
    # sentinel を使って last の存在を判定する
    # NO_VALUE を用いることで None を値として扱えるようにする

    # モジュールレベルのセントリネルをセット

    _last_value: object | T = field(default_factory=lambda: NO_VALUE)  # type: ignore[name-defined]

    def __post_init__(self):
        if self.max_queue_size is not None:
            assert self.max_queue_size > 0, "max_queue_size must be positive"

    def put(self, item: T):
        """上流にアイテムを置くと同時に last を更新する。"""
        # 最後の値を保持（セントリネルで判定する）
        self._last_value = item
        self._upstream.put_nowait(item)

    @asynccontextmanager
    async def activate(self):
        async def run():
            while True:
                item = await self._upstream.get()
                for subscriber in list(self._subscribers):
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
        while self.max_queue_size is not None and queue.qsize() >= self.max_queue_size:
            # 古いアイテムを捨てる
            try:
                queue.get_nowait()
            except asyncio.QueueEmpty:
                # 既に空の場合は何もしない
                pass
        queue.put_nowait(item)

    async def subscribe(self) -> AsyncIterator[T]:
        """購読。notify_last_on_subscribe が有効で last が存在すれば、それを即座に送る。"""
        queue: asyncio.Queue[T] = asyncio.Queue()
        self._subscribers.add(queue)
        # 直近値があれば最初にキューへ入れる（NO_VALUE と比較）
        if self.notify_last_on_subscribe and self._last_value is not NO_VALUE:
            self._put_to_subscriber_queue(queue, self._last_value)  # type: ignore[arg-type]
        try:
            while True:
                item = await queue.get()
                yield item
        except GeneratorExit:
            raise
        finally:
            self._subscribers.remove(queue)

    def last_value(self) -> T | None:
        if self._last_value is not NO_VALUE:
            return self._last_value  # type: ignore
