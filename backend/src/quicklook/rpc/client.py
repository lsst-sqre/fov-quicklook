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


def _process_args_and_kwargs(
    args: tuple[Any, ...],
    kwargs: dict[str, Any],
    ws: "ClientConnection",
    queue_tasks: list[asyncio.Task[None]],
) -> tuple[list[Any], dict[str, Any]]:
    """
    argsとkwargsを処理し、RpcQueueを設定する
    
    Args:
        args: 位置引数
        kwargs: キーワード引数
        ws: WebSocketコネクション
        queue_tasks: キュータスクのリスト（このリストに新しいタスクが追加される）
    
    Returns:
        処理済みのargs, kwargs
    """
    processed_args = []
    for arg in args:
        if isinstance(arg, _RpcQueue):
            queue_id = _get_next_queue_id()
            arg.queue_id = queue_id
            processed_args.append(arg)
            queue_tasks.append(
                asyncio.create_task(_send_queue_messages_helper(ws, queue_id, arg.queue))
            )
        else:
            processed_args.append(arg)

    processed_kwargs = {}
    for k, v in kwargs.items():
        if isinstance(v, _RpcQueue):
            queue_id = _get_next_queue_id()
            v.queue_id = queue_id
            processed_kwargs[k] = v
            queue_tasks.append(
                asyncio.create_task(_send_queue_messages_helper(ws, queue_id, v.queue))
            )
        else:
            processed_kwargs[k] = v

    return processed_args, processed_kwargs


async def _send_queue_messages_helper(
    ws: "ClientConnection", queue_id: int, q: asyncio.Queue[Any]
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
                done_msg = QueueDoneMessage(queue_id=queue_id)
                await ws.send(pickle.dumps(done_msg))
                break
            else:
                put_msg = QueuePutMessage(queue_id=queue_id, value=item)
                await ws.send(pickle.dumps(put_msg))
    except asyncio.CancelledError:
        raise
    except Exception:  # pragma: no cover
        pass


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
        ws = await websockets.connect(self.endpoint_url)
        
        # RpcQueueの処理
        processed_args, processed_kwargs = _process_args_and_kwargs(
            self.args, self.kwargs, ws, self._queue_tasks
        )

        # CallMessageを送信
        call_msg = CallMessage(
            func=self.func,
            args=tuple(processed_args),
            kwargs=processed_kwargs,
        )
        await ws.send(pickle.dumps(call_msg))

        # 結果を受信
        return await self._receive_results(ws)

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
        # WebSocketストリームをイテレータに変換
        ws_iterator = ws.__aiter__()
        
        try:
            # 最初のメッセージを取得
            data = await ws_iterator.__anext__()
            while isinstance(data, str):  # pragma: no cover
                data = await ws_iterator.__anext__()
            
            message: Message = pickle.loads(data)  # type: ignore[arg-type]
            
            match message:
                case YieldMessage(value=first_value):
                    # ジェネレータの場合（WebSocketとキューはジェネレータが管理）
                    return self._stream_remaining_results(ws, ws_iterator, first_value)
                case ReturnMessage(value=value):
                    # 単一の値の場合
                    await self._cleanup_and_close(ws)
                    return value
                case ErrorMessage(error_type=error_type, error_message=error_message, traceback=traceback):
                    # エラーの場合
                    await self._cleanup_and_close(ws)
                    raise RpcRemoteError(error_type, error_message, traceback)
            
            # ここには到達しないはずだが型チェッカーのために
            raise RuntimeError("No message received from server")  # pragma: no cover
        except Exception:
            await self._cleanup_and_close(ws)
            raise
    
    def _cleanup_queue_tasks(self) -> None:
        """キュータスクをクリーンアップする（同期的にキャンセルのみ）"""
        for task in self._queue_tasks:
            task.cancel()
    
    async def _cleanup_and_close(self, ws: "ClientConnection") -> None:
        """WebSocketを閉じてキュータスクをクリーンアップする"""
        try:
            await ws.close()
        except Exception:  # pragma: no cover
            pass
        
        for task in self._queue_tasks:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

    async def _stream_remaining_results(
        self, ws: "ClientConnection", ws_iterator: Any, first_value: R
    ) -> AsyncIterator[R]:
        """
        最初のyield後の残りの結果をストリーミングで受信する
        
        Args:
            ws_iterator: WebSocketのイテレータ
            first_value: 最初にyieldされた値
        """
        try:
            yield first_value
            
            async for data in ws_iterator:
                if isinstance(data, str):  # pragma: no cover
                    continue
                message: Message = pickle.loads(data)

                match message:
                    case YieldMessage(value=value):
                        yield value
                    case ReturnMessage():
                        return
                    case ErrorMessage(error_type=error_type, error_message=error_message, traceback=traceback):
                        raise RpcRemoteError(error_type, error_message, traceback)
        except StopAsyncIteration:  # pragma: no cover
            return
        finally:
            # ジェネレータが終了したらWebSocketを閉じてキューをクリーンアップ
            await self._cleanup_and_close(ws)
