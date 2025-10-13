import asyncio
import queue
from typing import Generic, TypeVar

T = TypeVar("T")


class _RpcQueue(Generic[T]):
    """
    asyncio.Queueをラップし、リモート実行時に特別な処理を行うマーカークラス

    クライアント側ではasyncio.Queueを受け取り、
    リモート側ではqueue.Queueとして扱われる。
    """

    def __init__(self, queue: asyncio.Queue[T]):
        self.queue = queue
        # リモート側でキューを識別するためのID (送信時に設定される)
        self.queue_id: int | None = None


def RpcQueue(queue: asyncio.Queue[T]) -> queue.Queue[T]:
    return _RpcQueue(queue)  # type: ignore
