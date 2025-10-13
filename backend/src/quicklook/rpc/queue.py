import asyncio
import queue
from typing import ClassVar, Generic, TypeVar

T = TypeVar("T")


class _RpcQueue(Generic[T]):
    """
    asyncio.Queueをラップし、リモート実行時に特別な処理を行うマーカークラス

    クライアント側ではasyncio.Queueを受け取り、
    リモート側ではqueue.Queueとして扱われる。
    """

    _next_id: ClassVar[int] = 0

    def __init__(self, queue: asyncio.Queue[T]):
        self.queue = queue
        # リモート側でキューを識別するためのIDを自動生成
        self.queue_id: int = _RpcQueue._next_id
        _RpcQueue._next_id += 1


def RpcQueue(queue: asyncio.Queue[T]) -> queue.Queue[T]:
    return _RpcQueue(queue)  # type: ignore
