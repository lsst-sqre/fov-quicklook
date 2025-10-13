import asyncio
import pickle
from collections.abc import AsyncIterator, Callable, Generator
from typing import TYPE_CHECKING, Any, Generic, ParamSpec, TypeVar, overload

import websockets.client

from .queue import _RpcQueue

if TYPE_CHECKING:
    from websockets.asyncio.client import ClientConnection
from .types import (
    CallMessage,
    ErrorMessage,
    Message,
    QueueDoneMessage,
    QueuePutMessage,
    ReturnMessage,
    RpcRemoteError,
    YieldMessage,
)

P = ParamSpec("P")
T = TypeVar("T")
R = TypeVar("R")

_next_queue_id = 0


def _get_next_queue_id() -> int:
    """次のキューIDを取得する"""
    global _next_queue_id
    _next_queue_id += 1
    return _next_queue_id


class Rpc(Generic[P, R]):
    """
    リモート関数呼び出しを行うクライアントクラス
    
    使用例:
        # 通常の関数
        result = await Rpc(endpoint_url, func, arg1, arg2).run()
        
        # ジェネレータ関数
        async for item in Rpc(endpoint_url, func, arg1, arg2).run():
            print(item)
    """

    @overload
    def __init__(
        self,
        endpoint_url: str,
        func: Callable[P, Generator[R, Any, Any]],
        *args: P.args,
        **kwargs: P.kwargs,
    ) -> None: ...

    @overload
    def __init__(
        self,
        endpoint_url: str,
        func: Callable[P, R],
        *args: P.args,
        **kwargs: P.kwargs,
    ) -> None: ...

    def __init__(
        self,
        endpoint_url: str,
        func: Callable[P, R] | Callable[P, Generator[R, Any, Any]],
        *args: P.args,
        **kwargs: P.kwargs,
    ):
        self.endpoint_url = endpoint_url
        self.func = func
        self.args = args
        self.kwargs = kwargs
        self._queue_tasks: list[asyncio.Task[None]] = []

    @overload
    async def run(self: "Rpc[P, Generator[R, Any, Any]]") -> AsyncIterator[R]: ...

    @overload
    async def run(self: "Rpc[P, R]") -> R: ...

    async def run(self) -> AsyncIterator[R] | R:
        """
        リモート関数を実行する
        
        Returns:
            ジェネレータの場合はAsyncIterator、通常の関数の場合は結果の値
        
        Raises:
            RpcRemoteError: リモート実行でエラーが発生した場合
        """
        async with websockets.connect(self.endpoint_url) as ws:
            # RpcQueueの処理
            processed_args = []
            for arg in self.args:
                if isinstance(arg, _RpcQueue):
                    queue_id = _get_next_queue_id()
                    arg.queue_id = queue_id
                    processed_args.append(arg)
                    # キューからメッセージを送信するタスクを作成
                    self._queue_tasks.append(
                        asyncio.create_task(
                            self._send_queue_messages(ws, queue_id, arg.queue)
                        )
                    )
                else:
                    processed_args.append(arg)

            processed_kwargs = {}
            for k, v in self.kwargs.items():
                if isinstance(v, _RpcQueue):
                    queue_id = _get_next_queue_id()
                    v.queue_id = queue_id
                    processed_kwargs[k] = v
                    self._queue_tasks.append(
                        asyncio.create_task(
                            self._send_queue_messages(ws, queue_id, v.queue)
                        )
                    )
                else:
                    processed_kwargs[k] = v

            # CallMessageを送信
            call_msg = CallMessage(
                func=self.func,
                args=tuple(processed_args),
                kwargs=processed_kwargs,
            )
            await ws.send(pickle.dumps(call_msg))

            # 結果を受信
            return await self._receive_results(ws)

    async def _send_queue_messages(
        self, ws: "ClientConnection", queue_id: int, q: asyncio.Queue[Any]
    ) -> None:
        """
        asyncio.Queueからアイテムを取得してWebSocketで送信する
        
        Args:
            ws: WebSocketコネクション
            queue_id: キューのID
            q: asyncio.Queue
        """
        try:
            while True:
                item = await q.get()
                if item is None:
                    # 終了メッセージを送信
                    done_msg = QueueDoneMessage(
                        queue_id=queue_id,
                    )
                    await ws.send(pickle.dumps(done_msg))
                    break
                else:
                    # putメッセージを送信
                    put_msg = QueuePutMessage(
                        queue_id=queue_id,
                        value=item,
                    )
                    await ws.send(pickle.dumps(put_msg))
        except asyncio.CancelledError:
            raise
        except Exception:  # pragma: no cover
            pass

    async def _receive_results(self, ws: "ClientConnection") -> AsyncIterator[R] | R:
        """
        WebSocketから結果を受信する
        
        Args:
            ws: WebSocketコネクション
        
        Returns:
            ジェネレータの場合はAsyncIterator、通常の関数の場合は結果の値
        
        Raises:
            RpcRemoteError: リモート実行でエラーが発生した場合
        """
        async def _stream_generator(first_value: R) -> AsyncIterator[R]:
            """ジェネレータとして結果をストリーミングする"""
            yield first_value
            try:
                async for data in ws:
                    if isinstance(data, str):  # pragma: no cover
                        continue
                    message: Message = pickle.loads(data)

                    match message:
                        case YieldMessage(value=value):
                            yield value
                        case ReturnMessage():
                            break
                        case ErrorMessage(error_type=error_type, error_message=error_message, traceback=traceback):
                            raise RpcRemoteError(error_type, error_message, traceback)
            finally:
                for task in self._queue_tasks:
                    task.cancel()
                    try:
                        await task
                    except asyncio.CancelledError:
                        pass

        try:
            async for data in ws:
                if isinstance(data, str):  # pragma: no cover
                    continue
                message: Message = pickle.loads(data)

                match message:
                    case YieldMessage(value=first_value):
                        return _stream_generator(first_value)
                    case ReturnMessage(value=value):
                        return value
                    case ErrorMessage(error_type=error_type, error_message=error_message, traceback=traceback):
                        raise RpcRemoteError(error_type, error_message, traceback)
        finally:
            for task in self._queue_tasks:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
        
        return None  # type: ignore
